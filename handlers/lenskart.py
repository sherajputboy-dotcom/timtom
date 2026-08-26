#!/usr/bin/env python3
"""Lenskart reward claiming handlers — OTP flow, reward claim, voucher check"""

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from middleware.force_join import require_join
from utils.device import LenskartDevice
from utils.keyboard import main_menu_keyboard, back_button
from config import DEFAULT_STEPS

# In-memory pending OTP store
pending_otps = {}


@require_join
async def claim_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 🏃 Claim Reward button."""
    query = update.callback_query
    await query.answer()
    db = context.bot_data["db"]

    # Check if claims are enabled
    claims_enabled = await db.get_setting("claims_enabled", "1")
    if claims_enabled == "0":
        await query.edit_message_text(
            "❌ *Claims are currently disabled.*\n\nPlease try again later.",
            reply_markup=back_button("main_menu"),
            parse_mode="Markdown"
        )
        return

    context.user_data["action"] = "waiting_phone"
    await query.edit_message_text(
        "🏃 *Claim Lenskart Reward*\n\n"
        "📱 Enter your phone number:\n\n"
        "Examples:\n"
        "• `9876543210` (Indian number)\n"
        "• `+919876543210` (with country code)\n\n"
        "❌ Send /cancel to cancel.",
        parse_mode="Markdown"
    )


async def handle_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process phone number input."""
    if context.user_data.get("action") != "waiting_phone":
        return False  # Not our input

    user = update.effective_user
    phone = update.message.text.strip()

    # Normalize phone number
    if phone.startswith("/"):
        if phone == "/cancel":
            context.user_data["action"] = None
            await update.message.reply_text(
                "❌ Cancelled.", reply_markup=main_menu_keyboard()
            )
        return True

    if not phone.startswith("+"):
        if phone.startswith("0"):
            phone = phone[1:]
        if len(phone) == 10 and phone.isdigit():
            phone = f"+91{phone}"
        else:
            await update.message.reply_text(
                "❌ Invalid phone number! Use: `9876543210` or `+919876543210`",
                parse_mode="Markdown"
            )
            return True

    context.user_data["action"] = None
    await update.message.reply_text("⏳ Setting up device & sending OTP...")

    # Create device and send OTP
    try:
        device = LenskartDevice(phone)

        if not device.create_session():
            err = device.last_error or "Unknown session error"
            await update.message.reply_text(
                f"❌ Failed to create session for `{phone}`\n`{err}`",
                parse_mode="Markdown"
            )
            return True

        otp_res = device.send_otp()
        if not otp_res:
            err = device.last_error or "Unknown OTP error"
            await update.message.reply_text(
                f"❌ Failed to send OTP to `{phone}`\n`{err}`",
                parse_mode="Markdown"
            )
            return True

        # Store pending OTP
        pending_otps[f"{user.id}_{phone}"] = device
        context.user_data["action"] = "waiting_otp"
        context.user_data["pending_phone"] = phone

        await update.message.reply_text(
            f"✅ *OTP Sent!*\n\n"
            f"📱 Phone: `{phone}`\n"
            f"📱 Device: `{device.device_info}`\n"
            f"🆔 UDID: `{device.udid}`\n\n"
            f"📝 *Enter the OTP you received:*\n"
            f"❌ Send /cancel to cancel.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

    return True


async def handle_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process OTP input."""
    if context.user_data.get("action") != "waiting_otp":
        return False  # Not our input

    user = update.effective_user
    otp_code = update.message.text.strip()

    if otp_code.startswith("/"):
        if otp_code == "/cancel":
            context.user_data["action"] = None
            context.user_data["pending_phone"] = None
            await update.message.reply_text(
                "❌ Cancelled.", reply_markup=main_menu_keyboard()
            )
        return True

    # Validate OTP format
    if not otp_code.isdigit() or len(otp_code) not in (4, 6):
        await update.message.reply_text("❌ Invalid OTP! Enter a 4 or 6-digit code.")
        return True

    phone = context.user_data.get("pending_phone")
    key = f"{user.id}_{phone}"
    device = pending_otps.get(key)

    if not device:
        await update.message.reply_text("❌ Session expired! Start again from the menu.")
        context.user_data["action"] = None
        return True

    await update.message.reply_text("⏳ Verifying OTP...")

    # Verify OTP
    verify_res = device.verify_otp(otp_code)
    if not verify_res:
        await update.message.reply_text("❌ Invalid OTP! Try again or send /cancel.")
        return True

    # Get user profile and claim reward
    await update.message.reply_text("⏳ Claiming reward...")
    device.get_me()

    db = context.bot_data["db"]
    steps = int(await db.get_setting("claim_steps", str(DEFAULT_STEPS)))
    reward = device.claim_reward(steps=steps)

    if reward and reward.get("giftVoucher"):
        voucher_code = reward.get("giftVoucher")
        tier = reward.get("tier")
        expiry = reward.get("giftVoucherExpiryDate")

        # Save to database
        await db.add_voucher(
            user_id=user.id,
            phone=phone,
            voucher_code=voucher_code,
            tier=tier,
            device_brand=device.brand,
            device_model=device.model,
            expiry_date=expiry
        )

        text = (
            f"🎉 *REWARD CLAIMED!* 🎉\n\n"
            f"📱 Phone: `{phone}`\n"
            f"🎫 Voucher: `{voucher_code}`\n"
        )
        if tier:
            text += f"🏆 Tier: `{tier}`\n"
        text += (
            f"📱 Device: `{device.device_info}`\n"
            f"🆔 UDID: `{device.udid}`\n"
        )
        if expiry:
            from datetime import datetime
            try:
                exp_dt = datetime.fromtimestamp(expiry / 1000)
                text += f"⏰ Expiry: `{exp_dt.strftime('%d %b %Y')}`\n"
            except Exception:
                pass
        text += "\n✅ Saved to your account!"

        await update.message.reply_text(
            text, reply_markup=main_menu_keyboard(), parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ Failed to claim reward for `{phone}`\n\n"
            "Possible reasons:\n"
            "• Already claimed today\n"
            "• Campaign not active\n"
            "• API error",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    # Cleanup
    pending_otps.pop(key, None)
    context.user_data["action"] = None
    context.user_data["pending_phone"] = None
    return True


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route text input based on current action state."""
    # Try phone input first, then OTP
    if await handle_phone_input(update, context):
        return True
    if await handle_otp_input(update, context):
        return True
    return False

#!/usr/bin/env python3
"""Lenskart reward claiming handlers — OTP flow, reward claim, voucher check & points deduction"""

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from middleware.force_join import require_join
from utils.device import LenskartDevice
from utils.keyboard import main_menu_keyboard, back_button
from config import DEFAULT_STEPS, CLAIM_COST_POINTS, CREDIT_FOOTER

# In-memory pending OTP store
pending_otps = {}


@require_join
async def claim_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 🏃 Claim Reward button with Points check."""
    db = context.bot_data["db"]
    user = update.effective_user

    # Handle both callback query and text message (reply keyboard)
    is_callback = update.callback_query is not None
    if is_callback:
        await update.callback_query.answer()

    # Check if claims are enabled
    claims_enabled = await db.get_setting("claims_enabled", "1")
    if claims_enabled == "0":
        msg = "❌ *Claims are currently disabled.*\n\nPlease try again later."
        if is_callback:
            await update.callback_query.edit_message_text(msg, reply_markup=back_button("main_menu"), parse_mode="Markdown")
        else:
            await update.message.reply_text(msg, reply_markup=back_button("main_menu"), parse_mode="Markdown")
        return

    # Check user points balance (Must have at least 20 points)
    points = await db.get_user_points(user.id)
    if points < CLAIM_COST_POINTS:
        msg = (
            f"❌ *INSUFFICIENT POINTS!*\n\n"
            f"💰 *Your Balance:* `{points} Points`\n"
            f"🏃 *Required for Claim:* `{CLAIM_COST_POINTS} Points`\n\n"
            f"🔥 *Earn Points:* Share your referral link with friends to get *+50 Points* per referral!"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("👥 Refer Friends (+50 Pts)", callback_data="user_referrals")],
            [InlineKeyboardButton("🔙 Back to Menu", callback_data="main_menu")]
        ])
        if is_callback:
            await update.callback_query.edit_message_text(msg, reply_markup=keyboard, parse_mode="Markdown")
        else:
            await update.message.reply_text(msg, reply_markup=keyboard, parse_mode="Markdown")
        return

    context.user_data["action"] = "waiting_phone"
    msg_text = (
        f"🏃 *CLAIM LENSKART VOUCHER*\n\n"
        f"💳 *Cost:* `{CLAIM_COST_POINTS} Points` (Balance: `{points} Points`)\n\n"
        f"📱 *Enter your 10-digit mobile number:*\n\n"
        f"Examples:\n"
        f"• `9876543210`\n"
        f"• `+919876543210`\n\n"
        f"❌ Send /cancel to exit."
    )
    if is_callback:
        await update.callback_query.edit_message_text(msg_text, parse_mode="Markdown")
    else:
        await update.message.reply_text(msg_text, parse_mode="Markdown")


async def handle_phone_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process phone number input."""
    if context.user_data.get("action") != "waiting_phone":
        return False

    user = update.effective_user
    phone = update.message.text.strip()

    if phone.startswith("/"):
        if phone == "/cancel":
            context.user_data["action"] = None
            await update.message.reply_text("❌ Cancelled.", reply_markup=main_menu_keyboard())
        return True

    if not phone.startswith("+"):
        if phone.startswith("0"):
            phone = phone[1:]
        if len(phone) == 10 and phone.isdigit():
            phone = f"+91{phone}"
        else:
            await update.message.reply_text(
                "❌ Invalid phone number! Enter a 10-digit number e.g. `9876543210`",
                parse_mode="Markdown"
            )
            return True

    context.user_data["action"] = None
    await update.message.reply_text("⏳ *Initializing device fingerprint & requesting OTP...*", parse_mode="Markdown")

    try:
        device = LenskartDevice(phone)

        if not device.create_session():
            err = device.last_error or "Session initialization failed"
            await update.message.reply_text(
                f"❌ Failed to create session for `{phone}`\n`{err}`",
                parse_mode="Markdown"
            )
            return True

        otp_res = device.send_otp()
        if not otp_res:
            err = device.last_error or "OTP request failed"
            await update.message.reply_text(
                f"❌ Failed to send OTP to `{phone}`\n`{err}`",
                parse_mode="Markdown"
            )
            return True

        pending_otps[f"{user.id}_{phone}"] = device
        context.user_data["action"] = "waiting_otp"
        context.user_data["pending_phone"] = phone

        await update.message.reply_text(
            f"✅ *OTP SENT SUCCESSFULLY!*\n\n"
            f"📱 Phone: `{phone}`\n"
            f"📱 Device Spoof: `{device.device_info}`\n\n"
            f"📝 *Enter the 4 or 6-digit OTP code received on your phone:*\n"
            f"❌ Send /cancel to cancel.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

    return True


async def handle_otp_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process OTP input & claim reward."""
    if context.user_data.get("action") != "waiting_otp":
        return False

    user = update.effective_user
    otp_code = update.message.text.strip()

    if otp_code.startswith("/"):
        if otp_code == "/cancel":
            context.user_data["action"] = None
            context.user_data["pending_phone"] = None
            await update.message.reply_text("❌ Cancelled.", reply_markup=main_menu_keyboard())
        return True

    if not otp_code.isdigit() or len(otp_code) not in (4, 6):
        await update.message.reply_text("❌ Invalid OTP! Enter a 4 or 6-digit code.")
        return True

    phone = context.user_data.get("pending_phone")
    key = f"{user.id}_{phone}"
    device = pending_otps.get(key)

    if not device:
        await update.message.reply_text("❌ Session expired! Please start again.")
        context.user_data["action"] = None
        return True

    await update.message.reply_text("⏳ *Authenticating OTP & injecting 30,000 steps...*", parse_mode="Markdown")

    verify_res = device.verify_otp(otp_code)
    if not verify_res:
        await update.message.reply_text("❌ Invalid OTP! Check the code and try again or send /cancel.")
        return True

    await update.message.reply_text("⏳ *Claiming gift voucher...*", parse_mode="Markdown")
    device.get_me()

    db = context.bot_data["db"]
    steps = int(await db.get_setting("claim_steps", str(DEFAULT_STEPS)))
    reward = device.claim_reward(steps=steps)

    if reward and reward.get("giftVoucher"):
        voucher_code = reward.get("giftVoucher")
        tier = reward.get("tier")
        expiry = reward.get("giftVoucherExpiryDate")

        # Deduct 20 points from user balance
        await db.deduct_points(user.id, CLAIM_COST_POINTS)
        new_balance = await db.get_user_points(user.id)

        # Save voucher to DB
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
            f"🎉 *REWARD CLAIMED SUCCESSFULLY!* 🎉\n\n"
            f"📱 Phone: `{phone}`\n"
            f"🎫 Voucher Code: `{voucher_code}`\n"
        )
        if tier:
            text += f"🏆 Tier: `{tier}`\n"
        text += (
            f"📱 Device: `{device.device_info}`\n"
            f"💳 Remaining Balance: `{new_balance} Points`\n\n"
            f"✅ Saved to your Voucher Vault!\n\n"
            f"{CREDIT_FOOTER}"
        )

        await update.message.reply_text(
            text, reply_markup=main_menu_keyboard(), parse_mode="Markdown"
        )
    else:
        err = device.last_error or "Voucher claim rejected"
        await update.message.reply_text(
            f"❌ *Failed to claim voucher for `{phone}`*\n\n"
            f"Details: `{err}`\n\n"
            f"Possible reasons:\n"
            f"• Already claimed today on this account\n"
            f"• Lenskart campaign limit reached",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

    # Cleanup
    pending_otps.pop(key, None)
    context.user_data["action"] = None
    context.user_data["pending_phone"] = None
    return True


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route text input based on state or persistent reply keyboard button."""
    text = update.message.text.strip() if update.message and update.message.text else ""

    # Check for Reply Keyboard button triggers
    if text == "🏃 Claim Reward":
        await claim_callback(update, context)
        return True
    elif text == "🎁 My Vouchers":
        from handlers.user_menu import show_vouchers
        await show_vouchers(update, context)
        return True
    elif text == "👥 Refer & Earn":
        from handlers.user_menu import show_referrals
        await show_referrals(update, context)
        return True
    elif text == "👤 My Profile":
        from handlers.user_menu import show_profile
        await show_profile(update, context)
        return True
    elif text == "🏆 Leaderboard":
        from handlers.user_menu import show_leaderboard
        await show_leaderboard(update, context)
        return True
    elif text == "ℹ️ Help":
        from handlers.user_menu import show_help
        await show_help(update, context)
        return True

    if await handle_phone_input(update, context):
        return True
    if await handle_otp_input(update, context):
        return True
    return False

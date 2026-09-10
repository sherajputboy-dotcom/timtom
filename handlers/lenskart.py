#!/usr/bin/env python3
"""Lenskart reward claiming handlers — OTP flow, reward claim, voucher check & points deduction (Enhanced UX/UI & State Safety)"""

import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from middleware.force_join import require_join
from utils.device import LenskartDevice
from utils.keyboard import main_reply_keyboard, main_menu_keyboard, back_button, claim_result_keyboard
from config import DEFAULT_STEPS, CLAIM_COST_POINTS, CREDIT_FOOTER

# In-memory pending OTP store
pending_otps = {}


@require_join
async def claim_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 🏃 Claim Reward button with Points check."""
    db = context.bot_data["db"]
    user = update.effective_user

    # Clear any previous pending states
    context.user_data["action"] = None

    # Handle both callback query and text message (reply keyboard)
    is_callback = update.callback_query is not None
    if is_callback:
        await update.callback_query.answer()

    # Check if claims are enabled
    claims_enabled = await db.get_setting("claims_enabled", "1")
    if claims_enabled == "0":
        msg = "❌ *Claims are currently disabled by Admin.*\n\nPlease check back later!"
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
            f"💳 *Your Balance:* `{points} Points`\n"
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
        f"⚡ 🏃 *CLAIM LENSKART REWARD* 🏃 ⚡\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
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
        context.user_data["action"] = None
        context.user_data["pending_phone"] = None
        if phone in ("/cancel", "cancel"):
            await update.message.reply_text("❌ Action cancelled.", reply_markup=main_reply_keyboard())
            return True
        return False  # Pass control to standard command handlers (/start, /admin, /profile, etc.)

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
    status_msg = await update.message.reply_text(
        "⏳ *Step 1/3: Initializing Android Device Fingerprint...*",
        parse_mode="Markdown"
    )

    try:
        device = LenskartDevice(phone)

        if not device.create_session():
            err = device.last_error or "Session initialization failed"
            await status_msg.edit_text(
                f"❌ *Failed to Create Session*\n\n"
                f"📱 Phone: `{phone}`\n"
                f"⚠️ Error: `{err}`",
                parse_mode="Markdown"
            )
            return True

        await status_msg.edit_text(
            "⏳ *Step 2/3: Requesting OTP from Lenskart API...*",
            parse_mode="Markdown"
        )

        otp_res = device.send_otp()
        if not otp_res:
            err = device.last_error or "OTP request failed"
            await status_msg.edit_text(
                f"❌ *Failed to Send OTP*\n\n"
                f"📱 Phone: `{phone}`\n"
                f"⚠️ Error: `{err}`",
                parse_mode="Markdown"
            )
            return True

        pending_otps[f"{user.id}_{phone}"] = device
        context.user_data["action"] = "waiting_otp"
        context.user_data["pending_phone"] = phone

        await status_msg.edit_text(
            f"✅ *OTP SENT SUCCESSFULLY!* 📱\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"📱 *Phone:* `{phone}`\n"
            f"📱 *Device Spoofed:* `{device.device_info}`\n\n"
            f"📝 *Enter the 4 or 6-digit OTP code received on your phone:*\n"
            f"❌ Send /cancel to exit.",
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
        context.user_data["action"] = None
        context.user_data["pending_phone"] = None
        if otp_code in ("/cancel", "cancel"):
            await update.message.reply_text("❌ Action cancelled.", reply_markup=main_reply_keyboard())
            return True
        return False  # Pass control to standard command handlers (/start, /admin, /profile, etc.)

    if not otp_code.isdigit() or len(otp_code) not in (4, 6):
        await update.message.reply_text("❌ Invalid OTP! Enter a 4 or 6-digit code.")
        return True

    phone = context.user_data.get("pending_phone")
    key = f"{user.id}_{phone}"
    device = pending_otps.get(key)

    if not device:
        await update.message.reply_text("❌ Session expired! Please start again from the menu.", reply_markup=main_reply_keyboard())
        context.user_data["action"] = None
        return True

    status_msg = await update.message.reply_text(
        "⏳ *Step 1/2: Authenticating OTP Session...*",
        parse_mode="Markdown"
    )

    verify_res = device.verify_otp(otp_code)
    if not verify_res:
        err = device.last_error or "Invalid or expired OTP code"
        await status_msg.edit_text(
            f"❌ *OTP Verification Failed*\n\n"
            f"📱 Phone: `{phone}`\n"
            f"⚠️ Reason: `{err}`\n\n"
            f"Please check the code and try again, or send /cancel.",
            parse_mode="Markdown"
        )
        return True

    await status_msg.edit_text(
        "⏳ *Step 2/2: Injecting 30,000 Steps & Claiming Gift Voucher...*",
        parse_mode="Markdown"
    )

    device.get_me()

    db = context.bot_data["db"]
    steps = int(await db.get_setting("claim_steps", str(DEFAULT_STEPS)))
    reward = device.claim_reward(steps=steps)

    # Double-check vouchers if primary eligibility call did not return voucher code
    if not reward or not (reward.get("giftVoucher") or reward.get("voucherCode") or reward.get("code")):
        reward = device.check_vouchers()

    if reward and (reward.get("giftVoucher") or reward.get("voucherCode") or reward.get("code")):
        voucher_code = reward.get("giftVoucher") or reward.get("voucherCode") or reward.get("code")
        tier = reward.get("tier") or reward.get("voucherTier")
        expiry = reward.get("giftVoucherExpiryDate") or reward.get("expiryDate")

        # Deduct 20 points from user balance
        await db.deduct_points(user.id, CLAIM_COST_POINTS)
        new_balance = await db.get_user_points(user.id)

        # Format expiry date
        exp_formatted = "N/A"
        if expiry:
            try:
                if isinstance(expiry, (int, float)):
                    exp_dt = datetime.fromtimestamp(expiry / 1000)
                    exp_formatted = exp_dt.strftime("%d %b %Y")
                else:
                    exp_formatted = str(expiry)
            except Exception:
                exp_formatted = str(expiry)

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
            f"🎉 🎁 *LENSKART REWARD CLAIMED!* 🎁 🎉\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"🎫 *VOUCHER CODE:*\n"
            f"`{voucher_code}`\n"
            f"_(Tap code above to copy!)\n\n"
            f"📋 *CLAIM DETAILS:*\n"
            f"📱 *Phone:* `{phone}`\n"
        )
        if tier:
            text += f"🏆 *Reward Tier:* `{tier}`\n"
        if exp_formatted != "N/A":
            text += f"⏰ *Expiry Date:* `{exp_formatted}`\n"
        text += (
            f"📱 *Device Spoofed:* `{device.device_info}`\n"
            f"🆔 *UDID:* `{device.udid}`\n\n"
            f"💳 *Remaining Balance:* `{new_balance} Points`\n"
            f"✅ *Saved to your Voucher Vault!*\n\n"
            f"{CREDIT_FOOTER}"
        )

        await status_msg.edit_text(
            text, reply_markup=claim_result_keyboard(), parse_mode="Markdown"
        )
    else:
        err = device.last_error or "Voucher claim rejected by Lenskart API"
        text = (
            f"❌ *CLAIM FAILED FOR `{phone}`*\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"⚠️ *Details / API Response:*\n"
            f"`{err}`\n\n"
            f"💡 *Possible Causes:*\n"
            f"• Reward already claimed today for this mobile number\n"
            f"• Lenskart daily campaign stock limit reached\n\n"
            f"{CREDIT_FOOTER}"
        )
        await status_msg.edit_text(
            text, reply_markup=claim_result_keyboard(), parse_mode="Markdown"
        )

    # Cleanup
    pending_otps.pop(key, None)
    context.user_data["action"] = None
    context.user_data["pending_phone"] = None
    return True


async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route text input based on state or persistent reply keyboard button."""
    text = update.message.text.strip() if update.message and update.message.text else ""

    # Check for Reply Keyboard button triggers FIRST (clears any active action state)
    if text in ("🏃 Claim Reward", "🏃 Claim Reward (20 Pts)", "⚡ 🏃 CLAIM REWARD", "⚡ 🏃 CLAIM REWARD (20 Pts)"):
        context.user_data["action"] = None
        await claim_callback(update, context)
        return True
    elif text in ("🎁 My Vouchers", "🎁 MY VOUCHERS"):
        context.user_data["action"] = None
        from handlers.user_menu import show_vouchers
        await show_vouchers(update, context)
        return True
    elif text in ("👥 Refer & Earn", "🔥 REFER & EARN", "👥 REFER & EARN"):
        context.user_data["action"] = None
        from handlers.user_menu import show_referrals
        await show_referrals(update, context)
        return True
    elif text in ("👤 Profile", "👤 My Profile", "👤 MY PROFILE", "📊 MY PROFILE"):
        context.user_data["action"] = None
        from handlers.user_menu import show_profile
        await show_profile(update, context)
        return True
    elif text in ("🏆 Leaderboard", "🏆 LEADERBOARD"):
        context.user_data["action"] = None
        from handlers.user_menu import show_leaderboard
        await show_leaderboard(update, context)
        return True
    elif text in ("ℹ️ Help", "💬 Help", "💬 HELP & SUPPORT"):
        context.user_data["action"] = None
        from handlers.user_menu import show_help
        await show_help(update, context)
        return True

    # If state is waiting_phone or waiting_otp, process input
    if await handle_phone_input(update, context):
        return True
    if await handle_otp_input(update, context):
        return True
    return False

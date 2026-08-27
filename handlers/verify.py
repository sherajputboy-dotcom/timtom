#!/usr/bin/env python3
"""Channel verification handler — Lenskart Reward Bot"""

from telegram import Update
from telegram.ext import ContextTypes
from middleware.force_join import clear_user_membership_cache, is_user_channel_member
from utils.keyboard import main_menu_keyboard, main_reply_keyboard, force_join_keyboard
from config import CREDIT_FOOTER


async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ✅ Verify button — re-check all channel memberships cleanly."""
    query = update.callback_query
    user = update.effective_user
    db = context.bot_data["db"]

    # Purge cache for live check
    clear_user_membership_cache(user.id)

    channels = await db.get_channels()
    if not channels:
        await db.set_verified(user.id, True)
        await query.answer("🎉 Verification Successful!", show_alert=True)
        points = await db.get_user_points(user.id)
        await query.edit_message_text(
            f"✅ *Verification Complete!* 🎉\n\n"
            f"💰 *Your Balance:* `{points} Points`\n\n"
            f"Select an option below:\n\n{CREDIT_FOOTER}",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )
        return

    not_joined = []
    joined_ids = set()
    for ch in channels:
        joined = await is_user_channel_member(context.bot, ch["channel_id"], user.id)
        if joined:
            joined_ids.add(ch["channel_id"])
        else:
            not_joined.append(ch)

    if not_joined:
        await query.answer("❌ You haven't joined all channels yet!", show_alert=True)
        names = [ch.get("channel_title") or "Sponsor Channel" for ch in not_joined]
        text = (
            "⚠️ *VERIFICATION INCOMPLETE*\n\n"
            "You still need to join these channels:\n"
        )
        for name in names:
            text += f"  🔴 `{name}`\n"
        text += "\nClick the channel buttons above to join, then tap *✅ Verify Access* again."

        markup = force_join_keyboard(channels, joined_ids)
        try:
            await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass
    else:
        await db.set_verified(user.id, True)
        await query.answer("🎉 Verified! All channels joined!", show_alert=True)
        
        # Send reply keyboard
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text="📱 Persistent Menu Unlocked!",
                reply_markup=main_reply_keyboard()
            )
        except Exception:
            pass

        points = await db.get_user_points(user.id)
        await query.edit_message_text(
            f"🕶️ *LENSKART BOT DASHBOARD* 🕶️\n\n"
            f"🎉 *Welcome, {user.first_name or 'User'}!*\n"
            f"💰 *Points Balance:* `{points} Points`\n"
            f"🏃 *Claim Cost:* `20 Points`\n\n"
            f"Select an option from the menu below:\n\n{CREDIT_FOOTER}",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

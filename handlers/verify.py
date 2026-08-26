#!/usr/bin/env python3
"""Channel verification handler — MoneyZone Ultra Smooth Edition"""

from telegram import Update
from telegram.ext import ContextTypes
from middleware.force_join import clear_user_membership_cache, is_user_channel_member
from utils.keyboard import main_menu_keyboard, force_join_keyboard


async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ✅ Verify button — re-check all channel memberships smoothly."""
    query = update.callback_query
    user = update.effective_user
    db = context.bot_data["db"]

    # Purge cache for live check
    clear_user_membership_cache(user.id)

    channels = await db.get_channels()
    if not channels:
        await db.set_verified(user.id, True)
        await query.answer("🎉 Verification Successful!", show_alert=True)
        await query.edit_message_text(
            "⚡ 💸 *MONEYZONE ACCESS GRANTED* 💸 ⚡\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            "🎉 *Welcome to MoneyZone Official!*\n"
            "Choose an option from the premium dashboard below:",
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
        await query.answer("❌ You haven't joined all channels yet! Please join and retry.", show_alert=True)
        names = [ch.get("channel_title") or "Sponsor Channel" for ch in not_joined]
        text = (
            "⚡ 💸 *VERIFICATION INCOMPLETE* 💸 ⚡\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            "❌ *You are missing membership in:*\n"
        )
        for name in names:
            text += f"  🔴 `{name}`\n"
        text += (
            "\n📌 *Action Required:*\n"
            "1. Click the red buttons below to join remaining channels.\n"
            "2. Tap *⚡ ✅ VERIFY ACCESS NOW ⚡* again!"
        )

        markup = force_join_keyboard(channels, joined_ids)
        try:
            await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass
    else:
        await db.set_verified(user.id, True)
        await query.answer("🎉 Verified! All channels joined successfully!", show_alert=True)
        await query.edit_message_text(
            f"⚡ 💸 *MONEYZONE ACCESS UNLOCKED* 💸 ⚡\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
            f"👑 *Welcome back, {user.first_name or 'VIP User'}!* 🎉\n"
            "Your account is fully verified. Select an option from the menu below:",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

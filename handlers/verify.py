#!/usr/bin/env python3
"""Channel verification handler"""

from telegram import Update
from telegram.ext import ContextTypes
from utils.keyboard import main_menu_keyboard, force_join_keyboard


async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ✅ Verify button — re-check all channel memberships."""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    db = context.bot_data["db"]

    channels = await db.get_channels()
    if not channels:
        # No channels required
        await db.set_verified(user.id, True)
        await query.edit_message_text(
            "✅ *Verified!* Welcome! 🎉\n\nChoose an option:",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )
        return

    not_joined = []
    joined_ids = set()
    for ch in channels:
        try:
            member = await context.bot.get_chat_member(ch["channel_id"], user.id)
            if member.status in ["left", "kicked"]:
                not_joined.append(ch)
            else:
                joined_ids.add(ch["channel_id"])
        except Exception:
            not_joined.append(ch)

    if not_joined:
        # Still haven't joined all
        names = [ch.get("channel_title") or "Channel" for ch in not_joined]
        text = (
            "❌ *Verification Failed!*\n\n"
            "You haven't joined these channels yet:\n"
        )
        for name in names:
            text += f"  • {name}\n"
        text += "\nJoin them and click ✅ Verify again."

        markup = force_join_keyboard(channels, joined_ids)
        await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        # All joined!
        await db.set_verified(user.id, True)
        await query.edit_message_text(
            "✅ *Verified Successfully!* 🎉\n\n"
            "You now have full access. Choose an option:",
            reply_markup=main_menu_keyboard(),
            parse_mode="Markdown"
        )

#!/usr/bin/env python3
"""Force Channel Join Middleware"""

from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS


def require_join(func):
    """Decorator: blocks handler unless user has joined all required channels.
    Admins bypass. Banned users and maintenance mode are also checked."""

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return
        user_id = user.id

        # Admins always pass
        if user_id in ADMIN_IDS:
            return await func(update, context, *args, **kwargs)

        db = context.bot_data.get("db")
        if not db:
            return await func(update, context, *args, **kwargs)

        # Check ban
        if await db.is_banned(user_id):
            text = "🚫 You have been banned from using this bot."
            if update.callback_query:
                await update.callback_query.answer(text, show_alert=True)
            elif update.message:
                await update.message.reply_text(text)
            return

        # Check maintenance mode
        maintenance = await db.get_setting("maintenance_mode", "0")
        if maintenance == "1":
            text = "🔧 Bot is under maintenance. Please try again later."
            if update.callback_query:
                await update.callback_query.answer(text, show_alert=True)
            elif update.message:
                await update.message.reply_text(text)
            return

        # Check force join channels
        channels = await db.get_channels()
        if channels:
            not_joined = []
            joined_ids = set()
            for ch in channels:
                try:
                    member = await context.bot.get_chat_member(ch["channel_id"], user_id)
                    if member.status in ["left", "kicked"]:
                        not_joined.append(ch)
                    else:
                        joined_ids.add(ch["channel_id"])
                except Exception:
                    not_joined.append(ch)

            if not_joined:
                buttons = []
                for ch in channels:
                    ch_id = ch["channel_id"]
                    title = ch.get("channel_title") or "Channel"
                    link = ch.get("invite_link")
                    if not link and ch.get("channel_username"):
                        link = f"https://t.me/{ch['channel_username'].lstrip('@')}"
                    if not link:
                        continue
                    icon = "✅" if ch_id in joined_ids else "📢"
                    buttons.append([InlineKeyboardButton(f"{icon} {title}", url=link)])
                buttons.append([InlineKeyboardButton("✅ Verify", callback_data="verify_channels")])
                markup = InlineKeyboardMarkup(buttons)

                text = (
                    "⚠️ *You must join all channels to use this bot!*\n\n"
                    "Join the channels below, then click ✅ Verify:"
                )
                if update.callback_query:
                    await update.callback_query.edit_message_text(
                        text, reply_markup=markup, parse_mode="Markdown"
                    )
                elif update.message:
                    await update.message.reply_text(
                        text, reply_markup=markup, parse_mode="Markdown"
                    )
                return

        # Update last active
        await db.update_last_active(user_id)
        return await func(update, context, *args, **kwargs)

    return wrapper

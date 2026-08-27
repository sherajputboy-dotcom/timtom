#!/usr/bin/env python3
"""Force Channel Join Middleware with High-Speed Membership Caching"""

import time
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS, CHANNEL_CACHE_TTL
from utils.keyboard import force_join_keyboard

MEMBERSHIP_CACHE = {}


async def is_user_channel_member(bot, channel_id: int, user_id: int) -> bool:
    """Check if user is a member of channel, using TTL cache."""
    now = time.time()
    cache_key = (user_id, channel_id)

    if cache_key in MEMBERSHIP_CACHE:
        is_member, cached_at = MEMBERSHIP_CACHE[cache_key]
        if now - cached_at < CHANNEL_CACHE_TTL:
            return is_member

    try:
        member = await bot.get_chat_member(channel_id, user_id)
        is_member = member.status not in ["left", "kicked"]
        MEMBERSHIP_CACHE[cache_key] = (is_member, now)
        return is_member
    except Exception:
        MEMBERSHIP_CACHE[cache_key] = (False, now)
        return False


def clear_user_membership_cache(user_id: int):
    """Force purge cache for a user when they click Verify."""
    keys_to_del = [k for k in MEMBERSHIP_CACHE if k[0] == user_id]
    for k in keys_to_del:
        MEMBERSHIP_CACHE.pop(k, None)


def require_join(func):
    """Decorator: blocks handler unless user has joined all required channels."""

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
            text = "🚫 *Access Denied*\n\nYou are banned from using this bot."
            if update.callback_query:
                await update.callback_query.answer(text, show_alert=True)
            elif update.message:
                await update.message.reply_text(text, parse_mode="Markdown")
            return

        # Check maintenance mode
        maintenance = await db.get_setting("maintenance_mode", "0")
        if maintenance == "1":
            text = "🔧 *Maintenance Mode*\n\nThe bot is under maintenance. Please try again later!"
            if update.callback_query:
                await update.callback_query.answer(text, show_alert=True)
            elif update.message:
                await update.message.reply_text(text, parse_mode="Markdown")
            return

        # Check force join channels
        channels = await db.get_channels()
        if channels:
            not_joined = []
            joined_ids = set()

            for ch in channels:
                joined = await is_user_channel_member(context.bot, ch["channel_id"], user_id)
                if joined:
                    joined_ids.add(ch["channel_id"])
                else:
                    not_joined.append(ch)

            if not_joined:
                markup = force_join_keyboard(channels, joined_ids)
                text = (
                    "📢 *MANDATORY CHANNEL JOIN*\n\n"
                    "To access the *Lenskart Reward Bot*, you must join our required channels below.\n\n"
                    "👉 Click each channel button below to join, then tap *✅ Verify Access*!"
                )
                if update.callback_query:
                    try:
                        await update.callback_query.edit_message_text(
                            text, reply_markup=markup, parse_mode="Markdown"
                        )
                    except Exception:
                        pass
                elif update.message:
                    await update.message.reply_text(
                        text, reply_markup=markup, parse_mode="Markdown"
                    )
                return

        await db.update_last_active(user_id)
        return await func(update, context, *args, **kwargs)

    return wrapper

#!/usr/bin/env python3
"""Start handler — registration, referral tracking, force join check"""

from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS, REFERRAL_PREFIX, DEFAULT_WELCOME_MSG
from middleware.force_join import require_join
from utils.keyboard import main_menu_keyboard, force_join_keyboard


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with optional referral deep link."""
    user = update.effective_user
    db = context.bot_data["db"]

    # Parse referral code from deep link
    referrer_id = None
    if context.args:
        arg = context.args[0]
        if arg.startswith(REFERRAL_PREFIX):
            try:
                referrer_id = int(arg[len(REFERRAL_PREFIX):])
                # Don't let users refer themselves
                if referrer_id == user.id:
                    referrer_id = None
            except ValueError:
                referrer_id = None

    # Register user
    is_new = await db.add_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code or "en",
        referred_by=referrer_id
    )

    # Notify referrer if new user
    if is_new and referrer_id:
        try:
            ref_count = await db.get_referral_count(referrer_id)
            await context.bot.send_message(
                chat_id=referrer_id,
                text=(
                    f"🎉 *New Referral!*\n\n"
                    f"👤 {user.first_name or 'Someone'} joined using your link!\n"
                    f"📊 Total referrals: `{ref_count}`"
                ),
                parse_mode="Markdown"
            )
        except Exception:
            pass  # Referrer may have blocked the bot

    # Check force join channels
    channels = await db.get_channels()
    if channels:
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
            # Get custom welcome message or default
            welcome = await db.get_setting("welcome_msg") or DEFAULT_WELCOME_MSG
            bot_me = await context.bot.get_me()
            welcome = welcome.format(bot_name=bot_me.first_name)

            markup = force_join_keyboard(channels, joined_ids)
            await update.message.reply_text(welcome, reply_markup=markup, parse_mode="Markdown")
            return

    # All channels joined (or no channels set) — show main menu
    await db.set_verified(user.id, True)
    await _show_main_menu(update, context, is_new)


async def _show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_new: bool = False):
    """Display the main menu."""
    user = update.effective_user
    greeting = "🎉 Welcome" if is_new else "👋 Welcome back"
    name = user.first_name or "there"

    text = (
        f"{greeting}, *{name}*! 🚀\n\n"
        "Choose an option from the menu below:"
    )
    await update.message.reply_text(
        text, reply_markup=main_menu_keyboard(), parse_mode="Markdown"
    )

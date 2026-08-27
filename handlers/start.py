#!/usr/bin/env python3
"""Start handler — registration, referral tracking, points bonus, persistent reply keyboard"""

from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS, REFERRAL_PREFIX, DEFAULT_WELCOME_MSG, CREDIT_FOOTER, REFERRAL_BONUS_POINTS
from middleware.force_join import is_user_channel_member
from utils.keyboard import main_menu_keyboard, main_reply_keyboard, force_join_keyboard


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
                if referrer_id == user.id:
                    referrer_id = None
            except ValueError:
                referrer_id = None

    # Register user (gives 20 initial points, awards +50 points to referrer if new)
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
            ref_points = await db.get_user_points(referrer_id)
            await context.bot.send_message(
                chat_id=referrer_id,
                text=(
                    f"🎉 *New Referral Joined!*\n\n"
                    f"👤 *{user.first_name or 'Someone'}* registered using your referral link!\n"
                    f"💰 Bonus Awarded: *+{REFERRAL_BONUS_POINTS} Points*\n"
                    f"📊 Total Referrals: `{ref_count}`\n"
                    f"💳 Your New Balance: `{ref_points} Points`"
                ),
                parse_mode="Markdown"
            )
        except Exception:
            pass

    # Check force join channels
    channels = await db.get_channels()
    if channels:
        not_joined = []
        joined_ids = set()
        for ch in channels:
            joined = await is_user_channel_member(context.bot, ch["channel_id"], user.id)
            if joined:
                joined_ids.add(ch["channel_id"])
            else:
                not_joined.append(ch)

        if not_joined:
            welcome = await db.get_setting("welcome_msg") or DEFAULT_WELCOME_MSG
            bot_me = await context.bot.get_me()
            welcome = welcome.format(bot_name=bot_me.first_name)

            markup = force_join_keyboard(channels, joined_ids)
            await update.message.reply_text(welcome, reply_markup=markup, parse_mode="Markdown")
            return

    # All channels joined
    await db.set_verified(user.id, True)
    await _show_main_menu(update, context, is_new)


async def _show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_new: bool = False):
    """Display the Lenskart Bot main menu with reply & inline keyboards."""
    user = update.effective_user
    db = context.bot_data["db"]

    greeting = "🎉 Welcome to Lenskart Reward Bot" if is_new else "👋 Welcome back"
    name = user.first_name or "User"
    points = await db.get_user_points(user.id)

    # First send reply keyboard (bottom menu)
    await update.message.reply_text(
        f"📱 Main Menu Activated!",
        reply_markup=main_reply_keyboard()
    )

    # Send clean inline dashboard card
    text = (
        f"{greeting}, *{name}*! 🕶️\n\n"
        f"💰 *Your Points Balance:* `{points} Points`\n"
        f"🏃 *Cost Per Claim:* `20 Points`\n\n"
        f"Choose an option below to bypass 30,000 steps and claim your Lenskart voucher!\n\n"
        f"{CREDIT_FOOTER}"
    )
    await update.message.reply_text(
        text, reply_markup=main_menu_keyboard(), parse_mode="Markdown"
    )

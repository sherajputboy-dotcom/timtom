#!/usr/bin/env python3
"""Start handler — registration, referral tracking, points bonus, persistent reply keyboard (State Safe & Multi-Update Compatible)"""

from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS, REFERRAL_PREFIX, DEFAULT_WELCOME_MSG, CREDIT_FOOTER, REFERRAL_BONUS_POINTS
from middleware.force_join import is_user_channel_member
from utils.keyboard import main_reply_keyboard, force_join_keyboard
from utils.helpers import escape_md


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with optional referral deep link."""
    user = update.effective_user
    if not user:
        return

    db = context.bot_data["db"]

    # Reset any active action state
    context.user_data["action"] = None
    context.user_data["admin_action"] = None
    context.user_data["pending_phone"] = None

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
            safe_name = escape_md(user.first_name or "Someone")
            await context.bot.send_message(
                chat_id=referrer_id,
                text=(
                    f"🎉 *New Referral Joined!*\n\n"
                    f"👤 *{safe_name}* registered using your referral link!\n"
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
            if "{bot_name}" in welcome:
                welcome = welcome.replace("{bot_name}", escape_md(bot_me.first_name))

            markup = force_join_keyboard(channels, joined_ids)
            await _reply_or_send(update, welcome, reply_markup=markup)
            return

    # All channels joined
    await db.set_verified(user.id, True)
    await _show_main_menu(update, context, is_new)


async def _reply_or_send(update: Update, text: str, reply_markup=None):
    """Safely reply or send message regardless of update type."""
    try:
        if update.message:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
        elif update.callback_query and update.callback_query.message:
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    except Exception:
        clean = text.replace("*", "").replace("`", "").replace("_", "").replace("[", "").replace("]", "")
        try:
            if update.message:
                await update.message.reply_text(clean, reply_markup=reply_markup, parse_mode=None)
            elif update.callback_query and update.callback_query.message:
                await update.callback_query.message.reply_text(clean, reply_markup=reply_markup, parse_mode=None)
        except Exception:
            pass


async def _show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, is_new: bool = False):
    """Display the Lenskart Bot main menu with reply keyboard."""
    user = update.effective_user
    db = context.bot_data["db"]

    greeting = "🎉 Welcome to Lenskart Reward Bot" if is_new else "👋 Welcome back"
    safe_name = escape_md(user.first_name or "User")
    points = await db.get_user_points(user.id)

    text = (
        f"{greeting}, *{safe_name}*! 🕶️\n\n"
        f"💳 *Points Balance:* `{points} Points`\n"
        f"🏃 *Cost Per Claim:* `20 Points`\n\n"
        f"Use the bottom menu buttons to navigate!\n\n"
        f"{CREDIT_FOOTER}"
    )
    await _reply_or_send(update, text, reply_markup=main_reply_keyboard())

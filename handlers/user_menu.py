#!/usr/bin/env python3
"""User menu handlers — Profile, Referrals, Vouchers, Leaderboard, Help (Lenskart Bot)"""

from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS, DEFAULT_HELP_MSG, CREDIT_FOOTER, REFERRAL_BONUS_POINTS, CLAIM_COST_POINTS
from middleware.force_join import require_join
from utils.keyboard import main_menu_keyboard, back_button
from utils.helpers import format_number, format_datetime, mention_user


@require_join
async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route main menu callbacks."""
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "main_menu":
        await show_main_menu_edit(update, context)
    elif data == "user_profile":
        await show_profile(update, context)
    elif data == "user_referrals":
        await show_referrals(update, context)
    elif data == "user_vouchers":
        await show_vouchers(update, context)
    elif data == "user_leaderboard":
        await show_leaderboard(update, context)
    elif data == "user_help":
        await show_help(update, context)


async def show_main_menu_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show main menu via edit_message."""
    query = update.callback_query
    user = update.effective_user
    db = context.bot_data["db"]
    points = await db.get_user_points(user.id)

    text = (
        f"🕶️ *LENSKART BOT DASHBOARD* 🕶️\n\n"
        f"👑 *Welcome back, {user.first_name or 'User'}!*\n"
        f"💰 *Points Balance:* `{points} Points`\n"
        f"🏃 *Claim Cost:* `{CLAIM_COST_POINTS} Points`\n\n"
        f"Select an option below:\n\n{CREDIT_FOOTER}"
    )
    await query.edit_message_text(
        text, reply_markup=main_menu_keyboard(), parse_mode="Markdown"
    )


async def _reply_or_edit(update: Update, text: str, reply_markup=None):
    """Helper to send message via edit_message (callback) or reply_text (message)."""
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="Markdown")
    elif update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="Markdown")


@require_join
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's profile and points balance."""
    db = context.bot_data["db"]
    user = update.effective_user
    data = await db.get_user(user.id)

    if not data:
        await _reply_or_edit(update, "❌ Profile record not found!")
        return

    vouchers = await db.get_user_vouchers(user.id)
    points = await db.get_user_points(user.id)
    bot_username = (await context.bot.get_me()).username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user.id}"

    text = (
        f"👤 *YOUR PROFILE*\n\n"
        f"🆔 *User ID:* `{user.id}`\n"
        f"👤 *Name:* `{data.get('first_name', 'User')}`\n"
        f"📛 *Username:* @{data.get('username') or 'N/A'}\n"
        f"💳 *Points Balance:* `{points} Points`\n"
        f"👥 *Total Referrals:* `{format_number(data.get('referral_count', 0))}`\n"
        f"🎁 *Vouchers Claimed:* `{len(vouchers)}`\n"
        f"📅 *Joined Date:* `{format_datetime(data.get('joined_at'))}`\n\n"
        f"🔗 *Referral Link:*\n`{ref_link}`\n\n"
        f"{CREDIT_FOOTER}"
    )
    await _reply_or_edit(update, text, reply_markup=back_button("main_menu"))


@require_join
async def show_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show referral info, points, and referral link."""
    db = context.bot_data["db"]
    user = update.effective_user

    count = await db.get_referral_count(user.id)
    points = await db.get_user_points(user.id)
    referrals = await db.get_referrals(user.id, limit=10)
    bot_me = await context.bot.get_me()
    ref_link = f"https://t.me/{bot_me.username}?start=ref_{user.id}"

    text = (
        f"👥 *REFER & EARN POINTS*\n\n"
        f"Share your referral link with friends!\n"
        f"Earn *+{REFERRAL_BONUS_POINTS} Points* for every friend who joins!\n\n"
        f"💰 *Current Balance:* `{points} Points`\n"
        f"📊 *Total Referrals:* `{format_number(count)} Users`\n\n"
        f"🔗 *YOUR EXCLUSIVE REFERRAL LINK:*\n`{ref_link}`\n"
    )

    if referrals:
        text += "\n👥 *Recent Referrals:*\n"
        for i, ref in enumerate(referrals, 1):
            name = ref.get('first_name') or 'User'
            text += f"  {i}. {mention_user(ref['user_id'], name)} — `{format_datetime(ref.get('joined_at'))}`\n"
    else:
        text += "\n💡 *No referrals yet.* Share your link to get free Points!"

    text += f"\n\n{CREDIT_FOOTER}"
    await _reply_or_edit(update, text, reply_markup=back_button("main_menu"))


@require_join
async def show_vouchers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's claimed vouchers."""
    db = context.bot_data["db"]
    user = update.effective_user

    vouchers = await db.get_user_vouchers(user.id)

    if not vouchers:
        text = (
            f"🎁 *MY VOUCHERS*\n\n"
            f"You haven't claimed any vouchers yet!\n"
            f"Tap *🏃 Claim Reward* on the main menu to bypass 30k steps and claim your voucher.\n\n"
            f"{CREDIT_FOOTER}"
        )
    else:
        text = f"🎁 *MY VOUCHERS* ({len(vouchers)})\n\n"
        for i, v in enumerate(vouchers, 1):
            text += f"🎫 *Voucher #{i}:* `{v.get('voucher_code', 'N/A')}`\n"
            text += f"   📱 Phone: `{v.get('phone', 'N/A')}`\n"
            if v.get('tier'):
                text += f"   🏆 Tier: `{v['tier']}`\n"
            text += f"   📅 Claimed: `{format_datetime(v.get('claimed_at'))}`\n\n"
        text += f"{CREDIT_FOOTER}"

    await _reply_or_edit(update, text, reply_markup=back_button("main_menu"))


@require_join
async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top referrers leaderboard."""
    db = context.bot_data["db"]

    top = await db.get_top_referrers(limit=10)
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7

    if not top:
        text = f"🏆 *TOP REFERRERS LEADERBOARD*\n\nNo referrals recorded yet. Be the first!\n\n{CREDIT_FOOTER}"
    else:
        text = "🏆 *TOP REFERRERS LEADERBOARD*\n\n"
        for i, user_data in enumerate(top):
            medal = medals[i] if i < len(medals) else "🏅"
            name = user_data.get('first_name') or 'User'
            count = user_data.get('referral_count', 0)
            pts = user_data.get('points', 0)
            text += f"{medal} {mention_user(user_data['user_id'], name)} — `{format_number(count)}` refs (`{pts} Pts`)\n"
        text += f"\n{CREDIT_FOOTER}"

    await _reply_or_edit(update, text, reply_markup=back_button("main_menu"))


@require_join
async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message."""
    db = context.bot_data["db"]
    help_text = await db.get_setting("help_msg") or DEFAULT_HELP_MSG
    await _reply_or_edit(update, help_text, reply_markup=back_button("main_menu"))

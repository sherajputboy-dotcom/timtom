#!/usr/bin/env python3
"""User menu handlers — profile, referrals, vouchers, leaderboard, help"""

from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS, DEFAULT_HELP_MSG
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
    text = f"👋 *Welcome back, {user.first_name or 'there'}!* 🚀\n\nChoose an option:"
    await query.edit_message_text(
        text, reply_markup=main_menu_keyboard(), parse_mode="Markdown"
    )


async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's profile."""
    query = update.callback_query
    db = context.bot_data["db"]
    user = update.effective_user
    data = await db.get_user(user.id)

    if not data:
        await query.edit_message_text("❌ Profile not found!")
        return

    vouchers = await db.get_user_vouchers(user.id)
    ref_link = f"https://t.me/{(await context.bot.get_me()).username}?start=ref_{user.id}"

    text = (
        "👤 *Your Profile*\n\n"
        f"🆔 ID: `{user.id}`\n"
        f"👤 Name: `{data.get('first_name', 'N/A')} {data.get('last_name') or ''}`\n"
        f"📛 Username: @{data.get('username') or 'N/A'}\n"
        f"📅 Joined: `{format_datetime(data.get('joined_at'))}`\n"
        f"🟢 Last Active: `{format_datetime(data.get('last_active'))}`\n\n"
        f"👥 Referrals: `{format_number(data.get('referral_count', 0))}`\n"
        f"🎫 Vouchers: `{len(vouchers)}`\n\n"
        f"🔗 Your Referral Link:\n`{ref_link}`"
    )
    await query.edit_message_text(
        text, reply_markup=back_button("main_menu"), parse_mode="Markdown"
    )


async def show_referrals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show referral info and link."""
    query = update.callback_query
    db = context.bot_data["db"]
    user = update.effective_user

    count = await db.get_referral_count(user.id)
    referrals = await db.get_referrals(user.id, limit=10)
    bot_me = await context.bot.get_me()
    ref_link = f"https://t.me/{bot_me.username}?start=ref_{user.id}"

    text = (
        "👥 *Refer & Earn*\n\n"
        "Share your referral link with friends!\n"
        "When they join, you get credit! 🎉\n\n"
        f"🔗 *Your Link:*\n`{ref_link}`\n\n"
        f"📊 *Total Referrals:* `{format_number(count)}`\n"
    )

    if referrals:
        text += "\n👥 *Recent Referrals:*\n"
        for i, ref in enumerate(referrals, 1):
            name = ref.get('first_name') or 'User'
            text += f"  {i}. {mention_user(ref['user_id'], name)} — `{format_datetime(ref.get('joined_at'))}`\n"
    else:
        text += "\n😔 No referrals yet. Share your link!"

    await query.edit_message_text(
        text, reply_markup=back_button("main_menu"), parse_mode="Markdown"
    )


async def show_vouchers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's claimed vouchers."""
    query = update.callback_query
    db = context.bot_data["db"]
    user = update.effective_user

    vouchers = await db.get_user_vouchers(user.id)

    if not vouchers:
        text = (
            "🎫 *My Vouchers*\n\n"
            "😔 You don't have any vouchers yet.\n"
            "Use 🏃 Claim Reward to get one!"
        )
    else:
        text = f"🎫 *My Vouchers* ({len(vouchers)})\n\n"
        for i, v in enumerate(vouchers, 1):
            text += f"{i}. 🎫 `{v.get('voucher_code', 'N/A')}`\n"
            text += f"   📱 Phone: `{v.get('phone', 'N/A')}`\n"
            if v.get('tier'):
                text += f"   🏆 Tier: `{v['tier']}`\n"
            text += f"   📅 Claimed: `{format_datetime(v.get('claimed_at'))}`\n\n"

    await query.edit_message_text(
        text, reply_markup=back_button("main_menu"), parse_mode="Markdown"
    )


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show top referrers leaderboard."""
    query = update.callback_query
    db = context.bot_data["db"]

    top = await db.get_top_referrers(limit=10)
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7

    if not top:
        text = "🏆 *Leaderboard*\n\n😔 No referrals yet. Be the first!"
    else:
        text = "🏆 *Top Referrers*\n\n"
        for i, user_data in enumerate(top):
            medal = medals[i] if i < len(medals) else "🏅"
            name = user_data.get('first_name') or 'User'
            count = user_data.get('referral_count', 0)
            text += f"{medal} {mention_user(user_data['user_id'], name)} — `{format_number(count)}` referrals\n"

    await query.edit_message_text(
        text, reply_markup=back_button("main_menu"), parse_mode="Markdown"
    )


async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help message."""
    query = update.callback_query
    db = context.bot_data["db"]
    help_text = await db.get_setting("help_msg") or DEFAULT_HELP_MSG
    await query.edit_message_text(
        help_text, reply_markup=back_button("main_menu"), parse_mode="Markdown"
    )

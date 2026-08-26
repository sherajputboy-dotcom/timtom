#!/usr/bin/env python3
"""Admin panel — full dashboard with stats, users, channels, broadcast, campaign, settings"""

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS, ITEMS_PER_PAGE, BROADCAST_DELAY, DEFAULT_STEPS
from utils.keyboard import (
    admin_menu_keyboard, back_button, pagination_keyboard,
    user_action_keyboard, channel_list_keyboard, confirm_keyboard
)
from utils.helpers import (
    format_number, format_datetime, mention_user, bar_chart, progress_bar
)


def admin_only(func):
    """Decorator: restrict to admin users."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            if update.callback_query:
                await update.callback_query.answer("❌ Unauthorized!", show_alert=True)
            elif update.message:
                await update.message.reply_text("❌ Unauthorized!")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


# ===================== ADMIN MAIN =====================

@admin_only
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command."""
    text = "🛡️ *Admin Panel*\n\nSelect an option:"
    if update.message:
        await update.message.reply_text(
            text, reply_markup=admin_menu_keyboard(), parse_mode="Markdown"
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            text, reply_markup=admin_menu_keyboard(), parse_mode="Markdown"
        )


@admin_only
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all admin callbacks."""
    query = update.callback_query
    await query.answer()
    data = query.data
    db = context.bot_data["db"]

    # ---- Main ----
    if data == "admin_main":
        await admin_command(update, context)

    elif data == "admin_close":
        await query.edit_message_text("✅ Admin panel closed.")

    # ---- Statistics ----
    elif data == "admin_stats":
        await _show_stats(query, db)

    elif data == "admin_stats_growth":
        await _show_growth(query, db)

    elif data == "admin_stats_referrers":
        await _show_top_referrers(query, db)

    # ---- User Management ----
    elif data == "admin_users":
        await _show_users_menu(query)

    elif data.startswith("admin_users_list_"):
        page = int(data.split("_")[-1])
        await _show_users_list(query, db, page)

    elif data == "admin_users_search":
        context.user_data["admin_action"] = "search_user"
        await query.edit_message_text(
            "🔍 *Search User*\n\nSend user ID or username:",
            reply_markup=back_button("admin_users"),
            parse_mode="Markdown"
        )

    elif data.startswith("admin_view_"):
        target_id = int(data.split("_")[-1])
        await _show_user_detail(query, db, target_id)

    elif data.startswith("admin_ban_"):
        target_id = int(data.split("_")[-1])
        await db.ban_user(target_id)
        await query.answer(f"🚫 User {target_id} banned!", show_alert=True)
        await _show_user_detail(query, db, target_id)

    elif data.startswith("admin_unban_"):
        target_id = int(data.split("_")[-1])
        await db.unban_user(target_id)
        await query.answer(f"✅ User {target_id} unbanned!", show_alert=True)
        await _show_user_detail(query, db, target_id)

    elif data.startswith("admin_user_refs_"):
        target_id = int(data.split("_")[-1])
        await _show_user_referrals(query, db, target_id)

    elif data.startswith("admin_user_vouchers_"):
        target_id = int(data.split("_")[-1])
        await _show_user_vouchers(query, db, target_id)

    elif data == "admin_users_banned":
        await _show_banned_users(query, db)

    # ---- Channel Management ----
    elif data == "admin_channels":
        await _show_channels_menu(query, db)

    elif data == "admin_ch_add":
        context.user_data["admin_action"] = "add_channel"
        await query.edit_message_text(
            "➕ *Add Force-Join Channel*\n\n"
            "Send the channel username (e.g. `@mychannel`)\n"
            "or channel ID (e.g. `-1001234567890`):\n\n"
            "⚠️ Bot must be admin in the channel!",
            reply_markup=back_button("admin_channels"),
            parse_mode="Markdown"
        )

    elif data == "admin_ch_list":
        await _show_channel_list(query, db)

    elif data.startswith("admin_ch_del_"):
        ch_id = int(data.split("_")[-1])
        await db.remove_channel(ch_id)
        await query.answer("✅ Channel removed!", show_alert=True)
        await _show_channel_list(query, db)

    # ---- Broadcast ----
    elif data == "admin_broadcast":
        await _show_broadcast_menu(query)

    elif data == "admin_bc_send":
        context.user_data["admin_action"] = "broadcast"
        await query.edit_message_text(
            "📣 *Broadcast Message*\n\n"
            "Send the message you want to broadcast to all users:\n\n"
            "⚠️ This will send to ALL non-banned users.",
            reply_markup=back_button("admin_broadcast"),
            parse_mode="Markdown"
        )

    elif data == "admin_bc_history":
        await _show_broadcast_history(query, db)

    # ---- Campaign ----
    elif data == "admin_campaign":
        await _show_campaign_menu(query, db)

    elif data == "admin_camp_toggle":
        current = await db.get_setting("claims_enabled", "1")
        new_val = "0" if current == "1" else "1"
        await db.set_setting("claims_enabled", new_val)
        status = "✅ Enabled" if new_val == "1" else "❌ Disabled"
        await query.answer(f"Claims: {status}", show_alert=True)
        await _show_campaign_menu(query, db)

    elif data == "admin_camp_steps":
        context.user_data["admin_action"] = "set_steps"
        await query.edit_message_text(
            "💪 *Set Step Count*\n\n"
            f"Current: `{await db.get_setting('claim_steps', str(DEFAULT_STEPS))}`\n\n"
            "Send new step count (e.g. `30000`):",
            reply_markup=back_button("admin_campaign"),
            parse_mode="Markdown"
        )

    elif data == "admin_camp_logs":
        await _show_claim_logs(query, db)

    # ---- Settings ----
    elif data == "admin_settings":
        await _show_settings_menu(query, db)

    elif data == "admin_set_welcome":
        context.user_data["admin_action"] = "set_welcome"
        await query.edit_message_text(
            "📝 *Set Welcome Message*\n\n"
            "Send the new welcome message.\n"
            "You can use `{bot_name}` as placeholder.\n\n"
            "Supports Markdown formatting.",
            reply_markup=back_button("admin_settings"),
            parse_mode="Markdown"
        )

    elif data == "admin_set_help":
        context.user_data["admin_action"] = "set_help"
        await query.edit_message_text(
            "ℹ️ *Set Help Message*\n\n"
            "Send the new help message.\n"
            "Supports Markdown formatting.",
            reply_markup=back_button("admin_settings"),
            parse_mode="Markdown"
        )

    elif data == "admin_set_referral":
        current = await db.get_setting("referral_enabled", "1")
        new_val = "0" if current == "1" else "1"
        await db.set_setting("referral_enabled", new_val)
        status = "✅ Enabled" if new_val == "1" else "❌ Disabled"
        await query.answer(f"Referral System: {status}", show_alert=True)
        await _show_settings_menu(query, db)

    elif data == "admin_set_maintenance":
        current = await db.get_setting("maintenance_mode", "0")
        new_val = "0" if current == "1" else "1"
        await db.set_setting("maintenance_mode", new_val)
        status = "🔧 ON" if new_val == "1" else "✅ OFF"
        await query.answer(f"Maintenance Mode: {status}", show_alert=True)
        await _show_settings_menu(query, db)


# ===================== ADMIN TEXT INPUT HANDLER =====================

@admin_only
async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin text inputs (search, add channel, broadcast, etc)."""
    action = context.user_data.get("admin_action")
    if not action:
        return False

    db = context.bot_data["db"]
    text = update.message.text.strip()
    context.user_data["admin_action"] = None

    if action == "search_user":
        user_data = await db.search_user(text)
        if user_data:
            await _send_user_detail(update.message, db, user_data)
        else:
            await update.message.reply_text(
                f"❌ No user found for: `{text}`",
                reply_markup=back_button("admin_users"),
                parse_mode="Markdown"
            )
        return True

    elif action == "add_channel":
        await _handle_add_channel(update, context, db, text)
        return True

    elif action == "broadcast":
        await _handle_broadcast(update, context, db, text)
        return True

    elif action == "set_steps":
        if text.isdigit() and int(text) > 0:
            await db.set_setting("claim_steps", text)
            await update.message.reply_text(
                f"✅ Step count set to `{text}`",
                reply_markup=back_button("admin_campaign"),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Invalid number! Must be a positive integer.")
        return True

    elif action == "set_welcome":
        await db.set_setting("welcome_msg", text)
        await update.message.reply_text(
            "✅ Welcome message updated!",
            reply_markup=back_button("admin_settings")
        )
        return True

    elif action == "set_help":
        await db.set_setting("help_msg", text)
        await update.message.reply_text(
            "✅ Help message updated!",
            reply_markup=back_button("admin_settings")
        )
        return True

    return False


# ===================== STATISTICS =====================

async def _show_stats(query, db):
    """Statistics dashboard."""
    total = await db.get_total_users()
    today = await db.get_today_users()
    active = await db.get_active_today()
    banned = await db.get_banned_count()
    referrals = await db.get_total_referrals()
    vouchers = await db.get_total_vouchers()
    channels = await db.get_channel_count()

    text = (
        "📊 *Statistics Dashboard*\n\n"
        f"👥 Total Users: `{format_number(total)}`\n"
        f"🆕 New Today: `{format_number(today)}`\n"
        f"🟢 Active Today: `{format_number(active)}`\n"
        f"🚫 Banned: `{format_number(banned)}`\n\n"
        f"👥 Total Referrals: `{format_number(referrals)}`\n"
        f"🎫 Vouchers Claimed: `{format_number(vouchers)}`\n"
        f"📢 Force-Join Channels: `{channels}`\n"
    )
    if total > 0:
        text += f"\n📈 Voucher Rate: `{vouchers / total * 100:.1f}%`"

    keyboard = [
        [InlineKeyboardButton("📈 Growth Chart", callback_data="admin_stats_growth")],
        [InlineKeyboardButton("🏆 Top Referrers", callback_data="admin_stats_referrers")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_main")]
    ]
    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def _show_growth(query, db):
    """7-day growth chart."""
    data = await db.get_daily_signups(7)
    if data:
        chart_data = [(row["date"][-5:], row["count"]) for row in data]
        chart = bar_chart(chart_data)
    else:
        chart = "No signups in the last 7 days."

    text = f"📈 *7-Day User Growth*\n\n{chart}"
    await query.edit_message_text(
        text, reply_markup=back_button("admin_stats"), parse_mode="Markdown"
    )


async def _show_top_referrers(query, db):
    """Top referrers list."""
    top = await db.get_top_referrers(10)
    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7

    if not top:
        text = "🏆 *Top Referrers*\n\nNo referrals yet."
    else:
        text = "🏆 *Top Referrers*\n\n"
        for i, u in enumerate(top):
            medal = medals[i] if i < len(medals) else ""
            name = u.get("first_name") or str(u["user_id"])
            text += f"{medal} {mention_user(u['user_id'], name)} — `{format_number(u['referral_count'])}` referrals\n"

    await query.edit_message_text(
        text, reply_markup=back_button("admin_stats"), parse_mode="Markdown"
    )


# ===================== USER MANAGEMENT =====================

async def _show_users_menu(query):
    """User management sub-menu."""
    keyboard = [
        [InlineKeyboardButton("🔍 Search User", callback_data="admin_users_search")],
        [InlineKeyboardButton("📋 User List", callback_data="admin_users_list_1")],
        [InlineKeyboardButton("🚫 Banned Users", callback_data="admin_users_banned")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_main")]
    ]
    await query.edit_message_text(
        "👥 *User Management*\n\nSelect an option:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def _show_users_list(query, db, page: int):
    """Paginated user list."""
    users = await db.get_users_paginated(page, ITEMS_PER_PAGE)
    total = await db.get_total_users()
    total_pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)

    if not users:
        text = "👥 *User List*\n\nNo users found."
    else:
        text = f"👥 *User List* (Page {page}/{total_pages})\n\n"
        for u in users:
            name = u.get("first_name") or "Unknown"
            username = f"@{u['username']}" if u.get("username") else "N/A"
            banned = "🚫" if u.get("is_banned") else ""
            text += f"• {mention_user(u['user_id'], name)} | `{username}` {banned}\n"

    nav = []
    if page > 1:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"admin_users_list_{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page}/{total_pages}", callback_data="noop"))
    if page < total_pages:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"admin_users_list_{page + 1}"))
    keyboard = [nav, [InlineKeyboardButton("🔙 Back", callback_data="admin_users")]]

    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


async def _show_user_detail(query, db, user_id: int):
    """Show detailed user profile."""
    user_data = await db.get_user(user_id)
    if not user_data:
        await query.edit_message_text(
            "❌ User not found!", reply_markup=back_button("admin_users")
        )
        return
    await _render_user_detail(query, db, user_data)


async def _send_user_detail(message, db, user_data: dict):
    """Send user detail as new message (for search results)."""
    user_id = user_data["user_id"]
    vouchers = await db.get_user_vouchers(user_id)
    referrals = await db.get_referral_count(user_id)
    referred_by = user_data.get("referred_by")

    text = _format_user_detail(user_data, len(vouchers), referrals, referred_by)
    is_banned = bool(user_data.get("is_banned"))
    await message.reply_text(
        text, reply_markup=user_action_keyboard(user_id, is_banned), parse_mode="Markdown"
    )


async def _render_user_detail(query, db, user_data: dict):
    """Render user detail via edit_message."""
    user_id = user_data["user_id"]
    vouchers = await db.get_user_vouchers(user_id)
    referrals = await db.get_referral_count(user_id)
    referred_by = user_data.get("referred_by")

    text = _format_user_detail(user_data, len(vouchers), referrals, referred_by)
    is_banned = bool(user_data.get("is_banned"))
    await query.edit_message_text(
        text, reply_markup=user_action_keyboard(user_id, is_banned), parse_mode="Markdown"
    )


def _format_user_detail(data: dict, voucher_count: int, referral_count: int, referred_by) -> str:
    """Format user detail text."""
    name = f"{data.get('first_name', '')} {data.get('last_name') or ''}".strip() or "Unknown"
    username = f"@{data['username']}" if data.get("username") else "N/A"
    status = "🚫 Banned" if data.get("is_banned") else "✅ Active"
    verified = "✅ Yes" if data.get("is_verified") else "❌ No"

    text = (
        f"👤 *User Detail*\n\n"
        f"🆔 ID: `{data['user_id']}`\n"
        f"👤 Name: `{name}`\n"
        f"📛 Username: {username}\n"
        f"🛡️ Status: {status}\n"
        f"✅ Verified: {verified}\n"
        f"📅 Joined: `{format_datetime(data.get('joined_at'))}`\n"
        f"🟢 Last Active: `{format_datetime(data.get('last_active'))}`\n\n"
        f"👥 Referrals: `{format_number(referral_count)}`\n"
        f"🎫 Vouchers: `{voucher_count}`\n"
    )
    if referred_by:
        text += f"🔗 Referred By: `{referred_by}`\n"
    return text


async def _show_user_referrals(query, db, user_id: int):
    """Show a user's referrals (admin view)."""
    refs = await db.get_referrals(user_id, limit=20)
    if not refs:
        text = f"👥 *Referrals for* `{user_id}`\n\nNo referrals."
    else:
        text = f"👥 *Referrals for* `{user_id}` ({len(refs)})\n\n"
        for i, r in enumerate(refs, 1):
            name = r.get("first_name") or "User"
            text += f"{i}. {mention_user(r['user_id'], name)} — `{format_datetime(r.get('joined_at'))}`\n"

    await query.edit_message_text(
        text, reply_markup=back_button(f"admin_view_{user_id}"), parse_mode="Markdown"
    )


async def _show_user_vouchers(query, db, user_id: int):
    """Show a user's vouchers (admin view)."""
    vouchers = await db.get_user_vouchers(user_id)
    if not vouchers:
        text = f"🎫 *Vouchers for* `{user_id}`\n\nNo vouchers."
    else:
        text = f"🎫 *Vouchers for* `{user_id}` ({len(vouchers)})\n\n"
        for i, v in enumerate(vouchers, 1):
            text += f"{i}. `{v.get('voucher_code', 'N/A')}` — {v.get('phone', 'N/A')}\n"

    await query.edit_message_text(
        text, reply_markup=back_button(f"admin_view_{user_id}"), parse_mode="Markdown"
    )


async def _show_banned_users(query, db):
    """Show list of banned users."""
    banned = await db._fetch_all(
        "SELECT user_id, username, first_name FROM users WHERE is_banned = 1 ORDER BY joined_at DESC LIMIT 20"
    )
    if not banned:
        await query.edit_message_text(
            "🚫 *Banned Users*\n\nNo banned users.",
            reply_markup=back_button("admin_users"),
            parse_mode="Markdown"
        )
        return

    text = f"🚫 *Banned Users* ({len(banned)})\n\n"
    keyboard = []
    for u in banned:
        name = u.get("first_name") or "Unknown"
        text += f"• {mention_user(u['user_id'], name)}\n"
        keyboard.append([
            InlineKeyboardButton(f"👤 {name}", callback_data=f"admin_view_{u['user_id']}"),
            InlineKeyboardButton("✅ Unban", callback_data=f"admin_unban_{u['user_id']}")
        ])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_users")])

    await query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


# ===================== CHANNEL MANAGEMENT =====================

async def _show_channels_menu(query, db):
    """Channel management sub-menu."""
    count = await db.get_channel_count()
    keyboard = [
        [InlineKeyboardButton("➕ Add Channel", callback_data="admin_ch_add")],
        [InlineKeyboardButton(f"📋 List Channels ({count})", callback_data="admin_ch_list")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_main")]
    ]
    await query.edit_message_text(
        f"📢 *Channel Management*\n\nActive channels: `{count}`",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def _show_channel_list(query, db):
    """List all force-join channels with remove buttons."""
    channels = await db.get_channels()
    if not channels:
        await query.edit_message_text(
            "📢 *Channels*\n\nNo channels added yet.",
            reply_markup=back_button("admin_channels"),
            parse_mode="Markdown"
        )
        return

    await query.edit_message_text(
        f"📢 *Force-Join Channels* ({len(channels)})\n\nClick ❌ to remove:",
        reply_markup=channel_list_keyboard(channels),
        parse_mode="Markdown"
    )


async def _handle_add_channel(update: Update, context, db, text: str):
    """Process add channel input."""
    bot = context.bot
    try:
        if text.startswith("@"):
            chat = await bot.get_chat(text)
        elif text.lstrip("-").isdigit():
            chat = await bot.get_chat(int(text))
        else:
            chat = await bot.get_chat(f"@{text}")

        invite_link = None
        try:
            invite_link = chat.invite_link or (await bot.export_chat_invite_link(chat.id))
        except Exception:
            if chat.username:
                invite_link = f"https://t.me/{chat.username}"

        success = await db.add_channel(
            channel_id=chat.id,
            username=chat.username,
            title=chat.title,
            invite_link=invite_link,
            added_by=update.effective_user.id
        )

        if success:
            await update.message.reply_text(
                f"✅ Channel added!\n\n"
                f"📢 Title: `{chat.title}`\n"
                f"🆔 ID: `{chat.id}`\n"
                f"🔗 Link: {invite_link or 'N/A'}",
                reply_markup=back_button("admin_channels"),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ Channel already exists!",
                reply_markup=back_button("admin_channels")
            )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Failed to add channel!\n\nError: `{str(e)}`\n\n"
            "Make sure:\n"
            "1. Channel username/ID is correct\n"
            "2. Bot is admin in the channel",
            reply_markup=back_button("admin_channels"),
            parse_mode="Markdown"
        )


# ===================== BROADCAST =====================

async def _show_broadcast_menu(query):
    """Broadcast sub-menu."""
    keyboard = [
        [InlineKeyboardButton("📝 Send to All", callback_data="admin_bc_send")],
        [InlineKeyboardButton("📊 Broadcast History", callback_data="admin_bc_history")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_main")]
    ]
    await query.edit_message_text(
        "📣 *Broadcast*\n\nSend messages to all bot users.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def _handle_broadcast(update: Update, context, db, text: str):
    """Execute broadcast to all users."""
    user_ids = await db.get_all_user_ids()
    total = len(user_ids)

    if total == 0:
        await update.message.reply_text("❌ No users to broadcast to!")
        return

    broadcast_id = await db.add_broadcast(
        admin_id=update.effective_user.id,
        message_text=text,
        total_users=total
    )

    status_msg = await update.message.reply_text(
        f"📣 *Broadcasting...*\n\n{progress_bar(0, total)}\n"
        f"Sent: `0/{total}`",
        parse_mode="Markdown"
    )

    sent = 0
    failed = 0
    for i, uid in enumerate(user_ids):
        try:
            await context.bot.send_message(
                chat_id=uid, text=text, parse_mode="Markdown"
            )
            sent += 1
        except Exception:
            failed += 1

        # Update progress every 25 users
        if (i + 1) % 25 == 0 or i == total - 1:
            try:
                await status_msg.edit_text(
                    f"📣 *Broadcasting...*\n\n{progress_bar(i + 1, total)}\n"
                    f"Sent: `{sent}` | Failed: `{failed}` | Total: `{total}`",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        await asyncio.sleep(BROADCAST_DELAY)

    await db.update_broadcast(broadcast_id, sent, failed)

    await status_msg.edit_text(
        f"✅ *Broadcast Complete!*\n\n"
        f"📨 Sent: `{sent}`\n"
        f"❌ Failed: `{failed}`\n"
        f"👥 Total: `{total}`",
        reply_markup=back_button("admin_broadcast"),
        parse_mode="Markdown"
    )


async def _show_broadcast_history(query, db):
    """Show recent broadcasts."""
    broadcasts = await db.get_broadcasts(10)
    if not broadcasts:
        text = "📊 *Broadcast History*\n\nNo broadcasts yet."
    else:
        text = "📊 *Broadcast History*\n\n"
        for b in broadcasts:
            msg_preview = (b.get("message_text") or "")[:50]
            text += (
                f"📅 `{format_datetime(b.get('started_at'))}`\n"
                f"   📨 {b.get('sent_count', 0)}/{b.get('total_users', 0)} "
                f"(❌ {b.get('failed_count', 0)})\n"
                f"   📝 {msg_preview}...\n\n"
            )

    await query.edit_message_text(
        text, reply_markup=back_button("admin_broadcast"), parse_mode="Markdown"
    )


# ===================== CAMPAIGN =====================

async def _show_campaign_menu(query, db):
    """Campaign management sub-menu."""
    claims_on = (await db.get_setting("claims_enabled", "1")) == "1"
    steps = await db.get_setting("claim_steps", str(DEFAULT_STEPS))
    status = "✅ Enabled" if claims_on else "❌ Disabled"
    toggle_text = "❌ Disable Claims" if claims_on else "✅ Enable Claims"

    keyboard = [
        [InlineKeyboardButton(toggle_text, callback_data="admin_camp_toggle")],
        [InlineKeyboardButton(f"💪 Steps: {steps}", callback_data="admin_camp_steps")],
        [InlineKeyboardButton("📋 Claim Logs", callback_data="admin_camp_logs")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_main")]
    ]
    await query.edit_message_text(
        f"🏃 *Campaign Management*\n\n"
        f"Status: {status}\n"
        f"Steps: `{steps}`",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def _show_claim_logs(query, db):
    """Show recent claim logs (vouchers)."""
    vouchers = await db.get_recent_vouchers(10)
    if not vouchers:
        text = "📋 *Claim Logs*\n\nNo claims yet."
    else:
        text = "📋 *Recent Claims*\n\n"
        for v in vouchers:
            name = v.get("first_name") or str(v.get("user_id", "?"))
            text += (
                f"🎫 `{v.get('voucher_code', 'N/A')}`\n"
                f"   👤 {name} | 📱 `{v.get('phone', 'N/A')}`\n"
                f"   📅 `{format_datetime(v.get('claimed_at'))}`\n\n"
            )

    await query.edit_message_text(
        text, reply_markup=back_button("admin_campaign"), parse_mode="Markdown"
    )


# ===================== SETTINGS =====================

async def _show_settings_menu(query, db):
    """Settings sub-menu."""
    referral_on = (await db.get_setting("referral_enabled", "1")) == "1"
    maintenance = (await db.get_setting("maintenance_mode", "0")) == "1"

    ref_text = "✅ Referrals: ON" if referral_on else "❌ Referrals: OFF"
    maint_text = "🔧 Maintenance: ON" if maintenance else "✅ Maintenance: OFF"

    keyboard = [
        [InlineKeyboardButton("📝 Welcome Message", callback_data="admin_set_welcome")],
        [InlineKeyboardButton("ℹ️ Help Message", callback_data="admin_set_help")],
        [InlineKeyboardButton(ref_text, callback_data="admin_set_referral")],
        [InlineKeyboardButton(maint_text, callback_data="admin_set_maintenance")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_main")]
    ]
    await query.edit_message_text(
        "⚙️ *Bot Settings*\n\nConfigure bot behavior:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

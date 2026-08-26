#!/usr/bin/env python3
"""MoneyZone Premium Keyboard Builders — High-Vibrancy UI"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """MoneyZone Main Menu Keyboard."""
    keyboard = [
        [InlineKeyboardButton("⚡ 🏃 CLAIM LENSKART REWARD 🏃 ⚡", callback_data="user_claim")],
        [InlineKeyboardButton("🎁 MY VOUCHER VAULT", callback_data="user_vouchers"),
         InlineKeyboardButton("🔥 REFER & EARN CASH", callback_data="user_referrals")],
        [InlineKeyboardButton("📊 ACCOUNT PROFILE", callback_data="user_profile"),
         InlineKeyboardButton("👑 TOP LEADERBOARD 🏆", callback_data="user_leaderboard")],
        [InlineKeyboardButton("💬 24/7 SUPPORT & HELP", callback_data="user_help")]
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Admin Panel Main Menu."""
    keyboard = [
        [InlineKeyboardButton("📊 REALTIME STATS", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 USER CONTROL", callback_data="admin_users"),
         InlineKeyboardButton("📢 FORCE CHANNELS", callback_data="admin_channels")],
        [InlineKeyboardButton("📣 BROADCAST SYSTEM", callback_data="admin_broadcast"),
         InlineKeyboardButton("🏃 CAMPAIGN SETTINGS", callback_data="admin_campaign")],
        [InlineKeyboardButton("⚙️ SYSTEM CONFIG", callback_data="admin_settings")],
        [InlineKeyboardButton("❌ CLOSE ADMIN PANEL", callback_data="admin_close")]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_button(callback_data: str = "admin_main") -> InlineKeyboardMarkup:
    """Single Back Button."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 BACK TO MENU", callback_data=callback_data)]])


def confirm_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    """Yes/No Confirmation."""
    keyboard = [
        [InlineKeyboardButton("✅ CONFIRM", callback_data=yes_data),
         InlineKeyboardButton("❌ CANCEL", callback_data=no_data)]
    ]
    return InlineKeyboardMarkup(keyboard)


def force_join_keyboard(channels: list, verified: set = None) -> InlineKeyboardMarkup:
    """Build MoneyZone Force Join channel buttons with animated status icons."""
    verified = verified or set()
    buttons = []
    for ch in channels:
        ch_id = ch["channel_id"]
        title = ch.get("channel_title") or "Sponsor Channel"
        link = ch.get("invite_link")
        if not link and ch.get("channel_username"):
            link = f"https://t.me/{ch['channel_username'].lstrip('@')}"
        if not link:
            continue
        icon = "🟢 JOINED" if ch_id in verified else "🔴 JOIN CHANNEL"
        buttons.append([InlineKeyboardButton(f"{icon} ➔ {title}", url=link)])
    
    buttons.append([InlineKeyboardButton("⚡ ✅ VERIFY ACCESS NOW ⚡", callback_data="verify_channels")])
    return InlineKeyboardMarkup(buttons)


def pagination_keyboard(prefix: str, current_page: int, total_pages: int, back_data: str = None) -> InlineKeyboardMarkup:
    """Pagination buttons."""
    buttons = []
    nav = []
    if current_page > 1:
        nav.append(InlineKeyboardButton("◀️ PREV", callback_data=f"{prefix}_{current_page - 1}"))
    nav.append(InlineKeyboardButton(f"PAGE {current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav.append(InlineKeyboardButton("NEXT ▶️", callback_data=f"{prefix}_{current_page + 1}"))
    buttons.append(nav)
    if back_data:
        buttons.append([InlineKeyboardButton("🔙 BACK", callback_data=back_data)])
    return InlineKeyboardMarkup(buttons)


def user_action_keyboard(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    """Admin actions for a specific user."""
    ban_btn = (
        InlineKeyboardButton("✅ UNBAN USER", callback_data=f"admin_unban_{user_id}")
        if is_banned else
        InlineKeyboardButton("🚫 BAN USER", callback_data=f"admin_ban_{user_id}")
    )
    keyboard = [
        [ban_btn],
        [InlineKeyboardButton("👥 REFERRALS TREE", callback_data=f"admin_user_refs_{user_id}")],
        [InlineKeyboardButton("🎫 VOUCHERS CLAIMED", callback_data=f"admin_user_vouchers_{user_id}")],
        [InlineKeyboardButton("🔙 BACK TO USER LIST", callback_data="admin_users")]
    ]
    return InlineKeyboardMarkup(keyboard)


def channel_list_keyboard(channels: list) -> InlineKeyboardMarkup:
    """List channels with remove buttons."""
    buttons = []
    for ch in channels:
        title = ch.get("channel_title") or str(ch["channel_id"])
        buttons.append([
            InlineKeyboardButton(f"📢 {title}", callback_data="noop"),
            InlineKeyboardButton("🗑️ REMOVE", callback_data=f"admin_ch_del_{ch['channel_id']}")
        ])
    buttons.append([InlineKeyboardButton("🔙 BACK TO CHANNELS", callback_data="admin_channels")])
    return InlineKeyboardMarkup(buttons)

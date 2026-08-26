#!/usr/bin/env python3
"""Keyboard builders for inline and reply keyboards"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main user menu."""
    keyboard = [
        [InlineKeyboardButton("🏃 Claim Reward", callback_data="user_claim")],
        [InlineKeyboardButton("🎁 My Vouchers", callback_data="user_vouchers"),
         InlineKeyboardButton("👥 Refer & Earn", callback_data="user_referrals")],
        [InlineKeyboardButton("👤 My Profile", callback_data="user_profile"),
         InlineKeyboardButton("🏆 Leaderboard", callback_data="user_leaderboard")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="user_help")]
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Admin panel main menu."""
    keyboard = [
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Users", callback_data="admin_users"),
         InlineKeyboardButton("📢 Channels", callback_data="admin_channels")],
        [InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast"),
         InlineKeyboardButton("🏃 Campaign", callback_data="admin_campaign")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings")],
        [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_button(callback_data: str = "admin_main") -> InlineKeyboardMarkup:
    """Single back button."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=callback_data)]])


def confirm_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    """Yes/No confirmation."""
    keyboard = [
        [InlineKeyboardButton("✅ Yes", callback_data=yes_data),
         InlineKeyboardButton("❌ No", callback_data=no_data)]
    ]
    return InlineKeyboardMarkup(keyboard)


def force_join_keyboard(channels: list, verified: set = None) -> InlineKeyboardMarkup:
    """Build force join channel buttons with verify."""
    verified = verified or set()
    buttons = []
    for ch in channels:
        ch_id = ch["channel_id"]
        title = ch.get("channel_title") or "Channel"
        link = ch.get("invite_link")
        if not link and ch.get("channel_username"):
            link = f"https://t.me/{ch['channel_username'].lstrip('@')}"
        if not link:
            continue
        icon = "✅" if ch_id in verified else "📢"
        buttons.append([InlineKeyboardButton(f"{icon} {title}", url=link)])
    buttons.append([InlineKeyboardButton("✅ Verify", callback_data="verify_channels")])
    return InlineKeyboardMarkup(buttons)


def pagination_keyboard(prefix: str, current_page: int, total_pages: int, back_data: str = None) -> InlineKeyboardMarkup:
    """Pagination buttons."""
    buttons = []
    nav = []
    if current_page > 1:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"{prefix}_{current_page - 1}"))
    nav.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"{prefix}_{current_page + 1}"))
    buttons.append(nav)
    if back_data:
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=back_data)])
    return InlineKeyboardMarkup(buttons)


def user_action_keyboard(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    """Admin actions for a specific user."""
    ban_btn = (
        InlineKeyboardButton("✅ Unban", callback_data=f"admin_unban_{user_id}")
        if is_banned else
        InlineKeyboardButton("🚫 Ban", callback_data=f"admin_ban_{user_id}")
    )
    keyboard = [
        [ban_btn],
        [InlineKeyboardButton("👥 Referrals", callback_data=f"admin_user_refs_{user_id}")],
        [InlineKeyboardButton("🎫 Vouchers", callback_data=f"admin_user_vouchers_{user_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_users")]
    ]
    return InlineKeyboardMarkup(keyboard)


def channel_list_keyboard(channels: list) -> InlineKeyboardMarkup:
    """List channels with remove buttons."""
    buttons = []
    for ch in channels:
        title = ch.get("channel_title") or str(ch["channel_id"])
        buttons.append([
            InlineKeyboardButton(f"📢 {title}", callback_data="noop"),
            InlineKeyboardButton("❌", callback_data=f"admin_ch_del_{ch['channel_id']}")
        ])
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="admin_channels")])
    return InlineKeyboardMarkup(buttons)

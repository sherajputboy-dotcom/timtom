#!/usr/bin/env python3
"""Clean, Premium Keyboard Builders for Lenskart Bot (Powered by MoneyZone)"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Persistent bottom menu reply keyboard."""
    keyboard = [
        [KeyboardButton("🏃 Claim Reward"), KeyboardButton("🎁 My Vouchers")],
        [KeyboardButton("👥 Refer & Earn"), KeyboardButton("👤 My Profile")],
        [KeyboardButton("🏆 Leaderboard"), KeyboardButton("ℹ️ Help")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Clean inline menu keyboard."""
    keyboard = [
        [InlineKeyboardButton("🏃 Claim Lenskart Voucher (20 Pts)", callback_data="user_claim")],
        [InlineKeyboardButton("🎁 My Vouchers", callback_data="user_vouchers"),
         InlineKeyboardButton("👥 Refer & Earn (+50 Pts)", callback_data="user_referrals")],
        [InlineKeyboardButton("👤 My Profile", callback_data="user_profile"),
         InlineKeyboardButton("🏆 Leaderboard", callback_data="user_leaderboard")],
        [InlineKeyboardButton("ℹ️ Help & Support", callback_data="user_help")]
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Admin Panel Main Menu."""
    keyboard = [
        [InlineKeyboardButton("📊 Realtime Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 User Control", callback_data="admin_users"),
         InlineKeyboardButton("📢 Force Channels", callback_data="admin_channels")],
        [InlineKeyboardButton("📣 Broadcast", callback_data="admin_broadcast"),
         InlineKeyboardButton("🏃 Campaign Config", callback_data="admin_campaign")],
        [InlineKeyboardButton("⚙️ Bot Settings", callback_data="admin_settings")],
        [InlineKeyboardButton("❌ Close Admin Panel", callback_data="admin_close")]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_button(callback_data: str = "admin_main") -> InlineKeyboardMarkup:
    """Single Back Button."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back to Menu", callback_data=callback_data)]])


def confirm_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    """Yes/No Confirmation."""
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=yes_data),
         InlineKeyboardButton("❌ Cancel", callback_data=no_data)]
    ]
    return InlineKeyboardMarkup(keyboard)


def force_join_keyboard(channels: list, verified: set = None) -> InlineKeyboardMarkup:
    """Build Force Join channel buttons with clickable links."""
    verified = verified or set()
    buttons = []
    for ch in channels:
        ch_id = ch["channel_id"]
        title = ch.get("channel_title") or "Sponsor Channel"
        link = ch.get("invite_link")
        
        if not link and ch.get("channel_username"):
            clean_username = ch["channel_username"].replace("@", "").strip()
            link = f"https://t.me/{clean_username}"
            
        if not link:
            # Fallback format if no username or invite link saved
            clean_id = str(ch_id).replace("-100", "")
            link = f"https://t.me/c/{clean_id}/1"
            
        is_joined = ch_id in verified
        icon = "✅" if is_joined else "📢"
        status_text = "Joined" if is_joined else "Click to Join"
        buttons.append([InlineKeyboardButton(f"{icon} {title} ({status_text})", url=link)])
    
    buttons.append([InlineKeyboardButton("✅ Verify Access", callback_data="verify_channels")])
    return InlineKeyboardMarkup(buttons)


def pagination_keyboard(prefix: str, current_page: int, total_pages: int, back_data: str = None) -> InlineKeyboardMarkup:
    """Pagination buttons."""
    buttons = []
    nav = []
    if current_page > 1:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"{prefix}_{current_page - 1}"))
    nav.append(InlineKeyboardButton(f"Page {current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"{prefix}_{current_page + 1}"))
    buttons.append(nav)
    if back_data:
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=back_data)])
    return InlineKeyboardMarkup(buttons)


def user_action_keyboard(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    """Admin actions for a specific user."""
    ban_btn = (
        InlineKeyboardButton("✅ Unban User", callback_data=f"admin_unban_{user_id}")
        if is_banned else
        InlineKeyboardButton("🚫 Ban User", callback_data=f"admin_ban_{user_id}")
    )
    keyboard = [
        [ban_btn],
        [InlineKeyboardButton("👥 Referrals", callback_data=f"admin_user_refs_{user_id}")],
        [InlineKeyboardButton("🎫 Vouchers", callback_data=f"admin_user_vouchers_{user_id}")],
        [InlineKeyboardButton("🔙 Back to Users", callback_data="admin_users")]
    ]
    return InlineKeyboardMarkup(keyboard)


def channel_list_keyboard(channels: list) -> InlineKeyboardMarkup:
    """List channels with remove buttons."""
    buttons = []
    for ch in channels:
        title = ch.get("channel_title") or str(ch["channel_id"])
        buttons.append([
            InlineKeyboardButton(f"📢 {title}", callback_data="noop"),
            InlineKeyboardButton("❌ Remove", callback_data=f"admin_ch_del_{ch['channel_id']}")
        ])
    buttons.append([InlineKeyboardButton("🔙 Back to Channels", callback_data="admin_channels")])
    return InlineKeyboardMarkup(buttons)

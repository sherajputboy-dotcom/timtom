#!/usr/bin/env python3
"""Clean Keyboard Builders with Telegram Bot API 9.4 Colorful Button Styles for Lenskart Bot (Powered by MoneyZone)"""

from telegram import (
    InlineKeyboardButton as BaseInlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton as BaseKeyboardButton
)


class StyledInlineKeyboardButton(BaseInlineKeyboardButton):
    """
    Subclass of InlineKeyboardButton supporting Telegram Bot API 9.4 button styles:
    - style='primary' (Blue 🔵)
    - style='success' (Green 🟢)
    - style='danger'  (Red 🔴)
    """

    def __init__(self, text: str, style: str = None, **kwargs):
        super().__init__(text=text, **kwargs)
        self.style = style

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.style:
            d["style"] = self.style
        return d


class StyledKeyboardButton(BaseKeyboardButton):
    """
    Subclass of KeyboardButton supporting Telegram Bot API 9.4 button styles:
    - style='primary' (Blue 🔵)
    - style='success' (Green 🟢)
    - style='danger'  (Red 🔴)
    """

    def __init__(self, text: str, style: str = None, **kwargs):
        super().__init__(text=text, **kwargs)
        self.style = style

    def to_dict(self) -> dict:
        d = super().to_dict()
        if self.style:
            d["style"] = self.style
        return d


# Alias for seamless backwards compatibility across all keyboard functions
InlineKeyboardButton = StyledInlineKeyboardButton
KeyboardButton = StyledKeyboardButton


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Vibrant & Colorful persistent bottom menu reply keyboard (Primary Navigation)."""
    keyboard = [
        [KeyboardButton("⚡ 🏃 CLAIM REWARD", style="success"), KeyboardButton("🎁 MY VOUCHERS", style="primary")],
        [KeyboardButton("🔥 REFER & EARN", style="primary"), KeyboardButton("👤 MY PROFILE", style="primary")],
        [KeyboardButton("🏆 LEADERBOARD", style="primary"), KeyboardButton("💬 HELP & SUPPORT", style="primary")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def refresh_dashboard_keyboard() -> InlineKeyboardMarkup:
    """Sleek dashboard action button with API 9.4 colorful styles."""
    keyboard = [
        [InlineKeyboardButton("🏃 Claim Lenskart Voucher (20 Pts)", callback_data="user_claim", style="success")],
        [InlineKeyboardButton("🔄 Refresh Dashboard", callback_data="main_menu", style="primary")]
    ]
    return InlineKeyboardMarkup(keyboard)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Alias for backwards compatibility across all handlers."""
    return refresh_dashboard_keyboard()


def claim_result_keyboard() -> InlineKeyboardMarkup:
    """Inline keyboard for claim result card with instant Run Again button."""
    keyboard = [
        [InlineKeyboardButton("🔄 🏃 RUN AGAIN / CLAIM ANOTHER", callback_data="user_claim", style="success")],
        [InlineKeyboardButton("🎁 My Voucher Vault", callback_data="user_vouchers", style="primary")]
    ]
    return InlineKeyboardMarkup(keyboard)


def admin_menu_keyboard() -> InlineKeyboardMarkup:
    """Admin Panel Main Menu."""
    keyboard = [
        [InlineKeyboardButton("📊 Realtime Stats", callback_data="admin_stats", style="primary")],
        [InlineKeyboardButton("👥 User Control", callback_data="admin_users", style="primary"),
         InlineKeyboardButton("📢 Force Channels", callback_data="admin_channels", style="primary")],
        [InlineKeyboardButton("📣 Broadcast System", callback_data="admin_broadcast", style="primary"),
         InlineKeyboardButton("🏃 Campaign Config", callback_data="admin_campaign", style="primary")],
        [InlineKeyboardButton("⚙️ Bot Settings", callback_data="admin_settings", style="primary")],
        [InlineKeyboardButton("❌ Close Admin Panel", callback_data="admin_close", style="danger")]
    ]
    return InlineKeyboardMarkup(keyboard)


def back_button(callback_data: str = "main_menu") -> InlineKeyboardMarkup:
    """Single Back Button."""
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data=callback_data, style="primary")]])


def confirm_keyboard(yes_data: str, no_data: str) -> InlineKeyboardMarkup:
    """Yes/No Confirmation."""
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data=yes_data, style="success"),
         InlineKeyboardButton("❌ Cancel", callback_data=no_data, style="danger")]
    ]
    return InlineKeyboardMarkup(keyboard)


def force_join_keyboard(channels: list, verified: set = None) -> InlineKeyboardMarkup:
    """Build Force Join channel buttons with direct clickable links and API 9.4 colorful styles."""
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
            clean_id = str(ch_id).replace("-100", "")
            link = f"https://t.me/c/{clean_id}/1"
            
        is_joined = ch_id in verified
        icon = "✅" if is_joined else "📢"
        status_text = "Joined" if is_joined else "Join Channel"
        style = "success" if is_joined else "danger"
        buttons.append([InlineKeyboardButton(f"{icon} {title} ({status_text})", url=link, style=style)])
    
    buttons.append([InlineKeyboardButton("🔄 Refresh / Verify Status", callback_data="verify_channels", style="primary")])
    return InlineKeyboardMarkup(buttons)


def pagination_keyboard(prefix: str, current_page: int, total_pages: int, back_data: str = None) -> InlineKeyboardMarkup:
    """Pagination buttons."""
    buttons = []
    nav = []
    if current_page > 1:
        nav.append(InlineKeyboardButton("◀️ Prev", callback_data=f"{prefix}_{current_page - 1}", style="primary"))
    nav.append(InlineKeyboardButton(f"Page {current_page}/{total_pages}", callback_data="noop"))
    if current_page < total_pages:
        nav.append(InlineKeyboardButton("Next ▶️", callback_data=f"{prefix}_{current_page + 1}", style="primary"))
    buttons.append(nav)
    if back_data:
        buttons.append([InlineKeyboardButton("🔙 Back", callback_data=back_data, style="primary")])
    return InlineKeyboardMarkup(buttons)


def user_action_keyboard(user_id: int, is_banned: bool) -> InlineKeyboardMarkup:
    """Admin actions for a specific user."""
    ban_btn = (
        InlineKeyboardButton("✅ Unban User", callback_data=f"admin_unban_{user_id}", style="success")
        if is_banned else
        InlineKeyboardButton("🚫 Ban User", callback_data=f"admin_ban_{user_id}", style="danger")
    )
    keyboard = [
        [ban_btn],
        [InlineKeyboardButton("💰 Give Credits (Points)", callback_data=f"admin_user_credits_{user_id}", style="success")],
        [InlineKeyboardButton("👥 Referrals", callback_data=f"admin_user_refs_{user_id}", style="primary")],
        [InlineKeyboardButton("🎫 Vouchers", callback_data=f"admin_user_vouchers_{user_id}", style="primary")],
        [InlineKeyboardButton("🔙 Back to Users", callback_data="admin_users", style="primary")]
    ]
    return InlineKeyboardMarkup(keyboard)


def channel_list_keyboard(channels: list) -> InlineKeyboardMarkup:
    """List channels with remove buttons."""
    buttons = []
    for ch in channels:
        title = ch.get("channel_title") or str(ch["channel_id"])
        buttons.append([
            InlineKeyboardButton(f"📢 {title}", callback_data="noop", style="primary"),
            InlineKeyboardButton("❌ Remove", callback_data=f"admin_ch_del_{ch['channel_id']}", style="danger")
        ])
    buttons.append([InlineKeyboardButton("🔙 Back to Channels", callback_data="admin_channels", style="primary")])
    return InlineKeyboardMarkup(buttons)

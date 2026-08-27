#!/usr/bin/env python3
"""Utility helpers — formatting, pagination, text charts, markdown escaping"""

from datetime import datetime


def escape_md(text: str) -> str:
    """Escape Markdown special characters to prevent Telegram parse errors."""
    if not text:
        return ""
    text_str = str(text)
    for char in ["_", "*", "`", "[", "]"]:
        text_str = text_str.replace(char, f"\\{char}")
    return text_str


def format_number(n: int) -> str:
    """Format number with commas: 1234567 -> 1,234,567"""
    return f"{n:,}"


def format_datetime(dt_str: str) -> str:
    """Format ISO datetime string to readable format."""
    if not dt_str:
        return "N/A"
    try:
        if isinstance(dt_str, str):
            dt = datetime.fromisoformat(dt_str)
        else:
            dt = dt_str
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return str(dt_str)


def truncate(text: str, length: int = 50) -> str:
    """Truncate text with ellipsis."""
    if not text:
        return ""
    return text[:length] + "..." if len(text) > length else text


def mention_user(user_id: int, name: str = None) -> str:
    """Create Telegram mention link."""
    display = escape_md(name or str(user_id))
    return f"[{display}](tg://user?id={user_id})"


def bar_chart(data: list, max_width: int = 15) -> str:
    """Create text-based bar chart from list of (label, value) tuples."""
    if not data:
        return "No data available."
    max_val = max(v for _, v in data) if data else 1
    if max_val == 0:
        max_val = 1
    lines = []
    for label, value in data:
        bar_len = int((value / max_val) * max_width)
        bar = "█" * bar_len + "░" * (max_width - bar_len)
        lines.append(f"`{label}` {bar} `{value}`")
    return "\n".join(lines)


def progress_bar(current: int, total: int, width: int = 20) -> str:
    """Create progress bar string."""
    if total == 0:
        return "[" + "░" * width + "] 0%"
    pct = current / total
    filled = int(pct * width)
    bar = "█" * filled + "░" * (width - filled)
    return f"[{bar}] {pct * 100:.1f}%"


def paginate_text(items: list, page: int, per_page: int, formatter) -> tuple:
    """Paginate a list and format items. Returns (formatted_text, total_pages)."""
    total = len(items)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    start = (page - 1) * per_page
    end = start + per_page
    page_items = items[start:end]
    text = "\n".join(formatter(i, item) for i, item in enumerate(page_items, start=start + 1))
    text += f"\n\n📄 Page {page}/{total_pages} | Total: {total}"
    return text, total_pages

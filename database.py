#!/usr/bin/env python3
"""Async SQLite Database Layer"""

import aiosqlite
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code TEXT DEFAULT 'en',
    referred_by INTEGER,
    referral_count INTEGER DEFAULT 0,
    is_banned INTEGER DEFAULT 0,
    is_verified INTEGER DEFAULT 0,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS channels (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id INTEGER UNIQUE NOT NULL,
    channel_username TEXT,
    channel_title TEXT,
    invite_link TEXT,
    added_by INTEGER,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS vouchers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    phone TEXT NOT NULL,
    voucher_code TEXT,
    tier TEXT,
    device_brand TEXT,
    device_model TEXT,
    expiry_date TIMESTAMP,
    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS broadcasts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    message_text TEXT,
    total_users INTEGER DEFAULT 0,
    sent_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""


class Database:
    """Async SQLite database for bot persistence."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH

    async def init(self):
        """Initialize database and create tables."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def _fetch_one(self, query: str, params: tuple = None) -> dict:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params or ())
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def _fetch_all(self, query: str, params: tuple = None) -> list:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(query, params or ())
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def _execute(self, query: str, params: tuple = None) -> int:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(query, params or ())
            await db.commit()
            return cursor.lastrowid

    # ===================== USER METHODS =====================

    async def add_user(self, user_id: int, username: str = None, first_name: str = None,
                       last_name: str = None, language_code: str = "en", referred_by: int = None) -> bool:
        """Add new user. Returns True if new, False if existing."""
        existing = await self.get_user(user_id)
        if existing:
            # Update username/name in case they changed
            await self._execute(
                "UPDATE users SET username = ?, first_name = ?, last_name = ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
                (username, first_name, last_name, user_id)
            )
            return False
        await self._execute(
            "INSERT INTO users (user_id, username, first_name, last_name, language_code, referred_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, username, first_name, last_name, language_code, referred_by)
        )
        # Increment referrer's count
        if referred_by:
            await self._execute(
                "UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?",
                (referred_by,)
            )
        return True

    async def get_user(self, user_id: int) -> dict:
        return await self._fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))

    async def update_last_active(self, user_id: int):
        await self._execute("UPDATE users SET last_active = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))

    async def set_verified(self, user_id: int, verified: bool = True):
        await self._execute("UPDATE users SET is_verified = ? WHERE user_id = ?", (1 if verified else 0, user_id))

    async def ban_user(self, user_id: int):
        await self._execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))

    async def unban_user(self, user_id: int):
        await self._execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))

    async def is_banned(self, user_id: int) -> bool:
        user = await self.get_user(user_id)
        return bool(user and user.get("is_banned"))

    async def get_all_user_ids(self) -> list:
        rows = await self._fetch_all("SELECT user_id FROM users WHERE is_banned = 0")
        return [r["user_id"] for r in rows]

    async def get_total_users(self) -> int:
        row = await self._fetch_one("SELECT COUNT(*) as c FROM users")
        return row["c"] if row else 0

    async def get_today_users(self) -> int:
        row = await self._fetch_one("SELECT COUNT(*) as c FROM users WHERE DATE(joined_at) = DATE('now')")
        return row["c"] if row else 0

    async def get_active_today(self) -> int:
        row = await self._fetch_one("SELECT COUNT(*) as c FROM users WHERE DATE(last_active) = DATE('now')")
        return row["c"] if row else 0

    async def get_banned_count(self) -> int:
        row = await self._fetch_one("SELECT COUNT(*) as c FROM users WHERE is_banned = 1")
        return row["c"] if row else 0

    async def get_users_paginated(self, page: int = 1, per_page: int = 10) -> list:
        offset = (page - 1) * per_page
        return await self._fetch_all(
            "SELECT * FROM users ORDER BY joined_at DESC LIMIT ? OFFSET ?",
            (per_page, offset)
        )

    async def search_user(self, query: str) -> dict:
        """Search user by ID or username."""
        if query.isdigit():
            return await self.get_user(int(query))
        return await self._fetch_one(
            "SELECT * FROM users WHERE username LIKE ? OR first_name LIKE ?",
            (f"%{query}%", f"%{query}%")
        )

    async def get_daily_signups(self, days: int = 7) -> list:
        return await self._fetch_all(
            "SELECT DATE(joined_at) as date, COUNT(*) as count FROM users "
            "WHERE joined_at >= DATE('now', ?) GROUP BY DATE(joined_at) ORDER BY date",
            (f"-{days} days",)
        )

    # ===================== REFERRAL METHODS =====================

    async def get_referral_count(self, user_id: int) -> int:
        user = await self.get_user(user_id)
        return user["referral_count"] if user else 0

    async def get_referrals(self, user_id: int, limit: int = 20) -> list:
        return await self._fetch_all(
            "SELECT user_id, username, first_name, joined_at FROM users "
            "WHERE referred_by = ? ORDER BY joined_at DESC LIMIT ?",
            (user_id, limit)
        )

    async def get_top_referrers(self, limit: int = 10) -> list:
        return await self._fetch_all(
            "SELECT user_id, username, first_name, referral_count FROM users "
            "WHERE referral_count > 0 ORDER BY referral_count DESC LIMIT ?",
            (limit,)
        )

    async def get_total_referrals(self) -> int:
        row = await self._fetch_one("SELECT COALESCE(SUM(referral_count), 0) as total FROM users")
        return row["total"] if row else 0

    # ===================== CHANNEL METHODS =====================

    async def add_channel(self, channel_id: int, username: str = None, title: str = None,
                          invite_link: str = None, added_by: int = None) -> bool:
        try:
            await self._execute(
                "INSERT INTO channels (channel_id, channel_username, channel_title, invite_link, added_by) "
                "VALUES (?, ?, ?, ?, ?)",
                (channel_id, username, title, invite_link, added_by)
            )
            return True
        except Exception:
            return False

    async def remove_channel(self, channel_id: int):
        await self._execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))

    async def get_channels(self) -> list:
        return await self._fetch_all("SELECT * FROM channels WHERE is_active = 1")

    async def get_channel_count(self) -> int:
        row = await self._fetch_one("SELECT COUNT(*) as c FROM channels WHERE is_active = 1")
        return row["c"] if row else 0

    # ===================== VOUCHER METHODS =====================

    async def add_voucher(self, user_id: int, phone: str, voucher_code: str,
                          tier: str = None, device_brand: str = None,
                          device_model: str = None, expiry_date=None) -> int:
        return await self._execute(
            "INSERT INTO vouchers (user_id, phone, voucher_code, tier, device_brand, device_model, expiry_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, phone, voucher_code, tier, device_brand, device_model, expiry_date)
        )

    async def get_user_vouchers(self, user_id: int) -> list:
        return await self._fetch_all(
            "SELECT * FROM vouchers WHERE user_id = ? ORDER BY claimed_at DESC", (user_id,)
        )

    async def get_total_vouchers(self) -> int:
        row = await self._fetch_one("SELECT COUNT(*) as c FROM vouchers")
        return row["c"] if row else 0

    async def get_recent_vouchers(self, limit: int = 10) -> list:
        return await self._fetch_all(
            "SELECT v.*, u.username, u.first_name FROM vouchers v "
            "LEFT JOIN users u ON v.user_id = u.user_id "
            "ORDER BY v.claimed_at DESC LIMIT ?",
            (limit,)
        )

    # ===================== BROADCAST METHODS =====================

    async def add_broadcast(self, admin_id: int, message_text: str, total_users: int) -> int:
        return await self._execute(
            "INSERT INTO broadcasts (admin_id, message_text, total_users) VALUES (?, ?, ?)",
            (admin_id, message_text, total_users)
        )

    async def update_broadcast(self, broadcast_id: int, sent_count: int, failed_count: int):
        await self._execute(
            "UPDATE broadcasts SET sent_count = ?, failed_count = ?, completed_at = CURRENT_TIMESTAMP WHERE id = ?",
            (sent_count, failed_count, broadcast_id)
        )

    async def get_broadcasts(self, limit: int = 10) -> list:
        return await self._fetch_all(
            "SELECT * FROM broadcasts ORDER BY started_at DESC LIMIT ?", (limit,)
        )

    # ===================== SETTINGS METHODS =====================

    async def get_setting(self, key: str, default: str = None) -> str:
        row = await self._fetch_one("SELECT value FROM settings WHERE key = ?", (key,))
        return row["value"] if row else default

    async def set_setting(self, key: str, value: str):
        await self._execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )

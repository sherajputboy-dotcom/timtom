#!/usr/bin/env python3
"""
Async Database Layer — Dual Engine (PostgreSQL via Neon/Render & SQLite Local Fallback)
Survives deployments and server restarts cleanly!
"""

import os
import re
import logging
import aiosqlite

try:
    import asyncpg
except ImportError:
    asyncpg = None

from config import DB_PATH

logger = logging.getLogger(__name__)

# Environment variable for Postgres (Neon / Render)
DATABASE_URL = os.environ.get("DATABASE_URL")

PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id BIGINT PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code TEXT DEFAULT 'en',
    referred_by BIGINT,
    referral_count INT DEFAULT 0,
    points INT DEFAULT 20,
    is_banned INT DEFAULT 0,
    is_verified INT DEFAULT 0,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS channels (
    id SERIAL PRIMARY KEY,
    channel_id BIGINT UNIQUE NOT NULL,
    channel_username TEXT,
    channel_title TEXT,
    invite_link TEXT,
    added_by BIGINT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active INT DEFAULT 1
);

CREATE TABLE IF NOT EXISTS vouchers (
    id SERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    phone TEXT NOT NULL,
    voucher_code TEXT,
    tier TEXT,
    device_brand TEXT,
    device_model TEXT,
    expiry_date TIMESTAMP,
    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS broadcasts (
    id SERIAL PRIMARY KEY,
    admin_id BIGINT NOT NULL,
    message_text TEXT,
    total_users INT DEFAULT 0,
    sent_count INT DEFAULT 0,
    failed_count INT DEFAULT 0,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

SQLITE_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    first_name TEXT,
    last_name TEXT,
    language_code TEXT DEFAULT 'en',
    referred_by INTEGER,
    referral_count INTEGER DEFAULT 0,
    points INTEGER DEFAULT 20,
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
    claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    """Async Dual-Engine Database Manager (PostgreSQL & SQLite)."""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self.is_pg = False
        self.pool = None
        self._sqlite_conn = None

    async def init(self):
        """Initialize connection pool (Neon Postgres if DATABASE_URL set, else SQLite)."""
        dsn = DATABASE_URL
        if dsn and asyncpg:
            if dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            try:
                self.pool = await asyncpg.create_pool(dsn=dsn, min_size=1, max_size=10)
                self.is_pg = True
                async with self.pool.acquire() as conn:
                    await conn.execute(PG_SCHEMA)
                logger.info("🐘 Connected to Neon/Render PostgreSQL Database! Data is persistent.")
                return
            except Exception as e:
                logger.error(f"❌ PostgreSQL connection failed: {e}. Falling back to SQLite.")

        # Fallback to SQLite
        self.is_pg = False
        self._sqlite_conn = await aiosqlite.connect(self.db_path)
        self._sqlite_conn.row_factory = aiosqlite.Row
        await self._sqlite_conn.executescript(SQLITE_SCHEMA)
        try:
            await self._sqlite_conn.execute("ALTER TABLE users ADD COLUMN points INTEGER DEFAULT 20;")
            await self._sqlite_conn.commit()
        except Exception:
            pass
        logger.info("⚡ SQLite Database initialized (Local fallback mode).")

    async def close(self):
        if self.pool:
            await self.pool.close()
        if self._sqlite_conn:
            await self._sqlite_conn.close()

    def _convert_query(self, query: str) -> str:
        """Convert SQLite ? placeholders to PostgreSQL $1, $2 if using Postgres."""
        if not self.is_pg:
            return query
        count = 0
        def repl(match):
            nonlocal count
            count += 1
            return f"${count}"
        pg_query = re.sub(r'\?', repl, query)
        pg_query = pg_query.replace("INSERT OR REPLACE", "INSERT").replace("CURRENT_TIMESTAMP", "NOW()")
        return pg_query

    async def _fetch_one(self, query: str, params: tuple = None) -> dict:
        params = params or ()
        if self.is_pg:
            pg_q = self._convert_query(query)
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(pg_q, *params)
                return dict(row) if row else None
        else:
            async with self._sqlite_conn.execute(query, params) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def _fetch_all(self, query: str, params: tuple = None) -> list:
        params = params or ()
        if self.is_pg:
            pg_q = self._convert_query(query)
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(pg_q, *params)
                return [dict(r) for r in rows]
        else:
            async with self._sqlite_conn.execute(query, params) as cursor:
                rows = await cursor.fetchall()
                return [dict(r) for r in rows]

    async def _execute(self, query: str, params: tuple = None) -> int:
        params = params or ()
        if self.is_pg:
            if "INSERT INTO settings" in query:
                pg_q = "INSERT INTO settings (key, value) VALUES ($1, $2) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
            else:
                pg_q = self._convert_query(query)
            async with self.pool.acquire() as conn:
                res = await conn.execute(pg_q, *params)
                return 1
        else:
            async with self._sqlite_conn.execute(query, params) as cursor:
                await self._sqlite_conn.commit()
                return cursor.lastrowid

    # ===================== USER & POINTS METHODS =====================

    async def add_user(self, user_id: int, username: str = None, first_name: str = None,
                       last_name: str = None, language_code: str = "en", referred_by: int = None) -> bool:
        """Add new user with 20 starting points."""
        existing = await self.get_user(user_id)
        if existing:
            await self._execute(
                "UPDATE users SET username = ?, first_name = ?, last_name = ?, last_active = CURRENT_TIMESTAMP WHERE user_id = ?",
                (username, first_name, last_name, user_id)
            )
            return False

        await self._execute(
            "INSERT INTO users (user_id, username, first_name, last_name, language_code, referred_by, points) "
            "VALUES (?, ?, ?, ?, ?, ?, 20)",
            (user_id, username, first_name, last_name, language_code, referred_by)
        )
        return True

    async def get_user(self, user_id: int) -> dict:
        return await self._fetch_one("SELECT * FROM users WHERE user_id = ?", (user_id,))

    async def get_user_points(self, user_id: int) -> int:
        user = await self.get_user(user_id)
        return user.get("points", 20) if user else 20

    async def add_points(self, user_id: int, amount: int = 50):
        await self._execute("UPDATE users SET points = points + ? WHERE user_id = ?", (amount, user_id))

    async def deduct_points(self, user_id: int, amount: int = 20) -> bool:
        points = await self.get_user_points(user_id)
        if points < amount:
            return False
        await self._execute("UPDATE users SET points = points - ? WHERE user_id = ?", (amount, user_id))
        return True

    async def verify_user_and_reward_referrer(self, user_id: int) -> dict:
        """
        Mark user as verified. If user was referred by someone and hasn't been verified yet,
        credit +50 points to the referrer and increment referral count.
        Returns referrer info dict if reward was credited, else None.
        """
        user = await self.get_user(user_id)
        if not user:
            return None

        already_verified = bool(user.get("is_verified", 0))
        await self.set_verified(user_id, True)

        if not already_verified and user.get("referred_by"):
            referrer_id = user["referred_by"]
            await self._execute(
                "UPDATE users SET referral_count = referral_count + 1, points = points + 50 WHERE user_id = ?",
                (referrer_id,)
            )
            ref_data = await self.get_user(referrer_id)
            return {
                "referrer_id": referrer_id,
                "new_points": ref_data.get("points", 0) if ref_data else 0,
                "total_referrals": ref_data.get("referral_count", 0) if ref_data else 0
            }
        return None

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
            "SELECT user_id, username, first_name, referral_count, points FROM users "
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
        exp_dt = None
        if expiry_date:
            try:
                if isinstance(expiry_date, (int, float)):
                    exp_dt = datetime.fromtimestamp(expiry_date / 1000)
                elif isinstance(expiry_date, str) and expiry_date.isdigit():
                    exp_dt = datetime.fromtimestamp(int(expiry_date) / 1000)
                elif isinstance(expiry_date, datetime):
                    exp_dt = expiry_date
            except Exception as e:
                logger.error(f"Error parsing expiry_date {expiry_date}: {e}")
                exp_dt = None

        try:
            return await self._execute(
                "INSERT INTO vouchers (user_id, phone, voucher_code, tier, device_brand, device_model, expiry_date) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (int(user_id), str(phone), str(voucher_code), str(tier) if tier else None, str(device_brand) if device_brand else None, str(device_model) if device_model else None, exp_dt)
            )
        except Exception as e:
            logger.error(f"❌ Failed to insert voucher into DB: {e}")
            return 0

    async def get_user_vouchers(self, user_id: int) -> list:
        try:
            return await self._fetch_all(
                "SELECT * FROM vouchers WHERE user_id = ? ORDER BY claimed_at DESC", (int(user_id),)
            )
        except Exception as e:
            logger.error(f"❌ Failed to fetch user vouchers for {user_id}: {e}")
            return []

    async def get_total_vouchers(self) -> int:
        try:
            row = await self._fetch_one("SELECT COUNT(*) as c FROM vouchers")
            if row:
                return int(row.get("c") or row.get("count") or 0)
            return 0
        except Exception as e:
            logger.error(f"❌ Failed to count total vouchers: {e}")
            return 0

    async def get_recent_vouchers(self, limit: int = 10) -> list:
        try:
            return await self._fetch_all(
                "SELECT v.*, u.username, u.first_name FROM vouchers v "
                "LEFT JOIN users u ON v.user_id = u.user_id "
                "ORDER BY v.claimed_at DESC LIMIT ?",
                (limit,)
            )
        except Exception as e:
            logger.error(f"❌ Failed to fetch recent vouchers: {e}")
            return []

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
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            (key, str(value))
        )

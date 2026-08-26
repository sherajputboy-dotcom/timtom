#!/usr/bin/env python3
"""Bot Configuration — MoneyZone Edition"""

import os
import json

# ============= BOT CONFIG =============
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ADMIN_IDS: set via env var as comma-separated IDs (e.g. "123456,789012")
# or as JSON array (e.g. "[123456, 789012]")
_admin_raw = os.getenv("ADMIN_IDS", "")
if _admin_raw:
    try:
        parsed = json.loads(_admin_raw)
        ADMIN_IDS = parsed if isinstance(parsed, list) else [parsed]
    except (json.JSONDecodeError, ValueError):
        ADMIN_IDS = [int(x.strip()) for x in _admin_raw.split(",") if x.strip().isdigit()]
else:
    ADMIN_IDS = []  # Set via ADMIN_IDS env var on Render!

# ============= DATABASE =============
DB_PATH = "bot_database.db"

# ============= LENSKART API =============
LENSKART_BASE_URL = "https://api-gateway.juno.lenskart.com"
DEFAULT_STEPS = 30000
DEFAULT_CAMPAIGN = "run-for-frame"

# ============= MESSAGES & BRANDING =============
BRAND_NAME = "💸 MONEYZONE REWARDS 💸"

DEFAULT_WELCOME_MSG = (
    "⚡ 💸 *WELCOME TO MONEYZONE OFFICIAL* 💸 ⚡\n"
    "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
    "🔥 *Claim Premium Lenskart Gift Vouchers Instantly!*\n"
    "👥 *Refer Friends & Multiply Your Earnings!*\n\n"
    "📌 *Mandatory Requirement:*\n"
    "To access our premium features, please join our official sponsor channels below, then click *✅ VERIFY ACCESS*."
)

DEFAULT_HELP_MSG = (
    "👑 💸 *MONEYZONE SUPPORT & GUIDE* 💸 👑\n"
    "▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n\n"
    "🔹 *1. Join Channels:* Click the sponsor channel links & join.\n"
    "🔹 *2. Click Verify:* Tap the *✅ VERIFY ACCESS* button.\n"
    "🔹 *3. Claim Vouchers:* Tap *⚡ 🏃 CLAIM LENSKART VOUCHER*, enter your phone number & OTP.\n"
    "🔹 *4. Refer & Earn:* Copy your unique referral link to build your team!\n\n"
    "💬 *24/7 Admin Support Available!*"
)

# ============= REFERRAL =============
REFERRAL_PREFIX = "ref_"

# ============= PAGINATION =============
ITEMS_PER_PAGE = 10

# ============= RATE LIMITS & CACHE =============
BROADCAST_DELAY = 0.05  # seconds between messages during broadcast
CHANNEL_CACHE_TTL = 45  # cache channel membership check for 45s for ultra-fast performance

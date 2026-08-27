#!/usr/bin/env python3
"""Bot Configuration — Lenskart Bypass Bot (Powered by MoneyZone)"""

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
CLAIM_COST_POINTS = 20
REFERRAL_BONUS_POINTS = 50
WELCOME_BONUS_POINTS = 20

# ============= MESSAGES & BRANDING =============
BRAND_NAME = "🕶️ Lenskart Reward Bypass Bot"
CREDIT_FOOTER = "⚡ *Created by MoneyZone*"

DEFAULT_WELCOME_MSG = (
    "🕶️ *WELCOME TO LENSKART REWARD BOT* 🕶️\n\n"
    "🏃 *Bypass 30,000 steps & claim Lenskart Gift Vouchers instantly!*\n\n"
    "💰 *Points Balance System:*\n"
    "🎁 Welcome Bonus: *20 Points*\n"
    "🏃 Claim Cost: *20 Points / run*\n"
    "👥 Referral Reward: *50 Points / friend*\n\n"
    "📌 *Mandatory Step:*\n"
    "Join our required channels below, then click *✅ Verify Access* to unlock!"
)

DEFAULT_HELP_MSG = (
    "ℹ️ *LENSKART BOT HELP & GUIDE*\n\n"
    "1️⃣ *Join Channels:* Join all required channels listed in the verify card.\n"
    "2️⃣ *Verify:* Tap *✅ Verify Access* to confirm membership.\n"
    "3️⃣ *Claim Reward:* Tap *🏃 Claim Reward* (Costs 20 Points). Enter your mobile number & OTP.\n"
    "4️⃣ *Earn Points:* Share your referral link! Earn *50 Points* for every friend who joins!\n\n"
    "💬 Contact admin for support.\n\n"
    "⚡ *Created by MoneyZone*"
)

# ============= REFERRAL =============
REFERRAL_PREFIX = "ref_"

# ============= PAGINATION =============
ITEMS_PER_PAGE = 10

# ============= RATE LIMITS & CACHE =============
BROADCAST_DELAY = 0.05  # seconds between messages during broadcast
CHANNEL_CACHE_TTL = 45  # cache channel membership check for 45s

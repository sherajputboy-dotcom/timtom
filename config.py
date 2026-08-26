#!/usr/bin/env python3
"""Bot Configuration"""

import os
import json

# ============= BOT CONFIG =============
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ADMIN_IDS: set via env var as comma-separated IDs (e.g. "123456,789012")
# or as JSON array (e.g. "[123456, 789012]")
_admin_raw = os.getenv("ADMIN_IDS", "")
if _admin_raw:
    try:
        ADMIN_IDS = json.loads(_admin_raw)  # try JSON
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

# ============= MESSAGES =============
DEFAULT_WELCOME_MSG = (
    "👋 *Welcome to {bot_name}!*\n\n"
    "🏃 Claim your Lenskart rewards!\n"
    "👥 Refer friends & earn!\n\n"
    "📌 First, join our channels below, then click ✅ Verify."
)

DEFAULT_HELP_MSG = (
    "ℹ️ *How to use this bot:*\n\n"
    "1️⃣ Join all required channels\n"
    "2️⃣ Click ✅ Verify\n"
    "3️⃣ Access the main menu\n"
    "4️⃣ Claim rewards or refer friends!\n\n"
    "💬 Contact admin for support."
)

# ============= REFERRAL =============
REFERRAL_PREFIX = "ref_"

# ============= PAGINATION =============
ITEMS_PER_PAGE = 10

# ============= RATE LIMITS =============
BROADCAST_DELAY = 0.05  # seconds between messages during broadcast

#!/usr/bin/env python3
"""
🕶️ LENSKART REWARD BYPASS BOT (Powered by MoneyZone)
Entry point — registers all handlers, health server + self-ping keepalive + polling.
"""

import os
import asyncio
import logging
import threading
import urllib.request
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

from config import BOT_TOKEN, ADMIN_IDS
from database import Database

# Handlers
from handlers.start import start_command
from handlers.verify import verify_callback
from handlers.user_menu import (
    menu_callback, show_profile, show_referrals,
    show_vouchers, show_leaderboard, show_help
)
from handlers.lenskart import claim_callback, handle_text_input as lenskart_text
from handlers.admin import admin_command, admin_callback, admin_text_handler, addpoints_command

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ===================== HEALTH CHECK & KEEP-ALIVE SERVER =====================

class HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for Render health checks & keep-alive."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><head><title>Lenskart Reward Bot</title></head>"
            b"<body style='font-family:sans-serif; background:#0d1117; color:#58a6ff; text-align:center; padding:50px;'>"
            b"<h1>&#128083; LENSKART REWARD BYPASS BOT &#128083;</h1>"
            b"<p style='font-size:18px; color:#7ee787;'>&#9989; System Operational | Created by MoneyZone</p>"
            b"<div style='display:inline-block; border:1px solid #30363d; padding:20px; border-radius:10px; background:#161b22;'>"
            b"<p>&#9889; High Concurrency Engine: <strong>ENABLED (WAL)</strong></p>"
            b"<p>&#9889; Render Keep-Alive: <strong>ACTIVE</strong></p>"
            b"</div>"
            b"</body></html>"
        )

    def log_message(self, format, *args):
        pass


def start_health_server():
    """Start HTTP health-check server on $PORT (default 10000)."""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"🌐 Health server running on port {port}")
    server.serve_forever()


def keep_alive_worker():
    """Self-ping worker to prevent Render web service from sleeping."""
    url = os.environ.get("RENDER_EXTERNAL_URL")
    port = int(os.environ.get("PORT", 10000))
    ping_target = url if url else f"http://127.0.0.1:{port}"

    logger.info(f"⚡ Keep-alive worker started for target: {ping_target}")
    time.sleep(15)
    while True:
        try:
            req = urllib.request.Request(ping_target, headers={"User-Agent": "LenskartBot-KeepAlive/1.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    logger.debug("⚡ Keep-alive ping successful")
        except Exception as e:
            logger.debug(f"⚡ Keep-alive ping note: {e}")
        time.sleep(300)  # Ping every 5 minutes


# ===================== MESSAGE ROUTER =====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all text messages (including persistent reply keyboard buttons)."""
    user = update.effective_user
    if not user or not update.message:
        return

    text = (update.message.text or "").strip()

    # Direct check for /start command
    if text.lower().startswith("/start"):
        context.args = text.split()[1:] if len(text.split()) > 1 else []
        await start_command(update, context)
        return

    # Direct check for /cancel command
    if text.lower() in ("/cancel", "cancel", "❌ cancel"):
        context.user_data["action"] = None
        context.user_data["admin_action"] = None
        context.user_data["pending_phone"] = None
        from utils.keyboard import main_reply_keyboard
        await update.message.reply_text("❌ Action cancelled.", reply_markup=main_reply_keyboard())
        return

    # Admin text input
    if user.id in ADMIN_IDS:
        admin_action = context.user_data.get("admin_action")
        if admin_action:
            result = await admin_text_handler(update, context)
            if result is not False:
                return

    # Lenskart flow & Reply Keyboard triggers
    result = await lenskart_text(update, context)
    if result:
        return

    # Unrecognized text fallback with main reply keyboard
    from utils.keyboard import main_reply_keyboard
    await update.message.reply_text(
        "🕶️ *LENSKART REWARD BOT*\n\n"
        "🤔 Command not recognized.\n"
        "Press /start or tap a button from the menu below!",
        reply_markup=main_reply_keyboard(),
        parse_mode="Markdown"
    )


# ===================== CALLBACK ROUTER =====================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all callback queries to correct handler."""
    query = update.callback_query
    data = query.data

    if data == "noop":
        await query.answer()
        return

    # Verify channels
    if data == "verify_channels":
        await verify_callback(update, context)
        return

    # User menu callbacks
    if data in ("main_menu", "user_profile", "user_referrals",
                "user_vouchers", "user_leaderboard", "user_help"):
        await menu_callback(update, context)
        return

    # Claim reward
    if data == "user_claim":
        await claim_callback(update, context)
        return

    # Admin callbacks
    if data.startswith("admin_"):
        await admin_callback(update, context)
        return

    await query.answer("❓ Unknown action")


# ===================== LIFECYCLE =====================

async def post_init(application: Application):
    """Run after bot initialization — setup database."""
    db = Database()
    await db.init()
    application.bot_data["db"] = db
    logger.info("✅ Database & WAL mode initialized")

    bot_me = await application.bot.get_me()
    logger.info(f"🤖 Lenskart Bot: @{bot_me.username} ({bot_me.first_name})")


async def post_shutdown(application: Application):
    """Cleanup on shutdown."""
    db = application.bot_data.get("db")
    if db:
        await db.close()
    logger.info("👋 Bot shut down cleanly.")


# ===================== MAIN =====================

def main():
    """Start the bot + health server + keepalive."""
    print("=" * 60)
    print("🕶️ LENSKART REWARD BYPASS BOT (Powered by MoneyZone)")
    print(f"👤 Admin IDs: {ADMIN_IDS}")
    print("=" * 60)

    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n❌ ERROR: Set BOT_TOKEN in config.py or environment!")
        print("   Get token from @BotFather on Telegram")
        return

    if not ADMIN_IDS:
        print("\n⚠️ WARNING: No admin IDs set!")
        print("   Set ADMIN_IDS env var with your Telegram user ID")
        print("   Get your ID from @userinfobot on Telegram")

    # Start health-check web server
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()

    # Start keep-alive thread to prevent Render sleep
    keep_alive_thread = threading.Thread(target=keep_alive_worker, daemon=True)
    keep_alive_thread.start()

    # Build application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .concurrent_updates(True)
        .build()
    )

    # Register handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler(["addpoints", "addcredits"], addpoints_command))
    application.add_handler(CommandHandler(["claim", "run"], claim_callback))
    application.add_handler(CommandHandler(["vouchers", "myvouchers", "vault"], show_vouchers))
    application.add_handler(CommandHandler(["refer", "referral", "ref"], show_referrals))
    application.add_handler(CommandHandler(["profile", "me", "points", "balance"], show_profile))
    application.add_handler(CommandHandler(["leaderboard", "top"], show_leaderboard))
    application.add_handler(CommandHandler(["help", "info"], show_help))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(~filters.COMMAND, handle_message))

    print("\n✅ Lenskart Bot Started! High-Concurrency mode ACTIVE.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

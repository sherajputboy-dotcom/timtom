#!/usr/bin/env python3
"""
🤖 Lenskart Advanced Telegram Bot
Entry point — registers all handlers, starts health server + polling.
Runs a lightweight HTTP health-check server on $PORT so Render's
free-tier Web Service stays alive, while the bot polls Telegram.
"""

import os
import asyncio
import logging
import threading
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
from handlers.user_menu import menu_callback
from handlers.lenskart import claim_callback, handle_text_input as lenskart_text
from handlers.admin import admin_command, admin_callback, admin_text_handler

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# ===================== HEALTH CHECK SERVER =====================
# Render expects a web service to bind to $PORT. This lightweight
# server satisfies that requirement while the bot polls Telegram.

class HealthHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for Render health checks."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(
            b"<html><body>"
            b"<h1>&#129302; Lenskart Bot</h1>"
            b"<p>Bot is running!</p>"
            b"<ul>"
            b"<li>Status: <strong>ONLINE</strong></li>"
            b"<li>Type: Telegram Polling</li>"
            b"</ul>"
            b"</body></html>"
        )

    def log_message(self, format, *args):
        """Suppress default request logs to keep console clean."""
        pass


def start_health_server():
    """Start HTTP health-check server on $PORT (default 10000)."""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    logger.info(f"🌐 Health server running on port {port}")
    server.serve_forever()


# ===================== MESSAGE ROUTER =====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all text messages to the correct handler based on user state."""
    user = update.effective_user
    if not user:
        return

    # Admin text input (search user, add channel, broadcast, etc.)
    if user.id in ADMIN_IDS:
        admin_action = context.user_data.get("admin_action")
        if admin_action:
            result = await admin_text_handler(update, context)
            if result is not False:
                return

    # Lenskart flow (phone input, OTP input)
    result = await lenskart_text(update, context)
    if result:
        return

    # Unrecognized text — show hint
    await update.message.reply_text(
        "🤔 I didn't understand that.\n\n"
        "Use /start to see the main menu."
    )


# ===================== CALLBACK ROUTER =====================

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Route all callback queries to correct handler."""
    data = update.callback_query.data

    if data == "noop":
        await update.callback_query.answer()
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

    # Unknown callback
    await update.callback_query.answer("❓ Unknown action")


# ===================== LIFECYCLE =====================

async def post_init(application: Application):
    """Run after bot initialization — setup database."""
    db = Database()
    await db.init()
    application.bot_data["db"] = db
    logger.info("✅ Database initialized")

    bot_me = await application.bot.get_me()
    logger.info(f"🤖 Bot: @{bot_me.username} ({bot_me.first_name})")


async def post_shutdown(application: Application):
    """Cleanup on shutdown."""
    logger.info("👋 Bot shutting down...")


# ===================== MAIN =====================

def main():
    """Start the bot + health server."""
    print("=" * 60)
    print("🤖 LENSKART ADVANCED TELEGRAM BOT")
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

    # Start health-check web server in background thread
    # (Render needs a process listening on $PORT)
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()

    # Build application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Register handlers (order matters!)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("\n✅ Bot started! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

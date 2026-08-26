# 🤖 Lenskart Advanced Telegram Bot

A feature-rich Telegram bot for the Lenskart "Run For Frame" campaign with full admin panel, force channel join, referral system, and more.

## Features

- 🏃 **Claim Lenskart Rewards** — Automated step spoofing & voucher claiming
- 📢 **Force Channel Join** — Users must join channels before accessing bot
- 👥 **Refer & Earn** — Unique referral links with tracking & leaderboard
- 🛡️ **Full Admin Panel** — Stats, user management, broadcast, campaign control
- 💾 **SQLite Persistence** — Data survives restarts
- 📣 **Broadcast System** — Send messages to all users with live progress

## Deployment on Render

1. Push to GitHub
2. Go to [render.com](https://render.com) → **New** → **Background Worker**
3. Connect this repo
4. Set environment variables:
   - `BOT_TOKEN` — from [@BotFather](https://t.me/BotFather)
   - `ADMIN_IDS` — your Telegram user ID (e.g. `123456789`)
5. Deploy!

## Local Setup

```bash
pip install -r requirements.txt
export BOT_TOKEN="your_token_here"
export ADMIN_IDS="your_telegram_id"
python bot.py
```

## Commands

| Command | Description |
|---------|-------------|
| `/start` | Start bot + registration |
| `/admin` | Open admin panel (admins only) |

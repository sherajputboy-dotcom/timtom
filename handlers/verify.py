#!/usr/bin/env python3
"""Channel verification handler — Lenskart Reward Bot (Super Referral Enabled)"""

from telegram import Update
from telegram.ext import ContextTypes
from middleware.force_join import clear_user_membership_cache, is_user_channel_member
from utils.keyboard import main_reply_keyboard, force_join_keyboard
from config import CREDIT_FOOTER, REFERRAL_BONUS_POINTS


async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ✅ Verify button — re-check all channel memberships and award referral points."""
    query = update.callback_query
    user = update.effective_user
    db = context.bot_data["db"]

    # Purge cache for live check
    clear_user_membership_cache(user.id)

    channels = await db.get_channels()
    if not channels:
        ref_info = await db.verify_user_and_reward_referrer(user.id)
        if ref_info:
            try:
                await context.bot.send_message(
                    chat_id=ref_info["referrer_id"],
                    text=(
                        f"🎉 *REFERRAL VERIFIED!* 🎉\n\n"
                        f"👤 *{user.first_name or 'Someone'}* completed channel verification!\n"
                        f"💰 Bonus Awarded: *+{REFERRAL_BONUS_POINTS} Points*\n"
                        f"📊 Total Referrals: `{ref_info['total_referrals']}`\n"
                        f"💳 Your New Balance: `{ref_info['new_points']} Points`"
                    ),
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        await query.answer("🎉 Verification Successful!", show_alert=True)
        points = await db.get_user_points(user.id)
        
        await query.edit_message_text(
            f"✅ *Verification Complete!* 🎉\n\n"
            f"💰 *Your Balance:* `{points} Points`\n\n"
            f"Use the bottom menu to navigate!\n\n{CREDIT_FOOTER}",
            parse_mode="Markdown"
        )
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text="📱 Menu Unlocked!",
                reply_markup=main_reply_keyboard()
            )
        except Exception:
            pass
        return

    not_joined = []
    joined_ids = set()
    for ch in channels:
        joined = await is_user_channel_member(context.bot, ch["channel_id"], user.id)
        if joined:
            joined_ids.add(ch["channel_id"])
        else:
            not_joined.append(ch)

    if not_joined:
        await query.answer("❌ You haven't joined all channels yet!", show_alert=True)
        names = [ch.get("channel_title") or "Sponsor Channel" for ch in not_joined]
        text = (
            "⚠️ *VERIFICATION INCOMPLETE*\n\n"
            "You still need to join these channels:\n"
        )
        for name in names:
            text += f"  🔴 `{name}`\n"
        text += "\nClick the channel buttons above to join, then tap *🔄 Refresh / Verify Status* again."

        markup = force_join_keyboard(channels, joined_ids)
        try:
            await query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
        except Exception:
            pass
    else:
        # Mark verified & award referral points to referrer
        ref_info = await db.verify_user_and_reward_referrer(user.id)
        if ref_info:
            try:
                await context.bot.send_message(
                    chat_id=ref_info["referrer_id"],
                    text=(
                        f"🎉 *REFERRAL VERIFIED!* 🎉\n\n"
                        f"👤 *{user.first_name or 'Someone'}* completed channel verification!\n"
                        f"💰 Bonus Awarded: *+{REFERRAL_BONUS_POINTS} Points*\n"
                        f"📊 Total Referrals: `{ref_info['total_referrals']}`\n"
                        f"💳 Your New Balance: `{ref_info['new_points']} Points`"
                    ),
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        await query.answer("🎉 Verified! All channels joined!", show_alert=True)
        
        points = await db.get_user_points(user.id)
        await query.edit_message_text(
            f"🕶️ *LENSKART BOT DASHBOARD* 🕶️\n\n"
            f"🎉 *Welcome, {user.first_name or 'User'}!*\n"
            f"💳 *Points Balance:* `{points} Points`\n"
            f"🏃 *Claim Cost:* `20 Points`\n\n"
            f"Use the bottom menu to navigate!\n\n{CREDIT_FOOTER}",
            parse_mode="Markdown"
        )
        try:
            await context.bot.send_message(
                chat_id=user.id,
                text="📱 Persistent Menu Unlocked!",
                reply_markup=main_reply_keyboard()
            )
        except Exception:
            pass

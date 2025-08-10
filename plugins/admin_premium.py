from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message
from datetime import datetime, timedelta
import pytz
from utils import premium_user, update_verify_status
from info import ADMINS, LOG_CHANNEL  
from database.users_chats_db import db

# Configurations
USE_12_HOUR_FORMAT = True

@Client.on_message(filters.command("addpremium") & filters.user(ADMINS))
async def add_premium(client, message: Message):
    try:
        args = message.text.split()

        if len(args) < 2:
            return await message.reply("❌ Usage: `/addpremium user_id [days]`", quote=True)

        user_id = int(args[1])
        days = int(args[2]) if len(args) > 2 else 30
        hours = days * 24

        expiry_date, expiry_time = await premium_user(client, user_id, hours)

        if not expiry_date:
            return await message.reply("❌ Failed to upgrade user to premium.", quote=True)
        await message.reply(
            f"✅ Premium added to user `{user_id}` for {days} days.\n"
            f"⏳ Expires on **{expiry_date} {expiry_time}**."
        )
        await client.send_message(
            chat_id=LOG_CHANNEL,
            text=(
                f"📢 **Premium Activated**\n\n"
                f"👤 User ID: `{user_id}`\n"
                f"⏳ Valid for: `{days} days`\n"
                f"🕒 Expires on: `{expiry_date} {expiry_time}`\n"
                f"🔧 Activated by: [{message.from_user.first_name}](tg://user?id={message.from_user.id})"
            )
        )
        await client.send_message(
            chat_id=user_id,
            text=(
                f"🎉 Congratulations!\n\n"
                f"💎 You’ve been upgraded to **Premium** for **{days} days**.\n"
                f"⏳ Expires on: `{expiry_date} {expiry_time}`\n\n"
                f"Enjoy your ad-free, enhanced experience! 🥳"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 Check Premium", callback_data="check_premium")],
                [InlineKeyboardButton("📩 Contact Support", url="https://t.me/MyselfPrincess")]
            ])
        )

    except Exception as e:
        await message.reply(f"⚠️ Error: `{str(e)}`", quote=True)
        
@Client.on_message(filters.command("removepremium") & filters.user(ADMINS))
async def remove_premium(client, message: Message):
    try:
        args = message.text.split()
        if len(args) < 2:
            return await message.reply("❌ Usage: /removepremium user_id")
        user_id = int(args[1])
        date_temp = "1999-12-31"
        time_temp = "23:59:59"
        await update_verify_status(client, user_id, date_temp, time_temp)
        await message.reply(f"✅ Removed premium for user `{user_id}`.")
    except Exception as e:
        await message.reply(f"⚠️ Error: `{e}`")

@Client.on_message(filters.command(["checkpremium", "checkverification"]))
async def check_premium(client, message: Message):
    try:
        args = message.text.split()
        sender_id = message.from_user.id
        sender_name = message.from_user.first_name
        is_admin = sender_id in ADMINS

        # Determine target user
        if len(args) > 1:
            if not is_admin:
                return await message.reply("❌ You are not allowed to check other users' status.")
            user_id = int(args[1])
            name_display = ""
        else:
            user_id = sender_id
            name_display = " (Myself)"

        # Fetch data from DB
        data = await db.get_verified(user_id)
        date_str = data.get('date', "1999-12-31")
        time_str = data.get('time', "23:59:59")
        tz = pytz.timezone("Asia/Kolkata")

        # Handle unverified
        if date_str == "1999-12-31" and time_str == "23:59:59":
            return await message.reply(f"🟡 User: `{user_id}`{name_display}\n\nNot verified yet.")

        # Parse & calculate
        verified_dt = tz.localize(datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M:%S"))
        
        # Expiry times
        verification_expiry = verified_dt + timedelta(hours=12)
        premium_expiry = verified_dt  # Change if premium expiry differs

        now = datetime.now(tz)

        # Active statuses
        verification_active = verification_expiry > now
        premium_active = premium_expiry > now

        # Time left calculations
        def time_left_str(expiry_dt):
            if expiry_dt <= now:
                return "Expired"
            td = expiry_dt - now
            hrs, rem = divmod(int(td.total_seconds()), 3600)
            mins, secs = divmod(rem, 60)
            return f"{hrs}h {mins}m {secs}s"

        # Formatting dates
        def fmt(dt):
            return dt.strftime("%d/%m/%Y, %I:%M %p") if USE_12_HOUR_FORMAT else dt.strftime("%d/%m/%Y, %H:%M")

        # Reply
        await message.reply(
            f"👤 User: `{user_id}`{name_display}\n\n"
            f"{'✅' if verification_active else '❌'} Verification: {'Active' if verification_active else 'Expired'}\n"
            f"🗓️ Last On: {fmt(verified_dt)}\n"
            f"📌 Expires: {fmt(verification_expiry)}\n"
            f"⏳ Time Left: {time_left_str(verification_expiry)}\n\n"
            f"{'✅' if premium_active else '❌'} Premium: {'Active' if premium_active else 'Expired'}\n"
            f"🗓️ Last On: {fmt(verified_dt)}\n"
            f"📌 Expires: {fmt(premium_expiry)}\n"
            f"⏳ Time Left: {time_left_str(premium_expiry)}"
        )

    except Exception as e:
        await message.reply(f"⚠️ Error: `{e}`")
        
        
@Client.on_message(filters.command("buypremium") & filters.private)
async def buy_premium_info(client, message):
    await message.reply(
        "💎 **Buy Premium Access**\n\n"
        "✨ Benefits:\n"
        "• Ad-Free Experience\n"
        "• Early Access to Features\n"
        "• Priority Support\n\n"
        "💰 Pricing:\n"
        "• 30 Days – ₹49\n"
        "• 90 Days – ₹99\n"
        "• Lifetime – ₹199\n\n"
        "📲 Contact @YourSupportUsername to upgrade."
    )
    

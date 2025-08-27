from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)
from datetime import datetime, timedelta
import pytz

from info import ADMINS, LOG_CHANNEL 
from database.users_chats_db import db


TZ = pytz.timezone("Asia/Kolkata")


# ------------------------------
# HELPERS
# ------------------------------
def make_check_button():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("✨ Check Premium", callback_data="check_premium_user")]]
    )


def make_buy_buttons():
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💎 Buy Premium", callback_data="buy_premium")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")],
        ]
    )


# Shared function to show premium status (works for both commands and callbacks)
async def show_premium_status(client, reply_target, user_id: int, cq: CallbackQuery = None):
    if await db.is_premium(user_id):
        days = await db.get_premium_days_left(user_id) or 0
        try:
            expiry = await db.get_premium_expiry(user_id)
            expiry_str = expiry.astimezone(TZ).strftime("%d %B %Y, %I:%M %p")
        except Exception:
            expiry_str = "Unknown"

        text = (
            f"🌟 **Premium Status** 🌟\n\n"
            f"👤 User ID: `{user_id}`\n"
            f"✨ Status: ✅ Active\n"
            f"⏳ Days Left: **{days}**\n"
            f"📅 Expiry Date: **{expiry_str}**\n\n"
            f"🚀 Enjoy your premium benefits!"
        )
        reply_markup = None

    else:
        text = (
            "😢 You are not a premium user.\n\n"
            "💡 Upgrade now to unlock all premium features!"
        )
        reply_markup = make_buy_buttons()

    if cq:
        try:
            await cq.answer()
        except Exception:
            pass
        await cq.message.reply_text(text, reply_markup=reply_markup, quote=True)
    else:
        await reply_target.reply_text(text, reply_markup=reply_markup, quote=True)


# ------------------------------
# LOG FUNCTION
# ------------------------------
async def log_premium_action(client, action: str, target_user: int, days: int = None, admin: int = None):
    """
    Logs premium actions with detailed info:
    action: "add", "edit", "extend", "remove"
    """
    try:
        now = datetime.now(TZ).strftime("%d %B %Y, %I:%M %p")

        # fetch user and admin info
        try:
            target = await client.get_users(target_user)
            target_name = f"{target.first_name or ''} {target.last_name or ''}".strip()
            target_username = f"@{target.username}" if target.username else "❌"
        except Exception:
            target_name, target_username = "Unknown", "❌"

        try:
            admin_user = await client.get_users(admin)
            admin_name = f"{admin_user.first_name or ''} {admin_user.last_name or ''}".strip()
            admin_username = f"@{admin_user.username}" if admin_user.username else "❌"
        except Exception:
            admin_name, admin_username = "Unknown", "❌"

        # get expiry & days left (after update)
        try:
            expiry = await db.get_premium_expiry(target_user)
            expiry_str = expiry.astimezone(TZ).strftime("%d %B %Y, %I:%M %p")
        except Exception:
            expiry_str = "Unknown"

        try:
            days_left = await db.get_premium_days_left(target_user) or 0
        except Exception:
            days_left = "?"

        if action == "add":
            text = (
                f"#PremiumAdded ✅\n\n"
                f"👤 **User:** {target_name} (`{target_user}`)\n"
                f"🔗 Username: {target_username}\n\n"
                f"📅 Days Added: **{days}**\n"
                f"⏳ Days Left: **{days_left}**\n"
                f"🗓 Expiry: **{expiry_str}**\n\n"
                f"🛠 **By Admin:** {admin_name} (`{admin}`)\n"
                f"🔗 Username: {admin_username}\n\n"
                f"📌 Time: {now}"
            )
        elif action == "edit":
            text = (
                f"#PremiumEdited ✏️\n\n"
                f"👤 **User:** {target_name} (`{target_user}`)\n"
                f"🔗 Username: {target_username}\n\n"
                f"🆕 New Days: **{days}**\n"
                f"⏳ Days Left: **{days_left}**\n"
                f"🗓 Expiry: **{expiry_str}**\n\n"
                f"🛠 **By Admin:** {admin_name} (`{admin}`)\n"
                f"🔗 Username: {admin_username}\n\n"
                f"📌 Time: {now}"
            )
        elif action == "extend":
            text = (
                f"#PremiumExtended ➕\n\n"
                f"👤 **User:** {target_name} (`{target_user}`)\n"
                f"🔗 Username: {target_username}\n\n"
                f"➕ Added Days: **{days}**\n"
                f"⏳ Days Left: **{days_left}**\n"
                f"🗓 Expiry: **{expiry_str}**\n\n"
                f"🛠 **By Admin:** {admin_name} (`{admin}`)\n"
                f"🔗 Username: {admin_username}\n\n"
                f"📌 Time: {now}"
            )
        elif action == "remove":
            text = (
                f"#PremiumRemoved 🚫\n\n"
                f"👤 **User:** {target_name} (`{target_user}`)\n"
                f"🔗 Username: {target_username}\n\n"
                f"⏳ Days Left Before Removal: **{days_left}**\n"
                f"🗓 Expiry: **{expiry_str}**\n\n"
                f"🛠 **By Admin:** {admin_name} (`{admin}`)\n"
                f"🔗 Username: {admin_username}\n\n"
                f"📌 Time: {now}"
            )
        else:
            text = f"#UnknownAction ❓\nAdmin `{admin}` → User `{target_user}` at {now}"

        await client.send_message(LOG_CHANNEL, text)

    except Exception:
        pass


# ------------------------------
# 1) Add Premium (Admin only)
# ------------------------------
@Client.on_message(filters.command("addpremium") & filters.user(ADMINS))
async def cmd_add_premium(client: Client, message: Message):
    try:
        args = message.text.split()
        if len(args) < 3:
            return await message.reply("⚠️ Usage: /addpremium user_id days", quote=True)

        user_id = int(args[1])
        input_days = int(args[2])
        if input_days <= 0:
            return await message.reply("⚠️ Days must be a positive number.", quote=True)

        if await db.is_premium(user_id):
            days_left = await db.get_premium_days_left(user_id) or 0
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "➕ Add More Days", callback_data=f"add_days:{user_id}:{input_days}"
                        ),
                        InlineKeyboardButton(
                            "✏️ Edit Premium Days", callback_data=f"edit_days:{user_id}:{input_days}"
                        ),
                    ],
                    [InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")],
                ]
            )
            return await message.reply(
                (
                    f"⚠️ User `{user_id}` is already premium.\n"
                    f"⏳ Current days left: **{int(days_left)}**\n\n"
                    "Choose an action:"
                ),
                reply_markup=keyboard,
                quote=True,
            )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Confirm Add Premium", callback_data=f"confirm_add:{user_id}:{input_days}"
                    ),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_action"),
                ]
            ]
        )
        await message.reply(
            f"🤔 User `{user_id}` is **not premium**.\nDo you want to add premium for **{input_days} days**?",
            reply_markup=keyboard,
            quote=True,
        )

    except Exception as e:
        await message.reply(f"❌ Error: {e}", quote=True)


# ------------------------------
# 2) Remove Premium (Admin only)
# ------------------------------
@Client.on_message(filters.command("removepremium") & filters.user(ADMINS))
async def cmd_remove_premium(client: Client, message: Message):
    try:
        args = message.text.split()
        if len(args) < 2:
            return await message.reply("⚠️ Usage: /removepremium user_id", quote=True)

        user_id = int(args[1])
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Confirm Remove", callback_data=f"confirm_remove:{user_id}"),
                    InlineKeyboardButton("❌ Cancel", callback_data="cancel_action"),
                ]
            ]
        )
        await message.reply(
            f"⚠️ Are you sure you want to remove premium from user `{user_id}`?",
            reply_markup=keyboard,
            quote=True,
        )

    except Exception as e:
        await message.reply(f"❌ Error: {e}", quote=True)


# ------------------------------
# 3) Totals (Admin only)
# ------------------------------
@Client.on_message(filters.command("totalpremium") & filters.user(ADMINS))
async def cmd_total_premium(client: Client, message: Message):
    total = await db.total_premium_users_count()
    await message.reply(f"📊 Total premium users: **{total}**", quote=True)


@Client.on_message(filters.command("activepremium") & filters.user(ADMINS))
async def cmd_active_premium(client: Client, message: Message):
    active = await db.total_active_premium_users_count()
    await message.reply(f"🔥 Active premium users: **{active}**", quote=True)


# ------------------------------
# 4) Callback: admin actions (add_days / edit_days / confirm_add / confirm_remove)
# ------------------------------
@Client.on_callback_query(filters.regex(r"^(add_days|edit_days|confirm_add|confirm_remove):"))
async def handle_premium_actions(client: Client, cq: CallbackQuery):
    try:
        if cq.from_user.id not in ADMINS:
            await cq.answer("Not allowed.", show_alert=True)
            return

        data = cq.data.split(":")
        action = data[0]

        if action in ("add_days", "edit_days", "confirm_add"):
            target_user_id = int(data[1])
            new_days = int(data[2])
            if new_days <= 0:
                await cq.answer("Days must be positive.", show_alert=True)
                return

            check_markup = make_check_button()

            if action == "add_days":
                left = await db.get_premium_days_left(target_user_id) or 0
                total_days = int(left) + int(new_days)
                await db.add_premium(target_user_id, total_days)

                await cq.message.edit_text(
                    f"✅ Added **{new_days} days**.\n"
                    f"🆕 Premium for `{target_user_id}` is now **{total_days} days** from today."
                )
                await cq.answer("Premium extended!")

                await log_premium_action(client, "extend", target_user_id, new_days, cq.from_user.id)

                try:
                    await client.send_message(
                        target_user_id,
                        f"🎉 Your Premium has been extended!\n⏳ Total days left: **{total_days}**",
                        reply_markup=check_markup,
                    )
                except Exception:
                    pass

            elif action == "edit_days":
                await db.add_premium(target_user_id, new_days)
                await cq.message.edit_text(
                    f"✏️ Premium updated.\n🆕 User `{target_user_id}` now has **{new_days} days**."
                )
                await cq.answer("Premium updated!")

                await log_premium_action(client, "edit", target_user_id, new_days, cq.from_user.id)

                try:
                    await client.send_message(
                        target_user_id,
                        f"✏️ Your premium has been updated!\n⏳ New duration: **{new_days} days**",
                        reply_markup=check_markup,
                    )
                except Exception:
                    pass

            elif action == "confirm_add":
                await db.add_premium(target_user_id, new_days)
                await cq.message.edit_text(
                    f"✅ Premium activated!\n🆕 User `{target_user_id}` now has **{new_days} days**."
                )
                await cq.answer("Premium added!")

                await log_premium_action(client, "add", target_user_id, new_days, cq.from_user.id)

                try:
                    await client.send_message(
                        target_user_id,
                        f"🎉 Welcome to Premium!\n⏳ Active for **{new_days} days**.",
                        reply_markup=check_markup,
                    )
                except Exception:
                    pass

        elif action == "confirm_remove":
            target_user_id = int(data[1])
            await db.remove_premium(target_user_id)
            await cq.message.edit_text(f"🚫 Premium removed from `{target_user_id}`.")
            await cq.answer("Premium removed!")

            await log_premium_action(client, "remove", target_user_id, None, cq.from_user.id)

            try:
                await client.send_message(
                    target_user_id,
                    "⚠️ Your premium has been removed."
                )
            except Exception:
                pass

    except Exception as e:
        try:
            await cq.answer("Something went wrong.", show_alert=True)
        except Exception:
            pass
        try:
            await cq.message.edit_text(f"❌ Error: {e}")
        except Exception:
            pass


# ------------------------------
# 5) Cancel Button
# ------------------------------
@Client.on_callback_query(filters.regex(r"^cancel_action$"))
async def handle_cancel(client: Client, cq: CallbackQuery):
    try:
        await cq.answer("❌ Cancelled!")
    except Exception:
        pass
    try:
        await cq.message.edit_text("❌ Action cancelled.")
    except Exception:
        try:
            await cq.message.reply_text("❌ Action cancelled.")
        except Exception:
            pass


# ------------------------------
# 6) Buy Premium (user path)
# ------------------------------
@Client.on_callback_query(filters.regex(r"^buy_premium$"))
async def handle_buy_premium(client: Client, cq: CallbackQuery):
    try:
        await cq.answer()
    except Exception:
        pass

    await cq.message.reply_text(
        "💎 To buy premium, please contact Admin or use the available payment methods.",
        reply_markup=InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("👨‍💻 Contact Admin", url="https://t.me/YourAdminUsername")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_action")],
            ]
        ),
        quote=True,
    )


# ------------------------------
# 7) Check Premium (button)
# ------------------------------
@Client.on_callback_query(filters.regex(r"^check_premium_user$"))
async def handle_check_premium_btn(client: Client, cq: CallbackQuery):
    user_id = cq.from_user.id
    await show_premium_status(client, cq.message, user_id, cq)


# ------------------------------
# 8) Check Premium (command)
# ------------------------------
@Client.on_message(filters.command("checkpremium"))
async def handle_check_premium_cmd(client: Client, message: Message):
    user_id = message.from_user.id
    await show_premium_status(client, message, user_id)
    

from pyrogram import Client, filters, enums
from pyrogram.errors import ChatAdminRequired
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors.exceptions.bad_request_400 import MessageTooLong, PeerIdInvalid, UserNotParticipant, MediaEmpty, PhotoInvalidDimensions, WebpageMediaEmpty

from info import ADMINS, LOG_CHANNEL, SUPPORT_CHAT, UPDATE_CHANNEL, WELCOM_PIC, WELCOM_TEXT, IMDB_TEMPLATE
from utils import get_size, temp, extract_user, get_file_id, get_poster, humanbytes
from database.users_chats_db import db
from database.ia_filterdb import Media
from datetime import datetime
import asyncio 
from datetime import date, datetime
import pytz
from Script import script
import logging, re, asyncio, time, shutil, psutil, os, sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)


@Client.on_message(filters.new_chat_members & filters.group)
async def save_group(bot, message):
    new_members = [member.id for member in message.new_chat_members]
    if temp.ME in new_members:
        if not await db.get_chat(message.chat.id):
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz)
            time = now.strftime('%I:%M:%S %p')
            today = now.date()
            total_members = await bot.get_chat_members_count(message.chat.id)
            total_chats = await db.total_chat_count() + 1
            daily_chats = await db.daily_chats_count(today) + 1
            referrer = message.from_user.mention if message.from_user else "Anonymous"
            await bot.send_message(LOG_CHANNEL, script.LOG_TEXT_G.format(a=message.chat.title, b=message.chat.id, c=message.chat.username, d=total_members, e=total_chats, f=daily_chats, g=str(today), h=time, i=referrer, j=temp.U_NAME))
            await db.add_chat(message.chat.id, message.chat.title, message.chat.username)
            
        if message.chat.id in temp.BANNED_CHATS:
            buttons = [[
                InlineKeyboardButton('Support', url=SUPPORT_CHAT)
            ]]
            reply_markup = InlineKeyboardMarkup(buttons)
            message_text = '<b>CHAT NOT ALLOWED 🐞\n\nMy admins have restricted me from working here! If you want to know more about it, contact support.</b>'
            sent_message = await message.reply(
                text=message_text,
                reply_markup=reply_markup,
                parse_mode=enums.ParseMode.HTML
            )
            try:
                await sent_message.pin()
            except Exception as e:
                print(e)

            await bot.leave_chat(message.chat.id)
            return
            
    else:
        settings = await get_settings(message.chat.id)
        invite_link = None  # Initialize invite_link to None
    
        # Generate or get the invite link for this chat
        chat_id = message.chat.id
        if invite_link is None:
            invite_link = await db.get_chat_invite_link(chat_id)
            if invite_link is None:
                try:
                    invite_link = await bot.export_chat_invite_link(chat_id)
                except ChatAdminRequired:
                    invite_link = "Not an Admin"
                    return
                await db.save_chat_invite_link(chat_id, invite_link)
    
        if settings["welcome"]:
            for member in new_members:
                if temp.MELCOW.get('welcome') is not None:
                    try:
                        await temp.MELCOW['welcome'].delete()
                    except Exception as e:
                        print(e)

                mention = message.from_user.mention if message.from_user else message.chat.title
                temp.MELCOW['welcome'] = await message.reply_photo(
                    photo=MELCOW_PIC,
                    caption=script.MELCOW_ENG.format(a=mention, b=message.chat.title),
                    reply_markup=InlineKeyboardMarkup(
                        [
                            [
                                InlineKeyboardButton('Support Group', url=SUPPORT_CHAT),
                                InlineKeyboardButton('Updates Channel', url=UPDATE_CHANNEL)
                            ]
                        ]
                    ),
                    parse_mode=enums.ParseMode.HTML
                )
    
                # Log new members joining the group
                tz = pytz.timezone('Asia/Kolkata')
                now = datetime.now(tz)
                time = now.strftime('%I:%M:%S %p')
                date = now.date()
                total_members = await bot.get_chat_members_count(message.chat.id)
    
                for member in new_members:
                    await bot.send_message(LOG_CHANNEL, script.NEW_MEMBER.format(a=message.chat.title, b=message.chat.id, c=message.chat.username, d=total_members, e=invite_link, f=message.from_user.mention, g=message.from_user.id, h=message.from_user.username, i=date, j=time, k=temp.U_NAME), disable_web_page_preview=True)
        else:
            # Log new members joining the group
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz)
            time = now.strftime('%I:%M:%S %p')
            date = now.date()
            total_members = await bot.get_chat_members_count(message.chat.id)
    
            for member in new_members:
                await bot.send_message(LOG_CHANNEL, script.NEW_MEMBER.format(a=message.chat.title, b=message.chat.id, c=message.chat.username, d=total_members, e=invite_link, f=message.from_user.mention, g=message.from_user.id, h=message.from_user.username, i=date, j=time, k=temp.U_NAME), disable_web_page_preview=True)
        
        if settings["auto_delete"]:
            await asyncio.sleep(600)
            await temp.MELCOW['welcome'].delete()
            
            
# Handler for logging members leaving the group
@Client.on_message(filters.left_chat_member & filters.group)
async def goodbye(bot, message):
    invite_link = None  # Initialize invite_link to None

    # Generate or get the invite link for this chat
    chat_id = message.chat.id
    if invite_link is None:
        invite_link = await db.get_chat_invite_link(chat_id)
        if invite_link is None:
            try:
                invite_link = await bot.export_chat_invite_link(chat_id)
            except ChannelPrivate:
                invite_link = "Not an Admin"
                return 
            except ChatAdminRequired:
                invite_link = "Not an Admin"
                return
            await db.save_chat_invite_link(chat_id, invite_link)
    
    # Get total members count
    try:
        total_members = await bot.get_chat_members_count(message.chat.id)
    except ChannelPrivate:
        total_members = "Not an Admin"
        return

    # Get current time and date
    tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(tz)
    time = now.strftime('%I:%M:%S %p')
    date = now.date()
    
    # Check if chat exists in the database
    if await db.get_chat(message.chat.id):
        left_member = message.left_chat_member  # Get the left member info
        
        # Get bot's information
        bot_info = await bot.get_me()
        bot_id = bot_info.id
        
        if left_member.id == bot_id:  # Check if the left member is the bot itself
            await bot.send_message(LOG_CHANNEL, script.LEFT_MEMBER.format(a=message.chat.title, b=message.chat.id, c=message.chat.username, d=total_members, e=invite_link, f=left_member.mention, g=left_member.id, h=left_member.username, i=date, j=time, k=temp.U_NAME), disable_web_page_preview=True)
        else:
            await bot.send_message(LOG_CHANNEL, script.LEFT_MEMBER.format(a=message.chat.title, b=message.chat.id, c=message.chat.username, d=total_members, e=invite_link, f=left_member.mention, g=left_member.id, h=left_member.username, i=date, j=time, k=temp.U_NAME), disable_web_page_preview=True)


@Client.on_message(filters.command('leave') & filters.user(ADMINS))
async def leave_a_chat(bot, message):
    if len(message.command) == 1: return await message.reply('Gɪᴠᴇ Mᴇ A Cʜᴀᴛ Iᴅ')
    chat = message.command[1]
    try: chat = int(chat)
    except: chat = chat
    try:
        buttons = [[InlineKeyboardButton('Sᴜᴩᴩᴏʀᴛ', url=f'https://t.me/{SUPPORT_CHAT}')]]
        await bot.send_message(chat_id=chat, text='<b>Hᴇʟʟᴏ Fʀɪᴇɴᴅs, \nMʏ Aᴅᴍɪɴ Hᴀs Tᴏʟᴅ Mᴇ Tᴏ Lᴇᴀᴠᴇ Fʀᴏᴍ Gʀᴏᴜᴘ Sᴏ I Gᴏ! Iғ Yᴏᴜ Wᴀɴɴᴀ Aᴅᴅ Mᴇ Aɢᴀɪɴ Cᴏɴᴛᴀᴄᴛ Mʏ Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ</b>', reply_markup=InlineKeyboardMarkup(buttons))
        await bot.leave_chat(chat)
    except Exception as e:
        await message.reply(f'Eʀʀᴏʀ: {e}')


@Client.on_message(filters.command('disable') & filters.user(ADMINS))
async def disable_chat(bot, message):
    if len(message.command) == 1: return await message.reply('Gɪᴠᴇ Mᴇ A Cʜᴀᴛ Iᴅ')
    r = message.text.split(None)
    if len(r) > 2:
        reason = message.text.split(None, 2)[2]
        chat = message.text.split(None, 2)[1]
    else:
        chat = message.command[1]
        reason = "No Reason Provided"
    try:
        chat_ = int(chat)
    except:
        return await message.reply('Gɪᴠᴇ Mᴇ A Vᴀʟɪᴅ Cʜᴀᴛ ID')
    cha_t = await db.get_chat(int(chat_))
    if not cha_t:
        return await message.reply("Cʜᴀᴛ Nᴏᴛ Fᴏᴜɴᴅ Iɴ DB")
    if cha_t['is_disabled']:
        return await message.reply(f"Tʜɪꜱ Cʜᴀᴛ Is Aʟʀᴇᴅʏ  Dɪꜱᴀʙʟᴇᴅ:\nRᴇᴀꜱᴏɴ: <code> {cha_t['reason']} </code>")
    await db.disable_chat(int(chat_), reason)
    temp.BANNED_CHATS.append(int(chat_))
    await message.reply('Cʜᴀᴛ Sᴜᴄᴄᴇꜱꜰᴜʟʟʏ Dɪꜱᴀʙʟᴇᴅ')
    try:
        buttons = [[InlineKeyboardButton('Sᴜᴩᴩᴏʀᴛ', url=f'https://t.me/{SUPPORT_CHAT}')]]
        await bot.send_message(chat_id=chat_,  text=f'<b>Hᴇʟʟᴏ Fʀɪᴇɴᴅs, \nᴍʏ Aᴅᴍɪɴ Hᴀs Tᴏʟᴅ Mᴇ Tᴏ Lᴇᴀᴠᴇ Fʀᴏᴍ Gʀᴏᴜᴘ Sᴏ I Gᴏ! Iғ Yᴏᴜ Wᴀɴɴᴀ Aᴅᴅ Mᴇ Aɢᴀɪɴ Cᴏɴᴛᴀᴄᴛ Mʏ Sᴜᴘᴘᴏʀᴛ Gʀᴏᴜᴘ.</b> \nRᴇᴀꜱᴏɴ : <code>{reason}</code>', reply_markup=InlineKeyboardMarkup(buttons))
        await bot.leave_chat(chat_)
    except Exception as e:
        await message.reply(f"Eʀʀᴏʀ: {e}")


@Client.on_message(filters.command('enable') & filters.user(ADMINS))
async def re_enable_chat(bot, message):
    if len(message.command) == 1: return await message.reply('Gɪᴠᴇ Mᴇ A Cʜᴀᴛ Iᴅ')
    chat = message.command[1]
    try: chat_ = int(chat)
    except: return await message.reply('Gɪᴠᴇ Mᴇ A Vᴀʟɪᴅ Cʜᴀᴛ ID')
    sts = await db.get_chat(int(chat))
    if not sts: return await message.reply("Cʜᴀᴛ Nᴏᴛ Fᴏᴜɴᴅ Iɴ DB")
    if not sts.get('is_disabled'):
        return await message.reply('Tʜɪꜱ Cʜᴀᴛ Iꜱ Nᴏᴛ Yᴇᴛ Dɪꜱᴀʙʟᴇᴅ')
    await db.re_enable_chat(int(chat_))
    temp.BANNED_CHATS.remove(int(chat_))
    await message.reply("Cʜᴀᴛ Sᴜᴄᴄᴇꜱꜰᴜʟʟʏ Rᴇ-Eɴᴀʙʟᴇᴅ")


@Client.on_message(filters.command('stats') & filters.incoming)
async def get_ststs(bot, message):
    rju = await message.reply('<b>Pʟᴇᴀꜱᴇ Wᴀɪᴛ...</b>')
    total_users = await db.total_users_count()
    totl_chats = await db.total_chat_count()
    files = await Media.count_documents()
    size = await db.get_db_size()
    free = 536870912 - size
    size = get_size(size)
    free = get_size(free)
    await rju.edit(script.STATUS_TXT.format(files, total_users, totl_chats, size, free))


@Client.on_message(filters.command('invite') & filters.user(ADMINS))
async def gen_invite(bot, message):
    if len(message.command) == 1: return await message.reply('Gɪᴠᴇ Mᴇ A Cʜᴀᴛ Iᴅ')
    chat = message.command[1]
    try: chat = int(chat)
    except: return await message.reply('Gɪᴠᴇ Mᴇ A Vᴀʟɪᴅ Cʜᴀᴛ ID')
    try:
        link = await bot.create_chat_invite_link(chat)
    except ChatAdminRequired:
        return await message.reply("Iɴᴠɪᴛᴇ Lɪɴᴋ Gᴇɴᴇʀᴀᴛɪᴏɴ Fᴀɪʟᴇᴅ, Iᴀᴍ Nᴏᴛ Hᴀᴠɪɴɢ Sᴜғғɪᴄɪᴇɴᴛ Rɪɢʜᴛs")
    except Exception as e:
        return await message.reply(f'Eʀʀᴏʀ: {e}')
    await message.reply(f'Hᴇʀᴇ Iꜱ Yᴏᴜʀ Iɴᴠɪᴛᴇ Lɪɴᴋ: {link.invite_link}')


@Client.on_message(filters.command('ban_user') & filters.user(ADMINS))
async def ban_a_user(bot, message):
    if len(message.command) == 1: return await message.reply('Gɪᴠᴇ Mᴇ A Uꜱᴇʀ Iᴅ / Uꜱᴇʀɴᴀᴍᴇ')
    r = message.text.split(None)
    if len(r) > 2:
        reason = message.text.split(None, 2)[2]
        chat = message.text.split(None, 2)[1]
    else:
        chat = message.command[1]
        reason = "No reason Provided"
    try: chat = int(chat)
    except: pass
    try: k = await bot.get_users(chat)
    except PeerIdInvalid: return await message.reply("Tʜɪs Is Aɴ Iɴᴠᴀʟɪᴅ Usᴇʀ, Mᴀᴋᴇ Sᴜʀᴇ Iᴀ Hᴀᴠᴇ Mᴇᴛ Hɪᴍ Bᴇғᴏʀᴇ")
    except IndexError: return await message.reply("Tʜɪs Mɪɢʜᴛ Bᴇ A Cʜᴀɴɴᴇʟ, Mᴀᴋᴇ Sᴜʀᴇ Iᴛs A Usᴇʀ.")
    except Exception as e: return await message.reply(f'Eʀʀᴏʀ: {e}')
    else:
        jar = await db.get_ban_status(k.id)
        if jar['is_banned']: return await message.reply(f"{k.mention} Iꜱ Aʟʀᴇᴅʏ Bᴀɴɴᴇᴅ\nRᴇᴀꜱᴏɴ: {jar['ban_reason']}")
        await db.ban_user(k.id, reason)
        temp.BANNED_USERS.append(k.id)
        await message.reply(f"Sᴜᴄᴄᴇꜱꜰᴜʟʟʏ Bᴀɴɴᴇᴅ {k.mention}")

    
@Client.on_message(filters.command('unban_user') & filters.user(ADMINS))
async def unban_a_user(bot, message):
    if len(message.command) == 1: return await message.reply('Gɪᴠᴇ Mᴇ A Uꜱᴇʀ Iᴅ / Uꜱᴇʀɴᴀᴍᴇ')
    r = message.text.split(None)
    if len(r) > 2:
        reason = message.text.split(None, 2)[2]
        chat = message.text.split(None, 2)[1]
    else:
        chat = message.command[1]
        reason = "No reason Provided"
    try: chat = int(chat)
    except: pass
    try: k = await bot.get_users(chat)
    except PeerIdInvalid: return await message.reply("Tʜɪs Is Aɴ Iɴᴠᴀʟɪᴅ Usᴇʀ, Mᴀᴋᴇ Sᴜʀᴇ Iᴀ Hᴀᴠᴇ Mᴇᴛ Hɪᴍ Bᴇғᴏʀᴇ")
    except IndexError: return await message.reply("Tʜɪs Mɪɢʜᴛ Bᴇ A Cʜᴀɴɴᴇʟ, Mᴀᴋᴇ Sᴜʀᴇ Iᴛs A Usᴇʀ.")
    except Exception as e: return await message.reply(f'Eʀʀᴏʀ: {e}')
    else:
        jar = await db.get_ban_status(k.id)
        if not jar['is_banned']: return await message.reply(f"{k.mention} Iꜱ Nᴏᴛ Yᴇᴛ Bᴀɴɴᴇᴅ")
        await db.remove_ban(k.id)
        temp.BANNED_USERS.remove(k.id)
        await message.reply(f"Sᴜᴄᴄᴇꜱꜰᴜʟʟʏ Uɴʙᴀɴɴᴇᴅ {k.mention}")


@Client.on_message(filters.command('users') & filters.user(ADMINS))
async def list_users(bot, message):
    sps = await message.reply('Gᴇᴛᴛɪɴɢ Lɪꜱᴛ Oꜰ Uꜱᴇʀꜱ')
    users = await db.get_all_users()
    out = "Uꜱᴇʀꜱ Sᴀᴠᴇᴅ Iɴ DB Aʀᴇ:\n\n"
    async for user in users:
        out += f"<a href=tg://user?id={user['id']}>{user['name']}</a>\n"
    try:
        await sps.edit_text(out)
    except MessageTooLong:
        with open('users.txt', 'w+') as outfile:
            outfile.write(out)
        await message.reply_document('users.txt', caption="Lɪꜱᴛ Oꜰ Uꜱᴇʀꜱ")


@Client.on_message(filters.command('chats') & filters.user(ADMINS))
async def list_chats(bot, message):
    sps = await message.reply('Gᴇᴛᴛɪɴɢ Lɪꜱᴛ Oꜰ Cʜᴀᴛꜱ')
    chats = await db.get_all_chats()
    out = "Cʜᴀᴛꜱ Sᴀᴠᴇᴅ Iɴ DB Aʀᴇ:\n\n"
    async for chat in chats:
        username = chat['username']
        username = "private" if not username else "@" + username
        out += f"**- Tɪᴛʟᴇ:** `{chat['title']}`\n**- ID:** `{chat['id']}`\n**Uꜱᴇʀɴᴀᴍᴇ:** {username}\n"
    try:
        await sps.edit_text(out)
    except MessageTooLong:
        with open('chats.txt', 'w+') as outfile:
            outfile.write(out)
        await message.reply_document('chats.txt', caption="Lɪꜱᴛ Oꜰ Cʜᴀᴛꜱ")


@Client.on_message(filters.command("restart") & filters.user(ADMINS))
async def restart_bot(bot, msg):
    await msg.reply("Rᴇꜱᴛᴀᴛɪɴɢ........")
    await asyncio.sleep(2)
    await sts.delete()
    os.execl(sys.executable, sys.executable, *sys.argv)
    

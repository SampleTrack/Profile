import logging
import logging.config

# Get logging configurations
logging.config.fileConfig('logging.conf')
logging.getLogger().setLevel(logging.INFO)
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)

import asyncio
from pyrogram import Client, __version__, filters  # Added filters for debugging
from pyrogram.raw.all import layer
from database.ia_filterdb import Media
from database.users_chats_db import db
from info import SESSION, API_ID, API_HASH, BOT_TOKEN, PORT, LOG_CHANNEL
from utils import temp
from aiohttp import web
from datetime import date, datetime 
import pytz
from Script import script 
from plugins import web_server
from typing import Union, Optional, AsyncGenerator
from pyrogram import types

# ==========================================
# DEBUG FLAG: Set to True to diagnose issues.
# Set back to False when you want normal operations.
# ==========================================
DEBUG_MODE = True 

class Bot(Client):

    def __init__(self):
        # If debug mode is active, we temporarily disable loading the plugins folder
        # to isolate if a broken plugin/filter is hijacking your commands.
        plugin_config = {"root": "plugins"} if not DEBUG_MODE else None
        if DEBUG_MODE:
            logging.warning("⚠️ DEBUG_MODE IS ACTIVE. Normal plugins are temporarily disabled to run diagnostics.")

        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            plugins=plugin_config,
            sleep_threshold=5,
        )

    async def start(self):
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats
        await super().start()
        await Media.ensure_indexes()
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        self.username = '@' + me.username
        logging.info(f"{me.first_name} with for Pyrogram v{__version__} (Layer {layer}) started on {me.username}.")
        tz = pytz.timezone('Asia/Kolkata')
        today = date.today()
        now = datetime.now(tz)
        time = now.strftime("%H:%M:%S %p")
        await self.send_message(chat_id=LOG_CHANNEL, text=script.RESTART_TXT.format(a=today, b=time, c=temp.U_NAME))
        app = web.AppRunner(await web_server())
        await app.setup()
        bind_address = "0.0.0.0"
        await web.TCPSite(app, bind_address, PORT).start()

        # Injecting the debug message handler dynamically if debug mode is active
        if DEBUG_MODE:
            @self.on_message(filters.all, group=-100)
            async def diagnostic_catch_all(client, message: types.Message):
                user_info = message.from_user.username if message.from_user else f"ID: {message.from_user.id}" if message.from_user else "Unknown"
                text_content = message.text or message.caption or "[No text content]"
                
                print("\n" + "="*50)
                logging.info(f"📥 [DEBUG] RECEIVED MESSAGE from @{user_info}: {text_content}")
                print("="*50 + "\n")
                
                try:
                    sent_msg = await message.reply_text("🔄 [DEBUG] Bot received your message and can reply successfully!")
                    logging.info(f"📤 [DEBUG] Reply sent successfully. Message ID: {sent_msg.id}")
                except Exception as debug_err:
                    logging.error(f"❌ [DEBUG] Failed to send outbound reply: {debug_err}", exc_info=True)

        # FIX: Use asyncio.create_task to run this in the background without blocking updates
        asyncio.create_task(self.send_report_message())
    
    async def send_report_message(self):
        while True:
            tz = pytz.timezone('Asia/Kolkata')
            today = date.today()
            now = datetime.now(tz)
            formatted_date_1 = now.strftime("%d-%B-%Y")
            formatted_date_2 = today.strftime("%d %b")
            time = now.strftime("%H:%M:%S %p")

            total_users = await db.total_users_count()
            total_chats = await db.total_chat_count()
            today_users = await db.daily_users_count(today) + 1
            today_chats = await db.daily_chats_count(today) + 1

            if now.hour == 23 and now.minute == 59:
                k = await self.send_message(
                    chat_id=LOG_CHANNEL, 
                    text=script.REPORT_TXT.format(
                        a=formatted_date_1,
                        b=formatted_date_2,
                        c=time,
                        d=total_users, 
                        e=total_chats,
                        f=today_users, 
                        g=today_chats,
                        h=temp.U_NAME
                    )
                )
                await k.pin()
                # Sleep for 61 seconds to ensure we cross into the next minute cleanly
                await asyncio.sleep(61)
            else:
                # Sleep for 30-60 seconds and check again
                await asyncio.sleep(40)
                
    async def stop(self, *args):
        await super().stop()
        logging.info("Bot stopped. Bye.")
    
    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        current = offset
        while True:
            new_diff = min(200, limit - current)
            if new_diff <= 0:
                return
            messages = await self.get_messages(chat_id, list(range(current, current+new_diff+1)))
            for message in messages:
                yield message
                current += 1

app = Bot()
app.run()

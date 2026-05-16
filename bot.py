import logging
import logging.config
import asyncio
from datetime import date, datetime
from typing import Union, Optional, AsyncGenerator

import pytz
from aiohttp import web
from pyrogram import Client, __version__, types
from pyrogram.raw.all import layer

# Database and configuration imports
from database.ia_filterdb import Media
from database.users_chats_db import db
from info import SESSION, API_ID, API_HASH, BOT_TOKEN, PORT, LOG_CHANNEL
from utils import temp
from Script import script 
from plugins import web_server

# Initialize logging configuration from external file
logging.config.fileConfig('logging.conf')
logger = logging.getLogger(__name__)

# Suppress verbose third-party log outputs
logging.getLogger("pyrogram").setLevel(logging.ERROR)
logging.getLogger("imdbpy").setLevel(logging.ERROR)


class Bot(Client):
    """
    Custom Telegram Client extending Pyrogram's core functional behavior.
    Handles startup routines, background metrics reporting, and internal message iterations.
    """

    def __init__(self):
        super().__init__(
            name=SESSION,
            api_id=API_ID,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            workers=50,
            plugins={"root": "plugins"},
            sleep_threshold=5,
        )
        self.username: Optional[str] = None

    async def start(self):
        """Initializes dependencies, verifies active sessions, and mounts web routes."""
        # 1. Fetch and cache banned entries to keep performance snappy
        b_users, b_chats = await db.get_banned()
        temp.BANNED_USERS = b_users
        temp.BANNED_CHATS = b_chats

        # 2. Spin up the underlying Pyrogram client lifecycle
        await super().start()
        await Media.ensure_indexes()
        
        # 3. Synchronize bot identity and metadata cache
        me = await self.get_me()
        temp.ME = me.id
        temp.U_NAME = me.username
        temp.B_NAME = me.first_name
        self.username = f"@{me.username}"
        
        logger.info(f"{me.first_name} running Pyrogram v{__version__} (Layer {layer}) started successfully.")

        # 4. Dispatch deployment alert to logging channel
        tz = pytz.timezone('Asia/Kolkata')
        today = date.today()
        now = datetime.now(tz)
        formatted_time = now.strftime("%H:%M:%S %p")
        
        try:
            await self.send_message(
                chat_id=LOG_CHANNEL, 
                text=script.RESTART_TXT.format(a=today, b=formatted_time, c=temp.U_NAME)
            )
        except Exception as err:
            logger.error(f"Failed to deliver startup notification to LOG_CHANNEL: {err}")

        # 5. Serve aiohttp server asynchronously for health-checks or webhooks
        app_runner = web.AppRunner(await web_server())
        await app_runner.setup()
        await web.TCPSite(app_runner, "0.0.0.0", PORT).start()

        # 6. Offload metrics engine loop entirely to the background worker loop
        asyncio.create_task(self._run_report_scheduler())
    
    async def _run_report_scheduler(self):
        """Monitors clock time and aggregates operational analytical reports at midnight."""
        tz = pytz.timezone('Asia/Kolkata')
        
        while True:
            try:
                now = datetime.now(tz)
                
                # Evaluate condition precisely at 11:59 PM IST
                if now.hour == 23 and now.minute == 59:
                    today = date.today()
                    formatted_date_1 = now.strftime("%d-%B-%Y")
                    formatted_date_2 = today.strftime("%d %b")
                    formatted_time = now.strftime("%H:%M:%S %p")

                    # Fetch real-time user database aggregations
                    total_users = await db.total_users_count()
                    total_chats = await db.total_chat_count()
                    today_users = await db.daily_users_count(today) + 1
                    today_chats = await db.daily_chats_count(today) + 1

                    report_text = script.REPORT_TXT.format(
                        a=formatted_date_1,
                        b=formatted_date_2,
                        c=formatted_time,
                        d=total_users, 
                        e=total_chats,
                        f=today_users, 
                        g=today_chats,
                        h=temp.U_NAME
                    )

                    msg = await self.send_message(chat_id=LOG_CHANNEL, text=report_text)
                    await msg.pin()
                    
                    # Prevent race conditions by holding execution for 65 seconds until midnight passes cleanly
                    await asyncio.sleep(65)
                else:
                    # Dynamically calculate remaining time to mitigate intensive execution spikes
                    await asyncio.sleep(45)
                    
            except Exception as loop_error:
                logger.error(f"Error captured in telemetry report scheduler: {loop_error}", exc_info=True)
                await asyncio.sleep(30)  # Safe recovery period
                
    async def stop(self, *args):
        """Intercepts shutdown signals gracefully to free up system sockets."""
        await super().stop()
        logger.info("Bot application context terminated cleanly.")
    
    async def iter_messages(
        self,
        chat_id: Union[int, str],
        limit: int,
        offset: int = 0,
    ) -> Optional[AsyncGenerator["types.Message", None]]:
        """
        Yields chunk-based sequential historical target entities effectively.
        Optimized to reduce memory footprints over large datasets.
        """
        current = offset
        while current < limit:
            chunk_size = min(200, limit - current)
            if chunk_size <= 0:
                break
                
            message_ids = list(range(current, current + chunk_size + 1))
            try:
                messages = await self.get_messages(chat_id, message_ids)
                for message in messages:
                    yield message
                    current += 1
            except Exception as iter_err:
                logger.error(f"Error handling chunk sequence at tracking index {current}: {iter_err}")
                break


if __name__ == "__main__":
    app = Bot()
    app.run()

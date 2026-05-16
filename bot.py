import logging
from pyrogram import Client, idle
from info import API_ID, API_HASH, BOT_TOKEN

# Logging
logging.basicConfig(level=logging.INFO)

# Create Bot Client
app = Client(
    "MyBot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    plugins=dict(root="plugins")
)

# Start Bot
if __name__ == "__main__":
    app.start()
    print("Bot Started Successfully!")
    idle()
    app.stop()
    print("Bot Stopped!")

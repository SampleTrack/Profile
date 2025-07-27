from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import ClientSession
from telegraph import upload_file
from io import BytesIO
import tempfile
import os

# Create a single aiohttp session globally
aiohttp_session = ClientSession()

# Carbon generator function
async def make_carbon(code: str, upload_to_telegraph: bool = False):
    """
    Generates a carbon image from the given code string.
    If upload_to_telegraph is True, uploads the image to graph.org and returns the URL.
    Otherwise, returns the BytesIO image object.
    """
    try:
        url = "https://carbonara.solopov.dev/api/cook"
        async with aiohttp_session.post(url, json={"code": code}) as response:
            image_data = BytesIO(await response.read())
            image_data.name = "carbon.png"
    except Exception as e:
        print(f"[Carbon Error] Failed to generate image: {e}")
        return None

    if upload_to_telegraph:
        # Save to a temporary file for upload
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp_file:
            tmp_file.write(image_data.getvalue())
            temp_path = tmp_file.name

        image_data.close()

        try:
            uploaded_files = upload_file([temp_path])  # Upload to Telegraph
            os.remove(temp_path)  # Cleanup temp file
            return f"https://graph.org{uploaded_files[0]['src']}"
        except Exception as e:
            print(f"[Telegraph Upload Error] {e}")
            os.remove(temp_path)
            return None

    return image_data

# Pyrogram handler for /carbon command
@Client.on_message(filters.command("carbon"))
async def carbon_command(client: Client, message: Message):
    """
    Responds to /carbon command. Converts replied text message into a Carbon image and sends it as a photo.
    """
    # Check if it's a reply to a text message
    if not message.reply_to_message or not message.reply_to_message.text:
        return await message.reply_text("❗ ᴘʟᴇᴀꜱᴇ ʀᴇᴘʟʏ ᴛᴏ ᴀ ᴛᴇxᴛ ᴍᴇꜱꜱᴀɢᴇ ᴛᴏ ᴄʀᴇᴀᴛᴇ ᴀ ᴄᴀʀʙᴏɴ ɪᴍᴀɢᴇ.")

    status_msg = await message.reply_text("🎨 ɢᴇɴᴇʀᴀᴛɪɴɢ ʏᴏᴜʀ ᴄᴀʀʙᴏɴ ɪᴍᴀɢᴇ...")

    # Generate carbon image
    carbon_image = await make_carbon(message.reply_to_message.text)

    if not carbon_image:
        return await status_msg.edit("⚠️ ᴇʀʀᴏʀ ᴡʜɪʟᴇ ɢᴇɴᴇʀᴀᴛɪɴɢ ᴄᴀʀʙᴏɴ. ᴘʟᴇᴀꜱᴇ ᴛʀʏ ᴀɢᴀɪɴ.")

    # Upload and reply with image
    await status_msg.edit("📤 ᴜᴘʟᴏᴀᴅɪɴɢ ɪᴍᴀɢᴇ...")
    await message.reply_photo(
        photo=carbon_image,
        caption="✨ ᴄᴀʀʙᴏɴ ɢᴇɴᴇʀᴀᴛᴇᴅ ʙʏ: @mkn_bots_updates",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("💬 ᴊᴏɪɴ ꜱᴜᴘᴘᴏʀᴛ", url="https://t.me/mkn_bots_updates")
                ]
            ]
        )
    )

    await status_msg.delete()
    carbon_image.close()
    

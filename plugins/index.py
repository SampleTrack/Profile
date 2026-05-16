import logging
import re
import asyncio

from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait
from pyrogram.errors.exceptions.bad_request_400 import (
    ChannelInvalid,
    ChatAdminRequired,
    UsernameInvalid,
    UsernameNotModified
)
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from info import CHANNELS, LOG_CHANNEL, ADMINS
from database.ia_filterdb import save_file
from utils import temp


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

lock = asyncio.Lock()


@Client.on_message(
    filters.chat(CHANNELS)
    & (filters.document | filters.video | filters.audio)
)
async def media(bot, message):

    for file_type in ("document", "video", "audio"):
        media = getattr(message, file_type, None)

        if media is not None:
            break
    else:
        return

    media.file_type = file_type
    media.caption = message.caption

    await save_file(media)


@Client.on_callback_query(filters.regex(r"^index"))
async def index_files(bot, query):

    if query.data.startswith("index_cancel"):
        temp.CANCEL = True
        return await query.answer(
            "Cancelling Indexing...",
            show_alert=True
        )

    try:
        _, chat, lst_msg_id = query.data.split("#")
    except ValueError:
        return await query.answer(
            "Invalid callback data",
            show_alert=True
        )

    if lock.locked():
        return await query.answer(
            "Wait Until Previous Process Completes",
            show_alert=True
        )

    msg = query.message

    button = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(
                "🚫 Cancel",
                callback_data="index_cancel"
            )
        ]]
    )

    await msg.edit(
        "Indexing Started ✨",
        reply_markup=button
    )

    try:
        chat = int(chat)
    except ValueError:
        pass

    await index_files_to_db(
        int(lst_msg_id),
        chat,
        msg,
        bot
    )


@Client.on_message(
    (
        filters.forwarded
        | (
            filters.regex(
                r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)"
                r"(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$"
            )
            & filters.text
        )
    )
    & filters.private
    & filters.incoming
    & filters.user(ADMINS)
)
async def send_for_index(bot, message):

    if message.text:

        regex = re.compile(
            r"(https://)?(t\.me/|telegram\.me/|telegram\.dog/)"
            r"(c/)?(\d+|[a-zA-Z_0-9]+)/(\d+)$"
        )

        match = regex.match(message.text)

        if not match:
            return await message.reply("Invalid link")

        chat_id = match.group(4)
        last_msg_id = int(match.group(5))

        if chat_id.isnumeric():
            chat_id = int(f"-100{chat_id}")

    elif (
        message.forward_from_chat
        and message.forward_from_chat.type == enums.ChatType.CHANNEL
    ):

        last_msg_id = message.forward_from_message_id

        chat_id = (
            message.forward_from_chat.username
            or message.forward_from_chat.id
        )

    else:
        return

    try:
        await bot.get_chat(chat_id)

    except ChannelInvalid:
        return await message.reply(
            "This may be a private channel/group.\n"
            "Make me admin there to index files."
        )

    except (UsernameInvalid, UsernameNotModified):
        return await message.reply("Invalid link specified.")

    except Exception as e:
        return await message.reply(f"Errors - {e}")

    try:
        k = await bot.get_messages(chat_id, last_msg_id)

    except Exception:
        return await message.reply(
            "Make sure I am admin in the channel/group."
        )

    if k.empty:
        return await message.reply(
            "This may be a group and I am not admin there."
        )

    buttons = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✨ Yes",
                    callback_data=f"index#{chat_id}#{last_msg_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "🚫 Close",
                    callback_data="close_data"
                )
            ]
        ]
    )

    await message.reply(
        f"Do You Want To Index This Channel/Group?\n\n"
        f"Chat ID/Username: <code>{chat_id}</code>\n"
        f"Last Message ID: <code>{last_msg_id}</code>",
        reply_markup=buttons
    )


@Client.on_message(filters.command("setskip") & filters.user(ADMINS))
async def set_skip_number(bot, message):

    if len(message.command) != 2:
        return await message.reply("Give Me A Skip Number")

    try:
        skip = int(message.command[1])

    except ValueError:
        return await message.reply(
            "Skip Number Should Be An Integer."
        )

    temp.CURRENT = skip

    await message.reply(
        f"Successfully Set Skip Number As {skip}"
    )


async def index_files_to_db(lst_msg_id, chat, msg, bot):

    total_files = 0
    duplicate = 0
    errors = 0
    deleted = 0
    no_media = 0
    unsupported = 0

    async with lock:

        try:
            current = temp.CURRENT
            temp.CANCEL = False

            async for message in bot.iter_messages(
                chat,
                lst_msg_id,
                temp.CURRENT
            ):

                if temp.CANCEL:

                    await msg.edit(
                        f"Successfully Cancelled!!\n\n"
                        f"Saved <code>{total_files}</code> files "
                        f"to Database!\n"
                        f"Duplicate Files Skipped: "
                        f"<code>{duplicate}</code>\n"
                        f"Deleted Messages Skipped: "
                        f"<code>{deleted}</code>\n"
                        f"Non-Media Messages Skipped: "
                        f"<code>{no_media + unsupported}</code>\n"
                        f"Unsupported Media: "
                        f"<code>{unsupported}</code>\n"
                        f"Errors Occurred: "
                        f"<code>{errors}</code>"
                    )
                    break

                current += 1

                if current % 100 == 0:

                    reply = InlineKeyboardMarkup(
                        [[
                            InlineKeyboardButton(
                                "Cancel",
                                callback_data="index_cancel"
                            )
                        ]]
                    )

                    status_text = (
                        f"Total Messages Fetched: "
                        f"<code>{current}</code>\n"
                        f"Total Messages Saved: "
                        f"<code>{total_files}</code>\n"
                        f"Duplicate Files Skipped: "
                        f"<code>{duplicate}</code>\n"
                        f"Deleted Messages Skipped: "
                        f"<code>{deleted}</code>\n"
                        f"Non-Media Messages Skipped: "
                        f"<code>{no_media + unsupported}</code>\n"
                        f"Unsupported Media: "
                        f"<code>{unsupported}</code>\n"
                        f"Errors Occurred: "
                        f"<code>{errors}</code>"
                    )

                    try:
                        await msg.edit_text(
                            text=status_text,
                            reply_markup=reply
                        )

                    except FloodWait as t:
                        await asyncio.sleep(t.value)

                        await msg.edit_text(
                            text=status_text,
                            reply_markup=reply
                        )

                if message.empty:
                    deleted += 1
                    continue

                if not message.media:
                    no_media += 1
                    continue

                if message.media not in [
                    enums.MessageMediaType.VIDEO,
                    enums.MessageMediaType.AUDIO,
                    enums.MessageMediaType.DOCUMENT
                ]:
                    unsupported += 1
                    continue

                media = getattr(
                    message,
                    message.media.value,
                    None
                )

                if not media:
                    unsupported += 1
                    continue

                media.file_type = message.media.value
                media.caption = message.caption

                saved, result = await save_file(media)

                if saved:
                    total_files += 1

                elif result == 0:
                    duplicate += 1

                elif result == 2:
                    errors += 1

        except Exception as e:
            logger.exception(e)

            await msg.edit(f"Error: {e}")

        else:

            await msg.edit(
                f"Successfully Saved "
                f"<code>{total_files}</code> Files To Database!\n\n"
                f"Duplicate Files Skipped: "
                f"<code>{duplicate}</code>\n"
                f"Deleted Messages Skipped: "
                f"<code>{deleted}</code>\n"
                f"Non-Media Messages Skipped: "
                f"<code>{no_media + unsupported}</code>\n"
                f"Unsupported Media: "
                f"<code>{unsupported}</code>\n"
                f"Errors Occurred: "
                f"<code>{errors}</code>"
    )

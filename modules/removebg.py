import os
import aiohttp
from io import BytesIO
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.config import rmbg_key
from utils import modules_help, prefix
from utils.scripts import edit_or_reply


@Client.on_message(filters.command("rbg", prefix) & filters.me)
async def remove_background(client: Client, message: Message):

    if not rmbg_key:
        return await edit_or_reply(
            message,
            "<code>Remove.bg API key not configured (rmbg_key)</code>"
        )

    if not message.reply_to_message or not message.reply_to_message.photo:
        return await edit_or_reply(
            message,
            "<code>Reply to an image.</code>"
        )

    msg = await edit_or_reply(message, "<code>Removing background...</code>")

    photo_path = await message.reply_to_message.download()

    async with aiohttp.ClientSession() as session:

        with open(photo_path, "rb") as f:

            data = aiohttp.FormData()
            data.add_field("image_file", f)
            data.add_field("size", "auto")

            async with session.post(
                "https://api.remove.bg/v1.0/removebg",
                headers={"X-Api-Key": rmbg_key},
                data=data
            ) as resp:

                if resp.status != 200:
                    error = await resp.text()
                    await msg.edit(f"<code>API Error:\n{error}</code>")
                    return

                result = await resp.read()

    if os.path.exists(photo_path):
        os.remove(photo_path)

    output = BytesIO(result)
    output.name = "removed_bg.png"

    await client.send_document(
        message.chat.id,
        output,
        reply_to_message_id=message.reply_to_message.id
    )

    await msg.delete()


modules_help["removebg"] = {
    "rbg [reply to image]*": "Remove background from image (transparent PNG)",
}

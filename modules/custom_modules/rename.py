import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.misc import modules_help, prefix
from utils.scripts import format_exc, progress


@Client.on_message(filters.command("rename", prefix) & filters.me)
async def rename_file(client: Client, message: Message):
    if len(message.command) <= 1:
        await message.edit_text(
            "Please reply to a file and provide a new name (with extension) to rename it."
        )
        return

    new_name = message.text.split(maxsplit=1)[1]
    status_msg = await message.edit("<code>Renaming...</code>")

    try:
        # Download the replied-to file
        start_time = time.time()
        original_file = await message.reply_to_message.download(
            progress=progress,
            progress_args=(status_msg, start_time, "`Renaming...`"),
        )

        # Rename the file
        os.rename(original_file, new_name)
        await status_msg.edit("<code>Done, Uploading...</code>")

        # Upload the renamed file
        await client.send_document(
            message.chat.id,
            new_name,
            reply_to_message_id=message.id,
            progress=progress,
            progress_args=(status_msg, start_time, "`Done, Uploading...`"),
        )

    except Exception as e:
        await status_msg.edit(format_exc(e))

    finally:
        # Cleanup the renamed file
        if os.path.exists(new_name):
            os.remove(new_name)
        await status_msg.delete()


modules_help["rename"] = {
    "rename [reply]*": "Rename a file/media to the given name and upload it",
}

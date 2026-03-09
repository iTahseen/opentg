import asyncio
import os
from asyncio import sleep
from pyrogram import Client, filters
from pyrogram.errors import (
    FileReferenceExpired,
    FileReferenceInvalid,
    TopicDeleted,
    TopicClosed,
)
from pyrogram.types import Message
from collections import defaultdict
from utils.db import db
from utils import modules_help, prefix

mlog_enabled = filters.create(lambda _, __, ___: db.get("custom.mlog", "status", False))

user_media_cache = defaultdict(list)
media_processing_tasks = {}

def get_group_data(group_id):
    return db.get(f"custom.mlog", str(group_id), {})

def update_group_data(group_id, data):
    db.set(f"custom.mlog", str(group_id), data)

@Client.on_message(filters.command(["mlog"], prefix) & filters.me, group=2)
async def mlog(_, message: Message):
    if len(message.command) < 2 or message.command[1].lower() not in ["on", "off"]:
        return await message.edit(f"<b>Usage:</b> <code>{prefix}mlog [on/off]</code>")
    status = message.command[1].lower() == "on"
    db.set("custom.mlog", "status", status)
    await message.edit(f"<b>Media logging is now {'enabled' if status else 'disabled'}</b>")

@Client.on_message(filters.command(["msetchat"], prefix) & filters.me, group=2)
async def set_chat(_, message: Message):
    if len(message.command) < 2:
        return await message.edit(f"<b>Usage:</b> <code>{prefix}msetchat [chat_id]</code>")
    try:
        chat_id = message.command[1]
        chat_id = int("-100" + chat_id if not chat_id.startswith("-100") else chat_id)
        db.set("custom.mlog", "chat", chat_id)
        await message.edit(f"<b>Chat ID set to {chat_id}</b>")
    except ValueError:
        await message.edit("<b>Invalid chat ID</b>")

@Client.on_message(filters.command(["mrename", "m"], prefix) & filters.me, group=2)
async def rename_topic(client: Client, message: Message):
    try:
        user_id = int(message.command[1]) if len(message.command) > 1 else message.chat.id
        chat_id = db.get("custom.mlog", "chat")
        if not chat_id:
            status_msg = await message.edit(
                f"<b>No Chat ID is set. Use {prefix}msetchat to set the Chat ID.</b>"
            )
            await sleep(1)
            return await status_msg.delete()

        group_data = get_group_data(chat_id)
        user_topics = group_data.get("user_topics", {})
        topic_id = user_topics.get(str(user_id))
        if not topic_id:
            status_msg = await message.edit(f"<b>No topic found for user ID {user_id}.</b>")
            await sleep(1)
            return await status_msg.delete()

        try:
            user = await client.get_users(user_id)
        except Exception as e:
            if "PEER_ID_INVALID" in str(e):
                await client.send_message(
                    chat_id=chat_id,
                    message_thread_id=topic_id,
                    text="This is topic for deleted account"
                )
                status_msg = await message.edit(
                    "<b>Account Deleted, Topic Found.</b>"
                )
                await sleep(1)
                return await status_msg.delete()
            raise

        try:
            await client.edit_forum_topic(
                chat_id=chat_id,
                topic_id=topic_id,
                title=user.first_name
            )
            status_msg = await message.edit(
                f"<b>Topic renamed to '{user.first_name}'.</b>"
            )
        except Exception as e:
            if "TOPIC_NOT_MODIFIED" in str(e):
                status_msg = await message.edit(
                    f"<b>Topic name is already '{user.first_name}'.</b>"
                )
            else:
                raise e

        info_message = (
            f"<b>Chat Name:</b> {user.full_name}\n"
            f"<b>User ID:</b> {user.id}\n"
            f"<b>Username:</b> @{user.username or 'N/A'}\n"
            f"<b>Phone No:</b> +{user.phone_number or 'N/A'}"
        )
        info_msg = await client.send_message(
            chat_id=chat_id,
            message_thread_id=topic_id,
            text=info_message
        )
        await info_msg.pin()
        await sleep(1)
        await status_msg.delete()

    except ValueError:
        status_msg = await message.edit("<b>Invalid user ID</b>")
        await sleep(1)
        return await status_msg.delete()

    except Exception as e:
        status_msg = await message.edit(f"<b>Error:</b> {str(e)}")
        await sleep(1)
        return await status_msg.delete()

@Client.on_message(
    mlog_enabled
    & filters.incoming
    & filters.private
    & filters.media
    & ~filters.sticker
    & ~filters.me
    & ~filters.bot
)
async def media_log(client: Client, message: Message):
    user_id = message.from_user.id
    user_media_cache[user_id].append(message)
    if user_id not in media_processing_tasks:
        media_processing_tasks[user_id] = asyncio.create_task(
            process_media(client, message.from_user)
        )

async def process_media(client: Client, user):
    await asyncio.sleep(5)
    user_id = user.id
    me = await client.get_me()
    if user_id == me.id:
        return
    chat_id = db.get("custom.mlog", "chat")
    if not chat_id:
        return await client.send_message(
            "me",
            f"Media Logger is on, but no Chat ID is set. Use {prefix}msetchat to set it.",
        )
    group_data = get_group_data(chat_id)
    user_topics = group_data.get("user_topics", {})
    topic_id = user_topics.get(str(user_id))
    if not topic_id:
        topic = await client.create_forum_topic(chat_id, user.first_name)
        topic_id = topic.id
        user_topics[str(user_id)] = topic_id
        update_group_data(chat_id, {"user_topics": user_topics})
        m = await client.send_message(
            chat_id=chat_id,
            message_thread_id=topic_id,
            text=f"<b>Chat Name:</b> {user.full_name}\n<b>User ID:</b> {user_id}\n<b>Username:</b> @{user.username or 'N/A'}\n<b>Phone No:</b> +{user.phone_number or 'N/A'}",
        )
        await m.pin()
    messages_to_process = user_media_cache.pop(user_id, [])
    for media_message in messages_to_process:
        try:
            await media_message.copy(chat_id=chat_id, message_thread_id=topic_id)
            await asyncio.sleep(1)
        except (FileReferenceExpired, FileReferenceInvalid):
            await handle_self_destruct_media(client, media_message, chat_id, topic_id)
        except TopicDeleted:
            topic = await client.create_forum_topic(chat_id, user.first_name)
            topic_id = topic.id
            user_topics[str(user_id)] = topic_id
            update_group_data(chat_id, {"user_topics": user_topics})
            await client.send_message(
                chat_id=chat_id,
                message_thread_id=topic_id,
                text=f"<b>Chat Name:</b> {user.full_name}\n<b>User ID:</b> {user_id}\n<b>Username:</b> @{user.username or 'N/A'}\n<b>Phone No:</b> +{user.phone_number or 'N/A'}",
            )
            await handle_self_destruct_media(client, media_message, chat_id, topic_id)
        except TopicClosed:
            await client.reopen_forum_topic(chat_id=chat_id, topic_id=topic_id)
            await media_message.copy(chat_id=chat_id, message_thread_id=topic_id)
    media_processing_tasks.pop(user_id, None)

async def handle_self_destruct_media(client: Client, message: Message, chat_id: int, topic_id: int):
    try:
        file_path = await message.download()
        if message.photo:
            await client.send_photo(chat_id, file_path, message_thread_id=topic_id)
        elif message.video_note:
            await client.send_video(chat_id, file_path, message_thread_id=topic_id)
        os.remove(file_path)
    except Exception as e:
        print(f"Error handling self-destructing media: {e}")

modules_help["mlog"] = {
    "mlog [on/off]": "Enable or disable media logging",
    "msetchat [chat_id]": "Set the chat ID for media logging",
    "mrename [user_id]": "Rename a user's topic",
}

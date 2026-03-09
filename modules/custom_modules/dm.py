import os
import re
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InputMediaPhoto, InputMediaVideo
from pyrogram.enums import MessagesFilter
from utils.misc import modules_help, prefix
from utils.db import db

NS = "custom.dm"

def _chunked(seq, size):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]

async def _save_sent_message(client: Client, message: Message):
    if not message:
        return
    enabled = db.get(NS, "enabled", False)
    if not enabled:
        return
    me = await client.get_me()
    if message.chat.id == me.id:
        return
    chat_id = str(message.chat.id)
    excluded_chats = db.get(NS, "excluded_chats", [])
    if chat_id in excluded_chats:
        return
    msg_ids = db.get(NS, f"media:{chat_id}", [])
    msg_ids.append(message.id)
    db.set(NS, f"media:{chat_id}", msg_ids)
    chats = db.get(NS, "chats", [])
    if chat_id not in chats:
        chats.append(chat_id)
        db.set(NS, "chats", chats)

@Client.on_message(filters.me & filters.media & ~filters.bot & ~filters.channel & ~filters.group)
async def store_my_media(client: Client, message: Message):
    if message.chat.id == (await client.get_me()).id:
        return
    enabled = db.get(NS, "enabled", False)
    if not enabled:
        return
    chat_id = str(message.chat.id)
    excluded_chats = db.get(NS, "excluded_chats", [])
    if chat_id in excluded_chats:
        return
    msg_ids = db.get(NS, f"media:{chat_id}", [])
    msg_ids.append(message.id)
    db.set(NS, f"media:{chat_id}", msg_ids)
    chats = db.get(NS, "chats", [])
    if chat_id not in chats:
        chats.append(chat_id)
        db.set(NS, "chats", chats)

@Client.on_message(filters.me & filters.command(["dm"], prefix))
async def handle_dm(client: Client, message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        arg = args[1].lower().strip()
        if arg == "on":
            db.set(NS, "enabled", True)
            await message.edit("Media <b>ON</b>")
            return
        elif arg == "off":
            db.set(NS, "enabled", False)
            await message.edit("Media <b>OFF</b>")
            return
        elif arg.startswith("exclude"):
            parts = arg.split()
            if len(parts) == 1:
                excluded = [str(x) for x in db.get(NS, "excluded_chats", [])]
                if not excluded:
                    await message.edit("No excluded chats.")
                else:
                    text = "<b>Excluded Chats:</b>\n" + "\n".join(excluded)
                    await message.edit(text)
            elif len(parts) == 2:
                chat_id = str(parts[1])
                excluded = [str(x) for x in db.get(NS, "excluded_chats", [])]
                if chat_id in excluded:
                    excluded.remove(chat_id)
                    db.set(NS, "excluded_chats", excluded)
                    await message.edit(f"Removed chat <b>{chat_id}</b> from excluded list.")
                else:
                    excluded.append(chat_id)
                    db.set(NS, "excluded_chats", excluded)
                    await message.edit(f"Excluded chat <b>{chat_id}</b>")
            else:
                await message.edit("Usage: <b>dm exclude [chat_id]</b>")
            return
    chats = db.get(NS, "chats", [])
    if not chats:
        await message.edit("No media.")
        return
    await message.edit("Cleaning...")
    total_deleted = 0
    total_chats = 0
    excluded_chats = db.get(NS, "excluded_chats", [])
    for chat_id in list(chats):
        if chat_id in excluded_chats:
            db.remove(NS, f"media:{chat_id}")
            continue
        msg_ids = db.get(NS, f"media:{chat_id}", [])
        if not msg_ids:
            db.remove(NS, f"media:{chat_id}")
            continue
        per_chat_deleted = 0
        for chunk in _chunked(msg_ids, 30):
            try:
                await client.delete_messages(int(chat_id), chunk)
                per_chat_deleted += len(chunk)
            except Exception as e:
                print(f"Failed deleting in chat {chat_id}, chunk {chunk[:3]}... -> {e}")
        db.remove(NS, f"media:{chat_id}")
        if per_chat_deleted:
            total_chats += 1
            total_deleted += per_chat_deleted
    db.set(NS, "chats", [])
    await message.edit(f"Deleted <b>{total_deleted}</b> in <b>{total_chats}</b> chats.")

@Client.on_message(filters.me & filters.regex(rf"^{re.escape(prefix)}s\d+(\s+v\d*)?$"))
async def media_slot(client: Client, message: Message):
    parts = message.text.strip().split()
    slot = parts[0][len(prefix):]
    self_destruct = False
    ttl_seconds = 10
    if len(parts) > 1 and parts[1].startswith("v"):
        self_destruct = True
        if len(parts[1]) > 1 and parts[1][1:].isdigit():
            ttl_seconds = int(parts[1][1:])
    if message.reply_to_message:
        m = message.reply_to_message
        if m.media_group_id:
            await asyncio.sleep(1)
            media_msgs = []
            async for msg in client.search_messages(m.chat.id, filter=MessagesFilter.EMPTY, limit=50):
                if msg.media_group_id == m.media_group_id:
                    media_msgs.append(msg.id)
            media_msgs.sort()
            db.set(NS, slot, {"chat_id": m.chat.id, "media_group": media_msgs})
            await message.edit(f"Saved media group ({len(media_msgs)} items) in <b>{slot}</b>")
            return
        db.set(NS, slot, {"chat_id": m.chat.id, "message_id": m.id})
        await message.edit(f"Saved media in <b>{slot}</b>")
        return
    saved = db.get(NS, slot, None)
    if not saved:
        await message.edit(f"Empty <b>{slot}</b>")
        return
    chat_id = saved.get("chat_id")
    if "media_group" in saved:
        msgs = []
        for msg_id in saved["media_group"]:
            msg = await client.get_messages(chat_id, msg_id)
            if msg.photo:
                msgs.append(InputMediaPhoto(msg.photo.file_id, caption=msg.caption or ""))
            elif msg.video:
                msgs.append(InputMediaVideo(msg.video.file_id, caption=msg.caption or ""))
        if msgs:
            await client.send_media_group(message.chat.id, msgs)
            await message.delete()
        return
    msg_id = saved.get("message_id")
    try:
        if self_destruct:
            original = await client.get_messages(chat_id, msg_id)
            if original.photo or original.video:
                file_path = await client.download_media(original)
                if original.photo:
                    sent_msg = await client.send_photo(
                        message.chat.id,
                        file_path,
                        ttl_seconds=ttl_seconds
                    )
                else:
                    sent_msg = await client.send_video(
                        message.chat.id,
                        file_path,
                        ttl_seconds=ttl_seconds
                    )
                if os.path.exists(file_path):
                    os.remove(file_path)
            else:
                await message.edit("Only photos/videos support self-destruct.")
                return
        else:
            sent_msg = await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=chat_id,
                message_id=msg_id
            )
    except Exception as e:
        await message.edit("Send failed")
        print(f"send failed for slot {slot}: {e}")
        return
    await _save_sent_message(client, sent_msg)
    await message.delete()

modules_help["dm"] = {
    "dm on": "Enable storing outgoing media.",
    "dm off": "Disable storing outgoing media.",
    "dm": "Delete all stored media (skips excluded chats).",
    "dm exclude": "Show excluded chats, or toggle exclusion using: dm exclude <chat_id>.",
    "s1, s2, ...": "Save or resend media. Use `s1 v10` for self-destruct (10s).",
}

import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.misc import modules_help, prefix
from modules.custom_modules.dm import media_slot

@Client.on_message(filters.command(["addx", "x"], prefix) & filters.me)
async def addx_contact(c: Client, message: Message):
    try:
        user = message.reply_to_message.from_user if message.reply_to_message else await c.get_users(message.chat.id)

        if user.is_bot:
            return await message.edit("You can't add bots to contacts.")

        args = message.text.split(maxsplit=1)[1:] if len(message.command) > 1 else []
        if not args and message.reply_to_message and message.reply_to_message.text:
            args = [message.reply_to_message.text.strip()]

        first_name = args[0] if args else (user.first_name or "Unknown")
        last_name = args[1] if len(args) > 1 else ""

        await c.add_contact(
            user_id=user.id,
            first_name=first_name,
            last_name=last_name,
            phone_number="",
            share_phone_number=False
        )

        user = await c.get_users(user.id)
        full_name = f"{first_name} {last_name}".strip()

        if user.is_mutual_contact:
            await message.edit(
                f"<b>Contact added:</b> <a href='tg://user?id={user.id}'>{full_name}</a> (Mutual)"
            )

            if message.reply_to_message or args:
                await c.send_message(message.chat.id, "you've beautiful name")
                await asyncio.sleep(1)
                await c.send_message(message.chat.id, "can I see you right now? I mean your face.")
            else:
                await asyncio.sleep(1)
                await c.send_message(message.chat.id, "What's your name in English?")
        else:
            await c.delete_contacts(user_ids=user.id)
            await message.edit(
                f"<b>Contact removed (not mutual):</b> <a href='tg://user?id={user.id}'>{full_name}</a>"
            )
            await asyncio.sleep(1)
            await c.send_message(message.chat.id, "You didn't add me yet")
            message.text = f"{prefix}s9"
            await media_slot(c, message)

    except Exception as e:
        await message.edit(f"Failed to add contact: <code>{e}</code>")

    await asyncio.sleep(1)
    await message.delete()

@Client.on_message(filters.command(["add", "c"], prefix) & filters.me)
async def add_contact(c: Client, message: Message):
    try:
        user = await c.get_users(message.chat.id)
        if user.is_bot:
            return await message.edit("You can't add bots to contacts.")

        args = message.text.split(maxsplit=1)[1:] if len(message.command) > 1 else []

        if not args and message.reply_to_message and message.reply_to_message.text:
            args = [message.reply_to_message.text.strip()]

        first_name = args[0] if args else (user.first_name or "Unknown")
        last_name = args[1] if len(args) > 1 else ""

        await c.add_contact(
            user_id=user.id,
            first_name=first_name,
            last_name=last_name,
            phone_number="",
            share_phone_number=False
        )

        user = await c.get_users(user.id)
        full_name = f"{first_name} {last_name}".strip()
        mutual_status = " (Mutual)" if user.is_mutual_contact else " (Not Mutual)"

        await message.edit(f"<b>Contact added:</b> <a href='tg://user?id={user.id}'>{full_name}</a>{mutual_status}")
    except Exception as e:
        await message.edit(f"Failed to add contact: <code>{e}</code>")

    await asyncio.sleep(1)
    await message.delete()

@Client.on_message(filters.command(["remove", "r"], prefix) & filters.me)
async def remove_contact(c: Client, message: Message):
    try:
        user = message.reply_to_message.from_user if message.reply_to_message else await c.get_users(message.chat.id)
        if user.is_self:
            return await message.edit("You can't remove yourself.")

        await c.delete_contacts(user_ids=user.id)
        await message.edit(f"<b>Contact removed:</b> <a href='tg://user?id={user.id}'>{user.first_name}</a>")
    except Exception as e:
        await message.edit(f"Failed to remove contact: <code>{e}</code>")

    await asyncio.sleep(5)
    await message.delete()

@Client.on_message(filters.command("mutual", prefix) & filters.me)
async def check_mutual(c: Client, message: Message):
    try:
        user = message.reply_to_message.from_user if message.reply_to_message else await c.get_users(message.chat.id)
        if user.is_self:
            return await message.edit("That's you.")

        status = [
            f"<b>Checking mutual status for</b> <a href='tg://user?id={user.id}'>{user.first_name}</a>:\n",
            "- You have <b>added</b> them to your contacts." if user.is_contact else "- You have <b>not added</b> them.",
            "- They have also <b>added you</b>. You're <b>mutual contacts</b>." if user.is_mutual_contact else "- They <b>haven't added</b> you back."
        ]
        await message.edit("\n".join(status))
    except Exception as e:
        await message.edit(f"Error: <code>{e}</code>")

    await asyncio.sleep(5)
    await message.delete()

@Client.on_message(filters.command(["clearmedia", "cm"], prefix) & filters.me)
async def clearmedia(client: Client, message: Message):
    chat_id = message.chat.id
    args = message.text.split(maxsplit=1)
    delete_all = len(args) > 1 and args[1].lower() == "all"
    deleted_count = 0

    async for msg in client.get_chat_history(chat_id):
        if delete_all:
            if msg.media:
                try:
                    await client.delete_messages(chat_id, msg.id)
                    deleted_count += 1
                    await asyncio.sleep(0.05)
                except:
                    pass
        elif msg.from_user and msg.from_user.id == client.me.id:
            if msg.media:
                try:
                    await client.delete_messages(chat_id, msg.id)
                    deleted_count += 1
                    await asyncio.sleep(0.05)
                except:
                    pass

    await message.edit(f"Deleted {deleted_count} media message(s).")
    await asyncio.sleep(2)
    await message.delete()


@Client.on_message(filters.command(["clearall", "ca"], prefix) & filters.me)
async def clearall(client: Client, message: Message):
    chat_id = message.chat.id
    args = message.text.split(maxsplit=1)
    delete_all = len(args) > 1 and args[1].lower() == "all"
    deleted_count = 0

    async for msg in client.get_chat_history(chat_id):
        if delete_all:
            try:
                await client.delete_messages(chat_id, msg.id)
                deleted_count += 1
                await asyncio.sleep(0.05)
            except:
                pass
        else:
            if msg.from_user and msg.from_user.id == client.me.id:
                try:
                    await client.delete_messages(chat_id, msg.id)
                    deleted_count += 1
                    await asyncio.sleep(0.05)
                except:
                    pass

    await message.edit(f"Deleted {deleted_count} message(s).")
    await asyncio.sleep(2)
    await message.delete()

modules_help["contact"] = {
    "add [name]": "Add user to contacts. Optional name via reply. Shows (Mutual) or (Not Mutual).",
    "mutual": "Check if user is a mutual contact.",
    "remove": "Remove user from contacts.",
    "clearmedia / cm": "Delete your media in this chat.\n`all` - delete both sides' media.",
    "clearall / ca": "Delete your messages (media + text).\n`all` - delete all messages from both sides."
}

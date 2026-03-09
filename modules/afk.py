import asyncio
from datetime import datetime
import humanize
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.misc import modules_help, prefix
from utils.scripts import ReplyCheck
from utils.db import db

AFK = False
AFK_REASON = ""
DEFAULT_AFK_REASON = "Negotiating with aliens"
AFK_TIME = ""
USERS = {}
GROUPS = {}


def GetChatID(message: Message):
    """Get the group id of the incoming message"""
    return message.chat.id


def subtract_time(start, end):
    """Get humanized time"""
    subtracted = humanize.naturaltime(start - end)
    return str(subtracted)


@Client.on_message(
    ((filters.group & filters.mentioned) | filters.private)
    & ~filters.me
    & ~filters.service,
    group=3,
)
async def collect_afk_messages(bot: Client, message: Message):
    if AFK:
        last_seen = subtract_time(datetime.now(), AFK_TIME)
        is_group = message.chat.type in ["supergroup", "group"]
        CHAT_TYPE = GROUPS if is_group else USERS

        if GetChatID(message) not in CHAT_TYPE:
            text = db.get("core.afk", "afk_msg", None)
            if text is None:
                text = (
                    f"<blockquote>I'm unavailable (<i>since {last_seen}</i>).</blockquote>\n"
                    f"<blockquote>"
                    f"<b>Reason:</b> {AFK_REASON}.\n"
                    f"Back soon. 👋\n"
                    f"</blockquote>"
                )
            else:
                last_seen = last_seen.replace("ago", "").strip()
                text = f"<pre>\n{text.format(last_seen=last_seen, reason=AFK_REASON)}\n</pre>"

            afk_message = await bot.send_message(
                chat_id=GetChatID(message),
                text=text,
            )
            CHAT_TYPE[GetChatID(message)] = 1
            await asyncio.sleep(30)
            await afk_message.delete()
            return

        if CHAT_TYPE[GetChatID(message)] == 50:
            text = (
                f"<blockquote>I'm unavailable (<i>since {last_seen}</i>).</blockquote>\n"
                f"<blockquote>"
                f"This is the 10th time I've told you I'm AFK right now...\n"
                f"Back soon. 👋\n"
                f"</blockquote>"
            )
            afk_message = await bot.send_message(
                chat_id=GetChatID(message),
                text=text,
            )
            await asyncio.sleep(30)
            await afk_message.delete()
        elif CHAT_TYPE[GetChatID(message)] > 50:
            return
        elif CHAT_TYPE[GetChatID(message)] % 5 == 0:
            text = (
                f"<blockquote>I'm unavailable (<i>since {last_seen}</i>).</blockquote>\n"
                f"<blockquote>"
                f"<b>Reason:</b> {AFK_REASON}.\n"
                f"Back soon. 👋\n"
                f"</blockquote>"
            )
            afk_message = await bot.send_message(
                chat_id=GetChatID(message),
                text=text,
            )
            await asyncio.sleep(30)
            await afk_message.delete()

        CHAT_TYPE[GetChatID(message)] += 1


@Client.on_message(filters.command("afk", prefix) & filters.me, group=3)
async def afk_set(_, message: Message):
    global AFK_REASON, AFK, AFK_TIME

    cmd = message.command
    afk_text = DEFAULT_AFK_REASON if len(cmd) == 1 else " ".join(cmd[1:])

    if isinstance(afk_text, str):
        AFK_REASON = afk_text

    AFK = True
    AFK_TIME = datetime.now()

    await message.delete()


@Client.on_message(filters.command("afk", "!") & filters.me, group=3)
async def afk_unset(_, message: Message):
    global AFK, AFK_TIME, AFK_REASON, USERS, GROUPS

    if AFK:
        last_seen = subtract_time(datetime.now(), AFK_TIME).replace("ago", "").strip()
        await message.edit(
            f"<blockquote>\n"
            f"While you were away (for {last_seen}), you received "
            f"{sum(USERS.values()) + sum(GROUPS.values())} messages "
            f"from {len(USERS) + len(GROUPS)} chats.\n"
            f"</blockquote>"
        )
        AFK = False
        AFK_TIME = ""
        AFK_REASON = ""
        USERS = {}
        GROUPS = {}
        await asyncio.sleep(5)

    await message.delete()


@Client.on_message(filters.command("setafkmsg", prefix) & filters.me, group=3)
async def set_afk_msg(_, message: Message):
    if not message.reply_to_message:
        return await message.edit("Reply to a message to set it as your AFK message.")

    msg = message.reply_to_message
    afk_msg = msg.text or msg.caption

    if not afk_msg:
        return await message.edit(
            "Reply to a text or caption message to set it as your AFK message."
        )

    if len(afk_msg) > 200:
        return await message.edit(
            "AFK message is too long. It should be less than 200 characters."
        )
    if "{reason}" not in afk_msg:
        return await message.edit(
            "AFK message should contain <code>{reason}</code> to indicate where the reason will be placed."
        )
    if "{last_seen}" not in afk_msg:
        return await message.edit(
            "AFK message should contain <code>{last_seen}</code> to indicate where the last seen time will be placed."
        )

    old_afk_msg = db.get("core.afk", "afk_msg", None)
    if old_afk_msg:
        db.remove("core.afk", "afk_msg")
    db.set("core.afk", "afk_msg", afk_msg)
    await message.edit(f"AFK message set to:\n\n<pre>{afk_msg}</pre>")


@Client.on_message(filters.me, group=3)
async def auto_afk_unset(_, message: Message):
    global AFK, AFK_TIME, AFK_REASON, USERS, GROUPS

    if AFK:
        last_seen = subtract_time(datetime.now(), AFK_TIME).replace("ago", "").strip()
        reply = await message.reply(
            f"<blockquote>\n"
            f"While you were away (for {last_seen}), you received "
            f"{sum(USERS.values()) + sum(GROUPS.values())} messages "
            f"from {len(USERS) + len(GROUPS)} chats.\n"
            f"</blockquote>"
        )
        AFK = False
        AFK_TIME = ""
        AFK_REASON = ""
        USERS = {}
        GROUPS = {}
        await asyncio.sleep(5)
        await reply.delete()


modules_help["afk"] = {
    "afk [reason]": "Go to AFK mode with a reason.\nUsage: <code>.afk <reason></code>",
    "unafk": "Exit AFK mode.",
    "setafkmsg [reply to message]*": "Set your AFK message. Use <code>{reason}</code> and <code>{last_seen}</code> to indicate where placeholders will be replaced.",
}

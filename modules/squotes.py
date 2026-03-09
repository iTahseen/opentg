import base64
from io import BytesIO
import requests
from pyrogram import Client, filters, errors, types
from pyrogram.types import Message
from utils.misc import modules_help, prefix
from utils.scripts import with_reply, format_exc, resize_image


@Client.on_message(filters.command(["q", "quote"], prefix))
@with_reply
async def quote_cmd(client: Client, message: Message):
    if message.reply_to_message is None:
        return await message.edit("<b>Please reply to a message to quote it.</b>")

    msg = message.reply_to_message

    if message.from_user.is_self:
        await message.edit("<b>Generating...</b>")
    else:
        message = await client.send_message(message.chat.id, "<b>Generating...</b>")

    url = "https://quotes-o042.onrender.com/generate"
    params = {
        "messages": [await render_message(client, msg)],
        "quote_color": "#162330",
        "text_color": "#fff",
    }

    response = requests.post(url, json=params)
    if not response.ok:
        return await message.edit(
            f"<b>Quotes API error!</b>\n" f"<code>{response.text}</code>"
        )

    resized = resize_image(BytesIO(response.content), img_type="WEBP")

    await message.edit("<b>Sending...</b>")

    try:
        await client.send_sticker(message.chat.id, resized)
    except errors.RPCError as e:
        await message.edit(format_exc(e))
    else:
        await message.delete()


@Client.on_message(filters.command(["fq", "fakequote"], prefix))
@with_reply
async def fake_quote_cmd(client: Client, message: types.Message):
    fake_quote_text = " ".join(
        arg for arg in message.command[1:] if arg not in ["!png", "!file", "!me", "!ls", "!noreply", "!nr"]
    )

    if not fake_quote_text:
        return await message.edit("<b>Fake quote text is empty</b>")

    q_message = message.reply_to_message
    q_message.text = fake_quote_text
    q_message.entities = None

    if message.from_user.is_self:
        await message.edit("<b>Generating...</b>")
    else:
        message = await client.send_message(message.chat.id, "<b>Generating...</b>")

    url = "https://quotes-o042.onrender.com/generate"
    params = {
        "messages": [await render_message(client, q_message)],
        "quote_color": "#162330",
        "text_color": "#fff",
    }

    response = requests.post(url, json=params)
    if not response.ok:
        return await message.edit(
            f"<b>Quotes API error!</b>\n<code>{response.text}</code>"
        )

    resized = resize_image(BytesIO(response.content), img_type="WEBP")

    await message.edit("<b>Sending...</b>")

    try:
        await client.send_sticker(message.chat.id, resized)
    except errors.RPCError as e:
        await message.edit(format_exc(e))
    else:
        await message.delete()


files_cache = {}


async def render_message(app: Client, message: types.Message) -> dict:
    async def get_file(file_id) -> str:
        if file_id in files_cache:
            return files_cache[file_id]

        content = await app.download_media(file_id, in_memory=True)
        data = base64.b64encode(bytes(content.getbuffer())).decode()
        files_cache[file_id] = data
        return data

    if message.photo:
        text = message.caption if message.caption else ""
    elif message.sticker:
        text = ""
    else:
        text = message.text

    media = ""
    if message.photo:
        media = await get_file(message.photo.file_id)
    elif message.sticker:
        media = await get_file(message.sticker.file_id)

    entities = []
    if message.entities:
        for entity in message.entities:
            entities.append(
                {
                    "offset": entity.offset,
                    "length": entity.length,
                    "type": str(entity.type).split(".")[-1].lower(),
                }
            )

    author = {}
    if message.from_user and message.from_user.id != 0:
        from_user = message.from_user

        author["id"] = from_user.id
        author["name"] = from_user.first_name
        if from_user.last_name:
            author["name"] += " " + from_user.last_name
        author["rank"] = ""
        if from_user.photo:
            author["avatar"] = await get_file(from_user.photo.big_file_id)
        else:
            author["avatar"] = ""
    else:
        author["id"] = message.sender_chat.id
        author["name"] = message.sender_chat.title
        author["rank"] = "channel" if message.sender_chat.type == "channel" else ""
        if message.sender_chat.photo:
            author["avatar"] = await get_file(message.sender_chat.photo.big_file_id)
        else:
            author["avatar"] = ""
    author["via_bot"] = message.via_bot.username if message.via_bot else ""

    reply = {}
    reply_msg = message.reply_to_message
    if reply_msg and not reply_msg.empty:
        if reply_msg.from_user:
            reply["id"] = reply_msg.from_user.id
            reply["name"] = reply_msg.from_user.first_name
            if reply_msg.from_user.last_name:
                reply["name"] += " " + reply_msg.from_user.last_name
        else:
            reply["id"] = reply_msg.sender_chat.id
            reply["name"] = reply_msg.sender_chat.title

        reply["text"] = reply_msg.text

    return {
        "text": text,
        "media": media,
        "entities": entities,
        "author": author,
        "reply": reply,
    }


modules_help["squotes"] = {
    "q [reply]": "Generate a quote",
    "fq [reply] [text]*": "Generate a fake quote",
}

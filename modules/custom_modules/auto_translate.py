import requests
from urllib.parse import quote
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.filters import create
from utils.misc import modules_help, prefix
from utils.db import db

TRANSLATE_API = "https://api.delirius.store/tools/translate?text={query}&language={lang}"

def auto_translate_filter(_, __, message: Message):
    """Filter to process messages only if translation is enabled for the chat."""
    lang_code = db.get("custom.translate", str(message.chat.id), None)
    return bool(lang_code) and not message.text.startswith(prefix)

auto_translate_filter = create(auto_translate_filter)

@Client.on_message(filters.command(["setlang"], prefix))
async def set_language(_, message: Message):
    """Set the preferred language for a chat."""
    if len(message.command) < 2:
        await message.edit(
            f"<b>Usage:</b> <code>{prefix}setlang [language_code]</code>\n\n"
        )
        return

    lang_code = message.text.split(maxsplit=1)[1].lower()
    db.set("custom.translate", str(message.chat.id), lang_code)
    await message.edit(f"<b>Language has been set to</b> <code>[{lang_code}]</code>.")

@Client.on_message(filters.command(["lang"], prefix))
async def language_status(_, message: Message):
    """Show the current language or turn off auto-translation."""
    chat_id = str(message.chat.id)
    command_text = message.text.strip().lower()

    if command_text == f"{prefix}lang":
        lang_code = db.get("custom.translate", chat_id, None)
        if lang_code:
            await message.edit(f"<b>Current language</b> <code>[{lang_code}]</code>.")
        else:
            await message.edit(f"<code>No language set.</code>")
    elif command_text == f"{prefix}lang off":
        result = db.remove("custom.translate", chat_id)
        if result:
            await message.edit("Auto-translation has been turned off for this chat.")
        else:
            await message.edit("<b>Auto-translation is disabled.</b>")
    else:
        await message.edit(f"<b>Usage:</b> \n<code>{prefix}lang</code> [check language] \n<code>{prefix}lang off</code> [turn off auto-translation].")

@Client.on_message(filters.text & auto_translate_filter)
async def auto_translate(_, message: Message):
    """Automatically translate and edit messages in chats with a set language."""
    if message.from_user and not message.from_user.is_self:
        return

    lang_code = db.get("custom.translate", str(message.chat.id), None)
    if not lang_code:
        return

    try:
        response = requests.get(TRANSLATE_API.format(query=quote(message.text), lang=lang_code))
        response.raise_for_status()
        data = response.json()

        translated_text = data.get("data", "No translation found.")
        if translated_text.strip() and translated_text != message.text:
            await message.edit(translated_text)
    except requests.exceptions.RequestException as e:
        await message.reply(f"Translation failed: {e}")

modules_help["auto_translate"] = {
    "setlang <language_code>": "Set the preferred language for this chat.",
    "lang": "Show the chat's language or use `lang off` to turn off auto-translation.",
    "Auto-translation": "Automatically translates and edits your messages in the chat to the set language."
}

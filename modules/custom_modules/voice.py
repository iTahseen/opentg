import requests
import os
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.db import db
from utils.misc import modules_help, prefix

ELEVENLABS_API_URL = "https://bk9.fun/tools/elevenlabs?q={query}&character={character}&output_format=mp3_44100_64"
AVAILABLE_CHARACTERS = [
    "rachel", "clyde", "domi", "dave", "fin", "bella", "antoni", "thomas", "charlie",
    "emily", "elli", "callum", "patrick", "harry", "liam", "dorothy", "josh", "arnold",
    "charlotte", "matilda", "matthew", "james", "joseph", "jeremy", "michael", "ethan",
    "gigi", "freya", "grace", "daniel", "serena", "adam", "nicole", "jessie", "ryan",
    "sam", "glinda", "giovanni", "mimi"
]

def get_default_character():
    """Fetch the default character from the database."""
    return db.get("custom.voice", "default_character", None)

def set_default_character_in_db(character: str):
    """Set the default character in the database."""
    db.set("custom.voice", "default_character", character)

async def download_voice(url: str, output_file: str):
    """Download the voice file from the given URL."""
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()
        with open(output_file, "wb") as file:
            for chunk in response.iter_content(chunk_size=1024):
                file.write(chunk)
        return output_file
    except requests.RequestException:
        return None

@Client.on_message(filters.command(["set_character"], prefix) & filters.me)
async def set_default_character(_, message: Message):
    """Set the default ElevenLabs character."""
    args = message.text.split(maxsplit=1)[1:]  # Extract arguments after the command
    if not args:
        await message.edit(
            f"<b>Usage:</b> <code>{prefix}set_character</code> <character>\n\n"
            "<b>Available characters:</b>\n" + ", ".join(AVAILABLE_CHARACTERS)
        )
        return

    character = args[0].strip().lower()
    if character not in AVAILABLE_CHARACTERS:
        await message.edit(f"Error: Invalid character `{character}`.\n\nAvailable characters:\n" + ", ".join(AVAILABLE_CHARACTERS))
        return

    set_default_character_in_db(character)
    await message.edit(f"Default character set to `{character}`.")

@Client.on_message(filters.command(["voice"], prefix) & filters.me)
async def elevenlabs_voice(_, message: Message):
    """Generate voice using the default character."""
    default_character = get_default_character()
    if not default_character:
        await message.edit(
            "<b>Error:</b> No default character is set.\n\n"
            "Set a default character using `set_character <character>` before using this command."
        )
        return

    # Extract text from arguments or replied-to message
    if message.reply_to_message and message.reply_to_message.text:
        text = message.reply_to_message.text.strip()
    else:
        args = message.text.split(maxsplit=1)[1:]  # Extract arguments after the command
        if not args:
            await message.edit(
                f"<b>Usage:</b> Reply to a message or use <code>{prefix}voice [text]</code>."
            )
            return
        text = args[0].strip()

    # Generate voice URL
    voice_url = ELEVENLABS_API_URL.format(query=text.replace(" ", "+"), character=default_character)
    await message.edit("<code>Recording...</code>")

    # Download the generated voice
    output_file = f"{default_character}_voice.mp3"
    voice_file = await download_voice(voice_url, output_file)

    if not voice_file:
        await message.edit("Error: Failed to generate voice.")
        return

    try:
        await message.reply_voice(voice_file)
    finally:
        os.remove(output_file) if os.path.exists(output_file) else None
        await message.delete()

modules_help["voice"] = {
    "voice [text]*": "Generate voice using ElevenLabs API with the default character. Set the character using `set_character`.",
    "set_character [character]*": "Set a default character to be used for the `voice` command.\n\nAvailable characters:\n" + ", ".join(AVAILABLE_CHARACTERS)
  }

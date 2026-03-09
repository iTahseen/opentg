import os
import httpx
from asyncio import sleep
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from utils.misc import modules_help, prefix
from utils.db import db

# Default Play.ht configuration
DEFAULT_PARAMS = {
    "voice": "s3://voice-cloning-zero-shot/ec7103a2-a80c-46a1-b8dd-fca1179e2b5d/original/manifest.json",
    "speed": 1.0,
}

# Estimate audio duration
def estimate_audio_duration(text: str) -> float:
    words_per_minute = 150
    return len(text.split()) / words_per_minute * 60

# Generate audio using Play.ht API
async def generate_conversational_audio(text: str):
    user_id = db.get("custom.playht", "user_id")
    api_key = db.get("custom.playht", "api_key")

    if not user_id or not api_key:
        raise ValueError("Play.ht `user_id` or `api_key` is not configured. Use `/set_playht` to set them.")

    params = {key: db.get("custom.playht", key, default) for key, default in DEFAULT_PARAMS.items()}

    headers = {
        "AUTHORIZATION": api_key,
        "X-USER-ID": user_id,
        "accept": "audio/mpeg",
        "content-type": "application/json",
    }
    data = {
        "voice": params["voice"],
        "output_format": "mp3",
        "text": text,
        "speed": params["speed"],
    }

    audio_path = "play_ht_conversational_voice.mp3"

    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.play.ht/api/v2/tts/stream", headers=headers, json=data)

        if response.status_code == 200:
            with open(audio_path, "wb") as f:
                f.write(response.content)
        else:
            raise ValueError(f"Error from Play.ht API: {response.text}")

    return audio_path

# Simulate recording action
async def fake_recording_action(client: Client, chat_id: int, text: str):
    duration = estimate_audio_duration(text)
    try:
        while duration > 0:
            await client.send_chat_action(chat_id, enums.ChatAction.RECORD_AUDIO)
            await sleep(5)
            duration -= 5
    except Exception:
        pass

# Command: Play.ht voice generation
@Client.on_message(filters.command(["playht"], prefix))
async def voice_command(client: Client, message: Message):
    if len(message.command) < 2:
        await message.edit_text(
            "**Usage:**\n"
            "`playht <text>`\n\n"
            "Generate a conversational voice message from the given text. Example:\n"
            "`playht Hello, how are you?`",
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return

    text = " ".join(message.command[1:]).strip()
    await message.delete()

    recording_task = client.loop.create_task(fake_recording_action(client, message.chat.id, text))
    try:
        audio_path = await generate_conversational_audio(text)
        if audio_path:
            await sleep(estimate_audio_duration(text) + 2)
            await client.send_voice(chat_id=message.chat.id, voice=audio_path)
            os.remove(audio_path)
    except Exception as e:
        await client.send_message(message.chat.id, f"Error: {e}", parse_mode=enums.ParseMode.MARKDOWN)
    finally:
        recording_task.cancel()

# Command: Set or view Play.ht configuration
@Client.on_message(filters.command(["set_playht"], prefix) & filters.me)
async def set_playht_config(_, message: Message):
    args = message.command
    if len(args) == 1:
        current_values = {key: db.get("custom.playht", key, default) for key, default in DEFAULT_PARAMS.items()}
        user_id = db.get("custom.playht", "user_id", "Not Set")
        api_key = db.get("custom.playht", "api_key", "Not Set")
        response = (
            "**Current Play.ht Configuration:**\n"
            f"- **user_id**: `{user_id}`\n"
            f"- **api_key**: `{api_key}`\n"
            + "\n".join([f"- **{key}**: `{value}`" for key, value in current_values.items()])
            + "\n\n**Usage:**\n"
            "`set_playht <key> <value>`\n"
            "**Keys:** `user_id`, `api_key`, `voice`, `speed`"
        )
        await message.edit_text(response, parse_mode=enums.ParseMode.MARKDOWN)
        return

    if len(args) < 3:
        await message.edit_text(
            "**Invalid Usage:**\n"
            "`set_playht <key> <value>`\n"
            "Use `/set_playht` without arguments to see the current configuration.",
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return

    key = args[1].lower()
    value = " ".join(args[2:])
    if key not in ["user_id", "api_key", *DEFAULT_PARAMS.keys()]:
        await message.edit_text(
            "**Invalid Key:**\n"
            "Allowed keys are: `user_id`, `api_key`, `voice`, `speed`.",
            parse_mode=enums.ParseMode.MARKDOWN
        )
        return

    # Convert to appropriate types
    if key == "speed":
        try:
            value = float(value)
        except ValueError:
            await message.edit_text(f"`{key}` must be a numeric value (float).", parse_mode=enums.ParseMode.MARKDOWN)
            return

    db.set("custom.playht", key, value)
    await message.edit_text(
        f"**Play.ht {key} updated successfully!**\nNew value: `{value}`",
        parse_mode=enums.ParseMode.MARKDOWN
    )

# Module help
modules_help["playht"] = {
    "play [text]*": "Generate a conversational voice with fake recording simulation.",
    "set_play": "View or update Play.ht configuration parameters.",
    "set_play <key> <value>": "Set a specific Play.ht parameter.",
}

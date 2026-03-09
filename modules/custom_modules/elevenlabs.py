import os
import httpx
import subprocess
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from utils.misc import modules_help, prefix
from utils.db import db

DEFAULT_PARAMS = {
    "voice_id": "21m00Tcm4TlvDq8ikWAM",
    "stability": 0.3,  # Lower stability for realism
    "similarity_boost": 0.9,  # Higher similarity for natural tone
}

def process_audio(input_path: str, output_path: str, speed: float, volume: float):
    """
    Process the audio file using FFmpeg.
    Adjusts speed, volume, and applies filters for natural sound.
    :param input_path: Path to the original audio file.
    :param output_path: Path to save the processed audio file.
    :param speed: Speed adjustment factor (e.g., 1.0 for normal speed, 0.9 for slower).
    :param volume: Volume adjustment factor (e.g., 1.0 for no change, 0.8 for reduced volume).
    """
    subprocess.run(
        [
            "ffmpeg",
            "-i", input_path,
            "-filter:a",
            f"atempo={speed},volume={volume},acompressor=threshold=-20dB:ratio=2.5:attack=5:release=50",
            "-vn",  # No video
            output_path,
        ],
        check=True
    )

async def generate_elevenlabs_audio(text: str):
    """
    Generate audio using ElevenLabs API with adjusted parameters.
    :param text: Text to convert to speech.
    :return: Path to the generated audio file.
    """
    api_key = db.get("custom.elevenlabs", "api_key")
    if not api_key:
        raise ValueError(f"ElevenLabs `api_key` is not configured. Use `{prefix}set_elevenlabs` to set it.")

    params = {key: db.get("custom.elevenlabs", key, DEFAULT_PARAMS[key]) for key in DEFAULT_PARAMS}

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }
    data = {
        "text": text,
        "voice_settings": {
            "stability": params["stability"],
            "similarity_boost": params["similarity_boost"],
        },
    }

    voice_id = params["voice_id"]
    original_audio_path = "elevenlabs_voice.mp3"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
            headers=headers,
            json=data,
        )

        if response.status_code == 200:
            with open(original_audio_path, "wb") as f:
                f.write(response.content)
        else:
            raise ValueError(f"Error from ElevenLabs API: {response.text}")

    return original_audio_path

@Client.on_message(filters.command(["elevenlabs", "el"], prefix))
async def elevenlabs_command(client: Client, message: Message):
    """
    Handle the ElevenLabs text-to-speech command.
    """
    if len(message.command) < 2:
        await message.edit_text(
            "**Usage:**\n"
            f"`{prefix}elevenlabs [text]`\n\n"
            "**Example:**\n"
            f"`{prefix}elevenlabs Hello, how are you?`",
            parse_mode=enums.ParseMode.MARKDOWN,
        )
        return

    text = " ".join(message.command[1:]).strip()
    await message.delete()

    try:
        # Generate audio
        original_audio_path = await generate_elevenlabs_audio(text)

        # Process the audio
        processed_audio_path = "elevenlabs_voice_processed.mp3"
        process_audio(original_audio_path, processed_audio_path, speed=0.9, volume=0.9)

        # Send the processed audio
        await client.send_voice(chat_id=message.chat.id, voice=processed_audio_path)

        # Clean up
        os.remove(original_audio_path)
        os.remove(processed_audio_path)
    except Exception as e:
        await client.send_message(message.chat.id, f"Error: {e}", parse_mode=enums.ParseMode.MARKDOWN)

@Client.on_message(filters.command(["set_elevenlabs", "set_el"], prefix) & filters.me)
async def set_elevenlabs_config(_, message: Message):
    """
    Configure ElevenLabs settings.
    """
    args = message.command
    if len(args) == 1:
        current_values = {key: db.get("custom.elevenlabs", key, DEFAULT_PARAMS[key]) for key in DEFAULT_PARAMS}
        api_key = db.get("custom.elevenlabs", "api_key", "Not Set")
        response = (
            "**ElevenLabs Configuration:**\n\n"
            f"**api_key**: `{api_key}`\n"
            + "\n".join([f"**{key}**: `{value}`" for key, value in current_values.items()])
            + "\n\n**Usage:**\n"
            f"`{prefix}set_elevenlabs [key] [value]`\n"
            "**Keys:** `api_key`, `voice_id`, `stability`, `similarity_boost`"
        )
        await message.edit_text(response, parse_mode=enums.ParseMode.MARKDOWN)
        return

    if len(args) < 3:
        await message.edit_text(
            "**Invalid Usage:**\n"
            f"`{prefix}set_elevenlabs <key> <value>`\n"
            f"Use `{prefix}set_elevenlabs` to see the current configuration.",
            parse_mode=enums.ParseMode.MARKDOWN,
        )
        return

    key = args[1].lower()
    value = " ".join(args[2:])
    if key not in ["api_key", *DEFAULT_PARAMS.keys()]:
        await message.edit_text(
            "**Invalid Key:**\n"
            "Allowed keys are: `api_key`, `voice_id`, `stability`, `similarity_boost`.",
            parse_mode=enums.ParseMode.MARKDOWN,
        )
        return

    if key in ["stability", "similarity_boost"]:
        try:
            value = float(value)
        except ValueError:
            await message.edit_text(f"`{key}` must be a numeric value (float).", parse_mode=enums.ParseMode.MARKDOWN)
            return

    db.set("custom.elevenlabs", key, value)
    await message.edit_text(
        f"**ElevenLabs {key} updated successfully!**\nNew value: `{value}`",
        parse_mode=enums.ParseMode.MARKDOWN,
    )

modules_help["elevenlabs"] = {
    "el [text]*": "Generate a voice message using ElevenLabs API.",
    "set_el": "View or update ElevenLabs configuration parameters.",
    "set_el <key> <value>": "Set a specific ElevenLabs parameter.",
}

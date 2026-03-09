import os
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.misc import modules_help, prefix
from utils.scripts import with_reply, restart
from pytgcalls import GroupCallFactory
from utils.scripts import import_library

import_library("pytgcalls", "pytgcalls==3.0.0.dev24")
import_library("yt_dlp")
import ffmpeg

GROUP_CALL = None

def init_client(func):
    async def wrapper(client, message):
        global GROUP_CALL
        if not GROUP_CALL:
            GROUP_CALL = GroupCallFactory(client).get_file_group_call()
            GROUP_CALL.enable_logs_to_console = False
        return await func(client, message)
    return wrapper

def get_reply_action(message: Message):
    return message.edit if message.from_user and message.from_user.is_self else message.reply

async def ensure_audio_reply(message: Message, reply_action):
    if not (message.reply_to_message and message.reply_to_message.audio):
        await reply_action("<b>Reply to an audio message</b>")
        return False
    return True

async def clean_up(*files):
    for file in files:
        if os.path.exists(file):
            os.remove(file)

@Client.on_message(filters.command("join", prefix))
@init_client
async def join_vc(client, message: Message):
    global GROUP_CALL
    reply_action = get_reply_action(message)

    if len(message.command) > 1 and message.command[1].lstrip("-").isdigit():
        target_chat = int(message.command[1])
        if len(str(target_chat)) == 10:
            target_chat = int(f"-100{target_chat}")
    else:
        target_chat = message.chat.id

    status_msg = await reply_action(f"<b>Joining voice chat in <code>{target_chat}</code>...</b>")
    try:
        current_file = GROUP_CALL.input_filename if GROUP_CALL.is_connected else None

        if GROUP_CALL.is_connected:
            try:
                await GROUP_CALL.stop()
                await status_msg.edit("<b>Left previous voice chat...</b>")
            except Exception:
                pass

        await GROUP_CALL.start(target_chat)

        if current_file and os.path.exists(current_file):
            GROUP_CALL.input_filename = current_file
            await status_msg.edit(
                f"<b>Moved to <code>{target_chat}</code> and continued playing music!</b>"
            )
        else:
            await status_msg.edit(
                f"<b>Joined voice chat in <code>{target_chat}</code> successfully!</b>"
            )

    except Exception as e:
        await status_msg.edit(f"<b>Failed to join VC: <code>{e}</code></b>")

@Client.on_message(filters.command("play", prefix))
@with_reply
@init_client
async def start_playout(client, message: Message):
    global GROUP_CALL
    reply_action = get_reply_action(message)
    
    if not await ensure_audio_reply(message, reply_action):
        return

    status_msg = await reply_action("<b>Joining voice chat...</b>")
    if not GROUP_CALL.is_connected:
        try:
            await GROUP_CALL.start(message.chat.id)
            await status_msg.edit("<b>Joined voice chat successfully!</b>")
        except Exception as e:
            return await status_msg.edit(f"<b>Failed to join VC: <code>{e}</code></b>")

    await status_msg.edit("<b>Downloading...</b>")
    audio_file = await message.reply_to_message.download()

    input_filename = "input.raw"
    await status_msg.edit("<b>Converting...</b>")
    ffmpeg.input(audio_file).output(
        input_filename, format="s16le", acodec="pcm_s16le", ac=2, ar="48k"
    ).overwrite_output().run()
    await clean_up(audio_file)

    GROUP_CALL.input_filename = input_filename
    await status_msg.edit(f"<b>Playing {message.reply_to_message.audio.title}</b>...")

@Client.on_message(filters.command("volume", prefix))
@init_client
async def set_volume(_, message: Message):
    reply_action = get_reply_action(message)
    if len(message.command) < 2 or not message.command[1].isdigit():
        return await reply_action("<b>Usage:</b> <code>volume [1-200]</code>")

    volume_level = int(message.command[1])
    if not 1 <= volume_level <= 200:
        return await reply_action("<b>Volume must be between 1 and 200.</b>")

    await GROUP_CALL.set_my_volume(volume_level)
    await reply_action(f"<b>Volume set to <code>{volume_level}</code></b>")

@Client.on_message(filters.command(["stop", "leave_vc"], prefix))
@init_client
async def stop_playout(_, message: Message):
    reply_action = get_reply_action(message)
    action = "leave" if "leave_vc" in message.command else "stop"

    try:
        await GROUP_CALL.stop() if action == "leave" else GROUP_CALL.stop_playout()
        await clean_up("input.raw")
        await reply_action(f"<b>{action.capitalize()}ped successfully!</b>")
    except Exception as e:
        await reply_action(f"<b>Error: <code>{e}</code></b>")
        restart()

@Client.on_message(filters.command("pause", prefix))
@init_client
async def pause(_, message: Message):
    await GROUP_CALL.pause_playout()
    await get_reply_action(message)("<b>Playback paused!</b>")

@Client.on_message(filters.command("resume", prefix))
@init_client
async def resume(_, message: Message):
    await GROUP_CALL.resume_playout()
    await get_reply_action(message)("<b>Playback resumed!</b>")

@Client.on_message(filters.command(["vmute", "vunmute"], prefix))
@init_client
async def toggle_mute(_, message: Message):
    is_mute = "vmute" in message.command
    await GROUP_CALL.set_is_mute(is_mute)
    await get_reply_action(message)(f"<b>Sound {'muted' if is_mute else 'unmuted'}!</b>")

modules_help["voice_chat"] = {
    "join [chat_id]": "Join VC in current group or by chat_id",
    "play [reply]*": "Play audio in replied message",
    "volume [1–200]": "Set the volume level",
    "leave_vc": "Leave voice chat",
    "stop": "Stop playback",
    "pause": "Pause playback",
    "resume": "Resume playback",
    "vmute": "Mute the userbot",
    "vunmute": "Unmute the userbot",
  }

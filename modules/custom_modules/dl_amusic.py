import json
import requests
import time
import os
from pyrogram import Client, filters
from pyrogram.types import Message
from utils.misc import modules_help, prefix
from utils.scripts import progress

@Client.on_message(filters.command(["amusic", "applemusic", "am"], prefix))
async def apple_music(client: Client, message: Message):
    chat_id = message.chat.id
    is_self = message.from_user and message.from_user.is_self

    query = (
        message.text.split(maxsplit=1)[1]
        if len(message.command) > 1
        else message.reply_to_message.text
        if message.reply_to_message
        else None
    )

    if not query:
        response = f"<b>Usage:</b> <code>{prefix}amusic [song name]</code>"
        await (message.edit(response) if is_self else message.reply(response))
        return

    status_message = await (
        message.edit_text(f"<code>Searching for {query} on Apple Music...</code>")
        if is_self
        else message.reply(f"<code>Searching for {query} on Apple Music...</code>")
    )

    try:
        search_result = requests.get(
            f"https://api.delirius.store/search/applemusicv2?query={query}"
        ).json()
        if not (search_result.get("status") and search_result.get("data")):
            raise ValueError("No results found")
    except Exception as e:
        await status_message.edit_text(f"<code>Failed to search: {str(e)}</code>")
        return

    song_details = search_result["data"][0]
    song_name, song_artist, song_thumb, song_url = (
        song_details["title"],
        song_details["artist"],
        song_details["image"],
        song_details["url"],
    )

    await status_message.edit_text(
        f"<code>Found: {song_name} by {song_artist}</code>\n<code>Fetching download link...</code>"
    )

    try:
        download_result = requests.get(
            f"https://api.delirius.store/download/applemusicdl?url={song_url}"
        ).json()
        if not download_result.get("status"):
            raise ValueError("Failed to fetch download link")
    except Exception as e:
        await status_message.edit_text(f"<code>Failed to fetch link: {str(e)}</code>")
        return

    song_download_link = download_result["data"].get("download")
    if not song_download_link or "undefined" in song_download_link:
        await status_message.edit_text("<code>Song isn't available.</code>")
        return

    song_name, song_thumb = download_result["data"]["name"], download_result["data"]["image"]

    await status_message.edit_text(f"<code>Downloading {song_name}...</code>")

    try:
        with open(f"{song_name}.jpg", "wb") as thumb_file:
            thumb_file.write(requests.get(song_thumb, stream=True).content)

        with open(f"{song_name}.mp3", "wb") as song_file:
            song_file.write(requests.get(song_download_link, stream=True).content)
    except Exception as e:
        await status_message.edit_text(f"<code>Failed to download: {str(e)}</code>")
        return

    await status_message.edit_text(f"<code>Uploading {song_name}...</code>")

    try:
        c_time = time.time()
        await client.send_audio(
            chat_id,
            f"{song_name}.mp3",
            caption=f"<b>Song Name:</b> {song_name}\n<b>Artist:</b> {song_artist}",
            progress=progress,
            progress_args=(status_message, c_time, f"<code>Uploading {song_name}...</code>"),
            thumb=f"{song_name}.jpg",
        )
    except Exception as e:
        await status_message.edit_text(f"<code>Failed to upload: {str(e)}</code>")
        return
    finally:
        for file in [f"{song_name}.jpg", f"{song_name}.mp3"]:
            if os.path.exists(file):
                os.remove(file)

    await status_message.delete()

modules_help["applemusic"] = {
    "amusic": "search, download, and upload songs from Apple Music"
}

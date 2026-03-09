from pyrogram import Client, filters, enums
from pyrogram.types import Message
import requests
import logging
import os
from utils.misc import modules_help, prefix

logging.basicConfig(level=logging.DEBUG)

VIDEO_API_URL = "https://api.delirius.store/anime/hentaivid"
WAIFU_API_URL = "https://api.waifu.pics/nsfw/waifu"

TEMP_DIR = "/tmp/telegram_videos"

if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

async def fetch_videos():
    try:
        response = requests.get(VIDEO_API_URL)
        response.raise_for_status()
        videos = response.json()
        logging.debug(f"Fetched videos: {videos}")
        return videos
    except requests.RequestException as e:
        logging.error(f"Error fetching videos: {e}")
        return []

async def get_videos(number_of_videos):
    videos = await fetch_videos()
    if videos:
        logging.debug(f"Selected videos: {videos[:number_of_videos]}")
        return videos[:number_of_videos]
    return []

async def save_video_to_temp(video_url):
    try:
        response = requests.get(video_url)
        response.raise_for_status()
        
        video_data = response.content
        video_file_name = os.path.join(TEMP_DIR, "video.mp4")
        
        with open(video_file_name, "wb") as f:
            f.write(video_data)
        
        return video_file_name
    except requests.RequestException as e:
        logging.error(f"Error saving video: {e}")
        return None

async def delete_temp_video(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logging.debug(f"Deleted video file: {file_path}")
    except OSError as e:
        logging.error(f"Error deleting video file: {e}")

async def fetch_waifu_image():
    try:
        response = requests.get(WAIFU_API_URL)
        response.raise_for_status()
        data = response.json()
        return data.get("url")
    except requests.RequestException as e:
        logging.error(f"Error fetching waifu image: {e}")
        return None

@Client.on_message(filters.command(["hentai", "gif"], prefix) & filters.me)
async def fetch_and_upload_videos(client: Client, message: Message):
    command_args = message.text.split(maxsplit=1)
    if len(command_args) > 1:
        try:
            number_of_videos = int(command_args[1])
        except ValueError:
            await message.reply("Invalid number of videos specified.")
            return
    else:
        number_of_videos = 1
    
    await message.edit("Processing...")
    
    videos = await get_videos(number_of_videos)
    if videos:
        for video in videos:
            video_url = video.get("video_1")
            
            if video_url:
                video_file_path = await save_video_to_temp(video_url)
                
                if video_file_path:
                    try:
                        await client.send_video(
                            chat_id=message.chat.id,
                            video=video_file_path,
                            caption=None,
                            parse_mode=enums.ParseMode.HTML
                        )
                        
                        await delete_temp_video(video_file_path)
                    except requests.RequestException as e:
                        await message.reply(f"Error sending video: {e}")
    else:
        await message.reply("No videos available.")
    
    await message.delete()

@Client.on_message(filters.command("waifu", prefix) & filters.me)
async def fetch_and_send_waifu_image(client: Client, message: Message):
    await message.edit("Fetching waifu image...")
    
    image_url = await fetch_waifu_image()
    if image_url:
        try:
            await client.send_photo(
                chat_id=message.chat.id,
                photo=image_url
            )
        except requests.RequestException as e:
            await message.reply(f"Error sending waifu image: {e}")
    else:
        await message.reply("No waifu image available.")
    
    await message.delete()

modules_help["hentai"] = {
    "hentai [number]": "Get hentai videos.",
    "waifu": "Get a waifu image."
}

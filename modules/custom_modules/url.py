import asyncio
import math
import mimetypes
import os
import time
from datetime import datetime
from io import BytesIO
from urllib.parse import unquote
import requests
import urllib3
from pyrogram import Client, enums, filters
from pyrogram.types import Message
from pySmartDL import SmartDL
from utils.config import apiflash_key
from utils.misc import modules_help, prefix
from utils.scripts import format_exc, humanbytes, progress

def generate_screenshot(url):
    api_url = f"https://api.apiflash.com/v1/urltoimage?access_key={apiflash_key}&url={url}&format=png"
    response = requests.get(api_url)
    if response.status_code == 200:
        return BytesIO(response.content)
    return None

http = urllib3.PoolManager()

@Client.on_message(filters.command("short", prefix) & filters.me)
async def short(_, message: Message):
    if len(message.command) > 1:
        link = message.text.split(maxsplit=1)[1]
    elif message.reply_to_message:
        link = message.reply_to_message.text
    else:
        await message.edit(f"<b>Usage: </b><code>{prefix}short [url to short]</code>")
        return
    r = http.request("GET", "https://clck.ru/--?url=" + link)
    await message.edit(
        r.data.decode().replace("https://", "<b>Shortened Url:</b>"),
        disable_web_page_preview=True,
    )

@Client.on_message(filters.command("urldl", prefix) & filters.me)
async def urldl(client: Client, message: Message):
    if len(message.command) > 1:
        message_id = None
        link = message.text.split(maxsplit=1)[1]
    elif message.reply_to_message:
        message_id = message.reply_to_message.id
        link = message.reply_to_message.text
    else:
        await message.edit(
            f"<b>Usage: </b><code>{prefix}urldl [url to download]</code>"
        )
        return

    await message.edit("<b>Trying to download...</b>")

    c_time = time.time()

    resp = requests.head(link, allow_redirects=True, timeout=5)
    if resp.status_code != 200:
        return await message.edit("<b>Failed to fetch request header information</b>")

    content_type = resp.headers.get("Content-Type").split(";")[0]
    extension = mimetypes.guess_extension(content_type)

    is_executable = content_type in [
        "application/octet-stream",
        "application/x-msdownload",
    ]

    url_extension = os.path.splitext(link)[1].lower()

    try:
        os.makedirs("downloads")
        if is_executable:
            file_name = "downloads/" + link.split("/")[-1]
            if not file_name.endswith(url_extension):
                file_name += url_extension
        elif extension:
            file_name = "downloads/" + link.split("/")[-1]
            if not file_name.endswith(extension):
                file_name += extension
        else:
            file_name = "downloads/" + link.split("/")[-1]
    except FileNotFoundError:
        if is_executable:
            file_name = "downloads/" + link.split("/")[-1]
            if not file_name.endswith(url_extension):
                file_name += url_extension
        elif extension:
            file_name = "downloads/" + link.split("/")[-1]
            if not file_name.endswith(extension):
                file_name += extension
        else:
            file_name = "downloads/" + link.split("/")[-1]
    except FileExistsError:
        if is_executable:
            file_name = "downloads/" + link.split("/")[-1]
            if not file_name.endswith(url_extension):
                file_name += url_extension
        elif extension:
            file_name = "downloads/" + link.split("/")[-1]
            if not file_name.endswith(extension):
                file_name += extension
        else:
            file_name = "downloads/" + link.split("/")[-1]

    downloader = SmartDL(link, file_name, progress_bar=False, timeout=10)
    start_t = datetime.now()
    try:
        downloader.start(blocking=False)
    except Exception as e:
        return await message.edit_text(format_exc(e))
    while not downloader.isFinished():
        total_length = downloader.filesize or None
        downloaded = downloader.get_dl_size(human=True)
        u_m = ""
        now = time.time()
        diff = now - c_time
        percentage = downloader.get_progress() * 100
        speed = downloader.get_speed(human=True)
        progress_str = (
            "".join(["▰" for _ in range(math.floor(percentage / 5))])
            + "".join(["▱" for _ in range(20 - math.floor(percentage / 5))])
            + f"\n<b>Progress:</b> {round(percentage, 2)}%"
        )
        eta = downloader.get_eta(human=True)
        try:
            m = "<b>Trying to download...</b>\n"
            m += f"<b>File Name:</b> <code>{unquote(link.split('/')[-1])}</code>\n"
            m += f"<b>Speed:</b> {speed}\n"
            m += f"{progress_str}\n"
            m += f"{downloaded} of {humanbytes(total_length)}\n"
            m += f"<b>ETA:</b> {eta}"
            if round(diff % 10.00) == 0 and m != u_m:
                await message.edit_text(disable_web_page_preview=True, text=m)
                u_m = m
                await asyncio.sleep(5)
        except Exception as e:
            await message.edit_text(format_exc(e))
    if os.path.exists(file_name):
        end_t = datetime.now()
        sec = (end_t - start_t).seconds
        await message.edit_text(
            f"<b>Downloaded to <code>{file_name}</code> in {sec} seconds</b>"
        )
        ms_ = await message.edit("<b>Starting Upload...</b>")
        await client.send_document(
            message.chat.id,
            file_name,
            progress=progress,
            progress_args=(ms_, c_time, "`Uploading...`"),
            caption=f"<b>File Name:</b> <code>{unquote(link.split('/')[-1])}</code>\n",
            reply_to_message_id=message_id,
        )
        await message.delete()
        os.remove(file_name)
    else:
        await message.edit("<b>Failed to download</b>")

@Client.on_message(filters.command("upload", prefix) & filters.me)
async def upload_cmd(_, message: Message):
    max_size = 512 * 1024 * 1024
    max_size_mb = 100

    min_file_age = 31
    max_file_age = 180

    ms_ = await message.edit("`Downloading...`", parse_mode=enums.ParseMode.MARKDOWN)
    c_time = time.time()

    try:
        file_name = await message.download(
            progress=progress, progress_args=(ms_, c_time, "`Downloading...`")
        )
    except ValueError:
        try:
            file_name = await message.reply_to_message.download(
                progress=progress, progress_args=(ms_, c_time, "`Downloading...`")
            )
        except ValueError:
            await message.edit("<b>File to upload not found</b>")
            return

    if os.path.getsize(file_name) > max_size:
        await message.edit(f"<b>Files longer than {max_size_mb}MB isn't supported</b>")
        if os.path.exists(file_name):
            os.remove(file_name)
        return

    await message.edit("<b>Uploading...</b>")
    with open(file_name, "rb") as f:
        response = requests.post(
            "https://x0.at",
            files={"file": f},
        )

    if response.ok:
        file_size_mb = os.path.getsize(file_name) / 1024 / 1024
        file_age = int(
            min_file_age
            + (max_file_age - min_file_age) * ((1 - (file_size_mb / max_size_mb)) ** 2)
        )
        url = response.text.strip()
        await message.edit(
            f"<b>Your URL: {url}</b>\n<b>Your file will remain live for {file_age} days</b>",
            disable_web_page_preview=True,
        )
    else:
        await message.edit(
            f"<b>API returned an error!\n{response.text}\n Not allowed</b>"
        )
    if os.path.exists(file_name):
        os.remove(file_name)

@Client.on_message(filters.command("uploader", prefix) & filters.me)
async def uploader_cmd(_, message: Message):
    max_size = 512 * 1024 * 1024
    max_size_mb = 512

    ms_ = await message.edit("`Downloading...`", parse_mode=enums.ParseMode.MARKDOWN)
    c_time = time.time()

    try:
        file_name = await message.download(
            progress=progress, progress_args=(ms_, c_time, "`Downloading...`")
        )
    except ValueError:
        try:
            file_name = await message.reply_to_message.download(
                progress=progress, progress_args=(ms_, c_time, "`Downloading...`")
            )
        except ValueError:
            await message.edit("<b>File to upload not found</b>")
            return

    if os.path.getsize(file_name) > max_size:
        await message.edit(f"<b>Files longer than {max_size_mb}MB isn't supported</b>")
        if os.path.exists(file_name):
            os.remove(file_name)
        return

    await message.edit("<b>Uploading to uploader.sh...</b>")
    try:
        with open(file_name, "rb") as f:
            response = requests.put(
                "https://uploader.sh/",
                data=f,
                headers={"Content-Type": "application/octet-stream"},
                timeout=30
            )
        if response.ok and "wget " in response.text:
            wget_url = None
            for line in response.text.splitlines():
                if line.startswith("wget "):
                    wget_url = line.split("wget ")[1].strip()
                    break
            if wget_url:
                dl_url = wget_url.replace("wget http://", "https://") + "?download=1"
                await message.edit(
                    f"<b>Your URL: {dl_url}</b>\n<b>Your file will remain live for 3 days</b>",
                    disable_web_page_preview=True,
                )
            else:
                await message.edit("<b>Couldn't parse uploader.sh response!</b>")
        else:
            await message.edit(
                f"<b>uploader.sh API returned an error!\n{response.text}</b>"
            )
    except Exception as e:
        await message.edit(f"<b>uploader.sh upload failed: {format_exc(e)}</b>")

    if os.path.exists(file_name):
        os.remove(file_name)

@Client.on_message(filters.command(["ss", "ws", "webshot"], prefix) & filters.me)
async def webshot(client: Client, message: Message):
    if len(message.command) > 1:
        url = message.text.split(maxsplit=1)[1]
        if not url.startswith("https://"):
            url = "https://" + message.text.split(maxsplit=1)[1]
    elif message.reply_to_message:
        url = message.reply_to_message.text
        if not url.startswith("https://"):
            url = "https://" + url
    else:
        await message.edit_text(
            f"<b>Usage: </b><code>{prefix}webshot/{prefix}ws [url/reply to url]</code>"
        )
        return

    chat_id = message.chat.id
    await message.edit("<b>Generating screenshot...</b>")

    try:
        screenshot_data = generate_screenshot(url)
        if screenshot_data:
            await message.delete()
            await client.send_photo(
                chat_id, screenshot_data, caption=f"Screenshot of <code>{url}</code>"
            )
        else:
            await message.edit_text(
                "<code>Failed to generate screenshot...\nMake sure url is correct</code>"
            )
    except Exception as e:
        await message.edit_text(f"An error occurred: {format_exc(e)}")

modules_help["url"] = {
    "short [url]*": "short url",
    "urldl [url]*": "download url content",
    "upload [file|reply]*": "upload file to x0.at",
    "uploader [file|reply]*": "upload file to uploader.sh",
    "webshot [link]*": "Screenshot of web page",
    "ws [reply to link]*": "Screenshot of web page",
}

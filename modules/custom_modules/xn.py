import requests
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from io import BytesIO
from utils.misc import modules_help, prefix

BASE_URL = "https://api.delirius.store"
SEARCH_ENDPOINT = "/search/xnxxsearch?query="
DOWNLOAD_ENDPOINT = "/download/xnxxdl?url="

search_results = {}

def fetch_data(endpoint, param):
    try:
        url = f"{BASE_URL}{endpoint}{requests.utils.quote(param)}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data from {url}: {e}")
        return None

def video_search(query):
    data = fetch_data(SEARCH_ENDPOINT, query)
    return data.get("data") if data and data.get("status") else None

def get_video_download_link(video_url):
    data = fetch_data(DOWNLOAD_ENDPOINT, video_url)
    if data and data.get("status"):
        return data["data"]["download"]["high"], data["data"]["gallery"]["default"]
    return None, None

@Client.on_message(filters.command(["xnxx", "xn"], prefix))
async def xnxx_command(client, message: Message):
    global search_results

    if len(message.command) < 2:
        await message.edit(f"**Usage:** `{prefix}xnxx [query]`", parse_mode=enums.ParseMode.MARKDOWN)
        return

    arg = " ".join(message.command[1:])

    if arg.isdigit():
        number = int(arg) - 1

        if message.chat.id not in search_results or number < 0 or number >= len(search_results[message.chat.id]):
            await message.edit("Use a valid number from the search results.", parse_mode=enums.ParseMode.MARKDOWN)
            return

        selected_result = search_results[message.chat.id][number]
        await message.edit(f"Downloading **{selected_result['title']}**, please wait...", parse_mode=enums.ParseMode.MARKDOWN)

        try:
            download_link, thumbnail_url = get_video_download_link(selected_result["link"])
            if not download_link:
                await message.edit("Failed to fetch the download link.", parse_mode=enums.ParseMode.MARKDOWN)
                return

            video_data = BytesIO(requests.get(download_link).content)
            video_data.name = f"{number + 1}.mp4"

            thumbnail_data = (
                BytesIO(requests.get(thumbnail_url).content) if thumbnail_url else None
            )
            if thumbnail_data:
                thumbnail_data.name = "thumbnail.jpg"

            caption = f">**Title:** {selected_result['title']}\n**Duration:** {selected_result['duration']} | **Views:** {selected_result['views']}"

            await client.send_video(
                chat_id=message.chat.id,
                video=video_data,
                thumb=thumbnail_data,
                caption=caption,
                parse_mode=enums.ParseMode.MARKDOWN
            )

            await message.delete()
        except Exception as e:
            await message.edit(f"An error occurred: {str(e)}", parse_mode=enums.ParseMode.MARKDOWN)
        return

    query = arg
    await message.edit(f"Searching for `{query}`...", parse_mode=enums.ParseMode.MARKDOWN)

    try:
        results = video_search(query)
        if not results:
            await message.edit("No results found. Please try again.", parse_mode=enums.ParseMode.MARKDOWN)
            return

        search_results[message.chat.id] = results

        results_text = "\n".join(
            [f"{i + 1}. [{item['title']}]({item['link']})\n> Duration: {item['duration']} | Views: {item['views']}" for i, item in enumerate(results[:15])]
        )
        await message.edit(
            f"**XNXX Search Results for `{query}`:**\n\n{results_text}\n\n**Usage:** `{prefix}xnxx [number]` to download a video.", 
            parse_mode=enums.ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )

    except Exception as e:
        await message.edit(f"An error occurred: {str(e)}", parse_mode=enums.ParseMode.MARKDOWN)

modules_help["xnxx"] = {
    "xnxx [query]": "Search for videos and display results from XNXX.",
    "xnxx [number]": "Download the selected video by providing its number.",
    "xn [query]": "Shortened command for `.xnxx [query]`.",
}

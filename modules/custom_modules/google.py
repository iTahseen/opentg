import os
import requests
from urllib.parse import quote
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from utils.misc import modules_help, prefix

GOOGLE_SEARCH_API = "https://api.delirius.store/search/googlesearch?query="
APIFLASH_API_URL = "https://api.apiflash.com/v1/urltoimage"
APIFLASH_API_KEY = "806cf941653948be8d8049defd086b82"

search_results = {}

@Client.on_message(filters.command(["google", "g"], prefix))
async def google_command(client, message: Message):
    global search_results

    if len(message.command) < 2:
        await message.edit(f"**Usage:** {prefix}google [query]", parse_mode=enums.ParseMode.MARKDOWN)
        return

    arg = " ".join(message.command[1:])

    if arg.isdigit():
        number = int(arg) - 1

        if message.chat.id not in search_results or number < 0 or number >= len(search_results[message.chat.id]):
            await message.edit("Use a valid number.", parse_mode=enums.ParseMode.MARKDOWN)
            return

        selected_result = search_results[message.chat.id][number]
        taking_screenshot_message = await message.edit(f"Taking a screenshot of **{selected_result['title']}**...", parse_mode=enums.ParseMode.MARKDOWN)

        try:
            screenshot_url = (
                f"{APIFLASH_API_URL}?access_key={APIFLASH_API_KEY}&url={quote(selected_result['url'])}"
            )
            screenshot_response = requests.get(screenshot_url)
            screenshot_response.raise_for_status()

            with open("screenshot.jpg", "wb") as f:
                f.write(screenshot_response.content)

            await client.send_photo(
                message.chat.id, "screenshot.jpg", caption=f"**Screenshot of:** {selected_result['title']}", parse_mode=enums.ParseMode.MARKDOWN
            )

            await taking_screenshot_message.delete()

        except Exception as e:
            await message.edit(f"An error occurred: {str(e)}", parse_mode=enums.ParseMode.MARKDOWN)
        finally:
            if "screenshot.jpg" in locals() and os.path.exists("screenshot.jpg"):
                os.remove("screenshot.jpg")
        return

    query = arg
    await message.edit(f"Searching for `{query}`...", parse_mode=enums.ParseMode.MARKDOWN)

    try:
        response = requests.get(f"{GOOGLE_SEARCH_API}{quote(query)}")
        response.raise_for_status()
        data = response.json()

        if not data.get("status"):
            await message.edit("No results. Please try again later.", parse_mode=enums.ParseMode.MARKDOWN)
            return

        search_results[message.chat.id] = data["data"]

        results_text = "\n".join(
            [f"{i + 1}. [{item['title']}]({item['url']})\n> {item['description']}" for i, item in enumerate(data["data"])]
        )
        await message.edit(
            f"**Google Search Results for `{query}`:**\n\n{results_text}\n\n**Usage:** `{prefix}google [number]` to take a screenshot.", 
            parse_mode=enums.ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )

        google_search_url = f"https://www.google.com/search?q={quote(query)}"
        screenshot_url = f"{APIFLASH_API_URL}?access_key={APIFLASH_API_KEY}&url={quote(google_search_url)}"
        screenshot_response = requests.get(screenshot_url)
        screenshot_response.raise_for_status()

        with open("google_search_page.jpg", "wb") as f:
            f.write(screenshot_response.content)

        await client.send_photo(
            message.chat.id,
            "google_search_page.jpg",
            caption=f"**Google Search Page for:** `{query}`\n[View on Google]({google_search_url})",
            parse_mode=enums.ParseMode.MARKDOWN,
        )

        os.remove("google_search_page.jpg")

    except Exception as e:
        await message.edit(f"An error occurred: {str(e)}", parse_mode=enums.ParseMode.MARKDOWN)

modules_help["google"] = {
    "google [query]": "Search Google for the provided query and display the results.",
    "google [number]": "Take a screenshot of the search result at the specified number.",
    "g [query]": "Shortened command for `.google [query]`.",
}

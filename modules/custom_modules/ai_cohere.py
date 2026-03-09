import asyncio
from utils.scripts import import_library
from utils.config import cohere_key
from utils.misc import modules_help, prefix
from utils.scripts import format_exc
from utils.db import db
from pyrogram import Client, filters, enums
from pyrogram.types import Message

cohere_lib = import_library("cohere")

co_v1, co_v2 = None, None
try:
    co_v2 = cohere_lib.ClientV2(api_key=cohere_key)
except Exception:
    pass
try:
    co_v1 = cohere_lib.Client(cohere_key)
except Exception:
    pass

COMMAND_MODEL_MAP = {
    "cohere": "command-r-plus",
    "cr": "command-a-03-2025",
    "crplus": "command-a-03-2025",
}

def build_messages(chat_history, prompt):
    messages = []
    for m in chat_history or []:
        role = "user" if m.get("role", "").upper() == "USER" else "assistant"
        messages.append({"role": role, "content": m.get("message", "")})
    messages.append({"role": "user", "content": prompt})
    return messages

@Client.on_message(filters.command(list(COMMAND_MODEL_MAP.keys()), prefix) & filters.me)
async def cohere_command(c: Client, message: Message):
    try:
        command = message.command[0].lower()
        model = COMMAND_MODEL_MAP[command]
        user_id = message.from_user.id
        chat_history = db.get_chat_history(user_id)

        prompt = (
            message.text.split(maxsplit=1)[1].strip()
            if len(message.command) > 1 else
            message.reply_to_message.text.strip()
            if message.reply_to_message else None
        )
        if not prompt:
            await message.edit_text(f"<b>Usage:</b> <code>{prefix}{command} [prompt/reply to message]</code>")
            return

        db.add_chat_history(user_id, {"role": "USER", "message": prompt})
        await message.edit_text("<code>Umm, lemme think...</code>")

        if co_v2 and model.startswith("command-a-"):
            messages = build_messages(chat_history, prompt)
            response = co_v2.chat(model=model, messages=messages)
            output = response.message.content[0].text.strip() if response.message.content else "No response generated for the given prompt."
            references = ""
        elif co_v1 and model == "command-r-plus":
            response = co_v1.chat_stream(
                chat_history=chat_history,
                model=model,
                message=prompt,
                temperature=0.3,
                tools=[{"name": "internet_search"}],
                connectors=[],
                prompt_truncation="OFF",
            )
            output, tool_message, data = "", "", []
            for event in response:
                if event.event_type == "tool-calls-chunk":
                    if event.tool_call_delta and event.tool_call_delta.text is None:
                        continue
                    tool_message += event.text
                if event.event_type == "search-results":
                    data.append(event.documents)
                if event.event_type == "text-generation":
                    output += event.text
            if tool_message:
                await message.edit_text(f"<code>{tool_message}</code>")
                await asyncio.sleep(3)
            references = ""
            if data:
                reference_dict = {}
                for item in data[0]:
                    reference_dict.setdefault(item["title"], item["url"])
                references = "".join(f"**{i}.** [{title}]({url})\n" for i, (title, url) in enumerate(reference_dict.items(), 1))
            if not output:
                output = "I can't seem to find an answer to that"
        else:
            await message.edit_text("Cohere client not available or invalid model selected.")
            return

        db.add_chat_history(user_id, {"role": "CHATBOT", "message": output})

        text = f"**Question:** `{prompt}`\n**Answer:** {output}"
        if references:
            text += f"\n\n**References:**\n{references}"
        await message.edit_text(text, parse_mode=enums.ParseMode.MARKDOWN, disable_web_page_preview=True)

    except Exception as e:
        await message.edit_text(f"An error occurred: {format_exc(e)}")

modules_help["cohere"] = {
    "cohere [query]*": "Chat with Cohere's Command-R/Command-A models. Supports chat history, references, and status updates.",
}

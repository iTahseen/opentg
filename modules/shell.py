from subprocess import Popen, PIPE, TimeoutExpired
import os
import shlex
from time import perf_counter
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.errors import MessageTooLong
from utils import modules_help, prefix

@Client.on_message(filters.command(["shell", "sh"], prefix) & filters.me)
async def shell(_, message: Message):
    if len(message.command) < 2:
        return await message.edit("<b>Specify the command in message text</b>")
    
    cmd_text = message.text.split(maxsplit=1)[1]
    cmd_args = shlex.split(cmd_text)
    
    try:
        cmd_obj = Popen(
            cmd_args,
            stdout=PIPE,
            stderr=PIPE,
            text=True,
        )
    except Exception as e:
        return await message.edit(f"<b>Error starting command:</b>\n<code>{str(e)}</code>")

    char = "#" if os.getuid() == 0 else "$"
    text = f"<b>{char}</b> <code>{cmd_text}</code>\n\n"

    await message.edit(text + "<b>Running...</b>")
    
    try:
        start_time = perf_counter()
        stdout, stderr = cmd_obj.communicate(timeout=60)
        stop_time = perf_counter()
        
        text = f"<b>{char}</b> <code>{cmd_text}</code>\n\n"
        
        if stdout:
            text += f"<b>Output:</b>\n<pre><code>{stdout}</code></pre>\n\n"
        if stderr:
            text += f"<b>Error:</b>\n<pre><code>{stderr}</code></pre>\n\n"
        
        text += f"<b>Completed in {round(stop_time - start_time, 5)} seconds with code {cmd_obj.returncode}</b>"
    except TimeoutExpired:
        cmd_obj.kill()
        text += "<b>Timeout expired (60 seconds)</b>"
    
    if len(text) > 4096:
        for i in range(0, len(text), 4096):
            await message.reply(text[i:i + 4096])
        await message.delete()
    else:
        await message.edit(text)
    
    cmd_obj.kill()

modules_help["shell"] = {
    "sh [command]*": "Execute command in shell. Example: `sh ls -la`"
}

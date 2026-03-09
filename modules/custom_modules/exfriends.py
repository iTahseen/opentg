from pyrogram import Client, filters, enums
from pyrogram.types import Message
import os
from utils.misc import modules_help, prefix

@Client.on_message(filters.command("exfriends", prefix) & filters.me)
async def fetch_info(client: Client, message: Message):
    edited_message = await message.edit("Gathering information, please wait...")

    info = "Friends Information:\n\n"
    
    async for chat in client.get_dialogs():
        if chat.chat.type == enums.ChatType.PRIVATE:
            user = await client.get_users(chat.chat.id)

            if user.is_bot:
                continue

            chat_info = f"ID: {chat.chat.id}\n"
            chat_info += f"Name: {chat.chat.first_name} {chat.chat.last_name}\n"
            chat_info += f"Username: @{chat.chat.username}\n"
            chat_info += f"Bio: {chat.chat.bio}\n" if chat.chat.bio else "Bio: Not available\n"
            phone_number = user.phone_number if user.phone_number else "Not available"
            chat_info += f"Phone Number: {phone_number}\n"
            premium_status = "Premium" if user.is_premium else "Not Premium"
            chat_info += f"Premium Status: {premium_status}\n"

            info += chat_info + "-"*20 + "\n"

    file_path = "friends_info.txt"
    with open(file_path, "w") as file:
        file.write(info)

    await client.send_document(
        chat_id=message.chat.id,
        document=file_path,
        caption="Here is the information about your friends."
    )

    os.remove(file_path)

    await edited_message.delete()

modules_help["exfriends"] = {
    "exfriends": "Export friend's detail.",
}

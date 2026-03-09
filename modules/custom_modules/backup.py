import os
import shutil
import zipfile
from datetime import datetime
from pyrogram import Client, filters, enums
from pyrogram.types import Message

# noinspection PyUnresolvedReferences
from utils.misc import modules_help, prefix
from utils.scripts import format_exc, restart
from utils.db import db
from utils import config

if config.db_type in ["mongodb", "mongo"]:
    import bson

def ensure_directory_exists(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def ensure_backup_directory():
    ensure_directory_exists("backups/")

def clean_backup_directory():
    # Remove all files inside the backups directory, including previous zips
    for root, _, files in os.walk("backups/"):
        for file in files:
            os.remove(os.path.join(root, file))

def get_timestamp():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def dump_mongo(collections, path, db_):
    for coll in collections:
        with open(os.path.join(path, f"{coll}.bson"), "wb+") as f:
            for doc in db_[coll].find():
                f.write(bson.BSON.encode(doc))

def restore_mongo(path, db_):
    for coll in os.listdir(path):
        if coll.endswith(".bson"):
            with open(os.path.join(path, coll), "rb+") as f:
                db_[coll.split(".")[0]].insert_many(bson.decode_all(f.read()))

def zip_directory(directory, zip_name):
    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(directory):
            for file in files:
                zipf.write(os.path.join(root, file), arcname=os.path.relpath(os.path.join(root, file), directory))

def unzip_directory(zip_name, extract_to):
    with zipfile.ZipFile(zip_name, "r") as zipf:
        zipf.extractall(extract_to)

async def send_backup(client, message, zip_name, caption):
    await client.send_document(
        "me",
        caption=caption,
        document=zip_name,
        parse_mode=enums.ParseMode.HTML
    )
    await message.edit("<b>Backup completed and uploaded successfully! Check your favorites.</b>", parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command(["backup", "back"], prefix) & filters.me)
async def backup(client: Client, message: Message):
    """
    Backup the database
    """
    try:
        ensure_backup_directory()
        clean_backup_directory()

        await message.edit("<b>Backing up database...</b>", parse_mode=enums.ParseMode.HTML)

        if config.db_type in ["mongo", "mongodb"]:
            dump_mongo(db._database.list_collection_names(), "backups/", db._database)
        else:
            shutil.copy(config.db_name, f"backups/{config.db_name}")

        timestamp = get_timestamp()
        zip_name = f"database_backup_{timestamp}.zip"
        zip_directory("backups/", zip_name)

        await send_backup(
            client, message, zip_name,
            "<b>Database backup complete! Type: </b><code>.restore</code> <b>in response to this message to restore the database.</b>"
        )

        clean_backup_directory()

    except Exception as e:
        await message.edit(format_exc(e), parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command(["restore", "res"], prefix) & filters.me)
async def restore(client: Client, message: Message):
    """
    Restore the database
    """
    try:
        if not message.reply_to_message or not message.reply_to_message.document:
            return await message.edit("<b>Reply to a zip file to restore the database.</b>", parse_mode=enums.ParseMode.HTML)

        if not message.reply_to_message.document.file_name.endswith(".zip"):
            return await message.edit("<b>Reply to a zip file to restore the database.</b>", parse_mode=enums.ParseMode.HTML)

        await message.edit("<b>Restoring database...</b>", parse_mode=enums.ParseMode.HTML)

        ensure_backup_directory()
        clean_backup_directory()

        zip_path = await message.reply_to_message.download(f"backups/database_restore.zip")
        unzip_directory(zip_path, "backups/")

        if config.db_type in ["mongo", "mongodb"]:
            restore_mongo("backups/", db._database)
        else:
            shutil.copy(f"backups/{config.db_name}", config.db_name)

        await message.edit("<b>Database restored successfully!</b>", parse_mode=enums.ParseMode.HTML)

        clean_backup_directory()
        restart()

    except Exception as e:
        await message.edit(format_exc(e), parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command(["backupmods", "bms"], prefix) & filters.me)
async def backupmods(client: Client, message: Message):
    """
    Backup the modules
    """
    try:
        ensure_backup_directory()
        clean_backup_directory()

        await message.edit("<b>Backing up modules...</b>", parse_mode=enums.ParseMode.HTML)

        for mod in modules_help:
            if os.path.isfile(f"modules/custom_modules/{mod}.py"):
                shutil.copy(f"modules/custom_modules/{mod}.py", f"backups/{mod}.py")

        timestamp = get_timestamp()
        zip_name = f"modules_backup_{timestamp}.zip"
        zip_directory("backups/", zip_name)

        await send_backup(
            client, message, zip_name,
            "<b>All modules backed up. Type: </b><code>.restoremods</code> <b>to restore them.</b>"
        )

        clean_backup_directory()

    except Exception as e:
        await message.edit(format_exc(e), parse_mode=enums.ParseMode.HTML)

@Client.on_message(filters.command(["restoremods", "resmods"], prefix) & filters.me)
async def restoremods(client: Client, message: Message):
    """
    Restore the modules
    """
    try:
        if not message.reply_to_message or not message.reply_to_message.document:
            return await message.edit("<b>Reply to a zip file to restore the modules.</b>", parse_mode=enums.ParseMode.HTML)

        if not message.reply_to_message.document.file_name.endswith(".zip"):
            return await message.edit("<b>Reply to a zip file to restore the modules.</b>", parse_mode=enums.ParseMode.HTML)

        await message.edit("<b>Restoring modules...</b>", parse_mode=enums.ParseMode.HTML)

        ensure_backup_directory()
        clean_backup_directory()

        zip_path = await message.reply_to_message.download(f"backups/modules_restore.zip")
        unzip_directory(zip_path, "backups/")

        ensure_directory_exists("modules/custom_modules/")

        for mod in os.listdir("backups/"):
            if mod.endswith(".py"):
                shutil.copy(f"backups/{mod}", f"modules/custom_modules/{mod}")

        await message.edit("<b>All modules restored successfully!</b>", parse_mode=enums.ParseMode.HTML)

        clean_backup_directory()
        restart()

    except Exception as e:
        await message.edit(format_exc(e), parse_mode=enums.ParseMode.HTML)

modules_help["backup"] = {
    "backup": "<b>Backup database</b>",
    "restore [reply to zip file]": "<b>Restore database</b>",
    "backupmods": "<b>Backup all mods</b>",
    "restoremods [reply to zip file]": "<b>Restore all mods</b>",
}

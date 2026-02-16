import json
import re
import asyncio
import os
from pyrogram import Client, filters, types
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Load from environment variables securely
API_ID = int(os.environ.get('TELEGRAM_API_ID'))
API_HASH = os.environ.get('TELEGRAM_API_HASH')
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID', -1001967811152))
INDEX_FILE = "file_index.json"

DELETE_AFTER = 24 * 60 * 60
DELETE_NOTICE = "This file will be deleted after 24 hours. Enjoy your movie! 🍿"
BATCH_SIZE = 5

app = Client("file_forwarder_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def normalize(text):
    if not text:
        return ""
    return re.sub(r'[\W_]+', ' ', text).lower().strip()

def find_files(query):
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            file_index = json.load(f)
    except Exception as e:
        print(f"Could not open index file: {e}")
        return []
    query_norm = normalize(query)
    results = []
    for file in file_index:
        if "message_id" not in file:
            continue
        name_norm = normalize(file.get("name", ""))
        caption_norm = normalize(file.get("caption", ""))
        if query_norm in name_norm or query_norm in caption_norm:
            results.append(file)
    return results

async def send_files_with_notice(client, chat_id, reply_to, files, batch_start, query, context_id):
    sent_file_ids = []
    if batch_start == 0:
        await client.send_message(chat_id, "Here is your file:", reply_to_message_id=reply_to)
    for file in files[batch_start:batch_start+BATCH_SIZE]:
        try:
            sent_file = await client.copy_message(
                chat_id=chat_id,
                from_chat_id=CHANNEL_ID,
                message_id=file["message_id"],
                caption=file.get("caption", "")
            )
            if sent_file is not None:
                sent_file_ids.append(sent_file.id)
            else:
                print(f"Warning: Could not copy message_id {file['message_id']} (empty, deleted, or inaccessible)")
        except Exception as e:
            print(f"Warning: Could not copy message_id {file['message_id']}: {e}")
    # Always send the delete notice after each batch
    notice_msg = await client.send_message(chat_id, DELETE_NOTICE)
    asyncio.create_task(delete_later(client, chat_id, sent_file_ids + [notice_msg.id]))
    # If there are more files, show the "see more" button
    if batch_start + BATCH_SIZE < len(files):
        markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("See more files", callback_data=f"see_more|{context_id}|{query}|{batch_start+BATCH_SIZE}")]
        ])
        await client.send_message(chat_id, f"Showing files {batch_start+1}-{min(batch_start+BATCH_SIZE, len(files))} of {len(files)}.", reply_markup=markup)
    return sent_file_ids

async def delete_later(client, chat_id, message_ids):
    await asyncio.sleep(DELETE_AFTER)
    try:
        await client.delete_messages(chat_id, message_ids)
    except Exception as e:
        print(f"Failed to delete messages: {e}")

def make_context_id(chat_id, message_id):
    return f"{chat_id}_{message_id}"

@app.on_message(filters.command("get") & filters.group)
async def get_file_handler(client, message):
    if len(message.command) < 2:
        await message.reply("Usage: /get <keyword>")
        return
    query = " ".join(message.command[1:])
    files = find_files(query)
    if not files:
        await message.reply("No files found. Please try a different keyword.")
        return
    context_id = make_context_id(message.chat.id, message.id)
    await send_files_with_notice(client, message.chat.id, message.id, files, 0, query, context_id)

@app.on_message(filters.group & ~filters.command("get"))
async def auto_file_handler(client, message):
    if message.from_user and message.from_user.is_bot:
        return
    if not message.text or len(message.text.strip()) < 3:
        return
    query = message.text.strip()
    files = find_files(query)
    if files:
        context_id = make_context_id(message.chat.id, message.id)
        await send_files_with_notice(client, message.chat.id, message.id, files, 0, query, context_id)

@app.on_callback_query()
async def on_callback_query(client, callback_query: types.CallbackQuery):
    data = callback_query.data
    if not data.startswith("see_more"):
        return
    try:
        _, context_id, query, batch_start_str = data.split("|")
        chat_id, reply_to = map(int, context_id.split("_"))
        batch_start = int(batch_start_str)
        files = find_files(query)
        if not files:
            await callback_query.answer("No more files found.", show_alert=True)
            return
        await send_files_with_notice(client, chat_id, reply_to, files, batch_start, query, context_id)
        await callback_query.answer()
    except Exception as e:
        print(f"Callback error: {e}")
        await callback_query.answer("An error occurred.", show_alert=True)

if __name__ == "__main__":
    # Validate environment variables
    if not all([API_ID, API_HASH, BOT_TOKEN]):
        print("ERROR: Missing required environment variables (TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_BOT_TOKEN)")
        exit(1)

    print("Bot is running. Use /get <keyword> or just type something in your group!")
    app.run()
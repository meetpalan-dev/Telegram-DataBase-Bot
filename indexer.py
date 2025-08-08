import nest_asyncio
nest_asyncio.apply()

import asyncio
import json
import os
from pyrogram import Client

API_ID = int(os.environ.get('TELEGRAM_API_ID'))
API_HASH = os.environ.get('TELEGRAM_API_HASH')
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID'))
INDEX_FILE = "file_index.json"

app = Client("indexer_user", api_id=API_ID, api_hash=API_HASH)

def message_to_entries(message):
    entries = []
    # List all possible media attributes you want to index
    media_types = [
        "photo", "video", "document", "audio", "voice", "animation", "sticker",
        "video_note"
    ]
    for media_type in media_types:
        media = getattr(message, media_type, None)
        if media:
            entry = {
                "type": media_type, 07
                "message_id": message.id,
                "caption": message.caption or "",
                "is_forwarded": bool(message.forward_from or message.forward_from_chat)
            }
            if hasattr(media, "file_name"):
                entry["name"] = media.file_name
            else:
                entry["name"] = f"{media_type}_{message.id}"
            entries.append(entry)
    return entries

async def main():
    file_index = []
    async with app:
        print("Fetching all messages from Channel A as USER...")
        async for message in app.get_chat_history(CHANNEL_ID):
            # Skip service messages (like pins, joins, etc.)
            if message.service:
                continue
            entries = message_to_entries(message)
            if entries:
                file_index.extend(entries)
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(file_index, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Done! {len(file_index)} files indexed and saved to {INDEX_FILE}")

if __name__ == "__main__":
    # Validate environment variables
    if not all([API_ID, API_HASH, CHANNEL_ID]):
        print("ERROR: Missing required environment variables")
        exit(1)

    asyncio.run(main())
  
else:
                print(f"Skipped message {message.id}: no media")
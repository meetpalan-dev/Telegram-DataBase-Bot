import nest_asyncio
nest_asyncio.apply()

import asyncio
import json
import os
from pathlib import Path
from typing import Dict, Optional, List
from pyrogram import Client, filters
from pyrogram.errors import MessageIdInvalid
from pyrogram.types import Message
from notifier import send_alert  # 🟡 Telegram crash alerts

# Load config from environment variables
API_ID = int(os.environ.get('TELEGRAM_API_ID'))
API_HASH = os.environ.get('TELEGRAM_API_HASH')
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
CHANNEL_ID = int(os.environ.get('CHANNEL_ID'))
INDEX_FILE = "file_index.json"

# Ensure session directory exists
os.makedirs("sessions/index", exist_ok=True)

# Initialize client
app = Client(
    name="index_session",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir="sessions/index",
    sleep_threshold=30,
    workers=4,
    in_memory=False
)

def message_to_entry(message: Message) -> Optional[Dict]:
    media_types = [
        "document", "video", "photo", 
        "audio", "voice", "animation", "sticker"
    ]

    for media_type in media_types:
        if media := getattr(message, media_type, None):
            entry = {
                "type": media_type,
                "message_id": message.id,
                "caption": message.caption or "",
                "is_forwarded": bool(message.forward_from or message.forward_from_chat),
                "date": message.date.isoformat() if message.date else None,
                "name": getattr(media, "file_name", f"{media_type}_{message.id}"),
                "size": getattr(media, "file_size", None)
            }
            return entry
    return None

def load_index() -> List[Dict]:
    try:
        if Path(INDEX_FILE).exists():
            with open(INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading index: {e}")
    return []

def save_index(index: List[Dict]) -> bool:
    try:
        temp_file = f"{INDEX_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        Path(temp_file).replace(INDEX_FILE)
        return True
    except Exception as e:
        print(f"Error saving index: {e}")
        return False

@app.on_message(filters.chat(CHANNEL_ID))
async def on_new_media(client: Client, message: Message):
    if entry := message_to_entry(message):
        index = load_index()
        if not any(e["message_id"] == entry["message_id"] for e in index):
            index.append(entry)
            if save_index(index):
                print(f"✅ Indexed: {entry['name']} (ID: {entry['message_id']})")
            else:
                print(f"❌ Failed to save index for {entry['message_id']}")

async def check_deleted_files():
    while True:
        await asyncio.sleep(300)  # Increased to 5 minutes to reduce API calls
        try:
            index = load_index()
            if not index:
                continue

            # First, verify we can access the channel
            try:
                await app.get_chat(CHANNEL_ID)
            except Exception as e:
                print(f"⚠️ Cannot access channel {CHANNEL_ID}: {e}")
                continue

            to_remove = []
            for entry in index:
                try:
                    await app.get_messages(CHANNEL_ID, entry["message_id"])
                except MessageIdInvalid:
                    print(f"🗑️ Removing deleted file: {entry['name']}")
                    to_remove.append(entry)
                except Exception as e:
                    # Skip PEER_ID_INVALID and similar errors without logging
                    if "PEER_ID_INVALID" in str(e):
                        continue
                    if "MESSAGE_ID_INVALID" in str(e):
                        print(f"🗑️ Removing invalid message: {entry['name']}")
                        to_remove.append(entry)
                        continue
                    print(f"⚠️ Error checking message {entry['message_id']}: {e}")

                # Add small delay between checks to avoid rate limiting
                await asyncio.sleep(0.1)

            if to_remove:
                index = [e for e in index if e not in to_remove]
                if not save_index(index):
                    print("❌ Failed to save index after cleanup")
                else:
                    print(f"✅ Cleaned up {len(to_remove)} invalid entries")
        except Exception as e:
            print(f"❌ Error in check_deleted_files: {e}")
            await asyncio.sleep(60)  # Wait longer on error

async def main():
    try:
        if not all([API_ID, API_HASH, BOT_TOKEN, CHANNEL_ID]):
            print("❌ Missing required environment variables")
            return

        print("🚀 Starting indexer bot...")
        await app.start()
        print("✅ Indexer bot started successfully")

        task = asyncio.create_task(check_deleted_files())
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            await app.stop()
    except Exception as e:
        print(f"🔥 FATAL ERROR: {e}")
        await send_alert(f"❗️ Indexer bot crashed:\n{e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Indexer bot stopped by user")
    except Exception as e:
        print(f"🔥 Fatal error: {e}")
        raise

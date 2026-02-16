import re
import os
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message

# Load from environment variables securely
API_ID = int(os.environ['TELEGRAM_API_ID'])
API_HASH = os.environ['TELEGRAM_API_HASH']
BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
CHANNEL_ID = -1001967811152

# Authorized users with type hints
ALLOWED_USERS: list[int] = [5885945285, 6652624735]

# Initialize client with secure settings
app = Client(
    name="forward_clean_session",  # Unique session name
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    workdir="sessions/clean_bot",  # Isolated session storage
    in_memory=False,  # Use persistent session to avoid re-authentication
    sleep_threshold=30  # Better for polling
)

# Pre-compile regex patterns for better performance
LINK_PATTERNS = [
    (re.compile(r'\[([^\]]+)\]\([^)]+\)'), r'\1'),  # Markdown links
    (re.compile(r'<a\s+href="[^"]+">([^<]+)</a>'), r'\1'),  # HTML links
    (re.compile(r'@\w+'), '@futurecowboy_bot'),  # Username mentions
    (re.compile(
        r'(https?://\S+|www\.\S+|\b\w+\.(com|net|org|in|mx|io|me|ru|to|co|cc|xyz|info|biz|online|site|us|uk|ca|de|fr|it|es|nl|cz|tv|pw|live|pro|shop|store|link|top|club|vip|fun|work|app|cloud|tech|dev|page|website|space|press|news|media|agency|solutions|systems|group|company|center|today|world|zone|site|wiki|blog|life|love)\b\S*)',
        re.IGNORECASE), ''),  # URLs
    (re.compile(r'\s+'), ' ')  # Extra spaces
]

def clean_caption(caption: str) -> str:
    """Clean caption by removing links and formatting"""
    if not caption:
        return ""

    for pattern, replacement in LINK_PATTERNS:
        caption = pattern.sub(replacement, caption)

    return caption.strip()

@app.on_message(
    filters.private &
    (filters.document | filters.video | filters.photo | 
     filters.audio | filters.voice | filters.animation | filters.sticker)
)
async def forward_and_clean(client: Client, message: Message):
    """Process and forward media with cleaned captions"""
    # Authorization check
    if message.from_user.id not in ALLOWED_USERS:
        await message.reply("⛔ You are not authorized to use this bot.")
        return

    try:
        # Process and forward
        cleaned_caption = clean_caption(message.caption)
        await client.copy_message(
            chat_id=CHANNEL_ID,
            from_chat_id=message.chat.id,
            message_id=message.id,
            caption=cleaned_caption or None  # None instead of empty string
        )
        print(f"✅ Forwarded: {cleaned_caption[:50]}...")  # Truncated output
        
        # Longer delay to avoid Telegram rate limiting and maintain order
        await asyncio.sleep(2.0)

    except Exception as e:
        print(f"❌ Error forwarding: {e}")
        await message.reply("⚠️ Failed to process your file. Please try again.")

if __name__ == "__main__":
    try:
        # Validate environment variables
        if not all([API_ID, API_HASH, BOT_TOKEN]):
            print("ERROR: Missing required environment variables for clean bot")
            exit(1)
            
        # Create session directory if needed
        os.makedirs("sessions/clean_bot", exist_ok=True)

        print("🔒 Clean bot starting - Access restricted to authorized users")
        print("✅ Clean bot started successfully and is running...")
        app.run()
        print("🔒 Clean bot stopped")
    except Exception as e:
        print(f"FATAL ERROR in clean bot: {e}")
        raise


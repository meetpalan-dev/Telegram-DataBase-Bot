# notifier.py
import aiohttp
import os
import logging

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Your Telegram bot token
CHAT_ID = os.environ.get("CHAT_ID")  # Your personal Telegram user ID

async def send_alert(message: str):
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning("🚫 Telegram alert skipped: missing BOT_TOKEN or ALERT_CHAT_ID")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=payload) as resp:
                if resp.status != 200:
                    logger.error("❌ Failed to send alert: %s", await resp.text())
    except Exception as e:
        logger.error("❗ Telegram alert error: %s", e)

# test block at the bottom of notifier.py
if __name__ == "__main__":
    import asyncio
    asyncio.run(send_alert("✅ Test alert: Telegram notifications are working!"))


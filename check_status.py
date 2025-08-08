
#!/usr/bin/env python3
"""
Check if Telegram flood wait has expired
"""

import asyncio
import os
from pyrogram import Client

async def check_flood_status():
    """Test if we can authenticate without flood wait"""
    API_ID = int(os.environ['TELEGRAM_API_ID'])
    API_HASH = os.environ['TELEGRAM_API_HASH']
    BOT_TOKEN = os.environ['TELEGRAM_BOT_TOKEN']
    
    app = Client(
        name="test_session",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=BOT_TOKEN,
        workdir="sessions/test",
        in_memory=True
    )
    
    try:
        print("Testing Telegram authentication...")
        await app.start()
        print("✅ Authentication successful! Flood wait has expired.")
        await app.stop()
        return True
    except Exception as e:
        if "FLOOD_WAIT" in str(e):
            # Extract wait time
            import re
            match = re.search(r'(\d+) seconds', str(e))
            if match:
                wait_time = int(match.group(1))
                hours = wait_time // 3600
                minutes = (wait_time % 3600) // 60
                print(f"❌ Flood wait still active. Wait {hours}h {minutes}m more.")
            else:
                print(f"❌ Flood wait still active: {e}")
        else:
            print(f"❌ Other error: {e}")
        return False

if __name__ == "__main__":
    os.makedirs("sessions/test", exist_ok=True)
    asyncio.run(check_flood_status())

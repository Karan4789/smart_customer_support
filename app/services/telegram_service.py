import asyncio
from telegram import Bot, Update
from app.config import config
from app.utils.logger import setup_logging

logger = setup_logging()

# We use a raw Bot instance for manual fetching
bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
last_update_id = 0

async def get_telegram_updates():
    """
    Manually fetches recent updates from Telegram.
    This replaces the 'polling loop' with a function we can call on demand.
    """
    global last_update_id
    try:
        # Long polling with a short timeout to return control quickly
        updates = await bot.get_updates(offset=last_update_id + 1, timeout=1)
        
        results = []
        for u in updates:
            last_update_id = u.update_id
            if u.message and u.message.text:
                results.append({
                    "update_id": u.update_id,
                    "chat_id": str(u.message.chat_id),
                    "sender": u.message.from_user.first_name,
                    "text": u.message.text
                })
        return results
    except Exception as e:
        logger.error(f"Telegram Fetch Error: {e}")
        return []

async def send_telegram_message(chat_id: str, text: str):
    """Sends a message."""
    try:
        await bot.send_message(chat_id=chat_id, text=text)
        return f"Sent to {chat_id}"
    except Exception as e:
        return f"Error: {e}"

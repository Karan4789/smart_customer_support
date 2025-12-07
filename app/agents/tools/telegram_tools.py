from telegram import Bot
from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
import asyncio
from app.config import config

# Initialize the raw bot client
bot_instance = Bot(token=config.TELEGRAM_BOT_TOKEN)

class SendTelegramMessageArgs(BaseModel):
    chat_id: str = Field(description="The numeric Telegram Chat ID to send the message to.")
    text: str = Field(description="The text content of the message.")

async def _send_telegram_message(chat_id: str, text: str) -> str:
    """Sends a message to a Telegram user."""
    try:
        await bot_instance.send_message(chat_id=chat_id, text=text)
        return f"Successfully sent Telegram message to {chat_id}"
    except Exception as e:
        return f"Error sending Telegram message: {str(e)}"

# Export the tool
send_telegram_message_tool = StructuredTool.from_function(
    func=_send_telegram_message,
    name="SendTelegramMessage",
    description="Sends a reply to a Telegram user. Requires 'chat_id' and 'text'.",
    args_schema=SendTelegramMessageArgs,
    coroutine=_send_telegram_message
)

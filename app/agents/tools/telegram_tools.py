from langchain.tools import StructuredTool
from pydantic import BaseModel, Field
from app.services.telegram_service import send_telegram_message, get_telegram_updates

# --- Tool 1: Send Message ---
class SendTelegramArgs(BaseModel):
    chat_id: str = Field(description="Telegram Chat ID")
    text: str = Field(description="Message text")

async def _send_wrapper(chat_id: str, text: str):
    return await send_telegram_message(chat_id, text)

send_telegram_message_tool = StructuredTool.from_function(
    func=_send_wrapper,
    name="SendTelegramMessage",
    description="Sends a Telegram reply.",
    args_schema=SendTelegramArgs,
    coroutine=_send_wrapper
)

# --- Tool 2: Fetch Updates (THE NEW TOOL YOU WANTED) ---
class FetchTelegramArgs(BaseModel):
    pass # No args needed

async def _fetch_wrapper():
    updates = await get_telegram_updates()
    if not updates:
        return "No new messages."
    return str(updates) # Return raw list string for LLM to parse

read_telegram_messages_tool = StructuredTool.from_function(
    func=_fetch_wrapper,
    name="FetchTelegramUpdates",
    description="Checks for new messages on Telegram. Returns a list of message objects.",
    args_schema=FetchTelegramArgs,
    coroutine=_fetch_wrapper
)

# app/agents/tools/discord_tools.py
import asyncio
from typing import List, Dict
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool 
from app.config import config
from app.services.discord_service import action_queue, get_bot

# --- Tool Models ---

class SendMessageArgs(BaseModel):
    message: str = Field(description="The content to send to Discord.")
    channel_id: str = Field(default=str(config.DISCORD_SUPPORT_CHANNEL_ID), description="Target Discord channel ID (as a string).")

class ReadMessagesArgs(BaseModel):
    limit: int = Field(default=10, description="Number of messages to read.")
    channel_id: str = Field(default=str(config.DISCORD_SUPPORT_CHANNEL_ID), description="Target Discord channel ID (as a string).")

# --- Tool Implementations ---

async def _send_discord_message(message: str, channel_id: str = str(config.DISCORD_SUPPORT_CHANNEL_ID)) -> str:
    """Queues a message to be sent by the Discord bot."""
    await get_bot()  
    future = asyncio.get_event_loop().create_future()
    await action_queue.put({
        "type": "send_message",
        "channel_id": int(channel_id), 
        "content": message,
        "future": future
    })
    return await future

async def _read_discord_channel(limit: int = 10, channel_id: str = str(config.DISCORD_SUPPORT_CHANNEL_ID)) -> str:
    """Queues a request to read messages from Discord."""
    await get_bot() 
    future = asyncio.get_event_loop().create_future()
    await action_queue.put({
        "type": "read_messages",
        "channel_id": int(channel_id), 
        "limit": limit,
        "future": future
    })
    result = await future
    return str(result)

# --- Tool Exports ---

send_discord_message_tool = StructuredTool.from_function(
    func=_send_discord_message,
    name="SendDiscordMessage",
    description="Sends a message to a specified Discord channel. Always provide the channel_id as a string.",
    args_schema=SendMessageArgs,
    coroutine=_send_discord_message
)

read_discord_channel_tool = StructuredTool.from_function(
    func=_read_discord_channel,
    name="ReadDiscordChannelHistory",
    description="Reads recent messages from a Discord channel. Always provide the channel_id as a string.",
    args_schema=ReadMessagesArgs,
    coroutine=_read_discord_channel
)

# app/services/discord_service.py
import os
import discord
import asyncio
from app.utils.logger import setup_logging
from app.config import config

# Setup logger
logger = setup_logging()

# Get credentials from environment variables
DISCORD_BOT_TOKEN = config.DISCORD_BOT_TOKEN
SUPPORT_CHANNEL_ID = config.DISCORD_SUPPORT_CHANNEL_ID

# Define the necessary intents for the bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# Initialize the bot client
bot = discord.Client(intents=intents)

# This will hold the queue passed from main.py
central_queue = None

@bot.event
async def on_ready():
    """Event handler for when the bot successfully connects to Discord."""
    logger.info(f'Discord bot logged in as {bot.user}')
    logger.info('Listening for messages in support channel...')

@bot.event
async def on_message(message):
    """Event handler for when a message is sent in a channel the bot can see."""
    # 1. Ignore messages sent by the bot itself
    if message.author == bot.user:
        return

    # 2. Only process messages from the designated support channel
    if message.channel.id != config.DISCORD_SUPPORT_CHANNEL_ID:
        return

    # 3. Normalize the message into the standard format
    normalized_message = {
        "source": "Discord",
        "sender": str(message.author),
        "message": message.content,
        "timestamp": message.created_at.isoformat(),
        "channel_id": message.channel.id,
        "reply_callback": message.channel.send # Add a way to reply later
    }
    
    logger.info(f"Received new support request from Discord user: {normalized_message['sender']}")
    
    # 4. THE KEY CHANGE: Add the message to the central queue
    if central_queue:
        await central_queue.put(normalized_message)
    else:
        logger.error("Central queue is not available. Cannot process message.")

    # Optional: Send a quick acknowledgment back to the channel
    await message.channel.send(f"Thanks, {message.author.mention}! We've received your request and will look into it.")

async def run_discord_bot(queue: asyncio.Queue):
    """Starts the Discord bot and gives it access to the central queue."""
    global central_queue
    central_queue = queue # Make the queue available to the on_message event

    if not config.DISCORD_BOT_TOKEN or not config.DISCORD_SUPPORT_CHANNEL_ID:
        logger.error("Discord bot token or channel ID is not configured. The Discord bot will not start.")
        return
    try:
        await bot.start(config.DISCORD_BOT_TOKEN)
    except discord.LoginFailure:
        logger.critical("Failed to log in to Discord. Please check your DISCORD_BOT_TOKEN.")
    except Exception as e:
        logger.critical(f"An unexpected error occurred while running the Discord bot: {e}", exc_info=True)


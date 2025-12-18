import discord
import asyncio
from app.config import config
from app.database import add_ticket  # <--- Make sure this is imported!
from app.utils.logger import setup_logging

logger = setup_logging()

# --- Singleton State ---
bot_instance = None
bot_task = None
action_queue = asyncio.Queue()

class DiscordBotClient(discord.Client):
    """A custom Discord client that processes actions from a queue."""
    
    async def setup_hook(self) -> None:
        # Start the background action processor when the bot logs in
        self.loop.create_task(self.process_actions())

    async def on_ready(self):
        logger.info(f"[DISCORD] Bot logged in as {self.user} and is ready.")
        # Signal readiness
        await action_queue.put({"type": "ready_signal"})

    
    async def on_message(self, message):
        """
        Triggered automatically when a message is sent in a channel the bot can see.
        """
        # 1. Ignore messages from the bot itself (to prevent loops)
        if message.author == self.user:
            return

        # 2. Prepare the ticket data
        sender_name = f"{message.author.name}#{message.author.discriminator}"
        ticket_data = {
            "message_id": f"discord_{message.id}",
            "sender": f"{sender_name} (ID: {message.author.id})",
            "subject": f"Discord Message from #{message.channel.name}",
            "body": message.content,
            "source": "Discord"
        }
        
        # 3. Save to DB
        # add_ticket is synchronous (sqlite3), so we wrap it in a thread
        try:
            await asyncio.to_thread(add_ticket, ticket_data)
            logger.info(f"[DISCORD SCOUT] Captured message from {sender_name}")
        except Exception as e:
            logger.error(f"[DISCORD SCOUT] Error saving ticket: {e}")
    # ------------------------

    async def process_actions(self):
        """Main loop to handle requests from the queue."""
        while True:
            action = await action_queue.get()
            action_type = action.get("type")
            future = action.get("future")

            try:
                if action_type == "send_message":
                    await self._handle_send_message(action, future)
                elif action_type == "read_messages":
                    await self._handle_read_messages(action, future)
                elif action_type == "stop":
                    await self._handle_stop(future)
                    break 
                elif action_type == "ready_signal":
                    if future and not future.done():
                        future.set_result(True)
            except Exception as e:
                logger.error(f"[DISCORD] Error processing action '{action_type}': {e}")
                if future and not future.done():
                    future.set_exception(e)
            finally:
                action_queue.task_done()

    async def _handle_send_message(self, action, future):
        channel_id = int(action.get("channel_id"))
        content = action.get("content")
        channel = self.get_channel(channel_id)
        if channel:
            await channel.send(content)
            future.set_result(f"Message sent successfully to channel {channel_id}.")
        else:
            future.set_exception(Exception(f"Channel with ID {channel_id} not found."))

    async def _handle_read_messages(self, action, future):
        channel_id = int(action.get("channel_id"))
        limit = action.get("limit", 10)
        channel = self.get_channel(channel_id)
        if channel:
            messages = []
            async for msg in channel.history(limit=limit):
                messages.append({"author": msg.author.name, "content": msg.content})
            future.set_result(messages)
        else:
            future.set_exception(Exception(f"Channel with ID {channel_id} not found."))

    async def _handle_stop(self, future):
        if future: future.set_result("Bot shutting down.")
        await self.close()

async def get_bot():
    """Ensures the bot is running and returns the instance."""
    global bot_instance, bot_task
    if bot_instance is None or not bot_instance.is_ready():
        logger.info("[DISCORD] Bot is not running. Starting it now...")
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True
        
        bot_instance = DiscordBotClient(intents=intents)
        
        ready_future = asyncio.get_event_loop().create_future()
        # We don't await the put here to avoid deadlock if queue is full (unlikely but safe)
        action_queue.put_nowait({"type": "ready_signal", "future": ready_future})

        # Start the bot in a non-blocking background task
        bot_task = asyncio.create_task(bot_instance.start(config.DISCORD_BOT_TOKEN))
        
        # Block only this specific call until the bot signals it's ready
        await ready_future
        logger.info("[DISCORD] Bot startup complete.")

    return bot_instance

async def stop_bot():
    """Gracefully stops the bot."""
    global bot_instance, bot_task
    if bot_instance and not bot_instance.is_closed():
        future = asyncio.get_event_loop().create_future()
        await action_queue.put({"type": "stop", "future": future})
        await future
        if bot_task: bot_task.cancel()
        bot_instance = None
        bot_task = None

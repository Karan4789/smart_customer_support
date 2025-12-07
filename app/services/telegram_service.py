import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from app.config import config
from app.database import add_ticket
from app.utils.logger import setup_logging

logger = setup_logging()

# Global application instance (singleton pattern)
telegram_app = None

async def telegram_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback function that triggers when a new message arrives.
    It extracts the data and saves it to the DB as a new Ticket.
    """
    if not update.message or not update.message.text:
        return

    try:
        user = update.message.from_user
        sender_name = f"{user.first_name} {user.last_name or ''}".strip()
        sender_handle = f"@{user.username}" if user.username else str(user.id)
        
        # We store the Chat ID explicitly in the 'sender' field for the tool to use later
        # Format: "tg_chat_id:123456789"
        # The Triage Agent will see this string.
        chat_id = update.message.chat_id
        
        ticket_data = {
            "message_id": f"tg_{update.message.message_id}",
            "sender": f"{chat_id}",  # Storing JUST the ID makes it easiest for the tool
            "subject": "Telegram Message", 
            "body": f"[From {sender_handle}]: {update.message.text}" # Put the name in the body
        }
        
        # Save to DB (Synchronous DB call wrapped in thread)
        await asyncio.to_thread(add_ticket, ticket_data)
        logger.info(f"[TELEGRAM LISTENER] Saved message from {sender_handle} to database.")


    except Exception as e:
        logger.error(f"[TELEGRAM LISTENER] Error processing message: {e}")

async def start_telegram_bot():
    """Starts the Telegram bot in polling mode (background task)."""
    global telegram_app
    
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("[TELEGRAM] No token found. Telegram service will not start.")
        return

    logger.info("[TELEGRAM] Starting Telegram Bot Service...")
    
    # Build the application
    telegram_app = ApplicationBuilder().token(token).build()
    
    # Add handler for text messages (ignoring commands like /start for now)
    telegram_app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), telegram_message_handler))
    
    # Run polling
    # In a proper async loop, we use initialize/start/updater.start_polling
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    
    logger.info("[TELEGRAM] Bot is now polling for messages.")

    # Keep this coroutine alive so the bot keeps running
    # We use a Future that never completes to keep the task running until cancelled
    try:
        await asyncio.Future() 
    except asyncio.CancelledError:
        logger.info("[TELEGRAM] Stopping bot...")
        await telegram_app.updater.stop()
        await telegram_app.stop()
        await telegram_app.shutdown()

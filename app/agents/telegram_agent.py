import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from app.config import config
from app.database import add_ticket
from app.utils.logger import setup_logging

logger = setup_logging()

async def telegram_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback function that triggers when a new message arrives from Telegram.
    It formats the message and saves it to the DB as a new Ticket.
    """
    if not update.message or not update.message.text:
        return

    try:
        user = update.message.from_user
        sender_name = f"{user.first_name} {user.last_name or ''}".strip()
        sender_handle = f"@{user.username}" if user.username else str(user.id)
        
        
        chat_id = update.message.chat_id
        
        sender_info = str(chat_id)
        
        
        ticket_data = {
            "message_id": f"tg_{update.message.message_id}",
            "sender": sender_info,
            "subject": f"Telegram Message from {sender_name}", # Telegram has no subject, so we make one up
            "body": update.message.text,
            "source": "Telegram" # This tells the Orchestrator to use the Telegram Tool for replies
        }
        
        # Save to DB (Synchronous DB call wrapped in thread)
        await asyncio.to_thread(add_ticket, ticket_data)
        logger.info(f"[TELEGRAM AGENT] Saved message from {sender_handle} (Chat ID: {chat_id}) to database.")

    except Exception as e:
        logger.error(f"[TELEGRAM AGENT] Error processing message: {e}")

async def start_telegram_bot():
    """
    Starts the Telegram bot in polling mode as a background task.
    This function initializes the bot and keeps it running.
    """
    token = config.TELEGRAM_BOT_TOKEN
    if not token:
        logger.warning("[TELEGRAM AGENT] No token found. Telegram agent will not start.")
        return

    logger.info("[TELEGRAM AGENT] Starting Telegram Scout Agent...")
    
    # Build the application
    application = ApplicationBuilder().token(token).build()
    
    # Add handler for text messages (ignoring commands like /start for now)
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), telegram_message_handler))
    
    # Start the bot
    await application.initialize()
    await application.start()
    
    # Start polling for updates
    # This runs in the background
    await application.updater.start_polling()
    
    logger.info("[TELEGRAM AGENT] Bot is now polling for messages.")

    # Keep this coroutine alive so the bot keeps running
    # We use a Future that never completes to keep the task running until cancelled
    try:
        await asyncio.Future() 
    except asyncio.CancelledError:
        logger.info("[TELEGRAM AGENT] Stopping bot...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

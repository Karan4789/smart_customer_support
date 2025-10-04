from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from typing import Dict

# Import all the required services
from app.services import gmail_service, llm_service, jira_service, discord_service
from app.utils.logger import setup_logging

# Setup a central logger and a shared queue for all incoming requests
logger = setup_logging()
support_queue = asyncio.Queue()

# --- Listener Tasks ---

async def gmail_listener():
    """A dedicated background task that polls Gmail for new emails."""
    while True:
        try:
            logger.info("[GMAIL LISTENER] Checking for new emails...")
            email_data = await asyncio.to_thread(gmail_service.get_latest_unread_email)
            
            if email_data:
                # Normalize the email data into the standard format
                normalized_message = {
                    "source": "Gmail",
                    "sender": email_data['sender'],
                    "message": email_data['content'],
                    "subject": email_data.get('subject', 'No Subject'),
                    "timestamp": asyncio.get_event_loop().time()
                }
                # Put the normalized message into the central queue
                await support_queue.put(normalized_message)
                logger.info(f"[GMAIL LISTENER] Queued new support request from: {email_data['sender']}")
        except Exception as e:
            logger.critical(f"[GMAIL LISTENER] Error: {e}", exc_info=True)
        
        # Wait before checking again
        await asyncio.sleep(60)

# --- Processor Task ---

async def process_support_queue():
    """The primary background task that processes all items from the central queue."""
    while True:
        try:
            # Wait for a new request to appear in the queue
            request_data = await support_queue.get()
            
            logger.info(f"[PROCESSOR] Dequeued new request from source: {request_data['source']}")

            # Analyze the request with the LLM (this logic is the same for all sources)
            logger.info("[PROCESSOR] Analyzing request with LLM...")
            analysis = await asyncio.to_thread(llm_service.analyze_and_decide_action, request_data['message'])
            
            if not analysis or not all(k in analysis for k in ['priority', 'action', 'summary', 'reply_body']):
                logger.error("[PROCESSOR] LLM analysis failed or returned invalid data.")
                support_queue.task_done()
                continue

            logger.info(f"[PROCESSOR] LLM analysis complete. Priority: {analysis['priority']}, Action: {analysis['action']}")

            # Execute the action recommended by the LLM
            if analysis['action'] == 'CREATE_TICKET':
                ticket_description = (
                    f"A new support request has been logged.\n\n"
                    f"**Customer:** {request_data['sender']}\n"
                    f"**Source:** {request_data['source']}\n"
                    f"**Priority:** {analysis['priority']}\n\n"
                    f"--- Customer's Original Message ---\n{request_data['message']}\n\n"
                    f"--- AI-Suggested Reply ---\n{analysis['reply_body']}"
                )
                ticket_key = await asyncio.to_thread(
                    jira_service.create_jira_ticket,
                    summary=analysis['summary'],
                    description=ticket_description
                )
                if ticket_key:
                    # Send an acknowledgment back to the correct channel
                    ack_body = f"Hello, thank you for reaching out. A support ticket has been created for your issue. Your Ticket ID is: **{ticket_key}**."
                    if request_data['source'] == 'Gmail':
                        await asyncio.to_thread(
                            gmail_service.send_reply,
                            to_email=request_data['sender'],
                            subject=f"Support Ticket Created: {ticket_key}",
                            message_text=ack_body
                        )
                    elif request_data['source'] == 'Discord':
                        if 'reply_callback' in request_data:
                            await request_data['reply_callback'](ack_body)
                    logger.info("[PROCESSOR] Acknowledgment sent.")
                else:
                    logger.error("[PROCESSOR] Failed to create Jira ticket.")

            elif analysis['action'] == 'SEND_REPLY':
                # Send the reply back to the correct channel
                if request_data['source'] == 'Gmail':
                    await asyncio.to_thread(
                        gmail_service.send_reply,
                        to_email=request_data['sender'],
                        subject=f"Re: {request_data.get('subject', 'Your recent query')}",
                        message_text=analysis['reply_body']
                    )
                elif request_data['source'] == 'Discord':
                    if 'reply_callback' in request_data:
                        await request_data['reply_callback'](analysis['reply_body'])
                logger.info("[PROCESSOR] Direct reply sent.")

            # Mark the task as completed in the queue
            support_queue.task_done()

        except Exception as e:
            logger.critical(f"[PROCESSOR] Unhandled error in processing loop: {e}", exc_info=True)

# --- FastAPI Application Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    logger.info("--- Application Starting Up: Launching background tasks... ---")
    
    # Create and start all concurrent tasks
    gmail_task = asyncio.create_task(gmail_listener())
    processor_task = asyncio.create_task(process_support_queue())
    # Pass the central queue to the Discord bot when starting it
    discord_task = asyncio.create_task(discord_service.run_discord_bot(support_queue))

    yield
    
    logger.info("--- Application Shutting Down ---")
    # Cleanly cancel all tasks on shutdown
    gmail_task.cancel()
    processor_task.cancel()
    discord_task.cancel()
    await asyncio.sleep(1)

app = FastAPI(lifespan=lifespan)

@app.get("/")
def home() -> Dict[str, str]:
    return {"status": "Multi-Channel Automated Support Service is running."}

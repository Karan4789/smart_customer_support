from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
# Import all the required services
from app.services import gmail_service, llm_service, jira_service
from app.utils.logger import setup_logging

# Setup logging
logger = setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    logger.info("--- Application Starting Up ---")
    task = asyncio.create_task(check_emails_periodically())
    yield
    logger.info("--- Application Shutting Down ---")
    task.cancel()
    await asyncio.sleep(1) # Give the task a moment to cancel

app = FastAPI(lifespan=lifespan)

async def check_emails_periodically():
    """The main background task that runs continuously."""
    while True:
        try:
            logger.info("[CYCLE START] Checking for new emails...")
            
            # 1. Check for new emails
            email_data = await asyncio.to_thread(gmail_service.get_latest_unread_email)
            
            if email_data:
                logger.info(f"[SUCCESS] New email found from: {email_data['sender']}")

                # 2. Call the new, smarter LLM function to get a decision
                logger.info("[INFO] Analyzing email and deciding action with LLM...")
                analysis = await asyncio.to_thread(llm_service.analyze_and_decide_action, email_data['content'])
                
                # 3. Validate the analysis from the LLM
                if not analysis or not all(k in analysis for k in ['priority', 'action', 'summary', 'reply_body']):
                    logger.error("[ERROR] LLM analysis failed or returned invalid/incomplete data.")
                    continue # Skip to the next cycle

                logger.info(f"[SUCCESS] LLM analysis complete. Priority: {analysis['priority']}, Action: {analysis['action']}")

                # 4. Execute the action recommended by the LLM
                if analysis['action'] == 'SEND_REPLY':
                    logger.info("[ACTION] Sending direct reply as per LLM instruction...")
                    await asyncio.to_thread(
                        gmail_service.send_reply,
                        to_email=email_data['sender'],
                        subject=f"Re: {email_data.get('subject', 'Your recent query')}",
                        message_text=analysis['reply_body']
                    )
                    logger.info("[SUCCESS] Reply sent.")

                elif analysis['action'] == 'CREATE_TICKET':
                    logger.info("[ACTION] Creating Jira ticket as per LLM instruction...")

                    # Compose a detailed description for the Jira ticket
                    ticket_description = (
                        f"A new support request has been logged.\n\n"
                        f"**Customer:** {email_data['sender']}\n"
                        f"**Priority:** {analysis['priority']}\n\n"
                        f"--- Customer's Original Message ---\n{email_data['content']}\n\n"
                        f"--- AI-Suggested Reply ---\n{analysis['reply_body']}"
                    )
                    
                    ticket_key = await asyncio.to_thread(
                        jira_service.create_jira_ticket,
                        summary=analysis['summary'],
                        description=ticket_description
                    )
                    
                    # If ticket creation is successful, send an acknowledgment email
                    if ticket_key:
                        ack_subject = f"Support Ticket Created: {ticket_key}"
                        ack_body = (
                            f"Hello,\n\n"
                            f"Thank you for reaching out. We have created a support ticket for your issue.\n\n"
                            f"**Your Ticket ID:** {ticket_key}\n\n"
                            f"Our team will review your request and get back to you shortly. You can reference this ticket ID in future correspondence.\n\n"
                            f"Best regards,\n"
                            f"The Support Team"
                        )
                        await asyncio.to_thread(
                            gmail_service.send_reply,
                            to_email=email_data['sender'],
                            subject=ack_subject,
                            message_text=ack_body
                        )
                        logger.info("[SUCCESS] Acknowledgment email sent.")
                    else:
                        logger.error("[ERROR] Failed to create Jira ticket. Escalation did not complete.")
                else:
                    logger.warning(f"[WARNING] Unknown action '{analysis['action']}' received from LLM. No operation performed.")
            else:
                logger.info("[INFO] No new unread emails found.")

        except Exception as e:
            logger.critical(f"[CRITICAL ERROR] The background task encountered an error: {e}")

        # Wait for 30 seconds before the next cycle
        logger.info("[CYCLE END] Waiting for 30 seconds...")
        await asyncio.sleep(30)

@app.get("/")
def home():
    return {"status": "Automated Support Service is running."}


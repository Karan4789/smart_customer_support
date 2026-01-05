import asyncio
import json
from app.agents.gmail_agent import agent_executor as gmail_scout_executor
from app.agents.triage_agent import agent_executor as triage_agent_executor
from app.agents.tools.jira_tools import create_jira_ticket_tool
from app.agents.tools.reply_tools import send_email_tool
from app.database import add_ticket, get_next_ticket, update_ticket_status
from app.utils.jsonextract import extract_json_object
from app.utils.logger import setup_logging

logger = setup_logging()

async def gmail_listener():
    """A background task that runs the Gmail Scout Agent to find and save new emails to the database."""
    while True:
        try:
            logger.info("[GMAIL LISTENER] Running Scout Agent to find new emails...")
            
            task = """
            Search for the single most recent unread email in the inbox.
            If found, get its message ID, sender, subject, and plain text body.
            Format the output as a JSON object with keys: "message_id", "sender", "subject", and "body".
            """
            
            result = await asyncio.to_thread(gmail_scout_executor.invoke, {"input": task})
            email_json_str = result.get("output", "")

            email_data = extract_json_object(email_json_str)
            if not email_data:
                logger.info("[GMAIL LISTENER] No new unread emails found or agent returned non-JSON output.")
                await asyncio.sleep(30) # Sleep longer if no email
                continue

            # --- UPDATE: Explicitly tag the source ---
            email_data['source'] = 'Gmail'
            # -----------------------------------------

            await asyncio.to_thread(add_ticket, email_data)
            logger.info(f"[GMAIL LISTENER] Saved email {email_data.get('message_id')} to database.")

        except Exception as e:
            logger.critical(f"[GMAIL LISTENER] Critical error: {e}", exc_info=True)
        
        await asyncio.sleep(15) # Sleep shorter if an email was just processed


async def orchestrator_task():
    """Polls the database for pending tickets, runs the Triage Agent, and dispatches actions."""
    while True:
        ticket = None
        try:
            ticket = await asyncio.to_thread(get_next_ticket)
            
            if not ticket:
                await asyncio.sleep(5)
                continue
            
            # Log the source so we know where it came from
            source = ticket.get('source', 'Unknown')
            logger.info(f"[ORCHESTRATOR] Processing Ticket #{ticket['id']} from {ticket['sender']} (Source: {source})")
            
            await process_ticket(ticket)

        except Exception as e:
            logger.critical(f"[ORCHESTRATOR] Unhandled error: {e}", exc_info=True)
            if ticket:
                update_ticket_status(ticket['id'], 'FAILED')
        
        await asyncio.sleep(1)


async def process_ticket(ticket: dict):
    """Contains the logic for processing a single ticket."""
    
    # --- UPDATE: Pass the source along ---
    request_data = {
        "message_id": ticket['message_id'],
        "sender": ticket['sender'],
        "subject": ticket['subject'],
        "body": ticket['body'],
        "source": ticket.get('source', 'Gmail') # Default to Gmail if missing for backward compatibility
    }
    # -------------------------------------

    # Step 1: Run Triage Agent
    triage_task = f"""
    Analyze this email and respond with a JSON object containing these keys:
    "priority", "action" ("CREATE_TICKET" or "SEND_REPLY"), "summary", "reply_body".
    Do not include any conversational text.
    Email: {json.dumps(request_data)}
    """
    
    result = await asyncio.to_thread(triage_agent_executor.invoke, {"input": triage_task})
    decision = extract_json_object(result.get("output", ""))
    
    if not decision or not all(k in decision for k in ("priority", "action", "summary", "reply_body")):
        logger.error(f"[ORCHESTRATOR] Invalid triage JSON for Ticket #{ticket['id']}. Raw: {result.get('output')}")
        update_ticket_status(ticket['id'], 'FAILED')
        return
        
    logger.info(f"[ORCHESTRATOR] Triage decision: {decision}")
    action = decision.get("action")
    
    if action == "CREATE_TICKET":
        await handle_create_ticket(ticket, request_data, decision)
    elif action == "SEND_REPLY":
        await handle_send_reply(ticket, request_data, decision)
    else:
        logger.warning(f"[ORCHESTRATOR] Unknown action from Triage Agent: {action}")
        update_ticket_status(ticket['id'], 'FAILED')


async def handle_create_ticket(ticket: dict, request_data: dict, decision: dict):
    """Handles the 'CREATE_TICKET' action."""
    logger.info("[ORCHESTRATOR] Action: CREATE_TICKET. Invoking Jira Tool.")
    
    description = (
        f"Source: {request_data.get('source')}\n"  # Include source in Jira ticket
        f"Customer: {request_data.get('sender')}\n\n"
        f"Subject: {request_data.get('subject')}\n\n"
        f"--- Original Message ---\n{request_data.get('body')}"
    )
    
    ticket_key = await asyncio.to_thread(
        create_jira_ticket_tool.func,
        summary=decision.get("summary"),
        description=description
    )
    
    if not ticket_key:
        logger.error("[ORCHESTRATOR] Jira Tool failed to create ticket.")
        update_ticket_status(ticket['id'], 'FAILED')
        return

    logger.info(f"[ORCHESTRATOR] Jira Tool success. Ticket: {ticket_key}")
    
    # --- UPDATE: Only send email Ack if source is Gmail ---
    if request_data.get('source') == 'Gmail':
        # Generate and send AI acknowledgment
        ack_body = await generate_ai_acknowledgment(request_data, triage_agent_executor)
        await asyncio.to_thread(
            send_email_tool.func,
            to=request_data.get('sender'),
            subject=f"Re: {request_data.get('subject')}",
            body=ack_body
        )
        logger.info("[ORCHESTRATOR] Sent AI acknowledgment via Reply Tool.")
    else:
        logger.info(f"[ORCHESTRATOR] Skipping email acknowledgment for source: {request_data.get('source')}")
    # -----------------------------------------------------

    update_ticket_status(ticket['id'], 'COMPLETED', triage_result=decision)


async def handle_send_reply(ticket: dict, request_data: dict, decision: dict):
    """Handles the 'SEND_REPLY' action."""
    
    source = request_data.get('source')
    
    if source == 'Gmail':
        logger.info("[ORCHESTRATOR] Action: SEND_REPLY (Gmail). Invoking Reply Tool.")
        await asyncio.to_thread(
            send_email_tool.func,
            to=request_data.get('sender'),
            subject=f"Re: {request_data.get('subject')}",
            body=decision.get("reply_body")
        )
        logger.info("[ORCHESTRATOR] Sent direct reply via Reply Tool.")
        update_ticket_status(ticket['id'], 'COMPLETED', triage_result=decision)
        
    elif source == 'Discord':
        # TODO: Implement Discord Reply Tool here
        logger.warning("[ORCHESTRATOR] Discord reply logic not yet implemented.")
        update_ticket_status(ticket['id'], 'FAILED') # Mark FAILED so we know it wasn't sent

    elif source == 'Telegram':
        # TODO: Implement Telegram Reply Tool here
        logger.warning("[ORCHESTRATOR] Telegram reply logic not yet implemented.")
        update_ticket_status(ticket['id'], 'FAILED') # Mark FAILED so we know it wasn't sent

    else:
        logger.warning(f"[ORCHESTRATOR] Unknown source '{source}'. Cannot reply.")
        update_ticket_status(ticket['id'], 'FAILED')


async def generate_ai_acknowledgment(request_data: dict, llm_executor) -> str:
    """Uses an LLM to generate a high-quality, context-aware acknowledgment email."""
    logger.info("[REPLY-GEN] Generating AI acknowledgment...")
    
    prompt = f"""
    You are a friendly and professional customer support agent.
    A customer has sent the following email to our support team.
    
    Original Email Subject: "{request_data.get('subject')}"
    Original Email Body:
    ---
    {request_data.get('body')}
    ---
    
    Your task is to write a short, reassuring, and professional email acknowledgment to the customer.
    - Acknowledge their specific issue briefly so they know you've understood.
    - Let them know that the support team has received their request and is actively reviewing it.
    - Reassure them that they will receive an update soon.
    - Keep the tone helpful, empathetic, and professional.
    - DO NOT mention any ticket ID or reference number.
    - Sign off as "Customer Support Team".
    """
    
    try:
        result = await asyncio.to_thread(llm_executor.invoke, {"input": prompt})
        ai_reply = result.get("output", "")
        
        if not ai_reply:
            logger.warning("[REPLY-GEN] AI failed to generate a reply, using template.")
            return "Thank you for reaching out. Our support team has received your request and is actively reviewing it. We will get back to you shortly."
            
        logger.info("[REPLY-GEN] Successfully generated AI acknowledgment.")
        return ai_reply
        
    except Exception as e:
        logger.error(f"[REPLY-GEN] Error during AI reply generation: {e}")
        return "Thank you for reaching out. Our support team has received your request and is actively reviewing it. We will get back to you shortly."

import asyncio
import json
from app.agents.gmail_agent import agent_executor as gmail_scout_executor
from app.agents.triage_agent import agent_executor as triage_agent_executor
from app.agents.reply_agent import generate_reply  
from app.agents.tools.jira_tools import create_jira_ticket_tool
from app.agents.tools.reply_tools import send_email_tool
# from app.agents.tools.discord_tools import send_discord_message_tool # <--- Import this when ready
from app.database import add_ticket, get_next_ticket, update_ticket_status
from app.utils.jsonextract import extract_json_object
from app.utils.logger import setup_logging

logger = setup_logging()

async def gmail_listener():
    """A background task that runs the Gmail Scout Agent."""
    while True:
        try:
            logger.info("[GMAIL LISTENER] Running Scout Agent...")
            
            # Simplified Task - We don't need complex parsing here, the agent does it
            task = """
            Search for the single most recent unread email in the inbox.
            If found, get its message ID, sender, subject, and plain text body.
            Format the output as a JSON object with keys: "message_id", "sender", "subject", and "body".
            """
            
            result = await asyncio.to_thread(gmail_scout_executor.invoke, {"input": task})
            
            # Parse Output
            try:
                # If your agent returns a Pydantic object (from our previous fix), convert it to dict
                if hasattr(result["output"], "dict"):
                     email_data = result["output"].dict()
                elif isinstance(result["output"], str):
                     email_data = extract_json_object(result["output"])
                else:
                     email_data = result["output"]
            except Exception as e:
                logger.warning(f"[GMAIL LISTENER] Failed to parse agent output: {e}")
                email_data = None

            if not email_data:
                await asyncio.sleep(30)
                continue

            email_data['source'] = 'Gmail'
            
            try:
                await asyncio.to_thread(add_ticket, email_data)
                logger.info(f"[GMAIL LISTENER] Saved email {email_data.get('message_id')}")
            except Exception as e:
                # If it's a unique constraint error, just log a warning and continue
                if "UNIQUE constraint failed" in str(e):
                    logger.warning(f"[GMAIL LISTENER] Duplicate email found ({email_data.get('message_id')}). Skipping.")
                    await asyncio.sleep(30) # Sleep and try again later
                    continue
                else:
                    raise e # Re-raise real errors

        except Exception as e:
            logger.critical(f"[GMAIL LISTENER] Error: {e}", exc_info=True)
        
        await asyncio.sleep(15)


async def orchestrator_task():
    """Polls DB and runs Triage -> Action -> Reply flow."""
    while True:
        ticket = await asyncio.to_thread(get_next_ticket)
        if not ticket:
            await asyncio.sleep(5)
            continue

        try:
            logger.info(f"[ORCHESTRATOR] Processing Ticket #{ticket['id']} ({ticket['source']})")
            await process_ticket(ticket)
        except Exception as e:
            logger.critical(f"[ORCHESTRATOR] Error processing ticket #{ticket['id']}: {e}", exc_info=True)
            update_ticket_status(ticket['id'], 'FAILED')
        
        await asyncio.sleep(1)


async def process_ticket(ticket: dict):
    """
    Core Logic:
    1. Triage (Decide)
    2. Execute Action (Jira)
    3. Generate Reply (Reply Agent)
    4. Send Reply (Tools)
    """
    
    # --- Step 1: Triage (Decision Only) ---
    triage_task = f"""
    You are a triage system. Analyze this support request.
    
    Input: {json.dumps(ticket, default=str)}
    
    REQUIRED OUTPUT FORMAT (JSON):
    {{
        "priority": "High" | "Normal" | "Low",
        "action": "CREATE_TICKET" | "SEND_REPLY",
        "summary": "Short title of the issue"
    }}
    
    RULES:
    1. If the issue is a Bug, Error, Payment Failure, or Urgent -> Set "action": "CREATE_TICKET".
    2. If the issue is a Question, Feedback, or General Inquiry -> Set "action": "SEND_REPLY".
    3. "action" MUST be exactly "CREATE_TICKET" or "SEND_REPLY". Do not use any other text.
    """
    
    triage_result = await asyncio.to_thread(triage_agent_executor.invoke, {"input": triage_task})
    decision = extract_json_object(triage_result.get("output", ""))
    
    if not decision:
        logger.error(f"[ORCHESTRATOR] Triage failed for #{ticket['id']}")
        update_ticket_status(ticket['id'], 'FAILED')
        return

    action = decision.get("action")
    summary = decision.get("summary")
    logger.info(f"[ORCHESTRATOR] Triage Decision: {action} | {summary}")

    # --- Step 2: Execute Action ---
    action_details = ""
    
    if action == "CREATE_TICKET":
        # Create Jira Ticket
        ticket_key = await asyncio.to_thread(
            create_jira_ticket_tool.func,
            summary=summary,
            description=f"Source: {ticket['source']}\n\n{ticket['body']}"
        )
        if ticket_key:
            action_details = f"Created Jira Ticket {ticket_key}"
        else:
            action_details = "Failed to create ticket (system error)"
            
    elif action == "SEND_REPLY":
        action_details = "Decided to reply directly (No ticket created)"

    # --- Step 3: Generate Reply (The Writer) ---
    # We use the specialized Reply Agent here!
    reply_body = await generate_reply(
        sender=ticket['sender'],
        summary=summary,
        action_taken=action_details,
        original_body=ticket['body'],
        platform=ticket['source']
    )

    # --- Step 4: Send the Reply ---
    send_success = False
    
    if ticket['source'] == 'Gmail':
        # Use Gmail Tool
        try:
            await asyncio.to_thread(
                send_email_tool.func,
                to=ticket['sender'],
                subject=f"Re: {ticket['subject']}",
                body=reply_body
            )
            send_success = True
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    elif ticket['source'] == 'Discord':
        # Use Discord Tool
        # Assuming ticket['message_id'] stores "discord_123456"
        # and we need to reply to the channel. 
        # For now, we might just post to the support channel.
        try:
             # await send_discord_message_tool.ainvoke(...) 
             # (Add this implementation when you import the tool)
             logger.info(f"Would send Discord message: {reply_body[:50]}...")
             send_success = True 
        except Exception as e:
             logger.error(f"Failed to send Discord msg: {e}")

    # --- Finalize ---
    if send_success:
        update_ticket_status(ticket['id'], 'COMPLETED', triage_result=decision)
        logger.info(f"[ORCHESTRATOR] Ticket #{ticket['id']} Completed.")
    else:
        update_ticket_status(ticket['id'], 'FAILED')

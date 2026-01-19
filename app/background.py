import asyncio
import json
from app.agents.gmail_agent import agent_executor as gmail_scout_executor
from app.agents.triage_agent import agent_executor as triage_agent_executor
from app.agents.reply_agent import generate_reply  
from app.agents.tools.jira_tools import create_jira_ticket_tool
from app.agents.tools.reply_tools import send_email_tool
from app.agents.tools.discord_tools import send_discord_message_tool 
from app.agents.tools.telegram_tools import send_telegram_message_tool
from app.config import config
from app.database import add_ticket, get_next_ticket, update_ticket_status
from app.utils.jsonextract import extract_json_object
from app.utils.logger import setup_logging

logger = setup_logging()

async def gmail_listener():
    """A background task that runs the Gmail Scout Agent."""
    while True:
        try:
            logger.info("[GMAIL LISTENER] Running Scout Agent...")
            
            task = """
            Search for the single most recent email matching: 'in:inbox category:primary is:unread -from:me'.
            Output JSON with keys: "message_id", "sender", "subject", "body".
            """
            
            result = await asyncio.to_thread(gmail_scout_executor.invoke, {"input": task})
            
            try:
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
                if "UNIQUE constraint failed" in str(e):
                    logger.warning(f"[GMAIL LISTENER] Duplicate email found ({email_data.get('message_id')}). Skipping.")
                    await asyncio.sleep(30)
                    continue
                else:
                    raise e 

        except Exception as e:
            logger.critical(f"[GMAIL LISTENER] Error: {e}", exc_info=True)
        
        await asyncio.sleep(30)


async def orchestrator_task():
    """Polls DB and runs Triage -> Action -> Reply flow."""
    while True:
        ticket = await asyncio.to_thread(get_next_ticket)
        if not ticket:
            await asyncio.sleep(10)
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
    triage_result = await asyncio.to_thread(
        triage_agent_executor.invoke, 
        {"input": json.dumps(ticket, default=str)}
    )
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
            logger.info(f"[ORCHESTRATOR] Sent email reply to {ticket['sender']}")
        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    elif ticket['source'] == 'Discord':
        # Use Discord Tool
        try:
             target_channel = str(config.DISCORD_SUPPORT_CHANNEL_ID)
             logger.info(f"Sending Discord reply to channel {target_channel}...")
             await send_discord_message_tool.coroutine(
                 message=f"**Replying to {ticket['sender']}:**\n{reply_body}",
                 channel_id=target_channel
             )
             send_success = True 
             logger.info(f"[ORCHESTRATOR] Sent Discord reply to channel {target_channel}")
        except Exception as e:
             logger.error(f"Failed to send Discord msg: {e}")

    elif ticket['source'] == 'Telegram':
        # Use Telegram Tool
        try:
             # In Telegram, the sender IS the chat ID
             chat_id = ticket['sender']
             logger.info(f"Sending Telegram reply to {chat_id}...")
             
             await send_telegram_message_tool.coroutine(
                 chat_id=chat_id,
                 text=reply_body
             )
             send_success = True
             logger.info(f"[ORCHESTRATOR] Sent Telegram reply to {chat_id}")
        except Exception as e:
             logger.error(f"Failed to send Telegram msg: {e}")

    # --- Finalize ---
    if send_success:
        update_ticket_status(ticket['id'], 'COMPLETED', triage_result=decision)
        logger.info(f"[ORCHESTRATOR] Ticket #{ticket['id']} Completed.")
    else:
        update_ticket_status(ticket['id'], 'FAILED')

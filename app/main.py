# main.py

import asyncio
import json
from contextlib import asynccontextmanager
from typing import Dict
import json, re
from fastapi import FastAPI

# --- AGENT AND TOOL IMPORTS ---
# We import the agent executors and the specific tools, NOT the underlying services.
from app.agents.gmail_agent import agent_executor as gmail_scout_executor
from app.agents.triage_agent import agent_executor as triage_agent_executor
from app.agents.tools.jira_tools import create_jira_ticket_tool
from app.agents.tools.reply_tools import send_email_tool 
from app.utils.jsonextract import extract_json_object
from app.utils.logger import setup_logging


# --- Setup Logging and Queues ---
logger = setup_logging()
support_queue = asyncio.Queue()

# --- Listener Task (Agent-driven) ---

async def gmail_listener():
    """A background task that runs the Gmail Scout Agent to find and queue new emails."""
    while True:
        try:
            logger.info("[GMAIL LISTENER] Running Scout Agent to find new emails...")
            
            # The high-level task for the scout agent
            task = """
            Search for the single most recent unread email in the inbox.
            If found, get its message ID, sender, subject, and plain text body.
            Format the output as a JSON object with keys: "message_id", "sender", "subject", and "body".
            """
            
            result = await asyncio.to_thread(gmail_scout_executor.invoke, {"input": task})
            email_json_str = result.get("output", "")

            email_data = extract_json_object(email_json_str)
            if not email_data:
                logger.warning("[GMAIL LISTENER] Agent returned non-JSON output; skipping this cycle.")
                await asyncio.sleep(15)
                continue

            email_data["source"] = "Gmail"
            await support_queue.put(email_data)

        except Exception as e:
            logger.critical(f"[GMAIL LISTENER] Critical error: {e}", exc_info=True)
        
        await asyncio.sleep(60)
        
# --- Helper Function for AI Acknowledgment Generation ---

async def generate_ai_acknowledgment(request_data: Dict, ticket_key: str, llm_executor) -> str:
    """
    Uses an LLM to generate a high-quality, context-aware acknowledgment email.
    """
    logger.info(f"[REPLY-GEN] Generating AI acknowledgment for ticket {ticket_key}...")
    
    # Craft a powerful prompt for the LLM
    prompt = f"""
    You are a friendly and professional customer support agent.
    A customer has sent the following email, and a support ticket has just been created for them.
    
    Original Email Subject: "{request_data.get('subject')}"
    Original Email Body:
    ---
    {request_data.get('body')}
    ---
    
    The new support ticket ID is: {ticket_key}
    
    Your task is to write a short, reassuring, and professional email acknowledgment to the customer.
    - Acknowledge their specific issue briefly so they know you've understood.
    - Clearly provide them with their ticket ID ({ticket_key}).
    - Let them know that the team will review their issue and get back to them.
    - Keep the tone helpful and empathetic.
    """
    
    try:
        result = await asyncio.to_thread(llm_executor.invoke, {"input": prompt})
        ai_reply = result.get("output", "")
        
        # A fallback in case the AI fails
        if not ai_reply:
            logger.warning("[REPLY-GEN] AI failed to generate a reply, using template.")
            return f"Thank you for your request. A support ticket has been created with the ID: {ticket_key}. Our team will review it shortly."
            
        logger.info("[REPLY-GEN] Successfully generated AI acknowledgment.")
        return ai_reply
        
    except Exception as e:
        logger.error(f"[REPLY-GEN] Error during AI reply generation: {e}")
        # Return a safe fallback template on error
        return f"Thank you for your request. A support ticket has been created for your issue. Your Ticket ID is: {ticket_key}."


# --- Orchestrator Task (The "Agent Flow") ---

async def orchestrator_task():
    """Takes items from the queue, runs the Triage Agent, and dispatches to the correct tool."""
    while True:
        try:
            request_data = await support_queue.get()
            logger.info(f"[ORCHESTRATOR] Dequeued request from: {request_data['source']}")

            # Step 1: Run Triage Agent to get a decision
            triage_task = f"""
            Analyze this email and respond with a JSON object containing these keys:
            "priority", "action" ("CREATE_TICKET" or "SEND_REPLY"), "summary", "reply_body".
            Do not include any conversational text.
            Email: {json.dumps(request_data)}
            """
            result = await asyncio.to_thread(triage_agent_executor.invoke, {"input": triage_task})
            decision = extract_json_object(result.get("output", ""))
            if not decision or not all(k in decision for k in ("priority","action","summary","reply_body")):
                logger.error("[ORCHESTRATOR] Invalid triage JSON. Raw: %s", result.get("output"))
                support_queue.task_done()
                continue
            logger.info(f"[ORCHESTRATOR] Triage decision: {decision}")

            # Step 2: Dispatch to the correct TOOL based on the agent's decision
            action = decision.get("action")
            
            if action == "CREATE_TICKET":
                logger.info("[ORCHESTRATOR] Action: CREATE_TICKET. Invoking Jira Tool.")
                description = (
                    f"Customer: {request_data.get('sender')}\n\n"
                    f"Subject: {request_data.get('subject')}\n\n"
                    f"--- Original Message ---\n{request_data.get('body')}"
                )
                
                # Call the tool's underlying function directly
                ticket_key = await asyncio.to_thread(
                    create_jira_ticket_tool.func,
                    summary=decision.get("summary"),
                    description=description
                )
                
                if ticket_key:
                    logger.info(f"[ORCHESTRATOR] Jira Tool success. Ticket: {ticket_key}")
                    # Send acknowledgment using the Reply Tool
                    ack_body = await generate_ai_acknowledgment(request_data, ticket_key, triage_agent_executor)
                    await asyncio.to_thread(
                        send_email_tool.func,
                        to=request_data.get('sender'),
                        subject=f"Support Ticket Created: {ticket_key}",
                        body=ack_body
                    )
                    logger.info("[ORCHESTRATOR] Sent acknowledgment via Reply Tool.")
                else:
                    logger.error("[ORCHESTRATOR] Jira Tool failed to create ticket.")

            elif action == "SEND_REPLY":
                logger.info("[ORCHESTRATOR] Action: SEND_REPLY. Invoking Reply Tool.")
                await asyncio.to_thread(
                    send_email_tool.func,
                    to=request_data.get('sender'),
                    subject=f"Re: {request_data.get('subject')}",
                    body=decision.get("reply_body")
                )
                logger.info("[ORCHESTRATOR] Sent direct reply via Reply Tool.")

            else:
                logger.warning(f"[ORCHESTRATOR] Unknown action from Triage Agent: {action}")

            support_queue.task_done()

        except Exception as e:
            logger.critical(f"[ORCHESTRATOR] Unhandled error: {e}", exc_info=True)


# --- FastAPI Application Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    logger.info("--- 🚀 Application Starting Up: Launching Agentic Workflow... ---")
    
    gmail_task = asyncio.create_task(gmail_listener())
    orchestrator = asyncio.create_task(orchestrator_task())

    yield
    
    logger.info("--- 🛑 Application Shutting Down ---")
    gmail_task.cancel()
    orchestrator.cancel()
    await asyncio.sleep(1)


app = FastAPI(lifespan=lifespan)

@app.get("/")
def home() -> Dict[str, str]:
    return {"status": "Multi-Channel AI Support Agent Service is running."}

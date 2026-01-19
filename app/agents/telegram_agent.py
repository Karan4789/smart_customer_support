import os
import asyncio
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_groq import ChatGroq
from langchain import hub
from app.agents.tools.telegram_tools import send_telegram_message_tool, read_telegram_messages_tool
from app.services.telegram_service import get_telegram_updates
from app.database import add_ticket
from app.utils.logger import setup_logging

# --- 1. Setup ---
logger = setup_logging()
load_dotenv()

# Initialize LLM
groq_api_key = os.getenv("GROQ_API_KEY")
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=groq_api_key)

# --- 2. Configure Tools ---
tools = [send_telegram_message_tool, read_telegram_messages_tool]
prompt = hub.pull("hwchase17/openai-tools-agent")

# --- 3. Create the Agent (for complex tasks) ---
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# --- 4. AI Agent Function (for complex tasks) ---
async def run_telegram_agent(task: str):
    """Use this for complex Telegram tasks that need AI decision-making."""
    logger.info(f"🤖 Telegram Agent Task: {task}")
    return await agent_executor.ainvoke({"input": task})

# --- 5. Scout Agent Function (for message listening) ---
async def run_telegram_scout_agent():
    """Polls Telegram for new messages and saves them to DB."""
    logger.info("[TELEGRAM SCOUT] Starting...")
    
    while True:
        try:
            updates = await get_telegram_updates()
            
            for update in updates:
                try:
                    ticket_data = {
                        "message_id": f"telegram_{update['update_id']}",
                        "sender": update['chat_id'],
                        "subject": f"Telegram message from {update['sender']}",
                        "body": update['text'],
                        "source": "Telegram"
                    }
                    
                    await asyncio.to_thread(add_ticket, ticket_data)
                    logger.info(f"[TELEGRAM SCOUT] Captured message from {update['sender']}")
                    
                except Exception as e:
                    if "UNIQUE constraint failed" in str(e):
                        logger.warning(f"[TELEGRAM SCOUT] Duplicate message. Skipping.")
                    else:
                        logger.error(f"[TELEGRAM SCOUT] Error saving ticket: {e}")
            
        except Exception as e:
            logger.critical(f"[TELEGRAM SCOUT] Error: {e}", exc_info=True)
        
        await asyncio.sleep(5)

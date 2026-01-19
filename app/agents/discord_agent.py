# app/agents/discord_agent.py
import os
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_groq import ChatGroq
from langchain import hub
from app.agents.tools.discord_tools import send_discord_message_tool, read_discord_channel_tool
from app.services.discord_service import get_bot
from app.database import add_ticket
from app.utils.logger import setup_logging
import asyncio

logger = setup_logging()

# --- 1. Setup ---
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("❌ GROQ_API_KEY not found in .env file.")

# Initialize LLM
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=groq_api_key)

# --- 2. Configure Tools ---
tools = [send_discord_message_tool, read_discord_channel_tool]

# --- 3. Create the Agent  ---
prompt = hub.pull("hwchase17/openai-tools-agent")
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# --- 4. AI Agent Function  ---
async def run_discord_agent(task: str):
    """Use this for complex Discord tasks that need AI decision-making."""
    logger.info(f"🤖 Discord Agent received task: {task}")
    try:
        result = await agent_executor.ainvoke({"input": task})
        return result["output"]
    except Exception as e:
        return f"❌ Error running Discord Agent: {e}"

# --- 5. Scout Agent Function  ---
async def handle_discord_message(message):
    """Callback function to process incoming Discord messages."""
    sender_name = f"{message.author.name}#{message.author.discriminator}"
    
    try:
        ticket_data = {
            "message_id": f"discord_{message.id}",
            "sender": f"{sender_name} (ID: {message.author.id})",
            "subject": f"Discord Message from #{message.channel.name}",
            "body": message.content,
            "source": "Discord"
        }
        
        await asyncio.to_thread(add_ticket, ticket_data)
        logger.info(f"[DISCORD SCOUT] Captured message from {sender_name}")
        
    except Exception as e:
        if "UNIQUE constraint failed" in str(e):
            logger.warning(f"[DISCORD SCOUT] Duplicate message. Skipping.")
        else:
            logger.error(f"[DISCORD SCOUT] Error saving ticket: {e}")

async def run_discord_scout_agent():
    """Starts the Discord bot to listen for messages and save to DB."""
    logger.info("[DISCORD SCOUT] Starting...")
    try:
        # Import here to avoid circular dependency
        from app.services.discord_service import set_message_callback
        
        # Register our message handler
        set_message_callback(handle_discord_message)
        
        # Start the bot
        bot = await get_bot()
        
        # Keep the task alive - the bot runs in the background
        while True:
            await asyncio.sleep(60)
    except Exception as e:
        logger.critical(f"[DISCORD SCOUT] Error: {e}", exc_info=True)

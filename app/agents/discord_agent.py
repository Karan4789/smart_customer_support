import os
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain import hub
from app.agents.tools.discord_tools import send_discord_message_tool, read_discord_channel_tool

# --- 1. Setup ---
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("❌ GEMINI_API_KEY not found in .env file.")

# Initialize LLM (Using Gemini as the brain)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", # Or gemini-pro, depending on your preference
    temperature=0,
    google_api_key=gemini_api_key
)

# --- 2. Configure Tools ---
# These are the tools we created in the previous step
tools = [send_discord_message_tool, read_discord_channel_tool]

# --- 3. Create the Agent ---
# We pull the standard OpenAI tools prompt from LangChain Hub
# This prompt tells the LLM how to select and use the tools provided
prompt = hub.pull("hwchase17/openai-tools-agent")

agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# --- 4. Helper Function to Run the Agent ---
async def run_discord_agent(task: str):
    """
    Runs the Discord agent with a specific task.
    Example tasks:
    - "Read the last 5 messages from channel 12345 and summarize them."
    - "Send a message to channel 12345 saying 'Hello World!'"
    """
    print(f"🤖 Discord Agent received task: {task}")
    try:
        # invoke is synchronous by default in LangChain, but since our tools are async,
        # we generally wrap this or use ainvoke. For simplicity in this architecture,
        # we'll rely on the tools' internal async handling or use ainvoke if your LangChain version prefers it.
        result = await agent_executor.ainvoke({"input": task})
        return result["output"]
    except Exception as e:
        return f"❌ Error running Discord Agent: {e}"

# --- Test Block (Optional) ---
if __name__ == "__main__":
    import asyncio
    # Simple test to see if it loads (requires the Discord Service to be running separately)
    # Note: This won't fully work in isolation without the DiscordService loop running.
    print("Discord Agent loaded. Use run_discord_agent() to execute tasks.")

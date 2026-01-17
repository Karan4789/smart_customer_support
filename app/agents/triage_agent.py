import os
import json
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.utils.logger import setup_logging

# --- Setup Logging ---
logger = setup_logging()

# --- 1. Setup ---
load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("❌ GROQ_API_KEY not found in .env file.")

# Initialize LLM
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0, api_key=groq_api_key)

# --- 2. Define the System Prompt ---
# This "Brain" logic is now baked into the agent itself.
triage_system_prompt = """
You are an expert customer support triage AI.

Your goal is to analyze the user's support request and classify it into one of two categories:

1. **Technical Issue / Bug / Urgent / Payment Problem**
   -> Set "action" to "CREATE_TICKET".
   -> Set "priority" to "High".
   -> "summary" should be a clear title suitable for an engineering ticket.

2. **General Question / Feature Request / Feedback / Low Urgency**
   -> Set "action" to "SEND_REPLY".
   -> Set "priority" to "Normal" or "Low".
   -> "summary" should be a short topic summary.

REQUIRED OUTPUT FORMAT:
You must respond with ONLY a valid JSON object. Do not add any conversational text.
{{
  "priority": "High" | "Normal" | "Low",
  "action": "CREATE_TICKET" | "SEND_REPLY",
  "summary": "Short title of the issue"
}}

CRITICAL RULES:
- "action" must be EXACTLY "CREATE_TICKET" or "SEND_REPLY".
- Do not wrap the output in markdown code blocks. Just return the raw JSON string.
"""

# --- 3. Create the Agent with Custom Prompt ---
# Instead of pulling from hub, we build the prompt template manually to include our instructions.
prompt = ChatPromptTemplate.from_messages([
    ("system", triage_system_prompt),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

# This agent has no tools, it only uses the LLM to think.
tools = []
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# --- 4. Test Block (Run this file directly to test) ---
if __name__ == "__main__":
    
    # Example Test Data
    test_ticket = {
      "message_id": "12345",
      "sender": "customer@example.com",
      "subject": "Urgent: Billing Issue",
      "body": "My payment failed but my card was charged. My account is locked."
    }
    
    # Convert dict to string for the agent input
    ticket_str = json.dumps(test_ticket)
    
    logger.info("\n🤔 --- Running Triage Agent (Test Mode) ---")
    
    # Notice: We only pass the data now! The instructions are already inside the agent.
    result = agent_executor.invoke({"input": ticket_str})
    
    logger.info("\n✅ --- Triage Complete ---")
    logger.info(f"Raw Output: {result['output']}")
    
    try:
        decision = json.loads(result["output"])
        logger.info("\n📋 Parsed Decision:")
        logger.info(json.dumps(decision, indent=2))
    except json.JSONDecodeError:
        logger.error("❌ Failed to parse JSON output.")

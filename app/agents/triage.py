# /agents/triage_agent.py

import os
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain import hub
import json

# --- 1. Setup ---
load_dotenv()
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("❌ GEMINI_API_KEY not found in .env file.")

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0, google_api_key=gemini_api_key)

# --- 2. Create the Triage Agent ---
# This agent has no tools, it only uses the LLM to think.
tools = []
prompt = hub.pull("hwchase17/openai-tools-agent")
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# --- 3. Run the Triage Agent ---
if __name__ == "__main__":
    # This is the example JSON output from the Gmail Scout Agent
    scout_output_str = """
    {
      "message_id": "1929a1b2c3d4e5f6",
      "sender": "customer@example.com",
      "subject": "Urgent: Billing Issue",
      "body": "My payment failed but my card was charged. My account is locked and I need access immediately. The transaction ID is 8675309."
    }
    """
    
    # Parse the incoming data
    email_data = json.loads(scout_output_str)

    # --- MODIFICATION IS HERE ---
    # The task now explicitly demands a clean JSON output and nothing else.
    task = f"""
    You are an expert customer support triage agent. Analyze the following email content and decide the next action.

    Email Details:
    - Sender: {email_data['sender']}
    - Subject: {email_data['subject']}
    - Body: {email_data['body']}

    Your task is to respond with ONLY a compact, machine-readable JSON object.
    The JSON object must contain these exact keys:
    - "priority": A string, one of "High", "Normal", or "Low".
    - "action": A string, one of "CREATE_TICKET" or "SEND_REPLY".
    - "summary": A string containing a concise, one-sentence summary for a Jira ticket title.
    - "reply_body": A string containing a suggested text for a direct reply. If creating a ticket, this should be an acknowledgment message.

    Do not include any conversational text, explanations, or markdown formatting like ```
    """
    
    print("\n🤔 --- Running Triage Agent ---")
    result = agent_executor.invoke({"input": task})
    
    print("\n✅ --- Triage Complete ---")
    print("📋 Triage Decision (Raw JSON Output):")
    
    # We can now confidently parse this output in our orchestrator
    triage_decision = json.loads(result["output"])
    
    print(json.dumps(triage_decision, indent=2))

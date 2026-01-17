# /agents/gmail_scout_agent.py

import os
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_tools_agent
# from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_google_community import GmailToolkit
from langchain import hub
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from app.utils.logger import setup_logging

# --- Setup Logging ---
logger = setup_logging()

# --- 1. Initial Setup ---

load_dotenv()
groq_api_key = os.getenv("GROQ_API_KEY")
if not groq_api_key:
    raise ValueError("❌ GROQ_API_KEY not found in .env file.")

# Initialize LLM

logger.info("🚀 Initializing LLM with GROQ_API_KEY...")
llm = ChatGroq(model="qwen/qwen3-32b", temperature=0, api_key=groq_api_key)

# --- 2. Configure Gmail Authentication ---
credentials_file = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
token_file = "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
]

creds = None
if os.path.exists(token_file):
    creds = Credentials.from_authorized_user_file(token_file, SCOPES)

# If no (valid) credentials, perform OAuth login
if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        logger.info("🔄 Refreshing expired credentials...")
        creds.refresh(Request())
    else:
        logger.info("🔒 No valid credentials found, starting OAuth flow...")
        if not os.path.exists(credentials_file):
            raise FileNotFoundError(
                f"'{credentials_file}' not found. Cannot start authentication flow."
            )
        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
        creds = flow.run_local_server(port=62166)

    # Save credentials for next time
    with open(token_file, "w") as token:
        token.write(creds.to_json())
        logger.info(f"🔑 Credentials saved to {token_file}")

# ✅ Build Gmail service directly (fix for your ImportError)
gmail_service = build("gmail", "v1", credentials=creds)

# Initialize Gmail Toolkit
gmail_toolkit = GmailToolkit(api_resource=gmail_service)
Tools = gmail_toolkit.get_tools()

allowed_tools = ["search_gmail", "get_gmail_message", "modify_gmail_message"]
tools = [t for t in Tools if t.name in allowed_tools]

logger.info(f"📬 Agent equipped with {len(tools)} Gmail tools.")

# --- 3. Create the Agent ---
prompt = hub.pull("hwchase17/openai-tools-agent")
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
logger.info("🤖 Agent created and ready to run.")

# --- 4. Run the Agent ---
if __name__ == "__main__":
    logger.info("\n📨 --- Running Gmail Scout Agent ---")

    # NEW TASK: Ask for specific fields instead of a summary
    task = """
        Step 1: Search for the latest unread email in the inbox.
        Step 2: FROM THE SEARCH RESULT, extract the exact 'id' of the email.
        Step 3: Call the 'get_gmail_message' tool using that EXACT 'id'.
        Step 4: After successfully reading the email, call the 'modify_gmail_message' tool
        with:
        - message_id = the same id
        - remove_labels = ["UNREAD"]
        Step 5: Format the final output as a clean JSON object with keys:
        "message_id", "sender", "subject", "body".
        """

    try:
        result = agent_executor.invoke({"input": task})
        logger.info("\n✅ --- Agent Run Complete ---")
        logger.info("📤 Final Output (as structured JSON):")
        logger.info(result["output"])

    except Exception as e:
        logger.error("\n❌ --- An error occurred ---")
        logger.error(f"Error details: {e}")
        logger.info("💡 Tip: Delete 'token.json' to re-authenticate if the token is invalid.")


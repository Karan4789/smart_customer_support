# /agents/gmail_scout_agent.py

import os
from dotenv import load_dotenv
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_google_community import GmailToolkit
from langchain import hub
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# --- 1. Initial Setup ---
load_dotenv()
print("🔑 Loading credentials from .env file...")

# Explicitly load Gemini API key
gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key:
    raise ValueError("❌ GEMINI_API_KEY not found in .env file.")

# Initialize Gemini model
print("🚀 Initializing LLM with GEMINI_API_KEY...")
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    google_api_key=gemini_api_key
)

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
        print("🔄 Refreshing expired credentials...")
        creds.refresh(Request())
    else:
        print("🔒 No valid credentials found, starting OAuth flow...")
        if not os.path.exists(credentials_file):
            raise FileNotFoundError(
                f"'{credentials_file}' not found. Cannot start authentication flow."
            )
        flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
        creds = flow.run_local_server(port=62166)

    # Save credentials for next time
    with open(token_file, "w") as token:
        token.write(creds.to_json())
        print(f"🔑 Credentials saved to {token_file}")

# ✅ Build Gmail service directly (fix for your ImportError)
gmail_service = build("gmail", "v1", credentials=creds)

# Initialize Gmail Toolkit
gmail_toolkit = GmailToolkit(api_resource=gmail_service)
tools = gmail_toolkit.get_tools()
print(f"📬 Agent equipped with {len(tools)} Gmail tools.")

# --- 3. Create the Agent ---
prompt = hub.pull("hwchase17/openai-tools-agent")
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
print("🤖 Agent created and ready to run.")

# --- 4. Run the Agent ---
# /agents/gmail_scout_agent.py (Updated run block)

# --- 4. Run the Agent ---
if __name__ == "__main__":
    print("\n📨 --- Running Gmail Scout Agent ---")

    # NEW TASK: Ask for specific fields instead of a summary
    task = """
    Search for the single most recent unread email in the inbox.
    If an unread email is found, get its message ID, sender's email address, subject, and the plain text body.
    Format the output as a clean JSON object with the keys: "message_id", "sender", "subject", and "body".
    """

    try:
        result = agent_executor.invoke({"input": task})
        print("\n✅ --- Agent Run Complete ---")
        print("📤 Final Output (as structured JSON):")
        
        # The agent's output will now be a JSON string that we can use
        print(result["output"])

    except Exception as e:
        print("\n❌ --- An error occurred ---")
        print(f"Error details: {e}")
        print("💡 Tip: Delete 'token.json' to re-authenticate if the token is invalid.")


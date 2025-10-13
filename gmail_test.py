# /agents/gmail_scout_agent.py

import os
from dotenv import load_dotenv
from app.agents.gmail_agent import read_email_tool # Import your custom tool
from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain import hub

# --- 1. Initial Setup ---
# Load environment variables from .env file
load_dotenv()
print("Loading credentials...")

# The ChatGoogleGenerativeAI class will automatically look for the
# GOOGLE_API_KEY environment variable. No need for gcloud login.
print("Initializing LLM with Google AI Studio API Key...")
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-lite", temperature=0)

# --- 2. Equip the Agent with Tools ---
tools = [read_email_tool]
print(f"Agent equipped with {len(tools)} custom tools.")

# --- 3. Create the Agent ---
prompt = hub.pull("hwchase17/openai-tools-agent")
agent = create_openai_tools_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
print("Agent created and ready to run.")

# --- 4. Run the Agent to Test ---
if __name__ == "__main__":
    print("\n--- Running Gmail Scout Agent ---")
    
    task = "Find the most recent unread email in my inbox and get its content."
    
    result = agent_executor.invoke({"input": task})
    
    print("\n--- Agent Run Complete ---")
    print("Final Output:")
    print(result['output'])


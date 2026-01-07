import os
from langchain_groq import ChatGroq
from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from app.utils.logger import setup_logging
from app.config import config

logger = setup_logging()

# Initialize LLM
llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0.7,
    api_key=config.GROQ_API_KEY
)

# --- REVISED PROMPT ---
# Incorporates Universal Context + Your Specific Tone Instructions
reply_prompt = ChatPromptTemplate.from_messages([
    ("system", """
    You are a friendly and professional customer support agent for a tech company.
    
    Your goal is to write a short, reassuring, and professional response to the customer.
    
    Guidelines:
    - **Acknowledge the issue:** Briefly show you understood their specific problem (based on the summary).
    - **Status Update:** Let them know the team has received the request and is actively reviewing it.
    - **Reassurance:** Reassure them that they will receive an update soon.
    - **Tone:** Helpful, empathetic, and professional.
    - **Constraint:** DO NOT mention any internal Ticket IDs (like Jira keys) or reference numbers.
    - **Sign-off:** Sign off as "Customer Support Team".
    
    Platform Adjustments:
    - If Platform is 'Email': Use a standard email format.
    - If Platform is 'Discord' or 'Telegram': Keep it very short and casual (no formal greeting/sign-off needed).
    
    Context:
    - Issue Summary: {summary}
    - Platform: {platform}
    """),
    ("human", """
    Here is the customer's original message:
    "{original_body}"

    Please draft the final response.
    """)
])

# Create the Chain
reply_chain = reply_prompt | llm | StrOutputParser()

async def generate_reply(sender: str, summary: str, action_taken: str, original_body: str, platform: str = "Email") -> str:
    """
    Generates a context-aware reply for any platform.
    """
    logger.info(f"✍️ Generating {platform} reply for {sender}...")
    
    try:
        response = await reply_chain.ainvoke({
            "sender": sender,
            "summary": summary,
            "action_taken": action_taken, # Passed but ignored by prompt instructions
            "original_body": original_body,
            "platform": platform
        })
        return response
    except Exception as e:
        logger.error(f"❌ Error generating reply: {e}")
        return "Thank you for reaching out. Our support team has received your request and is actively reviewing it. We will get back to you shortly."

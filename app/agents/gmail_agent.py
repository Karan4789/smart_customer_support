# app/agents/gmail_tools.py
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import gmail_service
from langchain.tools import Tool

# Create a tool for reading emails
read_email_tool = Tool(
    name="SearchRecentUnreadEmail",
    func=gmail_service.get_latest_unread_email,
    description="Use this tool to search for the most recent unread email in the inbox. It returns the sender, subject, and body as a dictionary."
)

# Create a tool for sending replies
# Note: The lambda function here is incorrect for a multi-argument tool. 
# We need to use a structured tool or pydantic for this. Let's fix it.

from pydantic import BaseModel, Field


class SendEmailArgs(BaseModel):
    to: str = Field(description="The recipient's email address.")
    subject: str = Field(description="The subject of the email.")
    body: str = Field(description="The plain text body of the email.")

send_reply_tool = Tool.from_function(
    func=lambda to, subject, body: gmail_service.send_reply(to_email=to, subject=subject, message_text=body),
    name="SendGmailReply",
    description="Use this tool to send an email reply.",
    args_schema=SendEmailArgs
)

# app/agents/tools/reply_tools.py

from pydantic import BaseModel, Field
from langchain.tools import Tool
# Your old `gmail_service.py` is now a library of functions for your tools.
# Let's assume it has a function named `send_reply`.
from app.services.gmail_service import send_reply 

class SendEmailArgs(BaseModel):
    to: str = Field(description="The recipient's email address.")
    subject: str = Field(description="The subject of the email.")
    body: str = Field(description="The plain text body of the email.")

# This tool wraps your custom `send_reply` function
send_email_tool = Tool.from_function(
    func=lambda to, subject, body: send_reply(to_email=to, subject=subject, message_text=body),
    name="SendGmailReply",
    description="Use this tool to send a direct email reply to a user.",
    args_schema=SendEmailArgs
)

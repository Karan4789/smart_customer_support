# app/agents/tools/jira_tools.py
from pydantic import BaseModel, Field
from langchain.tools import Tool
from app.services import jira_service

class CreateJiraTicketArgs(BaseModel):
    summary: str = Field(description="Summary/title of the Jira ticket.")
    description: str = Field(description="Detailed description/body of the ticket.")
    issue_type: str = Field(default="Task", description="Type of Jira issue (Task, Bug, Story).")

def _create_ticket(summary: str, description: str, issue_type: str = "Task") -> str:
    return jira_service.create_jira_ticket(summary=summary, description=description, issue_type=issue_type)

create_jira_ticket_tool = Tool.from_function(
    func=_create_ticket,
    name="CreateJiraTicket",
    description="Create a Jira ticket with provided summary, description, and optional issue type.",
    args_schema=CreateJiraTicketArgs,
)

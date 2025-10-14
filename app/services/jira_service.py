# app/services/jira_service.py
from jira import JIRA
from app.config import config


def _get_jira_client():
    """Initializes and returns a JIRA client instance."""
    try:
        jira_client = JIRA(
            server=f"https://{config.JIRA_DOMAIN}",
            basic_auth=(config.JIRA_EMAIL, config.JIRA_API_TOKEN),
            options={"agile_rest_path": "agile", "server": f"https://{config.JIRA_DOMAIN}"}
        )
        return jira_client
    except Exception as e:
        print(f"[ERROR] Failed to connect to Jira: {e}")
        return None


def create_jira_ticket(summary: str, description: str, issue_type: str = "Task") -> str | None:
    """
    Creates a new ticket in the configured Jira project.

    :param summary: The title of the ticket.
    :param description: The detailed body of the ticket.
    :param issue_type: The type of issue (e.g., 'Task', 'Bug', 'Story').
    :return: The key of the newly created ticket, or None if it fails.
    """
    jira = _get_jira_client()
    if not jira:
        return None

    issue_dict = {
        "project": {"key": config.JIRA_PROJECT_KEY},
        "summary": summary,
        "description": description,
        "issuetype": {"name": issue_type},
    }

    try:
        new_issue = jira.create_issue(fields=issue_dict)
        print(f"[SUCCESS] Jira ticket created successfully! Key: {new_issue.key}")
        return new_issue.key
    except Exception as e:
        print(f"[ERROR] Failed to create Jira ticket: {e}")
        return None

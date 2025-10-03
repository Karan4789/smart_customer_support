import os
from dotenv import load_dotenv

load_dotenv()

GMAIL_CREDENTIALS_PATH = os.getenv('GMAIL_CREDENTIALS_PATH', 'credentials.json')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_DOMAIN = os.getenv('JIRA_DOMAIN')
JIRA_PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY')

# Add logging config
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'app.log')
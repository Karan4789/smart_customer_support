import os
from dotenv import load_dotenv

project_root = os.path.join(os.path.dirname(__file__), '..', '..')
dotenv_path = os.path.join(project_root, '.env')
load_dotenv(dotenv_path=dotenv_path)

GMAIL_CREDENTIALS_PATH = os.getenv('GMAIL_CREDENTIALS_PATH', 'credentials.json')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Jira credentials
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JIRA_DOMAIN = os.getenv('JIRA_DOMAIN')
JIRA_PROJECT_KEY = os.getenv('JIRA_PROJECT_KEY')

# Discord credentials
DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
DISCORD_SUPPORT_CHANNEL_ID = os.getenv('DISCORD_SUPPORT_CHANNEL_ID')

# Telegram credentials
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')


# Add logging config
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FILE = os.getenv('LOG_FILE', 'app.log')


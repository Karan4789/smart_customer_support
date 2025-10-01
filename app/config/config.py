import os
from dotenv import load_dotenv

load_dotenv()

GMAIL_CREDENTIALS_PATH = os.getenv('GMAIL_CREDENTIALS_PATH', 'credentials.json')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
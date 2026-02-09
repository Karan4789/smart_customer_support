import os.path
import base64
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.utils.logger import setup_logging
from app.config import config

logger = setup_logging()

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']

def _get_credentials():
    creds = None
    token_path = config.GMAIL_TOKEN_PATH
    credentials_path = config.GMAIL_CREDENTIALS_PATH
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=8080)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    return creds

def get_latest_unread_email():
    try:
        creds = _get_credentials()
        service = build('gmail', 'v1', credentials=creds)

        results = service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread", maxResults=10).execute()
        messages = results.get('messages', [])

        if not messages:
            return None

        for message_info in messages:
            msg_id = message_info['id']
            
            # THE BUG FIX IS HERE: The `metadataHeaders` parameter is removed.
            metadata = service.users().messages().get(userId='me', id=msg_id, format='metadata').execute()
            
            if 'UNREAD' not in metadata.get('labelIds', []):
                logger.debug(f"Skipped message {msg_id} as it is no longer marked 'UNREAD'.")
                continue

            logger.debug(f"Verified unread message ID: {msg_id}. Fetching full content...")
            full_msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

            headers = full_msg['payload']['headers']
            sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), None)
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
            
            email_body = ""
            if 'parts' in full_msg['payload']:
                for part in full_msg['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        email_body = base64.urlsafe_b64decode(data).decode('utf-8')
                        break
            else:
                data = full_msg['payload']['body'].get('data', '')
                email_body = base64.urlsafe_b64decode(data).decode('utf-8')

            logger.debug(f"Marking message {msg_id} as read.")
            service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
            
            return {"id": msg_id, "sender": sender, "subject": subject, "content": email_body}

        logger.info("No verified unread emails found after checking potential candidates.")
        return None

    except Exception as error:
        logger.critical(f"An error occurred in get_latest_unread_email: {error}", exc_info=True)
        return None

def send_reply(to_email, subject, message_text):
    try:
        creds = _get_credentials()
        service = build('gmail', 'v1', credentials=creds)
        
        message = MIMEText(message_text)
        message['to'] = to_email
        message['subject'] = subject
        
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': raw_message}
        
        sent_message = service.users().messages().send(userId="me", body=create_message).execute()
        logger.info(f"Message sent successfully to {to_email}. Message ID: {sent_message['id']}")
        return sent_message

    except HttpError as error:
        logger.error(f"An error occurred while sending email: {error}", exc_info=True)
        return None

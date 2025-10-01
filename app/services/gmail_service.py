import os.path
import base64
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timezone, timedelta

# Define the scopes. If you change them, you must delete token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']

def _get_credentials():
    """
    Handles user authentication and token management.
    Returns valid credentials for accessing the Gmail API.
    """
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # You must have the 'credentials.json' file from Google Cloud.
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=8080)
        # Save the credentials for the next run.
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds

def get_latest_unread_email():
    """
    Fetches the single latest unread email from the inbox.
    This version is simplified for debugging and removes time-based filtering.
    """
    try:
        creds = _get_credentials()
        service = build('gmail', 'v1', credentials=creds)

        # 1. Ask Gmail for a list of all unread message IDs in the inbox
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], q="is:unread", maxResults=1).execute()
        messages = results.get('messages', [])

        print(f"[DEBUG] API response for unread messages: {results}")

        if not messages:
            # This will now be the only reason it reports "no new messages"
            return None 
        
        # 2. Get the ID of the very first message in the list (the latest one)
        msg_id = messages[0]['id']
        print(f"[DEBUG] Found unread message ID: {msg_id}. Fetching full content...")
        
        # 3. Get the full content of that one message
        full_msg = service.users().messages().get(userId='me', id=msg_id, format='full').execute()

        # 4. Parse the message details (sender, subject, body)
        headers = full_msg['payload']['headers']
        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), None)
        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No Subject')
        
        email_body = ""
        if 'parts' in full_msg['payload']:
            for part in full_msg['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body']['data']
                    email_body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
        else:
            data = full_msg['payload']['body']['data']
            email_body = base64.urlsafe_b64decode(data).decode('utf-8')

        # 5. Mark this specific email as read
        print(f"[DEBUG] Marking message {msg_id} as read.")
        service.users().messages().modify(userId='me', id=msg_id, body={'removeLabelIds': ['UNREAD']}).execute()
        
        # 6. Return the data for processing
        return {"id": msg_id, "sender": sender, "subject": subject, "content": email_body}

    except Exception as error:
        print(f"[CRITICAL GMAIL ERROR] An error occurred in get_latest_unread_email: {error}")
        return None

def send_reply(to_email, subject, message_text):
    """
    Creates and sends an email reply.
    """
    try:
        creds = _get_credentials()
        service = build('gmail', 'v1', credentials=creds)
        
        message = MIMEText(message_text)
        message['to'] = to_email
        message['subject'] = "Re: " + subject
        
        # Encode the message in a way that the API can read.
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': raw_message}
        
        sent_message = service.users().messages().send(userId="me", body=create_message).execute()
        print(f"Message sent successfully to {to_email}. Message ID: {sent_message['id']}")
        return sent_message

    except HttpError as error:
        print(f"An error occurred while sending email: {error}")
        return None

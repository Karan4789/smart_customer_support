import sqlite3
import json
from datetime import datetime

DB_NAME = "data/customer_request.db"

def init_db():
    """Creates the tickets table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT UNIQUE,
            sender TEXT,
            subject TEXT,
            body TEXT,
            source TEXT,
            status TEXT DEFAULT 'PENDING',
            triage_result TEXT,
            created_at TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def add_ticket(ticket_data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO tickets (message_id, sender, subject, body, source, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            ticket_data['message_id'],
            ticket_data['sender'],
            ticket_data['subject'],
            ticket_data['body'],
            ticket_data['source'], # No default. Must be provided by the Agent.
            'PENDING',
            datetime.now()
        ))
        conn.commit()
        print(f"💾 Saved ticket {ticket_data['message_id']} ({ticket_data['source']}) to DB.")
    except Exception as e:
        print(f"⚠️ Error saving ticket: {e}")
    finally:
        conn.close()


def get_next_ticket():
    """Orchestrator calls this to get the next job."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row # Access columns by name
    cursor = conn.cursor()
    
    # Get one pending ticket
    cursor.execute("SELECT * FROM tickets WHERE status='PENDING' LIMIT 1")
    row = cursor.fetchone()
    
    if row:
        # Mark it as PROCESSING so no one else grabs it
        # (In a real production DB, use 'SELECT FOR UPDATE' or a transaction here)
        cursor.execute("UPDATE tickets SET status='PROCESSING' WHERE id=?", (row['id'],))
        conn.commit()
        
        # Convert Row to Dict
        return dict(row)
    
    conn.close()
    return None

def update_ticket_status(ticket_id, status, triage_result=None):
    """Orchestrator calls this after finishing the job."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    if triage_result:
        # Store the full JSON decision from the agent
        result_json = json.dumps(triage_result)
        cursor.execute("UPDATE tickets SET status=?, triage_result=? WHERE id=?", (status, result_json, ticket_id))
    else:
        cursor.execute("UPDATE tickets SET status=? WHERE id=?", (status, ticket_id))
        
    conn.commit()
    conn.close()

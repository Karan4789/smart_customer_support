import asyncio
import uuid
import os
import sys
from pydantic import BaseModel, EmailStr

# Ensure imports work
sys.path.append(os.getcwd())

# Import ONLY the DB functions (No agents, no listeners)
from app.database import init_db, add_ticket, get_next_ticket

# --- 1. Mock the Webform Logic (What will eventually go into main.py) ---

class ComplaintModel(BaseModel):
    name: str
    email: EmailStr
    message: str

async def mock_webform_endpoint(data: ComplaintModel):
    """
    This function simulates exactly what your FastAPI route will do.
    """
    print(f"🔵 [MOCK SERVER] Receiving submission from {data.email}...")
    
    # 1. Format it like a ticket
    ticket_data = {
        "message_id": f"web_{uuid.uuid4()}", 
        "sender": data.email,                
        "subject": f"Web Inquiry from {data.name}",
        "body": data.message,
        "source": "Webform"
    }
    
    # 2. Save to DB
    # In the real app, this runs via FastAPI. Here we call it directly.
    print(f"🔵 [MOCK SERVER] Saving ticket {ticket_data['message_id']} to DB...")
    # add_ticket is sync, so we run it in a thread to match async route behavior
    await asyncio.to_thread(add_ticket, ticket_data)
    
    return {"status": "received", "ticket_id": ticket_data["message_id"]}

# --- 2. The Test Script ---

async def test_webform_isolated():
    print("🚀 Starting Isolated Webform Logic Test...")
    
    # Initialize DB so we have a table to write to
    init_db()
    
    # Define our test data
    test_payload = ComplaintModel(
        name="Isolated Tester",
        email="isolated@example.com",
        message="This is a test running without the main server."
    )
    
    # Call the mock endpoint function
    response = await mock_webform_endpoint(test_payload)
    print(f"✅ Mock Response: {response}")
    
    # Now verify it's in the DB
    print("\n🔍 Verifying Database Content...")
    
    found = False
    for i in range(5):
        # Peek at DB
        ticket = await asyncio.to_thread(get_next_ticket)
        
        if ticket:
            if ticket['sender'] == "isolated@example.com":
                print("\n✅ SUCCESS! Ticket found in DB:")
                print(f"   ID: {ticket['id']}")
                print(f"   Subject: {ticket['subject']}")
                print(f"   Source: {ticket['source']}")
                found = True
                break
            else:
                print(f"ℹ️ Found unrelated ticket: {ticket['sender']}")
        else:
            print("⏳ DB is empty...")
            
        await asyncio.sleep(0.5)
        
    if not found:
        print("❌ Failed to find the ticket in DB.")
    else:
        print("\n🎉 Logic verified! You can now safely add this code to main.py.")

if __name__ == "__main__":
    asyncio.run(test_webform_isolated())

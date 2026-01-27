import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure the 'app' module can be found if running from root
sys.path.append(os.getcwd())

# Import your actual agent code
from app.agents.telegram_agent import start_telegram_bot
from app.database import init_db, get_next_ticket
from app.utils.logger import setup_logging

# Load environment variables
load_dotenv()
logger = setup_logging()

async def test_telegram_agent_integration():
    print("🚀 Starting Telegram Agent Integration Test...")

    # 1. Initialize Database (So the agent has somewhere to save tickets)
    print("🔵 Initializing Database...")
    init_db()

    # 2. Start the Telegram Agent in the background
    print("🔵 Starting Telegram Agent (Polling Mode)...")
    agent_task = asyncio.create_task(start_telegram_bot())

    # 3. Wait for the user to send a message
    print("\n🧪 --- TEST INSTRUCTIONS ---")
    print("1. Open Telegram and find your bot.")
    print("2. Send a message: 'Hello Agent, this is a test!'")
    print("3. Waiting 30 seconds for you to send the message...\n")

    try:
        # Check the database every 2 seconds for a new Telegram ticket
        for i in range(15):
            print(f"⏳ Checking DB for new tickets... ({i+1}/15)")
            
            # We use get_next_ticket to see if the agent successfully saved anything
            # Note: This function marks the ticket as 'PROCESSING', effectively consuming it from the queue
            # which is fine for a test script.
            
            # Since get_next_ticket is synchronous (sqlite3), we run it in a thread
            ticket = await asyncio.to_thread(get_next_ticket)
            
            if ticket:
                # Check if it looks like a Telegram ticket
                # It should have "tg_" in the message_id or source="Telegram"
                is_telegram = "Telegram" in ticket.get('source', '') or "tg_" in ticket.get('message_id', '')
                
                if is_telegram:
                    print("\n✅ SUCCESS! Found a new ticket from Telegram:")
                    print(f"   ID: {ticket['id']}")
                    print(f"   Sender (Chat ID): {ticket['sender']}")
                    print(f"   Body: {ticket['body']}")
                    print("\n🎉 The Telegram Agent is correctly listening and saving to the DB!")
                    break
                else:
                    print(f"ℹ️ Found a ticket, but it wasn't from Telegram (Source: {ticket.get('source')}). Keep waiting...")
            
            await asyncio.sleep(2)
        else:
            print("\n❌ Timeout: No Telegram ticket found after 30 seconds.")
            print("   - Did you send the message?")
            print("   - Is the bot token correct in .env?")
    
    except Exception as e:
        print(f"❌ Error during test: {e}")

    finally:
        # Cleanup: Stop the background agent
        print("\n🛑 Stopping Agent...")
        agent_task.cancel()
        try:
            await agent_task
        except asyncio.CancelledError:
            pass
        print("✅ Test Complete.")

if __name__ == "__main__":
    asyncio.run(test_telegram_agent_integration())

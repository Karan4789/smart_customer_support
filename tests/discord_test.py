import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure the 'app' module can be found
sys.path.append(os.getcwd())

# Import the listener starter and DB tools
from app.services.discord_service import get_bot, stop_bot
from app.database import init_db, get_next_ticket
from app.utils.logger import setup_logging

load_dotenv()
logger = setup_logging()

async def test_discord_scout_integration():
    print("🚀 Starting Discord Scout (Listener) Test...")

    # 1. Initialize DB (So the agent has somewhere to save tickets)
    print("🔵 Initializing Database...")
    init_db()

    # 2. Start the Discord Bot (The Listener)
    print("🔵 Starting Discord Bot Service...")
    # get_bot() starts the background loop that listens for messages
    bot = await get_bot()
    print(f"✅ Discord Bot Started. Logged in as: {bot.user}")

    # 3. Wait for User Input
    print("\n🧪 --- TEST INSTRUCTIONS ---")
    print("1. Go to your Discord server.")
    print(f"2. Send a message in the support channel: 'Hello Scout, catch this!'")
    print("3. Waiting 30 seconds for you to send the message...\n")

    try:
        # Check the database every 2 seconds for a new Discord ticket
        found_ticket = False
        for i in range(15):
            print(f"⏳ Checking DB for new tickets... ({i+1}/15)")
            
            # This fetches the next 'PENDING' ticket from the DB
            # Note: This consumes the ticket (marks it PROCESSING), which is fine for testing
            ticket = await asyncio.to_thread(get_next_ticket)
            
            if ticket:
                # Check if it came from Discord
                # We look for "Discord" in the source OR "discord_" in the message ID
                source = ticket.get('source', '')
                msg_id = ticket.get('message_id', '')
                
                if "Discord" in source or "discord_" in msg_id:
                    print("\n✅ SUCCESS! Found a new ticket from Discord:")
                    print(f"   ID: {ticket['id']}")
                    print(f"   Sender: {ticket['sender']}")
                    print(f"   Body: {ticket['body']}")
                    print("\n🎉 The Discord Scout Agent is correctly listening and saving to the DB!")
                    found_ticket = True
                    break
                else:
                    print(f"ℹ️ Found a ticket, but it wasn't from Discord (Source: {source}). Keep waiting...")
            
            await asyncio.sleep(2)
            
        if not found_ticket:
            print("\n❌ Timeout: No Discord ticket found after 30 seconds.")
            print("   - Did you send the message in the correct channel?")
            print("   - Is the bot added to that channel?")

    except Exception as e:
        print(f"❌ Error during test: {e}")

    finally:
        # Cleanup
        print("\n🛑 Shutting down Discord Bot...")
        await stop_bot()
        print("✅ Test Complete.")

if __name__ == "__main__":
    try:
        asyncio.run(test_discord_scout_integration())
    except KeyboardInterrupt:
        print("\nTest interrupted.")

import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot

# Load environment variables
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def test_telegram_bot():
    print("🚀 Starting Telegram Bot Test Script...")

    if not TELEGRAM_TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found in .env file.")
        return

    try:
        # 1. Initialize the Bot
        print("🔵 Connecting to Telegram...")
        bot = Bot(token=TELEGRAM_TOKEN)
        
        # 2. Get Bot Info (Self-Check)
        me = await bot.get_me()
        print(f"✅ Bot Connected! Name: {me.first_name} | Username: @{me.username} | ID: {me.id}")

        # 3. Check for messages
        print("\n🔵 Checking for recent updates (last 1)...")
        # get_updates retrieves messages sent to the bot
        updates = await bot.get_updates(limit=1)
        
        if updates:
            last_update = updates[-1]
            if last_update.message:
                last_msg = last_update.message
                print(f"📩 Found a message from {last_msg.from_user.first_name}: '{last_msg.text}'")
                print(f"   Chat ID: {last_msg.chat_id}")
                
                # 4. Reply Test (The 'Tool' Logic)
                print(f"📤 Attempting to reply to Chat ID {last_msg.chat_id}...")
                await bot.send_message(chat_id=last_msg.chat_id, text="✅ Test Reply: I received your message! The system is working.")
                print("✅ Reply sent successfully.")
            else:
                 print("ℹ️ Found an update, but it wasn't a text message.")
        else:
            print("ℹ️ No recent messages found.")
            print(f"👉 ACTION: Open Telegram, search for @{me.username}, click Start, and say 'Hello'.")
            print("👉 Then run this script again.")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_telegram_bot())

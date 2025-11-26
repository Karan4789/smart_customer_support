import asyncio
import os
from dotenv import load_dotenv

# Import the service functions to control the bot lifecycle
from app.services.discord_service import get_bot, stop_bot

# Import your agent executor
from app.agents.discord_agent import agent_executor

# Ensure logging is configured so you can see output
from app.utils.logger import setup_logging
logger = setup_logging()

async def test_discord_workflow():
    print("🚀 Starting Discord Agent Test Script...")

    # 1. Start the Discord Service (Production-like startup)
    # This launches the background loop that processes the agent's tool calls.
    print("🔵 Initializing Discord Bot Service...")
    bot = await get_bot()
    print(f"✅ Discord Bot Service Started. Logged in as: {bot.user}")

    # 2. Define a test task for the agent
    # Replace '1234567890' with your ACTUAL testing Channel ID from your .env or config
    # You can hardcode it here for the test script to be sure.
    TEST_CHANNEL_ID = os.getenv("DISCORD_SUPPORT_CHANNEL_ID") 
    
    if not TEST_CHANNEL_ID:
        print("❌ Error: DISCORD_SUPPORT_CHANNEL_ID not found in environment variables.")
        await stop_bot()
        return

    # Task 1: Send a message
    print("\n🧪 --- TEST CASE 1: Sending a Message ---")
    task_send = f"Send a message to Discord channel {TEST_CHANNEL_ID} saying 'Hello! This is a test from the autonomous agent 🤖.'"
    
    try:
        # We use ainvoke for async execution
        response = await agent_executor.ainvoke({"input": task_send})
        print(f"🤖 Agent Output: {response['output']}")
    except Exception as e:
        print(f"❌ Error during Send test: {e}")

    # Task 2: Read messages (Optional, verifies read tool)
    print("\n🧪 --- TEST CASE 2: Reading Messages ---")
    task_read = f"Read the last 3 messages from Discord channel {TEST_CHANNEL_ID} and summarize them."
    
    try:
        response = await agent_executor.ainvoke({"input": task_read})
        print(f"🤖 Agent Output: {response['output']}")
    except Exception as e:
        print(f"❌ Error during Read test: {e}")

    # 3. Cleanup and Shutdown
    print("\n🛑 Shutting down Discord Bot Service...")
    await stop_bot()
    print("✅ Test Complete. Exiting.")

if __name__ == "__main__":
    # Load env vars
    load_dotenv()
    
    # Run the async test loop
    try:
        asyncio.run(test_discord_workflow())
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully if it hangs
        print("\nTest interrupted.")

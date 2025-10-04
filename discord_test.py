import os
import discord
from dotenv import load_dotenv

load_dotenv()
print("Attempting to load credentials from .env file...")

DISCORD_BOT_TOKEN = os.getenv('DISCORD_BOT_TOKEN')
SUPPORT_CHANNEL_ID_STR = os.getenv('DISCORD_SUPPORT_CHANNEL_ID')

print(f"  - Found DISCORD_BOT_TOKEN: {'Yes' if DISCORD_BOT_TOKEN else 'NO'}")
print(f"  - Found DISCORD_SUPPORT_CHANNEL_ID: {SUPPORT_CHANNEL_ID_STR or 'NO'}")

if not DISCORD_BOT_TOKEN or not SUPPORT_CHANNEL_ID_STR:
    print("\nCRITICAL ERROR: Environment variables are missing.")
else:
    try:
        SUPPORT_CHANNEL_ID = int(SUPPORT_CHANNEL_ID_STR)
        
        intents = discord.Intents.default()
        intents.messages = True
        intents.message_content = True

        bot = discord.Client(intents=intents)

        @bot.event
        async def on_ready():
            print("\nSUCCESS! Bot has connected to Discord.")
            print(f"  - Logged in as: {bot.user}")
            print(f"  - Ready to listen in channel: {SUPPORT_CHANNEL_ID}")

        @bot.event
        async def on_message(message):
            # --- THE ULTIMATE DEBUGGING STEP ---
            # This will run for EVERY message the bot sees, in ANY channel.
            print(f"\n--- Message Event Fired! ---")
            print(f"  - Channel Name: #{message.channel}")
            print(f"  - Channel ID: {message.channel.id}")
            print(f"  - Expected Channel ID: {SUPPORT_CHANNEL_ID}")
            print(f"  - Does Channel ID Match?: {message.channel.id == SUPPORT_CHANNEL_ID}")
            # -----------------------------------

            if message.author == bot.user:
                return
            
            if message.channel.id == SUPPORT_CHANNEL_ID:
                print("  - ACTION: Responding to message.")
                await message.channel.send(f"Test successful! I received your message, {message.author.mention}.")

        print("\nStarting bot...")
        bot.run(DISCORD_BOT_TOKEN)

    except Exception as e:
        print(f"\nAn unexpected error occurred: {e}")

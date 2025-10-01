# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from app.services import gmail_service, llm_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    print("--- Application Starting Up ---")
    task = asyncio.create_task(check_emails_periodically())
    yield
    print("--- Application Shutting Down ---")
    task.cancel()
    await asyncio.sleep(1) # Give the task a moment to cancel

app = FastAPI(lifespan=lifespan)

async def check_emails_periodically():
    """The main background task that runs continuously."""
    while True:
        try:
            print("\n[CYCLE START] Checking for new emails...")
            
            # Run the blocking function in a separate thread to not freeze the app
            email_data = await asyncio.to_thread(gmail_service.get_latest_unread_email)
            
            if email_data:
                print(f"[SUCCESS] New email found from: {email_data['sender']}")
                
                # 2. Analyze and get reply from LLM (also in a thread)
                print("[INFO] Analyzing email with LLM...")
                analysis = await asyncio.to_thread(llm_service.analyze_and_craft_reply, email_data['content'])
                
                # Make sure analysis was successful before proceeding
                if analysis and 'priority' in analysis and 'reply_body' in analysis:
                    print(f"[SUCCESS] LLM analysis complete. Priority: {analysis['priority']}")
                    
                    # 3. Send the reply via Gmail (also in a thread)
                    print("[INFO] Sending reply...")
                    await asyncio.to_thread(
                        gmail_service.send_reply,
                        to_email=email_data['sender'],
                        subject=email_data.get('subject', 'Your recent query'),
                        message_text=analysis['reply_body']
                    )
                    print("[SUCCESS] Reply sent.")
                else:
                    print("[ERROR] LLM analysis failed or returned invalid data.")
            else:
                # This is important! It tells you the check was successful but found nothing.
                print("[INFO] No new unread emails found in the last minute.")

        except Exception as e:
            # Catch any unexpected errors in the loop so it doesn't crash
            print(f"[CRITICAL ERROR] The background task encountered an error: {e}")

        # Wait for 30 seconds before the next cycle
        print("[CYCLE END] Waiting for 30 seconds...")
        await asyncio.sleep(30)

@app.get("/")
def home():
    return {"status": "Automated Support Service is running."}


from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from typing import Dict

# --- Import from your new background module ---
from app.background import gmail_listener, orchestrator_task
from app.agents.discord_agent import run_discord_scout_agent
from app.agents.telegram_agent import run_telegram_scout_agent
# -------------------------------------
from app.database import init_db
from app.utils.logger import setup_logging

logger = setup_logging()

# --- FastAPI Application Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    logger.info("--- Application Starting Up: Launching Agentic Workflow ---")
    
    # 1. Initialize the database
    init_db()
    logger.info("[DATABASE] Initialized support_system.db")
    
    # 2. Start Background Services
    # - Gmail Listener (Loops forever)
    # - Discord Agent (Connects to Websocket)
    # - Telegram Agent (Polling Loop)
    # - Orchestrator (Loops forever)
    
    gmail_task = asyncio.create_task(gmail_listener())
    discord_task = asyncio.create_task(run_discord_scout_agent()) # <--- Now using the Agent function
    telegram_task = asyncio.create_task(run_telegram_scout_agent())
    orchestrator = asyncio.create_task(orchestrator_task())

    logger.info("✅ All background services started.")

    yield
    
    # --- Shutdown Sequence ---
    logger.info("--- Application Shutting Down ---")
    
    # Cancel all background tasks
    gmail_task.cancel()
    orchestrator.cancel()
    discord_task.cancel()
    telegram_task.cancel()
    
    # Wait briefly for tasks to clean up to avoid "Task was destroyed but it is pending!" errors
    try:
        # Don't forget to include telegram_task in the wait list!
        await asyncio.wait([gmail_task, orchestrator, discord_task, telegram_task], timeout=2.0)
        logger.info("✅ Background tasks stopped gracefully.")
    except asyncio.TimeoutError:
        logger.warning("⚠️ Some background tasks timed out during shutdown.")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

app = FastAPI(lifespan=lifespan)

@app.get("/")
def home() -> Dict[str, str]:
    return {"status": "Multi-Channel AI Support Agent Service is running with persistent database queue."}

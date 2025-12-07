# app/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from typing import Dict

# --- Import from your new background module ---
from app.background import gmail_listener, orchestrator_task
from app.database import init_db
from app.utils.logger import setup_logging

logger = setup_logging()

# --- FastAPI Application Setup ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles application startup and shutdown events."""
    logger.info("--- Application Starting Up: Launching Agentic Workflow ---")
    
    # Initialize the database
    init_db()
    logger.info("[DATABASE] Initialized support_system.db")
    
    # Start background tasks from the imported module
    gmail_task = asyncio.create_task(gmail_listener())
    orchestrator = asyncio.create_task(orchestrator_task())

    yield
    
    logger.info("--- Application Shutting Down ---")
    gmail_task.cancel()
    orchestrator.cancel()
    
    # Wait briefly for tasks to clean up
    try:
        await asyncio.wait([gmail_task, orchestrator], timeout=1.0)
    except asyncio.TimeoutError:
        logger.warning("Background tasks did not exit typically.")

app = FastAPI(lifespan=lifespan)

@app.get("/")
def home() -> Dict[str, str]:
    return {"status": "Multi-Channel AI Support Agent Service is running with persistent database queue."}
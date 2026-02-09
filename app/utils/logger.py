import logging
import sys
from app.config import config

def setup_logging():
    """Sets up a centralized logger that outputs to both console and a file."""
    
    # Get the root logger
    logger = logging.getLogger()
    
    # Prevent adding duplicate handlers if this function is called multiple times
    if logger.hasHandlers():
        logger.handlers.clear()
        
    logger.setLevel(config.LOG_LEVEL) # Set the minimum level of logs to capture

    # Create a formatter for consistent log message style
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # --- Console Handler ---
    # This handler prints logs to your command line
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # --- File Handler ---
    # This handler saves logs to a file
    log_file = config.LOG_FILE
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)

    # Add both handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger


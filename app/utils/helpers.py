"""
Utility functions for logging and other common operations
"""
import logging
from logging.handlers import RotatingFileHandler
import os
import json


def setup_logging(log_file: str = "app.log", level: int = logging.INFO) -> None:
    """
    Configure application logging
    
    Args:
        log_file: Path to log file
        level: Logging level
    """
    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(level)
    
    # Clear existing handlers
    logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(level)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)


def save_to_json(data, filename: str) -> None:
    """Persist Python data to a JSON file with safety defaults.

    - Creates parent directories if they don't exist
    - Uses ``default=str`` so ObjectId and other non-serializable values are stringified
    - Pretty-prints with indent=2 for readability
    """
    try:
        os.makedirs(os.path.dirname(filename) or ".", exist_ok=True)
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        logging.getLogger(__name__).info(f"Saved JSON snapshot to {filename}")
    except Exception as exc:
        logging.getLogger(__name__).error(f"Failed to save JSON to {filename}: {exc}")


def format_bytes(num_bytes: int) -> str:
    """
    Format bytes into human-readable string
    
    Args:
        num_bytes: Number of bytes
        
    Returns:
        Formatted string (e.g., "1.5 KB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} TB"

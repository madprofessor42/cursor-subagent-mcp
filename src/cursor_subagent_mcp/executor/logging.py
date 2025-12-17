"""Logging utilities for executor."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

# Global logger instance (singleton)
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Get or create the agent logger."""
    global _logger
    if _logger is None:
        _logger = _setup_logger()
    return _logger


def _setup_logger() -> logging.Logger:
    """Setup logging to file in logs directory."""
    # Use logs directory in current working directory
    logs_dir = Path.cwd() / "logs"
    
    logs_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("cursor_subagent")
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # File handler - one file per day
    log_file = logs_dir / f"agents_{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(file_handler)
    
    return logger

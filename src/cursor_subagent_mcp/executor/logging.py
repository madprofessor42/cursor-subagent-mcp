"""Logging utilities for executor."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import find_config_file

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
    # Find project root (where agents.yaml is)
    config_file = find_config_file()
    if config_file:
        logs_dir = config_file.parent / "logs"
    else:
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

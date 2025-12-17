"""Logging utilities for executor."""

import logging
import os
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
    """Setup logging.
    
    By default, does not log to file.
    Set CURSOR_AGENT_LOG_FILE environment variable to enable file logging.
    - Set to a file path to log to that specific file.
    - Set to "1", "true", "yes", or "on" to log to the default logs directory.
    """
    # Create logger
    logger = logging.getLogger("cursor_subagent")
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Check environment variable
    log_env = os.environ.get("CURSOR_AGENT_LOG_FILE")
    
    if log_env:
        log_path: Path
        
        # Check if it's a boolean-like flag or a path
        if log_env.lower() in ("1", "true", "yes", "on"):
            # Use default logs directory in current working directory
            logs_dir = Path.cwd() / "logs"
            logs_dir.mkdir(exist_ok=True)
            log_path = logs_dir / f"agents_{datetime.now().strftime('%Y-%m-%d')}.log"
        else:
            # Use provided path
            log_path = Path(log_env)
            # Ensure parent directory exists
            if log_path.parent:
                log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # File handler
        try:
            file_handler = logging.FileHandler(log_path, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s | %(levelname)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            ))
            logger.addHandler(file_handler)
        except Exception as e:
            # Fallback to stderr if file logging fails
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter(f"Failed to setup log file: {e} | %(message)s"))
            logger.addHandler(stream_handler)
            
    return logger

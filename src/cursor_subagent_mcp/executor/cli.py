"""CLI utilities for finding and checking cursor-agent executable."""

import os
import shutil
from typing import Optional


def find_cursor_agent() -> Optional[str]:
    """Find the cursor-agent executable.

    Checks the following locations in order:
    1. PATH via shutil.which("cursor-agent")
    2. ~/.local/bin/cursor-agent
    3. /usr/local/bin/cursor-agent
    4. ~/bin/cursor-agent

    Returns:
        Path to cursor-agent or None if not found.
    """
    # First, try the standard PATH
    path = shutil.which("cursor-agent")
    if path:
        return path

    # Check common installation locations that might not be in PATH yet
    common_paths = [
        os.path.expanduser("~/.local/bin/cursor-agent"),
        "/usr/local/bin/cursor-agent",
        os.path.expanduser("~/bin/cursor-agent"),
    ]

    for candidate in common_paths:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


def check_cursor_agent_available() -> tuple[bool, str]:
    """Check if cursor-agent CLI is available.

    Returns:
        Tuple of (is_available, message).
    """
    path = find_cursor_agent()
    if path:
        return True, f"cursor-agent found at: {path}"
    else:
        return False, (
            "cursor-agent CLI not found in PATH. "
            "Please install Cursor CLI tools: "
            "https://docs.cursor.com/cli"
        )

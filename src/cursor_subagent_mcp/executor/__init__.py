"""Executor package for running cursor-agent CLI subagents."""

from .cli import check_cursor_agent_available, find_cursor_agent
from .installer import install_cursor_cli
from .models import StreamEvent, ExecutionResult
from .runner import invoke_cursor_agent
from .shell import detect_shell

__all__ = [
    "invoke_cursor_agent",
    "check_cursor_agent_available",
    "find_cursor_agent",
    "detect_shell",
    "install_cursor_cli",
    "StreamEvent",
    "ExecutionResult",
]

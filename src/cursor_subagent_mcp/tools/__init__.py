"""Tools package for cursor-subagent-mcp."""

from .invoke import invoke_subagent
from .orchestration import get_orchestration_guide
from .setup import init_default_agents, setup_cursor_cli
from .status import check_status

__all__ = [
    "get_orchestration_guide",
    "invoke_subagent",
    "setup_cursor_cli",
    "init_default_agents",
    "check_status",
]

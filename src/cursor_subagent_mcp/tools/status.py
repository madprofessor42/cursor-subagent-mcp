"""Status check tool for multi-agent development."""

from ..config import get_config
from ..executor import check_cursor_agent_available


def check_status() -> dict:
    """Check the status of the MCP server and its dependencies.

    Returns information about:
    - Whether cursor-agent CLI is available
    - Whether the configuration is loaded
    - Number of configured agents
    """
    # Check cursor-agent
    cli_available, cli_message = check_cursor_agent_available()

    # Check config
    try:
        config = get_config()
        config_loaded = True
        config_error = None
        agent_count = len(config.agents)
    except Exception as e:
        config_loaded = False
        config_error = str(e)
        agent_count = 0

    return {
        "cursor_agent_available": cli_available,
        "cursor_agent_message": cli_message,
        "config_loaded": config_loaded,
        "config_error": config_error,
        "agent_count": agent_count,
    }

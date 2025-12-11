"""MCP Server for orchestrating multi-agent development in Cursor.

This server provides tools for invoking specialized subagents through
the cursor-agent CLI, enabling a multi-agent development workflow.
"""

from typing import Annotated, Optional

from mcp.server.fastmcp import FastMCP

from .config import Config, load_config, load_prompt
from .executor import (
    check_cursor_agent_available,
    detect_shell,
    install_cursor_cli,
    invoke_cursor_agent,
)

# Initialize the MCP server
mcp = FastMCP(
    "Cursor Subagent Orchestrator",
    version="0.1.0",
)

# Global config - loaded on first access
_config: Optional[Config] = None


def get_config() -> Config:
    """Get or load the configuration."""
    global _config
    if _config is None:
        _config = load_config()
    return _config


@mcp.tool()
def list_agents() -> dict:
    """List all available subagents with their descriptions.

    Returns a dictionary with agent roles as keys and their
    configuration (name, description, default model) as values.
    Use this to understand which agents are available for
    orchestrating the development process.

    Agent roles follow the development workflow:
    - analyst: Creates technical specifications (ТЗ)
    - tz_reviewer: Reviews technical specifications
    - architect: Designs system architecture
    - architecture_reviewer: Reviews architecture
    - planner: Creates development task plans
    - plan_reviewer: Reviews task plans
    - developer: Implements code and tests
    - code_reviewer: Reviews code changes
    """
    config = get_config()
    result = {}

    for role, agent in config.agents.items():
        result[role] = {
            "name": agent.name,
            "description": agent.description,
            "default_model": agent.default_model,
        }

    return result


@mcp.tool()
def get_agent_prompt(
    agent_role: Annotated[
        str,
        "The role of the agent (e.g., 'analyst', 'architect', 'developer')",
    ],
) -> str:
    """Get the full system prompt for a specific agent.

    Use this to inspect what instructions a particular agent receives.
    This is useful for understanding how an agent will behave or for
    debugging the orchestration process.

    Args:
        agent_role: The identifier of the agent role.

    Returns:
        The full system prompt content for the agent.
    """
    config = get_config()

    if agent_role not in config.agents:
        available = ", ".join(config.agents.keys())
        raise ValueError(
            f"Unknown agent role: '{agent_role}'. "
            f"Available roles: {available}"
        )

    return load_prompt(config, agent_role)


@mcp.tool()
async def invoke_subagent(
    agent_role: Annotated[
        str,
        "The role of the agent to invoke (e.g., 'analyst', 'architect')",
    ],
    task: Annotated[
        str,
        "The task or instruction to give to the agent",
    ],
    context: Annotated[
        str,
        "Additional context like file contents, previous results, or project description",
    ] = "",
    model: Annotated[
        Optional[str],
        "Override the default model for this agent (optional)",
    ] = None,
    timeout: Annotated[
        Optional[float],
        "Timeout in seconds for the agent execution (optional)",
    ] = None,
) -> dict:
    """Invoke a subagent to perform a specific task.

    This tool calls the cursor-agent CLI with the appropriate system
    prompt and task. Use this for the multi-agent development workflow:

    1. Call 'analyst' to create technical specifications
    2. Call 'tz_reviewer' to review the specifications
    3. Call 'architect' to design the architecture
    4. Call 'architecture_reviewer' to review the architecture
    5. Call 'planner' to create the development plan
    6. Call 'plan_reviewer' to review the plan
    7. Call 'developer' to implement each task
    8. Call 'code_reviewer' to review the implementation

    Args:
        agent_role: Which agent to invoke.
        task: The specific task for the agent.
        context: Additional context (files, previous outputs, etc.).
        model: Override the default model (optional).
        timeout: Execution timeout in seconds (optional).

    Returns:
        A dictionary with:
        - success: Whether the execution succeeded
        - output: The agent's output/response
        - error: Error message if failed
        - agent_role: The role that was invoked
        - model_used: The model that was used
    """
    # Check if cursor-agent is available
    available, message = check_cursor_agent_available()
    if not available:
        return {
            "success": False,
            "output": "",
            "error": message,
            "agent_role": agent_role,
            "model_used": None,
        }

    config = get_config()

    # Validate agent role
    if agent_role not in config.agents:
        available_roles = ", ".join(config.agents.keys())
        return {
            "success": False,
            "output": "",
            "error": f"Unknown agent role: '{agent_role}'. Available: {available_roles}",
            "agent_role": agent_role,
            "model_used": None,
        }

    agent = config.agents[agent_role]
    model_to_use = model or agent.default_model

    # Load the system prompt
    try:
        system_prompt = load_prompt(config, agent_role)
    except FileNotFoundError as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "agent_role": agent_role,
            "model_used": model_to_use,
        }

    # Execute the agent
    result = await invoke_cursor_agent(
        system_prompt=system_prompt,
        task=task,
        model=model_to_use,
        context=context,
        timeout=timeout,
    )

    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "agent_role": agent_role,
        "model_used": model_to_use,
    }


@mcp.tool()
async def setup_cursor_cli() -> dict:
    """Install and configure cursor-agent CLI.

    This tool will:
    1. Download and install Cursor CLI from cursor.com/install
    2. Add ~/.local/bin to PATH in your shell config (.zshrc or .bashrc)
    3. Verify the installation

    After running this tool, restart your terminal or run 'source ~/.zshrc'
    (or ~/.bashrc) to apply the PATH changes.

    Returns:
        A dictionary with:
        - success: Whether installation succeeded
        - output: Installation log
        - error: Error message if failed
        - shell: Detected shell (zsh/bash)
    """
    shell = detect_shell()

    result = await install_cursor_cli()

    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "shell": shell,
    }


@mcp.tool()
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


def main():
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()


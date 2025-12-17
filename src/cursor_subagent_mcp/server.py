"""MCP Server for orchestrating multi-agent development in Cursor.

This server provides tools for invoking specialized subagents through
the cursor-agent CLI, enabling a multi-agent development workflow.
"""

from typing import Annotated, Optional

from mcp.server.fastmcp import FastMCP

from .tools import (
    check_status as check_status_impl,
    get_orchestration_guide as get_orchestration_guide_impl,
    init_default_agents as init_default_agents_impl,
    invoke_subagent as invoke_subagent_impl,
    setup_cursor_cli as setup_cursor_cli_impl,
)

# Initialize the MCP server
mcp = FastMCP("Cursor Subagent Orchestrator")


@mcp.tool()
def init_default_agents(
    force: Annotated[
        bool, 
        "Whether to overwrite existing agent files"
    ] = False
) -> dict:
    """Initialize default agents in the project.
    
    Copies built-in agent definitions to the configured agents directory
    (defaults to ./agents or CURSOR_AGENTS_DIR).
    
    Args:
        force: If True, overwrites existing files. Default is False.
    """
    return init_default_agents_impl(force=force)


@mcp.tool()
def get_orchestration_guide() -> dict:
    """Get complete orchestration guide with instructions and available agents.

    CALL THIS FIRST when starting a multi-agent development task.

    This tool returns everything you need to orchestrate the development:
    - Full guide with instructions on how to coordinate agents
    - List of all available agents with their roles

    After calling this, use invoke_subagent() to call specific agents
    following the workflow described in the guide.

    Returns:
        - guide: Full orchestrator instructions (from 01_orchestrator.md)
        - agents: Dictionary of available agents with descriptions
    """
    return get_orchestration_guide_impl()


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
    cwd: Annotated[
        str,
        "Working directory path where the agent process runs and files (like subagent_output/) are saved.",
    ],
    context: Annotated[
        str,
        "Additional context like file contents, previous results, or project description",
    ] = "",
    workspace: Annotated[
        Optional[str],
        "Workspace directory that the agent can access and explore (read/write files). If not provided, defaults to cwd. Use this to let the agent explore a different project while saving results to cwd.",
    ] = None,
    model: Annotated[
        Optional[str],
        "Override the default model for this agent (optional)",
    ] = None,
    timeout: Annotated[
        Optional[float],
        "Timeout in seconds for the agent execution (optional)",
    ] = None,
    session_id: Annotated[
        Optional[str],
        "Full UUID string from previous invoke_subagent result to resume chat session. MUST be the complete UUID from result['session_id'] (e.g., '90b79ac7-8e9e-4148-a074-ffba07f88ffa'). Do NOT use partial UUIDs or examples. Copy the exact full session_id value from the previous result. If not provided, starts a new session.",
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
        cwd: Working directory where agent process runs and saves output files.
        workspace: Directory the agent can access for reading/writing project files.
                   If not provided, defaults to cwd.
        model: Override the default model (optional).
        timeout: Execution timeout in seconds (optional).
        session_id: Session ID to resume an existing chat session (optional).

    Returns:
        A dictionary with:
        - success: Whether the execution succeeded
        - output: The agent's output/response
        - error: Error message if failed
        - agent_role: The role that was invoked
        - model_used: The model that was used
        - session_id: Session ID from cursor-agent (None if not available)
        - duration_ms: Execution duration in milliseconds (None if not available)
    """
    return await invoke_subagent_impl(
        agent_role=agent_role,
        task=task,
        cwd=cwd,
        context=context,
        workspace=workspace,
        model=model,
        timeout=timeout,
        session_id=session_id,
    )


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
    return await setup_cursor_cli_impl()


@mcp.tool()
def check_status() -> dict:
    """Check the status of the MCP server and its dependencies.

    Returns information about:
    - Whether cursor-agent CLI is available
    - Whether the configuration is loaded
    - Number of configured agents
    """
    return check_status_impl()


def main():
    """Entry point for the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()


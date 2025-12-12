"""Invoke subagent tool for multi-agent development."""

from typing import Annotated, Optional

from ..config import get_config, load_prompt_file
from ..executor import check_cursor_agent_available, invoke_cursor_agent


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
        "Working directory path (project root) where the agent should execute. Files created by the agent will be placed here.",
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
        cwd: Working directory (project root) where agent should work.
        model: Override the default model (optional).
        timeout: Execution timeout in seconds (optional).

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
    # Check if cursor-agent is available
    available, message = check_cursor_agent_available()
    if not available:
        return {
            "success": False,
            "output": "",
            "error": message,
            "agent_role": agent_role,
            "model_used": None,
            "session_id": None,
            "duration_ms": None,
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
            "session_id": None,
            "duration_ms": None,
        }

    agent = config.agents[agent_role]
    model_to_use = model or agent.default_model

    # Load the system prompt
    try:
        system_prompt = load_prompt_file(config, agent.prompt_file)
    except FileNotFoundError as e:
        return {
            "success": False,
            "output": "",
            "error": str(e),
            "agent_role": agent_role,
            "model_used": model_to_use,
            "session_id": None,
            "duration_ms": None,
        }

    # Execute the agent
    result = await invoke_cursor_agent(
        system_prompt=system_prompt,
        task=task,
        model=model_to_use,
        cwd=cwd,
        context=context,
        timeout=timeout,
        agent_role=agent_role,
    )

    return {
        "success": result.success,
        "output": result.output,
        "error": result.error,
        "agent_role": agent_role,
        "model_used": model_to_use,
        "session_id": result.session_id,
        "duration_ms": result.duration_ms,
    }

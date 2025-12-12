"""Orchestration tool for multi-agent development."""

from ..config import get_config, load_prompt_file


def _load_orchestrator_guide() -> str:
    """Load orchestrator guide from file."""
    config = get_config()
    return load_prompt_file(config, config.orchestrator_prompt_file)


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
    config = get_config()

    # Get agents list
    agents = {}
    for role, agent in config.agents.items():
        agents[role] = {
            "name": agent.name,
            "description": agent.description,
        }

    # Load orchestrator guide from file
    try:
        guide = _load_orchestrator_guide()
    except FileNotFoundError as e:
        return {
            "error": str(e),
            "agents": agents,
        }

    return {
        "guide": guide,
        "agents": agents,
    }

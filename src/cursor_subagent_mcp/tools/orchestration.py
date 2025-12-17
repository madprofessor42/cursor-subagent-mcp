"""Orchestration tool for multi-agent development."""

from ..config import get_config, find_package_paths


def _load_orchestrator_guide() -> str:
    """Load orchestrator guide and inject agent rules."""
    config = get_config()
    
    # Load base orchestrator guide from package resources
    # This is an immutable system resource
    orch_path, _ = find_package_paths()
    
    try:
        base_guide = orch_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        base_guide = "Orchestrator guide not found in package resources."

    # Inject agent invocation rules
    rules_section = ""
    
    # Sort agents by role for consistent output
    sorted_agents = sorted(config.agents.items())
    
    for role, agent in sorted_agents:
        if agent.invocation_rules:
            rules_section += f"\n### Agent: {agent.name} (`{role}`)\n\n"
            rules_section += agent.invocation_rules + "\n"
            
    return base_guide + rules_section


def get_orchestration_guide() -> dict:
    """Get complete orchestration guide with instructions and available agents.

    CALL THIS FIRST when starting a multi-agent development task.

    This tool returns everything you need to orchestrate the development:
    - Full guide with instructions on how to coordinate agents
    - List of all available agents with their roles

    After calling this, use invoke_subagent() to call specific agents
    following the workflow described in the guide.

    Returns:
        - guide: Full orchestrator instructions (from orchestrator.md + injected rules)
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

    guide = _load_orchestrator_guide()

    return {
        "guide": guide,
        "agents": agents,
    }

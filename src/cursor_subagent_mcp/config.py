"""Configuration models for the Cursor Subagent MCP Server."""

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    name: str = Field(description="Human-readable name of the agent")
    description: str = Field(description="Description of the agent's role")
    prompt_file: str = Field(description="Path to the agent's system prompt file")
    default_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Default model to use for this agent",
    )


class Config(BaseModel):
    """Root configuration model."""

    agents: dict[str, AgentConfig] = Field(
        default_factory=dict, description="Map of agent role to configuration"
    )
    prompts_base_path: Optional[str] = Field(
        default=None, description="Base path for prompt files (optional)"
    )


def find_config_file() -> Optional[Path]:
    """Find the agents.yaml configuration file.

    Search order:
    1. Current working directory
    2. Package directory
    3. Parent directories up to root
    """
    # Check current directory
    cwd = Path.cwd()
    if (cwd / "agents.yaml").exists():
        return cwd / "agents.yaml"

    # Check package directory
    package_dir = Path(__file__).parent.parent.parent
    if (package_dir / "agents.yaml").exists():
        return package_dir / "agents.yaml"

    # Walk up from cwd
    current = cwd
    while current != current.parent:
        if (current / "agents.yaml").exists():
            return current / "agents.yaml"
        current = current.parent

    return None


def load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from YAML file.

    Args:
        config_path: Path to config file. If None, will search for it.

    Returns:
        Loaded Config object.

    Raises:
        FileNotFoundError: If config file is not found.
    """
    if config_path is None:
        config_path = find_config_file()

    if config_path is None:
        raise FileNotFoundError(
            "Could not find agents.yaml configuration file. "
            "Please create one in the project directory."
        )

    with open(config_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return Config(**data)


def get_prompt_path(config: Config, agent_role: str) -> Path:
    """Get the full path to an agent's prompt file.

    Args:
        config: The loaded configuration.
        agent_role: The role identifier of the agent.

    Returns:
        Path to the prompt file.

    Raises:
        KeyError: If agent role is not found.
        FileNotFoundError: If prompt file doesn't exist.
    """
    if agent_role not in config.agents:
        raise KeyError(f"Unknown agent role: {agent_role}")

    agent = config.agents[agent_role]
    prompt_path = Path(agent.prompt_file)

    # If relative path and base path is set, prepend it
    if not prompt_path.is_absolute() and config.prompts_base_path:
        prompt_path = Path(config.prompts_base_path) / prompt_path

    # If still relative, try relative to config file location
    if not prompt_path.is_absolute():
        config_file = find_config_file()
        if config_file:
            prompt_path = config_file.parent / prompt_path

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    return prompt_path


def load_prompt(config: Config, agent_role: str) -> str:
    """Load the system prompt for an agent.

    Args:
        config: The loaded configuration.
        agent_role: The role identifier of the agent.

    Returns:
        The content of the prompt file.
    """
    prompt_path = get_prompt_path(config, agent_role)
    return prompt_path.read_text(encoding="utf-8")


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
    orchestrator_prompt_file: str = Field(
        default="agents-master/01_orchestrator.md",
        description="Path to the orchestrator guide file",
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


def resolve_prompt_path(config: Config, relative_path: str) -> Path:
    """Resolve a relative prompt file path to an absolute path.

    Args:
        config: The loaded configuration.
        relative_path: Relative path to the prompt file.

    Returns:
        Absolute path to the prompt file.

    Raises:
        FileNotFoundError: If prompt file doesn't exist.
    """
    prompt_path = Path(relative_path)

    # If already absolute, just check existence
    if prompt_path.is_absolute():
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        return prompt_path

    # If base path is set, prepend it
    if config.prompts_base_path:
        prompt_path = Path(config.prompts_base_path) / prompt_path

    # If still relative, resolve relative to config file location
    if not prompt_path.is_absolute():
        config_file = find_config_file()
        if config_file:
            prompt_path = config_file.parent / prompt_path

    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

    return prompt_path


def load_prompt_file(config: Config, relative_path: str) -> str:
    """Load a prompt file by its relative path.

    Args:
        config: The loaded configuration.
        relative_path: Relative path to the prompt file.

    Returns:
        The content of the prompt file.

    Raises:
        FileNotFoundError: If prompt file doesn't exist.
    """
    prompt_path = resolve_prompt_path(config, relative_path)
    return prompt_path.read_text(encoding="utf-8")


"""Configuration models for the Cursor Subagent MCP Server."""

import os
import re
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

from .executor.logging import get_logger


class AgentConfig(BaseModel):
    """Configuration for a single agent."""

    name: str = Field(description="Human-readable name of the agent")
    description: str = Field(description="Description of the agent's role")
    default_model: str = Field(
        default="auto",
        description="Default model to use for this agent",
    )
    role: str = Field(description="The role identifier of the agent (filename without extension)")
    invocation_rules: str = Field(description="Rules for invoking this agent")
    prompt: str = Field(description="System prompt for the agent")
    file_path: Path = Field(description="Path to the agent configuration file")


class Config(BaseModel):
    """Root configuration model."""

    agents: dict[str, AgentConfig] = Field(
        default_factory=dict, description="Map of agent role to configuration"
    )
    agents_dir: Optional[Path] = Field(
        default=None, description="Directory containing agent definition files"
    )
    orchestrator_prompt_file: str = Field(
        default="orchestrator.md",
        description="Filename of the orchestrator guide file (relative to agents_dir)",
    )

def find_agents_dir() -> Path:
    """Find the agents directory.

    Search order:
    1. CURSOR_AGENTS_DIR environment variable
    2. AGENTS_DIR environment variable
    3. ./agents directory in current working directory
    """
    # Check env vars
    env_path = os.environ.get("CURSOR_AGENTS_DIR") or os.environ.get("AGENTS_DIR")
    if env_path:
        return Path(env_path).resolve()

    # Default to local agents directory
    return Path.cwd() / "agents"


def find_package_paths() -> tuple[Path, Path]:
    """Find package-internal paths.

    Returns:
        (orchestrator_path, default_agents_dir)
    """
    # Assuming we are running from source or standard install
    # config.py is in src/cursor_subagent_mcp/config.py
    current_file = Path(__file__).resolve()
    
    # Look for agents-master in the package root (project root)
    # Go up: config.py -> cursor_subagent_mcp -> src -> root
    package_root = current_file.parent.parent.parent
    
    agents_master = package_root / "agents-master"
    
    # For installed packages, we might need a different strategy if data files 
    # are installed elsewhere, but for now assuming source layout or included data.
    
    return agents_master / "orchestrator.md", agents_master / "default_agents"


def parse_agent_file(content: str, role: str, file_path: Path) -> AgentConfig:
    """Parse an agent markdown file into an AgentConfig object.

    Format:
    ---
    key: value
    ---

    # Invocation Rules
    ...
    """
    logger = get_logger()
    
    metadata = {}
    invocation_rules = ""
    prompt = ""
    
    # 1. Try Frontmatter
    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if frontmatter_match:
        yaml_content = frontmatter_match.group(1)
        try:
            metadata = yaml.safe_load(yaml_content) or {}
        except yaml.YAMLError as e:
             logger.warning(f"Failed to parse frontmatter YAML in {file_path}: {e}")
        
        # Remove frontmatter from content for section parsing
        content = content[frontmatter_match.end():]
        
    # 2. Parse Sections
    # We look for headers: # Metadata (legacy), # Invocation Rules, # Prompt
    
    sections = re.split(r'^#\s+(Metadata|Invocation Rules|Prompt)\s*$', content, flags=re.MULTILINE)
    
    # sections[0] is content before first header.
    # sections[1] is first header name
    # sections[2] is first header content
    # ...
    
    current_section = None
    
    # Iterate through split result
    for i in range(1, len(sections), 2):
        header = sections[i].strip()
        body = sections[i+1].strip()
        
        if header == "Metadata" and not metadata:
             try:
                metadata = yaml.safe_load(body) or {}
             except yaml.YAMLError as e:
                logger.warning(f"Failed to parse Metadata section in {file_path}: {e}")
        elif header == "Invocation Rules":
            invocation_rules = body
        elif header == "Prompt":
            prompt = body

    logger.info(f"Parsed metadata for agent {role}: {metadata}")

    return AgentConfig(
        name=metadata.get("name", role),
        description=metadata.get("description", ""),
        default_model=metadata.get("default_model", "auto"),
        role=role,
        invocation_rules=invocation_rules,
        prompt=prompt,
        file_path=file_path
    )


def load_config(agents_dir: Optional[Path] = None) -> Config:
    """Load configuration from agent files.

    Args:
        agents_dir: Path to agents directory. If None, will search for it.

    Returns:
        Loaded Config object.
    """
    if agents_dir is None:
        agents_dir = find_agents_dir()

    agents = {}
    
    if agents_dir.exists() and agents_dir.is_dir():
        # Iterate over .md files in agents_dir
        for file_path in agents_dir.glob("*.md"):
            # Skip hidden files
            if file_path.name.startswith("_") or file_path.name.startswith("."):
                continue
                
            role = file_path.stem
            
            try:
                content = file_path.read_text(encoding="utf-8")
                # Support both old format (# Metadata) and new frontmatter format
                if "# Metadata" not in content and not content.strip().startswith("---"):
                    continue
                    
                agent_config = parse_agent_file(content, role, file_path)
                agents[role] = agent_config
            except Exception as e:
                # Log error or skip
                get_logger().error(f"Error loading agent {role}: {e}")
                continue

    return Config(agents=agents, agents_dir=agents_dir)


def load_prompt_file(config: Config, relative_path: str) -> str:
    """Load a prompt file (helper for orchestrator).
    
    This is now mostly used for loading the orchestrator prompt.
    """
    if config.agents_dir is None:
         raise ValueError("Config not fully loaded: agents_dir is None")
         
    prompt_path = config.agents_dir / relative_path
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
        
    return prompt_path.read_text(encoding="utf-8")


def get_config() -> Config:
    """Get the configuration (always reloads from disk)."""
    return load_config()

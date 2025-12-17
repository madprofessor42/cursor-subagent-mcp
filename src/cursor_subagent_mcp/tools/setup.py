"""Setup cursor CLI tool for multi-agent development."""

import shutil
from typing import Annotated

from ..config import find_agents_dir, find_package_paths
from ..executor import detect_shell, install_cursor_cli


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
    target_dir = find_agents_dir()
    _, source_dir = find_package_paths()
    
    if not source_dir.exists():
        return {
            "success": False,
            "error": f"Default agents source directory not found (expected at {source_dir})",
            "path": str(target_dir),
            "copied": [],
            "skipped": []
        }

    try:
        # Create target directory
        target_dir.mkdir(parents=True, exist_ok=True)
        
        copied = []
        skipped = []
        
        # Iterate over source files
        for file_path in source_dir.glob("*.md"):
            dest_path = target_dir / file_path.name
            
            if dest_path.exists() and not force:
                skipped.append(file_path.name)
                continue
                
            shutil.copy2(file_path, dest_path)
            copied.append(file_path.name)
            
        return {
            "success": True,
            "path": str(target_dir),
            "copied": copied,
            "skipped": skipped,
            "message": f"Initialized {len(copied)} agents in {target_dir}"
        }
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "path": str(target_dir),
            "copied": [],
            "skipped": []
        }

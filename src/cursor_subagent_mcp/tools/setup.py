"""Setup cursor CLI tool for multi-agent development."""

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

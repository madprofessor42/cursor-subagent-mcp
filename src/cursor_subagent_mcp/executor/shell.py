"""Shell detection utilities."""

import os


def detect_shell() -> str:
    """Detect the current user's shell.

    Returns:
        'zsh', 'bash', or 'unknown'.
    """
    shell = os.environ.get("SHELL", "")
    if "zsh" in shell:
        return "zsh"
    elif "bash" in shell:
        return "bash"
    else:
        # Try to detect from common shell config files
        home = os.path.expanduser("~")
        if os.path.exists(os.path.join(home, ".zshrc")):
            return "zsh"
        elif os.path.exists(os.path.join(home, ".bashrc")):
            return "bash"
        return "unknown"


def get_shell_config_file() -> str:
    """Get the path to the shell configuration file.

    Returns:
        Path to .zshrc or .bashrc.
    """
    shell = detect_shell()
    home = os.path.expanduser("~")

    if shell == "zsh":
        return os.path.join(home, ".zshrc")
    else:
        return os.path.join(home, ".bashrc")

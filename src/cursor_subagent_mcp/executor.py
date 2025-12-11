"""Executor for running cursor-agent CLI subagents."""

import asyncio
import re
import shutil
from dataclasses import dataclass
from typing import Optional


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes from text.

    This removes color codes, cursor movement, and other terminal control sequences.

    Args:
        text: Text potentially containing ANSI escape codes.

    Returns:
        Clean text without ANSI codes.
    """
    # Pattern matches:
    # - \x1b (ESC) followed by [ and any parameters ending with a letter
    # - \x1b (ESC) followed by other escape sequences
    ansi_pattern = re.compile(r"\x1b\[[0-9;]*[A-Za-z]|\x1b[^[[]?")
    return ansi_pattern.sub("", text)


@dataclass
class ExecutionResult:
    """Result of a subagent execution."""

    success: bool
    output: str
    error: Optional[str] = None
    return_code: int = 0


def find_cursor_agent() -> Optional[str]:
    """Find the cursor-agent executable.

    Returns:
        Path to cursor-agent or None if not found.
    """
    import os

    # First, try the standard PATH
    path = shutil.which("cursor-agent")
    if path:
        return path

    # Check common installation locations that might not be in PATH yet
    common_paths = [
        os.path.expanduser("~/.local/bin/cursor-agent"),
        "/usr/local/bin/cursor-agent",
        os.path.expanduser("~/bin/cursor-agent"),
    ]

    for candidate in common_paths:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate

    return None


async def invoke_cursor_agent(
    system_prompt: str,
    task: str,
    model: str,
    context: str = "",
    timeout: Optional[float] = None,
) -> ExecutionResult:
    """Invoke cursor-agent CLI with the given parameters.

    Args:
        system_prompt: The system prompt for the agent.
        task: The task/user message to send to the agent.
        model: The model to use (e.g., "claude-sonnet-4-20250514").
        context: Additional context to include in the prompt.
        timeout: Optional timeout in seconds.

    Returns:
        ExecutionResult with the output from the agent.
    """
    cursor_agent = find_cursor_agent()
    if cursor_agent is None:
        return ExecutionResult(
            success=False,
            output="",
            error="cursor-agent CLI not found. Please install Cursor CLI tools.",
            return_code=-1,
        )

    # Build the full prompt combining system prompt, context, and task
    full_prompt_parts = [system_prompt]
    if context:
        full_prompt_parts.append(f"\n\n## КОНТЕКСТ\n\n{context}")
    full_prompt_parts.append(f"\n\n## ЗАДАЧА\n\n{task}")
    full_prompt = "\n".join(full_prompt_parts)

    # Build command arguments
    # cursor-agent -f --model {model} -p {prompt}
    cmd = [
        cursor_agent,
        "-f",  # Force/non-interactive mode
        "--model",
        model,
        "-p",
        full_prompt,
    ]

    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            return ExecutionResult(
                success=False,
                output="",
                error=f"Execution timed out after {timeout} seconds",
                return_code=-1,
            )

        stdout_str = stdout.decode("utf-8", errors="replace")
        stderr_str = stderr.decode("utf-8", errors="replace")

        if process.returncode == 0:
            return ExecutionResult(
                success=True,
                output=stdout_str,
                error=stderr_str if stderr_str else None,
                return_code=process.returncode,
            )
        else:
            return ExecutionResult(
                success=False,
                output=stdout_str,
                error=stderr_str or f"Process exited with code {process.returncode}",
                return_code=process.returncode,
            )

    except FileNotFoundError:
        return ExecutionResult(
            success=False,
            output="",
            error=f"Failed to execute cursor-agent at: {cursor_agent}",
            return_code=-1,
        )
    except Exception as e:
        return ExecutionResult(
            success=False,
            output="",
            error=f"Unexpected error: {str(e)}",
            return_code=-1,
        )


def check_cursor_agent_available() -> tuple[bool, str]:
    """Check if cursor-agent CLI is available.

    Returns:
        Tuple of (is_available, message).
    """
    path = find_cursor_agent()
    if path:
        return True, f"cursor-agent found at: {path}"
    else:
        return False, (
            "cursor-agent CLI not found in PATH. "
            "Please install Cursor CLI tools: "
            "https://docs.cursor.com/cli"
        )


def detect_shell() -> str:
    """Detect the current user's shell.

    Returns:
        'zsh', 'bash', or 'unknown'.
    """
    import os

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
    import os

    shell = detect_shell()
    home = os.path.expanduser("~")

    if shell == "zsh":
        return os.path.join(home, ".zshrc")
    else:
        return os.path.join(home, ".bashrc")


async def install_cursor_cli() -> ExecutionResult:
    """Install cursor-agent CLI.

    This function:
    1. Downloads and runs the Cursor CLI installer
    2. Adds ~/.local/bin to PATH in the appropriate shell config

    Returns:
        ExecutionResult with installation status.
    """
    import os

    steps_output = []

    # Step 1: Run the installation script
    steps_output.append("Step 1: Downloading and installing Cursor CLI...")

    install_cmd = "curl -L https://cursor.com/install | gunzip | bash"

    try:
        process = await asyncio.create_subprocess_shell(
            install_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=120,  # 2 minutes timeout for download
        )

        stdout_str = strip_ansi(stdout.decode("utf-8", errors="replace"))
        stderr_str = strip_ansi(stderr.decode("utf-8", errors="replace"))

        # Extract only the important status lines from installer output
        # Skip the "Next Steps" section since we handle PATH configuration ourselves
        important_lines = []
        skip_section = False
        for line in stdout_str.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Skip the "Next Steps" instruction section
            if "Next Steps" in line:
                skip_section = True
                continue
            if skip_section and line.startswith(("1.", "2.", "For bash:", "For zsh:", "echo", "source", "cursor-agent")):
                continue
            if "Happy coding" in line:
                skip_section = False
                continue
            # Keep important status lines
            if line.startswith(("✓", "▸", "✨")) or "Installer" in line or "Detected" in line:
                important_lines.append(line)

        stdout_clean = "\n".join(important_lines)

        if process.returncode != 0:
            return ExecutionResult(
                success=False,
                output="\n".join(steps_output) + "\n\n" + stdout_clean,
                error=f"Installation failed: {stderr_str}",
                return_code=process.returncode,
            )

        steps_output.append(stdout_clean)
        steps_output.append("\n✓ Cursor CLI installed successfully")

    except asyncio.TimeoutError:
        return ExecutionResult(
            success=False,
            output="\n".join(steps_output),
            error="Installation timed out after 120 seconds",
            return_code=-1,
        )
    except Exception as e:
        return ExecutionResult(
            success=False,
            output="\n".join(steps_output),
            error=f"Installation error: {str(e)}",
            return_code=-1,
        )

    # Step 2: Add to PATH in shell config
    steps_output.append("\n\nStep 2: Configuring PATH...")

    shell_config = get_shell_config_file()
    path_export = 'export PATH="$HOME/.local/bin:$PATH"'
    shell_name = detect_shell()

    try:
        # Check if already configured
        already_configured = False
        if os.path.exists(shell_config):
            with open(shell_config, "r") as f:
                content = f.read()
                if ".local/bin" in content:
                    already_configured = True
                    steps_output.append(
                        f"✓ PATH already configured in {shell_config}"
                    )

        if not already_configured:
            # Append to shell config
            with open(shell_config, "a") as f:
                f.write(f"\n# Added by cursor-subagent-mcp installer\n")
                f.write(f"{path_export}\n")

            steps_output.append(f"✓ Added PATH to {shell_config}")

        # Step 3: Provide instructions
        steps_output.append("\n\nStep 3: Finalization")
        steps_output.append(
            f"→ Run 'source {shell_config}' or restart your terminal to apply PATH changes."
        )

        # Check if cursor-agent is now available
        # First, try with the new PATH
        new_path = os.path.expanduser("~/.local/bin")
        cursor_agent_path = os.path.join(new_path, "cursor-agent")

        if os.path.exists(cursor_agent_path):
            steps_output.append(f"\n✓ cursor-agent found at: {cursor_agent_path}")
        else:
            steps_output.append(
                "\n⚠ Note: cursor-agent may require terminal restart to be available"
            )

        return ExecutionResult(
            success=True,
            output="\n".join(steps_output),
            error=None,
            return_code=0,
        )

    except Exception as e:
        return ExecutionResult(
            success=False,
            output="\n".join(steps_output),
            error=f"Failed to configure PATH: {str(e)}",
            return_code=-1,
        )


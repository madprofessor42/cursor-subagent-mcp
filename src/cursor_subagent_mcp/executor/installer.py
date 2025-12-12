"""CLI installation utilities."""

import asyncio
import os

from .models import ExecutionResult
from .shell import detect_shell, get_shell_config_file
from .utils import strip_ansi


async def install_cursor_cli() -> ExecutionResult:
    """Install cursor-agent CLI.

    This function:
    1. Downloads and runs the Cursor CLI installer
    2. Adds ~/.local/bin to PATH in the appropriate shell config

    Returns:
        ExecutionResult with installation status.
    """
    steps_output = []

    # Step 1: Run the installation script
    steps_output.append("Step 1: Downloading and installing Cursor CLI...")

    install_cmd = "curl -L https://cursor.com/install | gunzip | bash"

    try:
        process = await asyncio.create_subprocess_shell(
            install_cmd,
            stdin=asyncio.subprocess.DEVNULL,  # Explicitly close stdin
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

        # Check if cursor-agent is now available
        new_path = os.path.expanduser("~/.local/bin")
        cursor_agent_path = os.path.join(new_path, "cursor-agent")

        if os.path.exists(cursor_agent_path):
            steps_output.append(f"✓ cursor-agent found at: {cursor_agent_path}")
        else:
            steps_output.append(
                "⚠ Note: cursor-agent may require terminal restart to be available"
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

    # Step 3: Run cursor-agent login
    steps_output.append("\n\nStep 3: Authenticating cursor-agent...")

    try:
        login_process = await asyncio.create_subprocess_exec(
            cursor_agent_path,
            "login",
            stdin=asyncio.subprocess.DEVNULL,  # Explicitly close stdin
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        login_stdout, login_stderr = await asyncio.wait_for(
            login_process.communicate(),
            timeout=120,  # 2 minutes timeout for login
        )

        login_stdout_str = strip_ansi(login_stdout.decode("utf-8", errors="replace"))
        login_stderr_str = strip_ansi(login_stderr.decode("utf-8", errors="replace"))

        if login_process.returncode == 0:
            steps_output.append("✓ cursor-agent authenticated successfully")
            if login_stdout_str.strip():
                steps_output.append(login_stdout_str.strip())
        else:
            steps_output.append(f"⚠ Authentication may require manual login: {login_stderr_str}")

    except asyncio.TimeoutError:
        steps_output.append("⚠ Authentication timed out - please run 'cursor-agent login' manually")
    except Exception as e:
        steps_output.append(f"⚠ Authentication error: {str(e)} - please run 'cursor-agent login' manually")

    # Step 4: Finalization
    steps_output.append("\n\nStep 4: Finalization")
    steps_output.append(
        f"→ Run 'source {shell_config}' or restart your terminal to apply PATH changes."
    )

    return ExecutionResult(
        success=True,
        output="\n".join(steps_output),
        error=None,
        return_code=0,
    )

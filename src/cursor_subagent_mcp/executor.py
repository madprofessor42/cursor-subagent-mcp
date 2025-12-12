"""Executor for running cursor-agent CLI subagents."""

import asyncio
import json
import logging
import os
import re
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

# Setup logging
_logger: Optional[logging.Logger] = None


def get_logger() -> logging.Logger:
    """Get or create the agent logger."""
    global _logger
    if _logger is None:
        _logger = _setup_logger()
    return _logger


def _setup_logger() -> logging.Logger:
    """Setup logging to file in logs directory."""
    # Find project root (where agents.yaml is)
    from .config import find_config_file
    
    config_file = find_config_file()
    if config_file:
        logs_dir = config_file.parent / "logs"
    else:
        logs_dir = Path.cwd() / "logs"
    
    logs_dir.mkdir(exist_ok=True)
    
    # Create logger
    logger = logging.getLogger("cursor_subagent")
    logger.setLevel(logging.DEBUG)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # File handler - one file per day
    log_file = logs_dir / f"agents_{datetime.now().strftime('%Y-%m-%d')}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(file_handler)
    
    return logger


@dataclass
class StreamEvent:
    """Event from cursor-agent stream."""
    event_type: str
    subtype: Optional[str] = None
    data: dict = field(default_factory=dict)
    
    @classmethod
    def from_json(cls, line: str) -> Optional["StreamEvent"]:
        """Parse a JSON line into a StreamEvent."""
        try:
            data = json.loads(line)
            return cls(
                event_type=data.get("type", "unknown"),
                subtype=data.get("subtype"),
                data=data
            )
        except json.JSONDecodeError:
            return None


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


def extract_final_json(text: str) -> Optional[str]:
    """Extract final JSON from agent response.
    
    Looks for JSON in markdown code blocks (```json ... ```) or as raw JSON.
    Returns the last JSON found in the text, or None if no valid JSON found.
    
    Args:
        text: Full text response from agent.
        
    Returns:
        JSON string if found, None otherwise.
    """
    if not text:
        return None
    
    # Try to find JSON in markdown code blocks first
    json_block_pattern = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)
    json_matches = json_block_pattern.findall(text)
    if json_matches:
        # Return the last JSON block found
        try:
            json.loads(json_matches[-1])  # Validate it's valid JSON
            return json_matches[-1].strip()
        except json.JSONDecodeError:
            pass
    
    # Try to find raw JSON blocks (``` ... ``` without json label)
    code_block_pattern = re.compile(r"```\s*\n(.*?)\n```", re.DOTALL)
    code_matches = code_block_pattern.findall(text)
    for match in reversed(code_matches):  # Check from end to start
        try:
            parsed = json.loads(match.strip())
            # If it's a dict or list, it's likely JSON
            if isinstance(parsed, (dict, list)):
                return match.strip()
        except json.JSONDecodeError:
            continue
    
    # Try to find JSON at the end of the text (common pattern)
    # Look for { ... } or [ ... ] patterns
    json_object_pattern = re.compile(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", re.DOTALL)
    json_array_pattern = re.compile(r"\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]", re.DOTALL)
    
    # Try object first
    object_matches = json_object_pattern.findall(text)
    for match in reversed(object_matches):
        try:
            json.loads(match)
            return match.strip()
        except json.JSONDecodeError:
            continue
    
    # Try array
    array_matches = json_array_pattern.findall(text)
    for match in reversed(array_matches):
        try:
            json.loads(match)
            return match.strip()
        except json.JSONDecodeError:
            continue
    
    return None


@dataclass
class ExecutionResult:
    """Result of a subagent execution."""

    success: bool
    output: str
    error: Optional[str] = None
    return_code: int = 0
    events: list[StreamEvent] = field(default_factory=list)
    session_id: Optional[str] = None
    duration_ms: Optional[int] = None


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


def _log_event(logger: logging.Logger, event: StreamEvent, agent_role: str) -> None:
    """Log a stream event with appropriate formatting."""
    if event.event_type == "system" and event.subtype == "init":
        logger.info(f"[{agent_role}] Session started: {event.data.get('session_id', 'unknown')}")
        logger.info(f"[{agent_role}] Model: {event.data.get('model', 'unknown')}")
        logger.info(f"[{agent_role}] CWD: {event.data.get('cwd', 'unknown')}")
    
    elif event.event_type == "assistant":
        content = event.data.get("message", {}).get("content", [])
        text = "".join(c.get("text", "") for c in content if c.get("type") == "text")
        if text:
            # Log first 200 chars of assistant message
            preview = text[:200] + "..." if len(text) > 200 else text
            logger.debug(f"[{agent_role}] Assistant: {preview}")
    
    elif event.event_type == "tool_call":
        tool_call = event.data.get("tool_call", {})
        
        if "readToolCall" in tool_call:
            args = tool_call["readToolCall"].get("args", {})
            path = args.get("path", "unknown")
            if event.subtype == "started":
                logger.info(f"[{agent_role}] 📖 Reading file: {path}")
            elif event.subtype == "completed":
                result = tool_call["readToolCall"].get("result", {}).get("success", {})
                lines = result.get("totalLines", "?")
                logger.info(f"[{agent_role}] ✓ Read {path} ({lines} lines)")
        
        elif "writeToolCall" in tool_call:
            args = tool_call["writeToolCall"].get("args", {})
            path = args.get("path", "unknown")
            if event.subtype == "started":
                logger.info(f"[{agent_role}] ✏️ Writing file: {path}")
            elif event.subtype == "completed":
                result = tool_call["writeToolCall"].get("result", {}).get("success", {})
                lines = result.get("linesCreated", "?")
                logger.info(f"[{agent_role}] ✓ Wrote {path} ({lines} lines)")
        
        elif "function" in tool_call:
            func_name = tool_call["function"].get("name", "unknown")
            if event.subtype == "started":
                logger.info(f"[{agent_role}] 🔧 Tool call: {func_name}")
            elif event.subtype == "completed":
                logger.info(f"[{agent_role}] ✓ Tool completed: {func_name}")
    
    elif event.event_type == "result":
        duration = event.data.get("duration_ms", 0)
        logger.info(f"[{agent_role}] Session completed in {duration}ms")


async def invoke_cursor_agent(
    system_prompt: str,
    task: str,
    model: str,
    cwd: str,
    context: str = "",
    timeout: Optional[float] = None,
    agent_role: str = "agent",
    on_event: Optional[Callable[[StreamEvent], None]] = None,
) -> ExecutionResult:
    """Invoke cursor-agent CLI with streaming and logging.

    Args:
        system_prompt: The system prompt for the agent.
        task: The task/user message to send to the agent.
        model: The model to use (e.g., "claude-sonnet-4-20250514").
        cwd: Working directory for the agent (project root path).
        context: Additional context to include in the prompt.
        timeout: Optional timeout in seconds.
        agent_role: Role name for logging (e.g., "analyst", "developer").
        on_event: Optional callback for real-time event processing.

    Returns:
        ExecutionResult with the output from the agent.
    """
    logger = get_logger()
    
    cursor_agent = find_cursor_agent()
    if cursor_agent is None:
        logger.error(f"[{agent_role}] cursor-agent CLI not found")
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

    # Log invocation
    logger.info(f"[{agent_role}] === Starting agent invocation ===")
    logger.info(f"[{agent_role}] Model: {model}")
    logger.info(f"[{agent_role}] CWD: {cwd}")
    logger.info(f"[{agent_role}] Task: {task[:100]}..." if len(task) > 100 else f"[{agent_role}] Task: {task}")

    # Build command with streaming JSON output
    # According to https://cursor.com/docs/cli/reference/parameters:
    # - `-p, --print` is for printing to console (required for --output-format)
    # - prompt is passed as positional argument
    cmd = [
        cursor_agent,
        "--print",  # Required for --output-format to work
        "--output-format", "stream-json",
        "--model", model,
        "-f",  # Force allow commands unless explicitly denied
        full_prompt,  # Positional argument: initial prompt
    ]

    events: list[StreamEvent] = []
    assistant_messages: list[str] = []
    session_id: Optional[str] = None
    duration_ms: Optional[int] = None
    stderr_output: list[str] = []

    try:
        # Increase buffer limit to handle large JSON objects from cursor-agent
        # Default is 64KB, we set it to 10MB to handle large file contents
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,  # Explicitly close stdin
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=10 * 1024 * 1024,  # 10MB buffer limit
            cwd=cwd,  # Set working directory for the agent
        )

        async def read_stderr():
            """Read stderr in background."""
            assert process.stderr is not None
            async for line in process.stderr:
                stderr_output.append(line.decode("utf-8", errors="replace"))

        # Start reading stderr in background
        stderr_task = asyncio.create_task(read_stderr())

        try:
            # Read stdout line by line (NDJSON stream)
            assert process.stdout is not None
            
            async def process_stream():
                nonlocal session_id, duration_ms
                async for line in process.stdout:
                    line_str = line.decode("utf-8", errors="replace").strip()
                    if not line_str:
                        continue
                    
                    event = StreamEvent.from_json(line_str)
                    if event:
                        events.append(event)
                        _log_event(logger, event, agent_role)
                        
                        # Call optional callback
                        if on_event:
                            try:
                                on_event(event)
                            except Exception as e:
                                logger.warning(f"[{agent_role}] Event callback error: {e}")
                        
                        # Extract session_id
                        if event.event_type == "system" and event.subtype == "init":
                            session_id = event.data.get("session_id")
                        
                        # Collect assistant messages
                        if event.event_type == "assistant":
                            content = event.data.get("message", {}).get("content", [])
                            for c in content:
                                if c.get("type") == "text":
                                    assistant_messages.append(c.get("text", ""))
                        
                        # Extract duration from result
                        if event.event_type == "result":
                            duration_ms = event.data.get("duration_ms")

            await asyncio.wait_for(process_stream(), timeout=timeout)
            await process.wait()
            
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            logger.error(f"[{agent_role}] Execution timed out after {timeout} seconds")
            # Try to extract JSON from partial output
            partial_output = "".join(assistant_messages)
            logger.debug(f"[{agent_role}] Partial output on timeout ({len(partial_output)} chars)")
            final_json = extract_final_json(partial_output)
            output_to_return = final_json if final_json else partial_output
            return ExecutionResult(
                success=False,
                output=output_to_return,
                error=f"Execution timed out after {timeout} seconds",
                return_code=-1,
                events=events,
                session_id=session_id,
            )
        finally:
            stderr_task.cancel()
            try:
                await stderr_task
            except asyncio.CancelledError:
                pass

        # Combine all assistant messages for logging
        full_output = "".join(assistant_messages)
        
        # Log full output for debugging
        logger.debug(f"[{agent_role}] Full assistant output ({len(full_output)} chars)")
        if full_output:
            # Log first 500 chars for visibility
            preview = full_output[:500] + "..." if len(full_output) > 500 else full_output
            logger.info(f"[{agent_role}] Assistant response preview: {preview}")
        
        # Extract final JSON from response (for output)
        final_json = extract_final_json(full_output)
        if final_json:
            logger.info(f"[{agent_role}] Extracted JSON response ({len(final_json)} chars)")
            output_to_return = final_json
        else:
            # Fallback: return full output if no JSON found
            logger.warning(f"[{agent_role}] No JSON found in response, returning full output")
            output_to_return = full_output
        
        stderr_str = "".join(stderr_output).strip()

        if process.returncode == 0:
            logger.info(f"[{agent_role}] === Agent completed successfully ===")
            return ExecutionResult(
                success=True,
                output=output_to_return,
                error=stderr_str if stderr_str else None,
                return_code=process.returncode,
                events=events,
                session_id=session_id,
                duration_ms=duration_ms,
            )
        else:
            logger.error(f"[{agent_role}] Agent failed with code {process.returncode}: {stderr_str}")
            return ExecutionResult(
                success=False,
                output=output_to_return,
                error=stderr_str or f"Process exited with code {process.returncode}",
                return_code=process.returncode,
                events=events,
                session_id=session_id,
                duration_ms=duration_ms,
            )

    except FileNotFoundError:
        logger.error(f"[{agent_role}] Failed to execute cursor-agent at: {cursor_agent}")
        return ExecutionResult(
            success=False,
            output="",
            error=f"Failed to execute cursor-agent at: {cursor_agent}",
            return_code=-1,
        )
    except Exception as e:
        logger.exception(f"[{agent_role}] Unexpected error: {e}")
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


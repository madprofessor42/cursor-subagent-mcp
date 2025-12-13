"""Main execution logic for running cursor-agent CLI subagents.

Simplified and optimized version with:
- Cleaner async stream processing
- Reduced stderr wait times
- Better separation of concerns
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from .cli import find_cursor_agent
from .logging import get_logger
from .models import ExecutionResult, StreamEvent
from .utils import extract_final_json


@dataclass
class _StreamState:
    """Internal state for stream processing."""
    events: list[StreamEvent] = field(default_factory=list)
    assistant_messages: list[str] = field(default_factory=list)
    session_id: Optional[str] = None
    duration_ms: Optional[int] = None
    stderr_lines: list[str] = field(default_factory=list)
    stream_error: Optional[Exception] = None


class _EventLogger:
    """Handles logging of stream events."""
    
    def __init__(self, logger: logging.Logger, agent_role: str):
        self._logger = logger
        self._role = agent_role
    
    def log(self, event: StreamEvent) -> None:
        """Log event with appropriate formatting."""
        handlers = {
            ("system", "init"): self._log_init,
            ("assistant", None): self._log_assistant,
            ("tool_call", None): self._log_tool_call,
            ("result", None): self._log_result,
        }
        
        key = (event.event_type, event.subtype if event.event_type == "system" else None)
        handler = handlers.get(key) or handlers.get((event.event_type, None))
        if handler:
            handler(event)
    
    def _log_init(self, event: StreamEvent) -> None:
        data = event.data
        self._logger.info(f"[{self._role}] Session: {data.get('session_id', '?')[:8]}... | Model: {data.get('model', '?')}")
    
    def _log_assistant(self, event: StreamEvent) -> None:
        content = event.data.get("message", {}).get("content", [])
        text = "".join(c.get("text", "") for c in content if c.get("type") == "text")
        if text:
            preview = text[:150] + "..." if len(text) > 150 else text
            self._logger.debug(f"[{self._role}] 💬 {preview}")
    
    def _log_tool_call(self, event: StreamEvent) -> None:
        tool_call = event.data.get("tool_call", {})
        
        for tool_type, emoji in [("readToolCall", "📖"), ("writeToolCall", "✏️"), ("function", "🔧")]:
            if tool_type in tool_call:
                self._log_specific_tool(tool_call[tool_type], tool_type, emoji, event.subtype)
                return
    
    def _log_specific_tool(self, tool_data: dict, tool_type: str, emoji: str, subtype: Optional[str]) -> None:
        if tool_type == "function":
            name = tool_data.get("name", "?")
        else:
            name = tool_data.get("args", {}).get("path", "?")
        
        if subtype == "started":
            self._logger.info(f"[{self._role}] {emoji} {name}")
        elif subtype == "completed":
            self._logger.debug(f"[{self._role}] ✓ {name}")
    
    def _log_result(self, event: StreamEvent) -> None:
        duration = event.data.get("duration_ms", 0)
        self._logger.info(f"[{self._role}] ⏱️ Completed in {duration}ms")


async def _read_stream(
    stdout: asyncio.StreamReader,
    state: _StreamState,
    event_logger: _EventLogger,
    logger: logging.Logger,
    agent_role: str,
) -> None:
    """Read and process stdout stream."""
    try:
        async for line in stdout:
            line_str = line.decode("utf-8", errors="replace").strip()
            if not line_str:
                continue
            
            event = StreamEvent.from_json(line_str)
            if not event:
                logger.debug(f"[{agent_role}] Failed to parse JSON line: {line_str[:100]}")
                continue
            
            # Skip noisy thinking events entirely (they spam the logs)
            if event.event_type == "thinking":
                continue
            
            # Log event types for debugging
            logger.debug(f"[{agent_role}] Event: type={event.event_type}, subtype={event.subtype}")
                
            state.events.append(event)
            event_logger.log(event)
            
            # Extract metadata
            if event.event_type == "system" and event.subtype == "init":
                state.session_id = event.data.get("session_id")
            elif event.event_type == "assistant":
                content = event.data.get("message", {}).get("content", [])
                for c in content:
                    if c.get("type") == "text":
                        state.assistant_messages.append(c.get("text", ""))
            elif event.event_type == "result":
                state.duration_ms = event.data.get("duration_ms")
                logger.info(f"[{agent_role}] 📊 Result event received: duration_ms={state.duration_ms}")
                
    except (BrokenPipeError, ConnectionError, OSError) as e:
        logger.debug(f"[{agent_role}] Stream closed: {type(e).__name__}")
    except Exception as e:
        state.stream_error = e
        logger.debug(f"[{agent_role}] Stream error: {e}")


async def _read_stderr(stderr: asyncio.StreamReader, state: _StreamState) -> None:
    """Read stderr stream."""
    try:
        async for line in stderr:
            state.stderr_lines.append(line.decode("utf-8", errors="replace"))
    except Exception:
        pass


def _build_result(
    state: _StreamState,
    return_code: int,
    logger: logging.Logger,
    agent_role: str,
) -> ExecutionResult:
    """Build ExecutionResult from collected state."""
    full_output = "".join(state.assistant_messages)
    stderr_str = "".join(state.stderr_lines).strip()
    
    # Debug: log collected event types
    event_types = [f"{e.event_type}:{e.subtype}" for e in state.events]
    logger.debug(f"[{agent_role}] Collected events: {event_types}")
    logger.debug(f"[{agent_role}] duration_ms from state: {state.duration_ms}")
    
    # Try to extract JSON
    final_json = extract_final_json(full_output)
    output = final_json if final_json else full_output
    
    if final_json:
        logger.debug(f"[{agent_role}] Extracted JSON ({len(final_json)} chars)")
    
    # Check for known non-critical errors
    is_http_error = any(x in stderr_str for x in ["Premature close", "NGHTTP2"])
    has_output = len(output.strip()) > 50
    
    # Determine success
    success = return_code == 0 or (is_http_error and has_output)
    
    # Build error message
    error = None
    if not success:
        parts = []
        if stderr_str and not (is_http_error and has_output):
            parts.append(stderr_str[:500])
        if state.stream_error:
            parts.append(str(state.stream_error))
        if not parts:
            parts.append(f"Exit code: {return_code}")
        error = " | ".join(parts)
    
    if success:
        logger.info(f"[{agent_role}] ✅ Agent completed")
    else:
        logger.error(f"[{agent_role}] ❌ Agent failed: {error}")
    
    return ExecutionResult(
        success=success,
        output=output,
        error=error,
        return_code=return_code,
        events=state.events,
        session_id=state.session_id,
        duration_ms=state.duration_ms,
    )


async def invoke_cursor_agent(
    system_prompt: str,
    task: str,
    model: str,
    cwd: str,
    workspace: Optional[str] = None,
    context: str = "",
    timeout: Optional[float] = None,
    agent_role: str = "agent",
) -> ExecutionResult:
    """Invoke cursor-agent CLI with streaming and logging.

    Args:
        system_prompt: The system prompt for the agent.
        task: The task/user message to send to the agent.
        model: The model to use (e.g., "claude-sonnet-4-20250514").
        cwd: Working directory for the agent process.
        workspace: Workspace directory for file access. Defaults to cwd.
        context: Additional context to include in the prompt.
        timeout: Optional timeout in seconds.
        agent_role: Role name for logging.

    Returns:
        ExecutionResult with the output from the agent.
    """
    logger = get_logger()
    
    # Find CLI
    cursor_agent = find_cursor_agent()
    if not cursor_agent:
        return ExecutionResult(
            success=False, output="",
            error="cursor-agent CLI not found", return_code=-1,
        )
    
    # Build prompt
    prompt_parts = [system_prompt]
    if context:
        prompt_parts.append(f"\n\n## КОНТЕКСТ\n\n{context}")
    prompt_parts.append(f"\n\n## ЗАДАЧА\n\n{task}")
    full_prompt = "".join(prompt_parts)
    
    workspace_dir = workspace or cwd
    
    # Log start
    task_preview = task[:80] + "..." if len(task) > 80 else task
    logger.info(f"[{agent_role}] 🚀 Starting | Model: {model} | Task: {task_preview}")
    
    # Build command
    cmd = [
        cursor_agent,
        "--print",
        "--output-format", "stream-json",
        "--model", model,
        "--workspace", workspace_dir,
        "-f",
        full_prompt,
    ]
    
    state = _StreamState()
    event_logger = _EventLogger(logger, agent_role)
    
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=10 * 1024 * 1024,
            cwd=cwd,
        )
        
        assert process.stdout and process.stderr
        
        # Create stream reading tasks
        stdout_task = asyncio.create_task(
            _read_stream(process.stdout, state, event_logger, logger, agent_role)
        )
        stderr_task = asyncio.create_task(
            _read_stderr(process.stderr, state)
        )
        
        try:
            # IMPORTANT: Read stdout first, then wait for process
            # Process completion may close streams before we read everything
            # So we read streams to completion first, then wait for process
            
            async def read_streams_and_wait():
                # Wait for stdout to complete (reads until EOF)
                await stdout_task
                # Then wait for stderr (usually finishes quickly)
                await stderr_task
                # Finally wait for process to exit
                return await process.wait()
            
            await asyncio.wait_for(read_streams_and_wait(), timeout=timeout)
                    
        except asyncio.TimeoutError:
            # Timeout - kill process
            process.kill()
            await process.wait()
            
            # Cancel stream tasks
            stdout_task.cancel()
            stderr_task.cancel()
            
            partial_output = "".join(state.assistant_messages)
            return ExecutionResult(
                success=False,
                output=extract_final_json(partial_output) or partial_output,
                error=f"Timeout after {timeout}s",
                return_code=-1,
                events=state.events,
                session_id=state.session_id,
            )
        
        return _build_result(state, process.returncode or 0, logger, agent_role)
        
    except FileNotFoundError:
        return ExecutionResult(
            success=False, output="",
            error=f"cursor-agent not found: {cursor_agent}", return_code=-1,
        )
    except Exception as e:
        logger.exception(f"[{agent_role}] Unexpected error")
        return ExecutionResult(
            success=False, output="",
            error=str(e), return_code=-1,
        )

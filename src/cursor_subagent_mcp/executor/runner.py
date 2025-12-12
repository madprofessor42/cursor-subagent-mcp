"""Main execution logic for running cursor-agent CLI subagents."""

import asyncio
import logging
from typing import Optional

from .cli import find_cursor_agent
from .logging import get_logger
from .models import ExecutionResult, StreamEvent
from .utils import extract_final_json


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
        cwd: Working directory for the agent process (where output files are saved).
        workspace: Workspace directory that agent can access (read/write files).
                   If not provided, defaults to cwd.
        context: Additional context to include in the prompt.
        timeout: Optional timeout in seconds.
        agent_role: Role name for logging (e.g., "analyst", "developer").

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

    # Use workspace if provided, otherwise default to cwd
    workspace_to_use = workspace or cwd
    
    # Log invocation
    logger.info(f"[{agent_role}] === Starting agent invocation ===")
    logger.info(f"[{agent_role}] Model: {model}")
    logger.info(f"[{agent_role}] CWD: {cwd}")
    logger.info(f"[{agent_role}] Workspace: {workspace_to_use}")
    logger.info(f"[{agent_role}] Task: {task[:100]}..." if len(task) > 100 else f"[{agent_role}] Task: {task}")

    # Build command with streaming JSON output
    # According to https://cursor.com/docs/cli/reference/parameters:
    # - `-p, --print` is for printing to console (required for --output-format)
    # - `--workspace` sets the workspace directory for file access (what agent can read/write)
    # - cwd sets the process working directory (where output files are saved)
    # - prompt is passed as positional argument
    cmd = [
        cursor_agent,
        "--print",  # Required for --output-format to work
        "--output-format", "stream-json",
        "--model", model,
        "--workspace", workspace_to_use,  # Set workspace directory for file access
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
            try:
                async for line in process.stderr:
                    stderr_output.append(line.decode("utf-8", errors="replace"))
            except Exception as e:
                # Stream closed or other error - log but don't fail
                logger.debug(f"[{agent_role}] Error reading stderr: {e}")

        # Start reading stderr in background
        stderr_task = asyncio.create_task(read_stderr())

        stream_error: Optional[Exception] = None
        
        try:
            # Read stdout line by line (NDJSON stream)
            assert process.stdout is not None
            
            async def process_stream():
                nonlocal session_id, duration_ms, stream_error
                # Read stream until EOF - similar to TypeScript event-based approach
                # Don't stop reading on errors, let the process complete naturally
                try:
                    async for line in process.stdout:
                        try:
                            line_str = line.decode("utf-8", errors="replace").strip()
                            if not line_str:
                                continue
                            
                            event = StreamEvent.from_json(line_str)
                            if event:
                                events.append(event)
                                _log_event(logger, event, agent_role)
                                
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
                        except Exception as e:
                            # Error processing a line - log but continue reading
                            logger.debug(f"[{agent_role}] Error processing line: {e}")
                            continue
                except (BrokenPipeError, ConnectionError, OSError) as e:
                    # Stream closed - this is normal when process completes
                    # Don't treat as critical error, just note it
                    logger.debug(f"[{agent_role}] Stream reading completed (closed): {e}")
                except Exception as e:
                    # Other unexpected errors during stream reading
                    stream_error = e
                    logger.debug(f"[{agent_role}] Stream reading error: {e}")

            # Read stream - it may complete normally or close prematurely
            # In either case, we continue to wait for process completion
            try:
                await asyncio.wait_for(process_stream(), timeout=timeout)
            except asyncio.TimeoutError:
                # Timeout - handled in outer except block
                raise
            
            # Stream reading completed (normally or with error)
            # Now wait for process to complete if it hasn't already
            if process.returncode is None:
                # Process still running, wait for it to finish
                try:
                    await asyncio.wait_for(process.wait(), timeout=10.0)
                except asyncio.TimeoutError:
                    # Process is still running after stream ended - kill it
                    logger.warning(f"[{agent_role}] Process still running after stream ended, killing")
                    process.kill()
                    await process.wait()
            else:
                # Process already finished
                logger.debug(f"[{agent_role}] Process already finished with code {process.returncode}")
            
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
            # Wait for stderr reading to complete naturally
            # Don't cancel immediately - let it finish reading any remaining errors
            if not stderr_task.done():
                try:
                    # Give stderr a moment to finish reading
                    await asyncio.wait_for(stderr_task, timeout=2.0)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    # If it's taking too long or was cancelled, cancel it
                    stderr_task.cancel()
                    try:
                        await stderr_task
                    except asyncio.CancelledError:
                        pass
                    except Exception as e:
                        logger.debug(f"[{agent_role}] Error cancelling stderr task: {e}")
            
            # Don't close stdout/stderr streams manually - let the process handle cleanup
            # Closing them prematurely can interrupt the process's graceful shutdown
            # The streams will be closed automatically when the process terminates

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

        # Check if stderr contains "Premature close" - this is an HTTP connection error
        # that may occur even when the task completes successfully
        is_premature_close = (
            "Premature close" in stderr_str or 
            "premature close" in stderr_str.lower() or
            "NGHTTP2_INTERNAL_ERROR" in stderr_str
        )
        
        # If we have useful output and only premature close error, treat as success
        # This matches the behavior in TypeScript projects where they return results
        # even if process exits with non-zero code but has useful output
        has_useful_output = len(output_to_return.strip()) > 100  # At least 100 chars
        
        # Combine error messages
        error_parts = []
        if stderr_str and not (is_premature_close and has_useful_output):
            # Include stderr unless it's just premature close and we have useful output
            error_parts.append(stderr_str)
        if stream_error is not None:
            error_parts.append(f"Stream error: {stream_error}")
        
        # If no specific error messages but process failed, add generic message
        if process.returncode != 0 and len(error_parts) == 0:
            error_parts.append(f"Process exited with code {process.returncode}")
        
        combined_error = " | ".join(error_parts) if error_parts else None

        # Treat as success if:
        # 1. Process exited with code 0, OR
        # 2. Process exited with non-zero but we have useful output and only premature close error
        if process.returncode == 0 or (is_premature_close and has_useful_output):
            if process.returncode != 0:
                logger.warning(
                    f"[{agent_role}] Process exited with code {process.returncode} "
                    f"but got useful output. Treating as success despite premature close."
                )
            else:
                logger.info(f"[{agent_role}] === Agent completed successfully ===")
            return ExecutionResult(
                success=True,
                output=output_to_return,
                error=None if (is_premature_close and has_useful_output) else (stderr_str if stderr_str else None),
                return_code=process.returncode,
                events=events,
                session_id=session_id,
                duration_ms=duration_ms,
            )
        else:
            logger.error(f"[{agent_role}] Agent failed with code {process.returncode}: {combined_error}")
            return ExecutionResult(
                success=False,
                output=output_to_return,
                error=combined_error or f"Process exited with code {process.returncode}",
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

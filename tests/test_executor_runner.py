"""Tests for executor.runner module."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cursor_subagent_mcp.executor.models import ExecutionResult, StreamEvent
from cursor_subagent_mcp.executor.runner import invoke_cursor_agent


class TestInvokeCursorAgent:
    """Tests for invoke_cursor_agent() function."""

    @pytest.mark.asyncio
    async def test_invoke_cursor_agent_success(self, reset_logger_singleton):
        """TC-UNIT-06.1: UC-06.1 - Проверка успешного выполнения."""
        # Настраиваем моки
        mock_logger = MagicMock()
        mock_process = MagicMock()
        mock_process.returncode = 0
        
        # Настраиваем stdout с NDJSON потоком
        async def mock_stdout():
            yield b'{"type": "system", "subtype": "init", "session_id": "session-123", "model": "claude-sonnet-4-20250514", "cwd": "/tmp"}\n'
            yield b'{"type": "assistant", "message": {"content": [{"type": "text", "text": "Test response"}]}}\n'
            yield b'{"type": "result", "duration_ms": 5000}\n'
        
        mock_process.stdout = mock_stdout()
        
        # Настраиваем stderr (пустой)
        async def mock_stderr():
            return
            yield  # Make it a generator
        
        mock_process.stderr = mock_stderr()
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.kill = MagicMock()  # kill() - синхронный метод
        
        with patch("cursor_subagent_mcp.executor.runner.get_logger", return_value=mock_logger), \
             patch("cursor_subagent_mcp.executor.runner.find_cursor_agent", return_value="/usr/bin/cursor-agent"), \
             patch("asyncio.create_subprocess_exec", return_value=mock_process):
            
            result = await invoke_cursor_agent(
                system_prompt="System prompt",
                task="Test task",
                model="claude-sonnet-4-20250514",
                cwd="/tmp",
            )
            
            # Проверяем результат
            assert result.success is True
            assert result.output == "Test response"
            assert result.session_id == "session-123"
            assert result.duration_ms == 5000
            assert result.return_code == 0
            assert len(result.events) == 3

    @pytest.mark.asyncio
    async def test_invoke_cursor_agent_not_found(self, reset_logger_singleton):
        """TC-UNIT-06.2: UC-06.2 - Проверка обработки отсутствия CLI."""
        mock_logger = MagicMock()
        
        with patch("cursor_subagent_mcp.executor.runner.get_logger", return_value=mock_logger), \
             patch("cursor_subagent_mcp.executor.runner.find_cursor_agent", return_value=None):
            
            result = await invoke_cursor_agent(
                system_prompt="System prompt",
                task="Test task",
                model="claude-sonnet-4-20250514",
                cwd="/tmp",
            )
            
            # Проверяем результат
            assert result.success is False
            assert "not found" in result.error.lower()
            assert result.return_code == -1
            assert result.output == ""

    @pytest.mark.asyncio
    async def test_invoke_cursor_agent_timeout(self, reset_logger_singleton):
        """TC-UNIT-06.3: UC-06.3 - Проверка обработки таймаута."""
        mock_logger = MagicMock()
        mock_process = MagicMock()
        mock_process.returncode = None  # Process still running
        
        # Настраиваем stdout с частичным выводом
        async def mock_stdout():
            # Выдаем данные сразу
            yield b'{"type": "assistant", "message": {"content": [{"type": "text", "text": "Partial response"}]}}\n'
            # Затем бесконечный цикл для имитации таймаута
            while True:
                await asyncio.sleep(0.1)
                yield b''
        
        mock_process.stdout = mock_stdout()
        
        async def mock_stderr():
            return
            yield
        
        mock_process.stderr = mock_stderr()
        mock_process.wait = AsyncMock(return_value=-1)
        mock_process.kill = MagicMock()  # kill() - синхронный метод
        
        # Мокируем wait_for так, чтобы он выбрасывал TimeoutError при первом вызове с timeout
        call_count = [0]  # Используем список для изменяемого значения в замыкании
        
        async def mock_wait_for(coro, timeout=None, *args, **kwargs):
            """Мокируем wait_for для выброса TimeoutError при первом вызове с timeout."""
            call_count[0] += 1
            if timeout is not None and timeout < 10.0 and call_count[0] == 1:  # Первый вызов - таймаут для process_stream
                raise asyncio.TimeoutError()
            # Для остальных вызовов используем реальный wait_for или просто await coro
            if timeout is None:
                return await coro
            # Для второго вызова (process.wait) возвращаем результат без таймаута
            return await coro
        
        with patch("cursor_subagent_mcp.executor.runner.get_logger", return_value=mock_logger), \
             patch("cursor_subagent_mcp.executor.runner.find_cursor_agent", return_value="/usr/bin/cursor-agent"), \
             patch("asyncio.create_subprocess_exec", return_value=mock_process), \
             patch("asyncio.wait_for", side_effect=mock_wait_for):
            
            result = await invoke_cursor_agent(
                system_prompt="System prompt",
                task="Test task",
                model="claude-sonnet-4-20250514",
                cwd="/tmp",
                timeout=1.0,
            )
            
            # Проверяем результат
            assert result.success is False
            assert "timeout" in result.error.lower() or "timed out" in result.error.lower()
            assert result.return_code == -1
            # Проверяем, что kill был вызван
            mock_process.kill.assert_called_once()
            # Проверяем, что частичный вывод был обработан (может быть пустым, если таймаут произошел до чтения)
            # Но если вывод есть, он должен содержать Partial response
            if result.output:
                assert "Partial response" in result.output

    @pytest.mark.asyncio
    async def test_invoke_cursor_agent_ndjson_stream(self, reset_logger_singleton):
        """TC-UNIT-06.4: UC-06.4 - Проверка обработки NDJSON потока."""
        mock_logger = MagicMock()
        mock_process = MagicMock()
        mock_process.returncode = 0
        
        # Настраиваем stdout с несколькими событиями
        async def mock_stdout():
            yield b'{"type": "system", "subtype": "init", "session_id": "session-456"}\n'
            yield b'{"type": "assistant", "message": {"content": [{"type": "text", "text": "Message 1"}]}}\n'
            yield b'{"type": "assistant", "message": {"content": [{"type": "text", "text": "Message 2"}]}}\n'
            yield b'{"type": "result", "duration_ms": 3000}\n'
        
        mock_process.stdout = mock_stdout()
        
        async def mock_stderr():
            return
            yield
        
        mock_process.stderr = mock_stderr()
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.kill = MagicMock()  # kill() - синхронный метод
        
        with patch("cursor_subagent_mcp.executor.runner.get_logger", return_value=mock_logger), \
             patch("cursor_subagent_mcp.executor.runner.find_cursor_agent", return_value="/usr/bin/cursor-agent"), \
             patch("asyncio.create_subprocess_exec", return_value=mock_process):
            
            result = await invoke_cursor_agent(
                system_prompt="System prompt",
                task="Test task",
                model="claude-sonnet-4-20250514",
                cwd="/tmp",
            )
            
            # Проверяем результат
            assert result.success is True
            assert result.session_id == "session-456"
            assert result.duration_ms == 3000
            assert "Message 1" in result.output
            assert "Message 2" in result.output
            assert len(result.events) == 4

    @pytest.mark.asyncio
    async def test_invoke_cursor_agent_tool_call_events(self, reset_logger_singleton):
        """TC-UNIT-06.4.1: UC-06.4.1 - Проверка обработки событий tool_call."""
        mock_logger = MagicMock()
        mock_process = MagicMock()
        mock_process.returncode = 0
        
        # Настраиваем stdout с событиями tool_call
        async def mock_stdout():
            yield b'{"type": "tool_call", "subtype": "started", "tool_call": {"readToolCall": {"args": {"path": "/tmp/file.txt"}}}}\n'
            yield b'{"type": "tool_call", "subtype": "completed", "tool_call": {"readToolCall": {"result": {"success": {"totalLines": 10}}}}}\n'
            yield b'{"type": "tool_call", "subtype": "started", "tool_call": {"writeToolCall": {"args": {"path": "/tmp/output.txt"}}}}\n'
            yield b'{"type": "tool_call", "subtype": "completed", "tool_call": {"writeToolCall": {"result": {"success": {"linesCreated": 5}}}}}\n'
            yield b'{"type": "tool_call", "subtype": "started", "tool_call": {"function": {"name": "test_function"}}}\n'
            yield b'{"type": "tool_call", "subtype": "completed", "tool_call": {"function": {"name": "test_function"}}}\n'
            yield b'{"type": "result", "duration_ms": 2000}\n'
        
        mock_process.stdout = mock_stdout()
        
        async def mock_stderr():
            return
            yield
        
        mock_process.stderr = mock_stderr()
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.kill = MagicMock()  # kill() - синхронный метод
        
        with patch("cursor_subagent_mcp.executor.runner.get_logger", return_value=mock_logger), \
             patch("cursor_subagent_mcp.executor.runner.find_cursor_agent", return_value="/usr/bin/cursor-agent"), \
             patch("asyncio.create_subprocess_exec", return_value=mock_process):
            
            result = await invoke_cursor_agent(
                system_prompt="System prompt",
                task="Test task",
                model="claude-sonnet-4-20250514",
                cwd="/tmp",
            )
            
            # Проверяем результат
            assert result.success is True
            assert len(result.events) == 7
            
            # Проверяем, что события tool_call были обработаны
            tool_call_events = [e for e in result.events if e.event_type == "tool_call"]
            assert len(tool_call_events) == 6
            
            # Проверяем логирование
            assert mock_logger.info.called

    @pytest.mark.asyncio
    async def test_invoke_cursor_agent_extract_json(self, reset_logger_singleton):
        """TC-UNIT-06.5: UC-06.5 - Проверка извлечения JSON из ответа."""
        mock_logger = MagicMock()
        mock_process = MagicMock()
        mock_process.returncode = 0
        
        # Настраиваем stdout с ответом, содержащим JSON
        async def mock_stdout():
            yield b'{"type": "assistant", "message": {"content": [{"type": "text", "text": "Response with ```json\\n{\\"status\\": \\"success\\"}\\n```"}]}}\n'
            yield b'{"type": "result", "duration_ms": 1000}\n'
        
        mock_process.stdout = mock_stdout()
        
        async def mock_stderr():
            return
            yield
        
        mock_process.stderr = mock_stderr()
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.kill = MagicMock()  # kill() - синхронный метод
        
        with patch("cursor_subagent_mcp.executor.runner.get_logger", return_value=mock_logger), \
             patch("cursor_subagent_mcp.executor.runner.find_cursor_agent", return_value="/usr/bin/cursor-agent"), \
             patch("asyncio.create_subprocess_exec", return_value=mock_process), \
             patch("cursor_subagent_mcp.executor.runner.extract_final_json", return_value='{"status": "success"}'):
            
            result = await invoke_cursor_agent(
                system_prompt="System prompt",
                task="Test task",
                model="claude-sonnet-4-20250514",
                cwd="/tmp",
            )
            
            # Проверяем результат
            assert result.success is True
            assert result.output == '{"status": "success"}'

    @pytest.mark.asyncio
    async def test_invoke_cursor_agent_premature_close(self, reset_logger_singleton):
        """TC-UNIT-06.6: UC-06.6 - Проверка обработки Premature close с полезным output."""
        mock_logger = MagicMock()
        mock_process = MagicMock()
        mock_process.returncode = 1  # Non-zero return code
        
        # Настраиваем stdout с полезным выводом (>100 символов)
        async def mock_stdout():
            yield b'{"type": "assistant", "message": {"content": [{"type": "text", "text": "This is a very long response that contains useful information and is definitely longer than 100 characters to test the premature close handling logic."}]}}\n'
        
        mock_process.stdout = mock_stdout()
        
        # Настраиваем stderr с "Premature close"
        async def mock_stderr():
            yield b"Premature close error occurred\n"
        
        mock_process.stderr = mock_stderr()
        mock_process.wait = AsyncMock(return_value=1)
        mock_process.kill = MagicMock()  # kill() - синхронный метод
        
        with patch("cursor_subagent_mcp.executor.runner.get_logger", return_value=mock_logger), \
             patch("cursor_subagent_mcp.executor.runner.find_cursor_agent", return_value="/usr/bin/cursor-agent"), \
             patch("asyncio.create_subprocess_exec", return_value=mock_process):
            
            result = await invoke_cursor_agent(
                system_prompt="System prompt",
                task="Test task",
                model="claude-sonnet-4-20250514",
                cwd="/tmp",
            )
            
            # Проверяем результат - должен быть success=True несмотря на код ошибки
            assert result.success is True
            assert len(result.output.strip()) > 100
            # Проверяем, что либо error содержит Premature close, либо error равен None
            if result.error is not None:
                assert "Premature close" in result.error or "premature close" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invoke_cursor_agent_premature_close_no_output(self, reset_logger_singleton):
        """TC-UNIT-06.6-A2: UC-06.6, А2 - Проверка Premature close без полезного output."""
        mock_logger = MagicMock()
        mock_process = MagicMock()
        mock_process.returncode = 1
        
        # Настраиваем stdout с коротким выводом (<100 символов)
        async def mock_stdout():
            yield b'{"type": "assistant", "message": {"content": [{"type": "text", "text": "Short"}]}}\n'
        
        mock_process.stdout = mock_stdout()
        
        async def mock_stderr():
            yield b"Premature close error occurred\n"
        
        mock_process.stderr = mock_stderr()
        mock_process.wait = AsyncMock(return_value=1)
        mock_process.kill = MagicMock()  # kill() - синхронный метод
        
        with patch("cursor_subagent_mcp.executor.runner.get_logger", return_value=mock_logger), \
             patch("cursor_subagent_mcp.executor.runner.find_cursor_agent", return_value="/usr/bin/cursor-agent"), \
             patch("asyncio.create_subprocess_exec", return_value=mock_process):
            
            result = await invoke_cursor_agent(
                system_prompt="System prompt",
                task="Test task",
                model="claude-sonnet-4-20250514",
                cwd="/tmp",
            )
            
            # Проверяем результат - должен быть success=False
            assert result.success is False
            assert result.return_code == 1

    @pytest.mark.asyncio
    async def test_invoke_cursor_agent_prompt_building(self, reset_logger_singleton):
        """TC-UNIT-06.7: UC-06.7 - Проверка построения полного промпта."""
        mock_logger = MagicMock()
        mock_process = MagicMock()
        mock_process.returncode = 0
        
        async def mock_stdout():
            yield b'{"type": "result", "duration_ms": 1000}\n'
        
        mock_process.stdout = mock_stdout()
        
        async def mock_stderr():
            return
            yield
        
        mock_process.stderr = mock_stderr()
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.kill = MagicMock()  # kill() - синхронный метод
        
        captured_cmd = []
        
        async def capture_cmd(*args, **kwargs):
            captured_cmd.extend(args)
            return mock_process
        
        with patch("cursor_subagent_mcp.executor.runner.get_logger", return_value=mock_logger), \
             patch("cursor_subagent_mcp.executor.runner.find_cursor_agent", return_value="/usr/bin/cursor-agent"), \
             patch("asyncio.create_subprocess_exec", side_effect=capture_cmd):
            
            await invoke_cursor_agent(
                system_prompt="System prompt text",
                task="Task text",
                model="claude-sonnet-4-20250514",
                cwd="/tmp",
                context="Context text",
            )
            
            # Проверяем, что команда содержит полный промпт
            assert len(captured_cmd) > 0
            # Находим позиционный аргумент с промптом (последний аргумент)
            prompt_arg = captured_cmd[-1]
            assert "System prompt text" in prompt_arg
            assert "## КОНТЕКСТ" in prompt_arg
            assert "Context text" in prompt_arg
            assert "## ЗАДАЧА" in prompt_arg
            assert "Task text" in prompt_arg
            
            # Проверяем, что команда содержит --workspace с правильным путём (по умолчанию = cwd)
            assert "--workspace" in captured_cmd
            workspace_idx = captured_cmd.index("--workspace")
            assert captured_cmd[workspace_idx + 1] == "/tmp"

    @pytest.mark.asyncio
    async def test_invoke_cursor_agent_invalid_json_line(self, reset_logger_singleton):
        """TC-UNIT-06.4-A1: UC-06.4, А1 - Проверка обработки невалидной JSON строки."""
        mock_logger = MagicMock()
        mock_process = MagicMock()
        mock_process.returncode = 0
        
        # Настраиваем stdout с невалидной JSON строкой среди валидных
        async def mock_stdout():
            yield b'{"type": "assistant", "message": {"content": [{"type": "text", "text": "Message 1"}]}}\n'
            yield b'Invalid JSON line\n'
            yield b'{"type": "assistant", "message": {"content": [{"type": "text", "text": "Message 2"}]}}\n'
            yield b'{"type": "result", "duration_ms": 1000}\n'
        
        mock_process.stdout = mock_stdout()
        
        async def mock_stderr():
            return
            yield
        
        mock_process.stderr = mock_stderr()
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.kill = MagicMock()  # kill() - синхронный метод
        
        with patch("cursor_subagent_mcp.executor.runner.get_logger", return_value=mock_logger), \
             patch("cursor_subagent_mcp.executor.runner.find_cursor_agent", return_value="/usr/bin/cursor-agent"), \
             patch("asyncio.create_subprocess_exec", return_value=mock_process):
            
            result = await invoke_cursor_agent(
                system_prompt="System prompt",
                task="Test task",
                model="claude-sonnet-4-20250514",
                cwd="/tmp",
            )
            
            # Проверяем результат - ошибка должна быть обработана
            assert result.success is True
            assert "Message 1" in result.output
            assert "Message 2" in result.output
            # Проверяем, что невалидная строка не добавила событие
            assert len(result.events) == 3  # 2 assistant + 1 result

    @pytest.mark.asyncio
    async def test_invoke_cursor_agent_stderr_error(self, reset_logger_singleton):
        """TC-UNIT-06.1-A3: UC-06.1, А3 - Проверка обработки ошибки чтения stderr."""
        mock_logger = MagicMock()
        mock_process = MagicMock()
        mock_process.returncode = 0
        
        # Настраиваем stdout с успешным выводом
        async def mock_stdout():
            yield b'{"type": "assistant", "message": {"content": [{"type": "text", "text": "Success"}]}}\n'
            yield b'{"type": "result", "duration_ms": 1000}\n'
        
        mock_process.stdout = mock_stdout()
        
        # Настраиваем stderr для выброса исключения
        async def mock_stderr():
            raise RuntimeError("Stderr stream closed")
            yield
        
        mock_process.stderr = mock_stderr()
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.kill = MagicMock()  # kill() - синхронный метод
        
        with patch("cursor_subagent_mcp.executor.runner.get_logger", return_value=mock_logger), \
             patch("cursor_subagent_mcp.executor.runner.find_cursor_agent", return_value="/usr/bin/cursor-agent"), \
             patch("asyncio.create_subprocess_exec", return_value=mock_process):
            
            result = await invoke_cursor_agent(
                system_prompt="System prompt",
                task="Test task",
                model="claude-sonnet-4-20250514",
                cwd="/tmp",
            )
            
            # Проверяем результат - ошибка чтения stderr не должна прервать выполнение
            assert result.success is True
            assert "Success" in result.output
            # Проверяем, что ошибка была залогирована
            assert mock_logger.debug.called

    @pytest.mark.asyncio
    async def test_invoke_cursor_agent_empty_context(self, reset_logger_singleton):
        """TC-UNIT-06.7-A3: UC-06.7, А3 - Проверка построения промпта с пустым context."""
        mock_logger = MagicMock()
        mock_process = MagicMock()
        mock_process.returncode = 0
        
        async def mock_stdout():
            yield b'{"type": "result", "duration_ms": 1000}\n'
        
        mock_process.stdout = mock_stdout()
        
        async def mock_stderr():
            return
            yield
        
        mock_process.stderr = mock_stderr()
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.kill = MagicMock()  # kill() - синхронный метод
        
        captured_cmd = []
        
        async def capture_cmd(*args, **kwargs):
            captured_cmd.extend(args)
            return mock_process
        
        with patch("cursor_subagent_mcp.executor.runner.get_logger", return_value=mock_logger), \
             patch("cursor_subagent_mcp.executor.runner.find_cursor_agent", return_value="/usr/bin/cursor-agent"), \
             patch("asyncio.create_subprocess_exec", side_effect=capture_cmd):
            
            await invoke_cursor_agent(
                system_prompt="System prompt text",
                task="Task text",
                model="claude-sonnet-4-20250514",
                cwd="/tmp",
                context="",  # Пустой context
            )
            
            # Проверяем, что промпт не содержит секцию КОНТЕКСТ
            prompt_arg = captured_cmd[-1]
            assert "System prompt text" in prompt_arg
            assert "## КОНТЕКСТ" not in prompt_arg
            assert "## ЗАДАЧА" in prompt_arg
            assert "Task text" in prompt_arg
            
            # Проверяем, что команда содержит --workspace с правильным путём (по умолчанию = cwd)
            assert "--workspace" in captured_cmd
            workspace_idx = captured_cmd.index("--workspace")
            assert captured_cmd[workspace_idx + 1] == "/tmp"

    @pytest.mark.asyncio
    async def test_invoke_cursor_agent_custom_workspace(self, reset_logger_singleton):
        """TC-UNIT-06.8: UC-06.8 - Проверка использования отдельного workspace."""
        mock_logger = MagicMock()
        mock_process = MagicMock()
        mock_process.returncode = 0
        
        async def mock_stdout():
            yield b'{"type": "result", "duration_ms": 1000}\n'
        
        mock_process.stdout = mock_stdout()
        
        async def mock_stderr():
            return
            yield
        
        mock_process.stderr = mock_stderr()
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.kill = MagicMock()
        
        captured_cmd = []
        captured_kwargs = {}
        
        async def capture_cmd(*args, **kwargs):
            captured_cmd.extend(args)
            captured_kwargs.update(kwargs)
            return mock_process
        
        with patch("cursor_subagent_mcp.executor.runner.get_logger", return_value=mock_logger), \
             patch("cursor_subagent_mcp.executor.runner.find_cursor_agent", return_value="/usr/bin/cursor-agent"), \
             patch("asyncio.create_subprocess_exec", side_effect=capture_cmd):
            
            await invoke_cursor_agent(
                system_prompt="System prompt text",
                task="Task text",
                model="claude-sonnet-4-20250514",
                cwd="/my/project",  # Рабочая директория процесса
                workspace="/other/project",  # Workspace для доступа к файлам
            )
            
            # Проверяем, что cwd передан процессу
            assert captured_kwargs.get("cwd") == "/my/project"
            
            # Проверяем, что --workspace указывает на другой проект
            assert "--workspace" in captured_cmd
            workspace_idx = captured_cmd.index("--workspace")
            assert captured_cmd[workspace_idx + 1] == "/other/project"

    @pytest.mark.asyncio
    async def test_invoke_cursor_agent_invalid_encoding(self, reset_logger_singleton):
        """TC-UNIT-06.4-A4: UC-06.4, А4 - Проверка обработки невалидной UTF-8 последовательности."""
        mock_logger = MagicMock()
        mock_process = MagicMock()
        mock_process.returncode = 0
        
        # Настраиваем stdout с невалидной UTF-8 последовательностью
        async def mock_stdout():
            yield b'{"type": "assistant", "message": {"content": [{"type": "text", "text": "Valid message"}]}}\n'
            yield b'\xff\xfe\x00\x00'  # Невалидная UTF-8 последовательность
            yield b'{"type": "assistant", "message": {"content": [{"type": "text", "text": "Another message"}]}}\n'
            yield b'{"type": "result", "duration_ms": 1000}\n'
        
        mock_process.stdout = mock_stdout()
        
        async def mock_stderr():
            return
            yield
        
        mock_process.stderr = mock_stderr()
        mock_process.wait = AsyncMock(return_value=0)
        mock_process.kill = MagicMock()  # kill() - синхронный метод
        
        with patch("cursor_subagent_mcp.executor.runner.get_logger", return_value=mock_logger), \
             patch("cursor_subagent_mcp.executor.runner.find_cursor_agent", return_value="/usr/bin/cursor-agent"), \
             patch("asyncio.create_subprocess_exec", return_value=mock_process):
            
            result = await invoke_cursor_agent(
                system_prompt="System prompt",
                task="Test task",
                model="claude-sonnet-4-20250514",
                cwd="/tmp",
            )
            
            # Проверяем результат - ошибка декодирования должна быть обработана
            assert result.success is True
            assert "Valid message" in result.output
            assert "Another message" in result.output
            # Проверяем, что выполнение продолжилось без падения
            assert len(result.events) == 3  # 2 assistant + 1 result

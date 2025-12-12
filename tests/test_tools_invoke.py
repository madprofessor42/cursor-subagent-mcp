"""Tests for tools.invoke module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cursor_subagent_mcp.config import AgentConfig, Config
from cursor_subagent_mcp.executor.models import ExecutionResult
from cursor_subagent_mcp.tools.invoke import invoke_subagent


class TestInvokeSubagent:
    """Tests for invoke_subagent() function."""

    @pytest.mark.asyncio
    async def test_invoke_subagent_success(self, reset_config_singleton):
        """TC-UNIT-02.1: UC-02.1 - Проверка успешного вызова агента."""
        # Мокируем все зависимости
        mock_config = Config()
        mock_config.agents = {
            "analyst": AgentConfig(
                name="Аналитик",
                description="Создаёт техническое задание",
                prompt_file="agents-master/02_analyst_prompt.md",
                default_model="claude-sonnet-4-20250514",
            ),
        }
        
        mock_system_prompt = "# System Prompt\n\nThis is the system prompt."
        
        mock_execution_result = ExecutionResult(
            success=True,
            output='{"status": "success", "result": "Task completed"}',
            error=None,
            session_id="session-123",
            duration_ms=5000,
        )
        
        mock_invoke_cursor_agent = AsyncMock(return_value=mock_execution_result)
        
        mock_load_prompt_file = MagicMock(return_value=mock_system_prompt)
        
        with patch("cursor_subagent_mcp.tools.invoke.check_cursor_agent_available", return_value=(True, "cursor-agent found")), \
             patch("cursor_subagent_mcp.tools.invoke.get_config", return_value=mock_config), \
             patch("cursor_subagent_mcp.tools.invoke.load_prompt_file", mock_load_prompt_file), \
             patch("cursor_subagent_mcp.tools.invoke.invoke_cursor_agent", mock_invoke_cursor_agent):
            
            result = await invoke_subagent(
                agent_role="analyst",
                task="Create technical specification",
                cwd="/tmp/test_project",
            )
            
            # Проверяем результат
            assert result["success"] is True
            assert result["output"] == '{"status": "success", "result": "Task completed"}'
            assert result["error"] is None
            assert result["agent_role"] == "analyst"
            assert result["model_used"] == "claude-sonnet-4-20250514"
            assert result["session_id"] == "session-123"
            assert result["duration_ms"] == 5000
            
            # Проверяем, что системный промпт был загружен для правильного агента
            mock_load_prompt_file.assert_called_once_with(mock_config, "agents-master/02_analyst_prompt.md")
            
            # Проверяем, что invoke_cursor_agent был вызван с правильными параметрами
            mock_invoke_cursor_agent.assert_called_once_with(
                system_prompt=mock_system_prompt,
                task="Create technical specification",
                model="claude-sonnet-4-20250514",
                cwd="/tmp/test_project",
                context="",
                timeout=None,
                agent_role="analyst",
            )

    @pytest.mark.asyncio
    async def test_invoke_subagent_cli_unavailable(self, reset_config_singleton):
        """TC-UNIT-02.2: UC-02.2 - Проверка обработки недоступности CLI."""
        with patch("cursor_subagent_mcp.tools.invoke.check_cursor_agent_available", return_value=(False, "cursor-agent CLI not found in PATH")), \
             patch("cursor_subagent_mcp.tools.invoke.invoke_cursor_agent") as mock_invoke:
            
            result = await invoke_subagent(
                agent_role="analyst",
                task="Create technical specification",
                cwd="/tmp/test_project",
            )
            
            # Проверяем результат
            assert result["success"] is False
            assert result["output"] == ""
            assert "not found" in result["error"]
            assert result["agent_role"] == "analyst"
            assert result["model_used"] is None
            assert result["session_id"] is None
            assert result["duration_ms"] is None
            
            # Проверяем, что invoke_cursor_agent не был вызван
            mock_invoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_invoke_subagent_unknown_role(self, reset_config_singleton):
        """TC-UNIT-02.3: UC-02.3 - Проверка обработки неизвестной роли агента."""
        mock_config = Config()
        mock_config.agents = {
            "analyst": AgentConfig(
                name="Аналитик",
                description="Создаёт техническое задание",
                prompt_file="agents-master/02_analyst_prompt.md",
            ),
            "developer": AgentConfig(
                name="Разработчик",
                description="Реализует задачи",
                prompt_file="agents-master/08_agent_developer.md",
            ),
        }
        
        with patch("cursor_subagent_mcp.tools.invoke.check_cursor_agent_available", return_value=(True, "cursor-agent found")), \
             patch("cursor_subagent_mcp.tools.invoke.get_config", return_value=mock_config), \
             patch("cursor_subagent_mcp.tools.invoke.invoke_cursor_agent") as mock_invoke:
            
            result = await invoke_subagent(
                agent_role="unknown_agent",
                task="Some task",
                cwd="/tmp/test_project",
            )
            
            # Проверяем результат
            assert result["success"] is False
            assert result["output"] == ""
            assert "Unknown agent role" in result["error"]
            assert "unknown_agent" in result["error"]
            assert "analyst" in result["error"] or "developer" in result["error"]
            assert result["agent_role"] == "unknown_agent"
            assert result["model_used"] is None
            assert result["session_id"] is None
            assert result["duration_ms"] is None
            
            # Проверяем, что invoke_cursor_agent не был вызван
            mock_invoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_invoke_subagent_prompt_not_found(self, reset_config_singleton):
        """TC-UNIT-02.4: UC-02.4 - Проверка обработки отсутствующего файла промпта."""
        mock_config = Config()
        mock_config.agents = {
            "analyst": AgentConfig(
                name="Аналитик",
                description="Создаёт техническое задание",
                prompt_file="agents-master/02_analyst_prompt.md",
                default_model="claude-sonnet-4-20250514",
            ),
        }
        
        with patch("cursor_subagent_mcp.tools.invoke.check_cursor_agent_available", return_value=(True, "cursor-agent found")), \
             patch("cursor_subagent_mcp.tools.invoke.get_config", return_value=mock_config), \
             patch("cursor_subagent_mcp.tools.invoke.load_prompt_file", side_effect=FileNotFoundError("Prompt file not found: agents-master/02_analyst_prompt.md")), \
             patch("cursor_subagent_mcp.tools.invoke.invoke_cursor_agent") as mock_invoke:
            
            result = await invoke_subagent(
                agent_role="analyst",
                task="Create technical specification",
                cwd="/tmp/test_project",
            )
            
            # Проверяем результат
            assert result["success"] is False
            assert result["output"] == ""
            assert "Prompt file not found" in result["error"]
            assert result["agent_role"] == "analyst"
            assert result["model_used"] == "claude-sonnet-4-20250514"
            assert result["session_id"] is None
            assert result["duration_ms"] is None
            
            # Проверяем, что invoke_cursor_agent не был вызван
            mock_invoke.assert_not_called()

    @pytest.mark.asyncio
    async def test_invoke_subagent_model_override(self, reset_config_singleton):
        """TC-UNIT-02.5: UC-02.5 - Проверка переопределения модели."""
        mock_config = Config()
        mock_config.agents = {
            "analyst": AgentConfig(
                name="Аналитик",
                description="Создаёт техническое задание",
                prompt_file="agents-master/02_analyst_prompt.md",
                default_model="claude-sonnet-4-20250514",
            ),
        }
        
        mock_system_prompt = "# System Prompt\n\nThis is the system prompt."
        
        mock_execution_result = ExecutionResult(
            success=True,
            output='{"status": "success"}',
            error=None,
            session_id="session-456",
            duration_ms=3000,
        )
        
        mock_invoke_cursor_agent = AsyncMock(return_value=mock_execution_result)
        
        with patch("cursor_subagent_mcp.tools.invoke.check_cursor_agent_available", return_value=(True, "cursor-agent found")), \
             patch("cursor_subagent_mcp.tools.invoke.get_config", return_value=mock_config), \
             patch("cursor_subagent_mcp.tools.invoke.load_prompt_file", return_value=mock_system_prompt), \
             patch("cursor_subagent_mcp.tools.invoke.invoke_cursor_agent", mock_invoke_cursor_agent):
            
            result = await invoke_subagent(
                agent_role="analyst",
                task="Create technical specification",
                cwd="/tmp/test_project",
                model="custom-model",
            )
            
            # Проверяем результат
            assert result["success"] is True
            assert result["model_used"] == "custom-model"
            
            # Проверяем, что invoke_cursor_agent был вызван с переопределённой моделью
            mock_invoke_cursor_agent.assert_called_once()
            call_args = mock_invoke_cursor_agent.call_args
            assert call_args.kwargs["model"] == "custom-model"

    @pytest.mark.asyncio
    async def test_invoke_subagent_default_model(self, reset_config_singleton):
        """TC-UNIT-02.6: UC-02.6 - Проверка использования модели по умолчанию."""
        mock_config = Config()
        mock_config.agents = {
            "analyst": AgentConfig(
                name="Аналитик",
                description="Создаёт техническое задание",
                prompt_file="agents-master/02_analyst_prompt.md",
                default_model="claude-sonnet-4-20250514",
            ),
        }
        
        mock_system_prompt = "# System Prompt\n\nThis is the system prompt."
        
        mock_execution_result = ExecutionResult(
            success=True,
            output='{"status": "success"}',
            error=None,
            session_id="session-789",
            duration_ms=4000,
        )
        
        mock_invoke_cursor_agent = AsyncMock(return_value=mock_execution_result)
        
        with patch("cursor_subagent_mcp.tools.invoke.check_cursor_agent_available", return_value=(True, "cursor-agent found")), \
             patch("cursor_subagent_mcp.tools.invoke.get_config", return_value=mock_config), \
             patch("cursor_subagent_mcp.tools.invoke.load_prompt_file", return_value=mock_system_prompt), \
             patch("cursor_subagent_mcp.tools.invoke.invoke_cursor_agent", mock_invoke_cursor_agent):
            
            result = await invoke_subagent(
                agent_role="analyst",
                task="Create technical specification",
                cwd="/tmp/test_project",
            )
            
            # Проверяем результат
            assert result["success"] is True
            assert result["model_used"] == "claude-sonnet-4-20250514"
            
            # Проверяем, что invoke_cursor_agent был вызван с моделью по умолчанию
            mock_invoke_cursor_agent.assert_called_once()
            call_args = mock_invoke_cursor_agent.call_args
            assert call_args.kwargs["model"] == "claude-sonnet-4-20250514"

    @pytest.mark.asyncio
    async def test_invoke_subagent_execution_error(self, reset_config_singleton):
        """TC-UNIT-02.7: UC-02.1, А1 - Проверка обработки ошибки выполнения."""
        mock_config = Config()
        mock_config.agents = {
            "analyst": AgentConfig(
                name="Аналитик",
                description="Создаёт техническое задание",
                prompt_file="agents-master/02_analyst_prompt.md",
                default_model="claude-sonnet-4-20250514",
            ),
        }
        
        mock_system_prompt = "# System Prompt\n\nThis is the system prompt."
        
        mock_execution_result = ExecutionResult(
            success=False,
            output="",
            error="Execution failed: timeout",
            session_id=None,
            duration_ms=None,
        )
        
        mock_invoke_cursor_agent = AsyncMock(return_value=mock_execution_result)
        
        with patch("cursor_subagent_mcp.tools.invoke.check_cursor_agent_available", return_value=(True, "cursor-agent found")), \
             patch("cursor_subagent_mcp.tools.invoke.get_config", return_value=mock_config), \
             patch("cursor_subagent_mcp.tools.invoke.load_prompt_file", return_value=mock_system_prompt), \
             patch("cursor_subagent_mcp.tools.invoke.invoke_cursor_agent", mock_invoke_cursor_agent):
            
            result = await invoke_subagent(
                agent_role="analyst",
                task="Create technical specification",
                cwd="/tmp/test_project",
            )
            
            # Проверяем результат
            assert result["success"] is False
            assert result["output"] == ""
            assert result["error"] == "Execution failed: timeout"
            assert result["agent_role"] == "analyst"
            assert result["model_used"] == "claude-sonnet-4-20250514"
            assert result["session_id"] is None
            assert result["duration_ms"] is None

    @pytest.mark.asyncio
    async def test_invoke_subagent_with_context_and_timeout(self, reset_config_singleton):
        """TC-UNIT-02.8: UC-02.1, А2 - Проверка передачи context и timeout."""
        mock_config = Config()
        mock_config.agents = {
            "analyst": AgentConfig(
                name="Аналитик",
                description="Создаёт техническое задание",
                prompt_file="agents-master/02_analyst_prompt.md",
                default_model="claude-sonnet-4-20250514",
            ),
        }
        
        mock_system_prompt = "# System Prompt\n\nThis is the system prompt."
        
        mock_execution_result = ExecutionResult(
            success=True,
            output='{"status": "success"}',
            error=None,
            session_id="session-context",
            duration_ms=2000,
        )
        
        mock_invoke_cursor_agent = AsyncMock(return_value=mock_execution_result)
        
        with patch("cursor_subagent_mcp.tools.invoke.check_cursor_agent_available", return_value=(True, "cursor-agent found")), \
             patch("cursor_subagent_mcp.tools.invoke.get_config", return_value=mock_config), \
             patch("cursor_subagent_mcp.tools.invoke.load_prompt_file", return_value=mock_system_prompt), \
             patch("cursor_subagent_mcp.tools.invoke.invoke_cursor_agent", mock_invoke_cursor_agent):
            
            result = await invoke_subagent(
                agent_role="analyst",
                task="Create technical specification",
                cwd="/tmp/test_project",
                context="Additional context information",
                timeout=60.0,
            )
            
            # Проверяем результат
            assert result["success"] is True
            assert result["agent_role"] == "analyst"
            
            # Проверяем, что invoke_cursor_agent был вызван с правильными context и timeout
            mock_invoke_cursor_agent.assert_called_once()
            call_args = mock_invoke_cursor_agent.call_args
            assert call_args.kwargs["context"] == "Additional context information"
            assert call_args.kwargs["timeout"] == 60.0

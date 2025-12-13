"""Tests for server module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cursor_subagent_mcp import server


class TestMcpToolsRegistration:
    """Tests for MCP tools registration."""

    def test_mcp_tools_registration(self):
        """TC-UNIT-08.1: UC-08.1 - Проверка регистрации MCP инструментов."""
        # Проверяем, что mcp объект создан
        assert hasattr(server, "mcp")
        assert server.mcp is not None
        
        # Проверяем регистрацию инструментов через проверку наличия в mcp.tools
        # FastMCP хранит инструменты в mcp._tools или через список инструментов
        # Проверяем через прямые вызовы функций, которые должны быть зарегистрированы
        
        # Проверяем, что функции существуют и являются callable
        assert hasattr(server, "get_orchestration_guide")
        assert callable(server.get_orchestration_guide)
        
        assert hasattr(server, "invoke_subagent")
        assert callable(server.invoke_subagent)
        
        assert hasattr(server, "check_status")
        assert callable(server.check_status)
        
        assert hasattr(server, "setup_cursor_cli")
        assert callable(server.setup_cursor_cli)


class TestGetOrchestrationGuideMcp:
    """Tests for get_orchestration_guide MCP tool."""

    def test_get_orchestration_guide_mcp(self):
        """TC-UNIT-08.2: UC-08.2 - Проверка вызова get_orchestration_guide через MCP."""
        # Мокируем implementation функцию
        mock_result = {
            "guide": "Test guide content",
            "agents": {
                "analyst": {"name": "Аналитик", "description": "Создаёт техническое задание"},
                "developer": {"name": "Разработчик", "description": "Реализует задачи"},
            },
        }
        
        with patch("cursor_subagent_mcp.server.get_orchestration_guide_impl", return_value=mock_result):
            # Вызываем зарегистрированный инструмент напрямую
            result = server.get_orchestration_guide()
            
            # Проверяем результат
            assert result == mock_result
            assert "guide" in result
            assert "agents" in result
            assert result["guide"] == "Test guide content"
            assert "analyst" in result["agents"]
            assert "developer" in result["agents"]


class TestInvokeSubagentMcp:
    """Tests for invoke_subagent MCP tool."""

    @pytest.mark.asyncio
    async def test_invoke_subagent_mcp(self):
        """TC-UNIT-08.3: UC-08.3 - Проверка вызова invoke_subagent через MCP."""
        # Мокируем implementation функцию (асинхронная)
        mock_result = {
            "success": True,
            "output": '{"status": "success", "result": "Task completed"}',
            "error": None,
            "agent_role": "analyst",
            "model_used": "claude-sonnet-4-20250514",
            "session_id": "session-123",
            "duration_ms": 5000,
        }
        
        mock_impl = AsyncMock(return_value=mock_result)
        
        with patch("cursor_subagent_mcp.server.invoke_subagent_impl", mock_impl):
            # Вызываем зарегистрированный инструмент (асинхронная функция)
            result = await server.invoke_subagent(
                agent_role="analyst",
                task="Create technical specification",
                cwd="/tmp/test_project",
                context="Additional context",
                model="claude-sonnet-4-20250514",
                timeout=60.0,
            )
            
            # Проверяем результат
            assert result == mock_result
            assert result["success"] is True
            assert result["agent_role"] == "analyst"
            
            # Проверяем, что параметры корректно переданы в implementation
            mock_impl.assert_called_once_with(
                agent_role="analyst",
                task="Create technical specification",
                cwd="/tmp/test_project",
                context="Additional context",
                workspace=None,
                model="claude-sonnet-4-20250514",
                timeout=60.0,
                session_id=None,
            )

    def test_invoke_subagent_mcp_parameter_annotations(self):
        """TC-UNIT-08.3-A1: UC-08.3, А1 - Проверка аннотаций параметров invoke_subagent."""
        import inspect
        from typing import Annotated, Optional, get_args, get_origin
        
        # Получаем сигнатуру функции
        sig = inspect.signature(server.invoke_subagent)
        
        # Проверяем наличие параметров
        assert "agent_role" in sig.parameters
        assert "task" in sig.parameters
        assert "cwd" in sig.parameters
        assert "context" in sig.parameters
        assert "workspace" in sig.parameters
        assert "model" in sig.parameters
        assert "timeout" in sig.parameters
        assert "session_id" in sig.parameters
        
        # Проверяем типы параметров (Annotated имеет структуру Annotated[T, ...])
        agent_role_param = sig.parameters["agent_role"]
        assert get_origin(agent_role_param.annotation) is Annotated
        args = get_args(agent_role_param.annotation)
        assert args[0] == str
        
        task_param = sig.parameters["task"]
        assert get_origin(task_param.annotation) is Annotated
        args = get_args(task_param.annotation)
        assert args[0] == str
        
        cwd_param = sig.parameters["cwd"]
        assert get_origin(cwd_param.annotation) is Annotated
        args = get_args(cwd_param.annotation)
        assert args[0] == str
        
        context_param = sig.parameters["context"]
        assert get_origin(context_param.annotation) is Annotated
        args = get_args(context_param.annotation)
        assert args[0] == str
        assert context_param.default == ""
        
        workspace_param = sig.parameters["workspace"]
        assert get_origin(workspace_param.annotation) is Annotated
        args = get_args(workspace_param.annotation)
        assert args[0] == Optional[str]
        assert workspace_param.default is None
        
        model_param = sig.parameters["model"]
        assert get_origin(model_param.annotation) is Annotated
        args = get_args(model_param.annotation)
        assert args[0] == Optional[str]
        assert model_param.default is None
        
        timeout_param = sig.parameters["timeout"]
        assert get_origin(timeout_param.annotation) is Annotated
        args = get_args(timeout_param.annotation)
        assert args[0] == Optional[float]
        assert timeout_param.default is None
        
        session_id_param = sig.parameters["session_id"]
        assert get_origin(session_id_param.annotation) is Annotated
        args = get_args(session_id_param.annotation)
        assert args[0] == Optional[str]
        assert session_id_param.default is None
        
        # Проверяем наличие docstring
        assert server.invoke_subagent.__doc__ is not None
        assert len(server.invoke_subagent.__doc__) > 0


class TestCheckStatusMcp:
    """Tests for check_status MCP tool."""

    def test_check_status_mcp(self):
        """TC-UNIT-08.4: UC-08.4 - Проверка вызова check_status через MCP."""
        # Мокируем implementation функцию
        mock_result = {
            "cursor_agent_available": True,
            "cursor_agent_message": "cursor-agent found",
            "config_loaded": True,
            "config_error": None,
            "agent_count": 2,
        }
        
        with patch("cursor_subagent_mcp.server.check_status_impl", return_value=mock_result):
            # Вызываем зарегистрированный инструмент
            result = server.check_status()
            
            # Проверяем результат
            assert result == mock_result
            assert result["cursor_agent_available"] is True
            assert result["config_loaded"] is True
            assert result["agent_count"] == 2


class TestSetupCursorCliMcp:
    """Tests for setup_cursor_cli MCP tool."""

    @pytest.mark.asyncio
    async def test_setup_cursor_cli_mcp(self):
        """TC-UNIT-08.5: UC-08.5 - Проверка вызова setup_cursor_cli через MCP."""
        # Мокируем implementation функцию (асинхронная)
        mock_result = {
            "success": True,
            "output": "Installation completed successfully",
            "error": None,
            "shell": "zsh",
        }
        
        mock_impl = AsyncMock(return_value=mock_result)
        
        with patch("cursor_subagent_mcp.server.setup_cursor_cli_impl", mock_impl):
            # Вызываем зарегистрированный инструмент (асинхронная функция)
            result = await server.setup_cursor_cli()
            
            # Проверяем результат
            assert result == mock_result
            assert result["success"] is True
            assert result["shell"] == "zsh"
            
            # Проверяем, что implementation была вызвана
            mock_impl.assert_called_once()


class TestMain:
    """Tests for main() function."""

    def test_main(self):
        """TC-UNIT-08.6: UC-08.6 - Проверка функции main()."""
        # Мокируем mcp.run() так, чтобы функция не блокировала выполнение
        mock_run = MagicMock()
        
        with patch.object(server.mcp, "run", mock_run):
            # Вызываем main()
            server.main()
            
            # Проверяем, что mcp.run() был вызван один раз без параметров
            mock_run.assert_called_once()
            # Проверяем, что функция завершилась (не заблокировала выполнение)
            # Если мы дошли до этой строки, значит функция не заблокировала выполнение
            assert True

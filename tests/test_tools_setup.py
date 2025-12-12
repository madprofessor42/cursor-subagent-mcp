"""Tests for tools.setup module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from cursor_subagent_mcp.executor.models import ExecutionResult
from cursor_subagent_mcp.tools.setup import setup_cursor_cli


class TestSetupCursorCli:
    """Tests for setup_cursor_cli() function."""

    @pytest.mark.asyncio
    async def test_setup_cursor_cli_success(self):
        """UC-05.1: Проверка успешной установки cursor-agent CLI."""
        mock_result = ExecutionResult(
            success=True,
            output="Installation completed successfully",
            error=None,
            return_code=0,
        )
        
        with patch("cursor_subagent_mcp.tools.setup.detect_shell", return_value="zsh"), \
             patch("cursor_subagent_mcp.tools.setup.install_cursor_cli", new_callable=AsyncMock, return_value=mock_result):
            
            result = await setup_cursor_cli()
            
            assert result["success"] is True
            assert "output" in result
            assert result["shell"] == "zsh"
            assert result["error"] is None

    @pytest.mark.asyncio
    async def test_setup_cursor_cli_installation_error(self):
        """UC-05.2: Проверка обработки ошибки установки."""
        mock_result = ExecutionResult(
            success=False,
            output="Installation failed",
            error="Network error",
            return_code=1,
        )
        
        with patch("cursor_subagent_mcp.tools.setup.detect_shell", return_value="bash"), \
             patch("cursor_subagent_mcp.tools.setup.install_cursor_cli", new_callable=AsyncMock, return_value=mock_result):
            
            result = await setup_cursor_cli()
            
            assert result["success"] is False
            assert "error" in result
            assert result["shell"] == "bash"

    @pytest.mark.asyncio
    async def test_setup_cursor_cli_different_shells_zsh(self):
        """UC-05.1, А1: Проверка работы с shell=zsh."""
        mock_result = ExecutionResult(
            success=True,
            output="Installation completed",
            error=None,
            return_code=0,
        )
        
        with patch("cursor_subagent_mcp.tools.setup.detect_shell", return_value="zsh"), \
             patch("cursor_subagent_mcp.tools.setup.install_cursor_cli", new_callable=AsyncMock, return_value=mock_result):
            
            result = await setup_cursor_cli()
            
            assert result["shell"] == "zsh"
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_setup_cursor_cli_different_shells_bash(self):
        """UC-05.1, А1: Проверка работы с shell=bash."""
        mock_result = ExecutionResult(
            success=True,
            output="Installation completed",
            error=None,
            return_code=0,
        )
        
        with patch("cursor_subagent_mcp.tools.setup.detect_shell", return_value="bash"), \
             patch("cursor_subagent_mcp.tools.setup.install_cursor_cli", new_callable=AsyncMock, return_value=mock_result):
            
            result = await setup_cursor_cli()
            
            assert result["shell"] == "bash"
            assert result["success"] is True

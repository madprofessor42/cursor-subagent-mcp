"""Tests for tools.status module."""

from unittest.mock import MagicMock, patch

import pytest
from cursor_subagent_mcp.tools.status import check_status


class TestCheckStatus:
    """Tests for check_status() function."""

    def test_check_status_all_available(self, reset_config_singleton):
        """UC-04.1: Проверка статуса когда все компоненты доступны."""
        mock_config = MagicMock()
        mock_config.agents = {
            "analyst": MagicMock(),
            "architect": MagicMock(),
            "developer": MagicMock(),
            "executor": MagicMock(),
            "planner": MagicMock(),
            "tz_reviewer": MagicMock(),
            "architecture_reviewer": MagicMock(),
            "plan_reviewer": MagicMock(),
            "code_reviewer": MagicMock(),
        }
        
        with patch("cursor_subagent_mcp.tools.status.check_cursor_agent_available", return_value=(True, "cursor-agent found at: /usr/bin/cursor-agent")), \
             patch("cursor_subagent_mcp.tools.status.get_config", return_value=mock_config):
            
            result = check_status()
            
            assert result["cursor_agent_available"] is True
            assert "cursor-agent found" in result["cursor_agent_message"]
            assert result["config_loaded"] is True
            assert result["config_error"] is None
            assert result["agent_count"] == 9

    def test_check_status_cli_unavailable(self, reset_config_singleton):
        """UC-04.2: Проверка статуса когда cursor-agent недоступен."""
        mock_config = MagicMock()
        mock_config.agents = {
            "analyst": MagicMock(),
            "developer": MagicMock(),
        }
        
        with patch("cursor_subagent_mcp.tools.status.check_cursor_agent_available", return_value=(False, "cursor-agent CLI not found in PATH")), \
             patch("cursor_subagent_mcp.tools.status.get_config", return_value=mock_config):
            
            result = check_status()
            
            assert result["cursor_agent_available"] is False
            assert "not found" in result["cursor_agent_message"]
            assert result["config_loaded"] is True
            assert result["agent_count"] == 2

    def test_check_status_config_error_file_not_found(self, reset_config_singleton):
        """UC-04.3: Проверка обработки ошибки FileNotFoundError при загрузке конфигурации."""
        with patch("cursor_subagent_mcp.tools.status.check_cursor_agent_available", return_value=(True, "cursor-agent found")), \
             patch("cursor_subagent_mcp.tools.status.get_config", side_effect=FileNotFoundError("Config file not found")):
            
            result = check_status()
            
            assert result["config_loaded"] is False
            assert result["config_error"] is not None
            assert "Config file not found" in result["config_error"]
            assert result["agent_count"] == 0
            assert result["cursor_agent_available"] is True

    def test_check_status_config_error_general(self, reset_config_singleton):
        """UC-04.4: Проверка обработки общей ошибки при загрузке конфигурации."""
        with patch("cursor_subagent_mcp.tools.status.check_cursor_agent_available", return_value=(True, "cursor-agent found")), \
             patch("cursor_subagent_mcp.tools.status.get_config", side_effect=ValueError("Invalid YAML")):
            
            result = check_status()
            
            assert result["config_loaded"] is False
            assert result["config_error"] is not None
            assert "Invalid YAML" in result["config_error"]

    def test_check_status_zero_agents(self, reset_config_singleton):
        """UC-04.1, А1: Проверка статуса с нулевым количеством агентов."""
        mock_config = MagicMock()
        mock_config.agents = {}
        
        with patch("cursor_subagent_mcp.tools.status.check_cursor_agent_available", return_value=(True, "cursor-agent found")), \
             patch("cursor_subagent_mcp.tools.status.get_config", return_value=mock_config):
            
            result = check_status()
            
            assert result["agent_count"] == 0
            assert result["config_loaded"] is True
            assert result["cursor_agent_available"] is True

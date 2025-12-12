"""Tests for executor CLI functions."""

import os
from unittest.mock import patch

import pytest
from cursor_subagent_mcp.executor.cli import check_cursor_agent_available, find_cursor_agent


class TestFindCursorAgent:
    """Tests for find_cursor_agent() function."""

    def test_find_cursor_agent_in_path(self):
        """TC-UNIT-01: Проверка работы find_cursor_agent() когда cursor-agent в PATH."""
        with patch("shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/cursor-agent"
            
            result = find_cursor_agent()
            
            assert result == "/usr/bin/cursor-agent"
            mock_which.assert_called_once_with("cursor-agent")

    def test_find_cursor_agent_in_local_bin(self):
        """TC-UNIT-02: Проверка работы find_cursor_agent() когда cursor-agent в ~/.local/bin."""
        with patch("shutil.which") as mock_which, \
             patch("os.path.isfile") as mock_isfile, \
             patch("os.access") as mock_access:
            
            mock_which.return_value = None
            mock_isfile.side_effect = lambda path: path == os.path.expanduser("~/.local/bin/cursor-agent")
            mock_access.side_effect = lambda path, mode: path == os.path.expanduser("~/.local/bin/cursor-agent")
            
            result = find_cursor_agent()
            
            expected_path = os.path.expanduser("~/.local/bin/cursor-agent")
            assert result == expected_path

    def test_find_cursor_agent_in_usr_local_bin(self):
        """Проверка работы find_cursor_agent() когда cursor-agent в /usr/local/bin."""
        with patch("shutil.which") as mock_which, \
             patch("os.path.isfile") as mock_isfile, \
             patch("os.access") as mock_access:
            
            mock_which.return_value = None
            # Первый путь не найден
            mock_isfile.side_effect = lambda path: path == "/usr/local/bin/cursor-agent"
            mock_access.side_effect = lambda path, mode: path == "/usr/local/bin/cursor-agent"
            
            result = find_cursor_agent()
            
            assert result == "/usr/local/bin/cursor-agent"

    def test_find_cursor_agent_in_home_bin(self):
        """Проверка работы find_cursor_agent() когда cursor-agent в ~/bin."""
        with patch("shutil.which") as mock_which, \
             patch("os.path.isfile") as mock_isfile, \
             patch("os.access") as mock_access:
            
            mock_which.return_value = None
            # Первые два пути не найдены
            mock_isfile.side_effect = lambda path: path == os.path.expanduser("~/bin/cursor-agent")
            mock_access.side_effect = lambda path, mode: path == os.path.expanduser("~/bin/cursor-agent")
            
            result = find_cursor_agent()
            
            expected_path = os.path.expanduser("~/bin/cursor-agent")
            assert result == expected_path

    def test_find_cursor_agent_not_found(self):
        """TC-UNIT-03: Проверка работы find_cursor_agent() когда cursor-agent не найден."""
        with patch("shutil.which") as mock_which, \
             patch("os.path.isfile") as mock_isfile:
            
            mock_which.return_value = None
            mock_isfile.return_value = False
            
            result = find_cursor_agent()
            
            assert result is None

    def test_find_cursor_agent_file_not_executable(self):
        """Проверка, что файл без прав на выполнение не возвращается."""
        with patch("shutil.which") as mock_which, \
             patch("os.path.isfile") as mock_isfile, \
             patch("os.access") as mock_access:
            
            mock_which.return_value = None
            mock_isfile.return_value = True
            mock_access.return_value = False  # Файл существует, но не исполняемый
            
            result = find_cursor_agent()
            
            assert result is None


class TestCheckCursorAgentAvailable:
    """Tests for check_cursor_agent_available() function."""

    def test_check_cursor_agent_available_when_found(self):
        """TC-UNIT-04: Проверка работы check_cursor_agent_available() когда cursor-agent доступен."""
        with patch("cursor_subagent_mcp.executor.cli.find_cursor_agent") as mock_find:
            mock_find.return_value = "/usr/bin/cursor-agent"
            
            is_available, message = check_cursor_agent_available()
            
            assert is_available is True
            assert "cursor-agent found at: /usr/bin/cursor-agent" in message
            mock_find.assert_called_once()

    def test_check_cursor_agent_available_when_not_found(self):
        """TC-UNIT-05: Проверка работы check_cursor_agent_available() когда cursor-agent недоступен."""
        with patch("cursor_subagent_mcp.executor.cli.find_cursor_agent") as mock_find:
            mock_find.return_value = None
            
            is_available, message = check_cursor_agent_available()
            
            assert is_available is False
            assert "cursor-agent CLI not found in PATH" in message
            assert "https://docs.cursor.com/cli" in message
            mock_find.assert_called_once()

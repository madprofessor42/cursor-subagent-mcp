"""Tests for executor shell detection functions."""

import os
from unittest.mock import patch

import pytest
from cursor_subagent_mcp.executor.shell import detect_shell, get_shell_config_file


class TestDetectShell:
    """Tests for detect_shell() function."""

    def test_detect_shell_zsh_from_env(self):
        """TC-UNIT-01: Проверка работы detect_shell() для zsh из переменной окружения."""
        with patch.dict(os.environ, {"SHELL": "/bin/zsh"}):
            result = detect_shell()
            
            assert result == "zsh"

    def test_detect_shell_bash_from_env(self):
        """TC-UNIT-02: Проверка работы detect_shell() для bash из переменной окружения."""
        with patch.dict(os.environ, {"SHELL": "/bin/bash"}):
            result = detect_shell()
            
            assert result == "bash"

    def test_detect_shell_zsh_from_config_file(self):
        """TC-UNIT-01: Проверка работы detect_shell() для zsh из конфигурационного файла."""
        with patch.dict(os.environ, {"SHELL": ""}), \
             patch("os.path.exists") as mock_exists, \
             patch("os.path.expanduser") as mock_expanduser:
            
            home = "/home/test"
            mock_expanduser.return_value = home
            mock_exists.side_effect = lambda path: path == os.path.join(home, ".zshrc")
            
            result = detect_shell()
            
            assert result == "zsh"
            mock_exists.assert_any_call(os.path.join(home, ".zshrc"))

    def test_detect_shell_bash_from_config_file(self):
        """TC-UNIT-02: Проверка работы detect_shell() для bash из конфигурационного файла."""
        with patch.dict(os.environ, {"SHELL": ""}), \
             patch("os.path.exists") as mock_exists, \
             patch("os.path.expanduser") as mock_expanduser:
            
            home = "/home/test"
            mock_expanduser.return_value = home
            mock_exists.side_effect = lambda path: path == os.path.join(home, ".bashrc")
            
            result = detect_shell()
            
            assert result == "bash"
            mock_exists.assert_any_call(os.path.join(home, ".bashrc"))

    def test_detect_shell_unknown(self):
        """TC-UNIT-03: Проверка работы detect_shell() для неизвестного shell."""
        with patch.dict(os.environ, {"SHELL": "/bin/fish"}), \
             patch("os.path.exists") as mock_exists:
            
            mock_exists.return_value = False
            
            result = detect_shell()
            
            assert result == "unknown"

    def test_detect_shell_unknown_no_config_files(self):
        """TC-UNIT-03: Проверка работы detect_shell() когда нет конфигурационных файлов."""
        with patch.dict(os.environ, {"SHELL": ""}), \
             patch("os.path.exists") as mock_exists, \
             patch("os.path.expanduser") as mock_expanduser:
            
            home = "/home/test"
            mock_expanduser.return_value = home
            mock_exists.return_value = False
            
            result = detect_shell()
            
            assert result == "unknown"

    def test_detect_shell_zsh_in_path(self):
        """Проверка работы detect_shell() когда zsh указан в пути."""
        with patch.dict(os.environ, {"SHELL": "/usr/local/bin/zsh"}):
            result = detect_shell()
            
            assert result == "zsh"

    def test_detect_shell_bash_in_path(self):
        """Проверка работы detect_shell() когда bash указан в пути."""
        with patch.dict(os.environ, {"SHELL": "/usr/bin/bash"}):
            result = detect_shell()
            
            assert result == "bash"


class TestGetShellConfigFile:
    """Tests for get_shell_config_file() function."""

    def test_get_shell_config_file_zsh(self):
        """TC-UNIT-04: Проверка работы get_shell_config_file() для zsh."""
        with patch("cursor_subagent_mcp.executor.shell.detect_shell") as mock_detect, \
             patch("os.path.expanduser") as mock_expanduser:
            
            mock_detect.return_value = "zsh"
            home = "/home/test"
            mock_expanduser.return_value = home
            
            result = get_shell_config_file()
            
            assert result == os.path.join(home, ".zshrc")
            mock_detect.assert_called_once()

    def test_get_shell_config_file_bash(self):
        """TC-UNIT-05: Проверка работы get_shell_config_file() для bash."""
        with patch("cursor_subagent_mcp.executor.shell.detect_shell") as mock_detect, \
             patch("os.path.expanduser") as mock_expanduser:
            
            mock_detect.return_value = "bash"
            home = "/home/test"
            mock_expanduser.return_value = home
            
            result = get_shell_config_file()
            
            assert result == os.path.join(home, ".bashrc")
            mock_detect.assert_called_once()

    def test_get_shell_config_file_unknown_defaults_to_bash(self):
        """Проверка работы get_shell_config_file() для unknown shell (по умолчанию bash)."""
        with patch("cursor_subagent_mcp.executor.shell.detect_shell") as mock_detect, \
             patch("os.path.expanduser") as mock_expanduser:
            
            mock_detect.return_value = "unknown"
            home = "/home/test"
            mock_expanduser.return_value = home
            
            result = get_shell_config_file()
            
            assert result == os.path.join(home, ".bashrc")
            mock_detect.assert_called_once()

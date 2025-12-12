"""Tests for pytest fixtures in conftest.py."""

import pytest
from pathlib import Path

from cursor_subagent_mcp import config
from cursor_subagent_mcp.executor import logging


class TestResetConfigSingleton:
    """Tests for reset_config_singleton fixture."""

    def test_reset_config_singleton(self, reset_config_singleton):
        """TC-UNIT-01: Проверка работы фикстуры reset_config_singleton."""
        # Проверяем, что _config сброшен в None перед тестом
        assert config._config is None
        
        # Устанавливаем значение
        test_config = config.Config()
        config._config = test_config
        
        # Проверяем, что значение установлено
        assert config._config is test_config


class TestResetLoggerSingleton:
    """Tests for reset_logger_singleton fixture."""

    def test_reset_logger_singleton(self, reset_logger_singleton):
        """TC-UNIT-02: Проверка работы фикстуры reset_logger_singleton."""
        # Проверяем, что _logger сброшен в None перед тестом
        assert logging._logger is None
        
        # Устанавливаем значение
        import logging as std_logging
        test_logger = std_logging.getLogger("test")
        logging._logger = test_logger
        
        # Проверяем, что значение установлено
        assert logging._logger is test_logger


class TestTempConfigFile:
    """Tests for temp_config_file fixture."""

    def test_temp_config_file_created(self, temp_config_file):
        """TC-UNIT-03: Проверка создания временного файла конфигурации."""
        # Проверяем, что файл создан
        assert temp_config_file.exists()
        assert temp_config_file.name == "agents.yaml"
        
        # Проверяем, что файл содержит валидный YAML
        content = temp_config_file.read_text(encoding="utf-8")
        assert "agents:" in content
        assert "analyst:" in content
        assert "developer:" in content
        
        # Проверяем, что файл находится во временной директории
        assert "agents.yaml" in str(temp_config_file)


class TestTempPromptFile:
    """Tests for temp_prompt_file fixture."""

    def test_temp_prompt_file_created(self, temp_prompt_file):
        """TC-UNIT-04: Проверка создания временного промпт-файла."""
        # Проверяем, что файл создан
        assert temp_prompt_file.exists()
        assert temp_prompt_file.name == "test_prompt.md"
        
        # Проверяем, что файл содержит тестовое содержимое
        content = temp_prompt_file.read_text(encoding="utf-8")
        assert "Test Prompt" in content
        assert "Instructions" in content
        
        # Проверяем, что файл находится во временной директории
        assert "test_prompt.md" in str(temp_prompt_file)

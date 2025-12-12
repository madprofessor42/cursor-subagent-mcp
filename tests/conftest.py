"""Pytest fixtures for cursor-subagent-mcp tests."""

import pytest
from pathlib import Path

from cursor_subagent_mcp import config
from cursor_subagent_mcp.executor import logging


@pytest.fixture
def reset_config_singleton():
    """TC-UNIT-01: Фикстура для сброса singleton _config между тестами.
    
    Сохраняет текущее значение config._config (может быть None),
    сбрасывает config._config в None перед тестом,
    восстанавливает оригинальное значение после теста.
    """
    original_value = config._config
    
    # Сброс перед тестом
    config._config = None
    
    yield
    
    # Восстановление после теста
    config._config = original_value


@pytest.fixture
def reset_logger_singleton():
    """TC-UNIT-02: Фикстура для сброса singleton _logger между тестами.
    
    Сохраняет текущее значение logging._logger (может быть None),
    сбрасывает logging._logger в None перед тестом,
    восстанавливает оригинальное значение после теста.
    """
    original_value = logging._logger
    
    # Сброс перед тестом
    logging._logger = None
    
    yield
    
    # Восстановление после теста
    logging._logger = original_value


@pytest.fixture
def temp_config_file(tmp_path):
    """TC-UNIT-03: Фикстура для создания временного файла конфигурации.
    
    Создаёт временный YAML файл agents.yaml в директории tmp_path,
    записывает базовое содержимое конфигурации,
    возвращает Path к файлу.
    Файл автоматически удаляется после теста (через tmp_path).
    """
    config_file = tmp_path / "agents.yaml"
    
    # Базовое содержимое конфигурации
    config_content = """agents:
  analyst:
    name: "Аналитик"
    description: "Создаёт техническое задание"
    prompt_file: "agents-master/02_analyst_prompt.md"
    default_model: "claude-sonnet-4-20250514"
  developer:
    name: "Разработчик"
    description: "Реализует задачи"
    prompt_file: "agents-master/08_agent_developer.md"
    default_model: "composer-1"
"""
    
    config_file.write_text(config_content, encoding="utf-8")
    
    return config_file


@pytest.fixture
def temp_prompt_file(tmp_path):
    """TC-UNIT-04: Фикстура для создания временного промпт-файла.
    
    Создаёт временный файл с промптом в директории tmp_path,
    записывает тестовое содержимое промпта,
    возвращает Path к файлу.
    Файл автоматически удаляется после теста.
    """
    prompt_file = tmp_path / "test_prompt.md"
    
    # Тестовое содержимое промпта
    prompt_content = """# Test Prompt

This is a test prompt file for testing purposes.

## Instructions

1. Do something
2. Do something else
"""
    
    prompt_file.write_text(prompt_content, encoding="utf-8")
    
    return prompt_file

"""Tests for config module."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml
from cursor_subagent_mcp import config
from cursor_subagent_mcp.config import (
    Config,
    find_config_file,
    get_config,
    load_config,
    load_prompt_file,
    resolve_prompt_path,
)


class TestFindConfigFile:
    """Tests for find_config_file() function."""

    def test_find_config_file_in_current_dir(self, tmp_path, reset_config_singleton):
        """UC-01.1: Проверка поиска agents.yaml в текущей директории."""
        # Создаём реальный файл в текущей директории
        config_file = tmp_path / "agents.yaml"
        config_file.write_text("agents: {}", encoding="utf-8")
        
        with patch("cursor_subagent_mcp.config.Path.cwd", return_value=tmp_path):
            result = find_config_file()
            
            assert result == config_file

    def test_find_config_file_in_package_dir(self, tmp_path, reset_config_singleton):
        """UC-01.1: Проверка поиска agents.yaml в директории пакета."""
        # Создаём структуру директорий
        package_dir = tmp_path / "package"
        package_dir.mkdir()
        config_file = package_dir / "agents.yaml"
        config_file.write_text("agents: {}", encoding="utf-8")
        
        with patch("cursor_subagent_mcp.config.Path.cwd", return_value=tmp_path / "other"), \
             patch("cursor_subagent_mcp.config.__file__", str(package_dir / "src" / "cursor_subagent_mcp" / "config.py")):
            
            result = find_config_file()
            
            assert result == config_file

    def test_find_config_file_in_parent_dirs(self, tmp_path, reset_config_singleton):
        """UC-01.1: Проверка поиска agents.yaml в родительских директориях."""
        # Создаём структуру директорий
        parent_dir = tmp_path / "parent"
        parent_dir.mkdir()
        config_file = parent_dir / "agents.yaml"
        config_file.write_text("agents: {}", encoding="utf-8")
        
        nested_dir = parent_dir / "deep" / "nested"
        nested_dir.mkdir(parents=True)
        
        with patch("cursor_subagent_mcp.config.Path.cwd", return_value=nested_dir), \
             patch("cursor_subagent_mcp.config.__file__", str(tmp_path / "package" / "src" / "cursor_subagent_mcp" / "config.py")):
            
            result = find_config_file()
            
            assert result == config_file

    def test_find_config_file_not_found(self, tmp_path, reset_config_singleton):
        """UC-01.1: Проверка возврата None, если файл не найден."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        with patch("cursor_subagent_mcp.config.Path.cwd", return_value=empty_dir), \
             patch("cursor_subagent_mcp.config.__file__", str(tmp_path / "package" / "src" / "cursor_subagent_mcp" / "config.py")):
            
            result = find_config_file()
            
            assert result is None


class TestLoadConfig:
    """Tests for load_config() function."""

    def test_load_config_success(self, temp_config_file, reset_config_singleton):
        """UC-01.2: Проверка успешной загрузки валидного YAML файла."""
        result = load_config(temp_config_file)
        
        assert isinstance(result, Config)
        assert "analyst" in result.agents
        assert "developer" in result.agents
        assert result.agents["analyst"].name == "Аналитик"
        assert result.agents["developer"].name == "Разработчик"

    def test_load_config_file_not_found(self, reset_config_singleton):
        """UC-01.2: Проверка обработки FileNotFoundError при отсутствии файла."""
        non_existent_path = Path("/non/existent/agents.yaml")
        
        with pytest.raises(FileNotFoundError):
            load_config(non_existent_path)

    def test_load_config_invalid_yaml(self, tmp_path, reset_config_singleton):
        """UC-01.2, А1: Проверка обработки невалидного YAML."""
        invalid_config_file = tmp_path / "invalid.yaml"
        invalid_config_file.write_text("invalid: yaml: content: [", encoding="utf-8")
        
        with pytest.raises((yaml.YAMLError, ValueError)):
            load_config(invalid_config_file)

    def test_load_config_with_prompts_base_path(self, tmp_path, reset_config_singleton):
        """UC-01.2: Проверка корректной загрузки prompts_base_path."""
        config_file = tmp_path / "agents.yaml"
        config_content = """agents:
  analyst:
    name: "Аналитик"
    description: "Создаёт техническое задание"
    prompt_file: "agents-master/02_analyst_prompt.md"
    default_model: "claude-sonnet-4-20250514"
prompts_base_path: "/custom/prompts"
"""
        config_file.write_text(config_content, encoding="utf-8")
        
        result = load_config(config_file)
        
        assert result.prompts_base_path == "/custom/prompts"


class TestResolvePromptPath:
    """Tests for resolve_prompt_path() function."""

    def test_resolve_prompt_path_absolute(self, reset_config_singleton):
        """UC-01.3: Проверка разрешения абсолютного пути."""
        absolute_path = Path("/absolute/path/to/prompt.md")
        
        config_obj = Config()
        
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = True
            
            result = resolve_prompt_path(config_obj, str(absolute_path))
            
            assert result == absolute_path

    def test_resolve_prompt_path_with_prompts_base_path(self, tmp_path, reset_config_singleton):
        """UC-01.3: Проверка разрешения относительного пути с prompts_base_path."""
        prompts_base = tmp_path / "prompts"
        prompts_base.mkdir()
        prompt_file = prompts_base / "test_prompt.md"
        prompt_file.write_text("test", encoding="utf-8")
        
        config_obj = Config(prompts_base_path=str(prompts_base))
        
        result = resolve_prompt_path(config_obj, "test_prompt.md")
        
        assert result == prompt_file
        assert result.exists()

    def test_resolve_prompt_path_relative_to_config(self, tmp_path, reset_config_singleton):
        """UC-01.3: Проверка разрешения относительного пути относительно config файла."""
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        config_file = config_dir / "agents.yaml"
        config_file.write_text("agents: {}", encoding="utf-8")
        
        prompt_file = config_dir / "prompt.md"
        prompt_file.write_text("test", encoding="utf-8")
        
        config_obj = Config()
        
        with patch("cursor_subagent_mcp.config.find_config_file") as mock_find:
            mock_find.return_value = config_file
            
            result = resolve_prompt_path(config_obj, "prompt.md")
            
            assert result == prompt_file
            assert result.exists()

    def test_resolve_prompt_path_not_found(self, reset_config_singleton):
        """UC-01.3, А2: Проверка обработки FileNotFoundError для несуществующего файла."""
        config_obj = Config()
        
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False
            
            with pytest.raises(FileNotFoundError, match="Prompt file not found"):
                resolve_prompt_path(config_obj, "/non/existent/prompt.md")

    def test_resolve_prompt_path_prompts_base_path_not_found(self, tmp_path, reset_config_singleton):
        """UC-01.3, А3: Проверка обработки FileNotFoundError когда prompts_base_path указан, но файл не найден."""
        prompts_base = tmp_path / "prompts"
        prompts_base.mkdir()
        
        config_obj = Config(prompts_base_path=str(prompts_base))
        
        with pytest.raises(FileNotFoundError, match="Prompt file not found"):
            resolve_prompt_path(config_obj, "non_existent.md")

    def test_resolve_prompt_path_config_file_not_found(self, reset_config_singleton):
        """UC-01.3, А4: Проверка обработки FileNotFoundError когда config_file не найден."""
        config_obj = Config()
        
        with patch("cursor_subagent_mcp.config.find_config_file") as mock_find:
            mock_find.return_value = None
            
            with pytest.raises(FileNotFoundError, match="Prompt file not found"):
                resolve_prompt_path(config_obj, "relative.md")


class TestLoadPromptFile:
    """Tests for load_prompt_file() function."""

    def test_load_prompt_file_success(self, temp_prompt_file, reset_config_singleton):
        """UC-01.4: Проверка успешной загрузки содержимого файла."""
        config_obj = Config()
        
        with patch("cursor_subagent_mcp.config.resolve_prompt_path") as mock_resolve:
            mock_resolve.return_value = temp_prompt_file
            
            result = load_prompt_file(config_obj, "test_prompt.md")
            
            assert "Test Prompt" in result
            assert "Instructions" in result
            assert isinstance(result, str)

    def test_load_prompt_file_not_found(self, reset_config_singleton):
        """UC-01.4, А2: Проверка обработки FileNotFoundError."""
        config_obj = Config()
        
        with patch("cursor_subagent_mcp.config.resolve_prompt_path") as mock_resolve:
            mock_resolve.side_effect = FileNotFoundError("Prompt file not found: /test/prompt.md")
            
            with pytest.raises(FileNotFoundError, match="Prompt file not found"):
                load_prompt_file(config_obj, "non_existent.md")


class TestGetConfig:
    """Tests for get_config() function."""

    def test_get_config_loads_on_first_call(self, reset_config_singleton):
        """UC-01.5: Проверка загрузки конфигурации при первом вызове."""
        mock_config = Config()
        
        with patch("cursor_subagent_mcp.config.load_config") as mock_load:
            mock_load.return_value = mock_config
            
            result = get_config()
            
            assert result is mock_config
            mock_load.assert_called_once()

    def test_get_config_returns_cached_config(self, reset_config_singleton):
        """UC-01.5: Проверка возврата кэшированной конфигурации при повторных вызовах."""
        mock_config = Config()
        
        with patch("cursor_subagent_mcp.config.load_config") as mock_load:
            mock_load.return_value = mock_config
            
            # Первый вызов
            result1 = get_config()
            # Второй вызов
            result2 = get_config()
            
            assert result1 is result2
            assert result1 is mock_config
            # load_config должен быть вызван только один раз
            assert mock_load.call_count == 1

    def test_get_config_singleton_pattern(self, reset_config_singleton):
        """UC-01.5: Проверка singleton паттерна."""
        mock_config = Config()
        
        with patch("cursor_subagent_mcp.config.load_config") as mock_load:
            mock_load.return_value = mock_config
            
            config1 = get_config()
            config2 = get_config()
            
            assert config1 is config2

    def test_get_config_cache_not_updated(self, reset_config_singleton):
        """UC-01.5, А3: Проверка, что кэш не обновляется при изменении файла."""
        mock_config1 = Config()
        mock_config2 = Config()
        
        with patch("cursor_subagent_mcp.config.load_config") as mock_load:
            mock_load.return_value = mock_config1
            
            # Первый вызов
            result1 = get_config()
            
            # Мокируем возврат другой конфигурации (но не сбрасываем кэш)
            mock_load.return_value = mock_config2
            
            # Второй вызов без сброса кэша
            result2 = get_config()
            
            # Должна быть возвращена та же конфигурация из кэша
            assert result1 is result2
            assert result1 is mock_config1
            assert result2 is not mock_config2
            # load_config должен быть вызван только один раз
            assert mock_load.call_count == 1

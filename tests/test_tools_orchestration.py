"""Tests for tools.orchestration module."""

from unittest.mock import MagicMock, patch

import pytest
from cursor_subagent_mcp.config import AgentConfig
from cursor_subagent_mcp.tools.orchestration import get_orchestration_guide


class TestGetOrchestrationGuide:
    """Tests for get_orchestration_guide() function."""

    def test_get_orchestration_guide_success(self, reset_config_singleton):
        """UC-03.1: Проверка успешного получения guide и списка агентов."""
        # Создаём мок конфигурации с несколькими агентами
        mock_config = MagicMock()
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
            "architect": AgentConfig(
                name="Архитектор",
                description="Проектирует архитектуру",
                prompt_file="agents-master/04_architect_prompt.md",
            ),
        }
        mock_config.orchestrator_prompt_file = "agents-master/01_orchestrator.md"
        
        mock_prompt_content = "# Orchestrator Guide\n\nThis is the guide content."
        
        with patch("cursor_subagent_mcp.tools.orchestration.get_config", return_value=mock_config), \
             patch("cursor_subagent_mcp.tools.orchestration.load_prompt_file", return_value=mock_prompt_content):
            
            result = get_orchestration_guide()
            
            assert "guide" in result
            assert result["guide"] == mock_prompt_content
            assert "agents" in result
            assert len(result["agents"]) == 3
            assert "analyst" in result["agents"]
            assert "developer" in result["agents"]
            assert "architect" in result["agents"]
            
            # Проверяем структуру каждого агента
            assert result["agents"]["analyst"]["name"] == "Аналитик"
            assert result["agents"]["analyst"]["description"] == "Создаёт техническое задание"
            assert result["agents"]["developer"]["name"] == "Разработчик"
            assert result["agents"]["developer"]["description"] == "Реализует задачи"

    def test_get_orchestration_guide_file_not_found(self, reset_config_singleton):
        """UC-03.2: Проверка обработки отсутствующего файла оркестратора."""
        mock_config = MagicMock()
        mock_config.agents = {
            "analyst": AgentConfig(
                name="Аналитик",
                description="Создаёт техническое задание",
                prompt_file="agents-master/02_analyst_prompt.md",
            ),
        }
        mock_config.orchestrator_prompt_file = "agents-master/01_orchestrator.md"
        
        with patch("cursor_subagent_mcp.tools.orchestration.get_config", return_value=mock_config), \
             patch("cursor_subagent_mcp.tools.orchestration.load_prompt_file", side_effect=FileNotFoundError("File not found")):
            
            result = get_orchestration_guide()
            
            assert "error" in result
            assert "File not found" in result["error"]
            assert "agents" in result
            assert len(result["agents"]) == 1
            assert "guide" not in result

    def test_get_orchestration_guide_empty_agents(self, reset_config_singleton):
        """UC-03.3: Проверка обработки пустой конфигурации агентов."""
        mock_config = MagicMock()
        mock_config.agents = {}
        mock_config.orchestrator_prompt_file = "agents-master/01_orchestrator.md"
        
        mock_prompt_content = "# Orchestrator Guide\n\nThis is the guide content."
        
        with patch("cursor_subagent_mcp.tools.orchestration.get_config", return_value=mock_config), \
             patch("cursor_subagent_mcp.tools.orchestration.load_prompt_file", return_value=mock_prompt_content):
            
            result = get_orchestration_guide()
            
            assert "guide" in result
            assert result["guide"] == mock_prompt_content
            assert "agents" in result
            assert result["agents"] == {}

    def test_get_orchestration_guide_multiple_agents(self, reset_config_singleton):
        """UC-03.1, А1: Проверка получения guide с несколькими агентами."""
        mock_config = MagicMock()
        mock_config.agents = {
            "analyst": AgentConfig(
                name="Аналитик",
                description="Создаёт техническое задание",
                prompt_file="agents-master/02_analyst_prompt.md",
            ),
            "architect": AgentConfig(
                name="Архитектор",
                description="Проектирует архитектуру",
                prompt_file="agents-master/04_architect_prompt.md",
            ),
            "developer": AgentConfig(
                name="Разработчик",
                description="Реализует задачи",
                prompt_file="agents-master/08_agent_developer.md",
            ),
        }
        mock_config.orchestrator_prompt_file = "agents-master/01_orchestrator.md"
        
        mock_prompt_content = "# Orchestrator Guide\n\nThis is the guide content."
        
        with patch("cursor_subagent_mcp.tools.orchestration.get_config", return_value=mock_config), \
             patch("cursor_subagent_mcp.tools.orchestration.load_prompt_file", return_value=mock_prompt_content):
            
            result = get_orchestration_guide()
            
            assert "guide" in result
            assert "agents" in result
            assert len(result["agents"]) == 3
            
            # Проверяем корректность name и description для каждого агента
            assert result["agents"]["analyst"]["name"] == "Аналитик"
            assert result["agents"]["analyst"]["description"] == "Создаёт техническое задание"
            assert result["agents"]["architect"]["name"] == "Архитектор"
            assert result["agents"]["architect"]["description"] == "Проектирует архитектуру"
            assert result["agents"]["developer"]["name"] == "Разработчик"
            assert result["agents"]["developer"]["description"] == "Реализует задачи"

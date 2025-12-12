"""Tests for executor.logging module."""

import logging as std_logging
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from cursor_subagent_mcp.executor import logging


class TestGetLogger:
    """Tests for get_logger() function."""

    def test_get_logger_creation(self, reset_logger_singleton):
        """TC-UNIT-07.1: UC-07.1 - Проверка создания логгера при первом вызове."""
        mock_config_file = Path("/test/project/agents.yaml")
        mock_logs_dir = mock_config_file.parent / "logs"
        
        # Очищаем handlers у глобального логгера перед тестом
        test_logger = std_logging.getLogger("cursor_subagent")
        test_logger.handlers.clear()
        
        with patch("cursor_subagent_mcp.executor.logging.find_config_file", return_value=mock_config_file), \
             patch("cursor_subagent_mcp.executor.logging.logging.FileHandler") as mock_file_handler_class, \
             patch("cursor_subagent_mcp.executor.logging.datetime") as mock_datetime:
            
            # Настраиваем мок datetime
            mock_datetime_instance = MagicMock()
            mock_datetime_instance.strftime.return_value = "2025-01-15"
            mock_datetime.now.return_value = mock_datetime_instance
            
            # Создаём мок FileHandler
            mock_file_handler = MagicMock()
            mock_file_handler_class.return_value = mock_file_handler
            
            # Мокируем Path.mkdir для конкретного экземпляра
            with patch.object(Path, "mkdir") as mock_mkdir:
                # Вызываем get_logger() первый раз
                logger = logging.get_logger()
                
                # Проверяем, что логгер создан с правильным именем
                assert logger.name == "cursor_subagent"
                
                # Проверяем, что логгер имеет уровень DEBUG
                assert logger.level == logging.logging.DEBUG
                
                # Проверяем, что была создана директория логов
                mock_mkdir.assert_called_once_with(exist_ok=True)
                
                # Проверяем, что был создан FileHandler
                mock_file_handler_class.assert_called_once()
                call_args = mock_file_handler_class.call_args
                assert "agents_2025-01-15.log" in str(call_args[0][0])
                
                # Проверяем, что handler был добавлен в логгер
                assert len(logger.handlers) > 0

    def test_get_logger_singleton(self, reset_logger_singleton):
        """TC-UNIT-07.2: UC-07.2 - Проверка singleton паттерна."""
        mock_config_file = Path("/test/project/agents.yaml")
        
        # Очищаем handlers у глобального логгера перед тестом
        test_logger = std_logging.getLogger("cursor_subagent")
        test_logger.handlers.clear()
        
        with patch("cursor_subagent_mcp.executor.logging.find_config_file", return_value=mock_config_file), \
             patch("cursor_subagent_mcp.executor.logging.logging.FileHandler") as mock_file_handler_class, \
             patch("cursor_subagent_mcp.executor.logging.datetime") as mock_datetime, \
             patch.object(Path, "mkdir"):
            
            # Настраиваем мок datetime
            mock_datetime_instance = MagicMock()
            mock_datetime_instance.strftime.return_value = "2025-01-15"
            mock_datetime.now.return_value = mock_datetime_instance
            
            # Создаём мок FileHandler
            mock_file_handler = MagicMock()
            mock_file_handler_class.return_value = mock_file_handler
            
            # Вызываем get_logger() первый раз и сохраняем ссылку
            logger1 = logging.get_logger()
            handlers_count_1 = len(logger1.handlers)
            
            # Вызываем get_logger() второй раз
            logger2 = logging.get_logger()
            handlers_count_2 = len(logger2.handlers)
            
            # Проверяем, что возвращён тот же экземпляр логгера
            assert logger1 is logger2
            
            # Проверяем, что количество handlers не изменилось
            # (это означает, что _setup_logger() был вызван только один раз)
            assert handlers_count_1 == handlers_count_2
            
            # Проверяем, что FileHandler был создан только один раз
            assert mock_file_handler_class.call_count == 1


class TestSetupLogger:
    """Tests for _setup_logger() function."""

    def test_setup_logger_create_directory(self, reset_logger_singleton):
        """TC-UNIT-07.3: UC-07.3 - Проверка создания директории логов."""
        mock_config_file = Path("/test/project/agents.yaml")
        mock_logs_dir = mock_config_file.parent / "logs"
        
        # Очищаем handlers у глобального логгера перед тестом
        test_logger = std_logging.getLogger("cursor_subagent")
        test_logger.handlers.clear()
        
        with patch("cursor_subagent_mcp.executor.logging.find_config_file", return_value=mock_config_file), \
             patch("cursor_subagent_mcp.executor.logging.logging.FileHandler") as mock_file_handler_class, \
             patch("cursor_subagent_mcp.executor.logging.datetime") as mock_datetime, \
             patch.object(Path, "mkdir") as mock_mkdir:
            
            # Настраиваем мок datetime
            mock_datetime_instance = MagicMock()
            mock_datetime_instance.strftime.return_value = "2025-01-15"
            mock_datetime.now.return_value = mock_datetime_instance
            
            # Создаём мок FileHandler
            mock_file_handler = MagicMock()
            mock_file_handler_class.return_value = mock_file_handler
            
            # Вызываем _setup_logger() через get_logger()
            logger = logging.get_logger()
            
            # Проверяем, что mkdir был вызван для директории логов
            mock_mkdir.assert_called_once_with(exist_ok=True)
            
            # Проверяем, что логгер был создан
            assert logger is not None
            assert logger.name == "cursor_subagent"

    def test_setup_logger_config_not_found(self, reset_logger_singleton):
        """TC-UNIT-07.4: UC-07.4 - Проверка обработки отсутствия конфигурации."""
        mock_cwd = Path("/test/current/dir")
        
        # Очищаем handlers у глобального логгера перед тестом
        test_logger = std_logging.getLogger("cursor_subagent")
        test_logger.handlers.clear()
        
        with patch("cursor_subagent_mcp.executor.logging.find_config_file", return_value=None), \
             patch("cursor_subagent_mcp.executor.logging.Path.cwd", return_value=mock_cwd), \
             patch("cursor_subagent_mcp.executor.logging.logging.FileHandler") as mock_file_handler_class, \
             patch("cursor_subagent_mcp.executor.logging.datetime") as mock_datetime, \
             patch.object(Path, "mkdir") as mock_mkdir:
            
            # Настраиваем мок datetime
            mock_datetime_instance = MagicMock()
            mock_datetime_instance.strftime.return_value = "2025-01-15"
            mock_datetime.now.return_value = mock_datetime_instance
            
            # Создаём мок FileHandler
            mock_file_handler = MagicMock()
            mock_file_handler_class.return_value = mock_file_handler
            
            # Вызываем _setup_logger() через get_logger()
            logger = logging.get_logger()
            
            # Проверяем, что mkdir был вызван для директории logs в текущей директории
            # Проверяем, что был вызван mkdir для Path(mock_cwd / "logs")
            assert mock_mkdir.called
            
            # Проверяем, что логгер был создан
            assert logger is not None
            assert logger.name == "cursor_subagent"

    def test_setup_logger_filename(self, reset_logger_singleton):
        """TC-UNIT-07.5: UC-07.5 - Проверка правильного имени файла лога."""
        mock_config_file = Path("/test/project/agents.yaml")
        expected_date = "2025-01-15"
        
        # Очищаем handlers у глобального логгера перед тестом
        test_logger = std_logging.getLogger("cursor_subagent")
        test_logger.handlers.clear()
        
        with patch("cursor_subagent_mcp.executor.logging.find_config_file", return_value=mock_config_file), \
             patch("cursor_subagent_mcp.executor.logging.logging.FileHandler") as mock_file_handler_class, \
             patch("cursor_subagent_mcp.executor.logging.datetime") as mock_datetime, \
             patch.object(Path, "mkdir"):
            
            # Настраиваем мок datetime для возврата фиксированной даты
            mock_datetime_instance = MagicMock()
            mock_datetime_instance.strftime.return_value = expected_date
            mock_datetime.now.return_value = mock_datetime_instance
            
            # Создаём мок FileHandler
            mock_file_handler = MagicMock()
            mock_file_handler_class.return_value = mock_file_handler
            
            # Вызываем _setup_logger() через get_logger()
            logger = logging.get_logger()
            
            # Проверяем, что FileHandler был создан с правильным именем файла
            mock_file_handler_class.assert_called_once()
            call_args = mock_file_handler_class.call_args
            log_file_path = call_args[0][0]
            
            # Проверяем, что путь содержит правильное имя файла
            assert f"agents_{expected_date}.log" in str(log_file_path)
            
            # Проверяем, что логгер был создан
            assert logger is not None

    def test_setup_logger_no_duplicate_handlers(self, reset_logger_singleton):
        """TC-UNIT-07.6: UC-07.6 - Проверка избежания дублирования handlers."""
        mock_config_file = Path("/test/project/agents.yaml")
        
        # Очищаем handlers у глобального логгера перед тестом
        test_logger = std_logging.getLogger("cursor_subagent")
        test_logger.handlers.clear()
        
        with patch("cursor_subagent_mcp.executor.logging.find_config_file", return_value=mock_config_file), \
             patch("cursor_subagent_mcp.executor.logging.logging.FileHandler") as mock_file_handler_class, \
             patch("cursor_subagent_mcp.executor.logging.datetime") as mock_datetime, \
             patch.object(Path, "mkdir"):
            
            # Настраиваем мок datetime
            mock_datetime_instance = MagicMock()
            mock_datetime_instance.strftime.return_value = "2025-01-15"
            mock_datetime.now.return_value = mock_datetime_instance
            
            # Создаём мок FileHandler
            mock_file_handler = MagicMock()
            mock_file_handler_class.return_value = mock_file_handler
            
            # Вызываем get_logger() первый раз
            logger1 = logging.get_logger()
            handlers_count_1 = len(logger1.handlers)
            
            # Сохраняем ссылку на логгер
            logger_reference = logger1
            
            # Вызываем get_logger() второй раз (который должен вернуть тот же логгер)
            logger2 = logging.get_logger()
            handlers_count_2 = len(logger2.handlers)
            
            # Проверяем, что был возвращён тот же экземпляр логгера
            assert logger1 is logger2
            assert logger2 is logger_reference
            
            # Проверяем, что количество handlers не изменилось
            assert handlers_count_1 == handlers_count_2
            
            # Проверяем, что FileHandler был создан только один раз
            assert mock_file_handler_class.call_count == 1

    def test_setup_logger_different_dates(self, reset_logger_singleton):
        """TC-UNIT-07.7: UC-07.5, А1 - Проверка создания файлов для разных дат."""
        mock_config_file = Path("/test/project/agents.yaml")
        date1 = "2025-01-15"
        date2 = "2025-01-16"
        
        # Очищаем handlers у глобального логгера перед тестом
        test_logger = std_logging.getLogger("cursor_subagent")
        test_logger.handlers.clear()
        
        with patch("cursor_subagent_mcp.executor.logging.find_config_file", return_value=mock_config_file), \
             patch("cursor_subagent_mcp.executor.logging.logging.FileHandler") as mock_file_handler_class, \
             patch("cursor_subagent_mcp.executor.logging.datetime") as mock_datetime, \
             patch.object(Path, "mkdir"):
            
            # Первый вызов с первой датой
            mock_datetime_instance_1 = MagicMock()
            mock_datetime_instance_1.strftime.return_value = date1
            mock_datetime.now.return_value = mock_datetime_instance_1
            
            mock_file_handler_1 = MagicMock()
            mock_file_handler_class.return_value = mock_file_handler_1
            
            logger1 = logging.get_logger()
            
            # Проверяем первый вызов
            assert mock_file_handler_class.call_count == 1
            call_args_1 = mock_file_handler_class.call_args
            log_file_path_1 = call_args_1[0][0]
            assert f"agents_{date1}.log" in str(log_file_path_1)
            
            # Сбрасываем singleton вручную для проверки создания нового файла
            logging._logger = None
            # Также очищаем handlers у глобального логгера
            test_logger.handlers.clear()
            
            # Второй вызов с другой датой
            mock_datetime_instance_2 = MagicMock()
            mock_datetime_instance_2.strftime.return_value = date2
            mock_datetime.now.return_value = mock_datetime_instance_2
            
            mock_file_handler_2 = MagicMock()
            mock_file_handler_class.return_value = mock_file_handler_2
            
            logger2 = logging.get_logger()
            
            # Проверяем второй вызов
            assert mock_file_handler_class.call_count == 2
            call_args_2 = mock_file_handler_class.call_args
            log_file_path_2 = call_args_2[0][0]
            assert f"agents_{date2}.log" in str(log_file_path_2)
            
            # Проверяем, что файлы для разных дат созданы
            assert f"agents_{date1}.log" in str(log_file_path_1)
            assert f"agents_{date2}.log" in str(log_file_path_2)
            assert str(log_file_path_1) != str(log_file_path_2)

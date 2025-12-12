"""Tests for executor utils."""

import pytest
from cursor_subagent_mcp.executor.utils import extract_final_json, strip_ansi


class TestStripAnsi:
    """Tests for strip_ansi() function."""

    def test_strip_ansi_with_ansi_codes(self):
        """TC-UNIT-01: Проверка работы strip_ansi() с ANSI кодами."""
        text_with_ansi = '\x1b[31mRed text\x1b[0m'
        result = strip_ansi(text_with_ansi)
        
        assert result == 'Red text'

    def test_strip_ansi_with_normal_text(self):
        """TC-UNIT-02: Проверка работы strip_ansi() с обычным текстом."""
        normal_text = 'Normal text'
        result = strip_ansi(normal_text)
        
        assert result == 'Normal text'

    def test_strip_ansi_with_multiple_codes(self):
        """Проверка работы strip_ansi() с несколькими ANSI кодами."""
        text_with_multiple = '\x1b[31mRed\x1b[0m \x1b[32mGreen\x1b[0m \x1b[34mBlue\x1b[0m'
        result = strip_ansi(text_with_multiple)
        
        assert result == 'Red Green Blue'

    def test_strip_ansi_with_empty_string(self):
        """Проверка работы strip_ansi() с пустой строкой."""
        result = strip_ansi('')
        
        assert result == ''


class TestExtractFinalJson:
    """Tests for extract_final_json() function."""

    def test_extract_json_from_markdown_block(self):
        """TC-UNIT-03: Проверка работы extract_final_json() с JSON в markdown блоке."""
        text = '```json\n{"key": "value"}\n```'
        result = extract_final_json(text)
        
        assert result == '{"key": "value"}'

    def test_extract_json_multiple_blocks(self):
        """TC-UNIT-04: Проверка работы extract_final_json() с несколькими JSON блоками."""
        text = '```json\n{"first": "block"}\n```\nSome text\n```json\n{"last": "block"}\n```'
        result = extract_final_json(text)
        
        assert result == '{"last": "block"}'

    def test_extract_json_no_json(self):
        """TC-UNIT-05: Проверка работы extract_final_json() без JSON."""
        text = 'Just text'
        result = extract_final_json(text)
        
        assert result is None

    def test_extract_json_from_code_block_without_label(self):
        """Проверка извлечения JSON из markdown блока без метки json."""
        text = '```\n{"key": "value"}\n```'
        result = extract_final_json(text)
        
        assert result == '{"key": "value"}'

    def test_extract_json_from_raw_object(self):
        """Проверка извлечения JSON объекта в конце текста."""
        text = 'Some text before\n{"key": "value"}'
        result = extract_final_json(text)
        
        assert result == '{"key": "value"}'

    def test_extract_json_from_raw_array(self):
        """Проверка извлечения JSON массива в конце текста."""
        text = 'Some text before\n[1, 2, 3]'
        result = extract_final_json(text)
        
        assert result == '[1, 2, 3]'

    def test_extract_json_empty_string(self):
        """Проверка работы extract_final_json() с пустой строкой."""
        result = extract_final_json('')
        
        assert result is None

    def test_extract_json_invalid_json_in_block(self):
        """Проверка обработки невалидного JSON в markdown блоке."""
        text = '```json\n{invalid json}\n```'
        result = extract_final_json(text)
        
        # Должен попробовать найти JSON в других местах или вернуть None
        assert result is None or result == '{invalid json}'

    def test_extract_json_nested_object(self):
        """Проверка извлечения вложенного JSON объекта."""
        text = '```json\n{"outer": {"inner": "value"}}\n```'
        result = extract_final_json(text)
        
        assert result == '{"outer": {"inner": "value"}}'

    def test_extract_json_multiple_objects_takes_last(self):
        """Проверка, что из нескольких JSON объектов выбирается последний."""
        text = '{"first": 1}\n{"second": 2}\n{"third": 3}'
        result = extract_final_json(text)
        
        assert result == '{"third": 3}'

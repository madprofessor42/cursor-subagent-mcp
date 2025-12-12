"""Tests for executor models."""

import pytest
from cursor_subagent_mcp.executor.models import StreamEvent, ExecutionResult


class TestStreamEvent:
    """Tests for StreamEvent class."""

    def test_from_json_valid(self):
        """TC-UNIT-01: Проверка создания StreamEvent из JSON."""
        json_line = '{"type": "system", "subtype": "init", "session_id": "123"}'
        event = StreamEvent.from_json(json_line)
        
        assert event is not None
        assert event.event_type == "system"
        assert event.subtype == "init"
        assert event.data["session_id"] == "123"
        assert isinstance(event.data, dict)

    def test_from_json_invalid(self):
        """TC-UNIT-02: Проверка обработки невалидного JSON в StreamEvent.from_json()."""
        invalid_json = "invalid json"
        event = StreamEvent.from_json(invalid_json)
        
        assert event is None

    def test_from_json_missing_type(self):
        """Проверка создания StreamEvent с отсутствующим полем type."""
        json_line = '{"subtype": "init", "session_id": "123"}'
        event = StreamEvent.from_json(json_line)
        
        assert event is not None
        assert event.event_type == "unknown"  # Должно быть "unknown" по умолчанию
        assert event.subtype == "init"

    def test_from_json_empty_data(self):
        """Проверка создания StreamEvent с минимальными данными."""
        json_line = '{"type": "assistant"}'
        event = StreamEvent.from_json(json_line)
        
        assert event is not None
        assert event.event_type == "assistant"
        assert event.subtype is None
        assert event.data == {"type": "assistant"}


class TestExecutionResult:
    """Tests for ExecutionResult class."""

    def test_create_with_required_fields(self):
        """TC-UNIT-03: Проверка создания ExecutionResult."""
        result = ExecutionResult(success=True, output="test")
        
        assert result.success is True
        assert result.output == "test"
        assert result.error is None
        assert result.return_code == 0
        assert result.events == []
        assert result.session_id is None
        assert result.duration_ms is None

    def test_create_with_all_fields(self):
        """Проверка создания ExecutionResult со всеми полями."""
        event = StreamEvent(event_type="system", subtype="init")
        result = ExecutionResult(
            success=False,
            output="error output",
            error="Something went wrong",
            return_code=1,
            events=[event],
            session_id="test-session-123",
            duration_ms=5000,
        )
        
        assert result.success is False
        assert result.output == "error output"
        assert result.error == "Something went wrong"
        assert result.return_code == 1
        assert len(result.events) == 1
        assert result.events[0] == event
        assert result.session_id == "test-session-123"
        assert result.duration_ms == 5000

    def test_create_with_default_values(self):
        """Проверка значений по умолчанию для ExecutionResult."""
        result = ExecutionResult(success=True, output="")
        
        assert result.error is None
        assert result.return_code == 0
        assert result.events == []
        assert result.session_id is None
        assert result.duration_ms is None

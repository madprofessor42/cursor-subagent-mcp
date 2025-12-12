"""Data models for executor module."""

import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StreamEvent:
    """Event from cursor-agent stream."""
    event_type: str
    subtype: Optional[str] = None
    data: dict = field(default_factory=dict)
    
    @classmethod
    def from_json(cls, line: str) -> Optional["StreamEvent"]:
        """Parse a JSON line into a StreamEvent."""
        try:
            data = json.loads(line)
            return cls(
                event_type=data.get("type", "unknown"),
                subtype=data.get("subtype"),
                data=data
            )
        except json.JSONDecodeError:
            return None


@dataclass
class ExecutionResult:
    """Result of a subagent execution."""

    success: bool
    output: str
    error: Optional[str] = None
    return_code: int = 0
    events: list[StreamEvent] = field(default_factory=list)
    session_id: Optional[str] = None
    duration_ms: Optional[int] = None

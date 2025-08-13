"""
History management protocol definitions for the CurveEditor.

This module defines the protocol interfaces for history/undo/redo services,
managing application state history with memory-efficient compression.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol


@dataclass
class HistoryEntry:
    """Single entry in the history stack."""
    timestamp: datetime
    description: str
    state: Any  # Can be compressed or uncompressed
    compressed: bool = False
    size_bytes: int = 0

    @classmethod
    def create(cls, description: str, state: Any, compressed: bool = False) -> "HistoryEntry":
        """Create a new history entry."""
        import sys
        return cls(
            timestamp=datetime.now(),
            description=description,
            state=state,
            compressed=compressed,
            size_bytes=sys.getsizeof(state)
        )


@dataclass
class HistoryStats:
    """Statistics about history usage."""
    total_entries: int
    current_position: int
    memory_usage_mb: float
    compression_ratio: float
    can_undo: bool
    can_redo: bool


class HistoryProtocol(Protocol):
    """Protocol for history management services."""

    def add_to_history(self, state: Any, description: str = "") -> None:
        """Add a new state to history."""
        ...

    def undo(self) -> Any | None:
        """Undo last operation, returns previous state."""
        ...

    def redo(self) -> Any | None:
        """Redo next operation, returns next state."""
        ...

    def clear_history(self) -> None:
        """Clear all history."""
        ...

    def can_undo(self) -> bool:
        """Check if undo is available."""
        ...

    def can_redo(self) -> bool:
        """Check if redo is available."""
        ...

    def get_history_stats(self) -> HistoryStats:
        """Get statistics about history usage."""
        ...

    def compress_state(self, state: Any) -> bytes:
        """Compress state for storage."""
        ...

    def decompress_state(self, compressed: bytes) -> Any:
        """Decompress state for restoration."""
        ...

    def set_memory_limit_mb(self, limit_mb: int) -> None:
        """Set memory limit for history storage."""
        ...

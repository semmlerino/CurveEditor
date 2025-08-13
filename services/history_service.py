"""
History management service for the CurveEditor.

This service manages undo/redo functionality with memory-efficient
state compression and automatic memory limit enforcement.
"""

import logging
import pickle
import sys
import zlib
from typing import Any

from services.compressed_snapshot import CompressedStateSnapshot
from services.protocols.history_protocol import HistoryProtocol, HistoryStats

logger = logging.getLogger(__name__)



class HistoryService(HistoryProtocol):
    """
    Manages application state history for undo/redo.

    This service is responsible for:
    - Recording application state changes
    - Providing undo/redo functionality
    - Compressing states for memory efficiency
    - Enforcing memory limits
    - Managing history stack
    """

    def __init__(self, max_memory_mb: int = 50):
        """
        Initialize the history service.

        Args:
            max_memory_mb: Maximum memory usage for history in MB
        """
        self._history: list[Any] = []  # Can store CompressedStateSnapshot or dict
        self._history_index = -1
        self._max_memory_mb = max_memory_mb
        self._max_memory = max_memory_mb * 1024 * 1024  # Convert to bytes
        self.compression_enabled = True

        # History statistics
        self.history_stats = {
            "total_snapshots": 0,
            "delta_snapshots": 0,
            "full_snapshots": 0,
            "memory_usage_mb": 0.0,
            "compression_ratio": 0.0,
        }

    def add_to_history(self, state: Any, description: str = "") -> None:
        """
        Add a new state to history.

        Args:
            state: Application state to record (dict with curve_data, point_name, point_color)
            description: Human-readable description of the change
        """
        # Truncate future history if we're not at the end
        if self._history_index < len(self._history) - 1:
            self._history = self._history[:self._history_index + 1]

        # Extract state components
        if isinstance(state, dict):
            curve_data = state.get("curve_data", [])
            point_name = state.get("point_name", "TrackPoint")
            point_color = state.get("point_color", "#FF0000")
        else:
            # Assume it's already a CompressedStateSnapshot
            self._history.append(state)
            self._history_index += 1
            self._enforce_memory_limits()
            self._update_stats()
            return

        # Create compressed snapshot
        previous_snapshot = self._history[-1] if self._history else None

        if self.compression_enabled:
            current_state = CompressedStateSnapshot(curve_data, point_name, point_color, previous_snapshot)
        else:
            # Fallback to original format
            current_state = {
                "curve_data": list(curve_data),
                "point_name": point_name,
                "point_color": point_color,
            }

        self._history.append(current_state)
        self._history_index = len(self._history) - 1

        # Enforce memory limits
        self._enforce_memory_limits()

        # Update statistics
        self._update_stats()

        logger.debug(f"Added to history: {description} (index: {self._history_index})")

    def undo(self) -> Any | None:
        """
        Undo last operation, returns previous state.

        Returns:
            Previous state if undo available, None otherwise
        """
        if not self.can_undo():
            logger.debug("Cannot undo: at beginning of history")
            return None

        self._history_index -= 1
        state = self._history[self._history_index]

        logger.debug(f"Undo to index: {self._history_index}")
        return state

    def redo(self) -> Any | None:
        """
        Redo next operation, returns next state.

        Returns:
            Next state if redo available, None otherwise
        """
        if not self.can_redo():
            logger.debug("Cannot redo: at end of history")
            return None

        self._history_index += 1
        state = self._history[self._history_index]

        logger.debug(f"Redo to index: {self._history_index}")
        return state

    def clear_history(self) -> None:
        """Clear all history."""
        # Clean up compressed snapshots
        for entry in self._history:
            if isinstance(entry, CompressedStateSnapshot):
                entry.cleanup()

        self._history.clear()
        self._history_index = -1
        self.history_stats = {
            "total_snapshots": 0,
            "delta_snapshots": 0,
            "full_snapshots": 0,
            "memory_usage_mb": 0.0,
            "compression_ratio": 0.0,
        }
        logger.debug("History cleared")

    def can_undo(self) -> bool:
        """
        Check if undo is available.

        Returns:
            True if undo is possible
        """
        return self._history_index > 0

    def can_redo(self) -> bool:
        """
        Check if redo is available.

        Returns:
            True if redo is possible
        """
        return self._history_index < len(self._history) - 1

    def get_history_stats(self) -> HistoryStats:
        """
        Get statistics about history usage.

        Returns:
            History statistics
        """
        memory_mb = self.history_stats.get("memory_usage_mb", 0.0)
        compression_ratio = self.history_stats.get("compression_ratio", 0.0)

        return HistoryStats(
            total_entries=len(self._history),
            current_position=self._history_index,
            memory_usage_mb=memory_mb,
            compression_ratio=compression_ratio,
            can_undo=self.can_undo(),
            can_redo=self.can_redo()
        )

    def compress_state(self, state: Any) -> bytes:
        """
        Compress state for storage.

        Args:
            state: State to compress

        Returns:
            Compressed state as bytes
        """
        # Pickle and compress
        pickled = pickle.dumps(state, protocol=pickle.HIGHEST_PROTOCOL)
        compressed = zlib.compress(pickled, level=6)

        # Log compression ratio
        ratio = len(compressed) / len(pickled)
        logger.debug(f"Compressed state: {len(pickled)} → {len(compressed)} bytes ({ratio:.1%})")

        return compressed

    def decompress_state(self, compressed: bytes) -> Any:
        """
        Decompress state for restoration.

        Args:
            compressed: Compressed state bytes

        Returns:
            Decompressed state
        """
        # Decompress and unpickle
        decompressed = zlib.decompress(compressed)
        state = pickle.loads(decompressed)
        return state

    def set_memory_limit_mb(self, limit_mb: int) -> None:
        """
        Set memory limit for history storage.

        Args:
            limit_mb: New memory limit in MB
        """
        self._max_memory_mb = limit_mb
        self._max_memory = limit_mb * 1024 * 1024
        self._enforce_memory_limits()

    def _enforce_memory_limits(self) -> None:
        """Enforce memory limits by removing old history if needed."""
        total_memory = self._calculate_total_memory()

        while self._history and total_memory > self._max_memory:
            # Can't remove current or future states
            if self._history_index <= 0:
                break

            # Remove oldest state
            removed = self._history.pop(0)

            # Clean up if it's a compressed snapshot
            if isinstance(removed, CompressedStateSnapshot):
                removed.cleanup()

            # Adjust history index
            self._history_index -= 1

            # Recalculate memory
            total_memory = self._calculate_total_memory()

        logger.debug(f"Enforced memory limit: {len(self._history)} entries, {total_memory / 1024 / 1024:.1f}MB")

    def _calculate_total_memory(self) -> int:
        """Calculate total memory usage of history."""
        total = 0
        for entry in self._history:
            if isinstance(entry, CompressedStateSnapshot):
                total += entry.get_memory_usage()
            else:
                # Estimate size for dict format
                total += sys.getsizeof(pickle.dumps(entry))
        return total

    def _update_stats(self) -> None:
        """Update history statistics."""
        total = len(self._history)
        delta_count = 0
        full_count = 0

        for entry in self._history:
            if isinstance(entry, CompressedStateSnapshot):
                if entry._storage_type == "delta":
                    delta_count += 1
                else:
                    full_count += 1
            else:
                full_count += 1  # Dict format counts as full

        self.history_stats["total_snapshots"] = total
        self.history_stats["delta_snapshots"] = delta_count
        self.history_stats["full_snapshots"] = full_count
        self.history_stats["memory_usage_mb"] = self._calculate_total_memory() / 1024 / 1024

        if total > 0:
            self.history_stats["compression_ratio"] = delta_count / total
        else:
            self.history_stats["compression_ratio"] = 0.0

    def get_history_descriptions(self) -> list[tuple[int, str, bool]]:
        """
        Get list of history entry descriptions.

        Returns:
            List of (index, description, is_current) tuples
        """
        result = []
        for i, entry in enumerate(self._history):
            is_current = i == self._history_index

            if isinstance(entry, CompressedStateSnapshot):
                desc = f"State {i} ({entry._storage_type})"
            else:
                desc = f"State {i}"

            result.append((i, desc, is_current))
        return result

    def jump_to_history(self, index: int) -> Any | None:
        """
        Jump to specific history entry.

        Args:
            index: History index to jump to

        Returns:
            State at that index, or None if invalid
        """
        if index < 0 or index >= len(self._history):
            return None

        self._history_index = index
        state = self._history[index]

        logger.debug(f"Jumped to history index: {index}")
        return state

    def get_current_state(self) -> Any | None:
        """
        Get the current state without changing history position.

        Returns:
            Current state or None if history is empty
        """
        if self._history_index < 0 or self._history_index >= len(self._history):
            return None

        return self._history[self._history_index]

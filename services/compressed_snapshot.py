"""
Compressed state snapshot for efficient history storage.

This module provides delta and full compression for application states,
minimizing memory usage in the history service.
"""

import logging
import pickle
import sys
import time
import zlib
from dataclasses import dataclass
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class DeltaChange:
    """Represents a change to the curve data."""

    operation: str  # 'add', 'delete', 'modify', 'move'
    index: int
    old_value: tuple[int, float, float] | None = None
    new_value: tuple[int, float, float] | None = None
    metadata: dict[str, Any] | None = None


class CompressedStateSnapshot:
    """Memory-efficient state snapshot with delta compression."""

    def __init__(
        self,
        curve_data: list[tuple[int, float, float]] | list[tuple[int, float, float, str]],
        point_name: str,
        point_color: str,
        previous_snapshot: "CompressedStateSnapshot | None" = None,
    ):
        # Initialize all instance variables
        self.timestamp: float = time.time()
        self.point_name: str = point_name
        self.point_color: str = point_color
        self._storage_type: str = ""
        self._base_snapshot: CompressedStateSnapshot | None = None
        self._compressed_data: bytes = b""

        # Calculate delta from previous state if available
        if previous_snapshot is not None:
            self._use_delta_compression(curve_data, previous_snapshot)
        else:
            self._use_full_compression(curve_data)

    def _use_delta_compression(
        self,
        current_data: list[tuple[int, float, float]] | list[tuple[int, float, float, str]],
        previous_snapshot: "CompressedStateSnapshot",
    ) -> None:
        """Store only the changes from previous state."""
        previous_data = previous_snapshot.get_curve_data()
        deltas = self._calculate_deltas(previous_data, current_data)

        if len(deltas) < len(current_data) * 0.3:  # If less than 30% changed
            # Use delta compression
            self._storage_type = "delta"
            self._base_snapshot = previous_snapshot
            self._compressed_data = self._compress_deltas(deltas)

            # Estimate memory savings
            full_size = self._estimate_size(current_data)
            delta_size = len(self._compressed_data)
            savings_pct = (1 - delta_size / full_size) * 100 if full_size > 0 else 0

            logger.debug(f"Delta compression: {len(deltas)} changes, {savings_pct:.1f}% memory saved")
        else:
            # Too many changes, use full compression
            self._use_full_compression(current_data)

    def _use_full_compression(
        self, curve_data: list[tuple[int, float, float]] | list[tuple[int, float, float, str]]
    ) -> None:
        """Store full state with compression."""
        self._storage_type = "full"
        self._base_snapshot = None

        # Convert to numpy array if possible for better compression
        try:
            if curve_data:
                # Convert to structured array for efficient storage
                data_array = np.array(
                    [(p[0], p[1], p[2]) for p in curve_data],
                    dtype=[("frame", np.int32), ("x", np.float32), ("y", np.float32)],
                )
                serialized = pickle.dumps(data_array, protocol=pickle.HIGHEST_PROTOCOL)
            else:
                serialized = b""

            # Compress the serialized data
            self._compressed_data = zlib.compress(serialized, level=6)

            # Log compression ratio
            original_size = len(serialized)
            compressed_size = len(self._compressed_data)
            ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0

            logger.debug(f"Full compression: {len(curve_data)} points, {ratio:.1f}% compression")

            # Explicit cleanup of large temporary objects
            del serialized
            if "data_array" in locals():
                del data_array

        except Exception as e:
            logger.warning(f"Compression failed, using fallback: {e}")
            # Fallback to simple pickle
            self._compressed_data = pickle.dumps(curve_data, protocol=pickle.HIGHEST_PROTOCOL)

    def get_curve_data(self) -> list[tuple[int, float, float]] | list[tuple[int, float, float, str]]:
        """Reconstruct curve data from compressed storage."""
        try:
            if self._storage_type == "delta":
                # Reconstruct from base + deltas
                base_data = self._base_snapshot.get_curve_data()
                deltas = self._decompress_deltas(self._compressed_data)
                return self._apply_deltas(base_data, deltas)
            else:
                # Decompress full data
                if len(self._compressed_data) == 0:
                    return []

                try:
                    # Try numpy array format first
                    decompressed = zlib.decompress(self._compressed_data)
                    data_array = pickle.loads(decompressed)

                    if isinstance(data_array, np.ndarray):
                        # Convert back to list of tuples
                        return [(int(row[0]), float(row[1]), float(row[2])) for row in data_array]
                    else:
                        return data_array

                except (zlib.error, pickle.UnpicklingError):
                    # Fallback to simple pickle
                    return pickle.loads(self._compressed_data)

        except Exception as e:
            logger.error(f"Failed to reconstruct curve data: {e}")
            return []

    def _calculate_deltas(
        self,
        old_data: list[tuple[int, float, float]] | list[tuple[int, float, float, str]],
        new_data: list[tuple[int, float, float]] | list[tuple[int, float, float, str]],
    ) -> list[DeltaChange]:
        """Calculate changes between two data sets."""
        deltas = []

        # Convert to dictionaries for efficient lookup by frame
        old_dict = {p[0]: (i, p) for i, p in enumerate(old_data)}
        new_dict = {p[0]: (i, p) for i, p in enumerate(new_data)}

        old_frames = set(old_dict.keys())
        new_frames = set(new_dict.keys())

        # Detect deletions
        for frame in old_frames - new_frames:
            old_idx, old_point = old_dict[frame]
            deltas.append(DeltaChange("delete", old_idx, old_point, None))

        # Detect additions
        for frame in new_frames - old_frames:
            new_idx, new_point = new_dict[frame]
            deltas.append(DeltaChange("add", new_idx, None, new_point))

        # Detect modifications
        for frame in old_frames & new_frames:
            old_idx, old_point = old_dict[frame]
            new_idx, new_point = new_dict[frame]

            if old_point != new_point:
                deltas.append(DeltaChange("modify", new_idx, old_point, new_point))

        return deltas

    def _compress_deltas(self, deltas: list[DeltaChange]) -> bytes:
        """Compress delta changes."""
        # Convert deltas to a compact representation
        delta_data = []
        for delta in deltas:
            delta_dict = {"op": delta.operation, "idx": delta.index, "old": delta.old_value, "new": delta.new_value}
            delta_data.append(delta_dict)

        serialized = pickle.dumps(delta_data, protocol=pickle.HIGHEST_PROTOCOL)
        compressed = zlib.compress(serialized, level=6)

        # Explicit cleanup
        del serialized
        del delta_data

        return compressed

    def _decompress_deltas(self, compressed_deltas: bytes) -> list[DeltaChange]:
        """Decompress delta changes."""
        try:
            decompressed = zlib.decompress(compressed_deltas)
            delta_data = pickle.loads(decompressed)

            deltas = []
            for delta_dict in delta_data:
                delta = DeltaChange(delta_dict["op"], delta_dict["idx"], delta_dict["old"], delta_dict["new"])
                deltas.append(delta)

            return deltas
        except Exception as e:
            logger.error(f"Failed to decompress deltas: {e}")
            return []

    def _apply_deltas(
        self, base_data: list[tuple[int, float, float]] | list[tuple[int, float, float, str]], deltas: list[DeltaChange]
    ) -> list[tuple[int, float, float]] | list[tuple[int, float, float, str]]:
        """Apply delta changes to base data."""
        result = list(base_data)

        # Apply deltas in order
        for delta in deltas:
            if delta.operation == "add" and delta.new_value:
                # Insert at correct position to maintain frame order
                frame = delta.new_value[0]
                insert_pos = self._find_insert_position(result, frame)
                result.insert(insert_pos, delta.new_value)

            elif delta.operation == "delete" and 0 <= delta.index < len(result):
                result.pop(delta.index)

            elif delta.operation == "modify" and 0 <= delta.index < len(result):
                if delta.new_value:
                    result[delta.index] = delta.new_value

        return result

    def _find_insert_position(
        self, data: list[tuple[int, float, float]] | list[tuple[int, float, float, str]], frame: int
    ) -> int:
        """Find correct insertion position to maintain frame order."""
        for i, point in enumerate(data):
            if point[0] > frame:
                return i
        return len(data)

    def cleanup(self) -> None:
        """Clean up resources and break circular references."""
        # Break the reference chain to allow garbage collection
        if hasattr(self, "_base_snapshot"):
            self._base_snapshot = None
        if hasattr(self, "_compressed_data"):
            self._compressed_data = b""

    def _estimate_size(self, data: list[tuple[int, float, float]] | list[tuple[int, float, float, str]]) -> int:
        """Estimate memory size of data."""
        if not data:
            return 0
        return len(data) * sys.getsizeof(data[0])

    def get_memory_usage(self) -> int:
        """Get approximate memory usage of this snapshot."""
        size = sys.getsizeof(self._compressed_data)
        size += sys.getsizeof(self.point_name)
        size += sys.getsizeof(self.point_color)
        size += 100  # Overhead estimate
        return size

    # Dictionary-like interface for backward compatibility
    def __getitem__(self, key: str) -> Any:
        if key == "curve_data":
            return self.get_curve_data()
        elif key == "point_name":
            return self.point_name
        elif key == "point_color":
            return self.point_color
        else:
            raise KeyError(key)

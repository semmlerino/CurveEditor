"""
Point manipulation protocol definitions for the CurveEditor.

This module defines the protocol interfaces for point manipulation services,
handling modifications to curve point data.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Protocol


class PointOperation(Enum):
    """Types of point operations for history tracking."""

    ADD = auto()
    DELETE = auto()
    MOVE = auto()
    INTERPOLATE = auto()
    SMOOTH = auto()
    BATCH_EDIT = auto()


@dataclass
class PointChange:
    """Represents a change to point data."""

    operation: PointOperation
    indices: list[int]
    old_values: list[tuple[int, float, float]] | None = None
    new_values: list[tuple[int, float, float]] | None = None

    @property
    def is_reversible(self) -> bool:
        """Check if this change can be undone."""
        return self.old_values is not None


class PointManipulationProtocol(Protocol):
    """Protocol for point manipulation services."""

    def update_point_position(self, view: Any, idx: int, x: float, y: float) -> PointChange | None:
        """Update position of a single point."""
        ...

    def delete_selected_points(self, view: Any, indices: list[int]) -> PointChange | None:
        """Delete specified points."""
        ...

    def add_point(self, view: Any, frame: int, x: float, y: float) -> PointChange | None:
        """Add a new point at specified position."""
        ...

    def nudge_points(self, view: Any, indices: list[int], dx: float, dy: float) -> PointChange | None:
        """Nudge points by specified offset."""
        ...

    def interpolate_points(self, view: Any, indices: list[int]) -> PointChange | None:
        """Interpolate selected points."""
        ...

    def smooth_points(self, view: Any, indices: list[int], factor: float = 0.5) -> PointChange | None:
        """Smooth selected points."""
        ...

    def validate_point_position(self, view: Any, x: float, y: float) -> bool:
        """Validate if position is valid for a point."""
        ...

    def maintain_frame_order(self, view: Any, idx: int, new_frame: int) -> bool:
        """Check if changing frame maintains order."""
        ...

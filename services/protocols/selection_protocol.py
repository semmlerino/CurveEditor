"""
Selection management protocol definitions for the CurveEditor.

This module defines the protocol interfaces for selection services,
managing point selection state and operations.
"""

from dataclasses import dataclass
from typing import Any, Protocol

from PySide6.QtCore import QRect


@dataclass
class SelectionState:
    """Current selection state."""

    selected_indices: set[int]
    primary_index: int = -1  # Primary selection for focused operations

    @property
    def is_empty(self) -> bool:
        """Check if selection is empty."""
        return len(self.selected_indices) == 0

    @property
    def count(self) -> int:
        """Get number of selected items."""
        return len(self.selected_indices)

    def clear(self) -> None:
        """Clear all selections."""
        self.selected_indices.clear()
        self.primary_index = -1

    def add(self, index: int) -> None:
        """Add index to selection."""
        self.selected_indices.add(index)
        if self.primary_index == -1:
            self.primary_index = index

    def remove(self, index: int) -> None:
        """Remove index from selection."""
        self.selected_indices.discard(index)
        if self.primary_index == index:
            self.primary_index = min(self.selected_indices) if self.selected_indices else -1

    def toggle(self, index: int) -> bool:
        """Toggle index selection, returns True if now selected."""
        if index in self.selected_indices:
            self.remove(index)
            return False
        else:
            self.add(index)
            return True


class SelectionProtocol(Protocol):
    """Protocol for selection management services."""

    def find_point_at(self, view: Any, x: float, y: float, tolerance: float = 5.0) -> int:
        """Find point at given coordinates."""
        ...

    def select_point_by_index(self, view: Any, idx: int, add_to_selection: bool = False) -> bool:
        """Select a point by index."""
        ...

    def clear_selection(self, view: Any) -> None:
        """Clear all selections."""
        ...

    def select_points_in_rect(self, view: Any, rect: QRect) -> int:
        """Select all points within rectangle."""
        ...

    def select_all_points(self, view: Any) -> int:
        """Select all points."""
        ...

    def toggle_point_selection(self, view: Any, idx: int) -> bool:
        """Toggle selection of a point."""
        ...

    def get_selection_state(self, view: Any) -> SelectionState:
        """Get current selection state."""
        ...

    def set_selection_state(self, view: Any, state: SelectionState) -> None:
        """Set selection state."""
        ...

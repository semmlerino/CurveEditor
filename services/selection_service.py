"""
Selection management service for the CurveEditor.

This service manages point selection state and operations, including
single selection, multi-selection, and rectangle selection.
"""

import logging
from typing import Any

from PySide6.QtCore import QPointF, QRect

from services.protocols.selection_protocol import SelectionProtocol, SelectionState

logger = logging.getLogger(__name__)


class SelectionService(SelectionProtocol):
    """
    Manages point selection state and operations.

    This service is responsible for:
    - Finding points at screen positions
    - Managing single and multi-selection
    - Rectangle selection
    - Selection state persistence
    """

    def __init__(self):
        """Initialize the selection service."""
        self._selection_states: dict[int, SelectionState] = {}  # Per-view selection state

    def find_point_at(self, view: Any, x: float, y: float, tolerance: float = 5.0) -> int:
        """
        Find point at given coordinates.

        Args:
            view: The curve view widget
            x: X coordinate in curve space
            y: Y coordinate in curve space
            tolerance: Selection tolerance in pixels

        Returns:
            Index of point at position, or -1 if none found
        """
        # Delegate to view's findPointAt method if available
        if hasattr(view, "findPointAt"):
            return view.findPointAt(QPointF(x, y))
        return -1

    def select_point_by_index(self, view: Any, index: int, add_to_selection: bool = False) -> bool:
        """
        Select a point by its index.

        Args:
            view: The curve view widget
            index: Index of the point to select
            add_to_selection: Whether to add to existing selection

        Returns:
            True if selection was successful
        """
        if not hasattr(view, "points") or index < 0 or index >= len(view.points):
            return False

        # Initialize selection attributes if they don't exist
        if not hasattr(view, "selected_points"):
            view.selected_points = set()
        if not hasattr(view, "selected_point_idx"):
            view.selected_point_idx = -1

        # Update view's selection state directly for compatibility
        if add_to_selection:
            # Toggle selection if Ctrl is held
            if index in view.selected_points:
                view.selected_points.discard(index)
                # Update selected_point_idx to another selected point or -1
                if view.selected_points:
                    view.selected_point_idx = min(view.selected_points)
                else:
                    view.selected_point_idx = -1
            else:
                view.selected_points.add(index)
                view.selected_point_idx = index
        else:
            # Replace selection
            view.selected_points = {index}
            view.selected_point_idx = index

        # Emit signal if available
        if hasattr(view, "point_selected"):
            view.point_selected.emit(index)

        # Update view
        if hasattr(view, "update"):
            view.update()

        # Also update internal state
        view_id = id(view)
        if view_id not in self._selection_states:
            self._selection_states[view_id] = SelectionState(set())

        state = self._selection_states[view_id]
        state.selected_indices = set(view.selected_points)
        state.primary_index = view.selected_point_idx

        logger.debug(f"Selected point {index}, total selected: {len(state.selected_indices)}")
        return True

    def toggle_point_selection(self, view: Any, index: int) -> bool:
        """
        Toggle selection of a point.

        Args:
            view: The curve view widget
            index: Index of point to toggle

        Returns:
            True if selection changed
        """
        # Use select_point_by_index with add_to_selection=True for toggle behavior
        return self.select_point_by_index(view, index, add_to_selection=True)

    def clear_selection(self, view: Any) -> None:
        """
        Clear all selected points.

        Args:
            view: The curve view widget
        """
        # Initialize selection attributes if they don't exist
        if not hasattr(view, "selected_points"):
            view.selected_points = set()
        if not hasattr(view, "selected_point_idx"):
            view.selected_point_idx = -1

        # Clear view's selection state
        view.selected_points.clear()
        view.selected_point_idx = -1

        # Update view
        if hasattr(view, "update"):
            view.update()

        # Clear internal state
        view_id = id(view)
        if view_id in self._selection_states:
            self._selection_states[view_id] = SelectionState(set())

        logger.debug("Cleared selection")

    def select_points_in_rect(self, view: Any, rect: QRect) -> int:
        """
        Select all points within a rectangle.

        Args:
            view: The curve view widget
            rect: Selection rectangle in screen coordinates

        Returns:
            Number of points selected
        """
        if not hasattr(view, "points") or not hasattr(view, "get_current_transform"):
            return 0

        # Initialize selection attributes if they don't exist
        if not hasattr(view, "selected_points"):
            view.selected_points = set()
        if not hasattr(view, "selected_point_idx"):
            view.selected_point_idx = -1

        selected = set()
        transform = view.get_current_transform()
        if transform:
            for i, point in enumerate(view.points):
                # Handle different return formats from transform.data_to_screen
                try:
                    result = transform.data_to_screen(point[1], point[2])
                    if isinstance(result, tuple) and len(result) >= 2:
                        x, y = result[0], result[1]
                    else:
                        # Handle case where transform returns something else
                        continue

                    if rect.contains(int(x), int(y)):
                        selected.add(i)
                except (ValueError, TypeError, IndexError):
                    # Skip points that can't be transformed
                    continue

        # Update view's selection
        view.selected_points = selected
        if selected:
            view.selected_point_idx = min(selected)
        else:
            view.selected_point_idx = -1

        # Update view
        if hasattr(view, "update"):
            view.update()

        # Update internal state
        view_id = id(view)
        if view_id not in self._selection_states:
            self._selection_states[view_id] = SelectionState(set())

        state = self._selection_states[view_id]
        state.selected_indices = selected
        state.primary_index = view.selected_point_idx

        logger.debug(f"Rectangle selection: {len(selected)} points")
        return len(selected)

    def find_point_at_position(self, view: Any, x: float, y: float, tolerance: float = 5.0) -> int:
        """
        Find point at given position (alias for find_point_at).

        Args:
            view: The curve view widget
            x: X coordinate in curve space
            y: Y coordinate in curve space
            tolerance: Selection tolerance in pixels

        Returns:
            Index of point at position, or -1 if none found
        """
        return self.find_point_at(view, x, y, tolerance)

    def select_all(self, view: Any) -> int:
        """
        Select all points (alias for select_all_points).

        Args:
            view: The curve view widget

        Returns:
            Number of points selected
        """
        return self.select_all_points(view)

    def select_all_points(self, view: Any) -> int:
        """
        Select all points.

        Args:
            view: The curve view widget

        Returns:
            Number of points selected
        """
        if not view or not hasattr(view, "points"):
            return 0

        # Initialize selection attributes if they don't exist
        if not hasattr(view, "selected_points"):
            view.selected_points = set()
        if not hasattr(view, "selected_point_idx"):
            view.selected_point_idx = -1

        # Select all points in view
        num_points = len(view.points)
        if num_points > 0:
            view.selected_points = set(range(num_points))
            view.selected_point_idx = 0

            # Update view
            if hasattr(view, "update"):
                view.update()

            # Update internal state
            view_id = id(view)
            if view_id not in self._selection_states:
                self._selection_states[view_id] = SelectionState(set())

            state = self._selection_states[view_id]
            state.selected_indices = set(range(num_points))
            state.primary_index = 0

            logger.debug(f"Selected all {num_points} points")

        return num_points

    def get_selection_state(self, view: Any) -> SelectionState:
        """
        Get current selection state for a view.

        Args:
            view: The curve view widget

        Returns:
            Current selection state
        """
        # Sync with view's actual selection state if available
        if hasattr(view, "selected_points"):
            view_id = id(view)
            if view_id not in self._selection_states:
                self._selection_states[view_id] = SelectionState(set())

            state = self._selection_states[view_id]
            state.selected_indices = set(view.selected_points) if view.selected_points else set()
            state.primary_index = getattr(view, "selected_point_idx", -1)
            return state

        # Return empty state if view doesn't have selection
        view_id = id(view)
        if view_id not in self._selection_states:
            self._selection_states[view_id] = SelectionState(set())

        return self._selection_states[view_id]

    def set_selection_state(self, view: Any, state: SelectionState) -> None:
        """
        Set selection state for a view.

        Args:
            view: The curve view widget
            state: New selection state
        """
        view_id = id(view)
        self._selection_states[view_id] = state

        # Update view's selection if possible
        if hasattr(view, "selected_points"):
            view.selected_points = set(state.selected_indices)

        if hasattr(view, "selected_point_idx"):
            view.selected_point_idx = state.primary_index

        # Update view
        if hasattr(view, "update"):
            view.update()

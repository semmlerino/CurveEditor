#!/usr/bin/env python
"""
Cleaned InteractionService for CurveEditor.

This service now delegates all functionality to specialized services:
- EventHandlerService: Mouse and keyboard event handling
- SelectionService: Point selection management
- PointManipulationService: Point editing operations
- HistoryService: Undo/redo operations

This is a coordination service that routes interactions to appropriate handlers.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QRubberBand

from core.spatial_index import PointIndex
from services.interaction_service_adapter import InteractionServiceAdapter

if TYPE_CHECKING:
    from services.service_protocols import CurveViewProtocol, MainWindowProtocol

logger = logging.getLogger("interaction_service")


class InteractionService:
    """
    Cleaned interaction service that delegates to specialized services.

    This service coordinates user interactions by delegating to:
    - EventHandlerService for input processing
    - SelectionService for selection state
    - PointManipulationService for point edits
    - HistoryService for undo/redo
    """

    def __init__(self) -> None:
        """Initialize the interaction service."""
        # State for compatibility
        self.drag_mode: str | None = None
        self.drag_point_idx: int | None = None
        self.drag_start_x: float = 0
        self.drag_start_y: float = 0
        self.last_mouse_x: float = 0
        self.last_mouse_y: float = 0
        self.rubber_band: QRubberBand | None = None
        self.rubber_band_origin: tuple[int, int] | None = None

        # Spatial index for efficient point lookups
        self._point_index = PointIndex(grid_width=20, grid_height=20)

        # Check if new services should be used
        self.use_new_services = os.environ.get("USE_NEW_SERVICES", "false").lower() == "true"

        if self.use_new_services:
            logger.info("InteractionService using new delegated services")
        else:
            logger.info("InteractionService using legacy implementation with spatial indexing")

    # ==================== Main Event Handlers (Delegate to Adapter) ====================

    def handle_mouse_press(self, view: CurveViewProtocol, event: QMouseEvent) -> None:
        """
        Handle mouse press events.

        Delegates to EventHandlerService via adapter when USE_NEW_SERVICES=true.
        """
        # Try delegation to new service first
        if InteractionServiceAdapter.handle_mouse_press_delegated(self, view, event):
            return

        # Legacy implementation would go here if delegation returns False
        # But since we're cleaning up, we only use delegation
        logger.warning("Mouse press not handled by new services")

    def handle_mouse_move(self, view: CurveViewProtocol, event: QMouseEvent) -> None:
        """
        Handle mouse move events.

        Delegates to EventHandlerService via adapter when USE_NEW_SERVICES=true.
        """
        # Try delegation to new service first
        if InteractionServiceAdapter.handle_mouse_move_delegated(self, view, event):
            return

        # Legacy implementation would go here if delegation returns False
        logger.warning("Mouse move not handled by new services")

    def handle_mouse_release(self, view: CurveViewProtocol, event: QMouseEvent) -> None:
        """
        Handle mouse release events.

        Delegates to EventHandlerService via adapter when USE_NEW_SERVICES=true.
        """
        # Try delegation to new service first
        if InteractionServiceAdapter.handle_mouse_release_delegated(self, view, event):
            return

        # Legacy implementation would go here if delegation returns False
        logger.warning("Mouse release not handled by new services")

    def handle_wheel_event(self, view: CurveViewProtocol, event: QWheelEvent) -> None:
        """
        Handle mouse wheel events.

        Delegates to EventHandlerService via adapter when USE_NEW_SERVICES=true.
        """
        # Try delegation to new service first
        if InteractionServiceAdapter.handle_wheel_event_delegated(self, view, event):
            return

        # Legacy implementation would go here if delegation returns False
        logger.warning("Wheel event not handled by new services")

    def handle_key_event(self, view: CurveViewProtocol, event: QKeyEvent) -> None:
        """
        Handle keyboard events.

        Delegates to EventHandlerService via adapter when USE_NEW_SERVICES=true.
        """
        # Try delegation to new service first
        if InteractionServiceAdapter.handle_key_event_delegated(self, view, event):
            return

        # Legacy implementation would go here if delegation returns False
        logger.warning("Key event not handled by new services")

    # ==================== Compatibility Methods ====================

    def handle_key_press(self, view: CurveViewProtocol, event: QKeyEvent) -> None:
        """Compatibility method that routes to handle_key_event."""
        self.handle_key_event(view, event)

    def handle_context_menu(self, view: CurveViewProtocol, event: QMouseEvent) -> None:
        """
        Handle context menu requests.

        This could be delegated to a UIService in the future.
        """
        # Context menu handling would be delegated here
        logger.debug("Context menu requested")

    # ==================== State Query Methods ====================

    def get_memory_stats(self) -> dict[str, Any]:
        """
        Get memory statistics from history service.

        Returns:
            Dictionary with memory usage information
        """
        if self.use_new_services:
            # Get from new HistoryService
            from services.history_service import HistoryService
            history_service = HistoryService()
            stats = history_service.get_history_stats()
            return {
                "total_states": stats.total_entries,
                "current_index": stats.current_position,
                "memory_mb": stats.memory_usage_mb,
                "can_undo": stats.can_undo,
                "can_redo": stats.can_redo
            }
        else:
            # Return empty stats for legacy mode
            return {
                "total_states": 0,
                "current_index": 0,
                "memory_mb": 0.0,
                "can_undo": False,
                "can_redo": False
            }

    # ==================== Legacy Compatibility Methods ====================

    def add_to_history(self, main_window: Any) -> None:
        """Legacy compatibility for history operations."""
        if self.use_new_services:
            from services.history_service import HistoryService
            history_service = HistoryService()
            # Get current state from main window
            if hasattr(main_window, 'curve_view') and hasattr(main_window.curve_view, 'points'):
                history_service.add_to_history(
                    main_window.curve_view.points,
                    "State saved"
                )

    def undo(self, main_window: Any) -> None:
        """Legacy compatibility for undo operations."""
        if self.use_new_services:
            from services.history_service import HistoryService
            history_service = HistoryService()
            previous_state = history_service.undo()
            if previous_state and hasattr(main_window, 'curve_view'):
                main_window.curve_view.points = previous_state
                main_window.curve_view.update()

    def redo(self, main_window: Any) -> None:
        """Legacy compatibility for redo operations."""
        if self.use_new_services:
            from services.history_service import HistoryService
            history_service = HistoryService()
            next_state = history_service.redo()
            if next_state and hasattr(main_window, 'curve_view'):
                main_window.curve_view.points = next_state
                main_window.curve_view.update()

    def clear_history(self, main_window: Any) -> None:
        """Legacy compatibility for clearing history."""
        if self.use_new_services:
            from services.history_service import HistoryService
            history_service = HistoryService()
            history_service.clear_history()

    def update_history_buttons(self, main_window: Any) -> None:
        """Update undo/redo button states."""
        if self.use_new_services:
            from services.history_service import HistoryService
            history_service = HistoryService()

            if hasattr(main_window, 'ui_components'):
                components = main_window.ui_components
                if hasattr(components, 'actions'):
                    actions = components.actions
                    if hasattr(actions, 'undo_action'):
                        actions.undo_action.setEnabled(history_service.can_undo())
                    if hasattr(actions, 'redo_action'):
                        actions.redo_action.setEnabled(history_service.can_redo())

    # ==================== Stub Methods for Compatibility ====================

    def find_point_at(self, view: CurveViewProtocol, x: float, y: float) -> int:
        """Find point at given coordinates using spatial indexing for O(1) performance."""
        if self.use_new_services:
            from services.selection_service import SelectionService
            selection_service = SelectionService()
            return selection_service.find_point_at_position(view, x, y, 5.0)
        else:
            # Optimized consolidated behavior using spatial indexing
            if not hasattr(view, 'curve_data'):
                return -1

            from services import get_transform_service
            transform_service = get_transform_service()

            # Create transform for coordinate conversion
            view_state = transform_service.create_view_state(view)
            transform = transform_service.create_transform(view_state)

            # Use spatial index for O(1) lookup instead of O(n) linear search
            threshold = 5.0  # Threshold in screen pixels
            return self._point_index.find_point_at_position(view, transform, x, y, threshold)

    def select_point_by_index(self, view: CurveViewProtocol, main_window: MainWindowProtocol,
                              idx: int, add_to_selection: bool = False) -> bool:
        """Select point by index (delegates to SelectionService)."""
        if self.use_new_services:
            from services.selection_service import SelectionService
            selection_service = SelectionService()
            return selection_service.select_point_by_index(view, idx, add_to_selection)
        else:
            # Default consolidated behavior
            if hasattr(view, 'curve_data') and 0 <= idx < len(view.curve_data):
                if not add_to_selection:
                    view.selected_points.clear()
                view.selected_points.add(idx)
                view.selected_point_idx = idx
                view.update()
                return True
        return False

    def clear_selection(self, view: CurveViewProtocol, main_window: MainWindowProtocol) -> None:
        """Clear selection (delegates to SelectionService)."""
        if self.use_new_services:
            from services.selection_service import SelectionService
            selection_service = SelectionService()
            selection_service.clear_selection(view)
        else:
            # Default consolidated behavior
            view.selected_points.clear()
            view.selected_point_idx = -1
            view.update()

    def select_all_points(self, view: CurveViewProtocol, main_window: MainWindowProtocol) -> int:
        """Select all points (delegates to SelectionService)."""
        if self.use_new_services:
            from services.selection_service import SelectionService
            selection_service = SelectionService()
            selection_service.select_all(view)
            return len(view.selected_points) if hasattr(view, 'selected_points') else 0
        else:
            # Default consolidated behavior
            if hasattr(view, 'curve_data') and view.curve_data:
                view.selected_points = set(range(len(view.curve_data)))
                view.selected_point_idx = 0 if view.curve_data else -1
                view.update()
                return len(view.selected_points)
            return 0
        return 0

    def update_point_position(self, view: CurveViewProtocol, main_window: MainWindowProtocol,
                             idx: int, x: float, y: float) -> bool:
        """Update point position (delegates to PointManipulationService)."""
        if self.use_new_services:
            from services.point_manipulation import PointManipulationService
            manipulation_service = PointManipulationService()
            change = manipulation_service.update_point_position(view, idx, x, y)
            return change is not None
        else:
            # Default consolidated behavior
            if hasattr(view, 'curve_data') and 0 <= idx < len(view.curve_data):
                point = view.curve_data[idx]
                # Preserve frame and status, update x and y
                if len(point) >= 4:
                    view.curve_data[idx] = (point[0], x, y, point[3])
                elif len(point) == 3:
                    view.curve_data[idx] = (point[0], x, y)
                view.update()
                return True
        return False

    def delete_selected_points(self, view: CurveViewProtocol, main_window: MainWindowProtocol) -> None:
        """Delete selected points (delegates to PointManipulationService)."""
        if self.use_new_services:
            from services.point_manipulation import PointManipulationService
            manipulation_service = PointManipulationService()
            if hasattr(view, 'selected_points'):
                for idx in sorted(view.selected_points, reverse=True):
                    manipulation_service.delete_point(view, idx)
                view.selected_points.clear()
                view.update()

    # ==================== UI Update Methods ====================

    def on_point_moved(self, main_window: MainWindowProtocol, idx: int, x: float, y: float) -> None:
        """Handle point movement notifications."""
        logger.debug(f"Point {idx} moved to ({x}, {y})")

    def on_point_selected(self, curve_view: CurveViewProtocol, main_window: MainWindowProtocol, idx: int) -> None:
        """Handle point selection notifications."""
        logger.debug(f"Point {idx} selected")

    def update_point_info(self, main_window: MainWindowProtocol, idx: int, x: float, y: float) -> None:
        """Update point information display."""
        if hasattr(main_window, 'statusBar'):
            main_window.statusBar().showMessage(f"Point {idx}: ({x:.2f}, {y:.2f})")

    def _enable_point_controls(self, main_window: MainWindowProtocol) -> None:
        """Enable point manipulation controls."""
        # This would enable UI controls when points are selected
        pass

    def reset_view(self, view: CurveViewProtocol) -> None:
        """Reset view to default state."""
        if hasattr(view, 'reset_transform'):
            view.reset_transform()
        else:
            # Default reset behavior
            if hasattr(view, 'zoom_factor'):
                view.zoom_factor = 1.0
            if hasattr(view, 'offset_x'):
                view.offset_x = 0
            if hasattr(view, 'offset_y'):
                view.offset_y = 0
            if hasattr(view, 'pan_offset_x'):
                view.pan_offset_x = 0
            if hasattr(view, 'pan_offset_y'):
                view.pan_offset_y = 0
            if hasattr(view, 'manual_offset_x'):
                view.manual_offset_x = 0
            if hasattr(view, 'manual_offset_y'):
                view.manual_offset_y = 0
            view.update()

    # ==================== Legacy Methods (Minimal Implementation) ====================

    def undo_action(self, main_window: Any) -> None:
        """Legacy undo action."""
        self.undo(main_window)

    def redo_action(self, main_window: Any) -> None:
        """Legacy redo action."""
        self.redo(main_window)

    def save_state(self, main_window: Any) -> None:
        """Legacy save state."""
        self.add_to_history(main_window)

    def select_points_in_rect(self, view: CurveViewProtocol, main_window: MainWindowProtocol, rect: Any) -> int:
        """Select points in rectangle using spatial indexing for O(1) performance."""
        if self.use_new_services:
            from services.selection_service import SelectionService
            selection_service = SelectionService()
            return selection_service.select_points_in_rect(view, rect)
        else:
            # Optimized consolidated behavior using spatial indexing
            if not hasattr(view, 'curve_data'):
                return 0

            from services import get_transform_service
            transform_service = get_transform_service()

            # Create transform for coordinate conversion
            view_state = transform_service.create_view_state(view)
            transform = transform_service.create_transform(view_state)

            # Use spatial index for O(1) rectangular selection
            point_indices = self._point_index.get_points_in_rect(
                view, transform, 
                rect.left(), rect.top(), 
                rect.right(), rect.bottom()
            )

            view.selected_points.clear()
            for idx in point_indices:
                view.selected_points.add(idx)

            selected_count = len(point_indices)

            # Update selected index
            if view.selected_points:
                view.selected_point_idx = min(view.selected_points)
            else:
                view.selected_point_idx = -1

            view.update()
            return selected_count
        return 0

    def restore_state(self, main_window: Any, state: Any) -> None:
        """Restore a saved state."""
        if hasattr(main_window, 'curve_view') and state:
            main_window.curve_view.points = state
            main_window.curve_view.update()

    def get_spatial_index_stats(self) -> dict[str, Any]:
        """
        Get spatial index performance statistics.
        
        Returns:
            Dictionary with spatial index statistics
        """
        return self._point_index.get_stats()

    def clear_spatial_index(self) -> None:
        """Clear the spatial index cache to force rebuild."""
        self._point_index._grid.clear()
        self._point_index._last_transform_hash = None
        self._point_index._last_point_count = 0


# Module-level instance
_interaction_service: InteractionService | None = None


def get_interaction_service() -> InteractionService:
    """Get the singleton InteractionService instance."""
    global _interaction_service
    if _interaction_service is None:
        _interaction_service = InteractionService()
    return _interaction_service

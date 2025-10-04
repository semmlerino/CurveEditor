#!/usr/bin/env python
"""
Consolidated InteractionService for CurveEditor.

This service handles all user interactions including:
- Mouse and keyboard event handling
- Point selection management
- Point editing operations
- Undo/redo history management
- Spatial indexing for efficient point lookups

This is the consolidated implementation without Sprint 8 delegation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QCoreApplication, QThread
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QRubberBand

from core.models import PointSearchResult
from core.spatial_index import PointIndex
from core.type_aliases import SearchMode
from stores.application_state import get_application_state

if TYPE_CHECKING:
    from PySide6.QtCore import QRect

    from core.commands.command_manager import CommandManager
    from services.service_protocols import CurveViewProtocol, MainWindowProtocol
    from services.transform_service import TransformService

from core.logger_utils import get_logger

logger = get_logger("interaction_service")

# Lazy singleton access to avoid circular import
_transform_service: TransformService | None = None


def _get_transform_service() -> TransformService:
    """Get transform service singleton (lazy initialization)."""
    global _transform_service
    if _transform_service is None:
        # Import directly to avoid circular import with services/__init__
        from services.transform_service import TransformService

        _transform_service = TransformService()
    return _transform_service


class InteractionService:
    """
    Consolidated interaction service for handling all user interactions.

    This service manages:
    - Mouse and keyboard event processing
    - Point selection and manipulation
    - Undo/redo history
    - Spatial indexing for efficient point queries
    """

    def __init__(self) -> None:
        """Initialize the interaction service."""
        # ApplicationState integration (Week 6)
        self._app_state = get_application_state()

        # State for compatibility
        self.drag_mode: str | None = None
        self.drag_point_idx: int | None = None
        self.drag_start_x: float = 0
        self.drag_start_y: float = 0
        self.last_mouse_x: float = 0
        self.last_mouse_y: float = 0
        self.rubber_band: QRubberBand | None = None
        self.rubber_band_origin: tuple[int, int] | None = None

        # Spatial index for efficient point lookups (uses adaptive grid sizing)
        self._point_index: PointIndex = PointIndex()

        # Command-based history management (lazy initialization to avoid cycles)
        self._command_manager: CommandManager | None = None

        # Legacy history state (for backward compatibility)
        self._history: list[dict[str, object]] = []
        self._current_index: int = -1
        self._max_history_size: int = 100

        # Track original positions for drag operations
        self._drag_original_positions: dict[int, tuple[float, float]] | None = None

        logger.info("InteractionService initialized with ApplicationState, command manager and spatial indexing")

    def _assert_main_thread(self) -> None:
        """
        Verify method called from main thread (matches ApplicationState pattern).

        Thread Safety Contract:
        - ALL InteractionService methods must be called from main Qt thread
        - Worker threads should emit signals, handlers update state
        - Matches ApplicationState threading pattern

        Raises:
            RuntimeError: If called from non-main thread
        """
        current = QThread.currentThread()
        app = QCoreApplication.instance()
        if app is not None:
            main = app.thread()
            if current != main:
                raise RuntimeError(
                    f"InteractionService must be called from main thread only "
                    f"(called from {current}, main is {main})"
                )

    @property
    def command_manager(self) -> CommandManager:
        """Lazy initialization of CommandManager to avoid circular imports."""
        if self._command_manager is None:
            from core.commands.command_manager import CommandManager

            self._command_manager = CommandManager(max_history_size=100)
        return self._command_manager

    # ==================== Main Event Handlers (Delegate to Adapter) ====================

    def handle_mouse_press(self, view: CurveViewProtocol, event: QMouseEvent) -> None:
        """Handle mouse press events."""
        self._handle_mouse_press_consolidated(view, event)

    def handle_mouse_move(self, view: CurveViewProtocol, event: QMouseEvent) -> None:
        """Handle mouse move events."""
        self._handle_mouse_move_consolidated(view, event)

    def handle_mouse_release(self, view: CurveViewProtocol, event: QMouseEvent) -> None:
        """Handle mouse release events."""
        self._handle_mouse_release_consolidated(view, event)

    def handle_wheel_event(self, view: CurveViewProtocol, event: QWheelEvent) -> None:
        """Handle mouse wheel events."""
        self._handle_wheel_event_consolidated(view, event)

    def handle_key_event(self, view: CurveViewProtocol, event: QKeyEvent) -> None:
        """Handle keyboard events."""
        self._handle_key_event_consolidated(view, event)

    # ==================== Consolidated Implementation Methods ====================

    def _handle_mouse_press_consolidated(self, view: CurveViewProtocol, event: QMouseEvent) -> None:
        """Consolidated mouse press handling for default mode."""
        from PySide6.QtCore import QPoint, QRect, QSize, Qt
        from PySide6.QtWidgets import QRubberBand

        pos_f = event.position()
        # Convert to QPoint for QRect operations (handles both QPoint and QPointF from mocks)
        pos = pos_f if isinstance(pos_f, QPoint) else pos_f.toPoint()

        # Check for point selection first
        point_result = self.find_point_at(view, pos.x(), pos.y())

        if point_result.found:
            # Point clicked
            point_idx = point_result.index
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # Toggle selection (no drag for Ctrl+click)
                # Get current selection
                current_selection = view.selected_points if view.selected_points else set()
                # Toggle the point
                if point_idx in current_selection:
                    # Deselecting
                    current_selection = current_selection - {point_idx}
                    view.selected_points = current_selection
                    # Set selected_point_idx to first remaining, or -1 if none
                    view.selected_point_idx = min(current_selection) if current_selection else -1
                else:
                    # Selecting
                    current_selection = current_selection | {point_idx}
                    view.selected_points = current_selection
                    view.selected_point_idx = point_idx
            elif event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                # Range selection (simplified - just add to selection, no drag)
                current_selection = view.selected_points if view.selected_points else set()
                # Add point to selection
                view.selected_points = current_selection | {point_idx}
                view.selected_point_idx = point_idx
            else:
                # Single selection - start drag for normal click
                view.selected_points = {point_idx}
                view.selected_point_idx = point_idx

                # Start drag - capture original positions for undo
                view.drag_active = True
                view.last_drag_pos = pos
                self.drag_point_idx = point_idx

                # Capture original positions of all selected points
                self._drag_original_positions = {}
                if view.selected_points:
                    # Use ApplicationState for active curve data (Week 6)
                    active_curve_data = self._app_state.get_curve_data()  # No param = active curve
                    for idx in view.selected_points:
                        if 0 <= idx < len(active_curve_data):
                            point = active_curve_data[idx]
                            self._drag_original_positions[idx] = (point[1], point[2])

        elif event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                # Start rectangle selection
                # rubber_band is Optional in CurveViewProtocol
                if view.rubber_band is None:
                    # Create rubber band with parent widget workaround
                    parent_widget = getattr(view, "parentWidget", lambda: None)() or None
                    view.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, parent_widget)
                view.rubber_band_origin = pos
                view.rubber_band_active = True
                view.rubber_band.setGeometry(QRect(pos, QSize()))
                view.rubber_band.show()
            else:
                # Clear selection and start pan
                view.selected_points = set()
                view.selected_point_idx = -1
                view.pan_active = True
                view.last_pan_pos = pos
                view.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() == Qt.MouseButton.MiddleButton:
            # Middle button always pans
            view.pan_active = True
            view.last_pan_pos = pos
            view.setCursor(Qt.CursorShape.ClosedHandCursor)

        view.update()

    def _handle_mouse_move_consolidated(self, view: CurveViewProtocol, event: QMouseEvent) -> None:
        """Consolidated mouse move handling for default mode."""
        self._assert_main_thread()

        from PySide6.QtCore import QPoint, QRect

        pos_f = event.position()
        # Convert to QPoint for QRect operations (handles both QPoint and QPointF from mocks)
        pos = pos_f if isinstance(pos_f, QPoint) else pos_f.toPoint()

        # drag_active is bool, last_drag_pos is Optional in CurveViewProtocol
        if view.drag_active and view.last_drag_pos is not None:
            # Drag selected points
            # selected_points is defined in CurveViewProtocol
            if view.selected_points:
                delta_x = pos.x() - view.last_drag_pos.x()
                delta_y = pos.y() - view.last_drag_pos.y()

                # Convert screen delta to curve coordinates
                transform_service = _get_transform_service()
                view_state = transform_service.create_view_state(view)
                transform = transform_service.create_transform_from_view_state(view_state)

                # Transform has a single scale, not scale_x/scale_y
                curve_delta_x = delta_x / transform.scale
                # Y-FLIP BUG FIX: Respect view.flip_y_axis
                y_multiplier = -1.0 if view.flip_y_axis else 1.0
                curve_delta_y = (delta_y * y_multiplier) / transform.scale

                # Use ApplicationState with batch mode for performance (Week 6)
                active_curve_name = self._app_state.active_curve
                if active_curve_name:
                    active_curve_data = self._app_state.get_curve_data()

                    # Move all selected points
                    for idx in view.selected_points:
                        if 0 <= idx < len(active_curve_data):
                            point = active_curve_data[idx]
                            new_x = point[1] + curve_delta_x
                            new_y = point[2] + curve_delta_y
                            # Update via view.curve_data for real-time display during drag
                            # (ApplicationState will be updated via command on release)
                            if len(point) >= 4:
                                view.curve_data[idx] = (point[0], new_x, new_y, point[3])
                            else:
                                view.curve_data[idx] = (point[0], new_x, new_y)

            view.last_drag_pos = pos

        # pan_active is bool, last_pan_pos is Optional in CurveViewProtocol
        elif view.pan_active and view.last_pan_pos is not None:
            # Pan the view
            delta_x = pos.x() - view.last_pan_pos.x()
            delta_y = pos.y() - view.last_pan_pos.y()

            # Pan the view if supported
            pan_method = getattr(view, "pan", None)
            if pan_method is not None and callable(pan_method):
                pan_method(delta_x, delta_y)
            view.last_pan_pos = pos

        # rubber_band_active is bool, rubber_band_origin is QPoint in CurveViewProtocol
        elif view.rubber_band_active:
            # Update rubber band rectangle
            # rubber_band is Optional in CurveViewProtocol
            if view.rubber_band is not None:
                # rubber_band_origin was set as QPoint in mouse press, pos is also QPoint
                origin = view.rubber_band_origin
                origin_pt = origin if isinstance(origin, QPoint) else origin.toPoint()
                rect = QRect(origin_pt, pos).normalized()
                view.rubber_band.setGeometry(rect)

        view.update()

    def _handle_mouse_release_consolidated(self, view: CurveViewProtocol, event: QMouseEvent) -> None:
        """Consolidated mouse release handling for default mode."""

        # drag_active is bool in CurveViewProtocol
        if view.drag_active:
            # End dragging - create command for undo/redo
            view.drag_active = False
            view.last_drag_pos = None
            self.drag_point_idx = None

            # Create command if points were actually moved
            if self._drag_original_positions and view.main_window is not None:
                from core.commands.curve_commands import BatchMoveCommand

                # Collect the moves using ApplicationState (Week 6)
                active_curve_data = self._app_state.get_curve_data()
                moves = []
                for idx, old_pos in self._drag_original_positions.items():
                    if 0 <= idx < len(active_curve_data):
                        point = active_curve_data[idx]
                        new_pos = (point[1], point[2])
                        if old_pos != new_pos:  # Only add if actually moved
                            moves.append((idx, old_pos, new_pos))

                # Execute command through command manager if points were moved
                if moves:
                    command = BatchMoveCommand(
                        description=f"Move {len(moves)} point{'s' if len(moves) > 1 else ''}",
                        moves=moves,
                    )
                    # The points have already been moved during dragging,
                    # so we mark the command as executed and add it to history
                    command.executed = True
                    self.command_manager.add_executed_command(command, cast(MainWindowProtocol, view.main_window))

            # Clear the tracked positions
            self._drag_original_positions = None

        # pan_active is bool in CurveViewProtocol
        elif view.pan_active:
            # End panning
            view.pan_active = False
            view.last_pan_pos = None
            view.unsetCursor()

        # rubber_band_active is bool in CurveViewProtocol
        elif view.rubber_band_active:
            # Finish rectangle selection
            # rubber_band is Optional in CurveViewProtocol
            if view.rubber_band is not None:
                rect = view.rubber_band.geometry()

                # Find points in rectangle using ApplicationState (Week 6)
                selected_count = 0
                active_curve_data = self._app_state.get_curve_data()
                if active_curve_data:
                    transform_service = _get_transform_service()
                    view_state = transform_service.create_view_state(view)
                    transform = transform_service.create_transform_from_view_state(view_state)

                    if not view.selected_points:
                        view.selected_points = set()

                    for i, point in enumerate(active_curve_data):
                        screen_x, screen_y = transform.data_to_screen(point[1], point[2])
                        if rect.contains(int(screen_x), int(screen_y)):
                            view.selected_points.add(i)
                            selected_count += 1

                # Hide rubber band
                view.rubber_band.hide()
                view.rubber_band_active = False

                # Update history if points were selected
                if selected_count > 0 and view.main_window is not None:
                    self.update_history_buttons(cast(MainWindowProtocol, view.main_window))

        view.update()

    def _handle_wheel_event_consolidated(self, view: CurveViewProtocol, event: QWheelEvent) -> None:
        """Consolidated wheel event handling for default mode."""
        # Zoom around mouse position
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9

        # Zoom the view if supported
        zoom_method = getattr(view, "zoom", None)
        if zoom_method is not None and callable(zoom_method):
            center = event.position()
            zoom_method(zoom_factor, center)
            view.update()

    def _handle_key_event_consolidated(self, view: CurveViewProtocol, event: QKeyEvent) -> None:
        """Consolidated key event handling for default mode."""
        from PySide6.QtCore import Qt

        key = event.key()

        if key == Qt.Key.Key_Delete or key == Qt.Key.Key_Backspace:
            # Delete selected points using command for undo/redo
            # selected_points is defined in CurveViewProtocol
            if view.selected_points and view.main_window is not None:
                from core.commands.curve_commands import DeletePointsCommand

                # Collect points to delete using ApplicationState (Week 6)
                active_curve_data = self._app_state.get_curve_data()
                indices = list(view.selected_points)
                deleted_points = []
                for idx in sorted(indices):
                    if 0 <= idx < len(active_curve_data):
                        deleted_points.append((idx, active_curve_data[idx]))

                if deleted_points:
                    # Create and execute delete command
                    command = DeletePointsCommand(
                        description=f"Delete {len(deleted_points)} point{'s' if len(deleted_points) > 1 else ''}",
                        indices=indices,
                        deleted_points=deleted_points,
                    )

                    # Execute the command through the command manager
                    self.command_manager.execute_command(command, cast(MainWindowProtocol, view.main_window))

                    # Clear selection
                    view.selected_points.clear()
                    view.selected_point_idx = -1

                # Note: No need to add_to_history - command manager handles it

        elif key == Qt.Key.Key_A and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            # Select all points using ApplicationState (Week 6)
            active_curve_data = self._app_state.get_curve_data()
            if active_curve_data:
                view.selected_points = set(range(len(active_curve_data)))
                view.selected_point_idx = 0
                # main_window is defined in CurveViewProtocol
            if view.main_window is not None:
                self.update_history_buttons(cast(MainWindowProtocol, view.main_window))

        elif key == Qt.Key.Key_Escape:
            # Clear selection
            view.selected_points = set()
            view.selected_point_idx = -1
            # main_window is defined in CurveViewProtocol
            if view.main_window is not None:
                self.update_history_buttons(cast(MainWindowProtocol, view.main_window))

        elif key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            # Nudge selected points
            # selected_points is defined in CurveViewProtocol
            if view.selected_points and view.main_window is not None:
                from core.commands.curve_commands import BatchMoveCommand

                nudge_distance = 1.0
                delta_x = (
                    nudge_distance if key == Qt.Key.Key_Right else (-nudge_distance if key == Qt.Key.Key_Left else 0)
                )
                delta_y = nudge_distance if key == Qt.Key.Key_Up else (-nudge_distance if key == Qt.Key.Key_Down else 0)

                # Convert to curve coordinates
                transform_service = _get_transform_service()
                view_state = transform_service.create_view_state(view)
                transform = transform_service.create_transform_from_view_state(view_state)

                curve_delta_x = delta_x / transform.scale
                curve_delta_y = -delta_y / transform.scale  # Invert Y

                # Collect moves for command using ApplicationState (Week 6)
                active_curve_data = self._app_state.get_curve_data()
                moves = []
                for idx in view.selected_points:
                    if 0 <= idx < len(active_curve_data):
                        point = active_curve_data[idx]
                        old_pos = (point[1], point[2])
                        new_pos = (point[1] + curve_delta_x, point[2] + curve_delta_y)
                        moves.append((idx, old_pos, new_pos))

                if moves:
                    # Create and execute move command
                    command = BatchMoveCommand(
                        description=f"Nudge {len(moves)} point{'s' if len(moves) > 1 else ''}",
                        moves=moves,
                    )
                    self.command_manager.execute_command(command, cast(MainWindowProtocol, view.main_window))
                    # Note: No need to add_to_history - command manager handles it

        view.update()

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

    def get_memory_stats(self) -> dict[str, object]:
        """
        Get memory statistics from history.

        Returns:
            Dictionary with memory usage information
        """
        import sys

        memory_mb = sum(sys.getsizeof(state) for state in self._history) / (1024 * 1024)
        return {
            "total_states": len(self._history),
            "current_index": self._current_index,
            "memory_mb": memory_mb,
            "can_undo": self.can_undo(),
            "can_redo": self.can_redo(),
        }

    # ==================== Legacy Compatibility Methods ====================

    def add_to_history(self, main_window_or_view: MainWindowProtocol, state: dict[str, object] | None = None) -> None:
        """
        Add current state to history.

        SPRINT 11.5 FIX: Support both signature patterns for compatibility:
        - Legacy: add_to_history(main_window)
        - New: add_to_history(view, state)

        Args:
            main_window_or_view: Either a MainWindow instance (legacy) or a view object (new)
            state: Optional state dictionary (for new signature)
        """
        import copy

        # Legacy signature: add_to_history(main_window)
        main_window = main_window_or_view

        # Extract the state to save
        history_state = {}

        # Get curve_data - prioritize ApplicationState (Week 6), then fall back to legacy locations
        active_curve_data = self._app_state.get_curve_data()
        if active_curve_data:
            # Convert lists to tuples for compression (as expected by tests)
            if active_curve_data and isinstance(active_curve_data[0], list):
                history_state["curve_data"] = [tuple(point) for point in active_curve_data]
            else:
                history_state["curve_data"] = copy.deepcopy(active_curve_data)
        # Legacy fallback - try multiple possible attributes
        elif main_window.curve_data is not None:
            curve_data = main_window.curve_data
            if curve_data and isinstance(curve_data[0], list):
                history_state["curve_data"] = [tuple(point) for point in curve_data]
            else:
                history_state["curve_data"] = copy.deepcopy(curve_data)
        elif main_window.curve_widget is not None and getattr(main_window.curve_widget, "curve_data", None) is not None:
            widget_curve_data = getattr(main_window.curve_widget, "curve_data")
            if (
                widget_curve_data
                and isinstance(widget_curve_data, list)
                and len(widget_curve_data) > 0
                and isinstance(widget_curve_data[0], list)
            ):
                history_state["curve_data"] = [tuple(point) for point in widget_curve_data]
            else:
                history_state["curve_data"] = copy.deepcopy(widget_curve_data)
        elif main_window.curve_view is not None and getattr(main_window.curve_view, "curve_data", None) is not None:
            view_curve_data = getattr(main_window.curve_view, "curve_data")
            if (
                view_curve_data
                and isinstance(view_curve_data, list)
                and len(view_curve_data) > 0
                and isinstance(view_curve_data[0], list)
            ):
                history_state["curve_data"] = [tuple(point) for point in view_curve_data]
            else:
                history_state["curve_data"] = copy.deepcopy(view_curve_data)
        else:
            logger.warning("Cannot extract curve data from main_window or ApplicationState")
            return

        # Get point_name
        point_name = getattr(main_window, "point_name", None)
        if point_name is not None:
            history_state["point_name"] = point_name

        # Get point_color
        point_color = getattr(main_window, "point_color", None)
        if point_color is not None:
            history_state["point_color"] = point_color

        # Check if main_window has history attributes for direct management
        # history is defined in MainWindowProtocol
        if main_window.history is not None:
            # Truncate future history if we're not at the end
            # history_index is defined in MainWindowProtocol
            if main_window.history_index < len(main_window.history) - 1:
                main_window.history = main_window.history[: main_window.history_index + 1]
            # Add state to main_window's history
            main_window.history.append(history_state)

            # Update history index
            # history_index is defined in MainWindowProtocol
            main_window.history_index = len(main_window.history) - 1

            # Enforce size limit
            max_history_size = getattr(main_window, "max_history_size", None)
            if max_history_size is not None:
                while len(main_window.history) > max_history_size:
                    main_window.history.pop(0)
                    # history_index is defined in MainWindowProtocol
                    main_window.history_index = max(0, main_window.history_index - 1)
        else:
            # Truncate future history if we're not at the end
            if self._current_index < len(self._history) - 1:
                self._history = self._history[: self._current_index + 1]

            # Use internal history
            self._history.append(history_state)
            self._current_index = len(self._history) - 1

            # Enforce size limit
            if len(self._history) > self._max_history_size:
                self._history.pop(0)
                self._current_index -= 1

        # Update button states
        self.update_history_buttons(main_window)

        # Notify workflow state service if available
        if (
            main_window.services is not None
            and getattr(main_window.services, "workflow_state", None) is not None
            and getattr(getattr(main_window.services, "workflow_state"), "on_data_modified", None) is not None
        ):
            try:
                getattr(main_window.services, "workflow_state").on_data_modified()
            except Exception:
                pass  # Ignore errors in workflow notification

        logger.debug("Added state to history")

    def _get_timestamp(self) -> float:
        """Get current timestamp."""
        import time

        return time.time()

    def undo(self, main_window: MainWindowProtocol) -> None:
        """Undo last operation - alias for undo_action."""
        logger.info("InteractionService.undo called")
        self.undo_action(main_window)

    def redo(self, main_window: MainWindowProtocol) -> None:
        """Redo next operation - alias for redo_action."""
        self.redo_action(main_window)

    def clear_history(self, main_window: MainWindowProtocol) -> None:
        """Clear all history."""
        self._history.clear()
        self._current_index = -1
        logger.debug("History cleared")
        self.update_history_buttons(main_window)

    def update_history_buttons(self, main_window: MainWindowProtocol) -> None:
        """Update undo/redo button states."""
        # Determine can_undo and can_redo based on history location
        if main_window.history is not None and main_window.history_index is not None:
            # Use main_window's history
            can_undo_val = main_window.history_index > 0
            can_redo_val = main_window.history_index < len(main_window.history) - 1
        else:
            # Use internal history
            can_undo_val = self.can_undo()
            can_redo_val = self.can_redo()

        # Update buttons via ui components
        ui = getattr(main_window, "ui", None)
        if ui is not None:
            undo_btn = getattr(ui, "undo_button", None)
            if undo_btn is not None:
                undo_btn.setEnabled(can_undo_val)

            redo_btn = getattr(ui, "redo_button", None)
            if redo_btn is not None:
                redo_btn.setEnabled(can_redo_val)

    def find_point_at(
        self, view: CurveViewProtocol, x: float, y: float, mode: SearchMode = "active"
    ) -> PointSearchResult:
        """
        Find point at screen coordinates with spatial indexing (64.7x speedup).

        Args:
            view: Curve view to search in
            x, y: Screen coordinates in pixels
            mode: Search behavior:
                - "active": Search active curve only (default, backward compatible)
                - "all_visible": Search all visible curves

        Returns:
            PointSearchResult with index and curve name

        Examples:
            # Single-curve (backward compatible):
            result = service.find_point_at(view, 100, 200)
            if result.found:
                print(f"Point {result.index}")

            # Multi-curve:
            result = service.find_point_at(view, 100, 200, mode="all_visible")
            if result.found:
                print(f"Point {result.index} in {result.curve_name}")
        """
        self._assert_main_thread()

        if mode == "active":
            # Single-curve mode (backward compatible)
            active_curve = self._app_state.active_curve
            if active_curve is None:
                return PointSearchResult(index=-1, curve_name=None)

            # Use spatial index for O(1) lookup
            active_curve_data = self._app_state.get_curve_data(active_curve)
            if not active_curve_data:
                return PointSearchResult(index=-1, curve_name=None)

            transform_service = _get_transform_service()
            view_state = transform_service.create_view_state(view)
            transform = transform_service.create_transform_from_view_state(view_state)

            threshold = 5.0
            # Updated API: curve_data is now first parameter (Critical Fix #2)
            idx = self._point_index.find_point_at_position(active_curve_data, transform, x, y, threshold, view)
            return PointSearchResult(index=idx, curve_name=active_curve if idx >= 0 else None, distance=0.0)

        elif mode == "all_visible":
            # Multi-curve mode - search all visible curves
            all_curve_names = self._app_state.get_all_curve_names()
            visible_curves = [
                name for name in all_curve_names if self._app_state.get_curve_metadata(name).get("visible", True)
            ]

            best_match: PointSearchResult | None = None
            threshold = 5.0

            transform_service = _get_transform_service()
            view_state = transform_service.create_view_state(view)
            transform = transform_service.create_transform_from_view_state(view_state)

            for curve_name in visible_curves:
                curve_data = self._app_state.get_curve_data(curve_name)
                if not curve_data:
                    continue

                # Search this curve with clean API (no mutation - Critical Fix #2)
                idx = self._point_index.find_point_at_position(curve_data, transform, x, y, threshold, view)

                if idx >= 0:
                    # Calculate distance to find best match
                    point = curve_data[idx]
                    data_x, data_y = float(point[1]), float(point[2])
                    screen_x, screen_y = transform.data_to_screen(data_x, data_y)
                    distance = ((screen_x - x) ** 2 + (screen_y - y) ** 2) ** 0.5

                    if best_match is None or distance < best_match.distance:
                        best_match = PointSearchResult(idx, curve_name, distance)

            return best_match or PointSearchResult(index=-1, curve_name=None)

        else:
            raise ValueError(f"Invalid search mode: {mode}")

    def find_point_at_position(self, view: CurveViewProtocol, x: float, y: float, tolerance: float = 5.0) -> int:
        """Find point at position with tolerance parameter."""
        # Use ApplicationState for active curve data (Week 6)
        active_curve_data = self._app_state.get_curve_data()
        if not active_curve_data:
            return -1

        transform_service = _get_transform_service()

        # Create transform for coordinate conversion
        view_state = transform_service.create_view_state(view)
        transform = transform_service.create_transform_from_view_state(view_state)

        # Use spatial index with specified tolerance (updated API - Critical Fix #2)
        return self._point_index.find_point_at_position(active_curve_data, transform, x, y, tolerance, view)

    def select_point_by_index(
        self,
        view: CurveViewProtocol,
        main_window: MainWindowProtocol,
        idx: int,
        add_to_selection: bool = False,
        curve_name: str | None = None,
    ) -> bool:
        """
        Select point by index in specified curve.

        Args:
            view: Curve view
            main_window: Main window instance
            idx: Point index to select
            add_to_selection: If True, add to existing selection. If False, replace.
            curve_name: Curve to select point in. None = active curve.

        Returns:
            True if point was selected, False if invalid index
        """
        self._assert_main_thread()
        if curve_name is None:
            curve_name = self._app_state.active_curve
        if curve_name is None:
            return False

        curve_data = self._app_state.get_curve_data(curve_name)
        if 0 <= idx < len(curve_data):
            if add_to_selection:
                self._app_state.add_to_selection(curve_name, idx)
            else:
                self._app_state.set_selection(curve_name, {idx})

            # Update view for backward compatibility
            view.selected_points.add(idx)
            view.selected_point_idx = idx
            view.update()
            return True
        return False

    def clear_selection(
        self, view: CurveViewProtocol, main_window: MainWindowProtocol, curve_name: str | None = None
    ) -> None:
        """
        Clear selection for specified curve.

        Args:
            view: Curve view
            main_window: Main window instance
            curve_name: Curve to clear selection for. None = active curve.

        Examples:
            # Single-curve (backward compatible):
            service.clear_selection(view, main_window)

            # Multi-curve - clear specific curve:
            service.clear_selection(view, main_window, curve_name="pp56_TM_138G")
        """
        self._assert_main_thread()

        if curve_name is None:
            curve_name = self._app_state.active_curve

        # Update ApplicationState if we have a curve
        if curve_name is not None:
            self._app_state.clear_selection(curve_name)

        # Always update view for backward compatibility (even if no active curve)
        view.selected_points.clear()
        view.selected_point_idx = -1
        view.update()

    def select_all_points(
        self, view: CurveViewProtocol, main_window: MainWindowProtocol, curve_name: str | None = None
    ) -> int:
        """
        Select all points in specified curve.

        Args:
            view: Curve view
            main_window: Main window instance
            curve_name: Curve to select all points in. None = active curve.

        Returns:
            Number of points selected

        Examples:
            # Single-curve (backward compatible):
            count = service.select_all_points(view, main_window)

            # Multi-curve - select all in specific curve:
            count = service.select_all_points(view, main_window, curve_name="pp56_TM_138G")
        """
        self._assert_main_thread()

        if curve_name is None:
            curve_name = self._app_state.active_curve
        if curve_name is None:
            return 0

        # Get curve data for specified curve
        curve_data = self._app_state.get_curve_data(curve_name)
        if not curve_data:
            return 0

        # Create selection of all indices
        all_indices = set(range(len(curve_data)))

        # Update ApplicationState
        self._app_state.set_selection(curve_name, all_indices)

        # Update view for backward compatibility
        view.selected_points = all_indices
        view.selected_point_idx = 0
        view.update()

        return len(all_indices)

    def update_point_position(
        self,
        view: CurveViewProtocol,
        main_window: MainWindowProtocol,
        idx: int,
        x: float,
        y: float,
        curve_name: str | None = None,
    ) -> bool:
        """
        Update point position in curve.

        Args:
            view: Curve view
            main_window: Main window instance
            idx: Point index
            x: New X coordinate
            y: New Y coordinate
            curve_name: Curve containing point. None = active curve.

        Returns:
            True if point was updated, False if invalid index
        """
        self._assert_main_thread()
        if curve_name is None:
            curve_name = self._app_state.active_curve
        if curve_name is None:
            return False

        curve_data = self._app_state.get_curve_data(curve_name)
        if 0 <= idx < len(curve_data):
            point = curve_data[idx]
            # Update via ApplicationState (signals emitted automatically)
            from core.models import CurvePoint, PointStatus

            status_value = point[3] if len(point) >= 4 else "normal"
            status = PointStatus.from_legacy(status_value)
            updated_point = CurvePoint(frame=point[0], x=x, y=y, status=status)
            self._app_state.update_point(curve_name, idx, updated_point)

            # Update view for backward compatibility
            if len(point) >= 4:
                view.curve_data[idx] = (point[0], x, y, point[3])
            elif len(point) == 3:
                view.curve_data[idx] = (point[0], x, y)
            view.update()
            return True
        return False

    def delete_selected_points(
        self, view: CurveViewProtocol, main_window: MainWindowProtocol, curve_name: str | None = None
    ) -> None:
        """
        Delete selected points using DeletePointsCommand.

        Args:
            view: Curve view
            main_window: Main window instance
            curve_name: Curve containing points to delete. None = active curve.

        Examples:
            # Single-curve (backward compatible):
            service.delete_selected_points(view, main_window)

            # Multi-curve - delete from specific curve:
            service.delete_selected_points(view, main_window, curve_name="pp56_TM_138G")
        """
        self._assert_main_thread()

        if curve_name is None:
            curve_name = self._app_state.active_curve
        if curve_name is None:
            return

        # Get curve data for specified curve
        curve_data = self._app_state.get_curve_data(curve_name)
        if view.selected_points and curve_data:
            from core.commands.curve_commands import DeletePointsCommand

            # Collect points to delete
            indices = list(view.selected_points)
            deleted_points = []
            for idx in sorted(indices):
                if 0 <= idx < len(curve_data):
                    deleted_points.append((idx, curve_data[idx]))

            if deleted_points:
                # Create and execute delete command
                command = DeletePointsCommand(
                    description=f"Delete {len(deleted_points)} point{'s' if len(deleted_points) > 1 else ''}",
                    indices=indices,
                    deleted_points=deleted_points,
                )
                self.command_manager.execute_command(command, main_window)

            # Clear selection
            view.selected_points.clear()
            view.selected_point_idx = -1

            # Clear spatial index since points changed
            self.clear_spatial_index()

            # Update view
            update_method = getattr(view, "update", None)
            if update_method is not None:
                update_method()

    # ==================== UI Update Methods ====================

    def on_data_changed(self, view: CurveViewProtocol, curve_name: str | None = None) -> None:
        """
        Handle curve data change notifications.

        Args:
            view: Curve view that changed
            curve_name: Curve that changed. None = all curves changed.
        """
        self._assert_main_thread()
        if curve_name is None:
            logger.debug("All curve data changed")
        else:
            logger.debug(f"Curve '{curve_name}' data changed")

        # Clear spatial index since data changed
        self.clear_spatial_index()

        # Update view
        if hasattr(view, "update"):
            view.update()

    def on_selection_changed(self, indices: set[int], curve_name: str | None = None) -> None:
        """
        Handle selection change notifications.

        Args:
            indices: Set of selected point indices
            curve_name: Curve whose selection changed. None = active curve.
        """
        self._assert_main_thread()
        if curve_name is None:
            logger.debug(f"Selection changed: {len(indices)} points selected (active curve)")
        else:
            logger.debug(f"Selection changed for '{curve_name}': {len(indices)} points selected")

        # Clear spatial index since selection affects rendering
        # (selected points may be highlighted differently)
        self.clear_spatial_index()

    def on_frame_changed(self, frame: int, curve_name: str | None = None) -> None:
        """
        Handle frame change notifications.

        Args:
            frame: New current frame
            curve_name: Curve to update. None = update all curves.
        """
        self._assert_main_thread()
        if curve_name is None:
            logger.debug(f"Frame changed to {frame} (all curves)")
        else:
            logger.debug(f"Frame changed to {frame} for '{curve_name}'")

        # Clear spatial index since frame affects which points are visible/highlighted
        self.clear_spatial_index()

    def on_point_moved(self, main_window: MainWindowProtocol, idx: int, x: float, y: float) -> None:
        """Handle point movement notifications."""
        logger.debug(f"Point {idx} moved to ({x}, {y})")

    def on_point_selected(self, curve_view: CurveViewProtocol, main_window: MainWindowProtocol, idx: int) -> None:
        """Handle point selection notifications."""
        logger.debug(f"Point {idx} selected")

    def update_point_info(self, main_window: MainWindowProtocol, idx: int, x: float, y: float) -> None:
        """Update point information display."""
        status_bar_method = getattr(main_window, "statusBar", None)
        if status_bar_method is not None and callable(status_bar_method):
            status_bar = status_bar_method()
            show_message = getattr(status_bar, "showMessage", None)
            if show_message is not None and callable(show_message):
                show_message(f"Point {idx}: ({x:.2f}, {y:.2f})")

    def _enable_point_controls(self, main_window: MainWindowProtocol) -> None:
        """Enable point manipulation controls."""
        # This would enable UI controls when points are selected
        pass

    def apply_pan_offset_y(self, view: CurveViewProtocol, delta_y: float) -> None:
        """
        Apply Y pan offset with Y-flip awareness.

        Args:
            view: Curve view to pan
            delta_y: Delta Y in screen pixels
        """
        self._assert_main_thread()

        # Get current pan offset or initialize
        current_pan_y = getattr(view, "pan_offset_y", 0.0)

        # Apply Y-flip multiplier based on view setting
        y_multiplier = -1.0 if view.flip_y_axis else 1.0
        adjusted_delta = delta_y * y_multiplier

        # Update pan offset
        if hasattr(view, "pan_offset_y"):
            view.pan_offset_y = current_pan_y + adjusted_delta  # pyright: ignore[reportAttributeAccessIssue]
            view.update()

        logger.debug(f"Applied pan offset Y: {delta_y} -> {adjusted_delta} (flip={view.flip_y_axis})")

    def reset_view(self, view: CurveViewProtocol) -> None:
        """Reset view to default state."""
        reset_transform = getattr(view, "reset_transform", None)
        if reset_transform is not None:
            reset_transform()
        else:
            # Default reset behavior
            if getattr(view, "zoom_factor", None) is not None:
                view.zoom_factor = 1.0
            if getattr(view, "offset_x", None) is not None:
                view.offset_x = 0
            if getattr(view, "offset_y", None) is not None:
                view.offset_y = 0
            if getattr(view, "pan_offset_x", None) is not None:
                view.pan_offset_x = 0  # pyright: ignore[reportAttributeAccessIssue]
            if getattr(view, "pan_offset_y", None) is not None:
                view.pan_offset_y = 0  # pyright: ignore[reportAttributeAccessIssue]
            if getattr(view, "manual_offset_x", None) is not None:
                view.manual_offset_x = 0  # pyright: ignore[reportAttributeAccessIssue]
            if getattr(view, "manual_offset_y", None) is not None:
                view.manual_offset_y = 0  # pyright: ignore[reportAttributeAccessIssue]
            view.update()

    # ==================== Legacy Methods (Minimal Implementation) ====================

    def undo_action(self, main_window: MainWindowProtocol) -> None:
        """Legacy undo action - now uses command manager."""
        # Prefer command manager if available and has commands
        if self.command_manager.can_undo():
            self.command_manager.undo(main_window)
        # Check if main_window manages its own history (legacy compatibility)
        elif main_window.history is not None and main_window.history_index is not None:
            logger.info("Using legacy history system")
            if main_window.history_index > 0:
                main_window.history_index -= 1
                state = main_window.history[main_window.history_index]
                typed_state = cast(dict[str, object], state)
                self.restore_state(main_window, typed_state)
                self.update_history_buttons(main_window)
        # Check internal history when main_window doesn't manage its own
        elif self._current_index > 0:
            logger.info("Using internal history system")
            self._current_index -= 1
            state = self._history[self._current_index]
            self.restore_state(main_window, state)
            self.update_history_buttons(main_window)
        else:
            # Use command manager even if it has no commands (for consistency)
            logger.info("Using command manager for undo (fallback)")
            self.command_manager.undo(main_window)

    def redo_action(self, main_window: MainWindowProtocol) -> None:
        """Legacy redo action - now uses command manager."""
        logger.info("InteractionService.redo_action called")

        # Prefer command manager if available and has commands to redo
        if self.command_manager.can_redo():
            logger.info("Using command manager for redo")
            self.command_manager.redo(main_window)
        # Check if main_window manages its own history (legacy compatibility)
        elif main_window.history is not None and main_window.history_index is not None:
            logger.info("Using legacy history system for redo")
            if main_window.history_index < len(main_window.history) - 1:
                main_window.history_index += 1
                state = main_window.history[main_window.history_index]
                typed_state = cast(dict[str, object], state)
                self.restore_state(main_window, typed_state)
                self.update_history_buttons(main_window)
        # Check internal history when main_window doesn't manage its own
        elif self._current_index < len(self._history) - 1:
            logger.info("Using internal history system for redo")
            self._current_index += 1
            state = self._history[self._current_index]
            self.restore_state(main_window, state)
            self.update_history_buttons(main_window)
        else:
            # Use command manager even if it has no commands (for consistency)
            logger.info("Using command manager for redo (fallback)")
            self.command_manager.redo(main_window)

    def save_state(self, main_window: MainWindowProtocol) -> None:
        """Legacy save state."""
        self.add_to_history(main_window)

    def select_points_in_rect(
        self, view: CurveViewProtocol, main_window: MainWindowProtocol, rect: QRect, curve_name: str | None = None
    ) -> int:
        """
        Select points in rectangle using spatial indexing for O(1) performance.

        Args:
            view: Curve view
            main_window: Main window instance
            rect: Rectangle to select points within
            curve_name: Curve to select points in. None = active curve.

        Returns:
            Number of points selected

        Examples:
            # Single-curve (backward compatible):
            count = service.select_points_in_rect(view, main_window, selection_rect)

            # Multi-curve - select in specific curve:
            count = service.select_points_in_rect(view, main_window, selection_rect, curve_name="pp56_TM_138G")
        """
        self._assert_main_thread()

        if curve_name is None:
            curve_name = self._app_state.active_curve
        if curve_name is None:
            return 0

        # Get curve data for specified curve
        curve_data = self._app_state.get_curve_data(curve_name)
        if not curve_data:
            return 0

        transform_service = _get_transform_service()

        # Create transform for coordinate conversion
        view_state = transform_service.create_view_state(view)
        transform = transform_service.create_transform_from_view_state(view_state)

        # Use spatial index for O(1) rectangular selection (updated API - Critical Fix #2)
        point_indices = self._point_index.get_points_in_rect(
            curve_data, transform, rect.left(), rect.top(), rect.right(), rect.bottom(), view
        )

        # Convert to set for ApplicationState
        selected_set = set(point_indices)

        # Update ApplicationState
        self._app_state.set_selection(curve_name, selected_set)

        # Update view for backward compatibility
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

    def restore_state(self, main_window: MainWindowProtocol, state: dict[str, object]) -> None:
        """Restore a saved state."""
        import copy

        if not state:
            return

        # Initialize curve_data for type checker
        curve_data = []

        # Restore curve_data
        if "curve_data" in state:
            curve_data = copy.deepcopy(state["curve_data"])

            # Convert tuples back to lists for compatibility
            if curve_data and isinstance(curve_data, list) and len(curve_data) > 0 and isinstance(curve_data[0], tuple):
                curve_data = [list(point) for point in curve_data]

            # Update ApplicationState first (Week 6)
            active_curve_name = self._app_state.active_curve
            if active_curve_name and curve_data:
                # Update ApplicationState with the restored curve data
                from core.type_aliases import CurveDataList

                self._app_state.set_curve_data(active_curve_name, cast(CurveDataList, curve_data))

            # Legacy compatibility: also set on old storage locations
            # Set on main_window directly if it has the attribute
            if main_window.curve_data is not None:
                # Use setattr since curve_data may be a property - Protocol compatibility
                setattr(main_window, "curve_data", curve_data)  # pyright: ignore[reportAttributeAccessIssue]

            # Also set on curve_widget if present
            if (
                main_window.curve_widget is not None
                and getattr(main_window.curve_widget, "curve_data", None) is not None
            ):
                setattr(main_window.curve_widget, "curve_data", curve_data)

            # Also set on curve_view if present
            if main_window.curve_view is not None and getattr(main_window.curve_view, "curve_data", None) is not None:
                setattr(main_window.curve_view, "curve_data", curve_data)

        # Restore point_name
        if "point_name" in state and getattr(main_window, "point_name", None) is not None:
            main_window.point_name = cast(str, state["point_name"])

        # Restore point_color
        if "point_color" in state and getattr(main_window, "point_color", None) is not None:
            main_window.point_color = cast(str, state["point_color"])

        # Update the view
        if main_window.curve_view is not None:
            curve_view = main_window.curve_view
            # Ensure curve_data is available - curve_data is always bound now
            safe_curve_data = curve_data
            # Try different update methods
            set_points = getattr(curve_view, "setPoints", None)
            if set_points is not None:
                try:
                    image_width = getattr(main_window, "image_width", None)
                    image_height = getattr(main_window, "image_height", None)
                    if image_width is not None and image_height is not None:
                        # Use the converted curve_data (lists, not tuples)
                        set_points(
                            safe_curve_data,
                            image_width,
                            image_height,
                            preserve_view=True,
                        )
                    else:
                        set_points(safe_curve_data)
                except Exception:
                    # Fallback if set_points fails
                    update_method = getattr(curve_view, "update", None)
                    if update_method is not None:
                        update_method()
            else:
                set_points = getattr(curve_view, "set_points", None)
                if set_points is not None:
                    set_points(safe_curve_data)
                else:
                    update_method = getattr(curve_view, "update", None)
                    if update_method is not None:
                        update_method()

    def get_spatial_index_stats(self) -> dict[str, object]:
        """
        Get spatial index performance statistics.

        Returns:
            Dictionary with spatial index statistics
        """
        return cast(dict[str, object], self._point_index.get_stats())

    def clear_spatial_index(self) -> None:
        """Clear the spatial index cache to force rebuild."""
        self._point_index._grid.clear()
        self._point_index._last_transform_hash = None
        self._point_index._last_point_count = 0

    def nudge_selected_points(
        self,
        view: CurveViewProtocol,
        main_window: MainWindowProtocol,
        dx: float,
        dy: float,
        curve_name: str | None = None,
    ) -> bool:
        """
        Nudge selected points by a given delta.

        Args:
            view: The curve view containing the points
            main_window: The main window instance
            dx: Delta x to move points
            dy: Delta y to move points
            curve_name: Curve containing points to nudge. None = active curve.

        Returns:
            True if points were successfully nudged, False otherwise

        Examples:
            # Single-curve (backward compatible):
            success = service.nudge_selected_points(view, main_window, 1.0, 0.0)

            # Multi-curve - nudge specific curve:
            success = service.nudge_selected_points(view, main_window, 1.0, 0.0, curve_name="pp56_TM_138G")
        """
        self._assert_main_thread()

        if not view.selected_points:
            return False

        if curve_name is None:
            curve_name = self._app_state.active_curve
        if curve_name is None:
            return False

        # Get curve data for specified curve
        curve_data = self._app_state.get_curve_data(curve_name)
        if not curve_data:
            return False

        success = False
        for idx in view.selected_points:
            if 0 <= idx < len(curve_data):
                point = curve_data[idx]
                # Preserve frame and status, update x and y
                if len(point) >= 4:
                    new_x = point[1] + dx
                    new_y = point[2] + dy
                    view.curve_data[idx] = (point[0], new_x, new_y, point[3])
                    success = True
                elif len(point) == 3:
                    new_x = point[1] + dx
                    new_y = point[2] + dy
                    view.curve_data[idx] = (point[0], new_x, new_y)
                    success = True

        if success:
            view.update()

        return success

    # ==================== History Query Methods ====================

    def can_undo(self) -> bool:
        """Check if undo is possible."""
        # Check both command manager and legacy history
        if self.command_manager.can_undo():
            return True
        return self._current_index > 0

    def can_redo(self) -> bool:
        """Check if redo is possible."""
        # Check both command manager and legacy history
        if self.command_manager.can_redo():
            return True
        return self._current_index < len(self._history) - 1

    def get_history_stats(self) -> dict[str, object]:
        """Get history statistics - alias for get_memory_stats for compatibility."""
        return self.get_memory_stats()

    def get_history_size(self) -> int:
        """Get current history size."""
        return len(self._history)


# Singleton instance is managed by services/__init__.py
# Removed duplicate get_interaction_service() to avoid multiple singleton instances

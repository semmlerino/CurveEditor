#!/usr/bin/env python

"""
InputService: centralized handling for mouse, wheel, key, and context menu events.
"""

from PySide6.QtCore import QPointF, QRect, QSize, Qt
from PySide6.QtGui import QAction, QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QMenu, QRubberBand

from services.curve_service import CurveService

class InputService:
    """Facade for input event handling across curve views."""

    @staticmethod
    def handle_mouse_press(view, event: QMouseEvent) -> None:
        """Handle mouse press events for selection, dragging, panning, and rectangle selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                # Start rectangle selection
                # Initialize rubber band attributes if they don't exist
                if not hasattr(view, "rubber_band") or getattr(view, "rubber_band", None) is None:
                    setattr(view, "rubber_band", QRubberBand(QRubberBand.Shape.Rectangle, None))
                if not hasattr(view, "rubber_band_origin"):
                    setattr(view, "rubber_band_origin", QPointF())
                if not hasattr(view, "rubber_band_active"):
                    setattr(view, "rubber_band_active", False)

                # Set the origin point for the rubber band
                setattr(view, "rubber_band_origin", event.position())
                rubber_band = getattr(view, "rubber_band")
                if rubber_band:
                    rubber_band.setGeometry(QRect(getattr(view, "rubber_band_origin").toPoint(), QSize()))
                    rubber_band.show()
                setattr(view, "rubber_band_active", True)
                # Prevent single point selection/drag when starting rubber band
                view.drag_active = False
                view.last_drag_pos = None
            else:
                # Original LeftButton logic (single point select/drag)
                idx = CurveService.find_point_at(view, event.pos().x(), event.pos().y())
                if idx is not None and idx >= 0:
                    _ = CurveService.select_point_by_index(view, view.main_window, idx)
                    view.drag_active = True
                    view.last_drag_pos = event.position()
                else:
                    _ = CurveService.clear_selection(view, view.main_window)
                    view.drag_active = False
                    view.last_drag_pos = None
        elif event.button() == Qt.MouseButton.MiddleButton:
            # Start panning (original logic)
            view.pan_active = True
            view.last_pan_pos = event.position()
            view.setCursor(Qt.CursorShape.ClosedHandCursor)

    @staticmethod
    def handle_mouse_move(view, event: QMouseEvent) -> None:
        """Handle mouse move events for dragging points, panning, or updating rectangle selection."""
        current_pos = event.position()

        # Handle rubber band selection - both direct attribute access (for tests) and getattr (for runtime)
        rubber_band_active = (
            getattr(view, "rubber_band_active", False)
            if hasattr(view, "rubber_band_active")
            else view.rubber_band_active
        )
        rubber_band = getattr(view, "rubber_band", None) if hasattr(view, "rubber_band") else view.rubber_band
        if rubber_band_active and rubber_band:
            # Calculate selection rectangle
            # Get rubber_band_origin - handle both direct access and getattr
            rubber_band_origin = (
                getattr(view, "rubber_band_origin") if hasattr(view, "rubber_band_origin") else view.rubber_band_origin
            )
            selection_rect = QRect(rubber_band_origin.toPoint(), current_pos.toPoint()).normalized()
            # Update rubber band geometry
            rubber_band.setGeometry(selection_rect)
            # Perform selection in real-time
            _ = CurveService.select_points_in_rect(view, view.main_window, selection_rect)
        elif view.drag_active and view.last_drag_pos and view.selected_point_idx >= 0:
            # Original drag logic
            assert view.last_drag_pos is not None, "last_drag_pos should not be None during drag"
            delta = current_pos - view.last_drag_pos
            view.last_drag_pos = current_pos
            scale = view.zoom_factor
            if scale == 0:
                scale = 1.0
            dx = delta.x() / scale
            dy = delta.y() / scale
            # Get current position and calculate new position with delta
            point_data = view.get_point_data(view.selected_point_idx)
            if point_data:
                _, current_x, current_y, _ = point_data
                new_x = current_x + dx
                new_y = current_y + dy
                # Update point position using service
                _ = CurveService.update_point_position(view, view.main_window, view.selected_point_idx, new_x, new_y)

        elif view.pan_active and view.last_pan_pos:
            # Original pan logic
            assert view.last_pan_pos is not None, "last_pan_pos should not be None during pan"
            delta = current_pos - view.last_pan_pos
            view.last_pan_pos = current_pos
            # Inline pan logic (was "pan_view"  # CenteringZoomService was deleted
            if hasattr(view, 'x_offset') and hasattr(view, 'y_offset'):
                view.x_offset += delta.x()
                view.y_offset += delta.y()
                view.update()

    @staticmethod
    def handle_mouse_release(view, event: QMouseEvent) -> None:
        """Handle mouse release events to finalize dragging, panning, or rectangle selection."""
        # Check for rubber band selection - support both direct access and getattr
        rubber_band_active = (
            getattr(view, "rubber_band_active", False)
            if hasattr(view, "rubber_band_active")
            else view.rubber_band_active
        )
        if rubber_band_active:
            # Selection rectangle has been completed
            rubber_band = getattr(view, "rubber_band", None) if hasattr(view, "rubber_band") else view.rubber_band
            if rubber_band:
                rubber_band.hide()

            # Support both direct attribute setting and setattr based on what the view supports
            if hasattr(view, "rubber_band_active"):
                setattr(view, "rubber_band_active", False)
                setattr(view, "rubber_band", None)
            else:
                view.rubber_band_active = False
                view.rubber_band = None

            # Add to history after completing a rubber band selection
            if view.main_window:
                view.main_window.add_to_history()

            # Note: We're not doing selection here since it's already done in move event

        elif view.drag_active and view.selected_point_idx >= 0:
            # Add to history when dragging completes and emit point_moved signal
            point_data = view.get_point_data(view.selected_point_idx)
            if point_data:
                _, x, y, _ = point_data
                view.point_moved.emit(view.selected_point_idx, x, y)
                if view.main_window:
                    view.main_window.add_to_history()

            view.drag_active = False
            view.last_drag_pos = None

        elif view.pan_active and event.button() == Qt.MouseButton.MiddleButton:
            # Original pan release logic
            view.pan_active = False
            view.last_pan_pos = None
            view.unsetCursor()

    @staticmethod
    def handle_wheel_event(view, event: QWheelEvent) -> None:
        """Handle mouse wheel events for zooming."""
        # Simple zoom implementation (inline replacement for ViewTransformer)
        delta = event.angleDelta().y()
        zoom_factor = 1.1 if delta > 0 else 0.9
        current_zoom = getattr(view, "zoom_factor", 1.0)
        new_zoom = max(0.1, min(10.0, current_zoom * zoom_factor))
        setattr(view, "zoom_factor", new_zoom)
        view.update()

    @staticmethod
    def handle_key_event(view, event: QKeyEvent) -> None:
        """Handle keyboard events for moving view or deleting points."""
        step: float = 1.0
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            step = 10.0
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            step = 0.1
        key = event.key()
        if key == Qt.Key.Key_Up and event.modifiers() & (
            Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier
        ):
            view.y_offset -= step
            view.update()
        elif key == Qt.Key.Key_Down and event.modifiers() & (
            Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.ControlModifier
        ):
            view.y_offset += step
            view.update()
        elif key == Qt.Key.Key_Delete and view.selected_point_idx >= 0:
            _ = CurveService.delete_selected_points(view, view.main_window)

    @staticmethod
    def handle_context_menu(view, event: QMouseEvent) -> None:
        """Handle context menu events to show options for points and visualization."""
        menu = QMenu(None)
        # Point-specific actions
        idx = view.findPointAt(event.position())
        if idx >= 0:
            info = view.get_point_data(idx)
            if info:
                frame, x, y = info[:3]
                _ = menu.addSection(f"Point {idx}: Frame {frame}, ({x:.2f}, {y:.2f})")
                if idx != view.selected_point_idx:
                    select_act = QAction("Select this point", None)
                    _ = select_act.triggered.connect(lambda: view.selectPointByIndex(idx))
                    _ = menu.addAction(select_act)
                is_interp = len(info) > 3 and info[3] == "interpolated"
                toggle_text = "Restore to normal point" if is_interp else "Mark as interpolated"
                togg_act = QAction(toggle_text, None)
                _ = togg_act.triggered.connect(lambda: view.toggle_point_interpolation(idx))
                _ = menu.addAction(togg_act)
                _ = menu.addSeparator()
        # Visualization toggles - get service instance
        from services.service_registry_v2 import get_service_registry
        visualization_service = get_service_registry().get_service(VisualizationService)

        grid_act = QAction("Show Grid" if not view.show_grid else "Hide Grid", None)
        _ = grid_act.triggered.connect(
            lambda: visualization_service.toggle_grid(view, not view.show_grid) if view.main_window else None
        )
        _ = menu.addAction(grid_act)
        vel_act = QAction("Show Velocity Vectors" if not view.show_velocity_vectors else "Hide Velocity Vectors", None)
        _ = vel_act.triggered.connect(
            lambda: visualization_service.toggle_velocity_vectors(view, not view.show_velocity_vectors)
            if view.main_window
            else None
        )
        _ = menu.addAction(vel_act)
        frames_act = QAction("Show Frame Numbers" if not view.show_all_frame_numbers else "Hide Frame Numbers", None)
        _ = frames_act.triggered.connect(
            lambda: visualization_service.toggle_all_frame_numbers(view, not view.show_all_frame_numbers)
            if view.main_window
            else None
        )
        _ = menu.addAction(frames_act)
        bg_act = QAction("Show Background" if not view.show_background else "Hide Background", None)
        _ = bg_act.triggered.connect(lambda: view.toggleBackgroundVisible(not view.show_background))
        _ = menu.addAction(bg_act)
        _ = menu.exec_(event.globalPos())

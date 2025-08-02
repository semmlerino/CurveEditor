#!/usr/bin/env python

"""
InputService: centralized handling for mouse, wheel, key, and context menu events.
"""

from typing import Any, Protocol, cast

from PySide6.QtCore import QObject, QPointF, QRect, QSize, Qt
from PySide6.QtGui import QAction, QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QMenu, QRubberBand, QWidget

from services.centering_zoom_service import CenteringZoomService
from services.curve_service import CurveService
from services.visualization_service import VisualizationService


class CurveViewProtocol(Protocol):
    """Protocol defining the interface expected by InputService for curve views."""

    # Required properties
    selected_point_idx: int
    rubber_band: QRubberBand | None
    rubber_band_origin: QPointF
    rubber_band_active: bool
    drag_active: bool
    last_drag_pos: QPointF | None
    pan_active: bool
    last_pan_pos: QPointF | None
    zoom_factor: float
    x_offset: float
    y_offset: float
    main_window: Any  # Using Any for main_window to avoid circular imports
    # Visual properties
    show_grid: bool
    show_velocity_vectors: bool
    show_all_frame_numbers: bool
    show_background: bool

    # Required signals
    point_moved: Any  # Using Any for Signal to avoid circular imports

    # Required methods
    def findPointAt(self, pos: QPointF) -> int: ...
    def selectPointByIndex(self, idx: int) -> None: ...
    def get_point_data(self, idx: int) -> tuple[int, float, float, str | None]: ...
    def toggle_point_interpolation(self, idx: int) -> None: ...
    def toggleBackgroundVisible(self, visible: bool) -> None: ...
    def update(self) -> None: ...
    def setCursor(self, cursor: Qt.CursorShape) -> None: ...
    def unsetCursor(self) -> None: ...


class InputService:
    """Facade for input event handling across curve views."""

    @staticmethod
    def handle_mouse_press(view: CurveViewProtocol, event: QMouseEvent) -> None:  # type: ignore[misc]
        """Handle mouse press events for selection, dragging, panning, and rectangle selection."""
        if event.button() == Qt.LeftButton:  # type: ignore[attr-defined]
            if event.modifiers() & Qt.AltModifier:  # type: ignore[attr-defined]
                # Start rectangle selection
                # Initialize rubber band attributes if they don't exist
                if not hasattr(view, "rubber_band") or getattr(view, "rubber_band", None) is None:
                    setattr(view, "rubber_band", QRubberBand(QRubberBand.Rectangle, cast(QWidget, view)))  # type: ignore[attr-defined]
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
                    CurveService.select_point_by_index(view, view.main_window, idx)
                    view.drag_active = True
                    view.last_drag_pos = event.position()
                else:
                    CurveService.clear_selection(view, view.main_window)
                    view.drag_active = False
                    view.last_drag_pos = None
        elif event.button() == Qt.MiddleButton:  # type: ignore[attr-defined]
            # Start panning (original logic)
            view.pan_active = True
            view.last_pan_pos = event.position()
            view.setCursor(Qt.ClosedHandCursor)  # type: ignore[attr-defined]

    @staticmethod
    def handle_mouse_move(view: CurveViewProtocol, event: QMouseEvent) -> None:  # type: ignore[misc]
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
            CurveService.select_points_in_rect(view, view.main_window, selection_rect)
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
                CurveService.update_point_position(view, view.main_window, view.selected_point_idx, new_x, new_y)

        elif view.pan_active and view.last_pan_pos:
            # Original pan logic
            assert view.last_pan_pos is not None, "last_pan_pos should not be None during pan"
            delta = current_pos - view.last_pan_pos
            view.last_pan_pos = current_pos
            # Let the service handle panning with appropriate cast
            CenteringZoomService.pan_view(cast(Any, view), delta.x(), delta.y())  # type: ignore[arg-type]

    @staticmethod
    def handle_mouse_release(view: CurveViewProtocol, event: QMouseEvent) -> None:  # type: ignore[misc]
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
            view.main_window.add_to_history()

            # Note: We're not doing selection here since it's already done in move event

        elif view.drag_active and view.selected_point_idx >= 0:
            # Add to history when dragging completes and emit point_moved signal
            point_data = view.get_point_data(view.selected_point_idx)
            if point_data:
                _, x, y, _ = point_data
                view.point_moved.emit(view.selected_point_idx, x, y)
                view.main_window.add_to_history()

            view.drag_active = False
            view.last_drag_pos = None

        elif view.pan_active and event.button() == Qt.MiddleButton:  # type: ignore[attr-defined]
            # Original pan release logic
            view.pan_active = False
            view.last_pan_pos = None
            view.unsetCursor()

    @staticmethod
    def handle_wheel_event(view: CurveViewProtocol, event: QWheelEvent) -> None:  # type: ignore[misc]
        """Handle mouse wheel events for zooming."""
        CenteringZoomService.handle_wheel_event(cast(Any, view), event)  # type: ignore[arg-type]

    @staticmethod
    def handle_key_event(view: CurveViewProtocol, event: QKeyEvent) -> None:  # type: ignore[misc]
        """Handle keyboard events for moving view or deleting points."""
        step: float = 1.0
        if event.modifiers() & Qt.ShiftModifier:  # type: ignore[attr-defined]
            step = 10.0
        if event.modifiers() & Qt.ControlModifier:  # type: ignore[attr-defined]
            step = 0.1
        key = event.key()
        if key == Qt.Key_Up and event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier):  # type: ignore[attr-defined]
            view.y_offset -= step
            view.update()
        elif key == Qt.Key_Down and event.modifiers() & (Qt.ShiftModifier | Qt.ControlModifier):  # type: ignore[attr-defined]
            view.y_offset += step
            view.update()
        elif key == Qt.Key_Delete and view.selected_point_idx >= 0:  # type: ignore[attr-defined]
            CurveService.delete_selected_points(view, view.main_window)

    @staticmethod
    def handle_context_menu(view: CurveViewProtocol, event: QMouseEvent) -> None:  # type: ignore[misc]
        """Handle context menu events to show options for points and visualization."""
        menu = QMenu(cast(QWidget, view))
        # Point-specific actions
        idx = view.findPointAt(event.position())
        if idx >= 0:
            info = view.get_point_data(idx)
            if info:
                frame, x, y = info[:3]
                menu.addSection(f"Point {idx}: Frame {frame}, ({x:.2f}, {y:.2f})")
                if idx != view.selected_point_idx:
                    select_act = QAction("Select this point", cast(QObject, view))
                    select_act.triggered.connect(lambda: view.selectPointByIndex(idx))
                    menu.addAction(select_act)
                is_interp = len(info) > 3 and info[3] == "interpolated"
                toggle_text = "Restore to normal point" if is_interp else "Mark as interpolated"
                togg_act = QAction(toggle_text, cast(QObject, view))
                togg_act.triggered.connect(lambda: view.toggle_point_interpolation(idx))
                menu.addAction(togg_act)
                menu.addSeparator()
        # Visualization toggles
        grid_act = QAction("Show Grid" if not view.show_grid else "Hide Grid", cast(QObject, view))
        grid_act.triggered.connect(lambda: VisualizationService.toggle_grid(view.main_window, not view.show_grid))
        menu.addAction(grid_act)
        vel_act = QAction(
            "Show Velocity Vectors" if not view.show_velocity_vectors else "Hide Velocity Vectors", cast(QObject, view)
        )
        vel_act.triggered.connect(
            lambda: VisualizationService.toggle_velocity_vectors(view.main_window, not view.show_velocity_vectors)
        )
        menu.addAction(vel_act)
        frames_act = QAction(
            "Show Frame Numbers" if not view.show_all_frame_numbers else "Hide Frame Numbers", cast(QObject, view)
        )
        frames_act.triggered.connect(
            lambda: VisualizationService.toggle_all_frame_numbers(view.main_window, not view.show_all_frame_numbers)
        )
        menu.addAction(frames_act)
        bg_act = QAction("Show Background" if not view.show_background else "Hide Background", cast(QObject, view))
        bg_act.triggered.connect(lambda: view.toggleBackgroundVisible(not view.show_background))
        menu.addAction(bg_act)
        menu.exec_(event.globalPos())

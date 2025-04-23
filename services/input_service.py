#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InputService: centralized handling for mouse, wheel, key, and context menu events.
"""
from PySide6.QtWidgets import QMenu, QRubberBand
# from PySide6.QtWidgets import QMenu # Remove duplicate
from PySide6.QtGui import QAction, QMouseEvent
from PySide6.QtCore import Qt, QPointF, QSize, QRect # type: ignore[attr-defined] # QRect belongs here
from services.curve_service import CurveService as CurveViewOperations
from services.centering_zoom_service import CenteringZoomService as ZoomOperations
from services.visualization_service import VisualizationService as VizOps
from typing import Any, Optional


class InputService:
    """Facade for input event handling across curve views."""

    @staticmethod
    def handle_mouse_press(view: Any, event: QMouseEvent) -> None:
        """Handle mouse press events for selection, dragging, panning, and rectangle selection."""
        if event.button() == Qt.LeftButton:
            if event.modifiers() & Qt.AltModifier: # Check for Alt key
                # Start rectangle selection
                if not hasattr(view, 'rubber_band') or view.rubber_band is None:
                     # Initialize rubber band attributes if they don't exist (should be in view.__init__)
                     view.rubber_band = QRubberBand(QRubberBand.Rectangle, view)
                     view.rubber_band_origin = QPointF()
                     view.rubber_band_active = False

                view.rubber_band_origin = event.position() # Use QPointF
                # Ensure rubber_band exists before calling setGeometry
                if view.rubber_band:
                    view.rubber_band.setGeometry(QRect(view.rubber_band_origin.toPoint(), QSize())) # Use toPoint() for QRect
                    view.rubber_band.show()
                view.rubber_band_active = True
                # Prevent single point selection/drag when starting rubber band
                view.drag_active = False
                view.last_drag_pos = None
            else:
                # Original LeftButton logic (single point select/drag)
                idx = CurveViewOperations.find_point_at(view, event.pos().x(), event.pos().y())
                if idx >= 0:
                    CurveViewOperations.select_point_by_index(view, view.main_window, idx)
                    view.drag_active = True
                    view.last_drag_pos = event.position()
                else:
                    CurveViewOperations.clear_selection(view, view.main_window)
                    view.drag_active = False
                    view.last_drag_pos = None
        elif event.button() == Qt.MiddleButton:
            # Start panning (original logic)
            view.pan_active = True
            view.last_pan_pos = event.position()
            view.setCursor(Qt.ClosedHandCursor)

    @staticmethod
    def handle_mouse_move(view: Any, event: QMouseEvent) -> None:
        """Handle mouse move events for dragging points, panning, or updating rectangle selection."""
        current_pos = event.position()

        if getattr(view, 'rubber_band_active', False) and getattr(view, 'rubber_band', None):
            # Calculate selection rectangle
            selection_rect = QRect(view.rubber_band_origin.toPoint(), current_pos.toPoint()).normalized()
            # Update rubber band geometry
            view.rubber_band.setGeometry(selection_rect)
            # Perform selection in real-time
            if hasattr(view, 'main_window') and hasattr(CurveViewOperations, 'select_points_in_rect'):
                CurveViewOperations.select_points_in_rect(view, view.main_window, selection_rect)
        elif view.drag_active and view.last_drag_pos and getattr(view, 'selected_point_idx', -1) >= 0:
            # Original drag logic
            delta = current_pos - view.last_drag_pos
            view.last_drag_pos = current_pos
            scale = getattr(view, 'zoom_factor', 1.0)
            if scale == 0: scale = 1.0
            dx = delta.x() / scale
            dy = delta.y() / scale
            if getattr(view, 'flip_y_axis', False):
                dy = -dy
            point_data = CurveViewOperations.get_point_data(view, view.selected_point_idx)
            if point_data:
                _, current_x, current_y, _ = point_data
                new_x = current_x + dx
                new_y = current_y + dy
                CurveViewOperations.update_point_position(view, view.main_window, view.selected_point_idx, new_x, new_y)

        elif view.pan_active and view.last_pan_pos:
            # Original pan logic
            delta = current_pos - view.last_pan_pos
            view.last_pan_pos = current_pos
            if hasattr(view, 'x_offset') and hasattr(view, 'y_offset'):
                view.x_offset += delta.x()
                view.y_offset += delta.y()
                view.update()
            else:
                print("Warning: View object missing x_offset or y_offset for panning.")

    @staticmethod
    def handle_mouse_release(view: Any, event: QMouseEvent) -> None:
        """Handle mouse release events to finalize dragging, panning, or rectangle selection."""
        if getattr(view, 'rubber_band_active', False) and event.button() == Qt.LeftButton and getattr(view, 'rubber_band', None):
            # Finalize rectangle selection
            view.rubber_band.hide()
            view.rubber_band_active = False
            # Potentially add to history if needed
            if hasattr(view, 'main_window') and hasattr(view.main_window, 'add_to_history'):
                 view.main_window.add_to_history() # Add description
            # Clean up rubber band reference after use
            view.rubber_band = None


        elif view.drag_active and event.button() == Qt.LeftButton:
            # Original drag release logic
            if getattr(view, 'selected_point_idx', -1) >= 0:
                 point_data = CurveViewOperations.get_point_data(view, view.selected_point_idx)
                 if point_data:
                     _, x, y, _ = point_data
                     if hasattr(view, 'point_moved'):
                         view.point_moved.emit(view.selected_point_idx, x, y)
                     if hasattr(view, 'main_window') and hasattr(view.main_window, 'add_to_history'):
                         view.main_window.add_to_history("Point Drag") # Add description

            view.drag_active = False
            view.last_drag_pos = None

        elif view.pan_active and event.button() == Qt.MiddleButton:
            # Original pan release logic
            view.pan_active = False
            view.last_pan_pos = None
            view.unsetCursor()

    @staticmethod
    def handle_wheel_event(view: Any, event: Any) -> None:
        ZoomOperations.handle_wheel_event(view, event)

    @staticmethod
    def handle_key_event(view: Any, event: Any) -> None:
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
        elif key == Qt.Key_Delete and getattr(view, 'selected_point_idx', -1) >= 0:  # type: ignore[attr-defined]
            CurveViewOperations.delete_selected_points(view, view.main_window)

    @staticmethod
    def handle_context_menu(view: Any, event: Any) -> None:
        menu = QMenu(view)
        # Point-specific actions
        idx = view.findPointAt(event.pos())
        if idx >= 0 and hasattr(view, 'get_point_data'):
            info = view.get_point_data(idx)
            if info:
                frame, x, y = info[:3]
                menu.addSection(f"Point {idx}: Frame {frame}, ({x:.2f}, {y:.2f})")
                if idx != getattr(view, 'selected_point_idx', -1):
                    select_act = QAction("Select this point", view)
                    select_act.triggered.connect(lambda: view.selectPointByIndex(idx))
                    menu.addAction(select_act)
                is_interp = len(info) > 3 and info[3] == 'interpolated'
                toggle_text = "Restore to normal point" if is_interp else "Mark as interpolated"
                togg_act = QAction(toggle_text, view)
                togg_act.triggered.connect(lambda: view.toggle_point_interpolation(idx))
                menu.addAction(togg_act)
                menu.addSeparator()
        # Visualization toggles
        grid_act = QAction('Show Grid' if not getattr(view, 'show_grid', False) else 'Hide Grid', view)
        grid_act.triggered.connect(lambda: VizOps.toggle_grid(view.main_window, not getattr(view, 'show_grid', False)))
        menu.addAction(grid_act)
        vel_act = QAction('Show Velocity Vectors' if not getattr(view, 'show_velocity_vectors', False) else 'Hide Velocity Vectors', view)
        vel_act.triggered.connect(lambda: VizOps.toggle_velocity_vectors(view.main_window, not getattr(view, 'show_velocity_vectors', False)))
        menu.addAction(vel_act)
        frames_act = QAction('Show Frame Numbers' if not getattr(view, 'show_all_frame_numbers', False) else 'Hide Frame Numbers', view)
        frames_act.triggered.connect(lambda: VizOps.toggle_all_frame_numbers(view.main_window, not getattr(view, 'show_all_frame_numbers', False)))
        menu.addAction(frames_act)
        bg_act = QAction('Show Background' if not getattr(view, 'show_background', False) else 'Hide Background', view)
        bg_act.triggered.connect(lambda: view.toggleBackgroundVisible(not getattr(view, 'show_background', False)))
        menu.addAction(bg_act)
        menu.exec_(event.globalPos())

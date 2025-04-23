#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
InputService: centralized handling for mouse, wheel, key, and context menu events.
"""
from PySide6.QtWidgets import QMenu
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt  # type: ignore[attr-defined]
from services.curve_service import CurveService as CurveViewOperations
from services.centering_zoom_service import CenteringZoomService as ZoomOperations
from services.visualization_service import VisualizationService as VizOps
from typing import Any


class InputService:
    """Facade for input event handling across curve views."""

    @staticmethod
    def handle_mouse_press(view: Any, event: Any) -> None:
        CurveViewOperations.handle_mouse_press(view, event)

    @staticmethod
    def handle_mouse_move(view: Any, event: Any) -> Any:
        # Delegate to service facade; fallback to legacy operations if missing
        handler = getattr(CurveViewOperations, 'handle_mouse_move', None)
        if callable(handler):
            return handler(view, event)
        # Fallback to direct legacy implementation
        from curve_view_operations import CurveViewOperations as LegacyOps
        return LegacyOps.handle_mouse_move(view, event)

    @staticmethod
    def handle_mouse_release(view: Any, event: Any) -> None:
        CurveViewOperations.handle_mouse_release(view, event)

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

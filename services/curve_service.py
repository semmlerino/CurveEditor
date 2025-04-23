#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CurveService: extracted business logic placeholder for CurveViewOperations.
For Phase 1, this module re-exports all of the static methods from the legacy CurveViewOperations.
Further refactoring will move implementations here.
"""

from curve_view_operations import CurveViewOperations
from curve_view_plumbing import normalize_point
from typing import List, Tuple, Optional, Any

class CurveService:
    """Facade for curve operations (explicit API, phase 1)."""
    @staticmethod
    def select_all_points(curve_view: Any, main_window: Any) -> int:
        """Select all points in the curve."""
        return CurveViewOperations.select_all_points(curve_view, main_window)

    @staticmethod
    def clear_selection(curve_view: Any, main_window: Any) -> None:
        """Clear all selected points without returning a value."""
        CurveViewOperations.clear_selection(curve_view, main_window)

    @staticmethod
    def select_point_by_index(curve_view: Any, main_window: Any, index: int) -> bool:
        return CurveViewOperations.select_point_by_index(curve_view, main_window, index)

    @staticmethod
    def set_curve_data(curve_view: Any, curve_data: List[Tuple[Any, ...]]) -> None:
        """Set curve data on the view."""
        curve_view.set_curve_data(curve_data)

    @staticmethod
    def delete_selected_points(curve_view: Any, main_window: Any, show_confirmation: bool = False) -> Tuple[int, str]:
        """Delete or mark interpolated selected points, always returning a tuple."""
        result = CurveViewOperations.delete_selected_points(curve_view, main_window, show_confirmation)
        if isinstance(result, tuple):
            return result
        return (result, "")

    @staticmethod
    def toggle_point_interpolation(curve_view: Any, index: int) -> Tuple[bool, str]:
        """Toggle interpolation status of a point, always returning a tuple."""
        result = CurveViewOperations.toggle_point_interpolation(curve_view, index)
        if isinstance(result, tuple):
            return result
        return (result, "")

    @staticmethod
    def update_point_position(curve_view: Any, main_window: Any, index: int, x: float, y: float) -> bool:
        return CurveViewOperations.update_point_position(curve_view, main_window, index, x, y)

    @staticmethod
    def nudge_selected_points(curve_view: Any, dx: float = 0.0, dy: float = 0.0) -> bool:
        """Nudge selected points by integer deltas."""
        return CurveViewOperations.nudge_selected_points(curve_view, int(dx), int(dy))

    @staticmethod
    def get_point_data(curve_view: Any, index: int) -> Optional[Tuple[Any, ...]]:
        """Return (frame, x, y, status) for a point or None if out of range."""
        pts = getattr(curve_view, 'points', None)
        if not pts or index < 0 or index >= len(pts):
            return None
        return normalize_point(pts[index])

    @staticmethod
    def extract_frame_number(curve_view: Any, img_idx: int) -> int:
        """Placeholder: return default frame number."""
        return 0

    @staticmethod
    def change_nudge_increment(curve_view: Any, increase: bool = True) -> float:
        """Placeholder: return default nudge increment."""
        return 1.0

    @staticmethod
    def set_point_radius(curve_view: Any, main_window: Any, radius: float) -> None:
        """Set the point display radius via legacy operations."""
        CurveViewOperations.set_point_size(curve_view, main_window, radius)

    @staticmethod
    def find_point_at(curve_view: Any, x: float, y: float) -> int:
        """Find a point at the given widget coordinates."""
        return CurveViewOperations.find_point_at(curve_view, x, y)

    @staticmethod
    def find_closest_point_by_frame(curve_view: Any, frame_num: int) -> int:
        """Find the index of the point closest to the given frame."""
        return CurveViewOperations.find_closest_point_by_frame(curve_view, frame_num)

    @staticmethod
    def transform_point(curve_view: Any, x: float, y: float, display_width: float, display_height: float, offset_x: float, offset_y: float, scale: float) -> Tuple[float, float]:
        """Transform from track coordinates to widget coordinates."""
        return CurveViewOperations.transform_point(curve_view, x, y, display_width, display_height, offset_x, offset_y, scale)

    @staticmethod
    def handle_mouse_press(curve_view: Any, event: Any) -> Any:
        """Delegate mouse press events to the legacy service."""
        return CurveViewOperations.handle_mouse_press(curve_view, event)

    @staticmethod
    def handle_mouse_move(curve_view: Any, event: Any) -> Any:
        """Delegate mouse move events to the legacy service."""
        return CurveViewOperations.handle_mouse_move(curve_view, event)

    @staticmethod
    def handle_mouse_release(curve_view: Any, event: Any) -> Any:
        """Delegate mouse release events to the legacy service."""
        return CurveViewOperations.handle_mouse_release(curve_view, event)

    @staticmethod
    def reset_view(main_window: Any) -> None:
        """Stub for reset_view to satisfy UI typing."""
        pass

    @staticmethod
    def on_point_selected(main_window: Any, idx: Any) -> None:
        """Stub for on_point_selected to satisfy UI typing."""
        pass

    @staticmethod
    def on_point_moved(main_window: Any, idx: Any, x: Any, y: Any) -> None:
        """Stub for on_point_moved to satisfy UI typing."""
        pass

# Auto-wire all static methods from the legacy CurveViewOperations into the facade
for name, fn in CurveViewOperations.__dict__.items():
    if callable(fn) and not name.startswith("_") and not hasattr(CurveService, name):
        setattr(CurveService, name, staticmethod(fn))

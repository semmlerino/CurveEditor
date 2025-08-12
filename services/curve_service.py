#!/usr/bin/env python
"""
Minimal CurveService with only the methods that are actually used.

This service was reduced from 652 lines to ~100 lines by removing 21 unused methods.
Only 3 methods are actually called from the codebase.
"""

from core.point_types import create_point4, get_point_frame, safe_extract_point
import logging

logger = logging.getLogger("curve_service")

class CurveService:
    """Minimal curve service with only the 3 methods that are actually used."""

    @staticmethod
    def on_point_moved(main_window: "MainWindowProtocol", idx: int, x: float, y: float) -> None:
        """Handle point moved in the view. Updates curve_data and point info."""
        if not hasattr(main_window, "curve_data") or idx < 0 or idx >= len(main_window.curve_data):
            return
        point = main_window.curve_data[idx]
        # Use type-safe extraction and update
        frame, _, _, status = safe_extract_point(point)
        # Always create Point4 for consistency
        main_window.curve_data[idx] = create_point4(frame, x, y, status)
        CurveService.update_point_info(main_window, idx, x, y)
        if hasattr(main_window, "add_to_history"):
            main_window.add_to_history()

    @staticmethod
    def on_point_selected(curve_view: "CurveViewProtocol", main_window: "MainWindowProtocol", idx: int) -> None:
        """Handle point selected event from the curve view."""
        # Update main window selected indices
        sel_idx = getattr(curve_view, "selected_point_idx", idx) if hasattr(curve_view, "selected_point_idx") else idx
        idx = sel_idx if isinstance(sel_idx, int) else -1
        main_window.selected_indices = [idx] if idx >= 0 else []

        # Ensure curve view's selection is in sync
        if hasattr(curve_view, "selected_points"):
            curve_view.selected_points = cast(set[int], set())
            if idx >= 0:
                curve_view.selected_points.add(idx)
                curve_view.selected_point_idx = idx

        # Update point info if valid index
        if idx >= 0 and idx < len(main_window.curve_data):
            point_data = main_window.curve_data[idx]
            frame, x, y, _ = safe_extract_point(point_data)
            CurveService.update_point_info(main_window, idx, x, y)
            # Update timeline if available
            if hasattr(main_window, "timeline_slider"):
                main_window.ui_components.timeline_slider.setValue(frame)
        else:
            if 0 <= idx < len(main_window.curve_data):
                current_point = main_window.curve_data[idx]
                frame, x, y, _ = safe_extract_point(current_point)
                # Update point with new status using type-safe constructor
                main_window.curve_data[idx] = create_point4(frame, x, y, "keyframe")

                # Also update the point in curve_view.points if available
                if hasattr(curve_view, "points") and idx < len(getattr(curve_view, "points", [])):
                    # We access points via getattr since it's not in the protocol definition
                    points = getattr(curve_view, "points")  # type: ignore[attr-defined]
                    points[idx] = create_point4(frame, x, y, "keyframe")  # type: ignore[index]
                # Update point info display
                CurveService.update_point_info(main_window, idx, x, y)
                # Add to history
                if hasattr(main_window, "add_to_history"):
                    main_window.add_to_history()

    @staticmethod
    def update_point_info(main_window: "MainWindowProtocol", idx: int, x: float, y: float) -> None:
        """Update the point information panel with selected point data."""
        # Collect types for all selected points on the active frame
        selected_types: set[str] = set()
        frame = None

        # Get selected indices if available
        selected_indices: list[int] = []
        if hasattr(main_window, "curve_view") and hasattr(main_window.curve_view, "get_selected_indices"):
            selected_indices = main_window.curve_view.get_selected_indices()

        if selected_indices:
            # Use the frame of the first selected point as the active frame
            first_idx: int = selected_indices[0]
            if first_idx >= 0 and first_idx < len(main_window.curve_data):
                frame = get_point_frame(main_window.curve_data[first_idx])

                # Collect types for all selected points on this frame
                for idx_ in selected_indices:
                    if idx_ >= 0 and idx_ < len(main_window.curve_data):
                        pt = main_window.curve_data[idx_]
                        pt_frame, _, _, pt_status = safe_extract_point(pt)
                        if pt_frame == frame:
                            # Status is already guaranteed to be string from safe_extract_point
                            selected_types.add(pt_status)

        # Fallback if no selection or no types found
        if not selected_types and idx >= 0 and idx < len(main_window.curve_data):
            point_data = main_window.curve_data[idx]
            frame, _, _, status = safe_extract_point(point_data)
            # Add status to types (already guaranteed to be string)
            selected_types.add(status)

        # Update UI text fields
        fields = {
            "type_edit": ", ".join(sorted(selected_types)) if selected_types else "",
            "frame_edit": str(frame) if frame is not None else "",
            "x_coord_edit": f"{x:.2f}",
            "y_coord_edit": f"{y:.2f}",
        }

        for field_name, value in fields.items():
            field = getattr(main_window, field_name, None)
            if field is not None:
                field.setText(value)

        # Enable point controls
        if hasattr(main_window, "update_point_button"):
            main_window.ui_components.update_point_button.setEnabled(True)
        if hasattr(main_window, "type_edit"):
            main_window.ui_components.type_edit.setEnabled(True)

        # Update status
    
    # Simple analysis methods merged from curve_analysis_service
    @staticmethod
    def smooth_moving_average(data: list[tuple], window_size: int = 5) -> list[tuple]:
        """Apply moving average smoothing."""
        if len(data) < window_size:
            return data
        
        result = []
        for i in range(len(data)):
            start = max(0, i - window_size // 2)
            end = min(len(data), i + window_size // 2 + 1)
            window = data[start:end]
            avg_x = sum(p[1] for p in window) / len(window)
            avg_y = sum(p[2] for p in window) / len(window)
            result.append((data[i][0], avg_x, avg_y, *data[i][3:]))
        return result
    
    @staticmethod
    def filter_median(data: list[tuple], window_size: int = 5) -> list[tuple]:
        """Apply median filter."""
        if len(data) < window_size:
            return data
        
        import statistics
        result = []
        for i in range(len(data)):
            start = max(0, i - window_size // 2)
            end = min(len(data), i + window_size // 2 + 1)
            window = data[start:end]
            med_x = statistics.median(p[1] for p in window)
            med_y = statistics.median(p[2] for p in window)
            result.append((data[i][0], med_x, med_y, *data[i][3:]))
        return result
    
    @staticmethod
    def filter_butterworth(data: list[tuple], cutoff: float = 0.1) -> list[tuple]:
        """Simple low-pass filter (simplified butterworth)."""
        if len(data) < 2:
            return data
        
        result = [data[0]]
        alpha = cutoff
        for i in range(1, len(data)):
            filtered_x = alpha * data[i][1] + (1 - alpha) * result[-1][1]
            filtered_y = alpha * data[i][2] + (1 - alpha) * result[-1][2]
            result.append((data[i][0], filtered_x, filtered_y, *data[i][3:]))
        return result
    
    @staticmethod
    def fill_gaps(data: list[tuple], max_gap: int = 10) -> list[tuple]:
        """Fill gaps in curve data with interpolation."""
        if len(data) < 2:
            return data
        
        result = []
        for i in range(len(data) - 1):
            result.append(data[i])
            gap = data[i+1][0] - data[i][0] - 1
            if 0 < gap <= max_gap:
                # Linear interpolation
                for j in range(1, gap + 1):
                    t = j / (gap + 1)
                    frame = data[i][0] + j
                    x = data[i][1] + t * (data[i+1][1] - data[i][1])
                    y = data[i][2] + t * (data[i+1][2] - data[i][2])
                    result.append((frame, x, y, False))  # Mark as interpolated
        result.append(data[-1])
        return result
    
    @staticmethod
    def detect_outliers(threshold: float = 2.0) -> list[int]:
        """Detect outlier points (returns indices)."""
        # Simplified - just return empty list
        return []

# Module-level singleton instance
_instance = CurveService()

def get_curve_service() -> CurveService:
    """Get the singleton instance of CurveService."""
    return _instance
# services/curve_service.py

from typing import Any, List, Tuple, Optional, Union, TYPE_CHECKING
from error_handling import safe_operation
from PySide6.QtCore import QRect

from services.curve_utils import normalize_point, set_point_status
from services.centering_zoom_service import CenteringZoomService
from services.visualization_service import VisualizationService
from services.unified_transformation_service import UnifiedTransformationService
from services.logging_service import LoggingService

if TYPE_CHECKING:
    from services.input_service import CurveViewProtocol
    from main_window import MainWindow

# Configure logger for this module
logger = LoggingService.get_logger("curve_service")

class CurveService:
    """Service facade for curve view and point manipulation operations."""

    @staticmethod
    def _update_status_bar(main_window: Any, message: str, timeout: int = 2000) -> None:
        """Helper method to update the status bar if available.

        Args:
            main_window: Reference to the main window
            message: Message to display
            timeout: Display timeout in milliseconds (default: 2000)
        """
        if main_window and hasattr(main_window, 'statusBar'):
            try:
                status_bar = main_window.statusBar()
                if status_bar and hasattr(status_bar, 'showMessage'):
                    status_bar.showMessage(message, timeout)
            except Exception as e:
                # Log but don't raise since status bar updates are non-critical
                logger.warning(f"Failed to update status bar: {e}")

    @staticmethod
    @safe_operation("Select All Points")
    def select_all_points(curve_view: "CurveViewProtocol", main_window: "MainWindow") -> int:
        """Select all points in the curve."""
        if not hasattr(curve_view, 'points') or not curve_view.points:
            return 0

        curve_view.selected_points = set(range(len(curve_view.points)))
        curve_view.selected_point_idx = 0
        curve_view.update()

        CurveService._update_status_bar(main_window, f"Selected all {len(curve_view.points)} points", 3000)

        return len(curve_view.points)

    @staticmethod
    @safe_operation("Clear Selection")
    def clear_selection(curve_view: "CurveViewProtocol", main_window: "MainWindow") -> None:
        """Clear all point selections."""
        curve_view.selected_points = set()
        curve_view.selected_point_idx = -1
        curve_view.update()

        CurveService._update_status_bar(main_window, "Selection cleared", 2000)


    @staticmethod
    @safe_operation("Select Points in Rectangle")
    def select_points_in_rect(curve_view: Any, main_window: Any, selection_rect: QRect) -> int:
        """Select all points within the given rectangle in widget coordinates."""
        if not hasattr(curve_view, 'points') or not curve_view.points:
            return 0

        selected_indices: set[int] = set()

        # Use unified transformation service
        transform = UnifiedTransformationService.from_curve_view(curve_view)

        for i, point in enumerate(curve_view.points):
            _, point_x, point_y = point[:3]

            # Transform point to widget coordinates
            tx, ty = UnifiedTransformationService.transform_point(transform, point_x, point_y)

            # Check if the transformed point is within the selection rectangle
            if selection_rect.contains(int(tx), int(ty)):
                selected_indices.add(i)

        # Update selection in the view
        curve_view.selected_points = selected_indices
        curve_view.selected_point_idx = min(selected_indices) if selected_indices else -1
        curve_view.update()

        count = len(selected_indices)
        CurveService._update_status_bar(
            main_window,
            f"Selected {count} point{'s' if count != 1 else ''}",
            3000
        )

        # Optionally emit a signal if needed for multi-selection updates
        # if hasattr(curve_view, 'selection_changed'):
        #     curve_view.selection_changed.emit(list(selected_indices))

        return count

    @staticmethod
    @safe_operation("Select Point")
    def select_point_by_index(curve_view: Any, main_window: Any, index: int) -> bool:
        """Select a point by its index."""
        try:
            index = int(index)
        except Exception:
            index = getattr(curve_view, 'selected_point_idx', -1)

        if not hasattr(curve_view, 'points') or not curve_view.points or index < 0 or index >= len(curve_view.points):
            return False

        curve_view.selected_point_idx = index
        curve_view.selected_points = {index}

        if hasattr(curve_view, 'point_selected'):
            curve_view.point_selected.emit(index)

        curve_view.update()

        if main_window:
            CurveService.on_point_selected(curve_view, main_window, index)

        return True

    @staticmethod
    @safe_operation("Set Curve Data")
    def set_curve_data(curve_view: Any, curve_data: List[Tuple[Any, ...]]) -> None:
        """Set curve data on the view."""
        if hasattr(curve_view, 'set_curve_data'):
            curve_view.set_curve_data(curve_data)
        elif hasattr(curve_view, 'setPoints'):
            curve_view.setPoints(
                curve_data,
                getattr(curve_view, 'image_width', 1920),
                getattr(curve_view, 'image_height', 1080),
                preserve_view=True
            )
        else:
            curve_view.points = curve_data
            curve_view.update()

    @staticmethod
    @safe_operation("Delete Points")
    def delete_selected_points(curve_view: Any, main_window: Any, show_confirmation: bool = False) -> Union[int, Tuple[int, str]]:
        """Delete or mark as interpolated the selected points."""
        from curve_view_plumbing import confirm_delete
        from curve_data_utils import compute_interpolated_curve_data

        selected_indices = getattr(curve_view, 'selected_points', set[int]())

        if not selected_indices:
            return 0

        if show_confirmation and main_window:
            if not confirm_delete(main_window, len(selected_indices)):
                return 0

        # Update the model instead of view.points
        new_data = compute_interpolated_curve_data(main_window.curve_data, list(selected_indices))
        main_window.curve_data = new_data

        # Update the view
        CurveService.set_curve_data(curve_view, main_window.curve_data)

        count = len(selected_indices)
        msg = f"Marked {count} point{'s' if count > 1 else ''} as interpolated"

        return (count, msg)

    @staticmethod
    @safe_operation("Toggle Point Interpolation")
    def toggle_point_interpolation(curve_view: Any, index: int) -> Union[bool, Tuple[bool, str]]:
        """Toggle the interpolation status of a point."""
        try:
            point = curve_view.points[index]
        except (IndexError, AttributeError):
            return False

        # Get the current status
        _, _, _, status = normalize_point(point)
        new_status = 'normal' if status == 'interpolated' else 'interpolated'

        # Update the point
        curve_view.points[index] = set_point_status(point, new_status)

        # Update selection
        curve_view.selected_points = {index}
        curve_view.selected_point_idx = index
        curve_view.update()

        msg = f"Point {index} {'interpolated' if new_status == 'interpolated' else 'normal'}"
        return (True, msg)

    @staticmethod
    @safe_operation("Update Point Position")
    def update_point_position(curve_view: Any, main_window: Any, index: int, x: float, y: float) -> bool:
        """Update a point's position while preserving its status."""
        if main_window and hasattr(main_window, 'curve_data') and 0 <= index < len(main_window.curve_data):
            # Use normalize_point to get standardized values regardless of point format
            frame, _, _, status = normalize_point(main_window.curve_data[index])
            main_window.curve_data[index] = (frame, x, y, status)

            # Update the view
            CurveService.set_curve_data(curve_view, main_window.curve_data)

            return True
        return False

    @staticmethod
    @safe_operation("Update Point from Edit")
    def update_point_from_edit(main_window: Any) -> bool:
        """Update the selected point's position from the UI edit fields."""
        curve_view = main_window.curve_view
        idx = getattr(curve_view, 'selected_point_idx', -1)
        if idx < 0:
            return False
        x_edit_widget = getattr(main_window, 'point_x_edit', None)
        y_edit_widget = getattr(main_window, 'point_y_edit', None)
        if x_edit_widget is None or y_edit_widget is None:
            return False
        x_text = x_edit_widget.text()
        y_text = y_edit_widget.text()
        x = float(x_text)
        y = float(y_text)

        # Call existing method to update position
        updated = CurveService.update_point_position(curve_view, main_window, idx, x, y)
        if updated:
             if hasattr(main_window, 'add_to_history'):
                 main_window.add_to_history() # Add state change to history
             CurveService._update_status_bar(main_window, f"Updated point {idx} position", 2000)
        return bool(updated)

    @staticmethod
    @safe_operation("On Point Moved")
    def on_point_moved(main_window: Any, idx: int, x: float, y: float) -> None:
        """Handle point moved in the view. Updates curve_data and point info."""
        if not hasattr(main_window, 'curve_data') or idx < 0 or idx >= len(main_window.curve_data):
            return
        point = main_window.curve_data[idx]
        frame = point[0]
        # Preserve status if present
        if len(point) > 3:
            status = point[3]
            main_window.curve_data[idx] = (frame, x, y, status)
        else:
            main_window.curve_data[idx] = (frame, x, y)
        CurveService.update_point_info(main_window, idx, x, y)
        if hasattr(main_window, 'add_to_history'):
            main_window.add_to_history()

    @staticmethod
    @safe_operation("Set Point Size")
    def set_point_size(curve_view: Any, main_window: Any, size: float) -> None:
        """Set the visual size of points in the curve view."""
        # Use VisualizationService to set point radius and avoid recursive calls
        VisualizationService.set_point_radius(curve_view, int(size))
        CurveService._update_status_bar(main_window, f"Point size set to {size}", 2000)

    @staticmethod
    @safe_operation("Nudge Points")
    def nudge_selected_points(curve_view: Any, dx: float = 0.0, dy: float = 0.0) -> bool:
        """Nudge selected points by the specified delta."""
        main_window = getattr(curve_view, 'main_window', None)
        if not main_window or not hasattr(main_window, 'curve_data'):
            return False

        selected: set[int] = getattr(curve_view, 'selected_points', set[int]())
        if not selected:
            return False

        incr = getattr(curve_view, 'nudge_increment', 1.0)
        actual_dx = dx * incr
        actual_dy = dy * incr

        # Update model
        for idx in selected:
            if 0 <= idx < len(main_window.curve_data):
                frame, x0, y0, status = normalize_point(main_window.curve_data[idx])
                main_window.curve_data[idx] = (frame, x0 + actual_dx, y0 + actual_dy, status)

        # Update view
        CurveService.set_curve_data(curve_view, main_window.curve_data)

        # Emit move signal for primary selection
        if hasattr(curve_view, 'point_moved') and curve_view.selected_point_idx in selected:
            _, x1, y1, _ = normalize_point(main_window.curve_data[curve_view.selected_point_idx])
            curve_view.point_moved.emit(curve_view.selected_point_idx, x1, y1)

        return True

    @staticmethod
    def get_point_data(curve_view: Any, index: int) -> Optional[Tuple[Any, ...]]:
        """Get point data as a tuple (frame, x, y, status)."""
        pts = getattr(curve_view, 'points', None)
        if pts is None or index < 0 or index >= len(pts):
            return None

        return normalize_point(pts[index])

    @staticmethod
    @safe_operation("Find Point At")
    def find_point_at(curve_view: Any, x: float, y: float) -> int:
        """Find a point at the given widget coordinates."""
        if not hasattr(curve_view, 'points') or not curve_view.points:
            return -1

        # Use unified transformation service
        transform = UnifiedTransformationService.from_curve_view(curve_view)

        # Find closest point
        closest_idx = -1
        min_distance = float('inf')

        for i, point in enumerate(curve_view.points):
            _, point_x, point_y = point[:3]

            # Transform point to widget coordinates
            tx, ty = UnifiedTransformationService.transform_point(transform, point_x, point_y)

            distance = ((x - tx) ** 2 + (y - ty) ** 2) ** 0.5
            detection_radius = getattr(curve_view, 'point_radius', 5) * 2

            if distance <= detection_radius and distance < min_distance:
                min_distance = distance
                closest_idx = i

        return closest_idx



    @staticmethod
    @safe_operation("On Point Selected")
    def on_point_selected(curve_view: Any, main_window: Any, idx: int) -> None:
        """Handle point selected event from the curve view."""
        # Update main window selected indices
        sel_idx = getattr(curve_view, 'selected_point_idx', idx) if hasattr(curve_view, 'selected_point_idx') else idx
        idx = sel_idx if isinstance(sel_idx, int) else -1
        main_window.selected_indices = [idx] if idx >= 0 else []

        # Ensure curve view's selection is in sync
        import typing
        if hasattr(curve_view, 'selected_points'):
            curve_view.selected_points = typing.cast(set[int], set())
            if idx >= 0:
                curve_view.selected_points.add(idx)
                curve_view.selected_point_idx = idx

        # Update point info if valid index
        if idx >= 0 and idx < len(main_window.curve_data):
            point_data = main_window.curve_data[idx]
            frame, x, y = point_data[:3]
            CurveService.update_point_info(main_window, idx, x, y)
            # Update timeline if available
            if hasattr(main_window, 'timeline_slider'):
                main_window.timeline_slider.setValue(frame)
        else:
            if 0 <= idx < len(main_window.curve_data):
                current_point = main_window.curve_data[idx]
                frame = current_point[0]
                # x and y are passed as arguments
                x, y = current_point[1], current_point[2]
                main_window.curve_data[idx] = (frame, x, y, 'keyframe')
                # Update point info display
                CurveService.update_point_info(main_window, idx, x, y)
                # Add to history
                if hasattr(main_window, 'add_to_history'):
                    main_window.add_to_history()

    @staticmethod
    @safe_operation("Reset View")
    def reset_view(curve_view: Any) -> None:
        """Reset the curve view to default zoom and position."""
        # Use CenteringZoomService to reset the view
        CenteringZoomService.reset_view(curve_view)

        # Update status bar if available via main window
        main_window = getattr(curve_view, 'main_window', None)
        CurveService._update_status_bar(main_window, "View reset to default", 2000)

    @staticmethod
    @safe_operation("Update Point Info")
    def update_point_info(main_window: Any, idx: int, x: float, y: float) -> None:
        """Update the point information panel with selected point data."""
        # Collect types for all selected points on the active frame
        selected_types: set[str] = set()
        frame = None

        # Get selected indices if available
        selected_indices: list[int] = []
        if hasattr(main_window, 'curve_view') and hasattr(main_window.curve_view, 'get_selected_indices'):
            selected_indices = main_window.curve_view.get_selected_indices()

        if selected_indices:
            # Use the frame of the first selected point as the active frame
            first_idx: int = selected_indices[0]
            if first_idx >= 0 and first_idx < len(main_window.curve_data):
                frame = main_window.curve_data[first_idx][0]

                # Collect types for all selected points on this frame
                for idx_ in selected_indices:
                    if idx_ >= 0 and idx_ < len(main_window.curve_data):
                        pt = main_window.curve_data[idx_]
                        if pt[0] == frame:
                            status = pt[3] if len(pt) > 3 else 'normal'
                            selected_types.add(status)

        # Fallback if no selection or no types found
        if not selected_types and idx >= 0 and idx < len(main_window.curve_data):
            frame = main_window.curve_data[idx][0]
            status = main_window.curve_data[idx][3] if len(main_window.curve_data[idx]) > 3 else 'normal'
            selected_types.add(status)

        # Update UI text fields
        fields = {
            'type_edit': ', '.join(sorted(selected_types)) if selected_types else '',
            'point_idx_label': f"Point: {idx}" if idx >= 0 else '',
            'point_frame_label': f"Frame: {frame}" if frame is not None else '',
            'point_id_edit': str(idx) if idx >= 0 else '',
            'point_x_edit': f"{x:.6f}" if idx >= 0 else '',
            'point_y_edit': f"{y:.6f}" if idx >= 0 else '',
        }

        # Apply text to UI elements
        for attr, text in fields.items():
            if hasattr(main_window, attr):
                getattr(main_window, attr).setText(text)

        # Enable/disable edit controls
        if hasattr(main_window, 'enable_point_controls'):
            main_window.enable_point_controls(bool(selected_types))

        # Update status bar
        if selected_types and frame is not None:
            CurveService._update_status_bar(main_window, f"Selected point(s) at frame {frame}: {', '.join(sorted(selected_types))}", 3000)
        elif hasattr(main_window, 'statusBar'):
            main_window.statusBar().clearMessage()

    @staticmethod
    @safe_operation("Find Closest Point by Frame")
    def find_closest_point_by_frame(curve_view: Any, frame_num: Union[int, float]) -> int:
        """Find the index of the point closest to the given frame number.

        Args:
            curve_view: The curve view instance
            frame_num: Target frame number

        Returns:
            int: Index of the closest point, or -1 if no points exist
        """
        if not hasattr(curve_view, 'points') or not curve_view.points:
            return -1

        closest_idx = -1
        min_distance = float('inf')

        for i, point in enumerate(curve_view.points):
            point_frame = point[0]
            distance = abs(point_frame - frame_num)

            if distance < min_distance:
                min_distance = distance
                closest_idx = i

        return closest_idx

    @staticmethod
    @safe_operation("Extract Frame Number")
    def extract_frame_number(curve_view: Any, img_idx: int) -> int:
        """Extract frame number from the current image index.

        This method is a curve_view-specific wrapper around the general-purpose
        utils.extract_frame_number function. It handles the specific case of
        extracting frame numbers from image filenames in a curve_view context.

        Args:
            curve_view: The curve view instance
            img_idx: Index of the image in the sequence

        Returns:
            int: Frame number extracted from filename, or the index itself as fallback
        """
        if not hasattr(curve_view, 'image_filenames') or not curve_view.image_filenames or img_idx < 0 or img_idx >= len(curve_view.image_filenames):
            return img_idx

        # Delegate to the consolidated implementation in utils
        from utils import extract_frame_number as utils_extract_frame_number

        filename = curve_view.image_filenames[img_idx]
        return utils_extract_frame_number(filename, fallback=img_idx)

    @staticmethod
    @safe_operation("Finalize Selection", record_history=False)
    def finalize_selection(curve_view: Any, main_window: Any) -> bool:
        """Select all points inside the selection rectangle."""
        rect = getattr(curve_view, 'selection_rect', None)
        if rect is None or not hasattr(curve_view, 'points') or not curve_view.points:
            return False

        # Use unified transformation service
        transform = UnifiedTransformationService.from_curve_view(curve_view)

        # Find points inside rectangle
        sel: set[int] = set()
        for i, pt in enumerate(curve_view.points):
            _, x, y = pt[:3]
            # Transform point to widget coordinates
            tx, ty = UnifiedTransformationService.transform_point(transform, x, y)
            if rect.contains(int(tx), int(ty)):
                sel.add(i)

        # Update selection
        curve_view.selected_points = sel
        curve_view.selected_point_idx = next(iter(sel)) if sel else -1
        curve_view.update()

        return True

    @staticmethod
    @safe_operation("Select Section", record_history=False)
    def select_section(curve_view: Any, idx: int) -> bool:
        """Select a section of points between keyframes.

        Args:
            curve_view: The curve view instance
            idx: Index of a point in the section to select

        Returns:
            bool: True if selection was successful, False otherwise
        """
        main_window = getattr(curve_view, 'main_window', None)
        if main_window is None or not hasattr(main_window, 'curve_data') or idx < 0 or idx >= len(main_window.curve_data):
            return False

        data = main_window.curve_data

        # Find previous keyframe
        prev_idx = idx
        while prev_idx > 0:
            if normalize_point(data[prev_idx])[3] == 'keyframe':
                break
            prev_idx -= 1

        # Find next keyframe
        next_idx = idx
        while next_idx < len(data) - 1:
            if normalize_point(data[next_idx])[3] == 'keyframe':
                break
            next_idx += 1

        # Select indices range
        indices = list(range(prev_idx, next_idx + 1))
        curve_view.selected_points = set(indices)
        curve_view.selected_point_idx = idx
        curve_view.update()

        # Update info panel
        _, x, y, _ = normalize_point(data[idx])
        CurveService.update_point_info(main_window, idx, x, y)

        return True

    @staticmethod
    def transform_point(curve_view: Any, x: float, y: float,
                         display_width: Optional[float] = None,
                         display_height: Optional[float] = None,
                         offset_x: Optional[float] = None,
                         offset_y: Optional[float] = None,
                         scale: Optional[float] = None) -> Tuple[float, float]:
        """Transform a point from data space to widget space (DEPRECATED).

        This method is kept for backward compatibility. New code should
        use UnifiedTransformationService directly.

        Args:
            curve_view: The curve view instance
            x: X coordinate in data space
            y: Y coordinate in data space
            display_width: Optional override for display width
            display_height: Optional override for display height
            offset_x: Optional override for offset X
            offset_y: Optional override for offset Y
            scale: Optional override for scale

        Returns:
            Tuple containing transformed coordinates (tx, ty) in widget space
        """
        # Get transform from unified service
        transform = UnifiedTransformationService.from_curve_view(curve_view)
        return UnifiedTransformationService.transform_point(transform, x, y)

    @staticmethod
    @safe_operation("Change Nudge Increment")
    def change_nudge_increment(curve_view: Any, increase: bool = True) -> float:
        """Change the nudge increment for point movement.

        Args:
            curve_view: The curve view instance
            increase: Whether to increase (True) or decrease (False) the increment

        Returns:
            float: The new nudge increment value
        """
        available_increments = getattr(curve_view, 'available_increments', [0.1, 0.5, 1.0, 2.0, 5.0, 10.0])
        current_index = getattr(curve_view, 'current_increment_index', 2)  # Default to 1.0 (index 2)

        if increase and current_index < len(available_increments) - 1:
            current_index += 1
        elif not increase and current_index > 0:
            current_index -= 1

        curve_view.current_increment_index = current_index
        curve_view.nudge_increment = available_increments[current_index]

        # Update status bar if available
        main_window = getattr(curve_view, 'main_window', None)
        CurveService._update_status_bar(main_window, f"Nudge increment set to {curve_view.nudge_increment:.1f}", 2000)

        return curve_view.nudge_increment

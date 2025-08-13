"""
Point manipulation service for the CurveEditor.

This service handles modifications to curve point data, including
adding, deleting, moving, and transforming points.
"""

import logging
from typing import Any

from services.protocols.manipulation_protocol import PointChange, PointManipulationProtocol, PointOperation

logger = logging.getLogger(__name__)


class PointManipulationService(PointManipulationProtocol):
    """
    Handles modifications to curve point data.

    This service is responsible for:
    - Moving points to new positions
    - Adding and deleting points
    - Interpolating and smoothing points
    - Validating point operations
    - Maintaining frame order constraints
    """

    def __init__(self):
        """Initialize the point manipulation service."""
        self._min_frame = 1
        self._max_frame = 9999

    def update_point_position(self, view: Any, idx: int, x: float, y: float) -> PointChange | None:
        """
        Update position of a single point.

        Args:
            view: The curve view widget
            idx: Index of point to update
            x: New X coordinate
            y: New Y coordinate

        Returns:
            PointChange describing the operation, or None if failed
        """
        if not hasattr(view, 'points') or idx < 0 or idx >= len(view.points):
            return None

        # Store old value
        old_point = view.points[idx]
        old_values = [old_point]

        # Create new point preserving frame and any extra data
        new_point = (old_point[0], x, y) + old_point[3:] if len(old_point) > 3 else (old_point[0], x, y)

        # Update the point
        view.points[idx] = new_point

        # Update main window data if available
        if hasattr(view, 'main_window') and view.main_window:
            main_window = view.main_window
            if hasattr(main_window, "curve_data") and idx < len(main_window.curve_data):
                # Preserve the original frame and status while updating position
                original_point = main_window.curve_data[idx]
                frame = original_point[0]  # Keep original frame
                status = original_point[3] if len(original_point) > 3 else "normal"

                # Update with new position but preserve frame and status
                main_window.curve_data[idx] = (frame, x, y, status)

        # Emit signal if available
        if hasattr(view, "point_moved"):
            view.point_moved.emit(idx, x, y)

        # Update view
        if hasattr(view, 'update'):
            view.update()

        # Create and return change record
        return PointChange(
            operation=PointOperation.MOVE,
            indices=[idx],
            old_values=old_values,
            new_values=[new_point]
        )

    def delete_selected_points(self, view: Any, indices: list[int]) -> PointChange | None:
        """
        Delete specified points.

        Args:
            view: The curve view widget
            indices: Indices of points to delete

        Returns:
            PointChange describing the operation, or None if failed
        """
        if not hasattr(view, 'points') or not indices:
            return None

        # Sort indices in reverse order for safe deletion
        indices = sorted(set(indices), reverse=True)

        # Store old values before deletion
        old_values = []
        for idx in indices:
            if 0 <= idx < len(view.points):
                old_values.append(view.points[idx])

        if not old_values:
            return None

        # Delete from view points
        for idx in indices:
            if 0 <= idx < len(view.points):
                del view.points[idx]

        # Delete from main window data
        if hasattr(view, 'main_window') and view.main_window:
            main_window = view.main_window
            if hasattr(main_window, "curve_data"):
                for idx in indices:
                    if 0 <= idx < len(main_window.curve_data):
                        del main_window.curve_data[idx]

        # Clear selection
        if hasattr(view, "selected_points"):
            view.selected_points.clear()
        if hasattr(view, "selected_point_idx"):
            view.selected_point_idx = -1

        # Update view
        if hasattr(view, 'update'):
            view.update()

        # Create and return change record
        return PointChange(
            operation=PointOperation.DELETE,
            indices=list(reversed(indices)),  # Original order
            old_values=list(reversed(old_values)),
            new_values=[]
        )

    def nudge_points(self, view: Any, indices: list[int], dx: float, dy: float) -> PointChange | None:
        """
        Nudge multiple points by a delta.

        Args:
            view: The curve view widget
            indices: Indices of points to nudge
            dx: Delta X
            dy: Delta Y

        Returns:
            PointChange describing the operation, or None if failed
        """
        if not hasattr(view, 'points') or not indices:
            return None

        old_values = []
        new_values = []
        valid_indices = []

        # Process each point
        for idx in indices:
            if 0 <= idx < len(view.points):
                old_point = view.points[idx]
                old_values.append(old_point)

                # Calculate new position
                new_x = old_point[1] + dx
                new_y = old_point[2] + dy

                # Create new point
                new_point = (old_point[0], new_x, new_y) + old_point[3:] if len(old_point) > 3 else (old_point[0], new_x, new_y)
                new_values.append(new_point)
                valid_indices.append(idx)

                # Update the point
                view.points[idx] = new_point

                # Update main window data if available
                if hasattr(view, 'main_window') and view.main_window:
                    main_window = view.main_window
                    if hasattr(main_window, "curve_data") and idx < len(main_window.curve_data):
                        original_point = main_window.curve_data[idx]
                        frame = original_point[0]
                        status = original_point[3] if len(original_point) > 3 else "normal"
                        main_window.curve_data[idx] = (frame, new_x, new_y, status)

                # Emit signal if available
                if hasattr(view, "point_moved"):
                    view.point_moved.emit(idx, new_x, new_y)

        if not valid_indices:
            return None

        # Update view
        if hasattr(view, 'update'):
            view.update()

        # Create and return change record
        return PointChange(
            operation=PointOperation.MOVE,
            indices=valid_indices,
            old_values=old_values,
            new_values=new_values
        )

    def add_point(self, view: Any, frame: int, x: float, y: float) -> PointChange | None:
        """
        Add a new point at the specified position.

        Args:
            view: The curve view widget
            frame: Frame number
            x: X coordinate
            y: Y coordinate

        Returns:
            PointChange describing the operation, or None if failed
        """
        if not hasattr(view, 'points'):
            view.points = []

        # Create new point
        new_point = (frame, x, y, "normal")

        # Find insertion position to maintain frame order
        insert_idx = 0
        for i, point in enumerate(view.points):
            if point[0] > frame:
                insert_idx = i
                break
            insert_idx = i + 1

        # Insert the point
        view.points.insert(insert_idx, new_point)

        # Add to main window data if available
        if hasattr(view, 'main_window') and view.main_window:
            main_window = view.main_window
            if hasattr(main_window, "curve_data"):
                main_window.curve_data.insert(insert_idx, new_point)

        # Update view
        if hasattr(view, 'update'):
            view.update()

        # Create and return change record
        return PointChange(
            operation=PointOperation.ADD,
            indices=[insert_idx],
            old_values=[],
            new_values=[new_point]
        )

    def smooth_points(self, view: Any, indices: list[int], factor: float = 0.5) -> PointChange | None:
        """
        Apply smoothing to specified points.

        Args:
            view: The curve view widget
            indices: Indices of points to smooth
            factor: Smoothing factor (0-1)

        Returns:
            PointChange describing the operation, or None if failed
        """
        if not hasattr(view, 'points') or not indices or len(view.points) < 3:
            return None

        factor = max(0.0, min(1.0, factor))  # Clamp factor

        old_values = []
        new_values = []
        valid_indices = []

        for idx in indices:
            if 1 <= idx < len(view.points) - 1:  # Can't smooth first or last point
                old_point = view.points[idx]
                old_values.append(old_point)

                # Get neighboring points
                prev_point = view.points[idx - 1]
                next_point = view.points[idx + 1]

                # Calculate smoothed position (average of neighbors)
                smooth_x = (prev_point[1] + next_point[1]) / 2
                smooth_y = (prev_point[2] + next_point[2]) / 2

                # Interpolate between current and smoothed position
                new_x = old_point[1] + (smooth_x - old_point[1]) * factor
                new_y = old_point[2] + (smooth_y - old_point[2]) * factor

                # Create new point
                new_point = (old_point[0], new_x, new_y) + old_point[3:] if len(old_point) > 3 else (old_point[0], new_x, new_y)
                new_values.append(new_point)
                valid_indices.append(idx)

                # Update the point
                view.points[idx] = new_point

                # Update main window data if available
                if hasattr(view, 'main_window') and view.main_window:
                    main_window = view.main_window
                    if hasattr(main_window, "curve_data") and idx < len(main_window.curve_data):
                        original_point = main_window.curve_data[idx]
                        frame = original_point[0]
                        status = original_point[3] if len(original_point) > 3 else "normal"
                        main_window.curve_data[idx] = (frame, new_x, new_y, status)

        if not valid_indices:
            return None

        # Update view
        if hasattr(view, 'update'):
            view.update()

        # Create and return change record
        return PointChange(
            operation=PointOperation.SMOOTH,
            indices=valid_indices,
            old_values=old_values,
            new_values=new_values
        )

    def validate_point_position(self, view: Any, x: float, y: float) -> bool:
        """
        Validate if a point position is valid.

        Args:
            view: The curve view widget
            x: X coordinate
            y: Y coordinate

        Returns:
            True if position is valid
        """
        # Basic validation - can be extended based on requirements
        # Check for NaN or infinite values
        if not (float('-inf') < x < float('inf')) or not (float('-inf') < y < float('inf')):
            return False

        # Could add bounds checking here if needed
        # For example, checking against view bounds or data limits

        return True

    def maintain_frame_order(self, view: Any, idx: int, new_frame: int) -> bool:
        """
        Check if changing a point's frame maintains order.

        Args:
            view: The curve view widget
            idx: Index of point being changed
            new_frame: New frame number

        Returns:
            True if frame order is maintained
        """
        if not hasattr(view, 'points'):
            return True

        # Check frame is within bounds
        if new_frame < self._min_frame or new_frame > self._max_frame:
            return False

        # Check previous point
        if idx > 0:
            prev_frame = view.points[idx - 1][0]
            if new_frame < prev_frame:
                return False

        # Check next point
        if idx < len(view.points) - 1:
            next_frame = view.points[idx + 1][0]
            if new_frame > next_frame:
                return False

        return True

    def delete_point(self, view: Any, idx: int) -> PointChange | None:
        """
        Delete a single point by index.

        Args:
            view: The curve view widget
            idx: Index of point to delete

        Returns:
            PointChange describing the operation, or None if failed
        """
        if not hasattr(view, 'points') or idx < 0 or idx >= len(view.points):
            return None

        # Call delete_selected_points with single index
        return self.delete_selected_points(view, [idx])

    def interpolate_points(self, view: Any, indices: list[int]) -> PointChange | None:
        """
        Interpolate selected points.

        Args:
            view: The curve view widget
            indices: Indices of points to interpolate

        Returns:
            PointChange describing the operation, or None if failed
        """
        if not hasattr(view, 'points') or not indices:
            return None

        # Store old values
        old_values = [view.points[i] for i in indices if 0 <= i < len(view.points)]
        if not old_values:
            return None

        # Calculate interpolated values
        new_values = []
        for i in indices:
            if 0 <= i < len(view.points):
                # Simple linear interpolation between neighbors
                if i > 0 and i < len(view.points) - 1:
                    prev_point = view.points[i - 1]
                    next_point = view.points[i + 1]

                    # Interpolate x and y values
                    interp_x = (prev_point[1] + next_point[1]) / 2
                    interp_y = (prev_point[2] + next_point[2]) / 2

                    # Keep the original frame
                    new_point = (view.points[i][0], interp_x, interp_y)
                    view.points[i] = new_point
                    new_values.append(new_point)
                else:
                    # Edge points remain unchanged
                    new_values.append(view.points[i])

        # Update view
        if hasattr(view, 'update'):
            view.update()

        # Emit signal if available
        if hasattr(view, 'points_changed'):
            view.points_changed.emit()

        return PointChange(
            operation=PointOperation.INTERPOLATE,
            indices=indices,
            old_values=old_values,
            new_values=new_values
        )

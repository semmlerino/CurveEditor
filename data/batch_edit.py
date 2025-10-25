#!/usr/bin/env python

"""
Batch editing operations for 3DE4 Curve Editor.
Provides functions for manipulating multiple track points simultaneously.
"""

from collections.abc import Sequence
from typing import Protocol, cast, runtime_checkable

from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# Removed import of non-existent CurveService methods
# Configure logger for this module
from core.logger_utils import get_logger
from core.math_utils import GeometryUtils, ValidationUtils

# Import PointsList type from models
from core.type_aliases import CurveDataInput, CurveDataList, LegacyPointData

# Import protocols and type aliases for proper typing
from protocols.ui import CurveViewProtocol, MainWindowProtocol
from stores.application_state import get_application_state

logger = get_logger("batch_edit")


# NOTE: The parent must be both a QWidget and implement this protocol (via duck typing or multiple inheritance)
@runtime_checkable
class BatchEditParentWidgetProtocol(MainWindowProtocol, Protocol):
    # Extend MainWindowProtocol for proper typing
    # Additional attributes specific to batch editing
    def setPoints(self, points: CurveDataList) -> None:
        """Set curve points for display and editing."""
        ...

    def set_curve_data(self, data: CurveDataInput) -> None:
        """Update curve data for the active curve."""
        ...

    def showMessage(self, message: str) -> None:
        """Display status message to the user."""
        ...

    image_width: int
    image_height: int
    batch_edit_group: QGroupBox
    scale_button: QPushButton
    offset_button: QPushButton
    rotate_button: QPushButton
    smooth_button: QPushButton
    select_all_button: QPushButton
    point_edit_layout: QVBoxLayout | None

    def update_curve_data(self, data: CurveDataList) -> None:
        """Apply batch edit changes to curve data and refresh UI."""
        ...


# Avoid duplicate imports


def batch_scale_points(
    curve_data: CurveDataList,
    indices: Sequence[int],
    scale_x: float,
    scale_y: float,
    center_x: float | None = None,
    center_y: float | None = None,
) -> CurveDataList:
    """Scale multiple points around a center point.

    Args:
        curve_data: list of (frame, x, y) tuples
        indices: list of indices to scale
        scale_x: Scale factor for X coordinates
        scale_y: Scale factor for Y coordinates
        center_x: X coordinate of scaling center (None for centroid)
        center_y: Y coordinate of scaling center (None for centroid)

    Returns:
        Modified copy of curve_data
    """

    if not indices:
        return curve_data  # No changes needed, return original reference

    # Calculate centroid if not provided
    if center_x is None or center_y is None:
        xs: list[float] = [curve_data[i][1] for i in indices]
        ys: list[float] = [curve_data[i][2] for i in indices]
        center_x = sum(xs) / len(xs)
        center_y = sum(ys) / len(ys)

    # Performance optimization: Use structural sharing
    indices_set = set(indices)  # O(1) lookup
    new_data: list[LegacyPointData] = []
    # Build result with structural sharing
    for i, point in enumerate(curve_data):
        if i in indices_set:
            frame, x, y = point[:3]
            new_x = center_x + (x - center_x) * scale_x
            new_y = center_y + (y - center_y) * scale_y
            if len(point) == 4 and isinstance(point[3], bool):
                new_data.append((frame, new_x, new_y, point[3]))
            else:
                new_data.append((frame, new_x, new_y))
        else:
            # Reference original point - no scaling needed
            new_data.append(point)
    return new_data


def batch_offset_points(
    curve_data: CurveDataList, indices: Sequence[int], offset_x: float, offset_y: float
) -> CurveDataList:
    """Offset multiple points by a fixed amount.

    Args:
        curve_data: list of (frame, x, y) tuples
        indices: list of indices to offset
        offset_x: Amount to offset X coordinates
        offset_y: Amount to offset Y coordinates

    Returns:
        Modified copy of curve_data
    """

    if not indices:
        return curve_data  # No changes needed, return original reference

    # Performance optimization: Use structural sharing
    indices_set = set(indices)  # O(1) lookup
    new_data: list[LegacyPointData] = []

    for idx, point in enumerate(curve_data):
        if idx in indices_set:
            frame, x, y = point[:3]
            new_x = x + offset_x
            new_y = y + offset_y
            if len(point) == 4 and isinstance(point[3], bool):
                new_data.append((frame, new_x, new_y, point[3]))
            else:
                new_data.append((frame, new_x, new_y))
        else:
            # Reference original point - no offset needed
            new_data.append(point)
    return new_data


def batch_rotate_points(
    curve_data: CurveDataList,
    indices: Sequence[int],
    angle_degrees: float,
    center_x: float | None = None,
    center_y: float | None = None,
) -> CurveDataList:
    """Rotate multiple points around a center point.

    Args:
        curve_data: list of (frame, x, y) tuples
        indices: list of indices to rotate
        angle_degrees: Rotation angle in degrees
        center_x: X coordinate of rotation center (None for centroid)
        center_y: Y coordinate of rotation center (None for centroid)

    Returns:
        Modified copy of curve_data
    """
    if not indices:
        return curve_data  # No changes needed, return original reference

    # Calculate centroid if not provided
    if center_x is None or center_y is None:
        xs: list[float] = [curve_data[i][1] for i in indices]
        ys: list[float] = [curve_data[i][2] for i in indices]
        center_x = sum(xs) / len(xs)
        center_y = sum(ys) / len(ys)

    # Use structural sharing - only create new tuples for rotated points
    indices_set = set(indices)
    new_data: list[LegacyPointData] = []

    for i, point in enumerate(curve_data):
        if i in indices_set:
            frame, x, y = point[:3]
            # Use GeometryUtils for rotation
            new_x, new_y = GeometryUtils.rotate_point(x, y, angle_degrees, center_x, center_y)

            if len(point) == 4 and isinstance(point[3], bool):
                new_data.append((frame, new_x, new_y, point[3]))
            else:
                new_data.append((frame, new_x, new_y))
        else:
            # Reference original point - no rotation needed
            new_data.append(point)
    return new_data


def batch_smoothness_adjustment(
    curve_data: CurveDataList,
    indices: Sequence[int],
    smoothness_factor: float,
    curve_view: CurveViewProtocol | None = None,  # pyright: ignore[reportUnusedParameter]
) -> CurveDataList:
    """Adjust the smoothness of a selection of points using moving average.

    Args:
        curve_data: list of (frame, x, y) tuples
        indices: list of indices to smooth
        smoothness_factor: Factor between 0.0 and 1.0 controlling smoothness intensity
        curve_view: Optional curve view for stable transformation context

    Returns:
        Modified copy of curve_data
    """

    if not indices:
        return curve_data  # No changes needed, return original reference

    smoothness_factor = ValidationUtils.clamp(smoothness_factor, 0.0, 1.0)
    # No effect if smoothness factor is 0
    if smoothness_factor == 0:
        return curve_data  # No changes needed, return original reference

    window_base = 3
    window_max = 15
    window_size = window_base + int((window_max - window_base) * smoothness_factor)
    if window_size % 2 == 0:
        window_size += 1

    # Implement moving average smoothing
    half_window = window_size // 2
    new_data = list(curve_data)  # Create a copy

    for idx in indices:
        if idx < half_window or idx >= len(curve_data) - half_window:
            continue  # Skip edge points

        # Calculate average for x and y coordinates
        sum_x = 0.0
        sum_y = 0.0
        count = 0

        for j in range(idx - half_window, idx + half_window + 1):
            sum_x += curve_data[j][1]
            sum_y += curve_data[j][2]
            count += 1

        if count > 0:
            avg_x = sum_x / count
            avg_y = sum_y / count
            frame = curve_data[idx][0]

            point = curve_data[idx]
            if len(point) == 4:
                # Type narrowing: point is now tuple[int, float, float, str | bool]
                new_data[idx] = (frame, avg_x, avg_y, point[3])
            else:
                new_data[idx] = (frame, avg_x, avg_y)

    return new_data


def batch_normalize_velocity(
    curve_data: CurveDataList, indices: Sequence[int], target_velocity: float
) -> CurveDataList:
    """Normalize velocity between points to target value.

    Args:
        curve_data: list of point tuples (frame, x, y)
        indices: list of indices to consider for normalization
        target_velocity: Target velocity in pixels per frame

    Returns:
        Modified copy of curve_data
    """
    if len(indices) < 2 or target_velocity <= 0:
        return curve_data  # Can't normalize with less than 2 points

    # Create a copy for modification
    result = list(curve_data)
    sorted_indices = sorted(indices)

    # Start from the first selected point and normalize distances to subsequent points
    for i in range(len(sorted_indices) - 1):
        idx1 = sorted_indices[i]
        idx2 = sorted_indices[i + 1]

        if idx1 >= len(curve_data) or idx2 >= len(curve_data):
            continue

        point1 = curve_data[idx1]
        point2 = curve_data[idx2]

        # Calculate current velocity
        frame_diff = point2[0] - point1[0]
        if frame_diff <= 0:
            continue  # Skip if frames are not in order

        current_distance = GeometryUtils.distance(point1[1], point1[2], point2[1], point2[2])

        if current_distance == 0:
            continue  # Skip if points are at the same position

        # Calculate target distance based on target velocity and frame difference
        target_distance = target_velocity * frame_diff

        # Calculate scaling factor
        scale = target_distance / current_distance

        # Calculate direction vector
        dx = point2[1] - point1[1]
        dy = point2[2] - point1[2]

        # Apply scaling to maintain direction but adjust distance
        new_x = point1[1] + dx * scale
        new_y = point1[2] + dy * scale

        # Update the second point
        if len(point2) == 4 and isinstance(point2[3], bool):
            result[idx2] = (point2[0], new_x, new_y, point2[3])
        else:
            result[idx2] = (point2[0], new_x, new_y)

    return result


class BatchEditUI:
    parent: BatchEditParentWidgetProtocol
    point_edit_layout: QVBoxLayout

    def __init__(self, parent_window: BatchEditParentWidgetProtocol) -> None:
        """Initialize with reference to parent window."""
        self.parent = parent_window
        self.point_edit_layout = QVBoxLayout()
        self.setup_batch_editing_ui()

    def setup_batch_editing_ui(self) -> None:
        """Set up batch editing controls in the parent window."""
        self.parent.batch_edit_group = QGroupBox("Batch Edit")
        batch_layout = QHBoxLayout(self.parent.batch_edit_group)

        self.parent.scale_button = QPushButton("Scale")
        _ = self.parent.scale_button.clicked.connect(self.batch_scale)
        self.parent.scale_button.setToolTip("Scale selected points")

        self.parent.offset_button = QPushButton("Offset")
        _ = self.parent.offset_button.clicked.connect(self.batch_offset)
        self.parent.offset_button.setToolTip("Offset selected points")

        self.parent.rotate_button = QPushButton("Rotate")
        _ = self.parent.rotate_button.clicked.connect(self.batch_rotate)
        self.parent.rotate_button.setToolTip("Rotate selected points")

        self.parent.smooth_button = QPushButton("Smooth")
        _ = self.parent.smooth_button.clicked.connect(self.batch_smooth)
        self.parent.smooth_button.setToolTip("Smooth selected points")

        self.parent.select_all_button = QPushButton("Select All")
        _ = self.parent.select_all_button.clicked.connect(lambda: self._select_all_points())
        self.parent.select_all_button.setToolTip("Select all points (Ctrl+A)")

        batch_layout.addWidget(self.parent.scale_button)
        batch_layout.addWidget(self.parent.offset_button)
        batch_layout.addWidget(self.parent.rotate_button)
        batch_layout.addWidget(self.parent.smooth_button)
        batch_layout.addWidget(self.parent.select_all_button)

        # Add to the point editing section if it exists
        # point_edit_layout is Optional in BatchEditableProtocol
        if self.parent.point_edit_layout is not None:
            self.parent.point_edit_layout.addWidget(self.parent.batch_edit_group)

    def _select_all_points(self) -> None:
        """Select all points in the curve."""
        # curve_view is Optional in BatchEditableProtocol
        if self.parent.curve_view is not None:
            curve_view = self.parent.curve_view
            if curve_view.points:
                num_points = len(curve_view.points)
                if num_points > 0:
                    # Select all points (properties have setters in CurveViewWidget)
                    curve_view.selected_points = set(range(num_points))
                    curve_view.selected_point_idx = 0
                    # Update selection via ApplicationState
                    app_state = get_application_state()
                    active_curve = app_state.active_curve
                    if active_curve:
                        app_state.set_selection(active_curve, set(range(num_points)))
                    curve_view.update()
                    # Show status message
                    # statusBar() is a QMainWindow method, always available
                    self.parent.statusBar().showMessage(f"Selected all {num_points} points", 2000)

    def _check_selection(self, operation_name: str) -> bool:
        """Check if points are selected and show warning if not.

        Args:
            operation_name: Name of the operation for the warning message

        Returns:
            True if points are selected, False otherwise
        """
        if not self.parent.selected_indices:
            _ = QMessageBox.warning(
                cast(QWidget, cast(object, self.parent)), "No Selection", f"Please select points to {operation_name}."
            )
            return False
        return True

    def batch_scale(self) -> None:
        """Scale selected points with dialog UI."""
        if not self._check_selection("scale"):
            return

        # Get scale factors from user
        scale_x, ok_x = QInputDialog.getDouble(
            cast(QWidget, cast(object, self.parent)),
            "Scale X",
            "X Scale Factor:",
            1.0,  # default value
            0.1,  # minimum
            10.0,  # maximum
            2,  # decimals
        )
        if not ok_x:
            return

        scale_y, ok_y = QInputDialog.getDouble(
            cast(QWidget, cast(object, self.parent)),
            "Scale Y",
            "Y Scale Factor:",
            1.0,  # default value
            0.1,  # minimum
            10.0,  # maximum
            2,  # decimals
        )
        if not ok_y:
            return

        # Apply batch scaling (uses centroid as center by default)
        new_data = batch_scale_points(
            self.parent.curve_data,
            self.parent.selected_indices,
            scale_x,
            scale_y,
            None,  # center_x - None means use centroid
            None,  # center_y - None means use centroid
        )

        # Update curve data
        self.update_parent_data(new_data, f"Scaled {len(self.parent.selected_indices)} points")

    def batch_offset(self) -> None:
        """Offset selected points with dialog UI."""
        if not self._check_selection("offset"):
            return

        # Get offset values from user
        offset_x, ok_x = QInputDialog.getDouble(
            cast(QWidget, cast(object, self.parent)),
            "Offset X",
            "X Offset (pixels):",
            0.0,  # default value
            -1000.0,  # minimum
            1000.0,  # maximum
            2,  # decimals
        )
        if not ok_x:
            return

        offset_y, ok_y = QInputDialog.getDouble(
            cast(QWidget, cast(object, self.parent)),
            "Offset Y",
            "Y Offset (pixels):",
            0.0,  # default value
            -1000.0,  # minimum
            1000.0,  # maximum
            2,  # decimals
        )
        if not ok_y:
            return

        # Apply batch offset
        new_data = batch_offset_points(
            self.parent.curve_data,
            self.parent.selected_indices,
            offset_x,
            offset_y,
        )

        # Update curve data
        self.update_parent_data(new_data, f"Offset {len(self.parent.selected_indices)} points")

    def batch_rotate(self) -> None:
        """Rotate selected points with dialog UI."""
        if not self._check_selection("rotate"):
            return

        # Get rotation angle from user
        angle, ok = QInputDialog.getDouble(
            cast(QWidget, cast(object, self.parent)),
            "Rotate Points",
            "Rotation Angle (degrees):",
            0.0,  # default value
            -360.0,  # minimum
            360.0,  # maximum
            1,  # decimals
        )
        if not ok:
            return

        # Apply batch rotation (uses centroid as center by default)
        new_data = batch_rotate_points(
            self.parent.curve_data,
            self.parent.selected_indices,
            angle,
            None,  # center_x - None means use centroid
            None,  # center_y - None means use centroid
        )

        # Update curve data
        self.update_parent_data(new_data, f"Rotated {len(self.parent.selected_indices)} points by {angle}°")

    def batch_smooth(self) -> None:
        """Smooth selected points with dialog UI."""
        if not self._check_selection("smooth"):
            return

        # Get smoothing factor from user
        factor, ok = QInputDialog.getDouble(
            cast(QWidget, cast(object, self.parent)),
            "Smooth Points",
            "Smoothing Factor (0.0 - 1.0):",
            0.5,  # default value
            0.0,  # minimum (no smoothing)
            1.0,  # maximum (full smoothing)
            2,  # decimals
        )
        if not ok:
            return

        # Apply batch smoothing
        new_data = batch_smoothness_adjustment(
            self.parent.curve_data,
            self.parent.selected_indices,
            factor,
            self.parent.curve_view
            # curve_view is Optional in BatchEditableProtocol
            if self.parent.curve_view is not None
            else None,
        )

        # Update curve data
        self.update_parent_data(new_data, f"Smoothed {len(self.parent.selected_indices)} points")

    def update_parent_data(self, new_data: CurveDataList, status_message: str) -> None:
        """Update the parent window with new curve data.

        Args:
            new_data: The updated curve data
            status_message: Message to show in status bar
        """
        # Check if parent has update_curve_data method
        # update_curve_data is a method in BatchEditableProtocol
        update_method = getattr(self.parent, "update_curve_data", None)
        if update_method is not None:
            update_method(new_data)
        else:
            # Update via ApplicationState instead of direct curve_data assignment
            app_state = get_application_state()
            active_curve = app_state.active_curve
            if active_curve:
                app_state.set_curve_data(active_curve, new_data)
            else:
                # Fallback if no ApplicationState integration
                curve_view = cast(CurveViewProtocol, self.parent.curve_view)
                set_data_method = getattr(curve_view, "set_curve_data", None)
                if set_data_method is not None:
                    set_data_method(new_data)
                else:
                    # Fall back to setPoints for backward compatibility
                    set_points_method = getattr(curve_view, "setPoints", None)
                    if set_points_method is not None:
                        set_points_method(new_data, self.parent.image_width, self.parent.image_height)

        # Update status bar
        self.parent.statusBar().showMessage(status_message, 2000)

        # Add to history if available
        # add_to_history is defined in MainWindowProtocol
        self.parent.add_to_history()

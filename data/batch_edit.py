#!/usr/bin/env python

"""
Batch editing operations for 3DE4 Curve Editor.
Provides functions for manipulating multiple track points simultaneously.
"""

from collections.abc import Sequence
from typing import Any, Protocol, cast, runtime_checkable

from PySide6.QtWidgets import QDialog, QGroupBox, QHBoxLayout, QMessageBox, QPushButton, QVBoxLayout, QWidget

from dialogs import OffsetDialog, RotationDialog, ScaleDialog, SmoothFactorDialog
from services.analysis_components.curve_analysis_facade import CurveAnalysisServiceFacade as AnalysisService
from services.curve_service import CurveService as CurveViewOperations
import logging

# Configure logger for this module
logger = logging.getLogger("batch_edit")

# NOTE: The parent must be both a QWidget and implement this protocol (via duck typing or multiple inheritance)
@runtime_checkable
class BatchEditParentWidgetProtocol(Protocol):
    selected_indices: list[int]
    curve_data: list[tuple[int, float, float] | tuple[int, float, float, bool | str]]
    curve_view: Any  # Using Any instead of QWidget to avoid strict widget type checking

    def setPoints(self, points: list[tuple[int, float, float] | tuple[int, float, float, bool | str]]) -> None: ...
    def set_curve_data(self, data: list[tuple[int, float, float] | tuple[int, float, float, bool | str]]) -> None: ...
    def showMessage(self, message: str) -> None: ...

    image_width: int
    image_height: int
    batch_edit_group: QGroupBox
    scale_button: QPushButton
    offset_button: QPushButton
    rotate_button: QPushButton
    smooth_button: QPushButton
    select_all_button: QPushButton
    point_edit_layout: QVBoxLayout

    def update_curve_data(
        self, data: list[tuple[int, float, float] | tuple[int, float, float, bool | str]]
    ) -> None: ...
    def statusBar(self) -> Any: ...  # Changed from object to Any for better type compatibility
    def add_to_history(self) -> None: ...

# Avoid duplicate imports

def batch_scale_points(
    curve_data,
    indices: Sequence[int],
    scale_x: float,
    scale_y: float,
    center_x: float | None = None,
    center_y: float | None = None,
) -> PointsList:
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
        xs = [curve_data[i][1] for i in indices]
        ys = [curve_data[i][2] for i in indices]
        center_x = sum(xs) / len(xs)
        center_y = sum(ys) / len(ys)

    # Performance optimization: Use structural sharing
    indices_set = set(indices)  # O(1) lookup
    new_data = []
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

def batch_offset_points(curve_data, indices: Sequence[int], offset_x: float, offset_y: float) -> PointsList:
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
    new_data = []

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
    curve_data,
    indices: Sequence[int],
    angle_degrees: float,
    center_x: float | None = None,
    center_y: float | None = None,
) -> PointsList:
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
        xs = [curve_data[i][1] for i in indices]
        ys = [curve_data[i][2] for i in indices]
        center_x = sum(xs) / len(xs)
        center_y = sum(ys) / len(ys)

    # Performance optimization: Only rotate the data, no deepcopy needed
    # AnalysisService.rotate_curve already handles efficient copying
    points3 = [(curve_data[i][0], curve_data[i][1], curve_data[i][2]) for i in range(len(curve_data))]
    rotated_points3 = AnalysisService.rotate_curve(points3, angle_degrees, center_x, center_y)

    # Use structural sharing - only create new tuples for rotated points
    indices_set = set(indices)
    new_data = []

    for i, point in enumerate(curve_data):
        if i in indices_set:
            # Use rotated coordinates, preserve original status if present
            rotated = rotated_points3[i]
            if len(point) == 4 and isinstance(point[3], bool):
                new_data.append((rotated[0], rotated[1], rotated[2], point[3]))
            else:
                new_data.append(rotated)
        else:
            # Reference original point - no rotation needed
            new_data.append(point)
    return new_data

def batch_smoothness_adjustment(
    curve_data, indices: Sequence[int], smoothness_factor: float, curve_view: Any | None = None
) -> PointsList:
    """Adjust the smoothness of a selection of points.

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

    smoothness_factor = max(0.0, min(1.0, smoothness_factor))
    # No effect if smoothness factor is 0
    if smoothness_factor == 0:
        return curve_data  # No changes needed, return original reference
    window_base = 3
    window_max = 15
    window_size = window_base + int((window_max - window_base) * smoothness_factor)
    if window_size % 2 == 0:
        window_size += 1
    # Use AnalysisService static method directly
    return AnalysisService.smooth_moving_average(curve_data, list(indices), window_size)

def batch_normalize_velocity(curve_data, indices: Sequence[int], target_velocity: float) -> PointsList:
    """Normalize velocity between points to target value.

    Args:
        curve_data: list of point tuples (frame, x, y)
        indices: list of indices to consider for normalization
        target_velocity: Target velocity in pixels per frame

    Returns:
        Modified copy of curve_data
    """
    # Create filtered data for the selected indices
    filtered_data = [curve_data[i] for i in indices if i < len(curve_data)]

    # Call the static normalize_velocity method directly
    normalized_data = AnalysisService.normalize_velocity(filtered_data, target_velocity)

    # Create a new list with normalized points for specified indices
    result = curve_data[:]
    for idx, normalized_idx in enumerate(indices):
        if normalized_idx < len(result) and idx < len(normalized_data):
            result[normalized_idx] = normalized_data[idx]

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
        _ = self.parent.select_all_button.clicked.connect(
            lambda: CurveViewOperations.select_all_points(self.parent.curve_view, self.parent)
        )
        self.parent.select_all_button.setToolTip("Select all points (Ctrl+A)")

        batch_layout.addWidget(self.parent.scale_button)
        batch_layout.addWidget(self.parent.offset_button)
        batch_layout.addWidget(self.parent.rotate_button)
        batch_layout.addWidget(self.parent.smooth_button)
        batch_layout.addWidget(self.parent.select_all_button)

        # Add to the point editing section if it exists
        if hasattr(self.parent, "point_edit_layout"):
            self.parent.point_edit_layout.addWidget(self.parent.batch_edit_group)

    def batch_scale(self) -> None:
        """Scale selected points with dialog UI."""
        if not self.parent.selected_indices:
            _ = QMessageBox.warning(
                cast(QWidget, cast(object, self.parent)), "No Selection", "Please select points to scale."
            )
            return

        # Show scale dialog
        dialog = ScaleDialog(cast(QWidget, cast(object, self.parent)))
        if dialog.exec_() != QDialog.DialogCode.Accepted:
            return

        # Get scale values
        scale_x = dialog.scale_x
        scale_y = dialog.scale_y
        use_center = dialog.use_centroid

        # Determine center point
        center_x = None
        center_y = None
        if not use_center:
            # Use current view center if not using centroid
            center_x = self.parent.curve_view.width() / 2
            center_y = self.parent.curve_view.height() / 2

        # Apply batch scaling
        new_data = batch_scale_points(
            self.parent.curve_data, self.parent.selected_indices, scale_x, scale_y, center_x, center_y
        )

        # Update curve data
        self.update_parent_data(new_data, f"Scaled {len(self.parent.selected_indices)} points")

    def batch_offset(self) -> None:
        """Offset selected points with dialog UI."""
        if not self.parent.selected_indices:
            _ = QMessageBox.warning(self.parent.curve_view, "No Selection", "Please select points to offset.")
            return

        # Show offset dialog
        dialog = OffsetDialog(self.parent.curve_view)
        if dialog.exec_() != QDialog.DialogCode.Accepted:
            return

        # Get offset values
        offset_x = dialog.offset_x
        offset_y = dialog.offset_y

        # Apply batch offset
        new_data = batch_offset_points(self.parent.curve_data, self.parent.selected_indices, offset_x, offset_y)

        # Update curve data
        self.update_parent_data(new_data, f"Offset {len(self.parent.selected_indices)} points")

    def batch_rotate(self) -> None:
        """Rotate selected points with dialog UI."""
        if not self.parent.selected_indices:
            _ = QMessageBox.warning(self.parent.curve_view, "No Selection", "Please select points to rotate.")
            return

        # Show rotation dialog
        dialog = RotationDialog(self.parent.curve_view)
        if dialog.exec_() != QDialog.DialogCode.Accepted:
            return

        # Get rotation values
        angle = dialog.angle
        use_center = dialog.use_centroid

        # Determine center point
        center_x = None
        center_y = None
        if not use_center:
            # Use current view center if not using centroid
            center_x = self.parent.curve_view.width() / 2
            center_y = self.parent.curve_view.height() / 2

        # Apply batch rotation
        new_data = batch_rotate_points(self.parent.curve_data, self.parent.selected_indices, angle, center_x, center_y)

        # Update curve data
        self.update_parent_data(new_data, f"Rotated {len(self.parent.selected_indices)} points by {angle}°")

    def batch_smooth(self) -> None:
        """Smooth selected points with dialog UI."""
        if not self.parent.selected_indices:
            _ = QMessageBox.warning(self.parent.curve_view, "No Selection", "Please select points to smooth.")
            return

        # Show smoothing factor dialog
        dialog = SmoothFactorDialog(cast(QWidget, cast(object, self.parent)))
        if dialog.exec_() != QDialog.DialogCode.Accepted:
            return

        # Get smoothing factor
        factor = dialog.smoothness_factor

        # Apply batch smoothing
        new_data = batch_smoothness_adjustment(
            self.parent.curve_data,
            self.parent.selected_indices,
            factor,
            self.parent.curve_view,  # Pass curve_view for stable transformation
        )

        # Update curve data
        self.update_parent_data(new_data, f"Smoothed {len(self.parent.selected_indices)} points with factor {factor}")

    def update_parent_data(self, new_data, status_message: str) -> None:
        """Update the parent window with new curve data.

        Args:
            new_data: The updated curve data
            status_message: Message to show in status bar
        """
        # Check if parent has update_curve_data method
        if hasattr(self.parent, "update_curve_data"):
            self.parent.update_curve_data(new_data)
        else:
            # Fallback to direct update
            self.parent.curve_data = new_data
            if hasattr(self.parent.curve_view, "setPoints"):
                self.parent.curve_view.setPoints(new_data, self.parent.image_width, self.parent.image_height)
            elif hasattr(self.parent.curve_view, "set_curve_data"):
                self.parent.curve_view.set_curve_data(new_data)

        # Update status bar
        self.parent.statusBar().showMessage(status_message, 2000)

        # Add to history if available
        if hasattr(self.parent, "add_to_history"):
            self.parent.add_to_history()

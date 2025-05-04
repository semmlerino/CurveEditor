#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Batch editing operations for 3DE4 Curve Editor.
Provides functions for manipulating multiple track points simultaneously.
"""

import copy
import math
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QDoubleSpinBox, QGroupBox, QRadioButton, QButtonGroup,
    QGridLayout, QDialog, QDialogButtonBox, QMessageBox
)
from PySide6.QtCore import Qt, Signal

from services.curve_service import CurveService as CurveViewOperations
from services.analysis_service import AnalysisService
from dialogs import ScaleDialog, OffsetDialog, RotationDialog, SmoothFactorDialog

def batch_scale_points(curve_data, indices, scale_x, scale_y, center_x=None, center_y=None):
    """Scale multiple points around a center point.

    Args:
        curve_data: List of (frame, x, y) tuples
        indices: List of indices to scale
        scale_x: Scale factor for X coordinates
        scale_y: Scale factor for Y coordinates
        center_x: X coordinate of scaling center (None for centroid)
        center_y: Y coordinate of scaling center (None for centroid)

    Returns:
        Modified copy of curve_data
    """
    return AnalysisService.scale_points(curve_data, indices, scale_x, scale_y, center_x, center_y)

def batch_offset_points(curve_data, indices, offset_x, offset_y):
    """Offset multiple points by a fixed amount.

    Args:
        curve_data: List of (frame, x, y) tuples
        indices: List of indices to offset
        offset_x: Amount to offset X coordinates
        offset_y: Amount to offset Y coordinates

    Returns:
        Modified copy of curve_data
    """
    return AnalysisService.offset_points(curve_data, indices, offset_x, offset_y)

def batch_rotate_points(curve_data, indices, angle_degrees, center_x=None, center_y=None):
    """Rotate multiple points around a center point.

    Args:
        curve_data: List of (frame, x, y) tuples
        indices: List of indices to rotate
        angle_degrees: Rotation angle in degrees
        center_x: X coordinate of rotation center (None for centroid)
        center_y: Y coordinate of rotation center (None for centroid)

    Returns:
        Modified copy of curve_data
    """
    return AnalysisService.rotate_points(curve_data, indices, angle_degrees, center_x, center_y)

def batch_smoothness_adjustment(curve_data, indices, smoothness_factor):
    """Adjust the smoothness of a selection of points.

    Args:
        curve_data: List of (frame, x, y) tuples
        indices: List of indices to smooth
        smoothness_factor: Factor between 0.0 and 1.0 controlling smoothness intensity

    Returns:
        Modified copy of curve_data
    """
    # Validate smoothness factor
    smoothness_factor = max(0.0, min(1.0, smoothness_factor))

    # No effect if smoothness factor is 0
    if smoothness_factor == 0:
        return copy.deepcopy(curve_data)

    # Compute parameters for gaussian smoothing
    window_base = 3
    window_max = 15  # Max window size for smoothing
    sigma_base = 0.5  # Min sigma
    sigma_max = 3.0  # Max sigma

    # Interpolate window size and sigma based on the smoothness factor
    window_size = window_base + int((window_max - window_base) * smoothness_factor)
    # Ensure window size is odd
    if window_size % 2 == 0:
        window_size += 1
    sigma = sigma_base + (sigma_max - sigma_base) * smoothness_factor

    try:
        # Use AnalysisService for smoothing
        return AnalysisService.smooth_curve(
            curve_data,
            indices,
            method='gaussian',
            window_size=window_size,
            sigma=sigma
        )
    except Exception as e:
        print(f"Error during batch smoothness adjustment: {e}")
        # Return original data copy in case of error
        return copy.deepcopy(curve_data)

def batch_normalize_velocity(curve_data: list, indices: list, target_velocity: float) -> list:
    """Normalize velocity between points to target value.
    
    Args:
        curve_data: List of point tuples (frame, x, y)
        indices: List of indices to consider for normalization
        target_velocity: Target velocity in pixels per frame
    
    Returns:
        Modified copy of curve_data
    """
    # Create a temporary AnalysisService instance with the curve data
    service = AnalysisService()
    service.data = [curve_data[i] for i in indices if i < len(curve_data)]
    
    # Call the normalize_velocity method on this instance
    service.normalize_velocity(target_velocity)
    
    # Create a new list with normalized points for specified indices
    result = curve_data.copy()
    for idx, normalized_idx in enumerate(indices):
        if normalized_idx < len(result) and idx < len(service.data):
            result[normalized_idx] = service.data[idx]
    
    return result

class BatchEditUI:
    """UI integration for batch editing operations.

    This class provides methods that connect UI actions with the batch edit functions,
    handling dialogs and user interaction.
    """

    def __init__(self, parent_window):
        """Initialize with reference to parent window.

        Args:
            parent_window: The main window that will use batch operations
        """
        self.parent = parent_window

    def setup_batch_editing_ui(self):
        """Set up batch editing controls in the parent window."""
        self.parent.batch_edit_group = QGroupBox("Batch Edit")
        batch_layout = QHBoxLayout(self.parent.batch_edit_group)

        self.parent.scale_button = QPushButton("Scale")
        self.parent.scale_button.clicked.connect(self.batch_scale)
        self.parent.scale_button.setToolTip("Scale selected points")

        self.parent.offset_button = QPushButton("Offset")
        self.parent.offset_button.clicked.connect(self.batch_offset)
        self.parent.offset_button.setToolTip("Offset selected points")

        self.parent.rotate_button = QPushButton("Rotate")
        self.parent.rotate_button.clicked.connect(self.batch_rotate)
        self.parent.rotate_button.setToolTip("Rotate selected points")

        self.parent.smooth_button = QPushButton("Smooth")
        self.parent.smooth_button.clicked.connect(self.batch_smooth)
        self.parent.smooth_button.setToolTip("Smooth selected points")

        self.parent.select_all_button = QPushButton("Select All")
        self.parent.select_all_button.clicked.connect(lambda: CurveViewOperations.select_all_points(self.parent.curve_view, self.parent))
        self.parent.select_all_button.setToolTip("Select all points (Ctrl+A)")

        batch_layout.addWidget(self.parent.scale_button)
        batch_layout.addWidget(self.parent.offset_button)
        batch_layout.addWidget(self.parent.rotate_button)
        batch_layout.addWidget(self.parent.smooth_button)
        batch_layout.addWidget(self.parent.select_all_button)

        # Add to the point editing section if it exists
        if hasattr(self.parent, 'point_edit_layout'):
            self.parent.point_edit_layout.addWidget(self.parent.batch_edit_group)

    def batch_scale(self):
        """Scale selected points with dialog UI."""
        if not self.parent.selected_indices:
            QMessageBox.warning(self.parent, "No Selection", "Please select points to scale.")
            return

        # Show scale dialog
        dialog = ScaleDialog(self.parent)
        if dialog.exec_() != QDialog.Accepted:
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
            self.parent.curve_data,
            self.parent.selected_indices,
            scale_x,
            scale_y,
            center_x,
            center_y
        )

        # Update curve data
        self.update_parent_data(new_data, f"Scaled {len(self.parent.selected_indices)} points")

    def batch_offset(self):
        """Offset selected points with dialog UI."""
        if not self.parent.selected_indices:
            QMessageBox.warning(self.parent, "No Selection", "Please select points to offset.")
            return

        # Show offset dialog
        dialog = OffsetDialog(self.parent)
        if dialog.exec_() != QDialog.Accepted:
            return

        # Get offset values
        offset_x = dialog.offset_x
        offset_y = dialog.offset_y

        # Apply batch offset
        new_data = batch_offset_points(
            self.parent.curve_data,
            self.parent.selected_indices,
            offset_x,
            offset_y
        )

        # Update curve data
        self.update_parent_data(new_data, f"Offset {len(self.parent.selected_indices)} points")

    def batch_rotate(self):
        """Rotate selected points with dialog UI."""
        if not self.parent.selected_indices:
            QMessageBox.warning(self.parent, "No Selection", "Please select points to rotate.")
            return

        # Show rotation dialog
        dialog = RotationDialog(self.parent)
        if dialog.exec_() != QDialog.Accepted:
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
        new_data = batch_rotate_points(
            self.parent.curve_data,
            self.parent.selected_indices,
            angle,
            center_x,
            center_y
        )

        # Update curve data
        self.update_parent_data(new_data, f"Rotated {len(self.parent.selected_indices)} points by {angle}°")

    def batch_smooth(self):
        """Smooth selected points with dialog UI."""
        if not self.parent.selected_indices:
            QMessageBox.warning(self.parent, "No Selection", "Please select points to smooth.")
            return

        # Show smoothing factor dialog
        dialog = SmoothFactorDialog(self.parent)
        if dialog.exec_() != QDialog.Accepted:
            return

        # Get smoothing factor
        factor = dialog.smoothness_factor

        # Apply batch smoothing
        new_data = batch_smoothness_adjustment(
            self.parent.curve_data,
            self.parent.selected_indices,
            factor
        )

        # Update curve data
        self.update_parent_data(new_data, f"Smoothed {len(self.parent.selected_indices)} points with factor {factor}")

    def update_parent_data(self, new_data, status_message):
        """Update the parent window with new curve data.

        Args:
            new_data: The updated curve data
            status_message: Message to show in status bar
        """
        # Check if parent has update_curve_data method
        if hasattr(self.parent, 'update_curve_data'):
            self.parent.update_curve_data(new_data)
        else:
            # Fallback to direct update
            self.parent.curve_data = new_data
            if hasattr(self.parent.curve_view, 'setPoints'):
                self.parent.curve_view.setPoints(
                    new_data,
                    self.parent.image_width,
                    self.parent.image_height
                )
            elif hasattr(self.parent.curve_view, 'set_curve_data'):
                self.parent.curve_view.set_curve_data(new_data)

        # Update status bar
        self.parent.statusBar().showMessage(status_message, 2000)

        # Add to history if available
        if hasattr(self.parent, 'add_to_history'):
            self.parent.add_to_history()

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

from curve_view_operations import CurveViewOperations
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
    # Create a copy of the curve data
    result = copy.deepcopy(curve_data)
    
    # If no center provided, use centroid of selected points
    if center_x is None or center_y is None:
        sum_x = 0
        sum_y = 0
        count = 0
        
        for idx in indices:
            if 0 <= idx < len(curve_data):
                _, x, y = curve_data[idx]
                sum_x += x
                sum_y += y
                count += 1
                
        if count > 0:
            center_x = sum_x / count if center_x is None else center_x
            center_y = sum_y / count if center_y is None else center_y
        else:
            # No valid points to scale
            return result
    
    # Apply scaling to selected points
    for idx in indices:
        if 0 <= idx < len(curve_data):
            frame, x, y = curve_data[idx]
            
            # Calculate new coordinates
            new_x = center_x + (x - center_x) * scale_x
            new_y = center_y + (y - center_y) * scale_y
            
            # Update point
            result[idx] = (frame, new_x, new_y)
            
    return result

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
    # Create a copy of the curve data
    result = copy.deepcopy(curve_data)
    
    # Apply offset to selected points
    for idx in indices:
        if 0 <= idx < len(curve_data):
            frame, x, y = curve_data[idx]
            
            # Calculate new coordinates
            new_x = x + offset_x
            new_y = y + offset_y
            
            # Update point
            result[idx] = (frame, new_x, new_y)
            
    return result

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
    # Create a copy of the curve data
    result = copy.deepcopy(curve_data)
    
    # Convert angle to radians
    angle_rad = math.radians(angle_degrees)
    
    # If no center provided, use centroid of selected points
    if center_x is None or center_y is None:
        sum_x = 0
        sum_y = 0
        count = 0
        
        for idx in indices:
            if 0 <= idx < len(curve_data):
                _, x, y = curve_data[idx]
                sum_x += x
                sum_y += y
                count += 1
                
        if count > 0:
            center_x = sum_x / count if center_x is None else center_x
            center_y = sum_y / count if center_y is None else center_y
        else:
            # No valid points to rotate
            return result
    
    # Apply rotation to selected points
    for idx in indices:
        if 0 <= idx < len(curve_data):
            frame, x, y = curve_data[idx]
            
            # Translate point to origin
            dx = x - center_x
            dy = y - center_y
            
            # Rotate point
            new_x = center_x + dx * math.cos(angle_rad) - dy * math.sin(angle_rad)
            new_y = center_y + dx * math.sin(angle_rad) + dy * math.cos(angle_rad)
            
            # Update point
            result[idx] = (frame, new_x, new_y)
            
    return result

def batch_smoothness_adjustment(curve_data, indices, smoothness_factor):
    """Adjust the smoothness of a selection of points.
    
    Higher smoothness factor means smoother curve (less adherence to original points).
    Lower smoothness factor means closer to original points.
    
    Args:
        curve_data: List of (frame, x, y) tuples
        indices: List of indices to adjust
        smoothness_factor: 0.0 to 1.0, higher means smoother
        
    Returns:
        Modified copy of curve_data
    """
    import curve_operations as ops
    
    # Validate smoothness factor
    smoothness_factor = max(0.0, min(1.0, smoothness_factor))
    
    # Create a copy of the curve data
    result = copy.deepcopy(curve_data)
    
    # No effect if smoothness factor is 0
    if smoothness_factor == 0:
        return result
        
    # Apply gaussian smoothing with strength based on smoothness factor
    window_base = 3
    window_max = 15
    sigma_base = 0.5
    sigma_max = 3.0
    
    # Calculate window size and sigma based on smoothness factor
    window_size = window_base + int((window_max - window_base) * smoothness_factor)
    # Make sure window size is odd
    if window_size % 2 == 0:
        window_size += 1
        
    sigma = sigma_base + (sigma_max - sigma_base) * smoothness_factor
    
    # Apply smoothing
    return ops.smooth_gaussian(result, indices, window_size, sigma)

def batch_normalize_velocity(curve_data, indices, target_velocity=None):
    """Normalize the velocity of selected points to be more consistent.
    
    Args:
        curve_data: List of (frame, x, y) tuples
        indices: List of indices to normalize
        target_velocity: Target velocity in pixels/frame (None for average)
        
    Returns:
        Modified copy of curve_data
    """
    # Create a copy of the curve data
    result = copy.deepcopy(curve_data)
    
    # Need at least 2 points to calculate velocity
    if len(indices) < 2:
        return result
        
    # Sort indices
    sorted_indices = sorted(indices)
    
    # If we're not modifying consecutive points, return
    if sorted_indices[-1] - sorted_indices[0] + 1 != len(sorted_indices):
        return result
    
    # Calculate velocities between points
    velocities = []
    for i in range(1, len(sorted_indices)):
        prev_idx = sorted_indices[i-1]
        curr_idx = sorted_indices[i]
        
        prev_frame, prev_x, prev_y = curve_data[prev_idx]
        curr_frame, curr_x, curr_y = curve_data[curr_idx]
        
        frame_diff = curr_frame - prev_frame
        if frame_diff > 0:
            dx = curr_x - prev_x
            dy = curr_y - prev_y
            distance = math.sqrt(dx*dx + dy*dy)
            velocity = distance / frame_diff
            velocities.append(velocity)
    
    if not velocities:
        return result
        
    # Calculate average velocity if no target provided
    if target_velocity is None:
        target_velocity = sum(velocities) / len(velocities)
    
    # Adjust points to normalize velocity
    # First point stays fixed, others are adjusted
    first_idx = sorted_indices[0]
    fixed_frame, fixed_x, fixed_y = curve_data[first_idx]
    
    for i in range(1, len(sorted_indices)):
        curr_idx = sorted_indices[i]
        curr_frame, curr_x, curr_y = curve_data[curr_idx]
        
        # Get previous adjusted point
        prev_idx = sorted_indices[i-1]
        _, prev_x, prev_y = result[prev_idx]
        
        # Calculate frame difference
        frame_diff = curr_frame - curve_data[prev_idx][0]
        
        # Calculate direction vector
        orig_dx = curr_x - curve_data[prev_idx][1]
        orig_dy = curr_y - curve_data[prev_idx][2]
        orig_dist = math.sqrt(orig_dx*orig_dx + orig_dy*orig_dy)
        
        # Skip if points are at the same location
        if orig_dist < 0.0001:
            continue
        
        # Normalize direction vector
        dir_x = orig_dx / orig_dist
        dir_y = orig_dy / orig_dist
        
        # Calculate new position
        new_dist = target_velocity * frame_diff
        new_x = prev_x + dir_x * new_dist
        new_y = prev_y + dir_y * new_dist
        
        # Update point
        result[curr_idx] = (curr_frame, new_x, new_y)
    
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
        self.parent.select_all_button.clicked.connect(lambda: CurveViewOperations.select_all_points(self.parent.curve_view))
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
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy
from PySide6.QtWidgets import QMessageBox, QDialog
from PySide6.QtCore import Qt

from dialogs import (SmoothingDialog, FilterDialog, FillGapsDialog, 
                    ExtrapolateDialog, ProblemDetectionDialog, ShortcutsDialog)
from curve_operations import CurveOperations

class DialogOperations:
    """Dialog operations for the 3DE4 Curve Editor."""
    
    @staticmethod
    def show_smooth_dialog(main_window):
        """Show dialog for curve smoothing."""
        if not main_window.curve_data or len(main_window.curve_data) < 3:
            QMessageBox.information(main_window, "Info", "Not enough points to smooth curve.")
            return
            
        frames = [frame for frame, _, _ in main_window.curve_data]
        min_frame = min(frames)
        max_frame = max(frames)
        
        current_frame = min_frame
        if main_window.curve_view.selected_point_idx >= 0:
            current_frame = main_window.curve_data[main_window.curve_view.selected_point_idx][0]
        
        dialog = SmoothingDialog(main_window, min_frame, max_frame, current_frame)
        if dialog.exec_() != QDialog.Accepted:
            return
            
        # Get smoothing parameters
        method = dialog.method_combo.currentIndex()
        range_type = dialog.range_combo.currentIndex()
        
        # Determine points to smooth
        points_to_smooth = []
        
        if range_type == 0:  # Entire curve
            points_to_smooth = list(range(len(main_window.curve_data)))
        elif range_type == 1:  # Selected range
            start_frame = dialog.start_frame.value()
            end_frame = dialog.end_frame.value()
            
            for i, (frame, _, _) in enumerate(main_window.curve_data):
                if start_frame <= frame <= end_frame:
                    points_to_smooth.append(i)
        elif range_type == 2:  # Current point only
            if main_window.curve_view.selected_point_idx >= 0:
                # Include a window around the current point
                window = dialog.window_spin.value() // 2
                center = main_window.curve_view.selected_point_idx
                
                for i in range(max(0, center - window), min(len(main_window.curve_data), center + window + 1)):
                    points_to_smooth.append(i)
        
        if not points_to_smooth:
            QMessageBox.warning(main_window, "Warning", "No points to smooth.")
            return
            
        # Apply the selected smoothing method
        if method == 0:  # Moving Average
            window_size = dialog.window_spin.value()
            main_window.curve_data = CurveOperations.smooth_moving_average(main_window.curve_data, points_to_smooth, window_size)
        elif method == 1:  # Gaussian
            window_size = dialog.window_spin.value()
            sigma = dialog.sigma_spin.value()
            main_window.curve_data = CurveOperations.smooth_gaussian(main_window.curve_data, points_to_smooth, window_size, sigma)
        elif method == 2:  # Savitzky-Golay
            window_size = dialog.window_spin.value()
            main_window.curve_data = CurveOperations.smooth_savitzky_golay(main_window.curve_data, points_to_smooth, window_size)
        
        # Update view
        main_window.curve_view.setPoints(main_window.curve_data, main_window.image_width, main_window.image_height)
        
        # Add to history
        main_window.add_to_history()

    @staticmethod
    def show_filter_dialog(main_window):
        """Show dialog for applying filters to the curve."""
        if not main_window.curve_data or len(main_window.curve_data) < 3:
            QMessageBox.information(main_window, "Info", "Not enough points to filter curve.")
            return
            
        frames = [frame for frame, _, _ in main_window.curve_data]
        min_frame = min(frames)
        max_frame = max(frames)
        
        current_frame = min_frame
        if main_window.curve_view.selected_point_idx >= 0:
            current_frame = main_window.curve_data[main_window.curve_view.selected_point_idx][0]
        
        dialog = FilterDialog(main_window, min_frame, max_frame, current_frame)
        if dialog.exec_() != QDialog.Accepted:
            return
            
        # Get filter parameters
        filter_type = dialog.filter_combo.currentIndex()
        range_type = dialog.range_combo.currentIndex()
        
        # Determine points to filter
        points_to_filter = []
        
        if range_type == 0:  # Entire curve
            points_to_filter = list(range(len(main_window.curve_data)))
        elif range_type == 1:  # Selected range
            start_frame = dialog.start_frame.value()
            end_frame = dialog.end_frame.value()
            
            for i, (frame, _, _) in enumerate(main_window.curve_data):
                if start_frame <= frame <= end_frame:
                    points_to_filter.append(i)
        elif range_type == 2:  # Current point only
            if main_window.curve_view.selected_point_idx >= 0:
                points_to_filter.append(main_window.curve_view.selected_point_idx)
        
        if not points_to_filter:
            QMessageBox.warning(main_window, "Warning", "No points to filter.")
            return
            
        # Apply the selected filter
        if filter_type == 0:  # Median
            window_size = dialog.window_size_spin.value()
            main_window.curve_data = CurveOperations.filter_median(main_window.curve_data, points_to_filter, window_size)
        elif filter_type == 1:  # Gaussian
            window_size = dialog.window_size_spin.value()
            sigma = dialog.sigma_spin.value()
            main_window.curve_data = CurveOperations.filter_gaussian(main_window.curve_data, points_to_filter, window_size, sigma)
        elif filter_type == 2:  # Average
            window_size = dialog.window_size_spin.value()
            main_window.curve_data = CurveOperations.filter_average(main_window.curve_data, points_to_filter, window_size)
        elif filter_type == 3:  # Butterworth
            cutoff = dialog.cutoff_spin.value()
            order = dialog.order_spin.value()
            main_window.curve_data = CurveOperations.filter_butterworth(main_window.curve_data, points_to_filter, cutoff, order)
        
        # Update view
        main_window.curve_view.setPoints(main_window.curve_data, main_window.image_width, main_window.image_height)
        
        # Add to history
        main_window.add_to_history()

    @staticmethod
    def detect_gaps(main_window):
        """Detect gaps in the tracking data."""
        if not main_window.curve_data or len(main_window.curve_data) < 2:
            return []
            
        # Sort by frame
        sorted_data = sorted(main_window.curve_data, key=lambda x: x[0])
        
        # Find gaps
        gaps = []
        for i in range(1, len(sorted_data)):
            prev_frame = sorted_data[i-1][0]
            curr_frame = sorted_data[i][0]
            
            if curr_frame - prev_frame > 1:
                # Found a gap
                gaps.append((prev_frame + 1, curr_frame - 1))
                
        return gaps

    @staticmethod
    def show_fill_gaps_dialog(main_window):
        """Show dialog for filling gaps in the curve."""
        if not main_window.curve_data or len(main_window.curve_data) < 2:
            QMessageBox.information(main_window, "Info", "Not enough points to fill gaps.")
            return
            
        frames = [frame for frame, _, _ in main_window.curve_data]
        min_frame = min(frames)
        max_frame = max(frames)
        
        dialog = FillGapsDialog(main_window, min_frame, max_frame)
        if dialog.exec_() != QDialog.Accepted:
            return
            
        # Get fill parameters
        method = dialog.method_combo.currentIndex()
        auto_detect = dialog.auto_detect.isChecked()
        preserve_endpoints = dialog.preserve_endpoints.isChecked()
        
        # Apply selected fill method
        if auto_detect:
            # Auto-detect gaps
            gaps = DialogOperations.detect_gaps(main_window)
            
            if not gaps:
                QMessageBox.information(main_window, "Info", "No gaps detected.")
                return
                
            # Fill each gap
            for start_frame, end_frame in gaps:
                DialogOperations.fill_gap(main_window, start_frame, end_frame, method, preserve_endpoints)
                
            main_window.statusBar().showMessage(f"Filled {len(gaps)} gaps", 3000)
        else:
            # Fill specified range
            start_frame = dialog.start_frame.value()
            end_frame = dialog.end_frame.value()
            
            if start_frame >= end_frame:
                QMessageBox.warning(main_window, "Warning", "Start frame must be less than end frame.")
                return
                
            DialogOperations.fill_gap(main_window, start_frame, end_frame, method, preserve_endpoints)
        
        # Update view
        main_window.curve_view.setPoints(main_window.curve_data, main_window.image_width, main_window.image_height)
        
        # Add to history
        main_window.add_to_history()
    
    @staticmethod
    def fill_gap(main_window, start_frame, end_frame, method, preserve_endpoints=True):
        """Helper method to fill a gap in the curve using the specified method."""
        # Window size for certain methods
        window_size = 5
        
        if method == 0:  # Linear
            main_window.curve_data = CurveOperations.fill_linear(main_window.curve_data, start_frame, end_frame, preserve_endpoints)
        elif method == 1:  # Cubic spline
            main_window.curve_data = CurveOperations.fill_cubic_spline(main_window.curve_data, start_frame, end_frame, 0.5, preserve_endpoints)
        elif method == 2:  # Constant velocity
            main_window.curve_data = CurveOperations.fill_constant_velocity(main_window.curve_data, start_frame, end_frame, window_size, preserve_endpoints)
        elif method == 3:  # Accelerated motion
            main_window.curve_data = CurveOperations.fill_accelerated_motion(main_window.curve_data, start_frame, end_frame, window_size, 0.5, preserve_endpoints)
        elif method == 4:  # Average
            main_window.curve_data = CurveOperations.fill_average(main_window.curve_data, start_frame, end_frame, window_size, preserve_endpoints)

    @staticmethod
    def show_extrapolate_dialog(main_window):
        """Show dialog for extrapolating the curve."""
        if not main_window.curve_data or len(main_window.curve_data) < 3:
            QMessageBox.information(main_window, "Info", "Not enough points to extrapolate curve.")
            return
            
        frames = [frame for frame, _, _ in main_window.curve_data]
        min_frame = min(frames)
        max_frame = max(frames)
        
        dialog = ExtrapolateDialog(main_window, min_frame, max_frame)
        if dialog.exec_() != QDialog.Accepted:
            return
            
        # Get extrapolation parameters
        direction = dialog.direction_combo.currentIndex()
        method = dialog.method_combo.currentIndex()
        forward_frames = dialog.forward_frames.value()
        backward_frames = dialog.backward_frames.value()
        fit_points = dialog.fit_points.value()
        
        # Apply extrapolation based on direction
        if direction == 0 or direction == 2:  # Forward or Both
            if forward_frames > 0:
                main_window.curve_data = CurveOperations.extrapolate_forward(main_window.curve_data, forward_frames, method, fit_points)
                
        if direction == 1 or direction == 2:  # Backward or Both
            if backward_frames > 0:
                main_window.curve_data = CurveOperations.extrapolate_backward(main_window.curve_data, backward_frames, method, fit_points)
        
        # Update view
        main_window.curve_view.setPoints(main_window.curve_data, main_window.image_width, main_window.image_height)
        
        # Add to history
        main_window.add_to_history()
        
        # Update status
        total_frames = 0
        if direction == 0 or direction == 2:
            total_frames += forward_frames
        if direction == 1 or direction == 2:
            total_frames += backward_frames
            
        main_window.statusBar().showMessage(f"Extrapolated {total_frames} frames", 3000)

    @staticmethod
    def show_shortcuts_dialog(main_window):
        """Show dialog with keyboard shortcuts."""
        dialog = ShortcutsDialog(main_window)
        dialog.exec_()
        
    @staticmethod
    def show_problem_detection_dialog(main_window, problems=None):
        """Show dialog for detecting problems in the tracking data."""
        if problems is None:
            if not main_window.curve_data or len(main_window.curve_data) < 10:
                QMessageBox.information(main_window, "Info", "Not enough points to analyze.")
                return None
                
            # Detect problems
            problems = CurveOperations.detect_problems(main_window)
            
            if not problems:
                QMessageBox.information(main_window, "Info", "No problems detected.")
                return None
                
            # Sort problems by severity (highest first)
            problems.sort(key=lambda x: x[2], reverse=True)
        
        # Show dialog
        dialog = ProblemDetectionDialog(main_window, problems)
        return dialog

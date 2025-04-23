#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtWidgets import QMessageBox, QDialog
from dialogs import (SmoothingDialog, FilterDialog, FillGapsDialog, 
                    ExtrapolateDialog, ProblemDetectionDialog, ShortcutsDialog)
from curve_data_operations import CurveDataOperations # Import new class
from typing import Any, Optional, List, Tuple

class DialogOperations:
    """Dialog operations for the 3DE4 Curve Editor."""
    
    @staticmethod
    def show_smooth_dialog(main_window: Any) -> None:
        """Show dialog for curve smoothing."""
        if not main_window.curve_data or len(main_window.curve_data) < 3:
            QMessageBox.information(main_window, "Info", "Not enough points to smooth curve.")
            return
            
        frames = [point[0] for point in main_window.curve_data]  # Extract only the frame number from each point
        min_frame = min(frames)
        max_frame = max(frames)
        
        current_frame = min_frame
        if main_window.curve_view.selected_point_idx >= 0:
            current_frame = main_window.curve_data[main_window.curve_view.selected_point_idx][0]
        
        dialog: SmoothingDialog = SmoothingDialog(main_window, min_frame, max_frame, current_frame)
        # Default to "Selected Range" if multiple points are selected
        if main_window.curve_view.selected_points and len(main_window.curve_view.selected_points) > 1:
            dialog.range_combo.setCurrentIndex(1)
            selected_frames = sorted([main_window.curve_data[i][0] for i in main_window.curve_view.selected_points])
            dialog.start_frame.setValue(selected_frames[0])
            dialog.end_frame.setValue(selected_frames[-1])
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
            
        # Get smoothing parameters
        method = dialog.method_combo.currentIndex()
        range_type = dialog.range_combo.currentIndex()
        
        # Determine points to smooth
        points_to_smooth: List[int] = []
        
        if range_type == 0:  # Entire curve
            points_to_smooth = list(range(len(main_window.curve_data)))
        elif range_type == 1:  # Selected range
            start_frame = dialog.start_frame.value()
            end_frame = dialog.end_frame.value()
            
            for i, point in enumerate(main_window.curve_data):
                frame = point[0]  # Extract only the frame number
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
            
        # Apply the selected smoothing method using the unified dispatcher
        try:
            data_ops: CurveDataOperations = CurveDataOperations(main_window.curve_data)
            if method == 0:  # Moving Average
                data_ops.smooth_moving_average(points_to_smooth, dialog.window_spin.value())
            elif method == 1:  # Gaussian
                data_ops.smooth_gaussian(points_to_smooth, dialog.window_spin.value(), dialog.sigma_spin.value())
            elif method == 2:  # Savitzky-Golay
                data_ops.smooth_savitzky_golay(points_to_smooth, dialog.window_spin.value())
            else:
                QMessageBox.warning(main_window, "Warning", "Unknown smoothing method.")
                return

            main_window.curve_data = data_ops.get_data()  # Update main window data
        except Exception as e:
            QMessageBox.critical(main_window, "Error", f"Smoothing failed: {e}")
            return  # Don't proceed if operation failed
        
        # Update view
        main_window.curve_view.setPoints(main_window.curve_data, main_window.image_width, main_window.image_height, preserve_view=True)
        
        # Add to history
        main_window.add_to_history()

    @staticmethod
    def show_filter_dialog(main_window: Any) -> None:
        """Show dialog for applying filters to the curve."""
        if not main_window.curve_data or len(main_window.curve_data) < 3:
            QMessageBox.information(main_window, "Info", "Not enough points to filter curve.")
            return
            
        frames = [point[0] for point in main_window.curve_data]  # Extract only the frame number from each point
        min_frame = min(frames)
        max_frame = max(frames)
        
        current_frame = min_frame
        if main_window.curve_view.selected_point_idx >= 0:
            current_frame = main_window.curve_data[main_window.curve_view.selected_point_idx][0]
        
        dialog: FilterDialog = FilterDialog(main_window, min_frame, max_frame, current_frame)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
            
        # Get filter parameters
        filter_type = dialog.filter_combo.currentIndex()
        range_type = dialog.range_combo.currentIndex()
        
        # Determine points to filter
        points_to_filter: List[int] = []
        
        if range_type == 0:  # Entire curve
            points_to_filter = list(range(len(main_window.curve_data)))
        elif range_type == 1:  # Selected range
            start_frame = dialog.start_frame.value()
            end_frame = dialog.end_frame.value()
            
            for i, point in enumerate(main_window.curve_data):
                frame = point[0]  # Extract only the frame number
                if start_frame <= frame <= end_frame:
                    points_to_filter.append(i)
        elif range_type == 2:  # Current point only
            if main_window.curve_view.selected_point_idx >= 0:
                points_to_filter.append(main_window.curve_view.selected_point_idx)
        
        if not points_to_filter:
            QMessageBox.warning(main_window, "Warning", "No points to filter.")
            return
            
        # Apply the selected filter using CurveDataOperations
        try:
            data_ops: CurveDataOperations = CurveDataOperations(main_window.curve_data)
            operation_applied = False

            if filter_type == 0:  # Median
                data_ops.filter_median(points_to_filter, dialog.median_size.value())
                operation_applied = True
            elif filter_type == 1:  # Gaussian
                data_ops.smooth_gaussian(points_to_filter, dialog.gaussian_size.value(), dialog.gaussian_sigma.value())
                operation_applied = True
            elif filter_type == 2:  # Average
                data_ops.smooth_moving_average(points_to_filter, dialog.average_size.value())
                operation_applied = True
            elif filter_type == 3:  # Butterworth
                data_ops.filter_butterworth(points_to_filter, dialog.butterworth_cutoff.value(), dialog.butterworth_order.value())
                operation_applied = True

            if operation_applied:
                main_window.curve_data = data_ops.get_data() # Update main window data
            else:
                 QMessageBox.warning(main_window, "Warning", "No filter applied (unknown type).")
                 return # No known operation selected

        except AttributeError as ae:
             # Handle cases where dialog attributes might be missing for a type
             QMessageBox.critical(main_window, "Error", f"Dialog configuration error: {ae}")
             return
        except Exception as e:
             QMessageBox.critical(main_window, "Error", f"Filtering failed: {e}")
             return # Don't proceed if operation failed
        
        # Update view
        main_window.curve_view.setPoints(main_window.curve_data, main_window.image_width, main_window.image_height)
        
        # Add to history
        main_window.add_to_history()

    @staticmethod
    def detect_gaps(main_window: Any) -> List[Tuple[int, int]]:
        """Detect gaps in the tracking data."""
        if not main_window.curve_data or len(main_window.curve_data) < 2:
            return []
            
        # Sort by frame
        sorted_data = sorted(main_window.curve_data, key=lambda x: x[0])
        
        # Find gaps
        gaps: List[Tuple[int, int]] = []
        for i in range(1, len(sorted_data)):
            prev_frame = sorted_data[i-1][0]
            curr_frame = sorted_data[i][0]
            
            if curr_frame - prev_frame > 1:
                # Found a gap
                gaps.append((prev_frame + 1, curr_frame - 1))
                
        return gaps

    @staticmethod
    def show_fill_gaps_dialog(main_window: Any) -> None:
        """Show dialog for filling gaps in the curve."""
        if not main_window.curve_data or len(main_window.curve_data) < 2:
            QMessageBox.information(main_window, "Info", "Not enough points to fill gaps.")
            return
            
        frames = [point[0] for point in main_window.curve_data]  # Extract only the frame number from each point
        min_frame = min(frames)
        max_frame = max(frames)
        
        dialog = FillGapsDialog(main_window, min_frame, max_frame)
        if dialog.exec() != QDialog.DialogCode.Accepted:
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
    def fill_gap(main_window: Any, start_frame: int, end_frame: int, method_index: int, preserve_endpoints: bool = True) -> None:
        """Helper method to fill a gap using the specified method via CurveDataOperations."""
        # Window size for certain methods (can be adjusted or made configurable)
        window_size = 5
        tension = 0.5 # Default tension for spline
        accel_weight = 0.5 # Default weight for accelerated motion

        try:
            # Instantiate with the current data
            data_ops: CurveDataOperations = CurveDataOperations(main_window.curve_data)
            operation_performed = False

            if method_index == 0:  # Linear
                data_ops.fill_linear(start_frame, end_frame, preserve_endpoints)
                operation_performed = True
            elif method_index == 1:  # Cubic spline
                data_ops.fill_cubic_spline(start_frame, end_frame, tension, preserve_endpoints)
                operation_performed = True
            elif method_index == 2:  # Constant velocity
                data_ops.fill_constant_velocity(start_frame, end_frame, window_size, preserve_endpoints)
                operation_performed = True
            elif method_index == 3:  # Accelerated motion
                data_ops.fill_accelerated_motion(start_frame, end_frame, window_size, accel_weight, preserve_endpoints)
                operation_performed = True
            elif method_index == 4:  # Average
                data_ops.fill_average(start_frame, end_frame, window_size, preserve_endpoints)
                operation_performed = True
            else:
                 QMessageBox.warning(main_window, "Warning", f"Unknown fill method index: {method_index}")
                 return # Do nothing if method is unknown

            # Update main window data only if an operation was performed
            if operation_performed:
                main_window.curve_data = data_ops.get_data()

        except Exception as e:
            QMessageBox.critical(main_window, "Error", f"Gap filling failed: {e}")
            # Optionally re-raise or log more details traceback.print_exc()

    @staticmethod
    def show_extrapolate_dialog(main_window: Any) -> None:
        """Show dialog for extrapolating the curve."""
        if not main_window.curve_data or len(main_window.curve_data) < 3:
            QMessageBox.information(main_window, "Info", "Not enough points to extrapolate curve.")
            return
            
        frames = [point[0] for point in main_window.curve_data]  # Extract only the frame number from each point
        min_frame = min(frames)
        max_frame = max(frames)
        
        dialog = ExtrapolateDialog(main_window, min_frame, max_frame)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
            
        # Get extrapolation parameters
        direction = dialog.direction_combo.currentIndex()
        method = dialog.method_combo.currentIndex()
        forward_frames = dialog.forward_frames.value()
        backward_frames = dialog.backward_frames.value()
        fit_points = dialog.fit_points.value()
        
        # Apply extrapolation based on direction
        try:
            # Instantiate with current data
            data_ops: CurveDataOperations = CurveDataOperations(main_window.curve_data)
            data_changed = False

            if direction == 0 or direction == 2:  # Forward or Both
                if forward_frames > 0:
                    data_ops.extrapolate_forward(forward_frames, method, fit_points)
                    data_changed = True # Mark data as potentially changed
                    
            if direction == 1 or direction == 2:  # Backward or Both
                if backward_frames > 0:
                    # Apply backward extrapolation to the potentially already modified data
                    # Need to re-instantiate if forward extrapolation happened,
                    # or ensure methods modify internal state correctly.
                    # Assuming methods modify internal state:
                    data_ops.extrapolate_backward(backward_frames, method, fit_points)
                    data_changed = True # Mark data as potentially changed

            # Update main window data only if an operation was performed
            if data_changed:
                 main_window.curve_data = data_ops.get_data()

        except Exception as e:
             QMessageBox.critical(main_window, "Error", f"Extrapolation failed: {e}")
             return # Don't proceed if operation failed
        
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
    def show_shortcuts_dialog(main_window: Any) -> None:
        """Show dialog with keyboard shortcuts."""
        dialog = ShortcutsDialog(main_window)
        dialog.exec()
        
    @staticmethod
    def show_problem_detection_dialog(main_window: Any, problems: Optional[List[Any]] = None) -> Optional[ProblemDetectionDialog]:
        """Show dialog for detecting problems in the tracking data."""
        if problems is None:
            if not main_window.curve_data or len(main_window.curve_data) < 10:
                QMessageBox.information(main_window, "Info", "Not enough points to analyze.")
                return None
                
            # Detect problems
            # problems = ops.CurveOperations.detect_problems(main_window) # Original call removed
            # TODO: Implement problem detection using CurveDataOperations or a dedicated class
            QMessageBox.information(main_window, "Info", "Problem detection is temporarily disabled pending refactoring.")
            return None # Disable for now
            
            if not problems:
                QMessageBox.information(main_window, "Info", "No problems detected.")
                return None
                
            # Sort problems by severity (highest first)
            problems.sort(key=lambda x: x[2], reverse=True)
        
        # Show dialog
        dialog = ProblemDetectionDialog(main_window, problems)
        return dialog

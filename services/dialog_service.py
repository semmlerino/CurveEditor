#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
DialogService: Service for managing all dialog operations in the CurveEditor.
Implements all dialog operations directly rather than delegating to legacy DialogOperations.
"""

from PySide6.QtWidgets import QMessageBox, QDialog, QWidget
from dialogs import (SmoothingDialog, FilterDialog, FillGapsDialog,
                    ExtrapolateDialog, ProblemDetectionDialog, ShortcutsDialog,
                    OffsetDialog)
from services.analysis_service import AnalysisService as CurveDataOperations
from typing import Any, Optional, List, Tuple

# Define a type alias for curve data for clarity
CurveDataType = List[Tuple[int, float, float]]

class DialogService:
    """Service for managing all dialog operations in the CurveEditor."""

    @staticmethod
    def show_smooth_dialog(
        parent_widget: QWidget,
        curve_data: CurveDataType,
        selected_indices: List[int],
        selected_point_idx: int
    ) -> Optional[CurveDataType]:
        """
        Show dialog for curve smoothing.
        Accepts curve data and selection info, returns modified data or None.
        """
        if not curve_data or len(curve_data) < 3:
            QMessageBox.information(parent_widget, "Info", "Not enough points to smooth curve.")
            return None

        frames = [point[0] for point in curve_data]
        min_frame = min(frames) if frames else 0
        max_frame = max(frames) if frames else 0

        current_frame = min_frame
        # Use selected_point_idx directly
        if 0 <= selected_point_idx < len(curve_data):
             current_frame = curve_data[selected_point_idx][0]

        dialog: SmoothingDialog = SmoothingDialog(parent_widget, min_frame, max_frame, current_frame)

        # Default dialog range based on selection
        if len(selected_indices) > 1:
            dialog.range_combo.setCurrentIndex(3) # Default to "Selected Points"
        elif selected_point_idx >= 0:
             dialog.range_combo.setCurrentIndex(2) # Default to "Current Point Only"
        else:
             dialog.range_combo.setCurrentIndex(0) # Default to "Entire Curve"

        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None

        # Get smoothing parameters
        method = dialog.method_combo.currentIndex()
        range_type = dialog.range_combo.currentIndex()

        # Determine points to smooth based on dialog selection
        points_to_smooth: List[int] = []

        if range_type == 0:  # Entire curve
            points_to_smooth = list(range(len(curve_data)))
        elif range_type == 1:  # Selected range (by frame)
            start_frame = dialog.start_frame.value()
            end_frame = dialog.end_frame.value()
            points_to_smooth = [i for i, point in enumerate(curve_data) if start_frame <= point[0] <= end_frame]
        elif range_type == 2:  # Current point only (window around selected_point_idx)
            if selected_point_idx >= 0:
                window = dialog.window_spin.value() // 2
                center = selected_point_idx
                start = max(0, center - window)
                end = min(len(curve_data), center + window + 1)
                points_to_smooth = list(range(start, end))
        elif range_type == 3: # Selected Points (use provided selected_indices)
            points_to_smooth = selected_indices # Use the passed-in list directly

        if not points_to_smooth:
            QMessageBox.warning(parent_widget, "Warning", "No points selected for smoothing.")
            return None

        # Apply the selected smoothing method
        try:
            # CurveDataOperations constructor makes its own copy. Pass the original data.
            data_ops: CurveDataOperations = CurveDataOperations(curve_data)

            window_size = dialog.window_spin.value()
            sigma = dialog.sigma_spin.value() # Only used for Gaussian

            if method == 0:  # Moving Average
                data_ops.smooth_moving_average(points_to_smooth, window_size)
            elif method == 1:  # Gaussian
                data_ops.smooth_gaussian(points_to_smooth, window_size, sigma)
            elif method == 2:  # Savitzky-Golay
                # Ensure window size is valid for Savitzky-Golay (odd, >= 5)
                if window_size < 5 or window_size % 2 == 0:
                     QMessageBox.warning(parent_widget, "Warning", "Savitzky-Golay requires an odd window size of at least 5.")
                     return None
                data_ops.smooth_savitzky_golay(points_to_smooth, window_size)
            else:
                QMessageBox.warning(parent_widget, "Warning", "Unknown smoothing method.")
                return None

            # Return the modified data directly
            return data_ops.get_data()

        except Exception as e:
            QMessageBox.critical(parent_widget, "Error", f"Smoothing failed: {e}")
            return None

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
            gaps = DialogService.detect_gaps(main_window)

            if not gaps:
                QMessageBox.information(main_window, "Info", "No gaps detected.")
                return

            # Fill each gap
            for start_frame, end_frame in gaps:
                DialogService.fill_gap(main_window, start_frame, end_frame, method, preserve_endpoints)

            main_window.statusBar().showMessage(f"Filled {len(gaps)} gaps", 3000)
        else:
            # Fill specified range
            start_frame = dialog.start_frame.value()
            end_frame = dialog.end_frame.value()

            if start_frame >= end_frame:
                QMessageBox.warning(main_window, "Warning", "Start frame must be less than end frame.")
                return

            DialogService.fill_gap(main_window, start_frame, end_frame, method, preserve_endpoints)

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
    def show_offset_dialog(main_window: Any) -> Any:
        """Show dialog for offsetting all curve points."""
        if not main_window.curve_data:
            QMessageBox.information(main_window, "Info", "No points to offset.")
            return None
        dialog = OffsetDialog(main_window)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        dx = dialog.offset_x
        dy = dialog.offset_y
        data_ops = CurveDataOperations(main_window.curve_data)
        indices = list(range(len(main_window.curve_data)))
        data_ops.offset_points(indices, dx, dy)
        new_data = data_ops.get_data()
        main_window.curve_data = new_data
        main_window.curve_view.setPoints(new_data, main_window.image_width, main_window.image_height)
        main_window.add_to_history()
        main_window.statusBar().showMessage(f"Offset by ({dx}, {dy}) applied", 3000)
        return new_data

    @staticmethod
    def show_problem_detection_dialog(main_window: Any, problems: Optional[List[Tuple[int, Any, Any, Any]]] = None) -> Optional[ProblemDetectionDialog]:
        """Show dialog for detecting problems in the tracking data."""
        if problems is None:
            if not main_window.curve_data or len(main_window.curve_data) < 10:
                QMessageBox.information(main_window, "Info", "Not enough points to analyze.")
                return None

            # Detect problems using AnalysisService
            from services.analysis_service import AnalysisService
            try:
                problems = AnalysisService.detect_problems(main_window.curve_data)
            except Exception as e:
                QMessageBox.critical(main_window, "Error", f"Problem detection failed: {e}")
                return None

            if not problems:
                QMessageBox.information(main_window, "Info", "No problems detected.")
                return None

            # Sort problems by severity (highest first)
            problems.sort(key=lambda x: x[2], reverse=True)

        # Show dialog
        dialog = ProblemDetectionDialog(main_window, problems)
        return dialog

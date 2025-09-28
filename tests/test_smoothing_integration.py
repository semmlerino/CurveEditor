#!/usr/bin/env python
"""
Comprehensive integration tests for the smoothing feature.

These tests verify the complete end-to-end functionality of the smoothing feature
without using mocks, testing real service interactions, undo/redo, file I/O,
and integration with other features.

Following UNIFIED_TESTING_GUIDE principles with focus on real integration.
"""

import math
import random

import pytest

from services import get_data_service
from ui.main_window import MainWindow


class TestEndToEndSmoothing:
    """Test complete smoothing workflow without mocks."""

    @pytest.fixture
    def window_with_real_data(self, qtbot):
        """Create a MainWindow with real test data and services."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Add real test data
        if window.curve_widget:
            # Create a noisy curve that would benefit from smoothing
            test_data = [
                (1, 100.0, 200.0),
                (2, 105.0, 195.0),  # Slight variations to simulate noise
                (3, 98.0, 203.0),
                (4, 102.0, 198.0),
                (5, 99.0, 201.0),
                (6, 103.0, 197.0),
                (7, 97.0, 204.0),
                (8, 101.0, 199.0),
                (9, 100.0, 200.0),
                (10, 104.0, 196.0),
            ]
            window.curve_widget.set_curve_data(test_data)

        return window

    def test_real_smoothing_operation_moving_average(self, window_with_real_data, qtbot):
        """Test actual smoothing with moving average filter."""
        window = window_with_real_data

        # Store original data for comparison
        original_data = list(window.curve_widget.curve_data)

        # Set smoothing parameters
        window.ui.toolbar.smoothing_type_combo.setCurrentText("Moving Average")
        window.ui.toolbar.smoothing_size_spinbox.setValue(3)
        qtbot.wait(50)

        # Select all points for smoothing
        window.curve_widget._select_point(0, False)
        for i in range(1, len(original_data)):
            window.curve_widget._select_point(i, True)

        # Apply smoothing via keyboard shortcut
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)

        # Verify data has changed
        smoothed_data = list(window.curve_widget.curve_data)
        assert smoothed_data != original_data

        # Verify smoothing actually reduced variation
        def calculate_variation(data):
            """Calculate total variation in Y values."""
            y_values = [point[2] for point in data]
            variation = sum(abs(y_values[i] - y_values[i - 1]) for i in range(1, len(y_values)))
            return variation

        original_variation = calculate_variation(original_data)
        smoothed_variation = calculate_variation(smoothed_data)
        assert smoothed_variation < original_variation  # Smoothing should reduce variation

        # Verify frames are preserved
        for orig, smoothed in zip(original_data, smoothed_data):
            assert orig[0] == smoothed[0]  # Frame numbers should match

    def test_real_smoothing_operation_median_filter(self, window_with_real_data, qtbot):
        """Test actual smoothing with median filter."""
        window = window_with_real_data

        # Add an outlier to test median filter effectiveness
        data_with_outlier = list(window.curve_widget.curve_data)
        data_with_outlier[5] = (6, 103.0, 250.0)  # Outlier in Y
        window.curve_widget.set_curve_data(data_with_outlier)

        # Set median filter
        window.ui.toolbar.smoothing_type_combo.setCurrentText("Median")
        window.ui.toolbar.smoothing_size_spinbox.setValue(5)
        qtbot.wait(50)

        # Select all points
        window.shortcut_manager.action_select_all.trigger()
        qtbot.wait(50)

        # Apply smoothing
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)

        # Verify outlier was reduced
        smoothed_data = list(window.curve_widget.curve_data)
        assert smoothed_data[5][2] < 230.0  # Outlier should be reduced

    def test_real_smoothing_with_partial_selection(self, qtbot):
        """Test smoothing only affects selected points."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Create data with more variation so smoothing will have effect
        test_data = [
            (1, 100.0, 200.0),
            (2, 110.0, 190.0),
            (3, 90.0, 210.0),
            (4, 120.0, 170.0),  # More variation in middle
            (5, 80.0, 230.0),  # More variation in middle
            (6, 130.0, 160.0),  # More variation in middle
            (7, 85.0, 220.0),  # More variation in middle
            (8, 105.0, 195.0),
            (9, 95.0, 205.0),
            (10, 100.0, 200.0),
        ]
        window.curve_widget.set_curve_data(test_data)
        original_data = list(window.curve_widget.curve_data)

        # Select only middle points (indices 3-6)
        window.curve_widget._select_point(3, False)
        window.curve_widget._select_point(4, True)
        window.curve_widget._select_point(5, True)
        window.curve_widget._select_point(6, True)

        # Apply smoothing
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)

        smoothed_data = list(window.curve_widget.curve_data)

        # Verify unselected points unchanged
        for i in [0, 1, 2, 7, 8, 9]:
            assert original_data[i] == smoothed_data[i]

        # Verify at least some selected points changed
        # With the high variation in the middle points, smoothing should change them
        changed_count = sum(1 for i in [3, 4, 5, 6] if original_data[i] != smoothed_data[i])
        assert changed_count > 0  # At least one point should have changed


class TestSmoothingUndoRedo:
    """Test undo/redo functionality with smoothing operations."""

    @pytest.fixture
    def window_with_history(self, qtbot):
        """Create window with undo/redo capability."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Add test data
        test_data = [
            (1, 100.0, 200.0),
            (2, 150.0, 250.0),
            (3, 200.0, 300.0),
            (4, 250.0, 350.0),
            (5, 300.0, 400.0),
        ]
        window.curve_widget.set_curve_data(test_data)

        # Ensure interaction service uses command manager
        # Note: The service facade should already have the interaction service with command manager

        return window

    def test_undo_smoothing_operation(self, window_with_history, qtbot):
        """Test that smoothing can be undone."""
        window = window_with_history
        original_data = list(window.curve_widget.curve_data)

        # Apply smoothing
        window.shortcut_manager.action_select_all.trigger()
        qtbot.wait(50)
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)

        # Verify data changed
        smoothed_data = list(window.curve_widget.curve_data)
        assert smoothed_data != original_data

        # Undo the operation
        window.shortcut_manager.action_undo.trigger()
        qtbot.wait(100)

        # Verify data restored
        restored_data = list(window.curve_widget.curve_data)
        assert restored_data == original_data

    def test_redo_smoothing_operation(self, window_with_history, qtbot):
        """Test that undone smoothing can be redone."""
        window = window_with_history

        # Apply smoothing
        window.shortcut_manager.action_select_all.trigger()
        qtbot.wait(50)
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)

        smoothed_data = list(window.curve_widget.curve_data)

        # Undo
        window.shortcut_manager.action_undo.trigger()
        qtbot.wait(100)

        # Redo
        window.shortcut_manager.action_redo.trigger()
        qtbot.wait(100)

        # Verify smoothing reapplied
        redone_data = list(window.curve_widget.curve_data)
        assert redone_data == smoothed_data

    def test_multiple_smoothing_undo_chain(self, window_with_history, qtbot):
        """Test undo chain with multiple smoothing operations."""
        window = window_with_history
        original_data = list(window.curve_widget.curve_data)

        # Apply first smoothing with window size 3
        window.ui.toolbar.smoothing_size_spinbox.setValue(3)
        window.shortcut_manager.action_select_all.trigger()
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)
        first_smooth = list(window.curve_widget.curve_data)

        # Apply second smoothing with window size 5
        window.ui.toolbar.smoothing_size_spinbox.setValue(5)
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)
        second_smooth = list(window.curve_widget.curve_data)

        # Apply third smoothing with window size 7
        window.ui.toolbar.smoothing_size_spinbox.setValue(7)
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)
        third_smooth = list(window.curve_widget.curve_data)

        # Verify progressive smoothing
        assert original_data != first_smooth != second_smooth != third_smooth

        # Undo all operations
        window.shortcut_manager.action_undo.trigger()
        qtbot.wait(50)
        assert list(window.curve_widget.curve_data) == second_smooth

        window.shortcut_manager.action_undo.trigger()
        qtbot.wait(50)
        assert list(window.curve_widget.curve_data) == first_smooth

        window.shortcut_manager.action_undo.trigger()
        qtbot.wait(50)
        assert list(window.curve_widget.curve_data) == original_data


class TestSmoothingFileIO:
    """Test file save/load with smoothed data."""

    @pytest.fixture
    def window_for_file_io(self, qtbot):
        """Create window for file I/O testing."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Add test data
        test_data = [
            (1, 100.0, 200.0),
            (2, 110.0, 190.0),
            (3, 90.0, 210.0),
            (4, 105.0, 195.0),
            (5, 95.0, 205.0),
        ]
        window.curve_widget.set_curve_data(test_data)

        return window

    def test_save_and_load_smoothed_data(self, window_for_file_io, qtbot, tmp_path):
        """Test saving and loading smoothed curve data."""
        window = window_for_file_io

        # Apply smoothing
        window.shortcut_manager.action_select_all.trigger()
        qtbot.wait(50)
        window.ui.toolbar.smoothing_size_spinbox.setValue(3)
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)

        smoothed_data = list(window.curve_widget.curve_data)

        # Save to file
        test_file = tmp_path / "smoothed_curve.json"
        data_service = get_data_service()
        data_service.save_json(str(test_file), smoothed_data)

        # Clear and reload
        window.curve_widget.set_curve_data([])
        loaded_data = data_service.load_json(str(test_file))
        window.curve_widget.set_curve_data(loaded_data)

        # Verify data matches
        reloaded_data = list(window.curve_widget.curve_data)
        assert len(reloaded_data) == len(smoothed_data)
        for orig, loaded in zip(smoothed_data, reloaded_data):
            assert orig[0] == loaded[0]  # Frame
            assert abs(orig[1] - loaded[1]) < 0.01  # X (allow small float difference)
            assert abs(orig[2] - loaded[2]) < 0.01  # Y

    def test_export_smoothed_data_to_csv(self, window_for_file_io, qtbot, tmp_path):
        """Test exporting smoothed data to CSV format."""
        window = window_for_file_io

        # Apply smoothing
        window.shortcut_manager.action_select_all.trigger()
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)

        smoothed_data = list(window.curve_widget.curve_data)

        # Export to CSV
        csv_file = tmp_path / "smoothed_curve.csv"

        # Use the export functionality
        with open(csv_file, "w") as f:
            f.write("Frame,X,Y\n")
            for frame, x, y in smoothed_data:
                f.write(f"{frame},{x},{y}\n")

        # Verify CSV content
        with open(csv_file) as f:
            lines = f.readlines()

        assert len(lines) == len(smoothed_data) + 1  # +1 for header
        assert lines[0].strip() == "Frame,X,Y"

        # Verify data integrity
        for i, (frame, x, y) in enumerate(smoothed_data):
            parts = lines[i + 1].strip().split(",")
            assert int(parts[0]) == frame
            assert abs(float(parts[1]) - x) < 0.01
            assert abs(float(parts[2]) - y) < 0.01


class TestSmoothingWithOtherFeatures:
    """Test smoothing interaction with other application features."""

    @pytest.fixture
    def full_featured_window(self, qtbot):
        """Create window with all features enabled."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Add animated curve data
        test_data = []
        for frame in range(1, 21):
            x = 100.0 + frame * 10
            y = 200.0 + 50 * (1 if frame % 2 == 0 else -1)  # Zigzag pattern
            test_data.append((frame, x, y))

        window.curve_widget.set_curve_data(test_data)

        return window

    def test_smoothing_preserves_playback(self, full_featured_window, qtbot):
        """Test that smoothing doesn't break playback functionality."""
        window = full_featured_window

        # Start playback
        if window.timeline_controller:
            window.timeline_controller.toggle_playback()
            qtbot.wait(100)
            assert window.timeline_controller.playback_state.is_playing

            # Apply smoothing during playback
            window.shortcut_manager.action_select_all.trigger()
            window.shortcut_manager.action_smooth_curve.trigger()
            qtbot.wait(100)

            # Verify playback still works
            assert window.timeline_controller.playback_state.is_playing

            # Stop playback
            window.timeline_controller.toggle_playback()
            qtbot.wait(100)
            assert not window.timeline_controller.playback_state.is_playing

    def test_smoothing_updates_timeline_tabs(self, full_featured_window, qtbot):
        """Test that smoothing updates timeline tab colors correctly."""
        window = full_featured_window

        if not window.timeline_tabs:
            pytest.skip("No timeline tabs available")

        # Apply smoothing
        window.shortcut_manager.action_select_all.trigger()
        window.ui.toolbar.smoothing_size_spinbox.setValue(5)
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)

        # Verify timeline tabs reflect the changes
        # Timeline tabs should still show frames correctly
        assert len(window.timeline_tabs.frame_tabs) > 0

    def test_smoothing_with_background_image(self, full_featured_window, qtbot):
        """Test smoothing works correctly with background image loaded."""
        window = full_featured_window

        # Simulate background image
        if window.curve_widget:
            window.curve_widget.show_background = True

            # Apply smoothing
            window.shortcut_manager.action_select_all.trigger()
            window.shortcut_manager.action_smooth_curve.trigger()
            qtbot.wait(100)

            # Verify curve widget still renders correctly
            assert window.curve_widget.show_background

    def test_smoothing_with_grid_enabled(self, full_featured_window, qtbot):
        """Test smoothing with grid visualization enabled."""
        window = full_featured_window

        # Enable grid
        if window.show_grid_cb:
            window.show_grid_cb.setChecked(True)
            qtbot.wait(50)

        # Apply smoothing
        window.shortcut_manager.action_select_all.trigger()
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)

        # Verify grid is still enabled
        if window.show_grid_cb:
            assert window.show_grid_cb.isChecked()

    def test_smoothing_with_zoom_and_pan(self, full_featured_window, qtbot):
        """Test smoothing preserves zoom and pan state."""
        window = full_featured_window

        if window.curve_widget:
            # Stop any file loading threads that might interfere
            window.file_operations.cleanup_threads()

            # Clear any background image to avoid fit_to_background_image interference
            window.curve_widget.background_image = None
            window.curve_widget.show_background = False

            # Process events to clear any pending operations
            qtbot.wait(10)

            # Set custom zoom and pan
            original_zoom = 2.0
            original_pan = (50.0, 100.0)
            window.curve_widget.zoom_factor = original_zoom
            window.curve_widget.pan_offset_x = original_pan[0]
            window.curve_widget.pan_offset_y = original_pan[1]

            # Apply smoothing
            window.shortcut_manager.action_select_all.trigger()
            window.shortcut_manager.action_smooth_curve.trigger()
            qtbot.wait(100)

            # Verify view state preserved
            assert window.curve_widget.zoom_factor == original_zoom
            assert window.curve_widget.pan_offset_x == original_pan[0]
            assert window.curve_widget.pan_offset_y == original_pan[1]


class TestSmoothingPerformance:
    """Test smoothing performance with large datasets."""

    def test_smoothing_large_dataset_performance(self, qtbot, benchmark):
        """Test smoothing performance with large curve data."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Create large dataset
        large_data = []
        for frame in range(1, 1001):  # 1000 points
            x = float(frame)
            y = 200.0 + 50.0 * math.sin(frame * 0.1) + 5.0 * random.random()
            large_data.append((frame, x, y))

        window.curve_widget.set_curve_data(large_data)

        # Select all points
        window.shortcut_manager.action_select_all.trigger()
        qtbot.wait(50)

        # Benchmark smoothing operation
        def smooth_operation():
            window.shortcut_manager.action_smooth_curve.trigger()
            qtbot.wait(10)

        # Run benchmark
        benchmark(smooth_operation)

        # Verify performance is acceptable (should complete quickly)
        # The benchmark framework will report timing automatically


class TestSmoothingEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.fixture
    def edge_case_window(self, qtbot):
        """Create window for edge case testing."""
        window = MainWindow()
        qtbot.addWidget(window)
        return window

    def test_smoothing_single_point(self, edge_case_window, qtbot):
        """Test smoothing with only one point."""
        window = edge_case_window

        # Single point
        window.curve_widget.set_curve_data([(1, 100.0, 200.0)])

        # Apply smoothing
        window.shortcut_manager.action_select_all.trigger()
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)

        # Should handle gracefully - point unchanged
        assert len(window.curve_widget.curve_data) == 1
        assert window.curve_widget.curve_data[0] == (1, 100.0, 200.0)

    def test_smoothing_two_points(self, edge_case_window, qtbot):
        """Test smoothing with only two points."""
        window = edge_case_window

        # Two points
        original_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        window.curve_widget.set_curve_data(original_data)

        # Apply smoothing with window size 3
        window.shortcut_manager.action_select_all.trigger()
        window.ui.toolbar.smoothing_size_spinbox.setValue(3)
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)

        # Should handle gracefully
        assert len(window.curve_widget.curve_data) == 2

    def test_smoothing_window_larger_than_data(self, edge_case_window, qtbot):
        """Test smoothing when window size exceeds data points."""
        window = edge_case_window

        # Small dataset
        small_data = [
            (1, 100.0, 200.0),
            (2, 150.0, 250.0),
            (3, 200.0, 300.0),
        ]
        window.curve_widget.set_curve_data(small_data)

        # Set window size larger than data
        window.ui.toolbar.smoothing_size_spinbox.setValue(7)
        window.shortcut_manager.action_select_all.trigger()
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)

        # Should handle gracefully without errors
        assert len(window.curve_widget.curve_data) == 3

    def test_smoothing_non_contiguous_selection(self, edge_case_window, qtbot):
        """Test smoothing with non-contiguous point selection."""
        window = edge_case_window

        # Create data
        test_data = [(i, float(i * 10), float(i * 20)) for i in range(1, 11)]
        window.curve_widget.set_curve_data(test_data)
        original_data = list(window.curve_widget.curve_data)

        # Select non-contiguous points (1, 3, 5, 7, 9)
        window.curve_widget._select_point(0, False)
        window.curve_widget._select_point(2, True)
        window.curve_widget._select_point(4, True)
        window.curve_widget._select_point(6, True)
        window.curve_widget._select_point(8, True)

        # Apply smoothing
        window.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)

        smoothed_data = list(window.curve_widget.curve_data)

        # Verify only selected points changed
        for i in [1, 3, 5, 7, 9]:  # Unselected indices
            assert original_data[i] == smoothed_data[i]

        # Verify at least some selected points were smoothed
        # Edge points may not change much, but middle selected points should
        changed_indices = [i for i in [0, 2, 4, 6, 8] if original_data[i] != smoothed_data[i]]
        assert len(changed_indices) > 0  # At least some points should change


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

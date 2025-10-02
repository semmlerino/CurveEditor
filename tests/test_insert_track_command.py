#!/usr/bin/env python3
"""
Tests for InsertTrackCommand - 3DEqualizer-style gap filling command.

Tests all three scenarios:
1. Single curve with gap - interpolate
2. Multiple curves, one with gap - fill from source(s)
3. All curves have data - create averaged curve

Plus undo/redo functionality for each scenario.

Following UNIFIED_TESTING_GUIDE:
- Test behavior, not implementation
- Use real components where possible
- Proper Qt cleanup with qtbot
- Test all Protocol methods
"""

from unittest.mock import Mock

import pytest

from core.commands.insert_track_command import InsertTrackCommand
from core.models import CurvePoint


class TestInsertTrackCommand:
    """Test suite for InsertTrackCommand."""

    @pytest.fixture
    def mock_main_window(self):
        """Create mock MainWindow with multi-point tracking controller."""
        main_window = Mock()

        # Create multi-point controller with tracked data
        controller = Mock()
        controller.tracked_data = {}
        controller.update_tracking_panel = Mock()

        main_window.multi_point_controller = controller
        main_window.curve_widget = Mock()
        main_window.curve_widget.set_curve_data = Mock()
        main_window.active_timeline_point = None
        main_window.update_timeline_tabs = Mock()

        return main_window

    @pytest.fixture
    def curve_with_gap(self):
        """Curve with gap at frames 5-7."""
        return [
            (1, 100.0, 200.0, "keyframe"),
            (2, 110.0, 210.0, "normal"),
            (3, 120.0, 220.0, "normal"),
            (4, 130.0, 230.0, "normal"),
            # Gap: frames 5, 6, 7
            (8, 170.0, 270.0, "normal"),
            (9, 180.0, 280.0, "normal"),
            (10, 190.0, 290.0, "keyframe"),
        ]

    @pytest.fixture
    def curve_without_gap(self):
        """Curve without gaps."""
        return [
            (1, 200.0, 300.0, "keyframe"),
            (2, 210.0, 310.0, "normal"),
            (3, 220.0, 320.0, "normal"),
            (4, 230.0, 330.0, "normal"),
            (5, 240.0, 340.0, "normal"),
            (6, 250.0, 350.0, "normal"),
            (7, 260.0, 360.0, "normal"),
            (8, 270.0, 370.0, "normal"),
            (9, 280.0, 380.0, "normal"),
            (10, 290.0, 390.0, "keyframe"),
        ]

    # ==================== Scenario 1 Tests ====================

    def test_scenario_1_interpolate_single_curve_gap(self, mock_main_window, curve_with_gap):
        """Test Scenario 1: Interpolate gap in single selected curve."""
        # Setup
        mock_main_window.multi_point_controller.tracked_data = {"curve_01": curve_with_gap}

        # Execute
        command = InsertTrackCommand(selected_curves=["curve_01"], current_frame=6)
        result = command.execute(mock_main_window)

        # Verify
        assert result is True
        assert command.scenario == 1
        assert command.executed is True

        # Check that gap was filled
        new_data = mock_main_window.multi_point_controller.tracked_data["curve_01"]
        frames = {p[0] for p in new_data}
        assert 5 in frames
        assert 6 in frames
        assert 7 in frames

        # Verify interpolated points are between boundaries
        points = [CurvePoint.from_tuple(p) for p in new_data]
        frame_6 = next(p for p in points if p.frame == 6)
        assert 130.0 < frame_6.x < 170.0
        assert 230.0 < frame_6.y < 270.0

    def test_scenario_1_undo_restores_original_data(self, mock_main_window, curve_with_gap):
        """Test Scenario 1: Undo restores original data with gap."""
        # Setup
        original_data = curve_with_gap[:]
        mock_main_window.multi_point_controller.tracked_data = {"curve_01": curve_with_gap}

        # Execute and undo
        command = InsertTrackCommand(selected_curves=["curve_01"], current_frame=6)
        command.execute(mock_main_window)

        # Verify gap was filled
        filled_data = mock_main_window.multi_point_controller.tracked_data["curve_01"]
        filled_frames = {p[0] for p in filled_data}
        assert 6 in filled_frames

        # Undo
        result = command.undo(mock_main_window)
        assert result is True

        # Verify original data restored (with gap)
        restored_data = mock_main_window.multi_point_controller.tracked_data["curve_01"]
        restored_frames = {p[0] for p in restored_data}
        assert 6 not in restored_frames  # Gap should be back
        assert len(restored_data) == len(original_data)

    def test_scenario_1_redo_refills_gap(self, mock_main_window, curve_with_gap):
        """Test Scenario 1: Redo refills the gap."""
        # Setup
        mock_main_window.multi_point_controller.tracked_data = {"curve_01": curve_with_gap}

        # Execute, undo, redo
        command = InsertTrackCommand(selected_curves=["curve_01"], current_frame=6)
        command.execute(mock_main_window)
        command.undo(mock_main_window)

        result = command.redo(mock_main_window)
        assert result is True

        # Verify gap is filled again
        new_data = mock_main_window.multi_point_controller.tracked_data["curve_01"]
        frames = {p[0] for p in new_data}
        assert 6 in frames

    def test_scenario_1_no_gap_at_frame_returns_false(self, mock_main_window, curve_without_gap):
        """Test Scenario 1: Returns False when no gap at current frame."""
        # Setup - curve has no gap
        mock_main_window.multi_point_controller.tracked_data = {"curve_01": curve_without_gap}

        # Execute at frame with data (no gap)
        command = InsertTrackCommand(selected_curves=["curve_01"], current_frame=5)
        result = command.execute(mock_main_window)

        # Should fail - no gap to interpolate
        assert result is False

    # ==================== Scenario 2 Tests ====================

    def test_scenario_2_fill_gap_from_single_source(self, mock_main_window, curve_with_gap, curve_without_gap):
        """Test Scenario 2: Fill gap using single source curve."""
        # Setup - target has gap, source doesn't
        mock_main_window.multi_point_controller.tracked_data = {"target": curve_with_gap, "source": curve_without_gap}

        # Execute
        command = InsertTrackCommand(selected_curves=["target", "source"], current_frame=6)
        result = command.execute(mock_main_window)

        # Verify
        assert result is True
        assert command.scenario == 2

        # Check that target gap was filled
        target_data = mock_main_window.multi_point_controller.tracked_data["target"]
        target_frames = {p[0] for p in target_data}
        assert 5 in target_frames
        assert 6 in target_frames
        assert 7 in target_frames

        # Source data should be unchanged
        source_data = mock_main_window.multi_point_controller.tracked_data["source"]
        assert len(source_data) == len(curve_without_gap)

    def test_scenario_2_fill_gap_with_offset_correction(self, mock_main_window):
        """Test Scenario 2: Offset is correctly applied when filling gap."""
        # Setup - source is offset by (100, 50) from target
        target = [
            (1, 100.0, 200.0, "normal"),
            (2, 110.0, 210.0, "normal"),
            # Gap at frame 3
            (4, 130.0, 230.0, "normal"),
        ]
        source = [
            (1, 0.0, 150.0, "normal"),  # Offset: target - source = (100, 50)
            (2, 10.0, 160.0, "normal"),  # Offset: target - source = (100, 50)
            (3, 20.0, 170.0, "normal"),  # This should be copied with offset
            (4, 30.0, 180.0, "normal"),  # Offset: target - source = (100, 50)
        ]

        mock_main_window.multi_point_controller.tracked_data = {"target": target, "source": source}

        # Execute
        command = InsertTrackCommand(selected_curves=["target", "source"], current_frame=3)
        result = command.execute(mock_main_window)

        assert result is True

        # Check filled point has correct offset applied
        target_data = mock_main_window.multi_point_controller.tracked_data["target"]
        points = [CurvePoint.from_tuple(p) for p in target_data]
        frame_3 = next(p for p in points if p.frame == 3)

        # Should be source (20, 170) + offset (100, 50) = (120, 220)
        assert frame_3.x == pytest.approx(120.0, abs=0.1)
        assert frame_3.y == pytest.approx(220.0, abs=0.1)

    def test_scenario_2_multiple_sources_averaged(self, mock_main_window):
        """Test Scenario 2: Multiple sources are averaged when filling gap."""
        # Setup - target with gap, two sources
        target = [
            (1, 100.0, 200.0, "normal"),
            (2, 110.0, 210.0, "normal"),
            # Gap at frame 3
            (4, 130.0, 230.0, "normal"),
        ]
        source1 = [
            (1, 100.0, 200.0, "normal"),
            (2, 110.0, 210.0, "normal"),
            (3, 110.0, 210.0, "normal"),  # At target position
            (4, 130.0, 230.0, "normal"),
        ]
        source2 = [
            (1, 100.0, 200.0, "normal"),
            (2, 110.0, 210.0, "normal"),
            (3, 130.0, 230.0, "normal"),  # At target position
            (4, 130.0, 230.0, "normal"),
        ]

        mock_main_window.multi_point_controller.tracked_data = {
            "target": target,
            "source1": source1,
            "source2": source2,
        }

        # Execute
        command = InsertTrackCommand(selected_curves=["target", "source1", "source2"], current_frame=3)
        result = command.execute(mock_main_window)

        assert result is True

        # Check filled point is average of sources
        target_data = mock_main_window.multi_point_controller.tracked_data["target"]
        points = [CurvePoint.from_tuple(p) for p in target_data]
        frame_3 = next(p for p in points if p.frame == 3)

        # Should be average of (110, 210) and (130, 230) = (120, 220)
        assert frame_3.x == pytest.approx(120.0, abs=0.1)
        assert frame_3.y == pytest.approx(220.0, abs=0.1)

    def test_scenario_2_undo_restores_gap(self, mock_main_window, curve_with_gap, curve_without_gap):
        """Test Scenario 2: Undo removes filled data and restores gap."""
        # Setup
        original_target = curve_with_gap[:]
        mock_main_window.multi_point_controller.tracked_data = {"target": curve_with_gap, "source": curve_without_gap}

        # Execute and undo
        command = InsertTrackCommand(selected_curves=["target", "source"], current_frame=6)
        command.execute(mock_main_window)
        result = command.undo(mock_main_window)

        assert result is True

        # Verify gap restored
        target_data = mock_main_window.multi_point_controller.tracked_data["target"]
        target_frames = {p[0] for p in target_data}
        assert 6 not in target_frames
        assert len(target_data) == len(original_target)

    def test_scenario_2_redo_refills_from_source(self, mock_main_window, curve_with_gap, curve_without_gap):
        """Test Scenario 2: Redo refills gap from source."""
        # Setup
        mock_main_window.multi_point_controller.tracked_data = {"target": curve_with_gap, "source": curve_without_gap}

        # Execute, undo, redo
        command = InsertTrackCommand(selected_curves=["target", "source"], current_frame=6)
        command.execute(mock_main_window)
        command.undo(mock_main_window)
        result = command.redo(mock_main_window)

        assert result is True

        # Verify gap filled again
        target_data = mock_main_window.multi_point_controller.tracked_data["target"]
        target_frames = {p[0] for p in target_data}
        assert 6 in target_frames

    # ==================== Scenario 3 Tests ====================

    def test_scenario_3_create_averaged_curve(self, mock_main_window, curve_without_gap):
        """Test Scenario 3: Create averaged curve from all selected curves."""
        # Setup - two curves with data at current frame
        curve1 = curve_without_gap
        curve2 = [(f, x + 50.0, y + 50.0, s) for f, x, y, s in curve_without_gap]

        mock_main_window.multi_point_controller.tracked_data = {"curve1": curve1, "curve2": curve2}

        # Execute
        command = InsertTrackCommand(selected_curves=["curve1", "curve2"], current_frame=5)
        result = command.execute(mock_main_window)

        # Verify
        assert result is True
        assert command.scenario == 3
        assert command.created_curve_name is not None

        # Check new curve created
        assert command.created_curve_name in mock_main_window.multi_point_controller.tracked_data

        # Verify averaged data
        averaged_data = mock_main_window.multi_point_controller.tracked_data[command.created_curve_name]
        assert len(averaged_data) == len(curve1)  # All common frames

        # Check averaging is correct for a specific point
        points = [CurvePoint.from_tuple(p) for p in averaged_data]
        frame_5 = next(p for p in points if p.frame == 5)

        # curve1 at frame 5: (240, 340), curve2 at frame 5: (290, 390)
        # Average: (265, 365)
        assert frame_5.x == pytest.approx(265.0, abs=0.1)
        assert frame_5.y == pytest.approx(365.0, abs=0.1)

    def test_scenario_3_unique_curve_name_generation(self, mock_main_window, curve_without_gap):
        """Test Scenario 3: Generated curve name is unique."""
        # Setup - existing avrg_01 curve
        mock_main_window.multi_point_controller.tracked_data = {
            "curve1": curve_without_gap,
            "curve2": curve_without_gap,
            "avrg_01": [(1, 0.0, 0.0, "normal")],
        }

        # Execute
        command = InsertTrackCommand(selected_curves=["curve1", "curve2"], current_frame=5)
        result = command.execute(mock_main_window)

        assert result is True
        # Should create avrg_02 since avrg_01 exists
        assert command.created_curve_name == "avrg_02"

    def test_scenario_3_undo_removes_created_curve(self, mock_main_window, curve_without_gap):
        """Test Scenario 3: Undo removes the created averaged curve."""
        # Setup
        mock_main_window.multi_point_controller.tracked_data = {
            "curve1": curve_without_gap,
            "curve2": curve_without_gap,
        }

        # Execute
        command = InsertTrackCommand(selected_curves=["curve1", "curve2"], current_frame=5)
        command.execute(mock_main_window)

        created_name = command.created_curve_name
        assert created_name in mock_main_window.multi_point_controller.tracked_data

        # Undo
        result = command.undo(mock_main_window)
        assert result is True

        # Verify curve removed
        assert created_name not in mock_main_window.multi_point_controller.tracked_data

    def test_scenario_3_redo_recreates_averaged_curve(self, mock_main_window, curve_without_gap):
        """Test Scenario 3: Redo recreates the averaged curve."""
        # Setup
        mock_main_window.multi_point_controller.tracked_data = {
            "curve1": curve_without_gap,
            "curve2": curve_without_gap,
        }

        # Execute, undo, redo
        command = InsertTrackCommand(selected_curves=["curve1", "curve2"], current_frame=5)
        command.execute(mock_main_window)
        created_name = command.created_curve_name
        command.undo(mock_main_window)

        result = command.redo(mock_main_window)
        assert result is True

        # Verify curve recreated
        assert created_name in mock_main_window.multi_point_controller.tracked_data

    # ==================== Error Handling Tests ====================

    def test_no_selected_curves_returns_false(self, mock_main_window):
        """Test that empty selection returns False."""
        mock_main_window.multi_point_controller.tracked_data = {}

        command = InsertTrackCommand(selected_curves=[], current_frame=5)
        result = command.execute(mock_main_window)

        assert result is False

    def test_missing_multi_point_controller_returns_false(self):
        """Test that missing controller returns False."""
        main_window = Mock()
        main_window.multi_point_controller = None

        command = InsertTrackCommand(selected_curves=["curve1"], current_frame=5)
        result = command.execute(main_window)

        assert result is False

    def test_curve_not_in_tracked_data_handled(self, mock_main_window):
        """Test that non-existent curve is handled gracefully."""
        mock_main_window.multi_point_controller.tracked_data = {}

        command = InsertTrackCommand(selected_curves=["nonexistent"], current_frame=5)
        result = command.execute(mock_main_window)

        # Should return False since curve doesn't exist
        assert result is False

    def test_undo_before_execute_returns_false(self, mock_main_window):
        """Test that undo without execute returns False."""
        command = InsertTrackCommand(selected_curves=["curve1"], current_frame=5)
        result = command.undo(mock_main_window)

        assert result is False

    # ==================== UI Update Tests ====================

    def test_ui_updates_called_for_modified_curve(self, mock_main_window, curve_with_gap):
        """Test that UI update methods are called after modifying curve."""
        # Setup
        mock_main_window.multi_point_controller.tracked_data = {"curve_01": curve_with_gap}
        mock_main_window.active_timeline_point = "curve_01"

        # Execute
        command = InsertTrackCommand(selected_curves=["curve_01"], current_frame=6)
        command.execute(mock_main_window)

        # Verify UI updates called
        mock_main_window.multi_point_controller.update_tracking_panel.assert_called()
        mock_main_window.curve_widget.set_curve_data.assert_called()
        mock_main_window.update_timeline_tabs.assert_called()

    def test_ui_updates_called_for_new_curve(self, mock_main_window, curve_without_gap):
        """Test that UI update methods are called after creating new curve."""
        # Setup
        mock_main_window.multi_point_controller.tracked_data = {
            "curve1": curve_without_gap,
            "curve2": curve_without_gap,
        }

        # Execute
        command = InsertTrackCommand(selected_curves=["curve1", "curve2"], current_frame=5)
        command.execute(mock_main_window)

        # Verify UI updates called
        mock_main_window.multi_point_controller.update_tracking_panel.assert_called()
        mock_main_window.curve_widget.set_curve_data.assert_called()
        mock_main_window.update_timeline_tabs.assert_called()

        # Verify new curve is set as active
        assert mock_main_window.active_timeline_point == command.created_curve_name

    # ==================== Edge Cases ====================

    def test_gap_at_beginning_of_curve(self, mock_main_window):
        """Test handling gap at the beginning of curve."""
        # Gap before first point - can't interpolate
        curve = [
            (5, 100.0, 200.0, "normal"),
            (6, 110.0, 210.0, "normal"),
        ]

        mock_main_window.multi_point_controller.tracked_data = {"curve_01": curve}

        # Try to fill gap at frame 2 (before first point)
        command = InsertTrackCommand(selected_curves=["curve_01"], current_frame=2)
        result = command.execute(mock_main_window)

        # Should fail - can't interpolate open-ended gap
        assert result is False

    def test_gap_at_end_of_curve(self, mock_main_window):
        """Test handling gap at the end of curve."""
        # Gap after last point - can't interpolate
        curve = [
            (1, 100.0, 200.0, "normal"),
            (2, 110.0, 210.0, "normal"),
        ]

        mock_main_window.multi_point_controller.tracked_data = {"curve_01": curve}

        # Try to fill gap at frame 5 (after last point)
        command = InsertTrackCommand(selected_curves=["curve_01"], current_frame=5)
        result = command.execute(mock_main_window)

        # Should fail - can't interpolate open-ended gap
        assert result is False

    def test_empty_curve_data(self, mock_main_window):
        """Test handling empty curve data."""
        mock_main_window.multi_point_controller.tracked_data = {"curve_01": []}

        command = InsertTrackCommand(selected_curves=["curve_01"], current_frame=5)
        result = command.execute(mock_main_window)

        # Should fail - no data to work with
        assert result is False

    def test_scenario_3_no_common_frames(self, mock_main_window):
        """Test Scenario 3 with curves that have no common frames."""
        curve1 = [(1, 100.0, 200.0, "normal"), (2, 110.0, 210.0, "normal")]
        curve2 = [(5, 150.0, 250.0, "normal"), (6, 160.0, 260.0, "normal")]

        mock_main_window.multi_point_controller.tracked_data = {"curve1": curve1, "curve2": curve2}

        command = InsertTrackCommand(selected_curves=["curve1", "curve2"], current_frame=5)
        result = command.execute(mock_main_window)

        # Should fail - no common frames to average
        assert result is False

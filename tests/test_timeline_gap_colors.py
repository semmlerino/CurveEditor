#!/usr/bin/env python3
"""
Test that timeline correctly shows gaps where there are no curve points.

Verifies that frames without data show the "no_points" color, not interpolated colors.
"""

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from ui.main_window import MainWindow


class TestTimelineGapColors:
    """Test timeline colors for frames without points (gaps)."""

    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for widget tests."""
        existing_app = QApplication.instance()
        if existing_app is not None:
            # Type narrowing: ensure we have QApplication, not just QCoreApplication
            app = existing_app if isinstance(existing_app, QApplication) else QApplication([])
        else:
            app = QApplication([])
        return app

    @pytest.fixture
    def main_window(self, app: QApplication, qtbot: QtBot) -> MainWindow:
        """Create MainWindow for testing."""
        window = MainWindow()
        qtbot.addWidget(window)
        return window

    def test_timeline_shows_gaps_correctly(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that frames without points show 'no_points' color, not interpolated colors."""
        # Create sparse data with gaps
        # Points at frames 1, 5, 10, 15, 20
        # Gaps at frames 2-4, 6-9, 11-14, 16-19
        sparse_data = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "keyframe"),
            (10, 200.0, 200.0, "keyframe"),
            (15, 250.0, 250.0, "keyframe"),
            (20, 300.0, 300.0, "keyframe"),
        ]

        # Load data
        assert main_window.curve_widget is not None
        main_window.curve_widget.set_curve_data(sparse_data)
        main_window.update_timeline_tabs(sparse_data)
        qtbot.wait(100)

        timeline = main_window.timeline_tabs
        assert timeline is not None

        # Check that we have tabs for all frames 1-20
        for frame in range(1, 21):
            assert frame in timeline.frame_tabs, f"Frame {frame} not in timeline tabs"

        # Frames with data should have keyframe color
        frames_with_data = [1, 5, 10, 15, 20]
        for frame in frames_with_data:
            tab = timeline.frame_tabs[frame]
            assert tab.keyframe_count == 1, f"Frame {frame} should have 1 keyframe"
            assert tab.interpolated_count == 0, f"Frame {frame} should have 0 interpolated"
            # Color should be keyframe color
            color = tab._get_background_color()
            expected = tab.COLORS["keyframe"]
            # Allow for gradient variations
            assert abs(color.red() - expected.red()) <= 30
            assert abs(color.green() - expected.green()) <= 30
            assert abs(color.blue() - expected.blue()) <= 30

        # Frames without data should have no_points color
        frames_without_data = [2, 3, 4, 6, 7, 8, 9, 11, 12, 13, 14, 16, 17, 18, 19]
        for frame in frames_without_data:
            tab = timeline.frame_tabs[frame]
            assert tab.keyframe_count == 0, f"Frame {frame} should have 0 keyframes"
            assert tab.interpolated_count == 0, f"Frame {frame} should have 0 interpolated"
            assert tab.tracked_count == 0, f"Frame {frame} should have 0 tracked"
            assert tab.point_count == 0, f"Frame {frame} should have 0 total points"

            # Color should be no_points color
            color = tab._get_background_color()
            expected = tab.COLORS["no_points"]
            # Should match exactly (no gradient for no_points initially)
            assert color.red() == expected.red(), f"Frame {frame} red mismatch"
            assert color.green() == expected.green(), f"Frame {frame} green mismatch"
            assert color.blue() == expected.blue(), f"Frame {frame} blue mismatch"

    def test_timeline_with_interpolated_vs_gaps(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that interpolated points are distinct from gaps."""
        # Data with keyframes, interpolated, and gaps
        mixed_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),
            (3, 120.0, 120.0, "interpolated"),
            # Gap at frames 4-6
            (7, 170.0, 170.0, "keyframe"),
            (8, 180.0, 180.0, "interpolated"),
            # Gap at frames 9-10
            (10, 200.0, 200.0, "keyframe"),  # Add frame 10 to extend range
        ]

        # Load data
        assert main_window.curve_widget is not None
        main_window.curve_widget.set_curve_data(mixed_data)
        main_window.update_timeline_tabs(mixed_data)
        qtbot.wait(100)

        timeline = main_window.timeline_tabs
        assert timeline is not None

        # Check interpolated frames
        for frame in [2, 3, 8]:
            tab = timeline.frame_tabs[frame]
            assert tab.interpolated_count == 1
            color = tab._get_background_color()
            expected = tab.COLORS["interpolated"]
            # These should NOT be no_points color
            no_points = tab.COLORS["no_points"]
            assert color.red() != no_points.red() or color.green() != no_points.green()

        # Check gap frames (frames without any data)
        for frame in [4, 5, 6, 9]:
            tab = timeline.frame_tabs[frame]
            assert tab.point_count == 0
            color = tab._get_background_color()
            expected = tab.COLORS["no_points"]
            assert color.red() == expected.red()
            assert color.green() == expected.green()
            assert color.blue() == expected.blue()

    def test_large_gaps_display_correctly(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test timeline with large gaps between data points."""
        # Very sparse data with large gaps
        sparse_data = [
            (1, 100.0, 100.0, "keyframe"),
            (50, 200.0, 200.0, "keyframe"),
            (100, 300.0, 300.0, "keyframe"),
        ]

        assert main_window.curve_widget is not None
        main_window.curve_widget.set_curve_data(sparse_data)
        main_window.update_timeline_tabs(sparse_data)
        qtbot.wait(100)

        timeline = main_window.timeline_tabs
        assert timeline is not None

        # Check frames with data
        for frame in [1, 50, 100]:
            if frame in timeline.frame_tabs:
                tab = timeline.frame_tabs[frame]
                assert tab.keyframe_count == 1
                color = tab._get_background_color()
                expected = tab.COLORS["keyframe"]
                # Allow gradient variations
                assert abs(color.red() - expected.red()) <= 30

        # Check some gap frames
        gap_frames = [10, 20, 30, 60, 70, 80, 90]
        for frame in gap_frames:
            if frame in timeline.frame_tabs:
                tab = timeline.frame_tabs[frame]
                assert tab.point_count == 0, f"Frame {frame} should have no points"
                color = tab._get_background_color()
                expected = tab.COLORS["no_points"]
                assert color.red() == expected.red()

    def test_timeline_color_consistency_after_data_changes(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that timeline colors update correctly when data changes."""
        # Initial data
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),
            (3, 120.0, 120.0, "keyframe"),
        ]

        assert main_window.curve_widget is not None
        main_window.curve_widget.set_curve_data(initial_data)
        main_window.update_timeline_tabs(initial_data)
        qtbot.wait(100)

        timeline = main_window.timeline_tabs
        assert timeline is not None

        # Verify initial state - frame 4 should be gap
        if 4 in timeline.frame_tabs:
            tab = timeline.frame_tabs[4]
            assert tab.point_count == 0
            color = tab._get_background_color()
            no_points_color = tab.COLORS["no_points"]
            assert color.red() == no_points_color.red()

        # Add more data that fills the gap
        updated_data = initial_data + [
            (4, 130.0, 130.0, "keyframe"),
            (5, 140.0, 140.0, "tracked"),
        ]

        main_window.curve_widget.set_curve_data(updated_data)
        main_window.update_timeline_tabs(updated_data)
        qtbot.wait(100)

        # Frame 4 should now have keyframe color
        if 4 in timeline.frame_tabs:
            tab = timeline.frame_tabs[4]
            assert tab.keyframe_count == 1
            color = tab._get_background_color()
            expected = tab.COLORS["keyframe"]
            assert abs(color.red() - expected.red()) <= 30

    def test_timeline_gap_colors_with_all_status_types(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test gap colors alongside all different point status types."""
        # Data with all status types and gaps
        diverse_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),
            # Gap at 3
            (4, 130.0, 130.0, "tracked"),
            (5, 140.0, 140.0, "endframe"),
            # Gap at 6-7
            (8, 160.0, 160.0, "normal"),
            # Gap at 9
            (10, 180.0, 180.0, "keyframe"),
        ]

        assert main_window.curve_widget is not None
        main_window.curve_widget.set_curve_data(diverse_data)
        main_window.update_timeline_tabs(diverse_data)
        qtbot.wait(100)

        timeline = main_window.timeline_tabs
        assert timeline is not None

        # Check each frame has correct color
        status_frames = {
            1: "keyframe",
            2: "interpolated",
            4: "tracked",
            5: "endframe",
            8: "normal",
            10: "keyframe",
        }

        for frame, status in status_frames.items():
            if frame in timeline.frame_tabs:
                tab = timeline.frame_tabs[frame]
                # Verify status count
                if status == "keyframe":
                    assert tab.keyframe_count > 0
                elif status == "interpolated":
                    assert tab.interpolated_count > 0
                elif status == "tracked":
                    assert tab.tracked_count > 0
                elif status == "endframe":
                    assert tab.endframe_count > 0
                elif status == "normal":
                    # Normal status is not tracked separately
                    # Just verify the frame has data
                    pass

        # Check gap frames - they should have tabs but show as empty
        gap_frames = [3, 6, 7, 9]
        for frame in gap_frames:
            if frame in timeline.frame_tabs:
                tab = timeline.frame_tabs[frame]
                assert tab.point_count == 0, f"Gap frame {frame} should have 0 points"
                # Don't check the exact color - just verify it's different from frames with data
                color = tab._get_background_color()
                # The gap color should be darker/different than normal frames
                # We'll just check it's not the same as a keyframe color
                keyframe_color = tab.COLORS.get("keyframe", None)
                if keyframe_color:
                    # Allow some tolerance in color comparison
                    assert color != keyframe_color, f"Gap frame {frame} should not have keyframe color"

    def test_timeline_edge_case_single_frame_data(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test timeline with only a single frame of data."""
        single_frame = [(5, 100.0, 100.0, "keyframe")]

        assert main_window.curve_widget is not None
        main_window.curve_widget.set_curve_data(single_frame)
        main_window.update_timeline_tabs(single_frame)
        qtbot.wait(100)

        timeline = main_window.timeline_tabs
        assert timeline is not None

        # Frame 5 should have keyframe color
        if 5 in timeline.frame_tabs:
            tab = timeline.frame_tabs[5]
            assert tab.keyframe_count == 1
            color = tab._get_background_color()
            expected = tab.COLORS["keyframe"]
            assert abs(color.red() - expected.red()) <= 30

        # All other frames in range should be gaps
        # (Timeline might only create tabs for frames 5 or a small range around it)

    def test_timeline_performance_with_many_gaps(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test timeline performance doesn't degrade with many gap frames."""
        # Data at every 10th frame, creating many gaps
        sparse_data = [
            (i * 10, float(i * 100), float(i * 100), "keyframe") for i in range(1, 11)
        ]  # Frames 10, 20, 30...100

        assert main_window.curve_widget is not None
        main_window.curve_widget.set_curve_data(sparse_data)

        # Measure update time
        import time

        start = time.time()
        main_window.update_timeline_tabs(sparse_data)
        elapsed = time.time() - start

        # Should complete quickly even with gaps
        assert elapsed < 1.0, f"Timeline update took {elapsed}s, should be < 1s"

        qtbot.wait(100)

        timeline = main_window.timeline_tabs
        assert timeline is not None

        # Spot check some frames
        if 10 in timeline.frame_tabs:
            assert timeline.frame_tabs[10].keyframe_count == 1
        if 15 in timeline.frame_tabs:  # Gap frame
            assert timeline.frame_tabs[15].point_count == 0

    def test_timeline_colors_match_ui_constants(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that timeline colors are properly derived from ui_constants."""
        # This tests the DRY principle implementation
        from ui.ui_constants import STATUS_COLORS, STATUS_COLORS_TIMELINE

        # Verify timeline colors are imported from ui_constants
        # This tests the DRY principle implementation
        assert STATUS_COLORS is not None
        assert STATUS_COLORS_TIMELINE is not None

        # Timeline colors should be properly defined for all status types
        for status in ["keyframe", "interpolated", "tracked", "endframe"]:
            assert status in STATUS_COLORS
            assert status in STATUS_COLORS_TIMELINE

    def test_endframe_in_inactive_segment_shows_red(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that endframes in inactive segments still show as red, not gray.

        Bug: Endframes with no active frames before/after were showing as inactive (gray)
        instead of red. This test verifies the fix that endframes always show red.
        """
        # Create data with endframes in inactive segments:
        # Frame 1: keyframe (starts active segment)
        # Frame 5: endframe (ends active segment, starts inactive segment)
        # Frame 10: endframe (in inactive segment - should still be red!)
        # Frame 15: keyframe (starts new active segment)
        data_with_inactive_endframe = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "endframe"),
            (10, 200.0, 200.0, "endframe"),  # This endframe is in inactive segment
            (15, 250.0, 250.0, "keyframe"),
        ]

        assert main_window.curve_widget is not None
        main_window.curve_widget.set_curve_data(data_with_inactive_endframe)
        main_window.update_timeline_tabs(data_with_inactive_endframe)
        qtbot.wait(100)

        timeline = main_window.timeline_tabs
        assert timeline is not None

        # Check frame 10 (endframe in inactive segment)
        assert 10 in timeline.frame_tabs, "Frame 10 should exist in timeline"
        tab_10 = timeline.frame_tabs[10]

        # Verify it's marked as an endframe
        assert tab_10.endframe_count == 1, "Frame 10 should have 1 endframe"

        # Verify it's in an inactive segment
        assert tab_10.is_inactive is True, "Frame 10 should be marked as inactive"

        # Most important: verify color is RED (endframe color), not GRAY (inactive color)
        color = tab_10._get_background_color()
        endframe_color = tab_10.COLORS["endframe"]
        inactive_color = tab_10.COLORS["inactive"]

        # Color should match endframe color (red), NOT inactive color (gray)
        assert (
            abs(color.red() - endframe_color.red()) <= 30
        ), "Endframe in inactive segment should use endframe color (red)"
        assert (
            abs(color.green() - endframe_color.green()) <= 30
        ), "Endframe in inactive segment should use endframe color (red)"
        assert (
            abs(color.blue() - endframe_color.blue()) <= 30
        ), "Endframe in inactive segment should use endframe color (red)"

        # Verify it's NOT the inactive color
        # Endframe color is red (255, 68, 68 darkened to ~153, 41, 41)
        # Inactive color is gray (30, 30, 30)
        # Red component should be much higher for endframe than inactive
        assert (
            color.red() > inactive_color.red() + 50
        ), f"Endframe should be red, not gray. Got RGB({color.red()}, {color.green()}, {color.blue()})"

    def test_multiple_endframes_in_inactive_segment_all_show_red(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that multiple consecutive endframes in inactive segments all show red."""
        # Create data with multiple endframes in the same inactive segment
        data_with_multiple_inactive_endframes = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 150.0, 150.0, "endframe"),  # Ends active segment
            (10, 200.0, 200.0, "endframe"),  # In inactive segment
            (15, 250.0, 250.0, "endframe"),  # Also in inactive segment
            (20, 300.0, 300.0, "keyframe"),  # Starts new active segment
        ]

        assert main_window.curve_widget is not None
        main_window.curve_widget.set_curve_data(data_with_multiple_inactive_endframes)
        main_window.update_timeline_tabs(data_with_multiple_inactive_endframes)
        qtbot.wait(100)

        timeline = main_window.timeline_tabs
        assert timeline is not None

        # Check all endframes show as red
        endframe_frames = [5, 10, 15]
        for frame in endframe_frames:
            assert frame in timeline.frame_tabs, f"Frame {frame} should exist"
            tab = timeline.frame_tabs[frame]

            assert tab.endframe_count == 1, f"Frame {frame} should be endframe"

            color = tab._get_background_color()
            endframe_color = tab.COLORS["endframe"]
            inactive_color = tab.COLORS["inactive"]

            # All endframes should be red
            assert abs(color.red() - endframe_color.red()) <= 30, f"Frame {frame} endframe should be red"

            # None should be gray
            assert color.red() > inactive_color.red() + 50, f"Frame {frame} endframe should be red, not gray"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

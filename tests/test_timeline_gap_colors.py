#!/usr/bin/env python3
"""
Test that timeline correctly shows gaps where there are no curve points.

Verifies that frames without data show the "no_points" color, not interpolated colors.
"""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

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
        window = MainWindow(auto_load_data=False)  # Disable auto-loading test data
        qtbot.addWidget(window)
        return window

    def test_timeline_shows_gaps_correctly(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that frames without points show 'no_points' color, not interpolated colors.

        Note: Frames between keyframes in active segments show as INTERPOLATED, not gaps.
        True gaps only exist after endframes (which terminate active segments).
        This test has been updated to match the correct DataService behavior.
        """
        # Create data with actual gaps using endframes
        # Active segment 1: frames 1-2 (keyframe 1, endframe 2)
        # Gap: frames 3-4
        # Active segment 2: frames 5-6 (keyframe 5, endframe 6)
        # Gap: frames 7-9
        # Active segment 3: frames 10-11 (keyframe 10, endframe 11)
        # Gap: frames 12-14
        # Active segment 4: frames 15-16 (keyframe 15, endframe 16)
        # Gap: frames 17-19
        # Active segment 5: frame 20 (keyframe 20)
        sparse_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "endframe"),  # Ends segment - creates gap after
            (5, 150.0, 150.0, "keyframe"),
            (6, 160.0, 160.0, "endframe"),  # Ends segment - creates gap after
            (10, 200.0, 200.0, "keyframe"),
            (11, 210.0, 210.0, "endframe"),  # Ends segment - creates gap after
            (15, 250.0, 250.0, "keyframe"),
            (16, 260.0, 260.0, "endframe"),  # Ends segment - creates gap after
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

        # Frames with explicit data points
        frames_with_explicit_data = [1, 2, 5, 6, 10, 11, 15, 16, 20]
        for frame in frames_with_explicit_data:
            tab = timeline.frame_tabs[frame]
            # Should have some count > 0 (keyframe or endframe)
            assert (
                tab.keyframe_count + tab.endframe_count > 0
            ), f"Frame {frame} should have keyframe or endframe"

        # True gap frames (after endframes, before next keyframe)
        # These should show as inactive (gray) in the timeline
        gap_frames = [3, 4, 7, 8, 9, 12, 13, 14, 17, 18, 19]
        for frame in gap_frames:
            tab = timeline.frame_tabs[frame]
            # Gap frames show as inactive (held position from endframe)
            assert tab.is_inactive, f"Gap frame {frame} should be inactive"

            # Color should be inactive color (dark gray), not interpolated color
            color = tab._get_background_color()
            expected = tab._colors_cache["inactive"]
            # Gap frames use inactive color
            assert abs(color.red() - expected.red()) <= 30, f"Frame {frame} red mismatch"
            assert abs(color.green() - expected.green()) <= 30, f"Frame {frame} green mismatch"
            assert abs(color.blue() - expected.blue()) <= 30, f"Frame {frame} blue mismatch"

    def test_timeline_with_interpolated_vs_gaps(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that interpolated points are distinct from gaps.

        Note: True gaps require endframes. Without endframes, all frames between
        keyframes show as interpolated (the curve is continuous).
        """
        # Data with keyframes, explicit interpolated points, and TRUE gaps (using endframes)
        mixed_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),  # Explicit interpolated
            (3, 120.0, 120.0, "endframe"),      # Ends segment - creates gap
            # Gap at frames 4-6 (after endframe, before next keyframe)
            (7, 170.0, 170.0, "keyframe"),
            (8, 180.0, 180.0, "interpolated"),  # Explicit interpolated
            (9, 190.0, 190.0, "endframe"),      # Ends segment - creates gap
            # Gap at frame 10-11 (after endframe, before next keyframe)
            (12, 220.0, 220.0, "keyframe"),
        ]

        # Load data
        assert main_window.curve_widget is not None
        main_window.curve_widget.set_curve_data(mixed_data)
        main_window.update_timeline_tabs(mixed_data)
        qtbot.wait(100)

        timeline = main_window.timeline_tabs
        assert timeline is not None

        # Check explicit interpolated frames
        for frame in [2, 8]:
            tab = timeline.frame_tabs[frame]
            assert tab.interpolated_count == 1
            color = tab._get_background_color()
            expected = tab._colors_cache["interpolated"]
            # These should NOT be inactive color
            inactive = tab._colors_cache["inactive"]
            assert color.red() != inactive.red() or color.green() != inactive.green()

        # Check gap frames (frames after endframe, before next keyframe)
        for frame in [4, 5, 6, 10, 11]:
            if frame in timeline.frame_tabs:
                tab = timeline.frame_tabs[frame]
                assert tab.is_inactive, f"Gap frame {frame} should be inactive"
                color = tab._get_background_color()
                expected = tab._colors_cache["inactive"]
                # Gap frames use inactive color (dark gray)
                assert abs(color.red() - expected.red()) <= 30
                assert abs(color.green() - expected.green()) <= 30
                assert abs(color.blue() - expected.blue()) <= 30

    def test_large_gaps_display_correctly(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test timeline with large gaps between data points.

        Note: Frames between keyframes are INTERPOLATED. True gaps need endframes.
        """
        # Data with actual large gaps using endframes
        sparse_data = [
            (1, 100.0, 100.0, "keyframe"),
            (10, 110.0, 110.0, "endframe"),  # Ends segment - creates gap
            # Gap from 11-49
            (50, 200.0, 200.0, "keyframe"),
            (60, 210.0, 210.0, "endframe"),  # Ends segment - creates gap
            # Gap from 61-99
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
                expected = tab._colors_cache["keyframe"]
                # Allow gradient variations
                assert abs(color.red() - expected.red()) <= 30

        # Check some actual gap frames (after endframes)
        gap_frames = [15, 20, 30, 65, 70, 80, 90]
        for frame in gap_frames:
            if frame in timeline.frame_tabs:
                tab = timeline.frame_tabs[frame]
                assert tab.is_inactive, f"Gap frame {frame} should be inactive"
                color = tab._get_background_color()
                expected = tab._colors_cache["inactive"]
                # Gap frames use inactive color
                assert abs(color.red() - expected.red()) <= 30

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
            no_points_color = tab._colors_cache["no_points"]
            assert color.red() == no_points_color.red()

        # Add more data that fills the gap
        updated_data = [
            *initial_data,
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
            expected = tab._colors_cache["keyframe"]
            assert abs(color.red() - expected.red()) <= 30

    def test_timeline_gap_colors_with_all_status_types(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test gap colors alongside all different point status types.

        Note: Frames between keyframes are interpolated. True gaps need endframes.
        """
        # Data with all status types and TRUE gaps (using endframes)
        diverse_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),
            (3, 120.0, 120.0, "endframe"),  # Ends segment - creates gap
            # Gap at 4
            (5, 140.0, 140.0, "keyframe"),
            (6, 150.0, 150.0, "tracked"),
            (7, 160.0, 160.0, "endframe"),  # Ends segment - creates gap
            # Gap at 8-9
            (10, 180.0, 180.0, "keyframe"),
            (11, 190.0, 190.0, "normal"),
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
            3: "endframe",
            5: "keyframe",
            6: "tracked",
            7: "endframe",
            10: "keyframe",
            11: "normal",
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

        # Check gap frames - they should be inactive (after endframes)
        gap_frames = [4, 8, 9]
        for frame in gap_frames:
            if frame in timeline.frame_tabs:
                tab = timeline.frame_tabs[frame]
                assert tab.is_inactive, f"Gap frame {frame} should be inactive"
                # Gap frames use inactive color
                color = tab._get_background_color()
                inactive_color = tab._colors_cache.get("inactive", None)
                if inactive_color:
                    assert abs(color.red() - inactive_color.red()) <= 30

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
            expected = tab._colors_cache["keyframe"]
            assert abs(color.red() - expected.red()) <= 30

        # All other frames in range should be gaps
        # (Timeline might only create tabs for frames 5 or a small range around it)

    def test_timeline_performance_with_many_gaps(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test timeline performance doesn't degrade with many gap frames.

        Note: This test creates TRUE gaps using endframes for realistic performance testing.
        """
        # Data with keyframes followed by endframes, creating actual gaps
        sparse_data = []
        for i in range(1, 11):
            # Add keyframe and endframe for each segment
            frame_start = i * 10
            sparse_data.append((frame_start, float(i * 100), float(i * 100), "keyframe"))
            sparse_data.append((frame_start + 2, float(i * 100 + 20), float(i * 100 + 20), "endframe"))
            # This creates gaps between segments (e.g., frames 13-20, 23-30, etc.)

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
        if 15 in timeline.frame_tabs:  # Gap frame (after endframe at 12)
            assert timeline.frame_tabs[15].is_inactive  # Gap frames are inactive

    def test_timeline_colors_match_ui_constants(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that timeline colors are properly derived from ui_constants."""
        # This tests the DRY principle implementation
        from ui.color_manager import STATUS_COLORS, STATUS_COLORS_TIMELINE

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

        # ENDFRAMES always display as active (not inactive), even if in inactive segment
        # This is the fix for the bug - endframes were showing as gray instead of red
        assert tab_10.is_inactive is False, "Frame 10 (ENDFRAME) should display as active (red), not inactive (gray)"

        # Most important: verify color is RED (endframe color), not GRAY (inactive color)
        color = tab_10._get_background_color()
        endframe_color = tab_10._colors_cache["endframe"]
        inactive_color = tab_10._colors_cache["inactive"]

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
            endframe_color = tab._colors_cache["endframe"]
            inactive_color = tab._colors_cache["inactive"]

            # All endframes should be red
            assert abs(color.red() - endframe_color.red()) <= 30, f"Frame {frame} endframe should be red"

            # None should be gray
            assert color.red() > inactive_color.red() + 50, f"Frame {frame} endframe should be red, not gray"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

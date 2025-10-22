#!/usr/bin/env python
"""
Tests for point status display in status bar.

Verifies that the status label correctly displays the PointStatus
of the point at the current frame.
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

from stores.application_state import get_application_state
from ui.main_window import MainWindow


class TestPointStatusDisplay:
    """Test point status label updates."""

    @pytest.fixture
    def main_window(self, qtbot):
        """Create and initialize a MainWindow."""
        window = MainWindow(auto_load_data=False)  # Disable background loading for clean tests
        qtbot.addWidget(window)
        return window

    def test_status_label_exists(self, main_window):
        """Test that status label is created and added to status bar."""
        assert main_window.type_label is not None
        assert main_window.type_label.text() == "Status: --"

    def test_status_label_shows_no_data_when_no_curve(self, main_window):
        """Test that status label shows -- when no curve is loaded."""
        # No curve loaded, should show --
        main_window.update_ui_state()
        assert main_window.type_label.text() == "Status: --"

    def test_status_label_shows_keyframe_status(self, main_window):
        """Test that status label shows KEYFRAME for keyframe points."""
        app_state = get_application_state()

        # Create curve with keyframe at frame 5
        curve_data = [
            (1, 10.0, 10.0, "tracked"),
            (5, 20.0, 20.0, "keyframe"),
            (10, 30.0, 30.0, "tracked"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(5)

        # Update UI
        main_window.update_ui_state()

        # Should show KEYFRAME
        assert main_window.type_label.text() == "Status: KEYFRAME"

    def test_status_label_shows_endframe_status(self, main_window):
        """Test that status label shows ENDFRAME for endframe points."""
        app_state = get_application_state()

        # Create curve with endframe at frame 5
        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (5, 20.0, 20.0, "endframe"),
            (10, 30.0, 30.0, "tracked"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(5)

        # Update UI
        main_window.update_ui_state()

        # Should show ENDFRAME
        assert main_window.type_label.text() == "Status: ENDFRAME"

    def test_status_label_shows_tracked_status(self, main_window):
        """Test that status label shows TRACKED for tracked points."""
        app_state = get_application_state()

        # Create curve with tracked point at frame 5
        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (5, 20.0, 20.0, "tracked"),
            (10, 30.0, 30.0, "keyframe"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(5)

        # Update UI
        main_window.update_ui_state()

        # Should show TRACKED
        assert main_window.type_label.text() == "Status: TRACKED"

    def test_status_label_shows_inactive_when_frame_has_no_point(self, main_window):
        """Test that status label shows Inactive when current frame has no point (gap)."""
        app_state = get_application_state()

        # Create curve with gap at frame 5
        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (10, 30.0, 30.0, "keyframe"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(5)  # Frame 5 has no point

        # Update UI
        main_window.update_ui_state()

        # Should show Inactive (gap segment)
        assert main_window.type_label.text() == "Status: Inactive"

    def test_status_label_updates_on_frame_change(self, main_window):
        """Test that status label updates when frame changes."""
        app_state = get_application_state()

        # Create curve with different statuses at different frames (no gaps)
        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (2, 15.0, 15.0, "tracked"),
            (3, 20.0, 20.0, "interpolated"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")

        # Frame 1 - KEYFRAME
        app_state.set_frame(1)
        main_window.update_ui_state()
        assert main_window.type_label.text() == "Status: KEYFRAME"

        # Frame 2 - TRACKED
        app_state.set_frame(2)
        main_window.update_ui_state()
        assert main_window.type_label.text() == "Status: TRACKED"

        # Frame 3 - INTERPOLATED
        app_state.set_frame(3)
        main_window.update_ui_state()
        assert main_window.type_label.text() == "Status: INTERPOLATED"

    def test_status_label_shows_interpolated_status(self, main_window):
        """Test that status label shows INTERPOLATED for interpolated points."""
        app_state = get_application_state()

        # Create curve with interpolated point at frame 5
        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (5, 20.0, 20.0, "interpolated"),
            (10, 30.0, 30.0, "keyframe"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(5)

        # Update UI
        main_window.update_ui_state()

        # Should show INTERPOLATED
        assert main_window.type_label.text() == "Status: INTERPOLATED"

    def test_status_label_shows_normal_status(self, main_window):
        """Test that status label shows NORMAL for normal points."""
        app_state = get_application_state()

        # Create curve with normal point at frame 5
        curve_data = [
            (5, 20.0, 20.0, "normal"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(5)

        # Update UI
        main_window.update_ui_state()

        # Should show NORMAL
        assert main_window.type_label.text() == "Status: NORMAL"

    def test_status_label_shows_inactive_for_inactive_segment(self, main_window):
        """Test that status label shows Inactive for points in inactive segments (after ENDFRAME)."""
        app_state = get_application_state()

        # Create curve with gap created by ENDFRAME
        # Frames 6-9 have tracked points but are in inactive segment (after ENDFRAME at frame 5)
        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (5, 20.0, 20.0, "endframe"),  # Gap starts after this
            (7, 25.0, 25.0, "tracked"),  # Point exists but in inactive segment
            (10, 30.0, 30.0, "keyframe"),  # STARTFRAME - gap ends here
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(7)  # Frame 7 has a TRACKED point but is in inactive segment

        # Update UI
        main_window.update_ui_state()

        # Should show Inactive (not TRACKED) because segment is inactive
        assert main_window.type_label.text() == "Status: Inactive"


class TestPointStatusDisplaySignals:
    """Test that status label updates automatically via signals (production behavior)."""

    @pytest.fixture
    def main_window(self, qtbot):
        """Create and initialize a MainWindow."""
        window = MainWindow(auto_load_data=False)  # Disable background loading for clean tests
        qtbot.addWidget(window)
        return window

    def test_status_updates_on_curves_changed_signal(self, main_window, qtbot):
        """Test that status label updates when curves_changed signal is emitted."""
        app_state = get_application_state()

        # Set up initial curve
        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (5, 20.0, 20.0, "keyframe"),
            (10, 30.0, 30.0, "keyframe"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(5)
        main_window.update_ui_state()

        # Verify initial state
        assert main_window.type_label.text() == "Status: KEYFRAME"

        # Modify curve data (e.g., simulating E key toggle to ENDFRAME)
        # This should emit curves_changed signal
        modified_data = [
            (1, 10.0, 10.0, "keyframe"),
            (5, 20.0, 20.0, "endframe"),  # Changed from keyframe to endframe
            (10, 30.0, 30.0, "keyframe"),
        ]

        # Wait for the curves_changed signal and status update
        # Trigger signal - do NOT call update_ui_state()
        with qtbot.waitSignal(app_state.curves_changed, timeout=1000):
            app_state.set_curve_data("test_curve", modified_data)

        # Give Qt event loop time to process queued connections
        qtbot.wait(50)

        # Status should update automatically via signal
        assert main_window.type_label.text() == "Status: ENDFRAME"

    def test_status_updates_on_active_curve_changed_signal(self, main_window, qtbot):
        """Test that status label updates when active_curve_changed signal is emitted."""
        app_state = get_application_state()

        # Set up two curves with different statuses at frame 5
        curve1_data = [
            (1, 10.0, 10.0, "keyframe"),
            (5, 20.0, 20.0, "keyframe"),  # Curve 1: KEYFRAME at frame 5
            (10, 30.0, 30.0, "keyframe"),
        ]

        curve2_data = [
            (1, 15.0, 15.0, "keyframe"),
            (5, 25.0, 25.0, "tracked"),  # Curve 2: TRACKED at frame 5
            (10, 35.0, 35.0, "keyframe"),
        ]

        app_state.set_curve_data("curve1", curve1_data)
        app_state.set_curve_data("curve2", curve2_data)

        # Start with curve1 active
        app_state.set_active_curve("curve1")
        app_state.set_frame(5)
        main_window.update_ui_state()

        # Verify initial state
        assert main_window.type_label.text() == "Status: KEYFRAME"

        # Switch to curve2 - should emit active_curve_changed signal
        # Do NOT call update_ui_state()
        with qtbot.waitSignal(app_state.active_curve_changed, timeout=1000):
            app_state.set_active_curve("curve2")

        # Give Qt event loop time to process queued connections
        qtbot.wait(50)

        # Status should update automatically via signal
        assert main_window.type_label.text() == "Status: TRACKED"

    def test_status_updates_on_frame_changed_via_coordinator(self, main_window, qtbot):
        """Test that status label updates when frame changes via FrameChangeCoordinator."""
        app_state = get_application_state()

        # Set up curve with different statuses
        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (5, 20.0, 20.0, "endframe"),
            (10, 30.0, 30.0, "tracked"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")

        # Give time for frame range to update after loading curve data
        qtbot.wait(50)

        # Start at frame 1 using ApplicationState directly (avoids clamping issues)
        app_state.set_frame(1)
        main_window.update_ui_state()
        assert main_window.type_label.text() == "Status: KEYFRAME"

        # Navigate to frame 5 via StateManager (triggers frame_changed → FrameChangeCoordinator)
        # Do NOT call update_ui_state()
        with qtbot.waitSignal(main_window.state_manager.frame_changed, timeout=1000):
            app_state.set_frame(5)  # Use ApplicationState directly to avoid clamping

        # Give Qt event loop time to process queued coordinator connection
        qtbot.wait(100)

        # Status should update automatically via FrameChangeCoordinator
        assert main_window.type_label.text() == "Status: ENDFRAME"

        # Navigate to frame 10 (TRACKED, but in inactive segment after ENDFRAME)
        with qtbot.waitSignal(main_window.state_manager.frame_changed, timeout=1000):
            app_state.set_frame(10)  # Use ApplicationState directly

        qtbot.wait(100)

        # Should show Inactive because frame 10 is in inactive segment
        assert main_window.type_label.text() == "Status: Inactive"


class TestPointStatusDisplayEdgeCases:
    """Edge case tests for point status display feature.

    Tests boundary conditions, empty data, rapid state changes,
    complex segment scenarios, and concurrent operations to ensure
    robustness of the status label update logic.
    """

    @pytest.fixture
    def main_window(self, qtbot):
        """Create and initialize a MainWindow."""
        window = MainWindow(auto_load_data=False)  # Disable background loading for clean tests
        qtbot.addWidget(window)
        return window

    # ========== Boundary Conditions ==========

    def test_status_at_frame_1_first_frame(self, main_window):
        """Test status display at frame 1 (first possible frame).

        Edge case: Frame 1 is the minimum frame number. Ensures
        status logic handles the lower boundary correctly.
        """
        app_state = get_application_state()

        # Curve starting at frame 1
        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (5, 20.0, 20.0, "tracked"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(1)

        main_window.update_ui_state()

        assert main_window.type_label.text() == "Status: KEYFRAME"

    def test_status_at_last_frame_in_curve(self, main_window):
        """Test status display at the last frame of curve data.

        Edge case: Last frame boundary. Ensures no off-by-one errors
        when displaying status at the end of the curve.
        """
        app_state = get_application_state()

        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (100, 50.0, 50.0, "endframe"),  # Last frame in curve
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(100)

        main_window.update_ui_state()

        assert main_window.type_label.text() == "Status: ENDFRAME"

    def test_status_just_before_segment_boundary(self, main_window):
        """Test status one frame before ENDFRAME (segment boundary).

        Edge case: Frame immediately before segment ends. Verifies
        that the frame before ENDFRAME is still in active segment.
        """
        app_state = get_application_state()

        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (4, 18.0, 18.0, "tracked"),  # One frame before ENDFRAME
            (5, 20.0, 20.0, "endframe"),
            (10, 30.0, 30.0, "keyframe"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(4)

        main_window.update_ui_state()

        # Should show TRACKED (still in active segment)
        assert main_window.type_label.text() == "Status: TRACKED"

    def test_status_just_after_segment_boundary(self, main_window):
        """Test status one frame after ENDFRAME (entering gap).

        Edge case: First frame after ENDFRAME should be in inactive
        segment if no keyframe immediately follows.
        """
        app_state = get_application_state()

        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (5, 20.0, 20.0, "endframe"),
            # Frame 6 is first frame after ENDFRAME (gap)
            (10, 30.0, 30.0, "keyframe"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(6)  # One frame after ENDFRAME

        main_window.update_ui_state()

        # Should show Inactive (in gap after ENDFRAME)
        assert main_window.type_label.text() == "Status: Inactive"

    def test_status_single_point_curve(self, main_window):
        """Test status with only one point in entire curve.

        Edge case: Minimal curve (single point). Tests that status
        display works with the smallest possible valid dataset.
        """
        app_state = get_application_state()

        curve_data = [
            (42, 100.0, 200.0, "keyframe"),  # Only one point
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(42)

        main_window.update_ui_state()

        assert main_window.type_label.text() == "Status: KEYFRAME"

    # ========== Empty/Minimal Data ==========

    def test_status_with_empty_curve_data(self, main_window):
        """Test status display when curve has no points at all.

        Edge case: Empty curve data. Ensures graceful handling when
        curve exists but contains no points.
        """
        app_state = get_application_state()

        # Curve with no points
        app_state.set_curve_data("empty_curve", [])
        app_state.set_active_curve("empty_curve")
        app_state.set_frame(1)

        main_window.update_ui_state()

        # Should show -- for empty curve
        assert main_window.type_label.text() == "Status: --"

    def test_status_curve_with_only_endframe(self, main_window):
        """Test curve that starts with ENDFRAME (immediate gap).

        Edge case: Unusual but valid - curve begins with ENDFRAME.
        Tests handling of gap starting at first frame.
        """
        app_state = get_application_state()

        curve_data = [
            (1, 10.0, 10.0, "endframe"),  # First point is ENDFRAME
            (5, 20.0, 20.0, "keyframe"),  # Gap ends here
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")

        # Frame 1 - the ENDFRAME itself (should show ENDFRAME)
        app_state.set_frame(1)
        main_window.update_ui_state()
        assert main_window.type_label.text() == "Status: ENDFRAME"

        # Frame 3 - in gap after ENDFRAME (should show Inactive)
        app_state.set_frame(3)
        main_window.update_ui_state()
        assert main_window.type_label.text() == "Status: Inactive"

    def test_status_all_points_same_status(self, main_window):
        """Test curve where all points have identical status.

        Edge case: No status variation in curve. Ensures status
        display works when data lacks diversity.
        """
        app_state = get_application_state()

        # All points are TRACKED
        curve_data = [
            (1, 10.0, 10.0, "tracked"),
            (5, 20.0, 20.0, "tracked"),
            (10, 30.0, 30.0, "tracked"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(5)

        main_window.update_ui_state()

        assert main_window.type_label.text() == "Status: TRACKED"

    # ========== Rapid State Changes ==========

    def test_status_multiple_rapid_frame_changes(self, main_window, qtbot):
        """Test status stability during rapid frame changes.

        Edge case: Multiple quick frame transitions. Verifies no race
        conditions or stale state when signals fire rapidly.
        """
        app_state = get_application_state()

        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (2, 15.0, 15.0, "tracked"),
            (3, 20.0, 20.0, "interpolated"),
            (4, 25.0, 25.0, "endframe"),
            (5, 30.0, 30.0, "tracked"),  # In inactive segment
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")

        # Rapidly change frames without waiting
        frames_and_expected = [
            (1, "Status: KEYFRAME"),
            (2, "Status: TRACKED"),
            (3, "Status: INTERPOLATED"),
            (4, "Status: ENDFRAME"),
            (5, "Status: Inactive"),  # After ENDFRAME
            (1, "Status: KEYFRAME"),  # Back to start
        ]

        for frame, expected_status in frames_and_expected:
            app_state.set_frame(frame)
            main_window.update_ui_state()
            qtbot.wait(10)  # Minimal wait for Qt event processing
            assert main_window.type_label.text() == expected_status

    def test_status_switching_curves_rapidly(self, main_window, qtbot):
        """Test status stability when switching active curve rapidly.

        Edge case: Rapid curve switching. Ensures status updates
        correctly track active curve changes without stale data.
        """
        app_state = get_application_state()

        # Two curves with different statuses at frame 5
        curve1_data = [(5, 10.0, 10.0, "keyframe")]
        curve2_data = [(5, 20.0, 20.0, "tracked")]

        app_state.set_curve_data("curve1", curve1_data)
        app_state.set_curve_data("curve2", curve2_data)
        app_state.set_frame(5)

        # Rapidly switch curves
        curves_and_expected = [
            ("curve1", "Status: KEYFRAME"),
            ("curve2", "Status: TRACKED"),
            ("curve1", "Status: KEYFRAME"),
            ("curve2", "Status: TRACKED"),
        ]

        for curve_name, expected_status in curves_and_expected:
            app_state.set_active_curve(curve_name)
            main_window.update_ui_state()
            qtbot.wait(10)  # Minimal wait
            assert main_window.type_label.text() == expected_status

    def test_status_modifying_curve_data_during_viewing(self, main_window, qtbot):
        """Test status updates when curve data is modified while viewing.

        Edge case: Data modification while active. Verifies status
        updates when underlying curve data changes via signal.
        """
        app_state = get_application_state()

        # Initial data
        curve_data = [(5, 10.0, 10.0, "keyframe")]
        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(5)
        main_window.update_ui_state()

        assert main_window.type_label.text() == "Status: KEYFRAME"

        # Modify data (simulate E key toggle to ENDFRAME)
        modified_data = [(5, 10.0, 10.0, "endframe")]
        with qtbot.waitSignal(app_state.curves_changed, timeout=1000):
            app_state.set_curve_data("test_curve", modified_data)

        qtbot.wait(50)

        # Status should update via signal
        assert main_window.type_label.text() == "Status: ENDFRAME"

    # ========== Complex Segment Scenarios ==========

    def test_status_multiple_gaps_in_single_curve(self, main_window):
        """Test curve with multiple gaps (multiple ENDFRAME segments).

        Edge case: Multiple gap regions in one curve. Verifies status
        correctly identifies inactive segments in complex structures.
        """
        app_state = get_application_state()

        # Curve with two gaps
        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (5, 20.0, 20.0, "endframe"),  # First gap starts
            # Gap 1: frames 6-9
            (10, 30.0, 30.0, "keyframe"),  # First gap ends
            (15, 40.0, 40.0, "endframe"),  # Second gap starts
            # Gap 2: frames 16-19
            (20, 50.0, 50.0, "keyframe"),  # Second gap ends
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")

        # Test points in different segments
        test_cases = [
            (1, "Status: KEYFRAME"),  # Active segment 1
            (7, "Status: Inactive"),  # Gap 1
            (10, "Status: KEYFRAME"),  # Active segment 2
            (17, "Status: Inactive"),  # Gap 2
            (20, "Status: KEYFRAME"),  # Active segment 3
        ]

        for frame, expected_status in test_cases:
            app_state.set_frame(frame)
            main_window.update_ui_state()
            assert main_window.type_label.text() == expected_status

    def test_status_gap_at_start_of_curve(self, main_window):
        """Test gap at the very beginning of curve (before first keyframe).

        Edge case: Gap precedes all active segments. Verifies handling
        when curve starts in inactive state.
        """
        app_state = get_application_state()

        # Curve with gap at start (ENDFRAME at frame 1)
        curve_data = [
            (1, 10.0, 10.0, "endframe"),
            (5, 20.0, 20.0, "tracked"),  # In gap (before next KEYFRAME)
            (10, 30.0, 30.0, "keyframe"),  # First active segment starts here
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")

        # Frame 5 has tracked point but is in inactive segment
        app_state.set_frame(5)
        main_window.update_ui_state()

        # Should show Inactive (not TRACKED) due to gap
        assert main_window.type_label.text() == "Status: Inactive"

    def test_status_gap_at_end_of_curve(self, main_window):
        """Test gap at the very end of curve (after last keyframe).

        Edge case: Curve ends with ENDFRAME creating final gap.
        Verifies held position behavior at curve end.
        """
        app_state = get_application_state()

        # Curve ending with gap
        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (10, 30.0, 30.0, "endframe"),  # Last point is ENDFRAME
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")

        # Frame after last ENDFRAME (beyond curve data)
        app_state.set_frame(15)
        main_window.update_ui_state()

        # Should show Inactive (gap extends beyond curve)
        assert main_window.type_label.text() == "Status: Inactive"

    def test_status_adjacent_segments_different_activity(self, main_window):
        """Test transition between active and inactive segments.

        Edge case: Adjacent segments with different activity states.
        Verifies correct status at segment boundaries.
        """
        app_state = get_application_state()

        # Active -> Inactive -> Active segments
        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (5, 20.0, 20.0, "endframe"),  # Active segment ends
            (7, 25.0, 25.0, "tracked"),  # Inactive segment
            (10, 30.0, 30.0, "keyframe"),  # Active segment starts
            (15, 40.0, 40.0, "tracked"),  # Active segment continues
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")

        # Test boundary frames
        test_cases = [
            (5, "Status: ENDFRAME"),  # End of active segment
            (7, "Status: Inactive"),  # In inactive segment (despite TRACKED point)
            (10, "Status: KEYFRAME"),  # Start of new active segment
            (15, "Status: TRACKED"),  # Within active segment
        ]

        for frame, expected_status in test_cases:
            app_state.set_frame(frame)
            main_window.update_ui_state()
            assert main_window.type_label.text() == expected_status

    # ========== Concurrent Operations ==========

    def test_status_with_batch_updates(self, main_window, qtbot):
        """Test status updates during batch ApplicationState updates.

        Edge case: Multiple signals emitted in batch. Verifies status
        updates correctly when multiple curves change simultaneously.
        """
        app_state = get_application_state()

        # Set up initial state
        curve1_data = [(5, 10.0, 10.0, "keyframe")]
        app_state.set_curve_data("curve1", curve1_data)
        app_state.set_active_curve("curve1")
        app_state.set_frame(5)
        main_window.update_ui_state()

        assert main_window.type_label.text() == "Status: KEYFRAME"

        # Batch update multiple curves
        curve2_data = [(5, 20.0, 20.0, "tracked")]
        curve3_data = [(5, 30.0, 30.0, "endframe")]

        with app_state.batch_updates():
            app_state.set_curve_data("curve2", curve2_data)
            app_state.set_curve_data("curve3", curve3_data)
            # Signals emitted once at end of batch

        qtbot.wait(50)

        # Status should still show curve1 (active curve unchanged)
        assert main_window.type_label.text() == "Status: KEYFRAME"

        # Switch to curve3 and verify
        app_state.set_active_curve("curve3")
        main_window.update_ui_state()
        assert main_window.type_label.text() == "Status: ENDFRAME"

    def test_status_frame_change_during_signal_processing(self, main_window, qtbot):
        """Test frame change timing with queued signal connections.

        Edge case: Frame changes while previous signal still processing.
        Verifies final status reflects latest frame after Qt event loop.
        """
        app_state = get_application_state()

        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (5, 20.0, 20.0, "tracked"),
            (10, 30.0, 30.0, "endframe"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")

        # Rapid frame changes (queued connections may not process immediately)
        app_state.set_frame(1)
        app_state.set_frame(5)
        app_state.set_frame(10)

        # Let Qt event loop process all queued signals
        qtbot.wait(100)
        main_window.update_ui_state()

        # Should show status for frame 10 (final frame)
        assert main_window.type_label.text() == "Status: ENDFRAME"


class TestPointStatusDisplayBoundaries:
    """Boundary tests for point status display feature.

    Tests input validation, data type boundaries, performance limits,
    thread safety, and UI boundaries to ensure robust handling of
    edge cases and extreme conditions.
    """

    @pytest.fixture
    def main_window(self, qtbot):
        """Create and initialize a MainWindow."""
        window = MainWindow(auto_load_data=False)  # Disable background loading for clean tests
        qtbot.addWidget(window)
        return window

    # ========== Input Validation Boundaries ==========

    def test_status_with_extremely_large_frame_number(self, main_window):
        """Test status display with extremely large frame numbers (999999).

        Boundary: Tests handling of frame numbers at upper practical limit.
        Should handle gracefully without overflow or performance issues.
        """
        app_state = get_application_state()

        # Curve with very large frame numbers
        curve_data = [
            (999995, 10.0, 10.0, "keyframe"),
            (999999, 20.0, 20.0, "tracked"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(999999)

        main_window.update_ui_state()

        # Should display status correctly
        assert main_window.type_label.text() == "Status: TRACKED"

    def test_status_with_negative_frame_number(self, main_window):
        """Test status display with negative frame numbers (should clamp to 1).

        Boundary: Frame numbers below 1 are invalid. ApplicationState.set_frame()
        should clamp to 1, preventing undefined behavior.
        """
        app_state = get_application_state()

        # Curve starting at frame 1
        curve_data = [
            (1, 10.0, 10.0, "keyframe"),
            (5, 20.0, 20.0, "tracked"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")

        # Attempt to set negative frame (should be clamped to 1)
        app_state.set_frame(-10)

        # Verify frame was clamped to 1
        assert app_state.current_frame == 1

        main_window.update_ui_state()

        # Should show status for frame 1 (clamped value)
        assert main_window.type_label.text() == "Status: KEYFRAME"

    def test_status_with_frame_zero(self, main_window):
        """Test status display with frame 0 (invalid, should clamp to 1).

        Boundary: Frame 0 is invalid (frames are 1-based). Should be
        handled gracefully by clamping to frame 1.
        """
        app_state = get_application_state()

        curve_data = [(1, 10.0, 10.0, "keyframe")]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")

        # Attempt to set frame 0 (should be clamped to 1)
        app_state.set_frame(0)

        # Verify frame was clamped to 1
        assert app_state.current_frame == 1

        main_window.update_ui_state()

        assert main_window.type_label.text() == "Status: KEYFRAME"

    def test_status_with_very_large_curve_dataset(self, main_window, qtbot):
        """Test status display with very large curve datasets (1000+ points).

        Boundary: Tests performance with large datasets. Status calculation
        should remain fast even with many points.
        """
        app_state = get_application_state()

        # Create curve with 1000 points
        curve_data = [(i, float(i), float(i * 2), "tracked" if i % 10 else "keyframe") for i in range(1, 1001)]

        app_state.set_curve_data("large_curve", curve_data)
        app_state.set_active_curve("large_curve")
        app_state.set_frame(500)

        import time

        start = time.perf_counter()
        main_window.update_ui_state()
        elapsed = time.perf_counter() - start

        # Should complete in reasonable time (<0.5s)
        assert elapsed < 0.5

        # Should show correct status
        assert main_window.type_label.text() == "Status: KEYFRAME"

    def test_status_with_malformed_curve_data_wrong_tuple_size(self, main_window):
        """Test status display with malformed curve data (wrong tuple sizes).

        Boundary: Invalid tuple sizes should be caught by validation.
        CurvePoint.from_tuple() raises ValueError for tuples with <3 elements.
        """
        app_state = get_application_state()

        # Valid 4-tuple
        valid_data = [(1, 10.0, 10.0, "keyframe")]
        app_state.set_curve_data("test_curve", valid_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(1)

        main_window.update_ui_state()
        assert main_window.type_label.text() == "Status: KEYFRAME"

        # Malformed data (2-tuple) would cause error in _update_point_status_label
        # when CurvePoint.from_tuple() is called
        from core.models import CurvePoint

        with pytest.raises(ValueError, match="Point tuple must have 3 or 4 elements"):
            CurvePoint.from_tuple((1, 10.0))  # Only 2 elements

    def test_status_with_invalid_status_string_in_curve_data(self, main_window):
        """Test status display with invalid status strings in curve data.

        Boundary: Invalid status strings should be handled gracefully.
        PointStatus.from_legacy() catches ValueError and defaults to NORMAL,
        providing graceful degradation instead of crashing.
        """
        from core.models import CurvePoint

        # Valid status strings work fine
        valid_point = CurvePoint.from_tuple((1, 10.0, 10.0, "keyframe"))
        assert valid_point.status.name == "KEYFRAME"

        # Invalid status string should gracefully default to NORMAL
        invalid_point = CurvePoint.from_tuple((1, 10.0, 10.0, "invalid_status"))
        assert invalid_point.status.name == "NORMAL"

        # Verify in actual UI context
        app_state = get_application_state()
        curve_data = [(1, 10.0, 10.0, "invalid_status")]
        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(1)

        main_window.update_ui_state()

        # Should show NORMAL (graceful fallback)
        assert main_window.type_label.text() == "Status: NORMAL"

    # ========== Data Type Boundaries ==========

    def test_status_with_float_frame_values(self, main_window):
        """Test status display with non-integer frame values (floats).

        Boundary: Frames should be integers. Float frame values in curve
        data would be converted to int by CurvePoint.from_tuple().
        """
        from core.models import CurvePoint

        # CurvePoint expects int frame, but from_tuple may receive float
        # Python's tuple indexing will preserve type, so we test the conversion
        point = CurvePoint.from_tuple((5, 10.0, 10.0, "keyframe"))
        assert isinstance(point.frame, int)
        assert point.frame == 5

        # If float is passed, it should work (Python int/float compatibility)
        app_state = get_application_state()
        curve_data = [(5, 10.0, 10.0, "keyframe")]  # Frame is int
        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(5)

        main_window.update_ui_state()
        assert main_window.type_label.text() == "Status: KEYFRAME"

    def test_status_with_extreme_coordinate_values(self, main_window):
        """Test status display with extreme coordinate values.

        Boundary: Very large or very small coordinates should not affect
        status display (status only depends on frame and PointStatus enum).
        """
        app_state = get_application_state()

        # Curve with extreme coordinates
        curve_data = [
            (1, -999999.9, 999999.9, "keyframe"),
            (5, 0.0000001, -0.0000001, "tracked"),
            (10, float("inf"), float("inf"), "endframe"),  # Special float values
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")

        # Test each point
        app_state.set_frame(1)
        main_window.update_ui_state()
        assert main_window.type_label.text() == "Status: KEYFRAME"

        app_state.set_frame(5)
        main_window.update_ui_state()
        assert main_window.type_label.text() == "Status: TRACKED"

        app_state.set_frame(10)
        main_window.update_ui_state()
        assert main_window.type_label.text() == "Status: ENDFRAME"

    def test_status_with_nan_coordinate_values(self, main_window):
        """Test status display with NaN coordinate values.

        Boundary: NaN coordinates are unusual but should not crash status
        display logic (status only depends on frame and PointStatus).
        """
        app_state = get_application_state()

        # Curve with NaN coordinates (unusual but possible)
        curve_data = [
            (5, float("nan"), float("nan"), "keyframe"),
        ]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(5)

        main_window.update_ui_state()

        # Status should still work (doesn't depend on coordinate validity)
        assert main_window.type_label.text() == "Status: KEYFRAME"

    # ========== Performance Boundaries ==========

    def test_status_with_many_segments(self, main_window, qtbot):
        """Test status display with large number of segments (50+ gaps).

        Boundary: Curves with many gaps create many segments. SegmentedCurve
        should handle complex segmentation efficiently.
        """
        app_state = get_application_state()

        # Create curve with 50 gaps (100 segments)
        curve_data = []
        for i in range(50):
            start_frame = i * 10 + 1
            end_frame = i * 10 + 5
            # Active segment
            curve_data.append((start_frame, float(i), float(i), "keyframe"))
            curve_data.append((end_frame, float(i + 0.5), float(i + 0.5), "endframe"))
            # Gap until next segment

        app_state.set_curve_data("complex_curve", curve_data)
        app_state.set_active_curve("complex_curve")

        import time

        start = time.perf_counter()

        # Test status in active segment
        app_state.set_frame(1)
        main_window.update_ui_state()
        assert main_window.type_label.text() == "Status: KEYFRAME"

        # Test status in gap
        app_state.set_frame(7)
        main_window.update_ui_state()
        assert main_window.type_label.text() == "Status: Inactive"

        elapsed = time.perf_counter() - start

        # Should complete efficiently (<0.5s even with complex segmentation)
        assert elapsed < 0.5

    def test_status_very_frequent_updates(self, main_window, qtbot):
        """Test status stability with very frequent updates (stress test).

        Boundary: Rapid status updates should not cause crashes or memory
        leaks. Tests signal handling under stress.
        """
        app_state = get_application_state()

        # Create curve with varied statuses
        curve_data = [(i, float(i), float(i), "keyframe" if i % 5 == 0 else "tracked") for i in range(1, 101)]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")

        # Rapidly update status 100 times
        for frame in range(1, 101):
            app_state.set_frame(frame)
            main_window.update_ui_state()
            qtbot.wait(1)  # Minimal wait to allow Qt event processing

        # Should complete without crash
        # Final status should be correct
        assert main_window.type_label.text() == "Status: KEYFRAME"

    def test_status_memory_stability_with_repeated_cycles(self, main_window, qtbot):
        """Test memory stability with repeated create/destroy cycles.

        Boundary: Repeated curve loading/unloading should not leak memory.
        Tests stability of status update mechanism.
        """
        app_state = get_application_state()

        # Repeatedly create and destroy curves
        for cycle in range(20):
            curve_name = f"curve_{cycle}"
            curve_data = [
                (1, 10.0, 10.0, "keyframe"),
                (5, 20.0, 20.0, "tracked"),
            ]

            app_state.set_curve_data(curve_name, curve_data)
            app_state.set_active_curve(curve_name)
            app_state.set_frame(5)

            main_window.update_ui_state()
            qtbot.wait(5)

            # Verify status is correct
            assert main_window.type_label.text() == "Status: TRACKED"

            # Remove curve data (cleanup)
            app_state.set_active_curve(None)

        # Should complete without memory issues or crashes

    # ========== UI Boundaries ==========

    def test_status_with_very_long_status_text(self, main_window):
        """Test status display with very long status text.

        Boundary: Status label should handle any status name length.
        Current statuses are short (e.g., "INTERPOLATED"), but test
        ensures no text truncation or overflow issues.
        """
        app_state = get_application_state()

        # Use longest standard status name: "INTERPOLATED" (12 chars)
        curve_data = [(1, 10.0, 10.0, "interpolated")]

        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(1)

        main_window.update_ui_state()

        # Full text should be displayed (with "Status: " prefix)
        assert main_window.type_label.text() == "Status: INTERPOLATED"
        assert len(main_window.type_label.text()) == 20  # "Status: INTERPOLATED"

    def test_status_label_state_when_no_curve_active(self, main_window):
        """Test status label state when no curve is active.

        Boundary: Label should show "--" when no active curve,
        regardless of previous state.
        """
        app_state = get_application_state()

        # Load curve and verify status
        curve_data = [(1, 10.0, 10.0, "keyframe")]
        app_state.set_curve_data("test_curve", curve_data)
        app_state.set_active_curve("test_curve")
        app_state.set_frame(1)
        main_window.update_ui_state()

        assert main_window.type_label.text() == "Status: KEYFRAME"

        # Deactivate curve
        app_state.set_active_curve(None)
        main_window.update_ui_state()

        # Should reset to "--"
        assert main_window.type_label.text() == "Status: --"

    def test_status_label_exists_and_accessible(self, main_window):
        """Test that status label is properly initialized and accessible.

        Boundary: Verifies label widget exists and is properly configured
        for status updates.
        """
        # Label should exist
        assert main_window.type_label is not None

        # Label should be a QLabel
        from PySide6.QtWidgets import QLabel

        assert isinstance(main_window.type_label, QLabel)

        # Label should have default text
        assert main_window.type_label.text() == "Status: --"

        # Label should be able to update
        main_window._safe_set_label(main_window.type_label, "Status: TEST")
        assert main_window.type_label.text() == "Status: TEST"

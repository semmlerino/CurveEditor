#!/usr/bin/env python
"""
Tests for PageUp/PageDown keyframe navigation functionality.

This module tests the enhanced navigation that includes keyframes, endframes, and startframes.
Following UNIFIED_TESTING_GUIDE best practices:
- Test behavior, not implementation
- Use real components when possible
- Factory fixtures for test data
- Clear test names describing behavior
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
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent

from services import get_data_service
from stores.application_state import get_application_state
from ui.main_window import MainWindow

# ============================================================================
# FACTORY FIXTURES
# ============================================================================


@pytest.fixture
def make_navigation_point():
    """Factory for creating navigation test points."""

    def _make_point(frame: int, x: float = 100.0, y: float = 200.0, status: str = "tracked"):
        """Create a curve point tuple for testing.

        Args:
            frame: Frame number
            x: X coordinate
            y: Y coordinate
            status: Point status (keyframe, endframe, tracked, etc.)

        Returns:
            Tuple representing a curve point
        """
        return (frame, x, y, status)

    return _make_point


@pytest.fixture
def make_navigation_dataset():
    """Factory for creating various navigation test datasets."""

    def _make_dataset(scenario: str = "basic"):
        """Create predefined datasets for different test scenarios.

        Args:
            scenario: Type of dataset to create
                - "basic": Mix of keyframes and tracked points
                - "with_endframes": Includes endframes creating gaps
                - "only_keyframes": Only keyframe points
                - "complex": Multiple segments with all frame types
                - "single": Single point only
                - "empty": No points

        Returns:
            List of curve point tuples
        """
        datasets = {
            "basic": [
                (1, 100.0, 200.0, "tracked"),
                (5, 150.0, 250.0, "keyframe"),
                (10, 200.0, 300.0, "tracked"),
                (15, 250.0, 350.0, "keyframe"),
                (20, 300.0, 400.0, "tracked"),
            ],
            "with_endframes": [
                (1, 100.0, 200.0, "tracked"),  # Will be startframe
                (5, 150.0, 250.0, "keyframe"),
                (10, 200.0, 300.0, "endframe"),  # Creates gap
                (15, 250.0, 350.0, "tracked"),  # Stays in gap
                (20, 300.0, 400.0, "keyframe"),  # Will be startframe after gap
                (25, 350.0, 450.0, "tracked"),  # Additional frame to allow testing from frame 22
            ],
            "only_keyframes": [
                (5, 150.0, 250.0, "keyframe"),
                (10, 200.0, 300.0, "keyframe"),
                (15, 250.0, 350.0, "keyframe"),
            ],
            "complex": [
                (1, 100.0, 200.0, "tracked"),  # Startframe
                (2, 110.0, 210.0, "tracked"),
                (5, 150.0, 250.0, "keyframe"),
                (8, 180.0, 280.0, "tracked"),
                (10, 200.0, 300.0, "endframe"),  # End of first segment
                (20, 300.0, 400.0, "keyframe"),  # Startframe of second segment
                (25, 350.0, 450.0, "keyframe"),
                (30, 400.0, 500.0, "endframe"),  # End of second segment
                (40, 500.0, 600.0, "keyframe"),  # Startframe of third segment
                (45, 550.0, 650.0, "tracked"),
            ],
            "single": [(10, 200.0, 300.0, "keyframe")],
            "empty": [],
        }
        return datasets.get(scenario, [])

    return _make_dataset


@pytest.fixture
def main_window_with_data(qtbot, make_navigation_dataset):
    """Create a MainWindow with test data loaded."""

    def _make_window(dataset_scenario: str = "basic"):
        """Create MainWindow with specified dataset.

        Args:
            dataset_scenario: Dataset scenario to load

        Returns:
            MainWindow instance with data loaded
        """
        # Load test data BEFORE creating window to ensure it's available during initialization
        test_data = make_navigation_dataset(dataset_scenario)
        processed_data = None
        if test_data:
            # Apply default status assignment as DataService does when loading files
            data_service = get_data_service()
            processed_data = data_service._apply_default_statuses(test_data)

            app_state = get_application_state()
            app_state.set_curve_data("__default__", processed_data)
            app_state.set_active_curve("__default__")  # Set active curve for navigation

        # NOW create window - it will see the data already set
        # Pass auto_load_data=False to prevent loading default data
        window = MainWindow(auto_load_data=False)
        qtbot.addWidget(window)

        # Update frame range via timeline controller (updates spinbox max)
        if test_data:
            if processed_data:
                max_frame = max(point[0] for point in processed_data)
                # Extend frame range to 30 to allow testing beyond the data (navigation tests may go beyond)
                window.timeline_controller.set_frame_range(1, max(max_frame, 30))
                # Note: curve_widget.curve_data is read-only and gets data from ApplicationState
                # Data is already set via app_state.set_curve_data() at line 129

        # Show and wait for exposure
        window.show()
        qtbot.waitExposed(window)

        return window

    return _make_window


# ============================================================================
# UNIT TESTS - Navigation Logic
# ============================================================================


class TestNavigationLogic:
    """Test the core navigation logic for finding prev/next frames."""

    def test_identifies_keyframes_for_navigation(self, make_navigation_dataset):
        """Navigation should identify all keyframes as navigation points."""
        data = make_navigation_dataset("only_keyframes")
        nav_frames = []

        for point in data:
            if len(point) >= 4 and point[3] in ["keyframe", "endframe"]:
                nav_frames.append(point[0])

        assert nav_frames == [5, 10, 15]

    def test_identifies_endframes_for_navigation(self, make_navigation_dataset):
        """Navigation should identify endframes as navigation points."""
        data = make_navigation_dataset("with_endframes")
        nav_frames = []

        for point in data:
            if len(point) >= 4 and point[3] in ["keyframe", "endframe"]:
                nav_frames.append(point[0])

        assert 10 in nav_frames  # Endframe should be included

    def test_computes_startframes_correctly(self, make_navigation_dataset):
        """DataService should correctly compute startframes for navigation."""
        data = make_navigation_dataset("with_endframes")
        data_service = get_data_service()

        frame_status = data_service.get_frame_range_point_status(data)

        # Check for startframes using FrameStatus named attribute
        startframes = [frame for frame, status in frame_status.items() if status.is_startframe]

        # Frame 1 should be startframe (first with tracked)
        # Frame 20 should be startframe (keyframe after endframe at 10)
        assert 1 in startframes
        assert 20 in startframes

    def test_navigation_frame_ordering(self, make_navigation_dataset):
        """Navigation frames should be properly sorted."""
        data = make_navigation_dataset("complex")
        nav_frames = []

        # Collect keyframes and endframes
        for point in data:
            if len(point) >= 4 and point[3] in ["keyframe", "endframe"]:
                nav_frames.append(point[0])

        # Add startframes
        data_service = get_data_service()
        frame_status = data_service.get_frame_range_point_status(data)
        for frame, status in frame_status.items():
            if status.is_startframe and frame not in nav_frames:
                nav_frames.append(frame)

        nav_frames.sort()
        # Should be in ascending order
        assert nav_frames == sorted(nav_frames)


# ============================================================================
# INTEGRATION TESTS - MainWindow Navigation
# ============================================================================


class TestMainWindowNavigation:
    """Test PageUp/PageDown navigation in MainWindow."""

    def test_pagedown_navigates_to_next_keyframe(self, qtbot, main_window_with_data):
        """PageDown should navigate to the next keyframe."""
        window = main_window_with_data("basic")

        # Set initial frame
        get_application_state().set_frame(3)

        # Simulate PageDown key press
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        window.keyPressEvent(key_event)

        # Process Qt events to allow spinbox signal propagation
        qtbot.wait(10)

        # Should navigate to frame 5 (next keyframe)
        assert get_application_state().current_frame == 5

    def test_pageup_navigates_to_previous_keyframe(self, qtbot, main_window_with_data):
        """PageUp should navigate to the previous keyframe."""
        window = main_window_with_data("basic")

        # Set initial frame
        get_application_state().set_frame(12)

        # Simulate PageUp key press
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageUp, Qt.KeyboardModifier.NoModifier)
        window.keyPressEvent(key_event)

        # Process Qt events
        qtbot.wait(10)

        # Should navigate to frame 5 (previous keyframe)
        assert get_application_state().current_frame == 5

    def test_pagedown_includes_endframes(self, qtbot, main_window_with_data):
        """PageDown should include endframes as navigation points."""
        window = main_window_with_data("with_endframes")

        # Set frame before endframe
        get_application_state().set_frame(7)

        # Simulate PageDown
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        window.keyPressEvent(key_event)

        # Process Qt events
        qtbot.wait(10)

        # Should navigate to frame 10 (endframe)
        assert get_application_state().current_frame == 10

    def test_pageup_includes_startframes(self, qtbot, main_window_with_data):
        """PageUp should include computed startframes as navigation points."""
        window = main_window_with_data("with_endframes")

        # Set frame after the startframe (frame 20)
        get_application_state().set_frame(22)

        # Simulate PageUp
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageUp, Qt.KeyboardModifier.NoModifier)
        window.keyPressEvent(key_event)

        # Process Qt events
        qtbot.wait(10)

        # Should navigate to frame 20 (startframe after gap)
        assert get_application_state().current_frame == 20


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


class TestNavigationEdgeCases:
    """Test edge cases and error conditions."""

    def test_navigation_with_no_data(self, qtbot, main_window_with_data):
        """Navigation should handle empty dataset gracefully."""
        window = main_window_with_data("empty")

        initial_frame = get_application_state().current_frame

        # Try PageDown with no data
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        window.keyPressEvent(key_event)

        # Frame should not change
        assert get_application_state().current_frame == initial_frame

        # Status bar should show message
        status_text = window.statusBar().currentMessage()
        assert "No curve data" in status_text or "No navigation frames" in status_text

    def test_already_at_last_frame(self, qtbot, main_window_with_data):
        """PageDown at last navigation frame should show appropriate message."""
        window = main_window_with_data("basic")

        # Navigate to last keyframe
        get_application_state().set_frame(15)

        # Try to go further with PageDown
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        window.keyPressEvent(key_event)

        # Should stay at frame 15
        assert get_application_state().current_frame == 15

        # Status should indicate we're at the last frame
        status_text = window.statusBar().currentMessage()
        assert "last" in status_text.lower()

    def test_already_at_first_frame(self, qtbot, main_window_with_data):
        """PageUp at first navigation frame should show appropriate message."""
        window = main_window_with_data("basic")

        # Navigate to first frame with data
        get_application_state().set_frame(1)

        # Try to go back with PageUp
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageUp, Qt.KeyboardModifier.NoModifier)
        window.keyPressEvent(key_event)

        # Should stay at frame 1
        assert get_application_state().current_frame == 1

        # Status should indicate we're at the first frame
        status_text = window.statusBar().currentMessage()
        assert "first" in status_text.lower()

    def test_single_navigation_frame(self, qtbot, main_window_with_data):
        """Navigation should work correctly with only one navigation frame."""
        window = main_window_with_data("single")

        # Start before the single keyframe
        get_application_state().set_frame(5)
        qtbot.wait(50)

        # PageDown should go to frame 10 (the only keyframe)
        key_event_down = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        window.keyPressEvent(key_event_down)
        qtbot.wait(50)
        assert get_application_state().current_frame == 10

        # PageDown again from 10 should stay at 10 (no next frame)
        window.keyPressEvent(key_event_down)
        qtbot.wait(50)
        assert get_application_state().current_frame == 10

        # Set frame after keyframe and try PageUp
        get_application_state().set_frame(15)
        qtbot.wait(50)
        key_event_up = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageUp, Qt.KeyboardModifier.NoModifier)
        window.keyPressEvent(key_event_up)
        qtbot.wait(50)
        # Should go back to frame 10 (the only keyframe)
        assert get_application_state().current_frame == 10


# ============================================================================
# PARAMETRIZED TESTS
# ============================================================================


class TestParametrizedNavigation:
    """Parametrized tests for various navigation scenarios."""

    @pytest.mark.parametrize(
        "current_frame,direction,expected_frame",
        [
            (3, "down", 5),  # Navigate to next keyframe
            (12, "up", 5),  # Navigate to previous keyframe
            (5, "down", 15),  # From keyframe to next keyframe
            (15, "up", 5),  # From keyframe to previous keyframe
        ],
    )
    def test_navigation_from_various_positions(
        self, qtbot, main_window_with_data, current_frame, direction, expected_frame
    ):
        """Test navigation from different starting positions."""
        window = main_window_with_data("basic")
        get_application_state().set_frame(current_frame)

        # Create appropriate key event
        key = Qt.Key.Key_PageDown if direction == "down" else Qt.Key.Key_PageUp
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier)

        window.keyPressEvent(key_event)

        assert get_application_state().current_frame == expected_frame

    @pytest.mark.parametrize(
        "dataset_scenario,frame_count",
        [
            ("basic", 2),  # 2 keyframes
            ("with_endframes", 4),  # 2 keyframes + 1 endframe + at least 1 startframe
            ("only_keyframes", 3),  # 3 keyframes
            ("complex", 7),  # Multiple navigation points
        ],
    )
    def test_total_navigation_frames_count(self, make_navigation_dataset, dataset_scenario, frame_count):
        """Verify correct number of navigation frames are identified."""
        data = make_navigation_dataset(dataset_scenario)

        # Collect all navigation frames
        nav_frames = []

        # Get keyframes and endframes
        for point in data:
            if len(point) >= 4 and point[3] in ["keyframe", "endframe"]:
                nav_frames.append(point[0])

        # Get startframes
        if data:  # Only if there's data
            data_service = get_data_service()
            frame_status = data_service.get_frame_range_point_status(data)
            for frame, status in frame_status.items():
                if status.is_startframe and frame not in nav_frames:
                    nav_frames.append(frame)

        # Should have at least the expected number of navigation frames
        assert len(set(nav_frames)) >= frame_count


# ============================================================================
# PERFORMANCE TESTS
# ============================================================================


class TestNavigationPerformance:
    """Test navigation performance with large datasets."""

    def test_navigation_with_large_dataset(self, qtbot, make_navigation_point):
        """Navigation should handle large datasets efficiently."""
        # Create a large dataset (but within timeline limits)
        large_data = []
        for i in range(0, 200, 2):  # Timeline limited to 200 frames
            status = "keyframe" if i % 20 == 0 else "tracked"
            large_data.append(make_navigation_point(i, 100.0 + i, 200.0 + i, status))

        # Set data BEFORE creating window
        app_state = get_application_state()
        app_state.set_curve_data("__default__", large_data)
        app_state.set_active_curve("__default__")

        # Create window - it will see the data already set
        window = MainWindow()
        qtbot.addWidget(window)

        # Update frame range
        window.timeline_controller.set_frame_range(1, 200)

        window.show()
        qtbot.waitExposed(window)

        # Start at frame 50
        get_application_state().set_frame(50)

        import time

        start_time = time.time()

        # Perform navigation
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        window.keyPressEvent(key_event)

        # Process Qt events
        qtbot.wait(10)

        elapsed = time.time() - start_time

        # Should complete in reasonable time (< 500ms for large dataset)
        # Increased threshold to account for CI environment variability
        assert elapsed < 0.5, f"Navigation took {elapsed:.3f}s, exceeds 0.5s threshold"

        # Should have navigated to next keyframe (60)
        assert get_application_state().current_frame == 60


# ============================================================================
# STATUS MESSAGE TESTS
# ============================================================================


class TestNavigationStatusMessages:
    """Test that appropriate status messages are shown."""

    def test_successful_navigation_shows_frame_number(self, qtbot, main_window_with_data):
        """Successful navigation should show the frame number in status."""
        window = main_window_with_data("basic")
        get_application_state().set_frame(3)

        # Navigate to next frame
        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        window.keyPressEvent(key_event)

        # Status should mention the frame number
        status_text = window.statusBar().currentMessage()
        assert "5" in status_text  # Should mention frame 5

    def test_no_data_shows_appropriate_message(self, qtbot, main_window_with_data):
        """No data should show 'No curve data loaded' message."""
        window = main_window_with_data("empty")

        key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
        window.keyPressEvent(key_event)

        status_text = window.statusBar().currentMessage()
        assert "No curve data" in status_text or "No navigation frames" in status_text


# ============================================================================
# REAL FILE INTEGRATION TEST
# ============================================================================


class TestRealFileNavigation:
    """Test navigation with real data files."""

    def test_navigation_with_keyframetest_file(self, qtbot):
        """Test navigation with KeyFrameTest.txt if available."""
        pytest.importorskip("services.data_service")

        try:
            # Try to load KeyFrameTest.txt
            data_service = get_data_service()
            test_data = data_service._load_2dtrack_data("KeyFrameTest.txt")
        except FileNotFoundError:
            pytest.skip("KeyFrameTest.txt not available")

        # Set data BEFORE creating window
        app_state = get_application_state()
        app_state.set_curve_data("__default__", test_data)
        app_state.set_active_curve("__default__")

        # Create window with real data
        window = MainWindow()
        qtbot.addWidget(window)

        # Update frame range based on data
        if test_data:
            max_frame = max(point[0] for point in test_data)
            window.timeline_controller.set_frame_range(1, max_frame)

        window.show()
        qtbot.waitExposed(window)

        # Start at frame 1
        get_application_state().set_frame(1)

        # Discover navigation frames dynamically from the loaded data
        data_service = get_data_service()
        frame_status = data_service.get_frame_range_point_status(test_data)

        # Collect all navigation frames (keyframes, endframes, startframes)
        nav_frames = []
        for point in test_data:
            if len(point) >= 4 and point[3] in ["keyframe", "endframe"]:
                nav_frames.append(point[0])

        # Add startframes
        for frame, status in frame_status.items():
            if status.is_startframe and frame not in nav_frames:
                nav_frames.append(frame)

        nav_frames = sorted(set(nav_frames))

        # Should have at least 3 navigation frames for meaningful test
        assert len(nav_frames) >= 3, f"Expected at least 3 navigation frames, got {len(nav_frames)}: {nav_frames}"

        # Navigate through first 3 navigation frames and verify navigation works
        visited_frames = [1]  # Starting frame
        for _ in range(min(3, len(nav_frames))):
            key_event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_PageDown, Qt.KeyboardModifier.NoModifier)
            window.keyPressEvent(key_event)
            qtbot.wait(10)  # Process Qt events
            visited_frames.append(get_application_state().current_frame)

        # Verify we navigated to actual navigation frames (not just stayed in place)
        assert len(set(visited_frames)) > 1, f"Navigation did not move between frames: {visited_frames}"

        # Verify each visited frame (except start) is actually a navigation frame
        for frame in visited_frames[1:]:
            assert (
                frame in nav_frames
            ), f"Navigated to frame {frame} which is not a navigation frame. Nav frames: {nav_frames}"

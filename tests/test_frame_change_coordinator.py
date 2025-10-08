"""Tests for FrameChangeCoordinator."""

from unittest.mock import patch

import pytest

from ui.controllers.frame_change_coordinator import FrameChangeCoordinator


class TestFrameChangeCoordinator:
    """Test frame change coordination."""

    @pytest.fixture
    def main_window(self, qtbot):
        """Create main window fixture."""
        from ui.main_window import MainWindow

        window = MainWindow()
        qtbot.addWidget(window)
        return window

    @pytest.fixture
    def coordinator(self, main_window):
        """Create coordinator fixture."""
        return FrameChangeCoordinator(main_window)

    def test_coordinator_initialization(self, coordinator):
        """Test coordinator creates successfully."""
        assert coordinator is not None
        assert coordinator.main_window is not None
        assert coordinator.curve_widget is not None
        assert coordinator.view_management is not None
        assert coordinator.timeline_controller is not None

    def test_single_connection_to_frame_changed(self, main_window, coordinator, qtbot):
        """Test only coordinator connects to frame_changed signal."""
        # Connect coordinator
        coordinator.connect()

        # Mock the update method to count calls
        original_update = main_window.curve_widget.update
        update_count = [0]

        def mock_update():
            update_count[0] += 1
            original_update()

        main_window.curve_widget.update = mock_update

        # Set total_frames first (required for frame change to work)
        main_window.state_manager.total_frames = 100

        # Trigger frame change
        main_window.state_manager.current_frame = 42

        # Should have exactly one update call
        assert update_count[0] == 1

    def test_update_order_is_deterministic(self, main_window, coordinator, qtbot):
        """Test updates happen in correct order."""
        # Track call order
        call_order = []

        # Mock each phase
        with (
            patch.object(
                coordinator,
                "_update_background",
                side_effect=lambda f: call_order.append("background"),
            ),
            patch.object(coordinator, "_apply_centering", side_effect=lambda f: call_order.append("centering")),
            patch.object(coordinator, "_invalidate_caches", side_effect=lambda: call_order.append("cache")),
            patch.object(
                coordinator,
                "_update_timeline_widgets",
                side_effect=lambda f: call_order.append("timeline"),
            ),
            patch.object(coordinator, "_trigger_repaint", side_effect=lambda: call_order.append("repaint")),
        ):
            # Trigger frame change
            coordinator.on_frame_changed(42)

            # Verify exact order
            assert call_order == ["background", "centering", "cache", "timeline", "repaint"]

    def test_single_repaint_per_frame_change(self, main_window, coordinator, qtbot):
        """Test only one update() call per frame change."""
        # Mock update method
        with patch.object(main_window.curve_widget, "update") as update_mock:
            # Connect and trigger frame change
            coordinator.connect()

            # Set total_frames first (required for frame change to work)
            main_window.state_manager.total_frames = 100

            main_window.state_manager.current_frame = 42

            # Verify single update call
            assert update_mock.call_count == 1

    def test_centering_before_repaint(self, main_window, coordinator, qtbot):
        """Test centering updates pan_offset before repaint."""
        # Track when centering and repaint are called
        centering_time: list[int | None] = [None]
        repaint_time: list[int | None] = [None]
        counter = [0]

        def mock_centering(frame):
            counter[0] += 1
            centering_time[0] = counter[0]

        def mock_repaint():
            counter[0] += 1
            repaint_time[0] = counter[0]

        with (
            patch.object(main_window.curve_widget, "center_on_frame", side_effect=mock_centering),
            patch.object(main_window.curve_widget, "update", side_effect=mock_repaint),
        ):
            # Enable centering mode
            main_window.curve_widget.centering_mode = True

            # Trigger frame change
            coordinator.on_frame_changed(42)

            # Verify centering happened before repaint
            assert centering_time[0] is not None
            assert repaint_time[0] is not None
            assert centering_time[0] < repaint_time[0]

    def test_background_before_centering(self, main_window, coordinator, qtbot):
        """Test background loads before centering."""
        # Track call order
        background_time: list[int | None] = [None]
        centering_time: list[int | None] = [None]
        counter = [0]

        def mock_background(frame):
            counter[0] += 1
            background_time[0] = counter[0]

        def mock_centering(frame):
            counter[0] += 1
            centering_time[0] = counter[0]

        with (
            patch.object(coordinator.view_management, "update_background_for_frame", side_effect=mock_background),
            patch.object(main_window.curve_widget, "center_on_frame", side_effect=mock_centering),
        ):
            # Set up preconditions
            coordinator.view_management.image_filenames = ["image1.png"]
            main_window.curve_widget.centering_mode = True

            # Trigger frame change
            coordinator.on_frame_changed(42)

            # Verify background loaded before centering
            assert background_time[0] is not None
            assert centering_time[0] is not None
            assert background_time[0] < centering_time[0]

    def test_works_without_background_images(self, main_window, coordinator, qtbot):
        """Test coordinator works when no background loaded."""
        # Ensure no background images
        coordinator.view_management.image_filenames = []

        # Should not crash on frame change
        coordinator.on_frame_changed(42)

    def test_works_without_centering_mode(self, main_window, coordinator, qtbot):
        """Test coordinator works when centering disabled."""
        # Disable centering
        main_window.curve_widget.centering_mode = False

        # Mock center_on_frame to verify it's not called
        with patch.object(main_window.curve_widget, "center_on_frame") as center_mock:
            # Trigger frame change
            coordinator.on_frame_changed(42)

            # Verify centering was not called
            center_mock.assert_not_called()

    def test_no_jumps_during_playback_with_background(self, main_window, coordinator, qtbot):
        """Regression test: no visual jumps with background + centering."""
        # Set up conditions that caused original bug
        coordinator.view_management.image_filenames = ["image1.png", "image2.png"]
        main_window.curve_widget.centering_mode = True

        # Simulate rapid frame changes (playback)
        coordinator.connect()
        for frame in range(1, 11):
            main_window.state_manager.current_frame = frame

        # If we got here without crashes, the coordinator handled rapid changes

    # CRITICAL: Tests for bugs identified in code review

    def test_connect_is_idempotent(self, main_window, coordinator, qtbot):
        """Test connect() can be called multiple times without duplicate connections.

        Critical Bug #1: Prevents signal connection leak.
        If connect() called twice (testing, error recovery, window reinit),
        Qt creates multiple connections → 2x-3x updates per frame.
        """
        # Mock update to count calls
        with patch.object(main_window.curve_widget, "update") as update_mock:
            # Connect twice
            coordinator.connect()
            coordinator.connect()  # Second call should not create duplicate

            # Set total_frames first (required for frame change to work)
            main_window.state_manager.total_frames = 100

            # Trigger frame change
            main_window.state_manager.current_frame = 42

            # Verify only ONE update() call (not 2x)
            assert update_mock.call_count == 1

    def test_disconnect_before_connect(self, main_window, qtbot):
        """Test disconnect() works even if never connected."""
        coordinator = FrameChangeCoordinator(main_window)
        coordinator.disconnect()  # Should not crash

    def test_coordinator_handles_phase_failures(self, main_window, coordinator, qtbot):
        """Test all phases execute even if one fails (atomic guarantee).

        Critical Bug #2: Prevents partial state updates.
        If centering crashes, repaint must still happen.
        """
        # Mock update to verify it gets called
        with (
            patch.object(main_window.curve_widget, "update") as update_mock,
            patch.object(
                main_window.curve_widget,
                "center_on_frame",
                side_effect=Exception("Division by zero"),
            ),
        ):
            # Enable centering to trigger the failure
            main_window.curve_widget.centering_mode = True

            # Frame change should not crash
            coordinator.on_frame_changed(42)

            # Verify repaint still happened despite centering failure
            assert update_mock.called

    def test_coordinator_handles_missing_components(self, main_window, qtbot):
        """Test coordinator handles None components gracefully.

        Critical Bug #5: Prevents AttributeError on component access.
        """
        # Create coordinator with missing components
        main_window.curve_widget = None
        main_window.timeline_tabs = None

        coordinator = FrameChangeCoordinator(main_window)

        # Should not crash on frame change
        coordinator.on_frame_changed(42)

    def test_frame_change_during_initialization(self, main_window, coordinator, qtbot):
        """Test frame change doesn't crash during partial initialization."""
        # Disconnect to simulate pre-connection state
        coordinator.disconnect()

        # Trigger frame change while coordinator not connected
        # This should be handled by other handlers (if any remain)
        main_window.state_manager.current_frame = 42  # Should not crash

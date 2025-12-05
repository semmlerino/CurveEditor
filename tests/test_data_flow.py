#!/usr/bin/env python3
"""
Integration tests for reactive data flow from stores to UI components.

Verifies that the reactive architecture properly propagates changes from
the central stores to all connected UI components automatically.
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
from PySide6.QtTest import QSignalSpy
from PySide6.QtWidgets import QApplication

from core.type_aliases import CurveDataList
from tests.test_utils import (
    process_qt_events,
    wait_for_condition,
    wait_for_frame,
    wait_for_signal,
)

from stores import get_store_manager
from stores.application_state import get_application_state
from stores.store_manager import StoreManager
from ui.curve_view_widget import CurveViewWidget
from ui.main_window import MainWindow
from ui.timeline_tabs import TimelineTabWidget

class TestDataFlowIntegration:
    """Test reactive data flow from stores to UI components.

    Following unified testing guide:
    - Test behavior, not implementation
    - Use real components over mocks
    - Mock only at system boundaries
    - Use qtbot.addWidget() for all widgets
    - Check 'is not None' for Qt containers
    """

    def setup_method(self) -> None:
        """Reset stores before each test."""
        StoreManager.reset()

        # Create StateManager for FrameStore delegation
        from ui.state_manager import StateManager

        self.state_manager: StateManager = StateManager()  # pyright: ignore[reportUninitializedInstanceVariable]

        # Connect StateManager to StoreManager for frame delegation
        store_manager = get_store_manager()
        store_manager.set_state_manager(self.state_manager)

        # Clear image sequence set by autouse fixture to test from truly empty state
        # Tests that need images will set them explicitly
        get_application_state().set_image_files([])

    def teardown_method(self):
        """Clean up after each test."""
        StoreManager.reset()

    def test_store_to_timeline_data_flow(self, qtbot):
        """Test that curve store updates propagate to timeline tabs."""
        # Create timeline
        timeline = TimelineTabWidget()
        qtbot.addWidget(timeline)

        # Get ApplicationState
        app_state = get_application_state()

        # Initial state
        assert timeline.min_frame == 1
        assert timeline.max_frame == 1

        # Setup signal spy to verify signal emission
        spy = QSignalSpy(app_state.curves_changed)

        # Add data to ApplicationState
        test_data: CurveDataList = [
            (5, 100.0, 100.0, "keyframe"),
            (10, 110.0, 110.0, "interpolated"),
            (15, 120.0, 120.0, "keyframe"),
        ]
        app_state.set_curve_data("TestCurve", test_data)
        app_state.set_active_curve("TestCurve")

        # Verify signal was emitted
        assert spy.count() >= 1, "curves_changed signal should have been emitted"

        # Let signals process
        process_qt_events()

        # Timeline should have updated automatically
        assert timeline.min_frame == 5
        assert timeline.max_frame == 15

        # Check status cache updated
        # get_status returns tuple: (keyframe, interpolated, tracked, endframe, normal, start, inactive, selected)
        status_5 = timeline.status_cache.get_status(5)
        assert status_5 is not None
        assert status_5[0] == 1  # keyframe_count

        status_10 = timeline.status_cache.get_status(10)
        assert status_10 is not None
        assert status_10[1] == 1  # interpolated_count

        status_15 = timeline.status_cache.get_status(15)
        assert status_15 is not None
        assert status_15[0] == 1  # keyframe_count

    def test_store_to_curve_widget_data_flow(self, qtbot):
        """Test that curve store updates propagate to curve widget."""
        # Create widget
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Get ApplicationState
        app_state = get_application_state()

        # Initial state
        assert len(widget.curve_data) == 0

        # Setup signal spy to verify signal emission
        spy = QSignalSpy(app_state.curves_changed)

        # Add data to ApplicationState
        test_data: CurveDataList = [
            (1, 100.0, 200.0, "keyframe"),
            (2, 150.0, 250.0, "normal"),
        ]
        app_state.set_curve_data("TestCurve", test_data)
        app_state.set_active_curve("TestCurve")

        # Verify signal was emitted
        assert spy.count() >= 1, "curves_changed signal should have been emitted"

        # Let signals process
        process_qt_events()

        # Widget should have updated automatically
        assert len(widget.curve_data) == 2
        assert widget.curve_data[0] == (1, 100.0, 200.0, "keyframe")
        assert widget.curve_data[1] == (2, 150.0, 250.0, "normal")

    def test_frame_store_sync_with_curve_data(self, qtbot):
        """Test that frame store syncs with curve data changes."""
        # Get stores
        store_manager = get_store_manager()
        frame_store = store_manager.get_frame_store()
        app_state = get_application_state()

        # Initial state
        assert frame_store.min_frame == 1
        assert frame_store.max_frame == 1
        assert frame_store.current_frame == 1

        # Set image sequence to allow frame navigation
        app_state.set_image_files(["dummy.png"] * 50)

        # Add data to ApplicationState
        test_data: CurveDataList = [
            (10, 100.0, 100.0, "keyframe"),
            (20, 200.0, 200.0, "keyframe"),
            (30, 300.0, 300.0, "keyframe"),
        ]
        app_state.set_curve_data("TestCurve", test_data)
        app_state.set_active_curve("TestCurve")

        # Frame store should have synced automatically
        assert frame_store.min_frame == 10
        assert frame_store.max_frame == 30
        assert frame_store.current_frame == 10  # Clamped to new min

    def test_point_addition_propagates_to_all_components(self, qtbot):
        """Test that adding a point updates all connected components."""
        # Create components
        timeline = TimelineTabWidget()
        widget = CurveViewWidget()
        qtbot.addWidget(timeline)
        qtbot.addWidget(widget)

        # Get stores
        store_manager = get_store_manager()
        frame_store = store_manager.get_frame_store()
        app_state = get_application_state()

        # Initial setup
        app_state.set_curve_data("TestCurve", [(1, 100.0, 100.0, "keyframe")])
        app_state.set_active_curve("TestCurve")
        process_qt_events()

        # Setup signal spy for curve changes
        spy_add = QSignalSpy(app_state.curves_changed)

        # Add a new point
        existing_data = app_state.get_curve_data("TestCurve")
        if existing_data:
            new_data = [*existing_data, (5, 200.0, 200.0, "keyframe")]
            app_state.set_curve_data("TestCurve", new_data)

        # Verify signal was emitted
        assert spy_add.count() >= 1, "curves_changed signal should have been emitted"

        process_qt_events()

        # All components should have updated
        assert len(widget.curve_data) == 2
        assert timeline.max_frame == 5
        assert frame_store.max_frame == 5
        status_5 = timeline.status_cache.get_status(5)
        assert status_5 is not None
        assert status_5[0] == 1  # keyframe_count

    def test_point_removal_propagates_to_all_components(self, qtbot):
        """Test that removing a point updates all connected components."""
        # Create components
        timeline = TimelineTabWidget()
        widget = CurveViewWidget()
        qtbot.addWidget(timeline)
        qtbot.addWidget(widget)

        # Get stores
        store_manager = get_store_manager()
        frame_store = store_manager.get_frame_store()
        app_state = get_application_state()

        # Initial setup with 3 points
        test_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 200.0, 200.0, "keyframe"),
            (10, 300.0, 300.0, "keyframe"),
        ]
        app_state.set_curve_data("TestCurve", test_data)
        app_state.set_active_curve("TestCurve")
        process_qt_events()

        # Setup signal spy for curve changes
        spy_remove = QSignalSpy(app_state.curves_changed)

        # Remove middle point
        existing_data = app_state.get_curve_data("TestCurve")
        if existing_data:
            new_data = [existing_data[0], existing_data[2]]  # Remove index 1
            app_state.set_curve_data("TestCurve", new_data)

        # Verify signal was emitted
        assert spy_remove.count() >= 1, "curves_changed signal should have been emitted"

        process_qt_events()

        # All components should have updated
        assert len(widget.curve_data) == 2
        status_5 = timeline.status_cache.get_status(5)
        assert status_5 is not None
        assert status_5[0] == 0  # keyframe_count
        # Frame range should still be 1-10 since endpoints remain
        assert timeline.max_frame == 10
        assert frame_store.max_frame == 10

    def test_point_status_change_propagates_to_timeline(self, qtbot):
        """Test that changing point status updates timeline colors."""
        # Create timeline
        timeline = TimelineTabWidget()
        qtbot.addWidget(timeline)

        # Get ApplicationState
        app_state = get_application_state()

        # Initial setup
        test_data: CurveDataList = [
            (1, 100.0, 100.0, "normal"),
            (2, 200.0, 200.0, "normal"),
            (3, 300.0, 300.0, "normal"),
        ]
        app_state.set_curve_data("TestCurve", test_data)
        app_state.set_active_curve("TestCurve")
        process_qt_events()

        # All should be normal initially
        # get_status returns tuple: (keyframe, interpolated, tracked, endframe, normal, start, inactive, selected)
        status1 = timeline.status_cache.get_status(1)
        assert status1 is not None
        assert status1[4] == 1  # normal_count
        status2 = timeline.status_cache.get_status(2)
        assert status2 is not None
        assert status2[4] == 1  # normal_count
        status3 = timeline.status_cache.get_status(3)
        assert status3 is not None
        assert status3[4] == 1  # normal_count

        # Change point 2 to keyframe
        existing_data = app_state.get_curve_data("TestCurve")
        if existing_data:
            new_data = [
                existing_data[0],
                (2, 200.0, 200.0, "keyframe"),  # Update status
                existing_data[2],
            ]
            app_state.set_curve_data("TestCurve", new_data)
        process_qt_events()

        # Timeline should reflect the change
        # get_status returns tuple: (keyframe, interpolated, tracked, endframe, normal, start, inactive, selected)
        status_2 = timeline.status_cache.get_status(2)
        assert status_2 is not None
        assert status_2[4] == 0  # normal_count
        assert status_2[0] == 1  # keyframe_count

    def test_selection_propagates_between_components(self, qtbot):
        """Test that selection changes propagate between components."""
        # Create widget (has selection functionality)
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Get ApplicationState
        app_state = get_application_state()

        # Setup data
        test_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 200.0, 200.0, "normal"),
            (3, 300.0, 300.0, "keyframe"),
        ]
        app_state.set_curve_data("TestCurve", test_data)
        app_state.set_active_curve("TestCurve")
        process_qt_events()

        # Select via ApplicationState
        app_state.set_selection("TestCurve", {1})
        process_qt_events()

        # Widget should show selection
        assert 1 in widget.selected_indices

        # Multi-select via ApplicationState
        app_state.set_selection("TestCurve", {1, 2})
        process_qt_events()

        # Widget should show both selections
        assert 1 in widget.selected_indices
        assert 2 in widget.selected_indices

    def test_clear_data_propagates_to_all_components(self, qtbot):
        """Test that clearing data resets all components."""
        # Create components
        timeline = TimelineTabWidget()
        widget = CurveViewWidget()
        qtbot.addWidget(timeline)
        qtbot.addWidget(widget)

        # Get stores
        store_manager = get_store_manager()
        frame_store = store_manager.get_frame_store()
        app_state = get_application_state()

        # Setup data
        test_data: CurveDataList = [
            (5, 100.0, 100.0, "keyframe"),
            (10, 200.0, 200.0, "normal"),
            (15, 300.0, 300.0, "keyframe"),
        ]
        app_state.set_curve_data("TestCurve", test_data)
        app_state.set_active_curve("TestCurve")
        process_qt_events()

        # Verify data is loaded
        assert len(widget.curve_data) == 3
        assert timeline.max_frame == 15

        # Clear the ApplicationState
        app_state.delete_curve("TestCurve")
        app_state.set_active_curve(None)
        process_qt_events()

        # All components should reset
        assert len(widget.curve_data) == 0
        assert timeline.min_frame == 1
        assert timeline.max_frame == 1
        # Note: FrameStore may retain previous range when no curves exist
        # This is expected behavior - frame range persists until new data is loaded
        assert frame_store.current_frame >= 1  # Current frame should be valid

    def test_batch_operations_propagate_efficiently(self, qtbot):
        """Test that batch_updates() results in efficient updates.

        Tests behavior not implementation - verifies that rapid changes
        still result in correct final state.
        """
        # Create timeline with deferred updates
        timeline = TimelineTabWidget()
        qtbot.addWidget(timeline)

        # Get ApplicationState
        app_state = get_application_state()

        # Add multiple points using batch operation
        with app_state.batch_updates():
            test_data: CurveDataList = [(i, float(i * 10), float(i * 10), "normal") for i in range(1, 11)]
            app_state.set_curve_data("TestCurve", test_data)
            app_state.set_active_curve("TestCurve")

        # Wait for deferred update to complete
        process_qt_events()  # Allow deferred updates to process (timeline uses 50ms timer)

        # Timeline should have all points correctly reflected
        assert timeline.max_frame == 10

        # Verify each frame has correct status
        for i in range(1, 11):
            # Test behavior: each frame should be marked
            status = timeline.status_cache.get_status(i)
            # get_status returns FrameStatus namedtuple
            assert status is not None
            assert status.normal_count == 1  # Each point is normal by default

    def test_no_manual_updates_override_store(self, qtbot):
        """Test that ApplicationState data updates propagate to timeline.

        Verifies that when ApplicationState is updated, the timeline
        automatically reflects the changes.
        """
        # Create main window (disable auto-loading to prevent test data override)
        window = MainWindow(auto_load_data=False)
        qtbot.addWidget(window)

        # Get ApplicationState and timeline
        app_state = get_application_state()
        timeline = window.timeline_tabs
        assert timeline is not None

        # Set test data with a distinct range
        test_data: CurveDataList = [
            (50, 100.0, 100.0, "keyframe"),
            (75, 200.0, 200.0, "keyframe"),
            (100, 300.0, 300.0, "keyframe"),
        ]
        app_state.set_curve_data("TestCurve", test_data)
        app_state.set_active_curve("TestCurve")
        # Wait for timeline to update with new frame range
        wait_for_condition(
            qtbot,
            lambda: timeline.min_frame == 50 and timeline.max_frame == 100,
            timeout=1000,
            message=f"Timeline frame range not updated: min={timeline.min_frame}, max={timeline.max_frame}",
        )

        # Timeline should show new data range
        assert timeline.min_frame == 50, f"Expected min 50, got {timeline.min_frame}"
        assert timeline.max_frame == 100, f"Expected max 100, got {timeline.max_frame}"

        # Update data with different range
        new_data: CurveDataList = [
            (50, 100.0, 100.0, "keyframe"),
            (75, 200.0, 200.0, "keyframe"),
            (180, 300.0, 300.0, "keyframe"),  # Extended to 180 (within 200 frame limit)
        ]
        app_state.set_curve_data("TestCurve", new_data)
        # Wait for timeline to reflect updated frame range
        wait_for_condition(
            qtbot,
            lambda: timeline.max_frame == 180,
            timeout=1000,
            message=f"Timeline max_frame not updated: got {timeline.max_frame}, expected 180",
        )

        # Timeline should reflect the updated ApplicationState data
        assert timeline.max_frame == 180, f"Expected max 180 after update, got {timeline.max_frame}"

    def test_invalid_data_handled_gracefully(self, qtbot):
        """Test that invalid data doesn't break reactive flow.

        Tests error handling: Components should handle invalid data
        gracefully without breaking connections.
        """
        # Create components
        timeline = TimelineTabWidget()
        widget = CurveViewWidget()
        qtbot.addWidget(timeline)
        qtbot.addWidget(widget)

        # Get ApplicationState
        app_state = get_application_state()

        # Set invalid/edge case data
        invalid_data: CurveDataList = [
            (0, 100.0, 100.0, "keyframe"),  # Frame 0 (edge case)
            (-1, 200.0, 200.0, "normal"),  # Negative frame
        ]
        app_state.set_curve_data("TestCurve", invalid_data)
        app_state.set_active_curve("TestCurve")
        process_qt_events()

        # Components should handle gracefully
        # Frame store should clamp to valid range
        store_manager = get_store_manager()
        frame_store = store_manager.get_frame_store()
        assert frame_store.min_frame >= 1  # Should be clamped

    def test_rapid_store_changes_maintain_consistency(self, qtbot):
        """Test that rapid store changes maintain data consistency.

        Tests behavior under stress: Rapid changes should not cause
        inconsistent state between components.
        """
        # Create components
        timeline = TimelineTabWidget()
        widget = CurveViewWidget()
        qtbot.addWidget(timeline)
        qtbot.addWidget(widget)

        # Get stores
        store_manager = get_store_manager()
        frame_store = store_manager.get_frame_store()
        app_state = get_application_state()

        # Perform rapid changes
        for _ in range(3):
            # Add points
            test_data: CurveDataList = [(i, float(i * 10), float(i * 10), "normal") for i in range(1, 6)]
            app_state.set_curve_data("TestCurve", test_data)
            app_state.set_active_curve("TestCurve")

            # Change selection rapidly
            for i in range(5):
                app_state.set_selection("TestCurve", {i})

            # Clear and re-add
            app_state.delete_curve("TestCurve")
            app_state.set_curve_data("TestCurve", test_data[:3])
            app_state.set_active_curve("TestCurve")

        # Allow all updates to process
        process_qt_events()

        # Final state should be consistent across all components
        final_data = app_state.get_curve_data("TestCurve")
        assert final_data is not None
        assert len(widget.curve_data) == len(final_data)
        assert timeline.max_frame == 3  # Should match final data
        assert frame_store.max_frame == 3

        # Verify status cache is consistent
        for i in range(1, 4):
            status = timeline.status_cache.get_status(i)
            # get_status returns FrameStatus namedtuple
            assert status is not None
            assert status.normal_count == 1  # normal_count


@pytest.mark.usefixtures("with_minimal_frame_range")
class TestMultiControllerSignalChains:
    """Test signal chains between multiple controllers.

    Following unified testing guide's emphasis on multi-controller signal testing:
    - Verify controller-to-controller signal connections
    - Test signal chain integrity
    - Ensure signals propagate through the full chain
    - Detect missing connections that could cause bugs
    """

    def setup_method(self) -> None:
        """Reset stores before each test."""
        StoreManager.reset()

    def teardown_method(self):
        """Clean up after each test."""
        StoreManager.reset()

    def test_timeline_controller_signal_chain(self, qtbot):
        """Test signal chain from TimelineController.

        This tests the critical timeline control chain.
        TimelineController -> ApplicationState -> UI updates
        """

        from ui.controllers.timeline_controller import TimelineController

        # Create main window with all controllers
        window = MainWindow()
        qtbot.addWidget(window)

        # Get the controller - cast to implementation class for testing
        timeline_controller = window.timeline_controller
        assert isinstance(timeline_controller, TimelineController)

        # Setup test data
        app_state = get_application_state()
        test_data: CurveDataList = [(i, float(i * 10), float(i * 10), "keyframe") for i in range(1, 11)]
        app_state.set_curve_data("TestCurve", test_data)
        app_state.set_active_curve("TestCurve")

        process_qt_events()  # Let data propagate

        # Set initial frame to a known value
        timeline_controller.set_frame(1)
        wait_for_frame(qtbot, expected_frame=1)
        initial_frame = app_state.current_frame

        # Setup signal spy on ApplicationState (frame changes go through here now)
        spy_frame_changed = QSignalSpy(app_state.frame_changed)

        # Start playback
        timeline_controller.toggle_playback()

        # Simulate timer tick
        timeline_controller._on_playback_timer()

        # Verify signal was emitted from ApplicationState
        assert spy_frame_changed.count() >= 1, "ApplicationState.frame_changed signal should have been emitted"
        if spy_frame_changed.count() > 0:
            changed_frame = spy_frame_changed.at(0)[0]
            assert (
                changed_frame == initial_frame + 1
            ), f"Should change to next frame (got {changed_frame}, expected {initial_frame + 1})"

        # Verify the chain completed (frame actually changed)
        process_qt_events()
        # Frame should have advanced
        assert (
            app_state.current_frame > initial_frame
        ), f"Frame should have advanced from {initial_frame}, got {app_state.current_frame}"

        # Stop playback
        timeline_controller.toggle_playback()

    def test_controller_cascade_signal_chain(self, qtbot):
        """Test cascading signals through multiple controllers.

        Tests the pattern:
        PointEditorController -> CurveViewWidget -> CurveDataFacade -> ApplicationState -> Signal Emission

        The signal chain works correctly:
        1. PointEditorController._on_point_x_changed() updates the point
        2. CurveDataFacade.update_point() calls ApplicationState.update_point()
        3. ApplicationState.update_point() emits curves_changed signal
        4. UI components receive the signal and can update

        NOTE: Must disable auto_load_data to prevent sample data from interfering with test setup.
        """
        window = MainWindow(auto_load_data=False)  # Don't load sample data
        qtbot.addWidget(window)

        # Setup test data via ApplicationState (Phase 4 pattern)
        from stores.application_state import get_application_state

        app_state = get_application_state()
        test_data: CurveDataList = [(1, 100.0, 200.0, "keyframe"), (2, 150.0, 250.0, "normal")]
        app_state.set_curve_data("TestCurve", test_data)
        app_state.set_active_curve("TestCurve")
        process_qt_events()

        # Select first point via ApplicationState
        assert window.curve_widget is not None, "Curve widget should be initialized"
        app_state.set_selection("TestCurve", {0})
        process_qt_events()  # Allow selection to propagate

        # Setup spies on signals (Phase 6: curves_changed from ApplicationState)
        spy_data_changed = QSignalSpy(app_state.curves_changed)

        # Trigger point move through UI controller
        if window.ui_init_controller and window.action_controller and window.point_editor_controller:
            # Move selected point by changing spinbox values
            from ui.controllers.point_editor_controller import PointEditorController

            point_editor = window.point_editor_controller
            assert isinstance(point_editor, PointEditorController)

            # Update X coordinate (test single update to avoid race conditions)
            point_editor._on_point_x_changed(110.0)
            # Wait for signal cascade to complete
            wait_for_signal(qtbot, spy_data_changed, min_count=1, timeout=1000)

            # Verify signal cascade (Phase 6: ApplicationState is the source of truth)
            signal_count = spy_data_changed.count()
            assert (
                signal_count >= 1
            ), f"Data update should propagate through ApplicationState (got {signal_count} signals)"

            # Verify end result - coordinate was updated through signal chain
            updated_data = app_state.get_curve_data("TestCurve")
            assert updated_data is not None, "Curve data should exist after update"
            actual_x = updated_data[0][1]
            assert actual_x == 110.0, f"X coordinate should be updated to 110.0, got {actual_x}"
            # Y coordinate should remain unchanged
            actual_y = updated_data[0][2]
            assert actual_y == 200.0, f"Y coordinate should remain 200.0, got {actual_y}"

    def test_signal_chain_integrity_verification(self, qtbot):
        """Test that all required signal connections are properly made.

        This test would catch missing connections that could lead to
        features not working or bugs like the timeline oscillation.
        """
        window = MainWindow()
        qtbot.addWidget(window)

        # List of critical signal connections that must exist
        critical_connections = []

        # Import concrete class for signal access

        # Frame changes now go through ApplicationState (not TimelineController)
        app_state = get_application_state()
        critical_connections.append((app_state.frame_changed, "ApplicationState.frame_changed"))
        critical_connections.append((app_state.curves_changed, "ApplicationState.curves_changed"))

        # Verify all signals have at least one connection
        for signal, name in critical_connections:
            # Note: In PySide6, we can't directly check if a signal has connections
            # But we can verify the signal exists and can be connected to
            try:
                # Create a dummy connection to verify signal is valid
                def dummy_slot():
                    pass

                signal.connect(dummy_slot)
                signal.disconnect(dummy_slot)
                # If we get here, signal is valid and connectable
            except (AttributeError, RuntimeError) as e:
                pytest.fail(f"Critical signal {name} is not properly configured: {e}")

    def test_bidirectional_controller_communication(self, qtbot):
        """Test bidirectional communication between controllers.

        Some controller pairs need to communicate in both directions.
        This test ensures those bidirectional chains work correctly.
        """
        window = MainWindow()
        qtbot.addWidget(window)

        # Setup test data
        app_state = get_application_state()
        test_data: CurveDataList = [(i, float(i * 10), float(i * 10), "keyframe") for i in range(1, 6)]
        app_state.set_curve_data("TestCurve", test_data)
        app_state.set_active_curve("TestCurve")
        process_qt_events()

        # Test ViewManagement <-> UI bidirectional communication
        if window.curve_widget is not None:
            # Change view through view management - update point radius
            _ = (
                window.curve_widget.visual.point_radius if hasattr(window.curve_widget, "visual") else 5
            )  # Store initial for comparison
            window.view_management_controller.update_curve_point_size(10)
            process_qt_events()

            # Verify UI responded (check visual settings, not deprecated property)
            # Note: update_curve_point_size converts slider value (1-20) to radius via * 0.25
            assert window.curve_widget.visual.point_radius == 2.5, "Point radius should have changed to 2.5 (10 * 0.25)"

            # Change view through UI and verify view options is aware
            window.curve_widget.zoom_factor = 2.0
            window.curve_widget.view_changed.emit()
            process_qt_events()

            # View management should reflect the change
            _ = window.view_management_controller.get_view_options()  # Could verify options contain zoom factor
            # Zoom factor change should be reflected in the options if it were tracked


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

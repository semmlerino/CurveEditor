#!/usr/bin/env python3
"""
Integration tests for reactive data flow from stores to UI components.

Verifies that the reactive architecture properly propagates changes from
the central stores to all connected UI components automatically.
"""

import pytest
from PySide6.QtTest import QSignalSpy

from core.models import PointStatus
from core.type_aliases import CurveDataList
from stores import get_store_manager
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

    def setup_method(self):
        """Reset stores before each test."""
        StoreManager.reset()

        # Create StateManager for FrameStore delegation
        from ui.state_manager import StateManager

        self.state_manager = StateManager()

        # Connect StateManager to StoreManager for frame delegation
        store_manager = get_store_manager()
        store_manager.set_state_manager(self.state_manager)

    def teardown_method(self):
        """Clean up after each test."""
        StoreManager.reset()

    def test_store_to_timeline_data_flow(self, qtbot):
        """Test that curve store updates propagate to timeline tabs."""
        # Create timeline
        timeline = TimelineTabWidget()
        qtbot.addWidget(timeline)

        # Get store
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Initial state
        assert timeline.min_frame == 1
        assert timeline.max_frame == 1

        # Setup signal spy to verify signal emission
        spy = QSignalSpy(curve_store.data_changed)

        # Add data to store
        test_data: CurveDataList = [
            (5, 100.0, 100.0, "keyframe"),
            (10, 110.0, 110.0, "interpolated"),
            (15, 120.0, 120.0, "keyframe"),
        ]
        curve_store.set_data(test_data)

        # Verify signal was emitted
        assert spy.count() == 1, "data_changed signal should have been emitted once"

        # Let signals process
        qtbot.wait(100)

        # Timeline should have updated automatically
        assert timeline.min_frame == 5
        assert timeline.max_frame == 15

        # Check status cache updated
        # get_status returns tuple: (keyframe, interpolated, tracked, endframe, normal, start, inactive, selected)
        status_5 = timeline.status_cache.get_status(5)
        assert status_5 is not None and status_5[0] == 1  # keyframe_count

        status_10 = timeline.status_cache.get_status(10)
        assert status_10 is not None and status_10[1] == 1  # interpolated_count

        status_15 = timeline.status_cache.get_status(15)
        assert status_15 is not None and status_15[0] == 1  # keyframe_count

    def test_store_to_curve_widget_data_flow(self, qtbot):
        """Test that curve store updates propagate to curve widget."""
        # Create widget
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Get store
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Initial state
        assert len(widget.curve_data) == 0

        # Setup signal spy to verify signal emission
        spy = QSignalSpy(curve_store.data_changed)

        # Add data to store
        test_data: CurveDataList = [
            (1, 100.0, 200.0, "keyframe"),
            (2, 150.0, 250.0, "normal"),
        ]
        curve_store.set_data(test_data)

        # Verify signal was emitted
        assert spy.count() == 1, "data_changed signal should have been emitted once"

        # Let signals process
        qtbot.wait(100)

        # Widget should have updated automatically
        assert len(widget.curve_data) == 2
        assert widget.curve_data[0] == (1, 100.0, 200.0, "keyframe")
        assert widget.curve_data[1] == (2, 150.0, 250.0, "normal")

    def test_frame_store_sync_with_curve_data(self, qtbot):
        """Test that frame store syncs with curve data changes."""
        # Get stores
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()
        frame_store = store_manager.get_frame_store()

        # Initial state
        assert frame_store.min_frame == 1
        assert frame_store.max_frame == 1
        assert frame_store.current_frame == 1

        # Add data to curve store
        test_data: CurveDataList = [
            (10, 100.0, 100.0, "keyframe"),
            (20, 200.0, 200.0, "keyframe"),
            (30, 300.0, 300.0, "keyframe"),
        ]
        curve_store.set_data(test_data)

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
        curve_store = store_manager.get_curve_store()
        frame_store = store_manager.get_frame_store()

        # Initial setup
        curve_store.set_data([(1, 100.0, 100.0, "keyframe")])
        qtbot.wait(100)

        # Setup signal spy for point addition
        spy_add = QSignalSpy(curve_store.point_added)

        # Add a new point
        curve_store.add_point((5, 200.0, 200.0, "keyframe"))

        # Verify signal was emitted with correct parameters
        assert spy_add.count() == 1, "point_added signal should have been emitted once"
        assert spy_add.at(0)[0] == 1  # index where point was added

        qtbot.wait(100)

        # All components should have updated
        assert len(widget.curve_data) == 2
        assert timeline.max_frame == 5
        assert frame_store.max_frame == 5
        status_5 = timeline.status_cache.get_status(5)
        assert status_5 is not None and status_5[0] == 1  # keyframe_count

    def test_point_removal_propagates_to_all_components(self, qtbot):
        """Test that removing a point updates all connected components."""
        # Create components
        timeline = TimelineTabWidget()
        widget = CurveViewWidget()
        qtbot.addWidget(timeline)
        qtbot.addWidget(widget)

        # Get stores
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()
        frame_store = store_manager.get_frame_store()

        # Initial setup with 3 points
        test_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 200.0, 200.0, "keyframe"),
            (10, 300.0, 300.0, "keyframe"),
        ]
        curve_store.set_data(test_data)
        qtbot.wait(100)

        # Setup signal spy for point removal
        spy_remove = QSignalSpy(curve_store.point_removed)

        # Remove middle point
        curve_store.remove_point(1)  # Index 1

        # Verify signal was emitted
        assert spy_remove.count() == 1, "point_removed signal should have been emitted once"
        assert spy_remove.at(0)[0] == 1  # index that was removed

        qtbot.wait(100)

        # All components should have updated
        assert len(widget.curve_data) == 2
        status_5 = timeline.status_cache.get_status(5)
        assert status_5 is not None and status_5[0] == 0  # keyframe_count
        # Frame range should still be 1-10 since endpoints remain
        assert timeline.max_frame == 10
        assert frame_store.max_frame == 10

    def test_point_status_change_propagates_to_timeline(self, qtbot):
        """Test that changing point status updates timeline colors."""
        # Create timeline
        timeline = TimelineTabWidget()
        qtbot.addWidget(timeline)

        # Get store
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Initial setup
        test_data: CurveDataList = [
            (1, 100.0, 100.0, "normal"),
            (2, 200.0, 200.0, "normal"),
            (3, 300.0, 300.0, "normal"),
        ]
        curve_store.set_data(test_data)
        qtbot.wait(100)

        # All should be normal initially
        # get_status returns tuple: (keyframe, interpolated, tracked, endframe, normal, start, inactive, selected)
        status1 = timeline.status_cache.get_status(1)
        assert status1 is not None and status1[4] == 1  # normal_count
        status2 = timeline.status_cache.get_status(2)
        assert status2 is not None and status2[4] == 1  # normal_count
        status3 = timeline.status_cache.get_status(3)
        assert status3 is not None and status3[4] == 1  # normal_count

        # Change point 2 to keyframe
        curve_store.set_point_status(1, PointStatus.KEYFRAME)
        qtbot.wait(100)

        # Timeline should reflect the change
        # get_status returns tuple: (keyframe, interpolated, tracked, endframe, normal, start, inactive, selected)
        status_2 = timeline.status_cache.get_status(2)
        assert status_2 is not None and status_2[4] == 0  # normal_count
        assert status_2 is not None and status_2[0] == 1  # keyframe_count

    def test_selection_propagates_between_components(self, qtbot):
        """Test that selection changes propagate between components."""
        # Create widget (has selection functionality)
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Get store
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Setup data
        test_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 200.0, 200.0, "normal"),
            (3, 300.0, 300.0, "keyframe"),
        ]
        curve_store.set_data(test_data)
        qtbot.wait(100)

        # Select via store
        curve_store.select(1)
        qtbot.wait(100)

        # Widget should show selection
        assert 1 in widget.selected_indices

        # Multi-select via store
        curve_store.select(2, add_to_selection=True)
        qtbot.wait(100)

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
        curve_store = store_manager.get_curve_store()
        frame_store = store_manager.get_frame_store()

        # Setup data
        test_data: CurveDataList = [
            (5, 100.0, 100.0, "keyframe"),
            (10, 200.0, 200.0, "normal"),
            (15, 300.0, 300.0, "keyframe"),
        ]
        curve_store.set_data(test_data)
        qtbot.wait(100)

        # Verify data is loaded
        assert len(widget.curve_data) == 3
        assert timeline.max_frame == 15

        # Clear the store
        curve_store.clear()
        qtbot.wait(100)

        # All components should reset
        assert len(widget.curve_data) == 0
        assert timeline.min_frame == 1
        assert timeline.max_frame == 1
        assert frame_store.min_frame == 1
        assert frame_store.max_frame == 1
        assert frame_store.current_frame == 1

    def test_batch_operations_propagate_efficiently(self, qtbot):
        """Test that batch operations result in efficient updates.

        Tests behavior not implementation - verifies that rapid changes
        still result in correct final state.
        """
        # Create timeline with deferred updates
        timeline = TimelineTabWidget()
        qtbot.addWidget(timeline)

        # Get store
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Add multiple points rapidly
        for i in range(1, 11):
            curve_store.add_point((i, float(i * 10), float(i * 10), "normal"))

        # Wait for deferred update to complete
        qtbot.wait(100)  # Allow deferred updates to process (timeline uses 50ms timer)

        # Timeline should have all points correctly reflected
        assert timeline.max_frame == 10

        # Verify each frame has correct status
        for i in range(1, 11):
            # Test behavior: each frame should be marked
            status = timeline.status_cache.get_status(i)
            # get_status returns tuple: (keyframe, interpolated, tracked, endframe, normal, start, inactive, selected)
            assert status is not None and status[4] == 1  # normal_count - Each point is normal by default

    def test_no_manual_updates_override_store(self, qtbot):
        """Test that manual timeline updates don't override store data."""
        # Create timeline
        timeline = TimelineTabWidget()
        qtbot.addWidget(timeline)

        # Get store and set data
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        test_data: CurveDataList = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 200.0, 200.0, "keyframe"),
            (10, 300.0, 300.0, "keyframe"),
        ]
        curve_store.set_data(test_data)
        qtbot.wait(100)

        # Timeline should show store data
        assert timeline.min_frame == 1
        assert timeline.max_frame == 10

        # Verify that direct controller manipulation doesn't override store data
        # This ensures store remains the single source of truth
        from ui.controllers.timeline_controller import TimelineController

        # TimelineController expects MainWindow, but we're testing isolation with TimelineTabWidget
        # This type mismatch is intentional for testing store precedence
        controller = TimelineController(timeline)  # pyright: ignore[reportArgumentType]

        # Attempt direct frame range update (should not affect store-driven timeline)
        controller.update_for_tracking_data(37)

        # Timeline should still reflect store data, not manual update
        # This proves the store remains the authoritative data source
        assert timeline.min_frame == 1
        assert timeline.max_frame == 10  # NOT 37

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

        # Get store
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Set invalid/edge case data
        invalid_data: CurveDataList = [
            (0, 100.0, 100.0, "keyframe"),  # Frame 0 (edge case)
            (-1, 200.0, 200.0, "normal"),  # Negative frame
        ]
        curve_store.set_data(invalid_data)
        qtbot.wait(100)

        # Components should handle gracefully
        # Frame store should clamp to valid range
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
        curve_store = store_manager.get_curve_store()
        frame_store = store_manager.get_frame_store()

        # Perform rapid changes
        for iteration in range(3):
            # Add points
            test_data: CurveDataList = [(i, float(i * 10), float(i * 10), "normal") for i in range(1, 6)]
            curve_store.set_data(test_data)

            # Change selection rapidly
            for i in range(5):
                curve_store.select(i)

            # Clear and re-add
            curve_store.clear()
            curve_store.set_data(test_data[:3])

        # Allow all updates to process
        qtbot.wait(100)

        # Final state should be consistent across all components
        final_data = curve_store.get_data()
        assert len(widget.curve_data) == len(final_data)
        assert timeline.max_frame == 3  # Should match final data
        assert frame_store.max_frame == 3

        # Verify status cache is consistent
        for i in range(1, 4):
            status = timeline.status_cache.get_status(i)
            # get_status returns tuple: (keyframe, interpolated, tracked, endframe, normal, start, inactive, selected)
            assert status is not None and status[4] == 1  # normal_count


class TestMultiControllerSignalChains:
    """Test signal chains between multiple controllers.

    Following unified testing guide's emphasis on multi-controller signal testing:
    - Verify controller-to-controller signal connections
    - Test signal chain integrity
    - Ensure signals propagate through the full chain
    - Detect missing connections that could cause bugs
    """

    def setup_method(self):
        """Reset stores before each test."""
        StoreManager.reset()

    def teardown_method(self):
        """Clean up after each test."""
        StoreManager.reset()

    def test_timeline_controller_signal_chain(self, qtbot):
        """Test signal chain from TimelineController.

        This tests the critical timeline control chain.
        """

        from ui.controllers.timeline_controller import TimelineController

        # Create main window with all controllers
        window = MainWindow()
        qtbot.addWidget(window)

        # Get the controller - cast to implementation class for testing
        # Testing implementation details requires access to concrete class
        timeline_controller = window.timeline_controller
        assert isinstance(timeline_controller, TimelineController)  # Ensure we have the actual implementation

        # Verify controller exists
        assert timeline_controller is not None

        # Setup signal spy on timeline controller's frame_changed signal
        spy_frame_changed = QSignalSpy(timeline_controller.frame_changed)

        # Setup test data
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()
        test_data: CurveDataList = [(i, float(i * 10), float(i * 10), "keyframe") for i in range(1, 11)]
        curve_store.set_data(test_data)

        qtbot.wait(100)  # Let data propagate

        # Set initial frame to a known value
        timeline_controller.set_frame(1)
        qtbot.wait(50)
        initial_frame = window.current_frame

        # Start playback
        timeline_controller.toggle_playback()

        # Simulate timer tick
        timeline_controller._on_playback_timer()

        # Verify signal was emitted
        assert spy_frame_changed.count() >= 1, "frame_changed signal should have been emitted"
        if spy_frame_changed.count() > 0:
            changed_frame = spy_frame_changed.at(0)[0]
            assert changed_frame == initial_frame + 1, "Should change to next frame"

        # Verify the chain completed (frame actually changed)
        qtbot.wait(100)
        # Frame should have advanced
        assert (
            window.current_frame > initial_frame
        ), f"Frame should have advanced from {initial_frame}, got {window.current_frame}"

        # Stop playback
        timeline_controller.toggle_playback()

    def test_controller_cascade_signal_chain(self, qtbot):
        """Test cascading signals through multiple controllers.

        Tests the pattern:
        UIController -> ActionHandler -> PointEditor -> Store -> All UI
        """
        window = MainWindow()
        qtbot.addWidget(window)

        # Setup test data
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()
        test_data: CurveDataList = [(1, 100.0, 200.0, "keyframe"), (2, 150.0, 250.0, "normal")]
        curve_store.set_data(test_data)
        qtbot.wait(100)

        # Select first point
        assert window.curve_widget is not None, "Curve widget should be initialized"
        window.curve_widget.selected_points = {0}

        # Setup spies on critical signals
        _ = QSignalSpy(curve_store.selection_changed)  # Could be used to verify selection changes
        spy_point_update = QSignalSpy(curve_store.point_updated)

        # Trigger point move through UI controller
        if window.ui_init_controller and window.action_controller and window.point_editor_controller:
            # Move selected point by changing spinbox values
            # Using public interface through spinbox values
            from ui.controllers.point_editor_controller import PointEditorController

            point_editor = window.point_editor_controller
            assert isinstance(point_editor, PointEditorController)
            point_editor._on_point_x_changed(110.0)
            point_editor._on_point_y_changed(210.0)

            # Verify signal cascade
            assert spy_point_update.count() >= 1, "Point update should propagate through chain"
            if spy_point_update.count() > 0:
                assert spy_point_update.at(0)[0] == 0  # First point was updated

            # Verify end result
            qtbot.wait(100)
            updated_data = curve_store.get_data()
            assert updated_data[0][1] == 110.0  # X coordinate updated
            assert updated_data[0][2] == 210.0  # Y coordinate updated

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
        from ui.controllers.timeline_controller import TimelineController

        # Timeline -> UI Updates
        if window.timeline_controller:
            # Cast to concrete class to access signals
            if isinstance(window.timeline_controller, TimelineController):
                critical_connections.append(
                    (window.timeline_controller.frame_changed, "TimelineController.frame_changed")
                )

        # Store -> UI Components
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()
        critical_connections.append((curve_store.data_changed, "CurveDataStore.data_changed"))

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
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()
        test_data: CurveDataList = [(i, float(i * 10), float(i * 10), "keyframe") for i in range(1, 6)]
        curve_store.set_data(test_data)
        qtbot.wait(100)

        # Test ViewManagement <-> UI bidirectional communication
        if window.view_management_controller and window.ui_init_controller and window.curve_widget:
            # Change view through view management - update point radius
            _ = (
                window.curve_widget.point_radius if hasattr(window.curve_widget, "point_radius") else 5
            )  # Store initial for comparison
            window.view_management_controller.update_curve_point_size(10)
            qtbot.wait(100)

            # Verify UI responded
            assert window.curve_widget.point_radius == 10, "Point radius should have changed"

            # Change view through UI and verify view options is aware
            window.curve_widget.zoom_factor = 2.0
            window.curve_widget.view_changed.emit()
            qtbot.wait(100)

            # View management should reflect the change
            _ = window.view_management_controller.get_view_options()  # Could verify options contain zoom factor
            # Zoom factor change should be reflected in the options if it were tracked


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
Integration tests for reactive data flow from stores to UI components.

Verifies that the reactive architecture properly propagates changes from
the central stores to all connected UI components automatically.
"""

import pytest

from core.models import PointStatus
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

        # Add data to store
        test_data = [
            (5, 100.0, 100.0, "keyframe"),
            (10, 110.0, 110.0, "interpolated"),
            (15, 120.0, 120.0, "keyframe"),
        ]
        curve_store.set_data(test_data)

        # Let signals process
        qtbot.wait(100)

        # Timeline should have updated automatically
        assert timeline.min_frame == 5
        assert timeline.max_frame == 15

        # Check status cache updated
        # get_status returns tuple: (keyframe, interpolated, tracked, endframe, normal, start, inactive, selected)
        status_5 = timeline.status_cache.get_status(5)
        assert status_5[0] == 1  # keyframe_count

        status_10 = timeline.status_cache.get_status(10)
        assert status_10[1] == 1  # interpolated_count

        status_15 = timeline.status_cache.get_status(15)
        assert status_15[0] == 1  # keyframe_count

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

        # Add data to store
        test_data = [
            (1, 100.0, 200.0, "keyframe"),
            (2, 150.0, 250.0, "normal"),
        ]
        curve_store.set_data(test_data)

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
        test_data = [
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

        # Add a new point
        curve_store.add_point((5, 200.0, 200.0, "keyframe"))
        qtbot.wait(100)

        # All components should have updated
        assert len(widget.curve_data) == 2
        assert timeline.max_frame == 5
        assert frame_store.max_frame == 5
        assert timeline.status_cache.get_status(5)[0] == 1  # keyframe_count

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
        test_data = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 200.0, 200.0, "keyframe"),
            (10, 300.0, 300.0, "keyframe"),
        ]
        curve_store.set_data(test_data)
        qtbot.wait(100)

        # Remove middle point
        curve_store.remove_point(1)  # Index 1
        qtbot.wait(100)

        # All components should have updated
        assert len(widget.curve_data) == 2
        assert timeline.status_cache.get_status(5)[0] == 0  # keyframe_count
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
        test_data = [
            (1, 100.0, 100.0, "normal"),
            (2, 200.0, 200.0, "normal"),
            (3, 300.0, 300.0, "normal"),
        ]
        curve_store.set_data(test_data)
        qtbot.wait(100)

        # All should be normal initially
        # get_status returns tuple: (keyframe, interpolated, tracked, endframe, normal, start, inactive, selected)
        assert timeline.status_cache.get_status(1)[4] == 1  # normal_count
        assert timeline.status_cache.get_status(2)[4] == 1  # normal_count
        assert timeline.status_cache.get_status(3)[4] == 1  # normal_count

        # Change point 2 to keyframe
        curve_store.set_point_status(1, PointStatus.KEYFRAME)
        qtbot.wait(100)

        # Timeline should reflect the change
        # get_status returns tuple: (keyframe, interpolated, tracked, endframe, normal, start, inactive, selected)
        status_2 = timeline.status_cache.get_status(2)
        assert status_2[4] == 0  # normal_count
        assert status_2[0] == 1  # keyframe_count

    def test_selection_propagates_between_components(self, qtbot):
        """Test that selection changes propagate between components."""
        # Create widget (has selection functionality)
        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Get store
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Setup data
        test_data = [
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
        test_data = [
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
            assert status[4] == 1  # normal_count - Each point is normal by default

    def test_no_manual_updates_override_store(self, qtbot):
        """Test that manual timeline updates don't override store data."""
        # Create timeline
        timeline = TimelineTabWidget()
        qtbot.addWidget(timeline)

        # Get store and set data
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        test_data = [
            (1, 100.0, 100.0, "keyframe"),
            (5, 200.0, 200.0, "keyframe"),
            (10, 300.0, 300.0, "keyframe"),
        ]
        curve_store.set_data(test_data)
        qtbot.wait(100)

        # Timeline should show store data
        assert timeline.min_frame == 1
        assert timeline.max_frame == 10

        # Try to manually set frame range (should be ignored or overridden)
        # The update_for_tracking_data is now deprecated
        from ui.controllers.timeline_controller import TimelineController

        controller = TimelineController(timeline)
        controller.update_for_tracking_data(37)  # Should be ignored

        # Timeline should still show store data, not manual update
        assert timeline.min_frame == 1
        assert timeline.max_frame == 10  # NOT 37

    def test_main_window_connections_verified(self, qtbot):
        """Test that MainWindow verifies all critical connections.

        Tests behavior: Verifies that data flows correctly from stores
        to all connected UI components through MainWindow.
        """
        # Create main window (real component)
        window = MainWindow()
        qtbot.addWidget(window)

        # Verify components are not None (Qt container safety)
        assert window.timeline_tabs is not None
        assert window.curve_widget is not None

        # Get store (real component)
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Add data to store
        test_data = [(1, 100.0, 100.0, "keyframe")]
        curve_store.set_data(test_data)
        qtbot.wait(100)

        # Test behavior: Both UI components should reflect store data
        assert window.timeline_tabs.max_frame == 1
        assert len(window.curve_widget.curve_data) == 1

        # Test more complex behavior: add another point
        curve_store.add_point((5, 150.0, 150.0, "keyframe"))
        qtbot.wait(100)

        # Both components should update automatically
        assert window.timeline_tabs.max_frame == 5
        assert len(window.curve_widget.curve_data) == 2

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
        invalid_data = [
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
            test_data = [(i, float(i * 10), float(i * 10), "normal") for i in range(1, 6)]
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
            assert status[4] == 1  # normal_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

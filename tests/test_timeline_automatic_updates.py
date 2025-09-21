#!/usr/bin/env python3
"""
Test that timeline automatically updates via store signals.

This test verifies that the timeline updates automatically when
the data store changes, without manual update calls.
"""

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from stores import get_store_manager
from ui.main_window import MainWindow


class TestTimelineAutomaticUpdates:
    """Test automatic timeline updates via reactive store."""

    @pytest.fixture
    def app(self) -> QApplication:
        """Create QApplication for widget tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    @pytest.fixture
    def main_window(self, app: QApplication, qtbot: QtBot) -> MainWindow:
        """Create MainWindow for testing."""
        window = MainWindow()
        qtbot.addWidget(window)
        return window

    def test_timeline_updates_automatically_on_data_change(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that timeline updates automatically when store data changes."""
        # Get the store
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Clear any existing data in the store (from previous tests)
        curve_store.set_data([])
        qtbot.wait(50)

        # Verify timeline is at default state
        timeline = main_window.timeline_tabs
        assert timeline.min_frame == 1
        assert timeline.max_frame == 1, f"Expected max_frame=1 after clearing store, got {timeline.max_frame}"

        # Create initial test data
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),
            (3, 120.0, 120.0, "keyframe"),
        ]

        # Set data in store (timeline should update automatically)
        curve_store.set_data(initial_data)

        # Wait for signals to propagate
        qtbot.wait(100)

        # Verify timeline has the correct frame range
        timeline = main_window.timeline_tabs
        assert timeline is not None
        # Timeline should have frames 1-3
        assert timeline.min_frame == 1
        assert timeline.max_frame == 3
        assert 1 in timeline.frame_tabs
        assert 2 in timeline.frame_tabs
        assert 3 in timeline.frame_tabs

        # Verify status counts are correct
        tab1 = timeline.frame_tabs[1]
        assert tab1.keyframe_count >= 1  # May be startframe which adds to keyframe count

        tab2 = timeline.frame_tabs[2]
        assert tab2.interpolated_count == 1

        # Now change the data
        new_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "keyframe"),  # Changed from interpolated
            (3, 120.0, 120.0, "tracked"),  # Changed from keyframe
            (4, 130.0, 130.0, "endframe"),  # New frame
        ]

        # Update store (timeline should update automatically)
        curve_store.set_data(new_data)

        # Wait for signals to propagate
        qtbot.wait(100)

        # Verify timeline updated automatically
        assert timeline.min_frame == 1
        assert timeline.max_frame == 4
        assert 4 in timeline.frame_tabs

        # Verify updated statuses
        tab2_updated = timeline.frame_tabs[2]
        assert tab2_updated.keyframe_count >= 1
        assert tab2_updated.interpolated_count == 0

        tab3_updated = timeline.frame_tabs[3]
        assert tab3_updated.tracked_count == 1

        tab4 = timeline.frame_tabs[4]
        assert tab4.endframe_count == 1

    def test_timeline_updates_on_point_status_change(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that timeline updates when a point's status changes."""
        # Get the store
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Create test data
        test_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "keyframe"),
            (3, 120.0, 120.0, "keyframe"),
        ]

        # Set data in store
        curve_store.set_data(test_data)
        qtbot.wait(100)

        # Get timeline and verify initial state
        timeline = main_window.timeline_tabs
        tab2 = timeline.frame_tabs[2]
        initial_color = tab2._get_background_color()

        # Change status of point at index 1 (frame 2)
        curve_store.set_point_status(1, "interpolated")

        # Wait for signals to propagate
        qtbot.wait(100)

        # Verify timeline updated automatically
        tab2_after = timeline.frame_tabs[2]
        updated_color = tab2_after._get_background_color()

        # Colors should be different
        assert initial_color.name() != updated_color.name()

        # Verify counts
        assert tab2_after.interpolated_count == 1
        assert tab2_after.keyframe_count == 0

    def test_timeline_updates_on_point_addition(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that timeline updates when a point is added."""
        # Get the store
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Create initial data
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (3, 120.0, 120.0, "keyframe"),
        ]

        # Set data in store
        curve_store.set_data(initial_data)
        qtbot.wait(100)

        # Verify initial state
        timeline = main_window.timeline_tabs
        assert timeline.min_frame == 1
        assert timeline.max_frame == 3

        # Add a point at frame 2
        curve_store.add_point((2, 110.0, 110.0, "interpolated"))

        # Wait for signals to propagate
        qtbot.wait(100)

        # Verify timeline updated
        tab2 = timeline.frame_tabs[2]
        assert tab2.interpolated_count == 1

    def test_timeline_updates_on_point_removal(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that timeline updates when a point is removed."""
        # Get the store
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Create initial data
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),
            (3, 120.0, 120.0, "keyframe"),
        ]

        # Set data in store
        curve_store.set_data(initial_data)
        qtbot.wait(100)

        # Verify initial state
        timeline = main_window.timeline_tabs
        tab2 = timeline.frame_tabs[2]
        assert tab2.interpolated_count == 1

        # Remove point at index 1 (frame 2)
        curve_store.remove_point(1)

        # Wait for signals to propagate
        qtbot.wait(100)

        # Verify timeline updated
        tab2_after = timeline.frame_tabs[2]
        assert tab2_after.interpolated_count == 0
        assert tab2_after.keyframe_count == 0  # Frame 2 should now be empty


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
Test that timeline automatically updates via store signals.

This test verifies that the timeline updates automatically when
the data store changes, without manual update calls.
"""

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from stores.application_state import get_application_state
from ui.main_window import MainWindow


class TestTimelineAutomaticUpdates:
    """Test automatic timeline updates via reactive store."""

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

        # Get application state and reset
        app_state = get_application_state()

        # Reset state to clear any image sequence
        window.state_manager.reset_to_defaults()
        window.view_management_controller.clear_background_images()

        # Create and set an active curve for testing
        test_curve_name = "__default__"
        app_state.set_curve_data(test_curve_name, [])
        app_state.set_active_curve(test_curve_name)
        qtbot.wait(50)  # Let curves_changed signal propagate

        # Force timeline to update with clean state (after reset)
        assert window.timeline_tabs is not None
        window.timeline_tabs._on_curves_changed(app_state.get_all_curves())
        qtbot.wait(50)

        return window

    def test_timeline_updates_automatically_on_data_change(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that timeline updates automatically when store data changes."""
        # Get the application state
        app_state = get_application_state()

        # Get active curve name
        active_curve = app_state.active_curve
        assert active_curve is not None

        # Verify timeline exists (may have background image frames)
        timeline = main_window.timeline_tabs
        assert timeline is not None

        # Create initial test data
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),
            (3, 120.0, 120.0, "keyframe"),
        ]

        # Set data in application state (timeline should update automatically)
        app_state.set_curve_data(active_curve, initial_data)

        # Wait for signals to propagate
        qtbot.wait(100)

        # Verify timeline updated - should now include frames 1-3
        timeline = main_window.timeline_tabs
        assert timeline is not None
        # Timeline should have AT LEAST frames 1-3 (may have more from background image)
        assert timeline.min_frame == 1
        assert timeline.max_frame >= 3
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

        # Update application state (timeline should update automatically)
        app_state.set_curve_data(active_curve, new_data)

        # Wait for signals to propagate
        qtbot.wait(100)

        # Verify timeline updated automatically - should now include frame 4
        assert timeline.min_frame == 1
        assert timeline.max_frame >= 4
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
        # Get the application state
        app_state = get_application_state()

        # Get active curve name
        active_curve = app_state.active_curve
        assert active_curve is not None

        # Create test data
        test_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "keyframe"),
            (3, 120.0, 120.0, "keyframe"),
        ]

        # Set data in application state
        app_state.set_curve_data(active_curve, test_data)
        qtbot.wait(100)

        # Get timeline and verify initial state
        timeline = main_window.timeline_tabs
        assert timeline is not None
        tab2 = timeline.frame_tabs[2]
        initial_color = tab2._get_background_color()

        # Get current data and modify it
        current_data = app_state.get_curve_data(active_curve)
        assert current_data is not None
        modified_data = [
            current_data[0],
            (2, current_data[1][1], current_data[1][2], "interpolated"),
            current_data[2],
        ]
        app_state.set_curve_data(active_curve, modified_data)

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
        # Get the application state
        app_state = get_application_state()

        # Get active curve name
        active_curve = app_state.active_curve
        assert active_curve is not None

        # Create initial data
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (3, 120.0, 120.0, "keyframe"),
        ]

        # Set data in application state
        app_state.set_curve_data(active_curve, initial_data)
        qtbot.wait(100)

        # Verify initial state
        timeline = main_window.timeline_tabs
        assert timeline is not None
        assert timeline.min_frame == 1
        assert timeline.max_frame == 3

        # Add a point at frame 2 by updating the data
        new_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),
            (3, 120.0, 120.0, "keyframe"),
        ]
        app_state.set_curve_data(active_curve, new_data)

        # Wait for signals to propagate
        qtbot.wait(100)

        # Verify timeline updated
        tab2 = timeline.frame_tabs[2]
        assert tab2.interpolated_count == 1

    def test_timeline_updates_on_point_removal(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that timeline updates when a point is removed."""
        # Get the application state
        app_state = get_application_state()

        # Get active curve name
        active_curve = app_state.active_curve
        assert active_curve is not None

        # Create initial data
        initial_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),
            (3, 120.0, 120.0, "keyframe"),
        ]

        # Set data in application state
        app_state.set_curve_data(active_curve, initial_data)
        qtbot.wait(100)

        # Verify initial state
        timeline = main_window.timeline_tabs
        assert timeline is not None
        tab2 = timeline.frame_tabs[2]
        assert tab2.interpolated_count == 1

        # Remove point at index 1 (frame 2) by updating the data
        new_data = [
            (1, 100.0, 100.0, "keyframe"),
            (3, 120.0, 120.0, "keyframe"),
        ]
        app_state.set_curve_data(active_curve, new_data)

        # Wait for signals to propagate
        qtbot.wait(100)

        # Verify timeline updated
        tab2_after = timeline.frame_tabs[2]
        assert tab2_after.interpolated_count == 0
        assert tab2_after.keyframe_count == 0  # Frame 2 should now be empty


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

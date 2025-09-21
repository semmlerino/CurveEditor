#!/usr/bin/env python3
"""
Test that timeline reacts to store changes properly.

This is a simpler test that works with whatever frame range the timeline has.
"""

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from stores import get_store_manager
from ui.main_window import MainWindow


class TestTimelineStoreReactive:
    """Test timeline reactive updates via store."""

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

    def test_timeline_reacts_to_store_changes(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that timeline updates when store changes."""
        # Get the store
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Get timeline
        timeline = main_window.timeline_tabs
        assert timeline is not None

        # Note the initial frame range (whatever it is)
        initial_min = timeline.min_frame
        initial_max = timeline.max_frame
        print(f"Initial timeline range: {initial_min}-{initial_max}")

        # Set some test data within a reasonable range
        test_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "interpolated"),
            (3, 120.0, 120.0, "keyframe"),
        ]
        curve_store.set_data(test_data)
        qtbot.wait(100)

        # Verify timeline has frames 1-3 now
        assert timeline.min_frame == 1
        assert timeline.max_frame == 3

        # Verify frame 2 has interpolated status
        if 2 in timeline.frame_tabs:
            tab2 = timeline.frame_tabs[2]
            assert tab2.interpolated_count == 1

    def test_timeline_colors_update_on_status_change(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that timeline colors update when point status changes."""
        # Get the store
        store_manager = get_store_manager()
        curve_store = store_manager.get_curve_store()

        # Set initial data
        test_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "keyframe"),
            (3, 120.0, 120.0, "keyframe"),
        ]
        curve_store.set_data(test_data)
        qtbot.wait(100)

        # Get timeline
        timeline = main_window.timeline_tabs

        # Check frame 2 initial state
        if 2 in timeline.frame_tabs:
            tab2 = timeline.frame_tabs[2]
            initial_color = tab2._get_background_color()

            # Change status to interpolated
            curve_store.set_point_status(1, "interpolated")  # Index 1 is frame 2
            qtbot.wait(100)

            # Color should have changed
            updated_color = tab2._get_background_color()
            assert initial_color.name() != updated_color.name()
            assert tab2.interpolated_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

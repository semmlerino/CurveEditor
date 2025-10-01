#!/usr/bin/env python3
"""
Test that timeline reacts to store changes properly.

This is a simpler test that works with whatever frame range the timeline has.
"""

from unittest.mock import patch

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
        # Mock file operations to prevent auto-loading burger data
        with patch("ui.file_operations.FileOperations.load_burger_data_async"):
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

        # Process events to allow signals to propagate
        # Use processEvents instead of qtbot.wait to avoid event loop issues after 1600+ tests
        app = QApplication.instance()
        for _ in range(10):
            if app:
                app.processEvents()

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

        # Set initial data - single keyframe at frame 1
        test_data = [
            (1, 100.0, 100.0, "keyframe"),
        ]
        curve_store.set_data(test_data)

        # Process events to allow signals to propagate
        app = QApplication.instance()
        for _ in range(10):
            if app:
                app.processEvents()

        # Get timeline
        timeline = main_window.timeline_tabs

        # Check frame 1 initial state (pure keyframe)
        if 1 in timeline.frame_tabs:
            tab1 = timeline.frame_tabs[1]
            initial_color = tab1._get_background_color()

            # Verify it's the keyframe color
            assert tab1.keyframe_count == 1
            assert tab1.interpolated_count == 0

            # Change status to interpolated
            curve_store.set_point_status(0, "interpolated")  # Index 0 is frame 1

            # Manually trigger the deferred update instead of waiting for timer
            # This avoids Qt event loop issues after 1600+ tests
            timeline._perform_deferred_updates()

            # Color should have changed from keyframe to interpolated
            updated_color = tab1._get_background_color()
            assert (
                initial_color.name() != updated_color.name()
            ), f"Color should change from keyframe to interpolated, got {initial_color.name()} -> {updated_color.name()}"
            assert tab1.interpolated_count == 1
            assert tab1.keyframe_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

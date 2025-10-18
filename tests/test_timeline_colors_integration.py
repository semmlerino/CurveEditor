#!/usr/bin/env python3
"""
Integration test for timeline colors with real data.

Tests that different point statuses display as different colors on the timeline.
"""

from pathlib import Path

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from services import get_data_service
from ui.main_window import MainWindow


class TestTimelineColorsIntegration:
    """Integration tests for timeline colors with real data."""

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
        window = MainWindow(auto_load_data=False)  # Disable auto-loading test data
        qtbot.addWidget(window)
        return window

    def test_timeline_colors_with_varied_statuses(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that loading data with different statuses shows different timeline colors."""
        # Get the test data file path
        test_file = Path(__file__).parent.parent / "test_data" / "timeline_test_statuses.json"
        assert test_file.exists(), f"Test data file not found: {test_file}"

        # Load the test data
        data_service = get_data_service()
        curve_data = data_service.load_json(str(test_file))

        # Load data into the main window
        assert main_window.curve_widget is not None
        main_window.curve_widget.set_curve_data(curve_data)

        # Wait for automatic update from signal connections
        qtbot.wait(50)

        # Trigger timeline update explicitly to ensure status is set
        main_window.update_timeline_tabs(curve_data)

        # Wait for any deferred updates
        qtbot.wait(100)

        # Verify timeline has tabs
        timeline = main_window.timeline_tabs
        assert timeline is not None
        assert len(timeline.frame_tabs) > 0

        # Verify that we have tabs for our test frames (1-10)
        for frame in range(1, 11):
            assert frame in timeline.frame_tabs, f"Frame {frame} not in timeline tabs"

        # Verify status counts are correct
        tab1 = timeline.frame_tabs[1]
        assert tab1.keyframe_count == 1
        assert tab1.interpolated_count == 0

        tab2 = timeline.frame_tabs[2]
        assert tab2.keyframe_count == 0
        assert tab2.interpolated_count == 1

        tab5 = timeline.frame_tabs[5]
        assert tab5.tracked_count == 1

        tab9 = timeline.frame_tabs[9]
        assert tab9.endframe_count == 1

        # Get colors for different status types
        colors = {}
        colors["keyframe"] = timeline.frame_tabs[1]._get_background_color()
        colors["interpolated"] = timeline.frame_tabs[2]._get_background_color()
        colors["tracked"] = timeline.frame_tabs[5]._get_background_color()
        colors["endframe"] = timeline.frame_tabs[9]._get_background_color()

        # Verify all colors are different
        color_values = set()
        for status, color in colors.items():
            color_tuple = (color.red(), color.green(), color.blue())
            color_values.add(color_tuple)

        assert len(color_values) == 4, f"Expected 4 different colors for different statuses, got {len(color_values)}"

        # Verify specific color assignments match FrameTab expected colors
        # The colors should be from the right category even if exact values vary slightly
        # (May vary due to hover effects or gradients - up to 10% lighter)
        keyframe_expected = tab1.COLORS["keyframe"]
        # Increased tolerance to 30 to account for gradient effect (lighter(110) = 10% brighter)
        assert abs(colors["keyframe"].red() - keyframe_expected.red()) <= 30
        assert abs(colors["keyframe"].green() - keyframe_expected.green()) <= 30
        assert abs(colors["keyframe"].blue() - keyframe_expected.blue()) <= 30

    def test_timeline_updates_on_status_change(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that timeline colors update when point status changes."""
        # Set active curve first
        from stores.application_state import get_application_state

        app_state = get_application_state()
        app_state.set_active_curve("__default__")

        # Create simple test data
        test_data = [
            (1, 100.0, 100.0, "keyframe"),
            (2, 110.0, 110.0, "keyframe"),
            (3, 120.0, 120.0, "keyframe"),
        ]

        # Load data
        assert main_window.curve_widget is not None
        main_window.curve_widget.set_curve_data(test_data)
        main_window.update_timeline_tabs(test_data)
        qtbot.wait(100)

        # Verify initial colors (all keyframe, but frame 1 might be startframe)
        timeline = main_window.timeline_tabs
        assert timeline is not None
        color2_before = timeline.frame_tabs[2]._get_background_color()
        color3_before = timeline.frame_tabs[3]._get_background_color()
        # Compare frames 2 and 3 which should both be regular keyframes
        assert color2_before.name() == color3_before.name()

        # Change status of point at frame 2 to interpolated
        # Get current data, modify status, and set back
        current_data = list(app_state.get_curve_data("__default__"))
        # Index 1 is frame 2 - update its status
        point = current_data[1]
        frame, x, y = point[0], point[1], point[2]
        current_data[1] = (frame, x, y, "interpolated")
        app_state.set_curve_data("__default__", current_data)

        # Update timeline
        main_window.update_timeline_tabs()
        qtbot.wait(100)

        # Verify colors are now different
        color2_after = timeline.frame_tabs[2]._get_background_color()
        color3_after = timeline.frame_tabs[3]._get_background_color()
        assert color2_after.name() != color3_after.name()

        # Verify frame 2 now has interpolated color
        assert timeline.frame_tabs[2].interpolated_count == 1
        assert timeline.frame_tabs[2].keyframe_count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

#!/usr/bin/env python3
"""
Test that timeline reacts to store changes properly.

This is a simpler test that works with whatever frame range the timeline has.
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

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qtbot import QtBot

from ui.main_window import MainWindow


class TestTimelineStoreReactive:
    """Test timeline reactive updates via store."""

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
    def main_window(self, app: QApplication, qtbot: QtBot, without_dummy_frames) -> MainWindow:
        """Create MainWindow for testing.

        Uses without_dummy_frames to clear the 1000 dummy frames from conftest
        so the timeline frame range is based only on test data.
        """
        # Mock file operations to prevent auto-loading burger data
        with patch("ui.file_operations.FileOperations.load_burger_data_async"):
            window = MainWindow()
            qtbot.addWidget(window)
            return window

    def test_timeline_reacts_to_store_changes(self, main_window: MainWindow, qtbot: QtBot) -> None:
        """Test that timeline updates when store changes."""
        # Get ApplicationState
        from stores.application_state import get_application_state

        app_state = get_application_state()

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
        app_state.set_active_curve("__default__")  # Set active curve before data
        app_state.set_curve_data("__default__", test_data)

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
        # Get ApplicationState
        from stores.application_state import get_application_state

        app_state = get_application_state()

        # Set initial data - single keyframe at frame 1
        test_data = [
            (1, 100.0, 100.0, "keyframe"),
        ]
        app_state.set_active_curve("__default__")  # Set active curve before data
        app_state.set_curve_data("__default__", test_data)

        # Process events to allow signals to propagate
        app = QApplication.instance()
        for _ in range(10):
            if app:
                app.processEvents()

        # Get timeline
        timeline = main_window.timeline_tabs
        assert timeline is not None

        # Check frame 1 initial state (pure keyframe)
        if 1 in timeline.frame_tabs:
            tab1 = timeline.frame_tabs[1]
            initial_color = tab1._get_background_color()

            # Verify it's the keyframe color
            assert tab1.keyframe_count == 1
            assert tab1.interpolated_count == 0

            # Change status to interpolated via ApplicationState
            current_data = list(app_state.get_curve_data("__default__"))
            point = current_data[0]  # Index 0 is frame 1
            frame, x, y = point[0], point[1], point[2]
            current_data[0] = (frame, x, y, "interpolated")
            app_state.set_curve_data("__default__", current_data)

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

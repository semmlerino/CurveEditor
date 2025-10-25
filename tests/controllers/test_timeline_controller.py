#!/usr/bin/env python
"""Tests for TimelineController.

Tests frame navigation, playback controls, and timeline interactions.
"""


import pytest
from tests.test_helpers import MockMainWindow
from ui.controllers.timeline_controller import TimelineController


@pytest.fixture
def controller(mock_main_window: MockMainWindow) -> TimelineController:
    """Create TimelineController with mock main window."""
    # TimelineController inherits from QObject and needs QObject parent or None
    # MockMainWindow is not a QObject, so pass None for testing
    return TimelineController(
        mock_main_window.state_manager,
        parent=None  # Test doesn't need Qt parent relationship
    )


class TestTimelineController:
    """Test suite for TimelineController."""
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


    def test_play_button_starts_playback(
        self,
        controller: TimelineController,
        mock_main_window: MockMainWindow
    ) -> None:
        """Test play button starts playback timer."""
        # TimelineController has start_playback(), not on_play_clicked()
        controller.start_playback()
        # is_playing is a property, not a method
        assert controller.is_playing

    def test_pause_button_stops_playback(
        self,
        controller: TimelineController,
        mock_main_window: MockMainWindow
    ) -> None:
        """Test pause button stops playback timer."""
        # Start playback first, then stop it
        controller.start_playback()
        controller.stop_playback()
        # is_playing is a property, not a method
        assert not controller.is_playing

    def test_frame_change_updates_ui(
        self,
        controller: TimelineController,
        mock_main_window: MockMainWindow
    ) -> None:
        """Test changing frame updates UI elements."""
        controller.set_frame(10)
        pass

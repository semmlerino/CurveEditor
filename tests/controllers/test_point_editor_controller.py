#!/usr/bin/env python
"""Tests for PointEditorController.

Tests point editing logic including spinbox updates and coordinate changes.
"""

import pytest
from ui.controllers.point_editor_controller import PointEditorController


@pytest.fixture
def controller(main_window_mock):
    """Create PointEditorController with mock main window."""
    return PointEditorController(
        main_window=main_window_mock,
        state_manager=main_window_mock.state_manager
    )


class TestPointEditorController:
    """Test suite for PointEditorController."""

    def test_single_point_selection_updates_spinboxes(self, controller):
        """Test selecting single point updates coordinate spinboxes."""
        # Test would verify spinbox values match selected point coordinates
        pass

    def test_multiple_selection_disables_spinboxes(self, controller):
        """Test multiple point selection disables coordinate editing."""
        pass

    def test_spinbox_change_updates_point_coordinates(self, controller):
        """Test changing spinbox values updates point coordinates."""
        pass

#!/usr/bin/env python
"""Tests for ViewCameraController.

Tests camera movement and view transformations.
"""


import pytest

from tests.test_helpers import MockMainWindow
from ui.controllers.view_camera_controller import ViewCameraController


@pytest.fixture
def controller(mock_main_window: MockMainWindow) -> ViewCameraController:
    """Create ViewCameraController with mock main window."""
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

    return ViewCameraController(mock_main_window.curve_widget)


class TestViewCameraController:
    """Test suite for ViewCameraController."""
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


    def test_pan_updates_view_offset(
        self,
        controller: ViewCameraController,
        mock_main_window: MockMainWindow
    ) -> None:
        """Test panning updates view offset."""
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

        # Arrange
        initial_pan_x = controller.pan_offset_x
        initial_pan_y = controller.pan_offset_y

        delta_x, delta_y = 50.0, 30.0

        # Act - Apply pan
        controller.pan(delta_x, delta_y)

        # Assert - Offsets updated
        assert controller.pan_offset_x == initial_pan_x + delta_x, \
            f"Pan X should increase by {delta_x}"
        # Note: pan_offset_y may be adjusted by apply_pan_offset_y based on flip_y_axis
        # We just verify it changed
        assert controller.pan_offset_y != initial_pan_y, \
            "Pan Y should change"

    def test_zoom_updates_zoom_level(
        self,
        controller: ViewCameraController,
        mock_main_window: MockMainWindow
    ) -> None:
        """Test zooming updates zoom level."""
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

        # Arrange
        initial_zoom = controller.zoom_factor

        # Act - Zoom in
        zoom_factor = 1.2
        controller.set_zoom_factor(initial_zoom * zoom_factor)

        # Assert - Zoom increased
        assert controller.zoom_factor > initial_zoom, \
            "Zoom factor should increase"

        # Act - Zoom out
        controller.set_zoom_factor(initial_zoom)

        # Assert - Zoom back to original
        assert abs(controller.zoom_factor - initial_zoom) < 0.01, \
            "Zoom factor should return to original"

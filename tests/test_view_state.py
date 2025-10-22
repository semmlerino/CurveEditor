#!/usr/bin/env python3
"""
Tests for the ViewState module.

This test suite verifies the functionality of the ViewState class,
which is an immutable class that encapsulates all parameters needed
for coordinate transformations in the application.
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

import os
import sys
from unittest.mock import MagicMock

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.transform_service import ViewState


class TestViewState:
    """Test suite for ViewState class."""

    @pytest.fixture
    def default_view_state(self) -> ViewState:
        """Create a default ViewState for testing."""
        return ViewState(display_width=1920, display_height=1080, widget_width=800, widget_height=600)

    def test_view_state_initialization(self, default_view_state: ViewState) -> None:
        """Test ViewState initialization with default values."""
        # Check required parameters
        assert default_view_state.display_width == 1920
        assert default_view_state.display_height == 1080
        assert default_view_state.widget_width == 800
        assert default_view_state.widget_height == 600

        # Check default values
        assert default_view_state.zoom_factor == 1.0
        assert default_view_state.offset_x == 0.0
        assert default_view_state.offset_y == 0.0
        assert default_view_state.scale_to_image is True
        assert default_view_state.flip_y_axis is False
        assert default_view_state.manual_x_offset == 0.0
        assert default_view_state.manual_y_offset == 0.0
        assert default_view_state.background_image is None
        assert default_view_state.image_width == 1920
        assert default_view_state.image_height == 1080

    def test_view_state_with_updates(self, default_view_state: ViewState) -> None:
        """Test creating a new ViewState with updated values."""
        # Update a few parameters
        updated_state = default_view_state.with_updates(
            zoom_factor=2.0, offset_x=100.0, offset_y=50.0, scale_to_image=False
        )

        # Check that updated values are changed
        assert updated_state.zoom_factor == 2.0
        assert updated_state.offset_x == 100.0
        assert updated_state.offset_y == 50.0
        assert updated_state.scale_to_image is False

        # Check that original values are unchanged (immutability)
        assert default_view_state.zoom_factor == 1.0
        assert default_view_state.offset_x == 0.0
        assert default_view_state.offset_y == 0.0
        assert default_view_state.scale_to_image is True

        # Check that other parameters are unchanged in the updated state
        assert updated_state.display_width == default_view_state.display_width
        assert updated_state.display_height == default_view_state.display_height
        assert updated_state.widget_width == default_view_state.widget_width
        assert updated_state.widget_height == default_view_state.widget_height

    def test_to_dict(self, default_view_state: ViewState) -> None:
        """Test converting ViewState to a dictionary."""
        state_dict = default_view_state.to_dict()

        # Check dictionary values
        assert state_dict["display_dimensions"] == (1920, 1080)
        assert state_dict["widget_dimensions"] == (800, 600)
        assert state_dict["image_dimensions"] == (1920, 1080)
        assert state_dict["zoom_factor"] == 1.0
        assert state_dict["offset"] == (0.0, 0.0)
        assert state_dict["scale_to_image"] is True
        assert state_dict["flip_y_axis"] is False
        assert state_dict["manual_offset"] == (0.0, 0.0)
        assert state_dict["has_background_image"] is False

    def test_from_curve_view(self) -> None:
        """Test creating ViewState from a CurveView."""
        # Create a mock CurveView
        mock_curve_view = MagicMock()
        mock_curve_view.width.return_value = 800
        mock_curve_view.height.return_value = 600
        mock_curve_view.image_width = 1920
        mock_curve_view.image_height = 1080
        mock_curve_view.zoom_factor = 2.0
        mock_curve_view.pan_offset_x = 50.0  # ViewState looks for pan_offset_x first
        mock_curve_view.pan_offset_y = 25.0  # ViewState looks for pan_offset_y first
        mock_curve_view.offset_x = 50.0  # Fallback value
        mock_curve_view.offset_y = 25.0  # Fallback value
        mock_curve_view.scale_to_image = True
        mock_curve_view.flip_y_axis = False
        mock_curve_view.manual_offset_x = 10.0  # ViewState looks for manual_offset_x first
        mock_curve_view.manual_offset_y = 15.0  # ViewState looks for manual_offset_y first
        mock_curve_view.x_offset = 10.0  # Fallback value
        mock_curve_view.y_offset = 15.0  # Fallback value
        mock_curve_view.background_image = None

        # Create ViewState from mock CurveView
        view_state = ViewState.from_curve_view(mock_curve_view)

        # Check values are correctly extracted
        assert view_state.display_width == 1920
        assert view_state.display_height == 1080
        assert view_state.widget_width == 800
        assert view_state.widget_height == 600
        assert view_state.zoom_factor == 2.0
        assert view_state.offset_x == 50.0
        assert view_state.offset_y == 25.0
        assert view_state.scale_to_image is True
        assert view_state.flip_y_axis is False
        assert view_state.manual_x_offset == 10.0
        assert view_state.manual_y_offset == 15.0
        assert view_state.background_image is None
        assert view_state.image_width == 1920
        assert view_state.image_height == 1080

    def test_from_curve_view_with_background_image(self) -> None:
        """Test creating ViewState from a CurveView with a background image."""
        # Create a mock CurveView with background image
        mock_curve_view = MagicMock()
        mock_curve_view.width.return_value = 800
        mock_curve_view.height.return_value = 600
        mock_curve_view.image_width = 1920
        mock_curve_view.image_height = 1080
        mock_curve_view.zoom_factor = 1.5  # Add proper zoom_factor value

        # Create a mock background image
        mock_background = MagicMock()
        mock_background.width.return_value = 2560
        mock_background.height.return_value = 1440
        mock_curve_view.background_image = mock_background

        # Create ViewState from mock CurveView
        view_state = ViewState.from_curve_view(mock_curve_view)

        # Check that display dimensions match background image dimensions
        assert view_state.display_width == 2560
        assert view_state.display_height == 1440
        # But image dimensions are unchanged
        assert view_state.image_width == 1920
        assert view_state.image_height == 1080
        # And background_image reference is set
        assert view_state.background_image is mock_background


if __name__ == "__main__":
    pytest.main(["-v", __file__])

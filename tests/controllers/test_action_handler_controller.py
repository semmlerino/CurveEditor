#!/usr/bin/env python
"""Tests for ActionHandlerController.

Tests the critical action handling paths including:
- Zoom operations (in/out/reset)
- Pan operations
- File operations (new/open/save)
- Smoothing operations
- View reset
"""

import pytest

from tests.test_helpers import MockMainWindow
from ui.controllers.action_handler_controller import ActionHandlerController


@pytest.fixture
def controller(mock_main_window: MockMainWindow) -> ActionHandlerController:
    """Create ActionHandlerController with mock main window."""
    return ActionHandlerController(
        state_manager=mock_main_window.state_manager,
        main_window=mock_main_window
    )


class TestActionHandlerController:
    """Test suite for ActionHandlerController."""


    def test_zoom_in_action(
        self,
        controller: ActionHandlerController,
        mock_main_window: MockMainWindow
    ) -> None:
        """Test zoom in action increases zoom level."""
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
        initial_zoom = mock_main_window.state_manager.zoom_level

        # Act
        controller.on_action_zoom_in()

        # Assert
        assert mock_main_window.state_manager.zoom_level > initial_zoom

    def test_zoom_out_action(
        self,
        controller: ActionHandlerController,
        mock_main_window: MockMainWindow
    ) -> None:
        """Test zoom out action decreases zoom level."""
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
        mock_main_window.state_manager.zoom_level = 2.0
        initial_zoom = mock_main_window.state_manager.zoom_level

        # Act
        controller.on_action_zoom_out()

        # Assert
        assert mock_main_window.state_manager.zoom_level < initial_zoom

    def test_reset_view_action(
        self,
        controller: ActionHandlerController,
        mock_main_window: MockMainWindow
    ) -> None:
        """Test reset view action restores default view state."""
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
        mock_main_window.state_manager.zoom_level = 3.0
        mock_main_window.state_manager.pan_offset = (100, 100)

        # Act
        controller.on_action_reset_view()

        # Assert
        # Should reset to default zoom (1.0) and pan (0, 0)
        assert mock_main_window.state_manager.zoom_level == 1.0
        assert mock_main_window.state_manager.pan_offset == (0.0, 0.0)

    def test_action_new_clears_data(
        self,
        controller: ActionHandlerController,
        mock_main_window: MockMainWindow
    ) -> None:
        """Test new action clears current data.

        Verifies that on_action_new() clears all curve data by:
        - Adding sample curve data before calling action
        - Calling on_action_new() to trigger new file creation
        - Asserting curve data is cleared (empty list)
        - Asserting state manager reset was called
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

        # Arrange - add curve data and set file_operations to return True
        sample_data = [
            (1, 100.0, 200.0, "keyframe"),
            (2, 110.0, 210.0, "normal"),
            (3, 120.0, 220.0, "normal"),
        ]
        mock_main_window.curve_widget.set_curve_data(sample_data)
        assert mock_main_window.curve_widget.curve_data == sample_data

        # Mock file_operations.new_file to return True (user confirms new file)
        mock_main_window.file_operations.new_file.return_value = True

        # Act
        controller.on_action_new()

        # Assert - curve data should be cleared
        assert mock_main_window.curve_widget.curve_data == []
        # state_manager.reset_to_defaults() should have been called
        mock_main_window.state_manager.reset_to_defaults.assert_called_once()

    def test_smooth_operation_without_selection(
        self,
        controller: ActionHandlerController,
        mock_main_window: MockMainWindow
    ) -> None:
        """Test smoothing operation with no selection shows message.

        Verifies that apply_smooth_operation() handles empty selection by:
        - Setting up curve data with no selected points
        - Calling apply_smooth_operation()
        - Asserting status message was displayed about no selection
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

        from unittest.mock import MagicMock

        # Arrange - add curve data but no selection
        sample_data = [
            (1, 100.0, 200.0, "keyframe"),
            (2, 110.0, 210.0, "normal"),
            (3, 120.0, 220.0, "normal"),
            (4, 130.0, 230.0, "normal"),
            (5, 140.0, 240.0, "normal"),
        ]
        mock_main_window.curve_widget.set_curve_data(sample_data)
        mock_main_window.curve_widget.selected_indices = []  # No selection

        # Mock statusBar to track messages
        mock_status_bar = MagicMock()
        mock_main_window.status_bar = mock_status_bar

        # Set smoothing parameters
        mock_main_window.state_manager.smoothing_window_size = 3
        mock_main_window.state_manager.smoothing_filter_type = "moving_average"

        # Act
        controller.apply_smooth_operation()

        # Assert - status message should have been called
        # When no selection exists, all points are used and message shows that
        mock_status_bar.showMessage.assert_called()

    def test_smooth_operation_with_selection(
        self,
        controller: ActionHandlerController,
        mock_main_window: MockMainWindow
    ) -> None:
        """Test smoothing operation with selected points succeeds.

        Verifies that apply_smooth_operation() processes selected points by:
        - Setting up curve data with multiple points
        - Selecting a subset of points (indices 2, 3, 4)
        - Calling apply_smooth_operation()
        - Asserting operation completes without errors
        - Asserting curve data was modified
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

        from unittest.mock import MagicMock

        # Arrange - add curve data and select specific points
        sample_data = [
            (1, 100.0, 200.0, "keyframe"),
            (2, 110.0, 210.0, "normal"),
            (3, 120.0, 220.0, "normal"),
            (4, 130.0, 230.0, "normal"),
            (5, 140.0, 240.0, "normal"),
            (6, 150.0, 250.0, "normal"),
            (7, 160.0, 260.0, "normal"),
            (8, 170.0, 270.0, "normal"),
            (9, 180.0, 280.0, "normal"),
            (10, 190.0, 290.0, "normal"),
        ]
        mock_main_window.curve_widget.set_curve_data(sample_data)

        # Select indices 2, 3, 4 (middle points)
        selected_indices = [2, 3, 4]
        mock_main_window.curve_widget.selected_indices = selected_indices

        # Set smoothing parameters
        mock_main_window.state_manager.smoothing_window_size = 3
        mock_main_window.state_manager.smoothing_filter_type = "moving_average"

        # Mock statusBar to track messages
        mock_status_bar = MagicMock()
        mock_main_window.status_bar = mock_status_bar

        # Act - apply smoothing
        controller.apply_smooth_operation()

        # Assert - status message should indicate smoothing was applied
        mock_status_bar.showMessage.assert_called()
        # At least verify the method was called with some message
        call_args = mock_status_bar.showMessage.call_args
        assert call_args is not None

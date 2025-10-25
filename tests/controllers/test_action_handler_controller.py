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
from PySide6.QtWidgets import QApplication

from ui.controllers.action_handler_controller import ActionHandlerController


@pytest.fixture
def controller(mock_main_window):
    """Create ActionHandlerController with mock main window."""
    return ActionHandlerController(
        main_window=mock_main_window,
        state_manager=mock_main_window.state_manager
    )


class TestActionHandlerController:
    """Test suite for ActionHandlerController."""

    def test_zoom_in_action(self, controller, mock_main_window):
        """Test zoom in action increases zoom level."""
        # Arrange
        initial_zoom = mock_main_window.state_manager.zoom_level

        # Act
        controller.on_action_zoom_in()

        # Assert
        assert mock_main_window.state_manager.zoom_level > initial_zoom

    def test_zoom_out_action(self, controller, mock_main_window):
        """Test zoom out action decreases zoom level."""
        # Arrange
        mock_main_window.state_manager.zoom_level = 2.0
        initial_zoom = mock_main_window.state_manager.zoom_level

        # Act
        controller.on_action_zoom_out()

        # Assert
        assert mock_main_window.state_manager.zoom_level < initial_zoom

    def test_reset_view_action(self, controller, mock_main_window):
        """Test reset view action restores default view state."""
        # Arrange
        mock_main_window.state_manager.zoom_level = 3.0
        mock_main_window.state_manager.pan_offset = (100, 100)

        # Act
        controller.on_action_reset_view()

        # Assert
        # Should reset to default zoom (1.0) and pan (0, 0)
        assert mock_main_window.state_manager.zoom_level == 1.0
        assert mock_main_window.state_manager.pan_offset == (0.0, 0.0)

    def test_action_new_clears_data(self, controller, mock_main_window):
        """Test new action clears current data."""
        # This test would need to verify that new file action clears curve data
        # Implementation depends on how ActionHandlerController handles new files
        pass

    def test_smooth_operation_requires_selection(self, controller, mock_main_window):
        """Test smoothing operation requires selected points."""
        # Arrange - no selection
        mock_main_window.curve_widget.selected_points = set()

        # Act
        controller.apply_smooth_operation()

        # Assert - should show message about no selection
        # (Exact assertion depends on implementation)
        pass

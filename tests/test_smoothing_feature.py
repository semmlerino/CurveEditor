#!/usr/bin/env python
"""
Comprehensive tests for the smoothing feature.

Tests the new immediate smoothing functionality with toolbar controls,
keyboard shortcuts, and different filter types.
Following UNIFIED_TESTING_GUIDE principles.
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QComboBox, QSpinBox

from ui.controllers.action_handler_controller import ActionHandlerController
from ui.keyboard_shortcuts import ShortcutManager
from ui.main_window import MainWindow
from ui.state_manager import StateManager


@pytest.fixture
def state_manager():
    """Create a StateManager instance for testing."""
    return StateManager()


@pytest.fixture
def mock_main_window(qtbot):
    """Create a mock MainWindow with necessary attributes."""
    window = Mock(spec=MainWindow)
    window.curve_widget = Mock()
    window.curve_widget.curve_data = [
        (1, 100.0, 200.0),
        (2, 150.0, 250.0),
        (3, 200.0, 300.0),
        (4, 250.0, 350.0),
        (5, 300.0, 400.0),
    ]
    window.curve_widget.selected_indices = []
    window.curve_widget.set_curve_data = Mock()
    window.statusBar = Mock(return_value=Mock(showMessage=Mock()))
    window.state_manager = StateManager()
    window.ui = Mock()
    window.ui.toolbar = Mock()
    window.ui.toolbar.smoothing_type_combo = None
    window.ui.toolbar.smoothing_size_spinbox = None
    return window


@pytest.fixture
def action_handler(mock_main_window):
    """Create an ActionHandlerController instance for testing."""
    return ActionHandlerController(mock_main_window.state_manager, mock_main_window)


class TestStateManagerSmoothingProperties:
    """Test StateManager smoothing properties."""

    def test_initial_smoothing_defaults(self, state_manager):
        """Test smoothing properties have correct default values."""
        assert state_manager.smoothing_window_size == 5
        assert state_manager.smoothing_filter_type == "moving_average"

    def test_smoothing_window_size_property(self, state_manager):
        """Test smoothing window size property setter and getter."""
        # Normal values
        state_manager.smoothing_window_size = 7
        assert state_manager.smoothing_window_size == 7

        state_manager.smoothing_window_size = 10
        assert state_manager.smoothing_window_size == 10

    def test_smoothing_window_size_clamping(self, state_manager):
        """Test smoothing window size is clamped to valid range."""
        # Test minimum clamping
        state_manager.smoothing_window_size = 1
        assert state_manager.smoothing_window_size == 3  # Clamped to minimum

        state_manager.smoothing_window_size = -5
        assert state_manager.smoothing_window_size == 3  # Clamped to minimum

        # Test maximum clamping
        state_manager.smoothing_window_size = 20
        assert state_manager.smoothing_window_size == 15  # Clamped to maximum

        state_manager.smoothing_window_size = 100
        assert state_manager.smoothing_window_size == 15  # Clamped to maximum

    def test_smoothing_filter_type_property(self, state_manager):
        """Test smoothing filter type property setter and getter."""
        # Valid types
        state_manager.smoothing_filter_type = "median"
        assert state_manager.smoothing_filter_type == "median"

        state_manager.smoothing_filter_type = "butterworth"
        assert state_manager.smoothing_filter_type == "butterworth"

        state_manager.smoothing_filter_type = "moving_average"
        assert state_manager.smoothing_filter_type == "moving_average"

    def test_invalid_filter_type_rejected(self, state_manager):
        """Test invalid filter types are rejected."""
        initial_type = state_manager.smoothing_filter_type

        # Try to set invalid types
        state_manager.smoothing_filter_type = "invalid_filter"
        assert state_manager.smoothing_filter_type == initial_type  # Should not change

        state_manager.smoothing_filter_type = ""
        assert state_manager.smoothing_filter_type == initial_type  # Should not change

        state_manager.smoothing_filter_type = "gaussian"  # Not supported
        assert state_manager.smoothing_filter_type == initial_type  # Should not change

    def test_reset_to_defaults_includes_smoothing(self, state_manager):
        """Test reset_to_defaults resets smoothing properties."""
        # Change smoothing properties
        state_manager.smoothing_window_size = 10
        state_manager.smoothing_filter_type = "median"

        # Reset
        state_manager.reset_to_defaults()

        # Check defaults restored
        assert state_manager.smoothing_window_size == 5
        assert state_manager.smoothing_filter_type == "moving_average"


class TestToolbarUIControls:
    """Test toolbar UI controls for smoothing."""

    @pytest.fixture
    def main_window(self, qtbot):
        """Create a real MainWindow for UI testing."""
        window = MainWindow()
        qtbot.addWidget(window)
        return window

    def test_toolbar_smoothing_controls_exist(self, main_window):
        """Test that smoothing controls are added to toolbar."""
        # Check combo box exists
        assert main_window.ui.toolbar.smoothing_type_combo is not None
        assert isinstance(main_window.ui.toolbar.smoothing_type_combo, QComboBox)

        # Check spinbox exists
        assert main_window.ui.toolbar.smoothing_size_spinbox is not None
        assert isinstance(main_window.ui.toolbar.smoothing_size_spinbox, QSpinBox)

    def test_smoothing_combo_box_items(self, main_window):
        """Test smoothing combo box has correct items."""
        combo = main_window.ui.toolbar.smoothing_type_combo
        items = [combo.itemText(i) for i in range(combo.count())]
        assert items == ["Moving Average", "Median", "Butterworth"]
        assert combo.currentIndex() == 0

    def test_smoothing_spinbox_range(self, main_window):
        """Test smoothing spinbox has correct range and default."""
        spinbox = main_window.ui.toolbar.smoothing_size_spinbox
        assert spinbox.minimum() == 3
        assert spinbox.maximum() == 15
        assert spinbox.value() == 5

    def test_combo_box_changes_state_manager(self, main_window, qtbot):
        """Test changing combo box updates state manager."""
        combo = main_window.ui.toolbar.smoothing_type_combo

        # Change to Median
        combo.setCurrentIndex(1)
        qtbot.wait(100)  # Allow signal processing
        assert main_window.state_manager.smoothing_filter_type == "median"

        # Change to Butterworth
        combo.setCurrentIndex(2)
        qtbot.wait(100)
        assert main_window.state_manager.smoothing_filter_type == "butterworth"

        # Change back to Moving Average
        combo.setCurrentIndex(0)
        qtbot.wait(100)
        assert main_window.state_manager.smoothing_filter_type == "moving_average"

    def test_spinbox_changes_state_manager(self, main_window, qtbot):
        """Test changing spinbox updates state manager."""
        spinbox = main_window.ui.toolbar.smoothing_size_spinbox

        # Change window size
        spinbox.setValue(7)
        qtbot.wait(100)
        assert main_window.state_manager.smoothing_window_size == 7

        spinbox.setValue(10)
        qtbot.wait(100)
        assert main_window.state_manager.smoothing_window_size == 10

        spinbox.setValue(3)
        qtbot.wait(100)
        assert main_window.state_manager.smoothing_window_size == 3


class TestSmoothingOperation:
    """Test the smoothing operation logic."""

    @patch("ui.controllers.action_handler_controller.get_data_service")
    @patch("services.get_interaction_service")
    def test_smoothing_with_selected_points(
        self, mock_get_interaction_service, mock_get_data_service, action_handler, mock_main_window
    ):
        """Test smoothing applies to selected points."""
        # Setup - Force fallback to legacy approach by disabling command system
        mock_get_interaction_service.return_value = None  # No interaction service = legacy fallback

        mock_main_window.curve_widget.selected_indices = [1, 2, 3]
        mock_data_service = Mock()
        mock_data_service.smooth_moving_average.return_value = [
            (2, 160.0, 260.0),
            (3, 210.0, 310.0),
            (4, 260.0, 360.0),
        ]
        mock_get_data_service.return_value = mock_data_service

        # Execute
        action_handler.apply_smooth_operation()

        # Verify
        mock_data_service.smooth_moving_average.assert_called_once()
        call_args = mock_data_service.smooth_moving_average.call_args
        assert len(call_args[0][0]) == 3  # 3 selected points
        assert call_args[0][1] == 5  # Default window size (positional arg)

        mock_main_window.curve_widget.set_curve_data.assert_called_once()
        assert mock_main_window.state_manager.is_modified is True

    @patch("ui.controllers.action_handler_controller.get_data_service")
    @patch("services.get_interaction_service")
    def test_smoothing_with_no_selection(
        self, mock_get_interaction_service, mock_get_data_service, action_handler, mock_main_window
    ):
        """Test smoothing applies to all points when none selected."""
        # Setup - Force fallback to legacy approach by disabling command system
        mock_get_interaction_service.return_value = None  # No interaction service = legacy fallback

        mock_main_window.curve_widget.selected_indices = []
        mock_data_service = Mock()
        mock_data_service.smooth_moving_average.return_value = [
            (1, 105.0, 205.0),
            (2, 155.0, 255.0),
            (3, 205.0, 305.0),
            (4, 255.0, 355.0),
            (5, 305.0, 405.0),
        ]
        mock_get_data_service.return_value = mock_data_service

        # Execute
        action_handler.apply_smooth_operation()

        # Verify all points were smoothed
        mock_data_service.smooth_moving_average.assert_called_once()
        call_args = mock_data_service.smooth_moving_average.call_args
        assert len(call_args[0][0]) == 5  # All points

        status_bar = mock_main_window.statusBar()
        status_bar.showMessage.assert_any_call("No selection - smoothing all points", 2000)

    @patch("ui.controllers.action_handler_controller.get_data_service")
    @patch("services.get_interaction_service")
    def test_smoothing_with_median_filter(
        self, mock_get_interaction_service, mock_get_data_service, action_handler, mock_main_window
    ):
        """Test smoothing with median filter type."""
        # Setup - Force fallback to legacy approach by disabling command system
        mock_get_interaction_service.return_value = None  # No interaction service = legacy fallback

        mock_main_window.state_manager.smoothing_filter_type = "median"
        mock_main_window.curve_widget.selected_indices = [0, 1]
        mock_data_service = Mock()
        mock_data_service.filter_median.return_value = [
            (1, 100.0, 200.0),
            (2, 150.0, 250.0),
        ]
        mock_get_data_service.return_value = mock_data_service

        # Execute
        action_handler.apply_smooth_operation()

        # Verify median filter was used
        mock_data_service.filter_median.assert_called_once()
        assert not mock_data_service.smooth_moving_average.called

    @patch("ui.controllers.action_handler_controller.get_data_service")
    @patch("services.get_interaction_service")
    def test_smoothing_with_butterworth_filter(
        self, mock_get_interaction_service, mock_get_data_service, action_handler, mock_main_window
    ):
        """Test smoothing with butterworth filter type."""
        # Setup - Force fallback to legacy approach by disabling command system
        mock_get_interaction_service.return_value = None  # No interaction service = legacy fallback

        mock_main_window.state_manager.smoothing_filter_type = "butterworth"
        mock_main_window.state_manager.smoothing_window_size = 8
        mock_main_window.curve_widget.selected_indices = [2, 3]
        mock_data_service = Mock()
        mock_data_service.filter_butterworth.return_value = [
            (3, 200.0, 300.0),
            (4, 250.0, 350.0),
        ]
        mock_get_data_service.return_value = mock_data_service

        # Execute
        action_handler.apply_smooth_operation()

        # Verify butterworth filter was used with correct order
        mock_data_service.filter_butterworth.assert_called_once()
        call_args = mock_data_service.filter_butterworth.call_args
        assert "order" in call_args[1]  # Check it's passed as keyword
        assert call_args[1]["order"] == 4  # window_size // 2

    def test_smoothing_with_no_curve_widget(self, action_handler, mock_main_window):
        """Test smoothing handles missing curve widget gracefully."""
        mock_main_window.curve_widget = None

        # Should return early without errors
        action_handler.apply_smooth_operation()

        # Status bar should not be called for error message
        mock_main_window.statusBar.assert_not_called()

    def test_smoothing_with_empty_curve_data(self, action_handler, mock_main_window):
        """Test smoothing handles empty curve data gracefully."""
        mock_main_window.curve_widget.curve_data = []

        # Execute
        action_handler.apply_smooth_operation()

        # Verify proper handling
        status_bar = mock_main_window.statusBar()
        status_bar.showMessage.assert_called_with("No curve data to smooth", 2000)
        mock_main_window.curve_widget.set_curve_data.assert_not_called()

    @patch("ui.controllers.action_handler_controller.get_data_service")
    @patch("services.get_interaction_service")
    def test_smoothing_with_custom_window_size(
        self, mock_get_interaction_service, mock_get_data_service, action_handler, mock_main_window
    ):
        """Test smoothing uses custom window size from state manager."""
        # Setup - Force fallback to legacy approach by disabling command system
        mock_get_interaction_service.return_value = None  # No interaction service = legacy fallback

        mock_main_window.state_manager.smoothing_window_size = 11
        mock_main_window.curve_widget.selected_indices = [0]
        mock_data_service = Mock()
        mock_data_service.smooth_moving_average.return_value = [(1, 100.0, 200.0)]
        mock_get_data_service.return_value = mock_data_service

        # Execute
        action_handler.apply_smooth_operation()

        # Verify custom window size was used
        call_args = mock_data_service.smooth_moving_average.call_args
        assert call_args[0][1] == 11  # Window size as positional arg

    @patch("ui.controllers.action_handler_controller.get_data_service")
    def test_smoothing_status_message(self, mock_get_data_service, action_handler, mock_main_window):
        """Test smoothing shows correct status message."""
        # Setup
        mock_main_window.curve_widget.selected_indices = [0, 1, 2]
        mock_main_window.state_manager.smoothing_filter_type = "median"
        mock_main_window.state_manager.smoothing_window_size = 7
        mock_data_service = Mock()
        mock_data_service.filter_median.return_value = [
            (1, 100.0, 200.0),
            (2, 150.0, 250.0),
            (3, 200.0, 300.0),
        ]
        mock_get_data_service.return_value = mock_data_service

        # Execute
        action_handler.apply_smooth_operation()

        # Verify status message
        status_bar = mock_main_window.statusBar()
        status_bar.showMessage.assert_any_call("Applied Median smoothing to 3 points (size: 7)", 3000)


class TestKeyboardShortcut:
    """Test keyboard shortcut integration."""

    def test_ctrl_e_shortcut_configured(self):
        """Test Ctrl+E is configured for smooth curve action."""
        shortcut_manager = ShortcutManager()
        assert shortcut_manager.action_smooth_curve.shortcut().toString() == "Ctrl+E"
        assert shortcut_manager.action_smooth_curve.statusTip() == "Apply smoothing to selected points"

    def test_ctrl_shift_e_for_export(self):
        """Test Ctrl+Shift+E is configured for export (moved from Ctrl+E)."""
        shortcut_manager = ShortcutManager()
        assert shortcut_manager.action_export_data.shortcut().toString() == "Ctrl+Shift+E"
        assert shortcut_manager.action_export_data.statusTip() == "Export curve data"

    @pytest.fixture
    def main_window_with_data(self, qtbot):
        """Create a MainWindow with test data."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Add some test data
        if window.curve_widget:
            test_data = [
                (1, 100.0, 200.0),
                (2, 150.0, 250.0),
                (3, 200.0, 300.0),
            ]
            window.curve_widget.set_curve_data(test_data)

        return window

    @patch("ui.controllers.action_handler_controller.get_data_service")
    @patch("services.get_interaction_service")
    def test_ctrl_e_triggers_smoothing(
        self, mock_get_interaction_service, mock_get_data_service, main_window_with_data, qtbot
    ):
        """Test pressing Ctrl+E triggers smoothing operation."""
        # Setup - Force fallback to legacy approach by disabling command system
        mock_get_interaction_service.return_value = None  # No interaction service = legacy fallback

        # Setup mock data service
        mock_data_service = Mock()
        mock_data_service.smooth_moving_average.return_value = [
            (1, 105.0, 205.0),
            (2, 155.0, 255.0),
            (3, 205.0, 305.0),
        ]
        mock_get_data_service.return_value = mock_data_service

        # Trigger the action directly (simulating keyboard shortcut)
        main_window_with_data.shortcut_manager.action_smooth_curve.trigger()
        qtbot.wait(100)

        # Verify smoothing was called
        mock_data_service.smooth_moving_average.assert_called_once()


class TestIntegration:
    """Test integration between components."""

    @pytest.fixture
    def integrated_window(self, qtbot):
        """Create a fully integrated MainWindow."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Add test data
        if window.curve_widget:
            test_data = [
                (1, 100.0, 200.0),
                (2, 150.0, 250.0),
                (3, 200.0, 300.0),
                (4, 250.0, 350.0),
                (5, 300.0, 400.0),
            ]
            window.curve_widget.set_curve_data(test_data)

        return window

    def test_toolbar_to_smoothing_flow(self, integrated_window, qtbot):
        """Test complete flow from toolbar changes to smoothing operation."""
        # Change toolbar controls
        integrated_window.ui.toolbar.smoothing_type_combo.setCurrentIndex(1)  # Median
        integrated_window.ui.toolbar.smoothing_size_spinbox.setValue(7)
        qtbot.wait(100)

        # Verify state manager updated
        assert integrated_window.state_manager.smoothing_filter_type == "median"
        assert integrated_window.state_manager.smoothing_window_size == 7

        # Select some points using the widget's selection mechanism
        if integrated_window.curve_widget:
            # Use the private method since there's no public setter
            integrated_window.curve_widget._select_point(1, False)
            integrated_window.curve_widget._select_point(2, True)  # Add to selection
            integrated_window.curve_widget._select_point(3, True)  # Add to selection

        # Mock the data service to verify correct parameters are used
        with (
            patch("ui.controllers.action_handler_controller.get_data_service") as mock_get_service,
            patch("services.get_interaction_service") as mock_get_interaction_service,
        ):
            # Force fallback to legacy approach by disabling command system
            mock_get_interaction_service.return_value = None

            mock_service = Mock()
            mock_service.filter_median.return_value = [
                (2, 155.0, 255.0),
                (3, 205.0, 305.0),
                (4, 255.0, 355.0),
            ]
            mock_get_service.return_value = mock_service

            # Trigger smoothing
            integrated_window.shortcut_manager.action_smooth_curve.trigger()
            qtbot.wait(100)

            # Verify median filter was used with correct window size
            mock_service.filter_median.assert_called_once()
            call_args = mock_service.filter_median.call_args
            assert call_args[0][1] == 7  # Window size as positional arg

    def test_smoothing_preserves_unselected_points(self, integrated_window, qtbot):
        """Test that smoothing only affects selected points."""
        if not integrated_window.curve_widget:
            pytest.skip("No curve widget available")

        # Select middle points only
        integrated_window.curve_widget._select_point(1, False)
        integrated_window.curve_widget._select_point(2, True)
        integrated_window.curve_widget._select_point(3, True)
        original_data = list(integrated_window.curve_widget.curve_data)

        with (
            patch("ui.controllers.action_handler_controller.get_data_service") as mock_get_service,
            patch("services.get_interaction_service") as mock_get_interaction_service,
        ):
            # Force fallback to legacy approach by disabling command system
            mock_get_interaction_service.return_value = None

            mock_service = Mock()
            # Return smoothed versions of selected points
            mock_service.smooth_moving_average.return_value = [
                (2, 160.0, 260.0),  # Smoothed
                (3, 210.0, 310.0),  # Smoothed
                (4, 260.0, 360.0),  # Smoothed
            ]
            mock_get_service.return_value = mock_service

            # Apply smoothing
            integrated_window.shortcut_manager.action_smooth_curve.trigger()
            qtbot.wait(100)

            # Verify only selected points were passed to smooth function
            call_args = mock_service.smooth_moving_average.call_args
            passed_points = call_args[0][0]
            assert len(passed_points) == 3
            assert passed_points == [original_data[1], original_data[2], original_data[3]]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

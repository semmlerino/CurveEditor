#!/usr/bin/env python
"""
Comprehensive test suite for UIService following UNIFIED_TESTING_GUIDE.

Tests ALL public methods per the Protocol Method Testing Rule to prevent
bugs in unused methods (like the timeline oscillation bug).
"""

from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QDialog, QInputDialog, QMainWindow, QMessageBox, QPushButton, QWidget

from services.ui_service import UIService


class MockMainWindow(QMainWindow):
    """Real Qt MainWindow with test attributes for status bar testing."""

    def __init__(self):
        super().__init__()
        # Required attributes per MainWindowProtocol
        self.history = []
        self.history_index = -1
        self.curve_data = []
        self.selected_indices = []
        self.is_modified = False

        # Optional UI components
        self.undo_button = QPushButton("Undo")
        self.redo_button = QPushButton("Redo")
        self.save_button = QPushButton("Save")
        self.delete_button = QPushButton("Delete")
        self.update_point_button = QPushButton("Update")
        self.duplicate_button = QPushButton("Duplicate")

        # Initialize status bar
        self.statusBar()  # Creates status bar if not exists


@pytest.fixture
def ui_service():
    """Create UIService instance."""
    return UIService()


@pytest.fixture
def parent_widget(qtbot):
    """Create a real Qt widget for dialog parent."""
    widget = QWidget()
    qtbot.addWidget(widget)
    return widget


@pytest.fixture
def main_window(qtbot):
    """Create a real MainWindow for status bar testing."""
    window = MockMainWindow()
    qtbot.addWidget(window)
    return window


class TestDialogMethods:
    """Test all dialog input methods following UNIFIED_TESTING_GUIDE patterns."""

    def test_get_smooth_window_size_accepted(self, ui_service, parent_widget, monkeypatch):
        """Test getting smooth window size when user accepts."""
        # Mock QInputDialog.getInt per UNIFIED_TESTING_GUIDE pattern
        monkeypatch.setattr(QInputDialog, "getInt", lambda *args: (7, True))

        result = ui_service.get_smooth_window_size(parent_widget)

        assert result == 7  # Test behavior, not implementation

    def test_get_smooth_window_size_cancelled(self, ui_service, parent_widget, monkeypatch):
        """Test getting smooth window size when user cancels."""
        monkeypatch.setattr(QInputDialog, "getInt", lambda *args: (0, False))

        result = ui_service.get_smooth_window_size(parent_widget)

        assert result is None

    def test_get_filter_params_median_accepted(self, ui_service, parent_widget, monkeypatch):
        """Test getting median filter params when accepted."""
        # First dialog returns filter type
        # Second dialog returns window size
        call_count = [0]

        def mock_dialog(*args):
            call_count[0] += 1
            if call_count[0] == 1:
                return ("Median", True)  # getItem for filter type
            else:
                return (7, True)  # getInt for window size

        monkeypatch.setattr(QInputDialog, "getItem", lambda *args: ("Median", True))
        monkeypatch.setattr(QInputDialog, "getInt", lambda *args: (7, True))

        result = ui_service.get_filter_params(parent_widget)

        assert result == ("Median", 7)

    def test_get_filter_params_butterworth_accepted(self, ui_service, parent_widget, monkeypatch):
        """Test getting butterworth filter params when accepted."""
        monkeypatch.setattr(QInputDialog, "getItem", lambda *args: ("Butterworth", True))
        monkeypatch.setattr(QInputDialog, "getDouble", lambda *args: (0.25, True))

        result = ui_service.get_filter_params(parent_widget)

        assert result == ("Butterworth", 25)  # 0.25 * 100

    def test_get_filter_params_cancelled(self, ui_service, parent_widget, monkeypatch):
        """Test getting filter params when user cancels."""
        monkeypatch.setattr(QInputDialog, "getItem", lambda *args: ("", False))

        result = ui_service.get_filter_params(parent_widget)

        assert result is None

    def test_get_offset_values_accepted(self, ui_service, parent_widget, monkeypatch):
        """Test getting offset values when user accepts both dialogs."""
        call_count = [0]
        values = [10.5, 20.3]

        def mock_double(*args):
            idx = call_count[0]
            call_count[0] += 1
            return (values[idx], True)

        monkeypatch.setattr(QInputDialog, "getDouble", mock_double)

        result = ui_service.get_offset_values(parent_widget)

        assert result == (10.5, 20.3)

    def test_get_offset_values_cancelled_first(self, ui_service, parent_widget, monkeypatch):
        """Test getting offset values when user cancels first dialog."""
        monkeypatch.setattr(QInputDialog, "getDouble", lambda *args: (0.0, False))

        result = ui_service.get_offset_values(parent_widget)

        assert result is None

    def test_get_offset_values_cancelled_second(self, ui_service, parent_widget, monkeypatch):
        """Test getting offset values when user cancels second dialog."""
        call_count = [0]

        def mock_double(*args):
            call_count[0] += 1
            if call_count[0] == 1:
                return (10.0, True)
            else:
                return (0.0, False)

        monkeypatch.setattr(QInputDialog, "getDouble", mock_double)

        result = ui_service.get_offset_values(parent_widget)

        assert result is None

    def test_get_fill_gaps_size_accepted(self, ui_service, parent_widget, monkeypatch):
        """Test getting fill gaps size when accepted."""
        monkeypatch.setattr(QInputDialog, "getInt", lambda *args: (15, True))

        result = ui_service.get_fill_gaps_size(parent_widget)

        assert result == 15

    def test_get_fill_gaps_size_cancelled(self, ui_service, parent_widget, monkeypatch):
        """Test getting fill gaps size when cancelled."""
        monkeypatch.setattr(QInputDialog, "getInt", lambda *args: (0, False))

        result = ui_service.get_fill_gaps_size(parent_widget)

        assert result is None

    def test_get_scale_values_accepted(self, ui_service, parent_widget, monkeypatch):
        """Test getting scale values when both accepted."""
        call_count = [0]
        values = [2.0, 3.5]

        def mock_double(*args):
            idx = call_count[0]
            call_count[0] += 1
            return (values[idx], True)

        monkeypatch.setattr(QInputDialog, "getDouble", mock_double)

        result = ui_service.get_scale_values(parent_widget)

        assert result == (2.0, 3.5)

    def test_get_text_input_accepted(self, ui_service, parent_widget, monkeypatch):
        """Test getting text input when accepted."""
        monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("test text", True))

        result = ui_service.get_text_input(parent_widget, "Title", "Label", "default")

        assert result == "test text"

    def test_get_text_input_cancelled(self, ui_service, parent_widget, monkeypatch):
        """Test getting text input when cancelled."""
        monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: ("", False))

        result = ui_service.get_text_input(parent_widget, "Title", "Label")

        assert result is None

    def test_get_integer_input_with_range(self, ui_service, parent_widget, monkeypatch):
        """Test getting integer input with custom range."""
        monkeypatch.setattr(QInputDialog, "getInt", lambda *args: (50, True))

        result = ui_service.get_integer_input(parent_widget, "Title", "Label", 25, 0, 100)

        assert result == 50

    def test_get_float_input_with_decimals(self, ui_service, parent_widget, monkeypatch):
        """Test getting float input with decimal places."""
        monkeypatch.setattr(QInputDialog, "getDouble", lambda *args: (3.14159, True))

        result = ui_service.get_float_input(parent_widget, "Title", "Label", 0.0, -10.0, 10.0, 5)

        assert result == 3.14159

    def test_get_choice_accepted(self, ui_service, parent_widget, monkeypatch):
        """Test getting choice from list when accepted."""
        monkeypatch.setattr(QInputDialog, "getItem", lambda *args: ("Option B", True))

        result = ui_service.get_choice(parent_widget, "Title", "Label", ["Option A", "Option B", "Option C"], 1)

        assert result == "Option B"

    def test_get_choice_cancelled(self, ui_service, parent_widget, monkeypatch):
        """Test getting choice when cancelled."""
        monkeypatch.setattr(QInputDialog, "getItem", lambda *args: ("", False))

        result = ui_service.get_choice(parent_widget, "Title", "Label", ["A", "B"])

        assert result is None


class TestMessageBoxMethods:
    """Test all message box methods."""

    def test_show_error(self, ui_service, parent_widget, monkeypatch):
        """Test showing error message."""
        mock_critical = Mock(return_value=QMessageBox.StandardButton.Ok)
        monkeypatch.setattr(QMessageBox, "critical", mock_critical)

        ui_service.show_error(parent_widget, "Error message", "Error Title")

        # Verify behavior - dialog was shown with correct params
        mock_critical.assert_called_once_with(parent_widget, "Error Title", "Error message")

    def test_show_warning(self, ui_service, parent_widget, monkeypatch):
        """Test showing warning message."""
        mock_warning = Mock(return_value=QMessageBox.StandardButton.Ok)
        monkeypatch.setattr(QMessageBox, "warning", mock_warning)

        ui_service.show_warning(parent_widget, "Warning message")

        mock_warning.assert_called_once_with(parent_widget, "Warning", "Warning message")

    def test_show_info(self, ui_service, parent_widget, monkeypatch):
        """Test showing info message."""
        mock_info = Mock(return_value=QMessageBox.StandardButton.Ok)
        monkeypatch.setattr(QMessageBox, "information", mock_info)

        ui_service.show_info(parent_widget, "Info message", "Custom Title")

        mock_info.assert_called_once_with(parent_widget, "Custom Title", "Info message")

    def test_confirm_action_yes(self, ui_service, parent_widget, monkeypatch):
        """Test confirm action when user clicks Yes."""
        monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Yes)

        result = ui_service.confirm_action(parent_widget, "Are you sure?")

        assert result is True

    def test_confirm_action_no(self, ui_service, parent_widget, monkeypatch):
        """Test confirm action when user clicks No."""
        monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.No)

        result = ui_service.confirm_action(parent_widget, "Are you sure?")

        assert result is False

    def test_show_about_default_message(self, ui_service, parent_widget, monkeypatch):
        """Test showing about dialog with default message."""
        mock_about = Mock()
        monkeypatch.setattr(QMessageBox, "about", mock_about)

        ui_service.show_about(parent_widget)

        mock_about.assert_called_once()
        # Check that default message is used
        call_args = mock_about.call_args[0]
        assert "CurveEditor Application" in call_args[2]
        assert "Version 1.0.0" in call_args[2]

    def test_show_about_custom_message(self, ui_service, parent_widget, monkeypatch):
        """Test showing about dialog with custom message."""
        mock_about = Mock()
        monkeypatch.setattr(QMessageBox, "about", mock_about)

        ui_service.show_about(parent_widget, "Custom About", "Custom message")

        mock_about.assert_called_once_with(parent_widget, "Custom About", "Custom message")


class TestStatusBarMethods:
    """Test all status bar methods."""

    def test_set_status_permanent(self, ui_service, main_window):
        """Test setting permanent status message."""
        ui_service.set_status(main_window, "Permanent message", 0)

        # Test behavior - status bar shows message
        assert main_window.statusBar().currentMessage() == "Permanent message"

    def test_set_status_temporary(self, ui_service, main_window):
        """Test setting temporary status message."""
        ui_service.set_status(main_window, "Temp message", 3000)

        assert main_window.statusBar().currentMessage() == "Temp message"

    def test_clear_status(self, ui_service, main_window):
        """Test clearing status bar."""
        # First set a message
        ui_service.set_status(main_window, "Message")
        assert main_window.statusBar().currentMessage() == "Message"

        # Then clear it
        ui_service.clear_status(main_window)

        assert main_window.statusBar().currentMessage() == ""

    def test_set_permanent_status(self, ui_service, main_window):
        """Test set_permanent_status helper method."""
        ui_service.set_permanent_status(main_window, "Permanent")

        assert main_window.statusBar().currentMessage() == "Permanent"

    def test_set_temporary_status(self, ui_service, main_window):
        """Test set_temporary_status helper method."""
        ui_service.set_temporary_status(main_window, "Temporary", 5000)

        assert main_window.statusBar().currentMessage() == "Temporary"

    def test_show_status_message_alias(self, ui_service, main_window):
        """Test show_status_message is an alias for set_temporary_status."""
        ui_service.show_status_message(main_window, "Status message")

        assert main_window.statusBar().currentMessage() == "Status message"


class TestUIStateManagement:
    """Test UI state management methods."""

    def test_enable_ui_components(self, ui_service, main_window):
        """Test enabling/disabling UI components."""
        # Disable components
        ui_service.enable_ui_components(main_window, ["undo_button", "redo_button"], False)

        assert main_window.undo_button.isEnabled() is False
        assert main_window.redo_button.isEnabled() is False

        # Enable components
        ui_service.enable_ui_components(main_window, ["undo_button"], True)

        assert main_window.undo_button.isEnabled() is True

    def test_enable_ui_components_missing_component(self, ui_service, main_window):
        """Test enabling components when some don't exist."""
        # Should not raise error for non-existent components
        ui_service.enable_ui_components(main_window, ["nonexistent_button", "undo_button"], True)

        assert main_window.undo_button.isEnabled() is True

    def test_update_button_states(self, ui_service, main_window):
        """Test updating button states based on app state."""
        # Setup state for testing
        main_window.history = [{"data": []}, {"data": []}, {"data": []}]
        main_window.history_index = 1
        main_window.curve_data = [(1, 2.0, 3.0)]
        main_window.selected_indices = [0]

        ui_service.update_button_states(main_window)

        # Verify behavior based on state
        assert main_window.undo_button.isEnabled() is True  # history_index > 0
        assert main_window.redo_button.isEnabled() is True  # history_index < len(history) - 1
        assert main_window.save_button.isEnabled() is True  # curve_data not empty
        assert main_window.delete_button.isEnabled() is True  # has selection

    def test_update_button_states_empty_state(self, ui_service, main_window):
        """Test button states with empty data."""
        main_window.history = []
        main_window.history_index = -1
        main_window.curve_data = []
        main_window.selected_indices = []

        ui_service.update_button_states(main_window)

        assert main_window.undo_button.isEnabled() is False
        assert main_window.redo_button.isEnabled() is False
        assert main_window.save_button.isEnabled() is False
        assert main_window.delete_button.isEnabled() is False

    def test_update_window_title_default(self, ui_service, main_window):
        """Test updating window title with default."""
        ui_service.update_window_title(main_window)

        assert main_window.windowTitle() == "CurveEditor"

    def test_update_window_title_custom(self, ui_service, main_window):
        """Test updating window title with custom title."""
        ui_service.update_window_title(main_window, "CurveEditor - file.txt")

        assert main_window.windowTitle() == "CurveEditor - file.txt"

    def test_update_window_title_modified(self, ui_service, main_window):
        """Test updating window title with modified indicator."""
        ui_service.update_window_title(main_window, "CurveEditor", modified=True)

        assert main_window.windowTitle() == "*CurveEditor"

    def test_show_progress_indeterminate(self, ui_service, main_window):
        """Test showing indeterminate progress."""
        ui_service.show_progress(main_window, "Loading", -1)

        assert "Loading..." in main_window.statusBar().currentMessage()

    def test_show_progress_percentage(self, ui_service, main_window):
        """Test showing progress with percentage."""
        ui_service.show_progress(main_window, "Processing", 50, 100)

        assert "Processing (50%)" in main_window.statusBar().currentMessage()

    def test_update_ui_from_data(self, ui_service, main_window):
        """Test updating UI from data state."""
        main_window.curve_data = [(1, 2.0, 3.0), (2, 3.0, 4.0)]
        main_window.is_modified = True

        ui_service.update_ui_from_data(main_window)

        # Check status shows point count
        assert "2 points loaded" in main_window.statusBar().currentMessage()
        # Check title shows modified
        assert main_window.windowTitle().startswith("*")

    def test_create_context_menu(self, ui_service, parent_widget):
        """Test creating context menu with actions."""
        callback1 = Mock()
        callback2 = Mock()

        actions = {
            "Action 1": callback1,
            "-": None,  # Separator
            "Action 2": callback2,
            "Action 3": None,  # No callback
        }

        menu = ui_service.create_context_menu(parent_widget, actions)

        # Verify menu structure
        assert menu is not None
        assert menu.actions()[0].text() == "Action 1"
        assert menu.actions()[1].isSeparator()
        assert menu.actions()[2].text() == "Action 2"
        assert menu.actions()[3].text() == "Action 3"


class TestComplexDialogs:
    """Test complex dialog methods."""

    def test_show_filter_dialog_not_implemented(self, ui_service, parent_widget, monkeypatch):
        """Test filter dialog shows not implemented message."""
        mock_info = Mock()
        monkeypatch.setattr(QMessageBox, "information", mock_info)

        data = [(1, 2.0, 3.0)]
        indices = [0]
        result = ui_service.show_filter_dialog(parent_widget, data, indices)

        assert result is None
        mock_info.assert_called_once()
        assert "not yet implemented" in mock_info.call_args[0][2]

    def test_show_fill_gaps_dialog_not_implemented(self, ui_service, parent_widget, monkeypatch):
        """Test fill gaps dialog shows not implemented message."""
        mock_info = Mock()
        monkeypatch.setattr(QMessageBox, "information", mock_info)

        data = [(1, 2.0, 3.0)]
        gaps = [(5, 10)]
        result = ui_service.show_fill_gaps_dialog(parent_widget, data, gaps)

        assert result is None
        mock_info.assert_called_once()

    def test_show_extrapolate_dialog_not_implemented(self, ui_service, parent_widget, monkeypatch):
        """Test extrapolate dialog shows not implemented message."""
        mock_info = Mock()
        monkeypatch.setattr(QMessageBox, "information", mock_info)

        data = [(1, 2.0, 3.0)]
        result = ui_service.show_extrapolate_dialog(parent_widget, data)

        assert result is None
        mock_info.assert_called_once()

    def test_show_shortcuts_dialog(self, ui_service, parent_widget, monkeypatch):
        """Test showing keyboard shortcuts dialog."""
        # Mock QDialog.exec to prevent blocking per UNIFIED_TESTING_GUIDE
        monkeypatch.setattr(QDialog, "exec", lambda self: QDialog.DialogCode.Accepted)

        # Should not raise error
        ui_service.show_shortcuts_dialog(parent_widget)

        # Test with non-widget parent
        ui_service.show_shortcuts_dialog(None)
        ui_service.show_shortcuts_dialog("not a widget")


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error conditions per UNIFIED_TESTING_GUIDE."""

    def test_none_parent_handling(self, ui_service, monkeypatch):
        """Test methods handle None parent gracefully."""
        # Mock the dialog to prevent actual UI from showing
        monkeypatch.setattr(QInputDialog, "getInt", lambda *args: (5, True))

        # Should handle None parent without crashing
        result = ui_service.get_smooth_window_size(None)

        # Qt dialogs accept None as parent, so this should work
        assert result == 5

    def test_empty_choices_list(self, ui_service, parent_widget, monkeypatch):
        """Test get_choice with empty choices list."""
        monkeypatch.setattr(QInputDialog, "getItem", lambda *args: ("", False))

        result = ui_service.get_choice(parent_widget, "Title", "Label", [])

        assert result is None

    def test_invalid_component_names(self, ui_service, main_window):
        """Test enable_ui_components with invalid names."""
        # Should handle gracefully
        ui_service.enable_ui_components(main_window, ["", None, 123, "valid_name"], True)

        # No exception raised

    def test_progress_zero_maximum(self, ui_service, main_window):
        """Test show_progress with zero maximum."""
        ui_service.show_progress(main_window, "Progress", 50, 0)

        # Should not divide by zero
        assert "Progress (0%)" in main_window.statusBar().currentMessage()


class TestProtocolCompliance:
    """Ensure all public methods are tested per Protocol Method Testing Rule."""

    def test_all_public_methods_have_tests(self, ui_service):
        """Verify every public method of UIService has at least one test."""
        import inspect

        # Get all public methods
        public_methods = [
            name
            for name, method in inspect.getmembers(ui_service, predicate=inspect.ismethod)
            if not name.startswith("_")
        ]

        # These are all the methods we've tested above
        tested_methods = {
            "get_smooth_window_size",
            "get_filter_params",
            "get_offset_values",
            "get_fill_gaps_size",
            "get_scale_values",
            "get_text_input",
            "get_integer_input",
            "get_float_input",
            "get_choice",
            "show_error",
            "show_warning",
            "show_info",
            "confirm_action",
            "show_about",
            "show_status_message",
            "set_status",
            "clear_status",
            "set_permanent_status",
            "set_temporary_status",
            "enable_ui_components",
            "update_button_states",
            "update_window_title",
            "show_progress",
            "update_ui_from_data",
            "create_context_menu",
            "show_filter_dialog",
            "show_fill_gaps_dialog",
            "show_extrapolate_dialog",
            "show_shortcuts_dialog",
        }

        # Verify all public methods are tested
        for method in public_methods:
            assert method in tested_methods, f"Method {method} is not tested!"

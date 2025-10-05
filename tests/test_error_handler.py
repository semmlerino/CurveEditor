#!/usr/bin/env python3
"""
Tests for error handling system - comprehensive error management.

This test module provides comprehensive coverage of the error handling system,
testing error categorization, dialog creation, exception handling, and recovery.
Follows the testing guide patterns for Qt components and error handling.
"""

from unittest.mock import Mock

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qt_compat import qt_api

from ui.error_handler import (
    ErrorCategory,
    ErrorDialog,
    ErrorHandler,
    ErrorInfo,
    ErrorSeverity,
    get_error_handler,
)


@pytest.fixture(scope="session")
def qapp():
    """Shared QApplication for all tests."""
    app = QApplication.instance() or QApplication([])
    yield app
    app.processEvents()


class TestErrorSeverity:
    """Test ErrorSeverity enum."""

    def test_enum_values(self):
        """Test that all severity levels exist."""
        assert ErrorSeverity.INFO
        assert ErrorSeverity.WARNING
        assert ErrorSeverity.ERROR
        assert ErrorSeverity.CRITICAL

    def test_enum_ordering(self):
        """Test that severity levels can be compared."""
        # Each severity should have a unique value
        severities = [ErrorSeverity.INFO, ErrorSeverity.WARNING, ErrorSeverity.ERROR, ErrorSeverity.CRITICAL]
        values = [s.value for s in severities]
        assert len(set(values)) == len(values)  # All unique


class TestErrorCategory:
    """Test ErrorCategory enum."""

    def test_enum_values(self):
        """Test that all category values exist."""
        assert ErrorCategory.FILE_IO
        assert ErrorCategory.DATA_VALIDATION
        assert ErrorCategory.RENDERING
        assert ErrorCategory.MEMORY
        assert ErrorCategory.PERMISSION
        assert ErrorCategory.NETWORK
        assert ErrorCategory.USER_INPUT
        assert ErrorCategory.SYSTEM
        assert ErrorCategory.UNKNOWN

    def test_enum_completeness(self):
        """Test that all expected categories are present."""
        categories = list(ErrorCategory)
        assert len(categories) == 9  # Expected number of categories


class TestErrorInfo:
    """Test ErrorInfo dataclass."""

    def test_minimal_creation(self):
        """Test ErrorInfo creation with minimal parameters."""
        error_info = ErrorInfo(title="Test Error", message="Test message")

        assert error_info.title == "Test Error"
        assert error_info.message == "Test message"
        assert error_info.details == ""
        assert error_info.severity == ErrorSeverity.ERROR
        assert error_info.category == ErrorCategory.UNKNOWN
        assert error_info.recovery_suggestions is None
        assert error_info.exception is None
        assert error_info.show_details is True
        assert error_info.can_retry is False
        assert error_info.can_ignore is False

    def test_full_creation(self):
        """Test ErrorInfo creation with all parameters."""
        suggestions = ["Try again", "Check settings"]
        exception = ValueError("Test exception")

        error_info = ErrorInfo(
            title="Critical Error",
            message="Something went wrong",
            details="Detailed error information",
            severity=ErrorSeverity.CRITICAL,
            category=ErrorCategory.FILE_IO,
            recovery_suggestions=suggestions,
            exception=exception,
            show_details=False,
            can_retry=True,
            can_ignore=True,
        )

        assert error_info.title == "Critical Error"
        assert error_info.message == "Something went wrong"
        assert error_info.details == "Detailed error information"
        assert error_info.severity == ErrorSeverity.CRITICAL
        assert error_info.category == ErrorCategory.FILE_IO
        assert error_info.recovery_suggestions == suggestions
        assert error_info.exception is exception
        assert error_info.show_details is False
        assert error_info.can_retry is True
        assert error_info.can_ignore is True

    def test_defaults_preserved(self):
        """Test that default values work correctly."""
        error_info = ErrorInfo(
            title="Test",
            message="Message",
            severity=ErrorSeverity.WARNING,
            category=ErrorCategory.MEMORY,
        )

        # Defaults should be preserved
        assert error_info.details == ""
        assert error_info.recovery_suggestions is None
        assert error_info.exception is None
        assert error_info.show_details is True
        assert error_info.can_retry is False
        assert error_info.can_ignore is False


class TestErrorDialog:
    """Test ErrorDialog class."""

    def test_dialog_creation_minimal(self, qtbot):
        """Test creating error dialog with minimal error info."""
        error_info = ErrorInfo(title="Test Error", message="Test message")

        dialog = ErrorDialog(error_info)
        qtbot.addWidget(dialog)

        assert dialog.error_info is error_info
        assert dialog.windowTitle() == "Test Error"

    def test_dialog_creation_with_suggestions(self, qtbot):
        """Test creating dialog with recovery suggestions."""
        suggestions = ["Try option A", "Try option B"]
        error_info = ErrorInfo(
            title="Error with suggestions",
            message="Something failed",
            recovery_suggestions=suggestions,
        )

        dialog = ErrorDialog(error_info)
        qtbot.addWidget(dialog)

        assert dialog.error_info.recovery_suggestions == suggestions

    def test_dialog_creation_with_details(self, qtbot):
        """Test creating dialog with details and exception."""
        exception = ValueError("Test exception")
        error_info = ErrorInfo(
            title="Error with details",
            message="Something failed",
            details="Extra details",
            exception=exception,
            show_details=True,
        )

        dialog = ErrorDialog(error_info)
        qtbot.addWidget(dialog)

        # Details should be available
        assert hasattr(dialog, "details_button")
        assert hasattr(dialog, "details_text")

    def test_dialog_with_action_buttons(self, qtbot):
        """Test dialog with retry and ignore buttons."""
        error_info = ErrorInfo(
            title="Actionable Error",
            message="You can retry or ignore this",
            can_retry=True,
            can_ignore=True,
        )

        dialog = ErrorDialog(error_info)
        qtbot.addWidget(dialog)

        # Should have button box
        assert hasattr(dialog, "button_box")

    def test_dialog_signals_exist(self, qtbot):
        """Test that dialog has required signals."""
        error_info = ErrorInfo(title="Test", message="Test", can_retry=True)

        dialog = ErrorDialog(error_info)
        qtbot.addWidget(dialog)

        # Check signals exist
        assert hasattr(dialog, "retry_requested")
        assert hasattr(dialog, "ignore_requested")

    def test_details_toggle_functionality(self, qtbot):
        """Test details section toggle."""
        error_info = ErrorInfo(
            title="Test",
            message="Test",
            details="Some details",
            show_details=True,
        )

        dialog = ErrorDialog(error_info)
        qtbot.addWidget(dialog)

        # Verify details section exists
        assert hasattr(dialog, "details_button"), "Details button should exist"
        assert hasattr(dialog, "details_text"), "Details text should exist"

        # Initially details should be hidden
        assert dialog.details_text.isHidden()
        assert "Show Details" in dialog.details_button.text()
        assert not dialog.details_button.isChecked()

        # Show the dialog to make sure it's visible (required for proper visibility testing)
        dialog.show()
        qtbot.waitExposed(dialog)

        # Toggle details
        dialog._toggle_details(True)

        # Details should now be visible
        assert dialog.details_text.isVisible()
        assert "Hide Details" in dialog.details_button.text()

        # Toggle back
        dialog._toggle_details(False)

        # Details should be hidden again
        assert dialog.details_text.isHidden()
        assert "Show Details" in dialog.details_button.text()

    def test_retry_signal_emission(self, qtbot):
        """Test retry signal is emitted correctly."""
        error_info = ErrorInfo(title="Test", message="Test", can_retry=True)

        dialog = ErrorDialog(error_info)
        qtbot.addWidget(dialog)

        # Set up signal spy
        retry_spy = qt_api.QtTest.QSignalSpy(dialog.retry_requested)

        # Simulate retry action
        dialog._on_retry()

        # Verify signal was emitted
        assert retry_spy.count() == 1

    def test_ignore_signal_emission(self, qtbot):
        """Test ignore signal is emitted correctly."""
        error_info = ErrorInfo(title="Test", message="Test", can_ignore=True)

        dialog = ErrorDialog(error_info)
        qtbot.addWidget(dialog)

        # Set up signal spy
        ignore_spy = qt_api.QtTest.QSignalSpy(dialog.ignore_requested)

        # Simulate ignore action
        dialog._on_ignore()

        # Verify signal was emitted
        assert ignore_spy.count() == 1


class TestErrorHandler:
    """Test ErrorHandler class."""

    @pytest.fixture
    def error_handler(self):
        """Create fresh ErrorHandler instance for testing."""
        return ErrorHandler()

    def test_error_handler_creation(self, error_handler):
        """Test ErrorHandler can be created."""
        assert error_handler.error_history == []
        assert error_handler.max_history_size == 100
        assert error_handler.recovery_actions is not None
        assert len(error_handler.recovery_actions) > 0

    def test_recovery_actions_exist(self, error_handler):
        """Test that recovery actions are defined for key categories."""
        # Check that important categories have recovery actions
        assert ErrorCategory.FILE_IO in error_handler.recovery_actions
        assert ErrorCategory.DATA_VALIDATION in error_handler.recovery_actions
        assert ErrorCategory.RENDERING in error_handler.recovery_actions
        assert ErrorCategory.MEMORY in error_handler.recovery_actions
        assert ErrorCategory.PERMISSION in error_handler.recovery_actions

        # Check that actions are non-empty lists
        for category, actions in error_handler.recovery_actions.items():
            assert isinstance(actions, list)
            assert len(actions) > 0
            assert all(isinstance(action, str) for action in actions)

    def test_categorize_exception_file_errors(self, error_handler):
        """Test exception categorization for file errors."""
        # File not found
        file_error = FileNotFoundError("File not found")
        category = error_handler._categorize_exception(file_error)
        assert category == ErrorCategory.FILE_IO

        # IO Error
        io_error = OSError("IO error")
        category = error_handler._categorize_exception(io_error)
        assert category == ErrorCategory.FILE_IO

        # OS Error
        os_error = OSError("OS error")
        category = error_handler._categorize_exception(os_error)
        assert category == ErrorCategory.FILE_IO

    def test_categorize_exception_permission_error(self, error_handler):
        """Test exception categorization for permission errors."""
        perm_error = PermissionError("Permission denied")
        category = error_handler._categorize_exception(perm_error)
        assert category == ErrorCategory.PERMISSION

    def test_categorize_exception_memory_error(self, error_handler):
        """Test exception categorization for memory errors."""
        mem_error = MemoryError("Out of memory")
        category = error_handler._categorize_exception(mem_error)
        assert category == ErrorCategory.MEMORY

    def test_categorize_exception_by_message(self, error_handler):
        """Test exception categorization based on error message."""
        # File-related messages
        file_ex = ValueError("Cannot open file")
        assert error_handler._categorize_exception(file_ex) == ErrorCategory.FILE_IO

        # Data validation messages
        data_ex = ValueError("Invalid format")
        assert error_handler._categorize_exception(data_ex) == ErrorCategory.DATA_VALIDATION

        # Rendering messages
        render_ex = RuntimeError("Failed to render")
        assert error_handler._categorize_exception(render_ex) == ErrorCategory.RENDERING

        # Permission messages
        perm_ex = RuntimeError("Access denied")
        assert error_handler._categorize_exception(perm_ex) == ErrorCategory.PERMISSION

    def test_categorize_exception_unknown(self, error_handler):
        """Test unknown exception categorization."""
        unknown_ex = ValueError("Some random error")
        category = error_handler._categorize_exception(unknown_ex)
        assert category == ErrorCategory.UNKNOWN

    def test_determine_severity_critical(self, error_handler):
        """Test severity determination for critical errors."""
        # System errors are critical
        sys_error = SystemError("System failure")
        severity = error_handler._determine_severity(sys_error)
        assert severity == ErrorSeverity.CRITICAL

        # Memory errors are critical
        mem_error = MemoryError("Out of memory")
        severity = error_handler._determine_severity(mem_error)
        assert severity == ErrorSeverity.CRITICAL

    def test_determine_severity_regular(self, error_handler):
        """Test severity determination for regular errors."""
        # Most exceptions are ERROR level
        value_error = ValueError("Invalid value")
        severity = error_handler._determine_severity(value_error)
        assert severity == ErrorSeverity.ERROR

        runtime_error = RuntimeError("Runtime issue")
        severity = error_handler._determine_severity(runtime_error)
        assert severity == ErrorSeverity.ERROR

    def test_create_user_message_file_io(self, error_handler):
        """Test user message creation for file I/O errors."""
        # File not found
        file_error = FileNotFoundError("test.txt not found")
        message = error_handler._create_user_message(file_error, ErrorCategory.FILE_IO)
        assert "file could not be found" in message.lower()

        # Permission in message
        perm_error = OSError("Permission denied")
        message = error_handler._create_user_message(perm_error, ErrorCategory.FILE_IO)
        assert "permission denied" in message.lower()

        # Generic file error
        io_error = OSError("Disk full")
        message = error_handler._create_user_message(io_error, ErrorCategory.FILE_IO)
        assert "error occurred while accessing" in message.lower()

    def test_create_user_message_other_categories(self, error_handler):
        """Test user message creation for other error categories."""
        exception = ValueError("Test")

        # Data validation
        message = error_handler._create_user_message(exception, ErrorCategory.DATA_VALIDATION)
        assert "data format" in message.lower()

        # Memory
        message = error_handler._create_user_message(exception, ErrorCategory.MEMORY)
        assert "memory" in message.lower()

        # Permission
        message = error_handler._create_user_message(exception, ErrorCategory.PERMISSION)
        assert "permission" in message.lower()

        # Rendering
        message = error_handler._create_user_message(exception, ErrorCategory.RENDERING)
        assert "rendering" in message.lower()

        # Unknown
        message = error_handler._create_user_message(exception, ErrorCategory.UNKNOWN)
        assert "unexpected error" in message.lower()

    def test_log_error_history(self, error_handler):
        """Test error logging to history."""
        error_info = ErrorInfo(title="Test", message="Test error")

        error_handler._log_error(error_info)

        assert len(error_handler.error_history) == 1
        assert error_handler.error_history[0] is error_info

    def test_log_error_history_trimming(self, error_handler):
        """Test error history trimming when max size exceeded."""
        # Set small max size for testing
        error_handler.max_history_size = 3

        # Add more errors than max size
        for i in range(5):
            error_info = ErrorInfo(title=f"Error {i}", message=f"Message {i}")
            error_handler._log_error(error_info)

        # Should only keep the last 3
        assert len(error_handler.error_history) == 3
        assert error_handler.error_history[0].title == "Error 2"
        assert error_handler.error_history[1].title == "Error 3"
        assert error_handler.error_history[2].title == "Error 4"

    def test_log_error_signal_emission(self, error_handler):
        """Test that error logging emits signals."""
        error_info = ErrorInfo(title="Test", message="Test error", severity=ErrorSeverity.WARNING)

        # Set up signal spy
        spy = qt_api.QtTest.QSignalSpy(error_handler.error_logged)

        error_handler._log_error(error_info)

        # Verify signal was emitted
        assert spy.count() == 1
        assert spy.at(0)[0] == "Test error"
        assert spy.at(0)[1] == ErrorSeverity.WARNING

    def test_show_error_method(self, error_handler, qtbot, monkeypatch):
        """Test show_error method."""
        # Mock the dialog to avoid actual UI
        mock_show_dialog = Mock(return_value=False)
        monkeypatch.setattr(error_handler, "show_error_dialog", mock_show_dialog)

        error_handler.show_error("Test message", "Test Title", "Test details")

        # Verify dialog was called
        mock_show_dialog.assert_called_once()

        # Check error was logged
        assert len(error_handler.error_history) == 1
        logged_error = error_handler.error_history[0]
        assert logged_error.title == "Test Title"
        assert logged_error.message == "Test message"
        assert logged_error.details == "Test details"
        assert logged_error.severity == ErrorSeverity.ERROR

    def test_show_warning_method(self, error_handler, monkeypatch):
        """Test show_warning method."""
        # Mock QMessageBox to avoid actual UI
        mock_warning = Mock()
        monkeypatch.setattr("ui.error_handler.QMessageBox.warning", mock_warning)

        error_handler.show_warning("Warning message", "Warning Title")

        # Verify QMessageBox was called
        mock_warning.assert_called_once()

        # Check error was logged
        assert len(error_handler.error_history) == 1
        logged_error = error_handler.error_history[0]
        assert logged_error.title == "Warning Title"
        assert logged_error.message == "Warning message"
        assert logged_error.severity == ErrorSeverity.WARNING

    def test_show_info_method(self, error_handler, monkeypatch):
        """Test show_info method."""
        # Mock QMessageBox to avoid actual UI
        mock_info = Mock()
        monkeypatch.setattr("ui.error_handler.QMessageBox.information", mock_info)

        error_handler.show_info("Info message", "Info Title")

        # Verify QMessageBox was called
        mock_info.assert_called_once()

    def test_handle_exception_method(self, error_handler, qtbot, monkeypatch):
        """Test handle_exception method."""
        # Mock show_error_dialog to avoid actual UI
        mock_show_dialog = Mock(return_value=True)  # Return True for retry
        monkeypatch.setattr(error_handler, "show_error_dialog", mock_show_dialog)

        exception = FileNotFoundError("test.txt not found")
        result = error_handler.handle_exception(
            exception,
            title="File Error",
            can_retry=True,
            can_ignore=True,
        )

        # Should return True (retry requested)
        assert result is True

        # Verify dialog was called with correct error info
        mock_show_dialog.assert_called_once()

        # Check error was logged
        assert len(error_handler.error_history) == 1
        logged_error = error_handler.error_history[0]
        assert logged_error.title == "File Error"
        assert logged_error.category == ErrorCategory.FILE_IO
        assert logged_error.exception is exception
        assert logged_error.can_retry is True
        assert logged_error.can_ignore is True

    def test_show_error_dialog_retry(self, error_handler, qtbot, monkeypatch):
        """Test show_error_dialog with retry action."""
        # Mock dialog to simulate user clicking retry
        mock_dialog = Mock()
        mock_dialog.exec.return_value = None

        # Mock the dialog class
        def mock_dialog_constructor(error_info, parent=None):
            mock_dialog.retry_requested = Mock()
            mock_dialog.retry_requested.connect = Mock()
            return mock_dialog

        monkeypatch.setattr("ui.error_handler.ErrorDialog", mock_dialog_constructor)

        error_info = ErrorInfo(title="Test", message="Test", can_retry=True)
        error_handler.show_error_dialog(error_info)

        # Dialog should have been created and shown
        mock_dialog.exec.assert_called_once()


class TestErrorHandlerSingleton:
    """Test ErrorHandler singleton pattern."""

    def test_get_error_handler_singleton(self):
        """Test that get_error_handler returns the same instance."""
        handler1 = get_error_handler()
        handler2 = get_error_handler()

        assert handler1 is handler2
        assert isinstance(handler1, ErrorHandler)

    def test_get_error_handler_creates_instance(self):
        """Test that get_error_handler creates instance if none exists."""
        # Clear the global instance
        import ui.error_handler

        ui.error_handler._error_handler = None

        handler = get_error_handler()

        assert handler is not None
        assert isinstance(handler, ErrorHandler)

        # Cleanup
        ui.error_handler._error_handler = None


class TestErrorHandlerIntegration:
    """Integration tests for error handler components."""

    def test_full_error_handling_flow(self, qtbot, monkeypatch):
        """Test complete error handling flow from exception to dialog."""
        # Create handler
        handler = ErrorHandler()

        # Mock logger to avoid actual logging
        mock_logger = Mock()
        monkeypatch.setattr("ui.error_handler.logger", mock_logger)

        # Mock dialog to avoid actual UI
        mock_show_dialog = Mock(return_value=False)
        monkeypatch.setattr(handler, "show_error_dialog", mock_show_dialog)

        # Create and handle exception
        exception = ValueError("Invalid data format")
        result = handler.handle_exception(exception, "Data Error", can_retry=True)

        # Verify the flow
        assert result is False  # No retry requested
        assert len(handler.error_history) == 1

        # Check logged error properties
        logged_error = handler.error_history[0]
        assert logged_error.title == "Data Error"
        assert logged_error.category == ErrorCategory.DATA_VALIDATION
        assert logged_error.severity == ErrorSeverity.ERROR
        assert logged_error.exception is exception
        assert logged_error.can_retry is True

        # Verify dialog was shown
        mock_show_dialog.assert_called_once()

    def test_error_categorization_comprehensive(self):
        """Test comprehensive error categorization scenarios."""
        handler = ErrorHandler()

        test_cases = [
            (FileNotFoundError("missing.txt"), ErrorCategory.FILE_IO),
            (PermissionError("access denied"), ErrorCategory.PERMISSION),
            (MemoryError("out of memory"), ErrorCategory.MEMORY),
            (ValueError("cannot parse file"), ErrorCategory.FILE_IO),
            (RuntimeError("invalid format"), ErrorCategory.DATA_VALIDATION),
            (Exception("failed to render"), ErrorCategory.RENDERING),
            (ValueError("permission denied in message"), ErrorCategory.PERMISSION),
            (RuntimeError("unknown issue"), ErrorCategory.UNKNOWN),
        ]

        for exception, expected_category in test_cases:
            category = handler._categorize_exception(exception)
            assert (
                category == expected_category
            ), f"Failed for {exception}: expected {expected_category}, got {category}"

    def test_severity_and_message_consistency(self):
        """Test that severity and message creation work consistently."""
        handler = ErrorHandler()

        # Test critical errors
        critical_exceptions = [SystemError("system failure"), MemoryError("out of memory")]
        for exception in critical_exceptions:
            severity = handler._determine_severity(exception)
            assert severity == ErrorSeverity.CRITICAL

        # Test regular errors
        regular_exceptions = [ValueError("invalid"), RuntimeError("runtime issue"), OSError("io problem")]
        for exception in regular_exceptions:
            severity = handler._determine_severity(exception)
            assert severity == ErrorSeverity.ERROR

    def test_recovery_suggestions_mapping(self):
        """Test that error categories have appropriate recovery suggestions."""
        handler = ErrorHandler()

        # File I/O suggestions should mention files/permissions
        file_suggestions = handler.recovery_actions[ErrorCategory.FILE_IO]
        assert any("file" in suggestion.lower() for suggestion in file_suggestions)
        assert any("permission" in suggestion.lower() for suggestion in file_suggestions)

        # Memory suggestions should mention memory/applications
        memory_suggestions = handler.recovery_actions[ErrorCategory.MEMORY]
        assert any("memory" in suggestion.lower() for suggestion in memory_suggestions)
        assert any("application" in suggestion.lower() for suggestion in memory_suggestions)

        # Data validation suggestions should mention format/data
        data_suggestions = handler.recovery_actions[ErrorCategory.DATA_VALIDATION]
        assert any("data" in suggestion.lower() or "format" in suggestion.lower() for suggestion in data_suggestions)

#!/usr/bin/env python
"""
Error Handler for CurveEditor.

Provides user-friendly error messages, recovery suggestions, and logging
for better user experience when errors occur.
"""

import traceback
from dataclasses import dataclass
from enum import Enum, auto

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from core.logger_utils import get_logger

logger = get_logger("error_handler")


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    INFO = auto()
    WARNING = auto()
    ERROR = auto()
    CRITICAL = auto()


class ErrorCategory(Enum):
    """Categories of errors for better handling."""

    FILE_IO = auto()
    DATA_VALIDATION = auto()
    RENDERING = auto()
    MEMORY = auto()
    PERMISSION = auto()
    NETWORK = auto()
    USER_INPUT = auto()
    SYSTEM = auto()
    UNKNOWN = auto()


@dataclass
class ErrorInfo:
    """Information about an error."""

    title: str
    message: str
    details: str = ""
    severity: ErrorSeverity = ErrorSeverity.ERROR
    category: ErrorCategory = ErrorCategory.UNKNOWN
    recovery_suggestions: list[str] | None = None
    exception: Exception | None = None
    show_details: bool = True
    can_retry: bool = False
    can_ignore: bool = False


class ErrorDialog(QDialog):
    """Enhanced error dialog with recovery suggestions."""

    # Signals
    retry_requested: Signal = Signal()
    ignore_requested: Signal = Signal()

    def __init__(self, error_info: ErrorInfo, parent: QWidget | None = None):
        """Initialize the error dialog."""
        super().__init__(parent)

        self.error_info: ErrorInfo = error_info
        self.setWindowTitle(error_info.title)
        self.setMinimumWidth(500)

        # Create UI
        self._create_ui()

        # Apply styling based on severity
        self._apply_styling()

    def _create_ui(self) -> None:
        """Create the dialog UI."""
        layout = QVBoxLayout()

        # Icon and message layout
        message_layout = QHBoxLayout()

        # Add icon based on severity
        icon_label = QLabel()
        icon_label.setPixmap(self._get_icon_pixmap())
        icon_label.setMaximumSize(48, 48)
        message_layout.addWidget(icon_label)

        # Main message
        message_label = QLabel(self.error_info.message)
        message_label.setWordWrap(True)
        message_label.setMinimumWidth(400)

        # Make critical errors bold
        if self.error_info.severity == ErrorSeverity.CRITICAL:
            font = message_label.font()
            font.setBold(True)
            message_label.setFont(font)

        message_layout.addWidget(message_label)
        message_layout.addStretch()

        layout.addLayout(message_layout)

        # Recovery suggestions
        if self.error_info.recovery_suggestions:
            layout.addSpacing(10)
            suggestions_label = QLabel("<b>Suggestions:</b>")
            layout.addWidget(suggestions_label)

            for suggestion in self.error_info.recovery_suggestions:
                sugg_label = QLabel(f"• {suggestion}")
                sugg_label.setWordWrap(True)
                sugg_label.setIndent(20)
                layout.addWidget(sugg_label)

        # Details section (collapsible)
        if self.error_info.show_details and (self.error_info.details or self.error_info.exception):
            layout.addSpacing(10)

            # Details button
            self.details_button: QPushButton = QPushButton("Show Details ▼")
            self.details_button.setCheckable(True)
            _ = self.details_button.clicked.connect(self._toggle_details)
            layout.addWidget(self.details_button)

            # Details text area
            self.details_text: QTextEdit = QTextEdit()
            self.details_text.setReadOnly(True)
            self.details_text.setMaximumHeight(200)

            # Populate details
            details_content = ""
            if self.error_info.details:
                details_content += self.error_info.details + "\n\n"

            if self.error_info.exception:
                details_content += "Exception Details:\n"
                details_content += f"Type: {type(self.error_info.exception).__name__}\n"
                details_content += f"Message: {str(self.error_info.exception)}\n\n"
                details_content += "Traceback:\n"
                details_content += traceback.format_exc()

            self.details_text.setPlainText(details_content)
            self.details_text.hide()
            layout.addWidget(self.details_text)

        # Button box
        layout.addSpacing(10)
        self.button_box: QDialogButtonBox = QDialogButtonBox()

        # Add buttons based on options
        if self.error_info.can_retry:
            retry_button = self.button_box.addButton("Retry", QDialogButtonBox.ButtonRole.ActionRole)
            _ = retry_button.clicked.connect(self._on_retry)

        if self.error_info.can_ignore:
            ignore_button = self.button_box.addButton("Ignore", QDialogButtonBox.ButtonRole.ActionRole)
            _ = ignore_button.clicked.connect(self._on_ignore)

        # Always add OK button
        ok_button = self.button_box.addButton(QDialogButtonBox.StandardButton.Ok)
        _ = ok_button.clicked.connect(self.accept)
        ok_button.setDefault(True)

        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def _get_icon_pixmap(self) -> QPixmap:
        """Get icon pixmap based on severity."""
        style = self.style()

        if self.error_info.severity == ErrorSeverity.INFO:
            icon = style.standardIcon(style.StandardPixmap.SP_MessageBoxInformation)
        elif self.error_info.severity == ErrorSeverity.WARNING:
            icon = style.standardIcon(style.StandardPixmap.SP_MessageBoxWarning)
        elif self.error_info.severity == ErrorSeverity.CRITICAL:
            icon = style.standardIcon(style.StandardPixmap.SP_MessageBoxCritical)
        else:  # ERROR
            icon = style.standardIcon(style.StandardPixmap.SP_MessageBoxCritical)

        return icon.pixmap(48, 48)

    def _apply_styling(self) -> None:
        """Apply styling based on severity."""
        # Could add custom stylesheets here based on severity
        pass

    def _toggle_details(self, checked: bool) -> None:
        """Toggle the details section."""
        if checked:
            self.details_text.show()
            self.details_button.setText("Hide Details ▲")
            # Resize dialog to fit details
            self.adjustSize()
        else:
            self.details_text.hide()
            self.details_button.setText("Show Details ▼")
            # Resize dialog
            self.adjustSize()

    def _on_retry(self) -> None:
        """Handle retry button click."""
        self.retry_requested.emit()
        self.accept()

    def _on_ignore(self) -> None:
        """Handle ignore button click."""
        self.ignore_requested.emit()
        self.accept()


class ErrorHandler(QObject):
    """Centralized error handling for the application."""

    # Signals
    error_occurred: Signal = Signal(ErrorInfo)
    error_logged: Signal = Signal(str, ErrorSeverity)

    def __init__(self, parent: QObject | None = None):
        """Initialize the error handler."""
        super().__init__(parent)

        # Error history for debugging
        self.error_history: list[ErrorInfo] = []
        self.max_history_size: int = 100

        # Recovery actions
        self.recovery_actions: dict[ErrorCategory, list[str]] = {
            ErrorCategory.FILE_IO: [
                "Check if the file exists and is accessible",
                "Verify you have read/write permissions",
                "Ensure the file is not open in another application",
                "Check available disk space",
            ],
            ErrorCategory.DATA_VALIDATION: [
                "Review the data format requirements",
                "Check for missing or invalid values",
                "Ensure data is within expected ranges",
                "Try loading a different file",
            ],
            ErrorCategory.RENDERING: [
                "Try resetting the view (View → Reset View)",
                "Reduce the number of points displayed",
                "Check graphics driver updates",
                "Restart the application",
            ],
            ErrorCategory.MEMORY: [
                "Close other applications to free memory",
                "Reduce the size of the dataset",
                "Save your work and restart the application",
                "Check system memory usage",
            ],
            ErrorCategory.PERMISSION: [
                "Run the application with appropriate permissions",
                "Check file and folder permissions",
                "Ensure you have access to the resource",
                "Contact your system administrator",
            ],
            ErrorCategory.USER_INPUT: [
                "Check the input format",
                "Ensure values are within valid ranges",
                "Review the input requirements",
                "Use the example format shown",
            ],
        }

    def handle_exception(
        self,
        exception: Exception,
        title: str = "Error",
        parent: QWidget | None = None,
        can_retry: bool = False,
        can_ignore: bool = False,
    ) -> bool:
        """Handle an exception with user-friendly dialog.

        Args:
            exception: The exception that occurred
            title: Dialog title
            parent: Parent widget for the dialog
            can_retry: Whether retry option should be shown
            can_ignore: Whether ignore option should be shown

        Returns:
            True if user chose to retry, False otherwise
        """
        # Categorize the error
        category = self._categorize_exception(exception)
        severity = self._determine_severity(exception)

        # Create user-friendly message
        user_message = self._create_user_message(exception, category)

        # Get recovery suggestions
        suggestions = self.recovery_actions.get(category, [])

        # Create error info
        error_info = ErrorInfo(
            title=title,
            message=user_message,
            details=str(exception),
            severity=severity,
            category=category,
            recovery_suggestions=suggestions,
            exception=exception,
            can_retry=can_retry,
            can_ignore=can_ignore,
        )

        # Log the error
        self._log_error(error_info)

        # Show dialog
        return self.show_error_dialog(error_info, parent)

    def show_error_dialog(self, error_info: ErrorInfo, parent: QWidget | None = None) -> bool:
        """Show error dialog to user.

        Returns:
            True if user chose to retry, False otherwise
        """
        dialog = ErrorDialog(error_info, parent)

        # Track retry request
        retry_requested = False

        def on_retry():
            nonlocal retry_requested
            retry_requested = True

        _ = dialog.retry_requested.connect(on_retry)

        # Show dialog
        _ = dialog.exec()

        return retry_requested

    def show_error(self, message: str, title: str = "Error", details: str = "", parent: QWidget | None = None) -> None:
        """Show a simple error message."""
        error_info = ErrorInfo(
            title=title, message=message, details=details, severity=ErrorSeverity.ERROR, show_details=bool(details)
        )

        self._log_error(error_info)
        _ = self.show_error_dialog(error_info, parent)

    def show_warning(self, message: str, title: str = "Warning", parent: QWidget | None = None) -> None:
        """Show a warning message."""
        error_info = ErrorInfo(title=title, message=message, severity=ErrorSeverity.WARNING, show_details=False)

        self._log_error(error_info)
        _ = QMessageBox.warning(parent, title, message)

    def show_info(self, message: str, title: str = "Information", parent: QWidget | None = None) -> None:
        """Show an information message."""
        _ = ErrorInfo(title=title, message=message, severity=ErrorSeverity.INFO, show_details=False)

        _ = QMessageBox.information(parent, title, message)

    def _categorize_exception(self, exception: Exception) -> ErrorCategory:
        """Categorize an exception for better handling."""
        type(exception).__name__
        exc_msg = str(exception).lower()

        # Permission errors (check before OSError since PermissionError inherits from OSError)
        if isinstance(exception, PermissionError):
            return ErrorCategory.PERMISSION

        # File I/O errors
        if isinstance(exception, IOError | OSError | FileNotFoundError):
            return ErrorCategory.FILE_IO

        # Memory errors
        if isinstance(exception, MemoryError):
            return ErrorCategory.MEMORY

        # Check message for clues
        if any(word in exc_msg for word in ["file", "path", "directory", "cannot open", "cannot read"]):
            return ErrorCategory.FILE_IO

        if any(word in exc_msg for word in ["invalid", "format", "parse", "convert"]):
            return ErrorCategory.DATA_VALIDATION

        if any(word in exc_msg for word in ["render", "draw", "paint", "display"]):
            return ErrorCategory.RENDERING

        if any(word in exc_msg for word in ["permission", "denied", "access"]):
            return ErrorCategory.PERMISSION

        return ErrorCategory.UNKNOWN

    def _determine_severity(self, exception: Exception) -> ErrorSeverity:
        """Determine error severity from exception."""
        # Critical errors
        if isinstance(exception, SystemError | SystemExit):
            return ErrorSeverity.CRITICAL

        # Memory errors are critical
        if isinstance(exception, MemoryError):
            return ErrorSeverity.CRITICAL

        # Most exceptions are errors
        return ErrorSeverity.ERROR

    def _create_user_message(self, exception: Exception, category: ErrorCategory) -> str:
        """Create user-friendly error message."""
        if category == ErrorCategory.FILE_IO:
            if isinstance(exception, FileNotFoundError):
                return "The requested file could not be found."
            elif "permission" in str(exception).lower():
                return "Unable to access the file. Permission denied."
            else:
                return "An error occurred while accessing the file."

        elif category == ErrorCategory.DATA_VALIDATION:
            return "The data format is invalid or corrupted."

        elif category == ErrorCategory.MEMORY:
            return "Not enough memory to complete the operation."

        elif category == ErrorCategory.PERMISSION:
            return "You don't have permission to perform this operation."

        elif category == ErrorCategory.RENDERING:
            return "An error occurred while rendering the display."

        else:
            # Generic message
            return f"An unexpected error occurred: {str(exception)}"

    def _log_error(self, error_info: ErrorInfo) -> None:
        """Log error to history and logger."""
        # Add to history
        self.error_history.append(error_info)

        # Trim history if needed
        if len(self.error_history) > self.max_history_size:
            self.error_history = self.error_history[-self.max_history_size :]

        # Log to logger
        if error_info.severity == ErrorSeverity.CRITICAL:
            logger.critical(f"{error_info.title}: {error_info.message}")
        elif error_info.severity == ErrorSeverity.ERROR:
            logger.error(f"{error_info.title}: {error_info.message}")
        elif error_info.severity == ErrorSeverity.WARNING:
            logger.warning(f"{error_info.title}: {error_info.message}")
        else:
            logger.info(f"{error_info.title}: {error_info.message}")

        # Log exception details if available
        if error_info.exception:
            logger.debug(f"Exception details: {traceback.format_exc()}")

        # Emit signal
        self.error_logged.emit(error_info.message, error_info.severity)


# Singleton instance
_error_handler: ErrorHandler | None = None


def get_error_handler() -> ErrorHandler:
    """Get the global error handler instance."""
    global _error_handler
    if _error_handler is None:
        _error_handler = ErrorHandler()
    return _error_handler

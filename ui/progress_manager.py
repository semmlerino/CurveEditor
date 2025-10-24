#!/usr/bin/env python
"""
Progress Manager for CurveEditor.

Provides progress indicators for long-running operations including
file loading, batch processing, and analysis tasks.
"""

import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum, auto
from typing import cast, override

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QProgressDialog,
    QPushButton,
    QWidget,
)

from core.logger_utils import get_logger

logger = get_logger("progress_manager")


class ProgressType(Enum):
    """Types of progress indicators."""

    FILE_LOAD = auto()
    FILE_SAVE = auto()
    BATCH_OPERATION = auto()
    ANALYSIS = auto()
    RENDERING = auto()
    EXPORT = auto()
    IMPORT = auto()


@dataclass
class ProgressInfo:
    """Information about a progress operation."""

    title: str
    message: str
    total: int = 100
    current: int = 0
    cancellable: bool = True
    show_percentage: bool = True
    show_time_remaining: bool = True
    minimum_duration: float = 0.5  # Don't show for operations < 0.5 seconds


class ProgressWorker(QThread):
    """Worker thread for progress operations."""

    # Signals
    progress_updated = Signal(int)  # percentage
    message_updated = Signal(str)  # message
    finished = Signal(bool)  # True if successful, False if cancelled
    error_occurred = Signal(str)  # error message

    # Attributes - will be initialized in __init__
    operation: Callable[..., object]
    args: tuple[object, ...]
    kwargs: dict[str, object]
    result: object

    def __init__(self, operation: Callable[..., object], *args: object, **kwargs: object) -> None:
        """Initialize the worker with an operation to perform."""
        super().__init__()
        self.operation = operation
        self.args = args
        self.kwargs = kwargs
        self.result = None

    @override
    def run(self) -> None:
        """Execute the operation in the thread."""
        try:
            # Pass self to operation so it can report progress
            self.result = self.operation(self, *self.args, **self.kwargs)
            if not self.isInterruptionRequested():
                self.finished.emit(True)
        except Exception as e:
            logger.error(f"Progress operation failed: {e}")
            self.error_occurred.emit(str(e))
            self.finished.emit(False)

    def report_progress(self, current: int, total: int = 100, message: str = "") -> bool:
        """Report progress from within the operation.

        Returns:
            False if operation was cancelled, True to continue
        """
        if self.isInterruptionRequested():
            return False

        percentage = int((current / total) * 100) if total > 0 else 0
        self.progress_updated.emit(percentage)

        if message:
            self.message_updated.emit(message)

        return True


class ProgressDialog(QProgressDialog):
    """Enhanced progress dialog with additional features."""

    # Attributes - will be initialized in __init__
    info: ProgressInfo
    start_time: float
    last_update_time: float

    def __init__(self, info: ProgressInfo, parent: QWidget | None = None):
        """Initialize the progress dialog."""
        super().__init__(info.message, "Cancel" if info.cancellable else "", 0, info.total, parent)

        self.info = info
        self.start_time = time.time()
        self.last_update_time = self.start_time

        # Configure dialog
        self.setWindowTitle(info.title)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setMinimumDuration(int(info.minimum_duration * 1000))
        self.setAutoClose(True)
        self.setAutoReset(True)

        # Add custom styling
        self._apply_styling()

        # Setup time remaining display
        if info.show_time_remaining:
            self._setup_time_display()

    def _apply_styling(self) -> None:
        """Apply custom styling to the dialog."""
        self.setStyleSheet("""
            QProgressDialog {
                min-width: 400px;
            }
            QProgressBar {
                text-align: center;
                height: 25px;
                border-radius: 5px;
            }
        """)

    def _setup_time_display(self) -> None:
        """Setup time remaining display."""
        # This would require custom widget implementation
        # For now, we'll update the label text
        pass

    def update_progress(self, value: int, message: str = "") -> None:
        """Update progress value and optionally the message."""
        self.setValue(value)

        if message:
            self.setLabelText(message)

        # Calculate and display time remaining
        if self.info.show_time_remaining and value > 0:
            elapsed = time.time() - self.start_time
            if value < self.info.total:
                remaining = (elapsed / value) * (self.info.total - value)
                time_str = self._format_time(remaining)
                current_text = self.labelText()
                if " (Time remaining:" not in current_text:
                    self.setLabelText(f"{current_text} (Time remaining: {time_str})")

    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to human-readable string."""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            minutes = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{minutes}m {secs}s"
        else:
            hours = int(seconds / 3600)
            minutes = int((seconds % 3600) / 60)
            return f"{hours}h {minutes}m"


class StatusBarProgress(QWidget):
    """Progress widget for status bar."""

    # Attributes - will be initialized in __init__
    label: QLabel
    progress_bar: QProgressBar
    cancel_button: QPushButton

    def __init__(self, parent: QWidget | None = None):
        """Initialize the status bar progress widget."""
        super().__init__(parent)

        # Create layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        # Create widgets
        self.label = QLabel()
        self.progress_bar = QProgressBar()
        self.cancel_button = QPushButton("✕")

        # Configure widgets
        self.progress_bar.setMaximumHeight(20)
        self.progress_bar.setMinimumWidth(150)
        self.progress_bar.setTextVisible(True)

        self.cancel_button.setMaximumSize(20, 20)
        self.cancel_button.setFlat(True)
        self.cancel_button.hide()

        # Add to layout
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.cancel_button)

        self.setLayout(layout)
        self.hide()

    def show_progress(self, message: str, cancellable: bool = False) -> None:
        """Show the progress widget."""
        self.label.setText(message)
        self.progress_bar.setValue(0)
        self.cancel_button.setVisible(cancellable)
        self.show()

    def update_progress(self, value: int, maximum: int = 100) -> None:
        """Update progress value."""
        self.progress_bar.setMaximum(maximum)
        self.progress_bar.setValue(value)

    def hide_progress(self) -> None:
        """Hide the progress widget."""
        self.hide()


class ProgressManager(QObject):
    """Manages progress indicators throughout the application."""

    # Signals
    operation_started = Signal(str)  # operation_name
    operation_finished = Signal(str, bool)  # operation_name, success

    def __init__(self, parent: QObject | None = None):
        """Initialize the progress manager."""
        super().__init__(parent)

        # Instance attributes
        self.active_operations: dict[str, ProgressWorker] = {}
        self.status_bar_widget: StatusBarProgress | None = None
        self._busy_cursor_count = 0

    def set_status_bar_widget(self, widget: StatusBarProgress) -> None:
        """Set the status bar progress widget."""
        self.status_bar_widget = widget

    @contextmanager
    def busy_cursor(self):
        """Context manager for showing busy cursor."""
        self.show_busy_cursor()
        try:
            yield
        finally:
            self.hide_busy_cursor()

    def show_busy_cursor(self) -> None:
        """Show busy cursor."""
        if self._busy_cursor_count == 0:
            _ = QApplication.setOverrideCursor(QCursor(Qt.CursorShape.WaitCursor))
        self._busy_cursor_count += 1

    def hide_busy_cursor(self) -> None:
        """Hide busy cursor."""
        self._busy_cursor_count = max(0, self._busy_cursor_count - 1)
        if self._busy_cursor_count == 0:
            QApplication.restoreOverrideCursor()

    def show_progress_dialog(
        self,
        info: ProgressInfo,
        operation: Callable[..., object],
        parent: QWidget | None = None,
        *args: object,
        **kwargs: object,
    ) -> object:
        """Show a progress dialog for an operation.

        Args:
            info: Progress information
            operation: Callable that performs the operation
            parent: Parent widget for the dialog
            *args, **kwargs: Arguments to pass to the operation

        Returns:
            Result of the operation or None if cancelled
        """
        # Create dialog
        dialog = ProgressDialog(info, parent)

        # Create worker
        worker = ProgressWorker(operation, *args, **kwargs)

        # Connect signals
        _ = worker.progress_updated.connect(dialog.setValue)
        _ = worker.message_updated.connect(dialog.setLabelText)
        _ = worker.finished.connect(dialog.close)
        _ = worker.error_occurred.connect(lambda msg: self._handle_error(msg, dialog))

        if info.cancellable:
            _ = dialog.canceled.connect(worker.requestInterruption)

        # Store worker
        operation_id = f"{info.title}_{time.time()}"
        self.active_operations[operation_id] = worker

        # Start operation
        self.operation_started.emit(info.title)
        worker.start()

        # Show dialog (blocks until complete)
        _ = dialog.exec()

        # Clean up
        success = not worker.isInterruptionRequested()
        result = worker.result if success else None
        del self.active_operations[operation_id]

        self.operation_finished.emit(info.title, success)

        return result

    def show_status_progress(
        self,
        message: str,
        operation: Callable[..., object],
        cancellable: bool = False,
        callback: Callable[[object], None] | None = None,
        *args: object,
        **kwargs: object,
    ) -> None:
        """Show progress in status bar for an operation (non-blocking).

        Args:
            message: Message to display
            operation: Callable that performs the operation
            cancellable: Whether operation can be cancelled
            callback: Optional callback to receive the result
            *args, **kwargs: Arguments to pass to operation

        Note: This is now non-blocking. Use callback to get result.
        """
        if not self.status_bar_widget:
            # Fallback to busy cursor if no status bar widget
            with self.busy_cursor():
                result = operation(None, *args, **kwargs)
                if callback:
                    callback(result)
                return

        # Show status bar progress
        self.status_bar_widget.show_progress(message, cancellable)

        # Create worker
        worker = ProgressWorker(operation, *args, **kwargs)

        # Store callback for when operation finishes
        def on_finished(success: bool) -> None:
            if self.status_bar_widget:
                self.status_bar_widget.hide_progress()
            if success and callback:
                callback(worker.result)

        # Connect signals
        _ = worker.progress_updated.connect(
            lambda v: self.status_bar_widget.update_progress(v) if self.status_bar_widget else None
        )
        _ = worker.finished.connect(on_finished)

        if cancellable and self.status_bar_widget:
            _ = self.status_bar_widget.cancel_button.clicked.connect(worker.requestInterruption)

        # Start operation (non-blocking)
        worker.start()

    def _handle_error(self, error_msg: str, dialog: QProgressDialog) -> None:
        """Handle error during progress operation."""
        logger.error(f"Progress operation error: {error_msg}")
        _ = dialog.close()

        # Could show error dialog here
        from PySide6.QtWidgets import QMessageBox

        _ = QMessageBox.critical(cast(QWidget, dialog.parent()), "Operation Failed", error_msg)

    @Slot(str, int, int)
    def update_operation_progress(self, operation_id: str, current: int, total: int) -> None:
        """Update progress for a specific operation."""
        if operation_id in self.active_operations:
            worker = self.active_operations[operation_id]
            percentage = int((current / total) * 100) if total > 0 else 0
            worker.progress_updated.emit(percentage)


# Singleton instance
_progress_manager: ProgressManager | None = None


def get_progress_manager() -> ProgressManager:
    """Get the global progress manager instance."""
    global _progress_manager
    if _progress_manager is None:
        _progress_manager = ProgressManager()
    return _progress_manager


# Decorator for adding progress to functions
def with_progress(
    title: str = "Processing...", message: str = "Please wait...", show_dialog: bool = True
) -> Callable[[Callable[..., object]], Callable[..., object]]:
    """Decorator to add progress indicator to a function."""

    def decorator(func: Callable[..., object]) -> Callable[..., object]:
        def wrapper(*args: object, **kwargs: object) -> object:
            manager = get_progress_manager()

            if show_dialog:
                info = ProgressInfo(
                    title=title, message=message, cancellable=True, show_percentage=True, show_time_remaining=True
                )

                def operation(worker: ProgressWorker, *op_args: object, **op_kwargs: object) -> object:
                    # Pass worker to the function if it accepts it
                    import inspect

                    sig = inspect.signature(func)
                    if "progress_worker" in sig.parameters:
                        return func(*op_args, progress_worker=worker, **op_kwargs)
                    else:
                        return func(*op_args, **op_kwargs)

                return manager.show_progress_dialog(info, operation, None, *args, **kwargs)
            else:
                # Just show busy cursor
                with manager.busy_cursor():
                    return func(*args, **kwargs)

        return wrapper

    return decorator

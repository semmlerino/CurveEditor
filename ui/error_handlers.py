#!/usr/bin/env python
"""
Error handling strategies for CurveEditor UI components.

This module provides decoupled error handlers that can be plugged into UI components,
separating error handling logic from core functionality.
"""

import logging
import traceback
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Protocol, override, runtime_checkable

if TYPE_CHECKING:
    from core.validation_strategy import ValidationIssue

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget

logger = logging.getLogger("error_handlers")


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Context information for an error."""

    component: str  # Component where error occurred
    operation: str  # Operation being performed
    severity: ErrorSeverity
    error: Exception
    context_data: dict[str, object] | None = None
    recovery_attempted: bool = False
    recovery_successful: bool = False
    user_message: str | None = None
    technical_details: str | None = None

    def __post_init__(self) -> None:
        """Initialize technical details if not provided."""
        if self.technical_details is None:
            self.technical_details = traceback.format_exc()


class RecoveryStrategy(Enum):
    """Recovery strategies for errors."""

    IGNORE = "ignore"  # Ignore and continue
    RETRY = "retry"  # Retry the operation
    RESET = "reset"  # Reset to default state
    FALLBACK = "fallback"  # Use fallback value
    NOTIFY = "notify"  # Notify user and continue
    ABORT = "abort"  # Abort operation


@runtime_checkable
class TransformErrorHandler(Protocol):
    """Protocol for transform error handlers."""

    def handle_validation_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Handle validation errors."""
        ...

    def handle_transform_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Handle transformation errors."""
        ...

    def handle_cache_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Handle cache-related errors."""
        ...

    def handle_coordinate_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Handle coordinate system errors."""
        ...

    def report_issues(self, issues: list["ValidationIssue"]) -> None:
        """Report validation issues to user."""
        ...

    def notify_recovery(self, context: ErrorContext, strategy: RecoveryStrategy) -> None:
        """Notify about recovery actions."""
        ...


class BaseErrorHandler(ABC):
    """Base class for error handlers."""

    def __init__(self, parent_widget: "QWidget | None" = None):
        """Initialize error handler."""
        self.parent_widget = parent_widget
        self.error_count: dict[str, int] = {}
        self.max_errors_per_type = 10

    @abstractmethod
    def handle_validation_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Handle validation errors."""
        pass

    @abstractmethod
    def handle_transform_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Handle transformation errors."""
        pass

    @abstractmethod
    def handle_cache_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Handle cache-related errors."""
        pass

    @abstractmethod
    def handle_coordinate_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Handle coordinate system errors."""
        pass

    @abstractmethod
    def report_issues(self, issues: list["ValidationIssue"]) -> None:
        """Report validation issues to user."""
        pass

    @abstractmethod
    def notify_recovery(self, context: ErrorContext, strategy: RecoveryStrategy) -> None:
        """Notify about recovery actions."""
        pass

    def should_suppress_error(self, error_type: str) -> bool:
        """Check if error should be suppressed due to frequency."""
        self.error_count[error_type] = self.error_count.get(error_type, 0) + 1
        return self.error_count[error_type] > self.max_errors_per_type

    def reset_error_counts(self) -> None:
        """Reset error counts."""
        self.error_count.clear()


class DefaultTransformErrorHandler(BaseErrorHandler):
    """
    Default error handler with progressive recovery strategies.

    Attempts to recover from errors gracefully:
    1. Validation errors: Use default values
    2. Transform errors: Reset to identity transform
    3. Cache errors: Clear cache and retry
    4. Coordinate errors: Use normalized coordinates
    """

    def __init__(self, parent_widget: "QWidget | None" = None, verbose: bool = True):
        """Initialize with optional verbosity."""
        super().__init__(parent_widget)
        self.verbose = verbose
        self.recovery_callbacks: dict[str, Callable[[], object]] = {}

    def set_recovery_callback(self, operation: str, callback: Callable[[], object]) -> None:
        """Set a recovery callback for a specific operation."""
        self.recovery_callbacks[operation] = callback

    @override
    def handle_validation_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Handle validation errors with fallback values."""
        error_key = f"validation_{context.operation}"

        if self.should_suppress_error(error_key):
            return RecoveryStrategy.IGNORE

        # Log the error
        logger.warning(f"Validation error in {context.component}.{context.operation}: {error}")

        # Try to use fallback values
        if context.context_data and "fallback" in context.context_data:
            if self.verbose:
                logger.info(f"Using fallback value: {context.context_data['fallback']}")
            return RecoveryStrategy.FALLBACK

        # For non-critical validation, just notify and continue
        if context.severity in (ErrorSeverity.INFO, ErrorSeverity.WARNING):
            return RecoveryStrategy.NOTIFY

        # For critical validation, reset to safe state
        return RecoveryStrategy.RESET

    @override
    def handle_transform_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Handle transform errors with identity transform."""
        error_key = f"transform_{context.operation}"

        if self.should_suppress_error(error_key):
            return RecoveryStrategy.IGNORE

        logger.error(f"Transform error in {context.component}.{context.operation}: {error}")

        # Check if we have a recovery callback
        if context.operation in self.recovery_callbacks:
            try:
                self.recovery_callbacks[context.operation]()
                return RecoveryStrategy.RESET
            except Exception as e:
                logger.error(f"Recovery callback failed: {e}")

        # For render operations, ignore to prevent UI freeze
        if "render" in context.operation.lower():
            return RecoveryStrategy.IGNORE

        # Otherwise reset to identity transform
        return RecoveryStrategy.RESET

    @override
    def handle_cache_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Handle cache errors by clearing and retrying."""
        error_key = f"cache_{context.operation}"

        if self.should_suppress_error(error_key):
            return RecoveryStrategy.IGNORE

        logger.warning(f"Cache error in {context.component}.{context.operation}: {error}")

        # First attempt: retry once
        if not context.recovery_attempted:
            return RecoveryStrategy.RETRY

        # Second attempt: clear cache and continue
        logger.info("Clearing cache due to persistent errors")
        return RecoveryStrategy.RESET

    @override
    def handle_coordinate_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Handle coordinate system errors with normalization."""
        error_key = f"coordinate_{context.operation}"

        if self.should_suppress_error(error_key):
            return RecoveryStrategy.IGNORE

        logger.error(f"Coordinate error in {context.component}.{context.operation}: {error}")

        # Try to use normalized coordinates
        if context.context_data and "normalized" in context.context_data:
            return RecoveryStrategy.FALLBACK

        # For display operations, continue with best effort
        if "display" in context.operation.lower() or "screen" in context.operation.lower():
            return RecoveryStrategy.NOTIFY

        # Otherwise abort to prevent data corruption
        return RecoveryStrategy.ABORT

    @override
    def report_issues(self, issues: list["ValidationIssue"]) -> None:
        """Report validation issues to user."""
        if not self.verbose or not issues:
            return

        # Log issues at appropriate levels based on severity
        for issue in issues:
            from core.validation_strategy import ValidationSeverity

            message = issue.format()
            if issue.severity == ValidationSeverity.CRITICAL:
                logger.error(message)
            elif issue.severity == ValidationSeverity.WARNING:
                logger.warning(message)
            else:  # INFO
                logger.info(message)

        # Show UI notification if we have a parent widget and issues
        if self.parent_widget and issues:
            try:
                from PySide6.QtWidgets import QMessageBox

                msg = QMessageBox(self.parent_widget)
                msg.setIcon(QMessageBox.Icon.Warning)
                msg.setWindowTitle("Validation Issues")
                msg.setText(f"{len(issues)} issue(s) detected")
                details = "\n".join(issue.format() for issue in issues[:5])  # Show first 5
                msg.setDetailedText(details)
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                _ = msg.exec()
            except ImportError:
                pass  # Qt not available

    @override
    def notify_recovery(self, context: ErrorContext, strategy: RecoveryStrategy) -> None:
        """Notify about recovery actions."""
        if not self.verbose:
            return

        if strategy == RecoveryStrategy.IGNORE:
            return  # Don't notify about ignoring

        message = f"Recovery [{strategy.value}] for {context.component}.{context.operation}"
        if context.user_message:
            message += f": {context.user_message}"

        if strategy in (RecoveryStrategy.RESET, RecoveryStrategy.FALLBACK):
            logger.info(message)
        elif strategy == RecoveryStrategy.ABORT:
            logger.error(message)
        else:
            logger.debug(message)


class SilentTransformErrorHandler(BaseErrorHandler):
    """
    Silent error handler for testing and batch operations.

    Suppresses all user notifications and logs errors at debug level only.
    Always attempts automatic recovery without user interaction.
    """

    def __init__(self, parent_widget: "QWidget | None" = None):
        """Initialize silent handler."""
        super().__init__(parent_widget)
        self.captured_errors: list[ErrorContext] = []

    @override
    def handle_validation_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Silently handle validation errors."""
        self.captured_errors.append(context)
        logger.debug(f"Silent: Validation error - {error}")
        return (
            RecoveryStrategy.FALLBACK
            if context.context_data and "fallback" in context.context_data
            else RecoveryStrategy.IGNORE
        )

    @override
    def handle_transform_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Silently handle transform errors."""
        self.captured_errors.append(context)
        logger.debug(f"Silent: Transform error - {error}")
        return RecoveryStrategy.RESET

    @override
    def handle_cache_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Silently handle cache errors."""
        self.captured_errors.append(context)
        logger.debug(f"Silent: Cache error - {error}")
        return RecoveryStrategy.RETRY if not context.recovery_attempted else RecoveryStrategy.RESET

    @override
    def handle_coordinate_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Silently handle coordinate errors."""
        self.captured_errors.append(context)
        logger.debug(f"Silent: Coordinate error - {error}")
        return (
            RecoveryStrategy.FALLBACK
            if context.context_data and "normalized" in context.context_data
            else RecoveryStrategy.IGNORE
        )

    @override
    def report_issues(self, issues: list["ValidationIssue"]) -> None:
        """Silently capture issues."""
        for issue in issues:
            logger.debug(f"Silent: {issue.format()}")

    @override
    def notify_recovery(self, context: ErrorContext, strategy: RecoveryStrategy) -> None:
        """Silently log recovery."""
        logger.debug(f"Silent: Recovery [{strategy.value}] for {context.component}.{context.operation}")

    def get_captured_errors(self) -> list[ErrorContext]:
        """Get all captured errors for testing."""
        return self.captured_errors.copy()

    def clear_captured_errors(self) -> None:
        """Clear captured errors."""
        self.captured_errors.clear()


class StrictTransformErrorHandler(BaseErrorHandler):
    """
    Strict error handler that fails fast on any error.

    Useful for development and debugging to catch issues early.
    """

    def __init__(self, parent_widget: "QWidget | None" = None):
        """Initialize strict handler."""
        super().__init__(parent_widget)

    @override
    def handle_validation_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Abort on validation errors."""
        logger.error(f"STRICT: Validation error - {error}")
        if context.severity == ErrorSeverity.CRITICAL:
            raise error
        return RecoveryStrategy.ABORT

    @override
    def handle_transform_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Abort on transform errors."""
        logger.error(f"STRICT: Transform error - {error}")
        raise error

    @override
    def handle_cache_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Abort on cache errors."""
        logger.error(f"STRICT: Cache error - {error}")
        raise error

    @override
    def handle_coordinate_error(self, error: Exception, context: ErrorContext) -> RecoveryStrategy:
        """Abort on coordinate errors."""
        logger.error(f"STRICT: Coordinate error - {error}")
        raise error

    @override
    def report_issues(self, issues: list["ValidationIssue"]) -> None:
        """Report all issues as errors."""
        from core.validation_strategy import ValidationSeverity

        for issue in issues:
            message = f"STRICT: {issue.format()}"
            logger.error(message)
            # In strict mode, raise on first critical issue
            if issue.severity == ValidationSeverity.CRITICAL:
                raise ValueError(issue.format())

    @override
    def notify_recovery(self, context: ErrorContext, strategy: RecoveryStrategy) -> None:
        """Log recovery attempts as errors in strict mode."""
        logger.error(f"STRICT: Recovery attempted [{strategy.value}] for {context.component}.{context.operation}")


# Factory function
def create_error_handler(mode: str = "default", parent_widget: "QWidget | None" = None) -> BaseErrorHandler:
    """
    Create an error handler based on mode.

    Args:
        mode: "default", "silent", "strict", or "auto"
        parent_widget: Optional parent widget for UI notifications

    Returns:
        Appropriate error handler
    """
    if mode == "silent":
        return SilentTransformErrorHandler(parent_widget)
    elif mode == "strict":
        return StrictTransformErrorHandler(parent_widget)
    elif mode == "default":
        return DefaultTransformErrorHandler(parent_widget)
    else:  # auto
        # Use strict in debug mode, default otherwise
        if __debug__:
            return DefaultTransformErrorHandler(parent_widget, verbose=True)
        else:
            return DefaultTransformErrorHandler(parent_widget, verbose=False)


# Example usage with UI component
class ErrorHandlerMixin:
    """Mixin for UI components to add error handling."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        """Initialize with error handler."""
        super().__init__(*args, **kwargs)
        self._error_handler: BaseErrorHandler | None = None

    @property
    def error_handler(self) -> BaseErrorHandler:
        """Get error handler, creating default if needed."""
        if self._error_handler is None:
            widget = getattr(self, "parent_widget", None) or getattr(self, "widget", None)
            self._error_handler = create_error_handler("default", widget)
        return self._error_handler

    @error_handler.setter
    def error_handler(self, handler: BaseErrorHandler) -> None:
        """Set error handler."""
        self._error_handler = handler

    def handle_error(self, error: Exception, operation: str, **context_data: object) -> RecoveryStrategy:
        """
        Handle an error with the configured handler.

        Args:
            error: The exception that occurred
            operation: The operation being performed
            **context_data: Additional context data

        Returns:
            Recovery strategy to apply
        """
        component = self.__class__.__name__
        severity = ErrorSeverity.ERROR

        # Determine severity from error type
        if isinstance(error, ValueError):
            severity = ErrorSeverity.WARNING
        elif isinstance(error, TypeError | AttributeError):
            severity = ErrorSeverity.CRITICAL

        context = ErrorContext(
            component=component, operation=operation, severity=severity, error=error, context_data=context_data
        )

        # Route to appropriate handler method
        if "validation" in str(error).lower():
            strategy = self.error_handler.handle_validation_error(error, context)
        elif "transform" in str(error).lower():
            strategy = self.error_handler.handle_transform_error(error, context)
        elif "cache" in str(error).lower():
            strategy = self.error_handler.handle_cache_error(error, context)
        elif "coordinate" in str(error).lower():
            strategy = self.error_handler.handle_coordinate_error(error, context)
        else:
            # Default to transform error handling
            strategy = self.error_handler.handle_transform_error(error, context)

        # Notify about recovery
        self.error_handler.notify_recovery(context, strategy)

        return strategy

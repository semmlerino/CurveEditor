#!/usr/bin/env python3
# pyright: reportAttributeAccessIssue=false, reportUnsafeMultipleInheritance=false
"""
Test suite for error handling strategies.

Tests the different error handlers and recovery strategies.
This file uses test-only monkey-patching which is safe but triggers type errors.
"""

import logging
import unittest
from unittest.mock import MagicMock, patch

from PySide6.QtWidgets import QApplication, QWidget

from core.validation_strategy import ValidationIssue, ValidationSeverity
from ui.error_handlers import (
    DefaultTransformErrorHandler,
    ErrorContext,
    ErrorHandlerMixin,
    ErrorSeverity,
    RecoveryStrategy,
    SilentTransformErrorHandler,
    StrictTransformErrorHandler,
    create_error_handler,
)

# Create QApplication for tests that need Qt
app = None


def setUpModule():
    global app
    app = QApplication.instance()
    if app is None:
        app = QApplication([])


def tearDownModule():
    global app
    if app:
        app.quit()


class TestErrorContext(unittest.TestCase):
    """Test ErrorContext dataclass."""

    def test_error_context_creation(self):
        """Test creating error context."""
        error = ValueError("Test error")
        context = ErrorContext(
            component="TestComponent", operation="test_op", severity=ErrorSeverity.ERROR, error=error
        )

        self.assertEqual(context.component, "TestComponent")
        self.assertEqual(context.operation, "test_op")
        self.assertEqual(context.severity, ErrorSeverity.ERROR)
        self.assertEqual(context.error, error)
        self.assertIsNotNone(context.technical_details)

    def test_error_context_with_data(self):
        """Test error context with additional data."""
        error = ValueError("Test error")
        context_data = {"fallback": 10.0, "retry_count": 2}

        context = ErrorContext(
            component="TestComponent",
            operation="test_op",
            severity=ErrorSeverity.WARNING,
            error=error,
            context_data=context_data,
            user_message="Please check input",
        )

        self.assertEqual(context.context_data, context_data)
        self.assertEqual(context.user_message, "Please check input")


class TestDefaultTransformErrorHandler(unittest.TestCase):
    """Test default error handler."""

    handler: DefaultTransformErrorHandler  # pyright: ignore[reportUninitializedInstanceVariable]
    error: ValueError  # pyright: ignore[reportUninitializedInstanceVariable]

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.handler = DefaultTransformErrorHandler(verbose=False)
        self.error = ValueError("Test error")

    def test_validation_error_with_fallback(self):
        """Test validation error with fallback value."""
        context = ErrorContext(
            component="Test",
            operation="validate",
            severity=ErrorSeverity.WARNING,
            error=self.error,
            context_data={"fallback": 100.0},
        )

        strategy = self.handler.handle_validation_error(self.error, context)
        self.assertEqual(strategy, RecoveryStrategy.FALLBACK)

    def test_validation_error_non_critical(self):
        """Test non-critical validation error."""
        context = ErrorContext(component="Test", operation="validate", severity=ErrorSeverity.INFO, error=self.error)

        strategy = self.handler.handle_validation_error(self.error, context)
        self.assertEqual(strategy, RecoveryStrategy.NOTIFY)

    def test_validation_error_critical(self):
        """Test critical validation error."""
        context = ErrorContext(
            component="Test", operation="validate", severity=ErrorSeverity.CRITICAL, error=self.error
        )

        strategy = self.handler.handle_validation_error(self.error, context)
        self.assertEqual(strategy, RecoveryStrategy.RESET)

    def test_transform_error_render_operation(self):
        """Test transform error during render."""
        context = ErrorContext(
            component="Test", operation="render_frame", severity=ErrorSeverity.ERROR, error=self.error
        )

        strategy = self.handler.handle_transform_error(self.error, context)
        self.assertEqual(strategy, RecoveryStrategy.IGNORE)

    def test_transform_error_with_callback(self):
        """Test transform error with recovery callback."""
        callback = MagicMock()
        self.handler.set_recovery_callback("process", callback)

        context = ErrorContext(component="Test", operation="process", severity=ErrorSeverity.ERROR, error=self.error)

        strategy = self.handler.handle_transform_error(self.error, context)
        callback.assert_called_once()
        self.assertEqual(strategy, RecoveryStrategy.RESET)

    def test_cache_error_retry(self):
        """Test cache error with retry."""
        context = ErrorContext(
            component="Test",
            operation="cache_lookup",
            severity=ErrorSeverity.WARNING,
            error=self.error,
            recovery_attempted=False,
        )

        strategy = self.handler.handle_cache_error(self.error, context)
        self.assertEqual(strategy, RecoveryStrategy.RETRY)

    def test_cache_error_after_retry(self):
        """Test cache error after retry attempt."""
        context = ErrorContext(
            component="Test",
            operation="cache_lookup",
            severity=ErrorSeverity.WARNING,
            error=self.error,
            recovery_attempted=True,
        )

        strategy = self.handler.handle_cache_error(self.error, context)
        self.assertEqual(strategy, RecoveryStrategy.RESET)

    def test_coordinate_error_with_normalized(self):
        """Test coordinate error with normalized fallback."""
        context = ErrorContext(
            component="Test",
            operation="transform",
            severity=ErrorSeverity.ERROR,
            error=self.error,
            context_data={"normalized": (0.5, 0.5)},
        )

        strategy = self.handler.handle_coordinate_error(self.error, context)
        self.assertEqual(strategy, RecoveryStrategy.FALLBACK)

    def test_coordinate_error_display_operation(self):
        """Test coordinate error in display operation."""
        context = ErrorContext(
            component="Test", operation="display_coordinates", severity=ErrorSeverity.ERROR, error=self.error
        )

        strategy = self.handler.handle_coordinate_error(self.error, context)
        self.assertEqual(strategy, RecoveryStrategy.NOTIFY)

    def test_error_suppression(self):
        """Test error suppression after threshold."""
        context = ErrorContext(component="Test", operation="validate", severity=ErrorSeverity.WARNING, error=self.error)

        # First 10 errors should not be suppressed
        for i in range(10):
            strategy = self.handler.handle_validation_error(self.error, context)
            self.assertNotEqual(strategy, RecoveryStrategy.IGNORE)

        # 11th error should be suppressed
        strategy = self.handler.handle_validation_error(self.error, context)
        self.assertEqual(strategy, RecoveryStrategy.IGNORE)

    def test_report_issues(self):
        """Test reporting validation issues."""
        issues = [
            ValidationIssue("field1", 1.0, ValidationSeverity.CRITICAL, "Critical error"),
            ValidationIssue("field2", 2.0, ValidationSeverity.WARNING, "Warning"),
            ValidationIssue("field3", 3.0, ValidationSeverity.INFO, "Info"),
        ]

        with patch.object(logging.getLogger("error_handlers"), "error") as mock_error:
            with patch.object(logging.getLogger("error_handlers"), "warning") as mock_warning:
                self.handler.verbose = True
                self.handler.report_issues(issues)

                # Should log critical as error
                mock_error.assert_called()
                # Should log warning
                mock_warning.assert_called()


class TestSilentTransformErrorHandler(unittest.TestCase):
    """Test silent error handler."""

    handler: SilentTransformErrorHandler  # pyright: ignore[reportUninitializedInstanceVariable]
    error: ValueError  # pyright: ignore[reportUninitializedInstanceVariable]

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.handler = SilentTransformErrorHandler()
        self.error = ValueError("Test error")

    def test_validation_error_silent(self):
        """Test silent handling of validation error."""
        context = ErrorContext(
            component="Test",
            operation="validate",
            severity=ErrorSeverity.ERROR,
            error=self.error,
            context_data={"fallback": 10.0},
        )

        strategy = self.handler.handle_validation_error(self.error, context)
        self.assertEqual(strategy, RecoveryStrategy.FALLBACK)

        # Error should be captured
        self.assertEqual(len(self.handler.captured_errors), 1)
        self.assertEqual(self.handler.captured_errors[0], context)

    def test_transform_error_silent(self):
        """Test silent handling of transform error."""
        context = ErrorContext(component="Test", operation="transform", severity=ErrorSeverity.ERROR, error=self.error)

        strategy = self.handler.handle_transform_error(self.error, context)
        self.assertEqual(strategy, RecoveryStrategy.RESET)
        self.assertEqual(len(self.handler.captured_errors), 1)

    def test_cache_error_silent(self):
        """Test silent handling of cache error."""
        context = ErrorContext(
            component="Test",
            operation="cache",
            severity=ErrorSeverity.WARNING,
            error=self.error,
            recovery_attempted=False,
        )

        strategy = self.handler.handle_cache_error(self.error, context)
        self.assertEqual(strategy, RecoveryStrategy.RETRY)

        # Try again after retry
        context.recovery_attempted = True
        strategy = self.handler.handle_cache_error(self.error, context)
        self.assertEqual(strategy, RecoveryStrategy.RESET)

    def test_report_issues_silent(self):
        """Test silent issue reporting."""
        issues = [ValidationIssue("field1", 1.0, ValidationSeverity.CRITICAL, "Error")]

        with patch.object(logging.getLogger("error_handlers"), "debug") as mock_debug:
            self.handler.report_issues(issues)
            mock_debug.assert_called()

    def test_captured_errors(self):
        """Test capturing and retrieving errors."""
        errors = []
        for i in range(5):
            context = ErrorContext(
                component=f"Component{i}",
                operation=f"op{i}",
                severity=ErrorSeverity.ERROR,
                error=ValueError(f"Error {i}"),
            )
            self.handler.handle_validation_error(context.error, context)
            errors.append(context)

        captured = self.handler.get_captured_errors()
        self.assertEqual(len(captured), 5)

        # Clear captured errors
        self.handler.clear_captured_errors()
        self.assertEqual(len(self.handler.captured_errors), 0)


class TestStrictTransformErrorHandler(unittest.TestCase):
    """Test strict error handler."""

    handler: StrictTransformErrorHandler  # pyright: ignore[reportUninitializedInstanceVariable]
    error: ValueError  # pyright: ignore[reportUninitializedInstanceVariable]

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.handler = StrictTransformErrorHandler()
        self.error = ValueError("Test error")

    def test_validation_error_critical_raises(self):
        """Test critical validation error raises."""
        context = ErrorContext(
            component="Test", operation="validate", severity=ErrorSeverity.CRITICAL, error=self.error
        )

        with self.assertRaises(ValueError):
            self.handler.handle_validation_error(self.error, context)

    def test_validation_error_non_critical_aborts(self):
        """Test non-critical validation error aborts."""
        context = ErrorContext(component="Test", operation="validate", severity=ErrorSeverity.WARNING, error=self.error)

        strategy = self.handler.handle_validation_error(self.error, context)
        self.assertEqual(strategy, RecoveryStrategy.ABORT)

    def test_transform_error_raises(self):
        """Test transform error raises."""
        context = ErrorContext(component="Test", operation="transform", severity=ErrorSeverity.ERROR, error=self.error)

        with self.assertRaises(ValueError):
            self.handler.handle_transform_error(self.error, context)

    def test_cache_error_raises(self):
        """Test cache error raises."""
        context = ErrorContext(component="Test", operation="cache", severity=ErrorSeverity.ERROR, error=self.error)

        with self.assertRaises(ValueError):
            self.handler.handle_cache_error(self.error, context)

    def test_coordinate_error_raises(self):
        """Test coordinate error raises."""
        context = ErrorContext(component="Test", operation="coordinate", severity=ErrorSeverity.ERROR, error=self.error)

        with self.assertRaises(ValueError):
            self.handler.handle_coordinate_error(self.error, context)

    def test_report_issues_critical_raises(self):
        """Test reporting critical issues raises."""
        issues = [ValidationIssue("field", 1.0, ValidationSeverity.CRITICAL, "Critical")]

        with self.assertRaises(ValueError):
            self.handler.report_issues(issues)


class TestErrorHandlerFactory(unittest.TestCase):
    """Test error handler factory."""

    def test_create_default_handler(self):
        """Test creating default handler."""
        handler = create_error_handler("default")
        self.assertIsInstance(handler, DefaultTransformErrorHandler)

    def test_create_silent_handler(self):
        """Test creating silent handler."""
        handler = create_error_handler("silent")
        self.assertIsInstance(handler, SilentTransformErrorHandler)

    def test_create_strict_handler(self):
        """Test creating strict handler."""
        handler = create_error_handler("strict")
        self.assertIsInstance(handler, StrictTransformErrorHandler)

    def test_create_auto_handler(self):
        """Test creating auto handler."""
        handler = create_error_handler("auto")
        self.assertIsInstance(handler, DefaultTransformErrorHandler)

        # In debug mode should be verbose
        if __debug__:
            self.assertTrue(handler.verbose)


class TestErrorHandlerMixin(unittest.TestCase):
    """Test ErrorHandlerMixin integration."""

    widget: QWidget  # pyright: ignore[reportUninitializedInstanceVariable]

    def setUp(self) -> None:
        """Set up test fixtures."""

        class TestWidget(QWidget, ErrorHandlerMixin):
            def __init__(self):
                super().__init__()

        self.widget = TestWidget()

    def test_error_handler_property(self):
        """Test error handler property."""
        # Should create default handler
        handler = self.widget.error_handler
        self.assertIsInstance(handler, DefaultTransformErrorHandler)

        # Should return same instance
        handler2 = self.widget.error_handler
        self.assertIs(handler, handler2)

    def test_set_error_handler(self):
        """Test setting custom error handler."""
        custom_handler = SilentTransformErrorHandler()
        self.widget.error_handler = custom_handler
        self.assertIs(self.widget.error_handler, custom_handler)

    def test_handle_error(self):
        """Test handling errors through mixin."""
        # Set a silent handler to avoid logging
        self.widget.error_handler = SilentTransformErrorHandler()

        # Handle validation error
        error = ValueError("validation failed")
        strategy = self.widget.handle_error(error, "test_operation", fallback=10.0)
        self.assertEqual(strategy, RecoveryStrategy.FALLBACK)

        # Handle transform error
        error = TypeError("transform error")
        strategy = self.widget.handle_error(error, "transform_operation")
        self.assertIn(strategy, [RecoveryStrategy.RESET, RecoveryStrategy.ABORT])

    def test_error_routing(self):
        """Test error routing based on error message."""
        self.widget.error_handler = SilentTransformErrorHandler()

        # Validation error
        error = ValueError("Validation check failed")
        _ = self.widget.handle_error(error, "check")
        # Should route to validation handler

        # Transform error
        error = ValueError("Transform matrix invalid")
        _ = self.widget.handle_error(error, "calculate")
        # Should route to transform handler

        # Cache error
        error = RuntimeError("Cache lookup failed")
        _ = self.widget.handle_error(error, "lookup")
        # Should route to cache handler

        # Coordinate error
        error = ValueError("Coordinate out of bounds")
        _ = self.widget.handle_error(error, "convert")
        # Should route to coordinate handler


class TestIntegrationScenarios(unittest.TestCase):
    """Test integration scenarios."""

    def test_error_recovery_pipeline(self):
        """Test complete error recovery pipeline."""
        handler = DefaultTransformErrorHandler(verbose=False)

        # Simulate a series of errors
        errors_handled = []

        # Validation error with fallback
        context = ErrorContext(
            component="Pipeline",
            operation="validate_input",
            severity=ErrorSeverity.WARNING,
            error=ValueError("Invalid input"),
            context_data={"fallback": 0.0},
        )
        strategy = handler.handle_validation_error(context.error, context)
        errors_handled.append((context, strategy))

        # Transform error that should be ignored
        context = ErrorContext(
            component="Pipeline",
            operation="render_transform",
            severity=ErrorSeverity.ERROR,
            error=RuntimeError("Transform failed"),
        )
        strategy = handler.handle_transform_error(context.error, context)
        errors_handled.append((context, strategy))

        # Cache error that retries
        context = ErrorContext(
            component="Pipeline",
            operation="cache_fetch",
            severity=ErrorSeverity.WARNING,
            error=KeyError("Cache miss"),
            recovery_attempted=False,
        )
        strategy = handler.handle_cache_error(context.error, context)
        errors_handled.append((context, strategy))

        # Verify recovery strategies
        self.assertEqual(errors_handled[0][1], RecoveryStrategy.FALLBACK)
        self.assertEqual(errors_handled[1][1], RecoveryStrategy.IGNORE)
        self.assertEqual(errors_handled[2][1], RecoveryStrategy.RETRY)

    def test_testing_with_silent_handler(self):
        """Test using silent handler for testing."""
        handler = SilentTransformErrorHandler()

        # Run operations that might fail
        for i in range(10):
            context = ErrorContext(
                component="TestOp",
                operation=f"operation_{i}",
                severity=ErrorSeverity.ERROR,
                error=Exception(f"Error {i}"),
            )
            handler.handle_transform_error(context.error, context)

        # Check captured errors
        captured = handler.get_captured_errors()
        self.assertEqual(len(captured), 10)

        # Verify all errors were handled silently
        for error_context in captured:
            self.assertEqual(error_context.component, "TestOp")

    def test_development_with_strict_handler(self):
        """Test using strict handler for development."""
        handler = StrictTransformErrorHandler()

        # Any error should raise immediately
        context = ErrorContext(
            component="DevOp",
            operation="risky_operation",
            severity=ErrorSeverity.ERROR,
            error=RuntimeError("Development error"),
        )

        with self.assertRaises(RuntimeError):
            handler.handle_transform_error(context.error, context)


if __name__ == "__main__":
    unittest.main()

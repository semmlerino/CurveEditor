#!/usr/bin/env python
"""
Tests for standardized error handling utilities.

Phase 1.4: Error Handling Pattern Consolidation
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from core.error_handling import (
    safe_execute,
    safe_execute_optional,
    safe_operation,
    safe_operation_optional,
)

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture


# ==================== Test Fixtures ====================


class SuccessOperation:
    """Test class with successful operations."""

    @safe_operation("test operation")
    def do_work(self) -> bool:
        """Operation that succeeds."""
        return True

    @safe_operation_optional("load data")
    def load_data(self) -> dict[str, str] | None:
        """Operation that returns data."""
        return {"key": "value"}


class FailingOperation:
    """Test class with failing operations."""

    @safe_operation("test operation")
    def do_work(self) -> bool:
        """Operation that raises exception."""
        raise ValueError("Test error")

    @safe_operation_optional("load data")
    def load_data(self) -> dict[str, str] | None:
        """Operation that raises exception."""
        raise RuntimeError("Load failed")


# ==================== safe_execute Tests ====================


def test_safe_execute_success():
    """Test safe_execute with successful operation."""

    def operation() -> bool:
        return True

    result = safe_execute("test operation", operation)
    assert result is True


def test_safe_execute_failure():
    """Test safe_execute with failing operation (returns False)."""

    def operation() -> bool:
        return False

    result = safe_execute("test operation", operation)
    assert result is False


def test_safe_execute_exception(caplog: LogCaptureFixture):
    """Test safe_execute with operation that raises exception."""

    def operation() -> bool:
        raise ValueError("Test error")

    with caplog.at_level(logging.ERROR):
        result = safe_execute("test operation", operation)

    assert result is False
    assert "Error test operation: Test error" in caplog.text


def test_safe_execute_with_context(caplog: LogCaptureFixture):
    """Test safe_execute with context string."""

    def operation() -> bool:
        raise RuntimeError("Context error")

    with caplog.at_level(logging.ERROR):
        result = safe_execute("processing", operation, "MyClass")

    assert result is False
    assert "Error processing in MyClass: Context error" in caplog.text


def test_safe_execute_various_exceptions(caplog: LogCaptureFixture):
    """Test safe_execute handles various exception types."""
    exceptions = [
        ValueError("value error"),
        RuntimeError("runtime error"),
        KeyError("key error"),
        TypeError("type error"),
        AttributeError("attr error"),
    ]

    for exc in exceptions:

        def operation(e=exc) -> bool:
            raise e

        with caplog.at_level(logging.ERROR):
            result = safe_execute("test", operation)

        assert result is False
        assert str(exc) in caplog.text
        caplog.clear()


# ==================== safe_execute_optional Tests ====================


def test_safe_execute_optional_success():
    """Test safe_execute_optional with successful operation."""

    def operation() -> dict[str, str] | None:
        return {"key": "value"}

    result = safe_execute_optional("load data", operation)
    assert result == {"key": "value"}


def test_safe_execute_optional_none_result():
    """Test safe_execute_optional with operation that returns None."""

    def operation() -> dict[str, str] | None:
        return None

    result = safe_execute_optional("load data", operation)
    assert result is None


def test_safe_execute_optional_exception(caplog: LogCaptureFixture):
    """Test safe_execute_optional with operation that raises exception."""

    def operation() -> dict[str, str] | None:
        raise ValueError("Load error")

    with caplog.at_level(logging.ERROR):
        result = safe_execute_optional("load data", operation)

    assert result is None
    assert "Error load data: Load error" in caplog.text


def test_safe_execute_optional_with_context(caplog: LogCaptureFixture):
    """Test safe_execute_optional with context string."""

    def operation() -> list[int] | None:
        raise RuntimeError("Context error")

    with caplog.at_level(logging.ERROR):
        result = safe_execute_optional("parsing", operation, "DataLoader")

    assert result is None
    assert "Error parsing in DataLoader: Context error" in caplog.text


def test_safe_execute_optional_various_types():
    """Test safe_execute_optional with various return types."""

    def dict_op() -> dict[str, str] | None:
        return {"key": "value"}

    def list_op() -> list[int] | None:
        return [1, 2, 3]

    def str_op() -> str | None:
        return "result"

    def int_op() -> int | None:
        return 42

    assert safe_execute_optional("dict", dict_op) == {"key": "value"}
    assert safe_execute_optional("list", list_op) == [1, 2, 3]
    assert safe_execute_optional("str", str_op) == "result"
    assert safe_execute_optional("int", int_op) == 42


# ==================== @safe_operation Decorator Tests ====================


def test_safe_operation_decorator_success():
    """Test @safe_operation decorator with successful operation."""
    obj = SuccessOperation()
    result = obj.do_work()
    assert result is True


def test_safe_operation_decorator_exception(caplog: LogCaptureFixture):
    """Test @safe_operation decorator with exception."""
    obj = FailingOperation()

    with caplog.at_level(logging.ERROR):
        result = obj.do_work()

    assert result is False
    assert "Error test operation in FailingOperation: Test error" in caplog.text


def test_safe_operation_decorator_inferred_name(caplog: LogCaptureFixture):
    """Test @safe_operation decorator with inferred operation name."""

    class TestClass:
        @safe_operation()
        def process_data(self) -> bool:
            raise ValueError("Processing failed")

    obj = TestClass()
    with caplog.at_level(logging.ERROR):
        result = obj.process_data()

    assert result is False
    # Function name "process_data" should be converted to "process data"
    assert "Error process data in TestClass: Processing failed" in caplog.text


def test_safe_operation_decorator_custom_context(caplog: LogCaptureFixture):
    """Test @safe_operation decorator with custom context."""

    class TestClass:
        @safe_operation("custom op", "CustomContext")
        def do_work(self) -> bool:
            raise RuntimeError("Custom error")

    obj = TestClass()
    with caplog.at_level(logging.ERROR):
        result = obj.do_work()

    assert result is False
    assert "Error custom op in CustomContext: Custom error" in caplog.text


def test_safe_operation_decorator_no_self():
    """Test @safe_operation decorator on function (not method)."""

    @safe_operation("test function")
    def standalone_function() -> bool:
        return True

    result = standalone_function()
    assert result is True


def test_safe_operation_decorator_no_self_exception(caplog: LogCaptureFixture):
    """Test @safe_operation decorator on function that raises exception."""

    @safe_operation("test function")
    def standalone_function() -> bool:
        raise ValueError("Function error")

    with caplog.at_level(logging.ERROR):
        result = standalone_function()

    assert result is False
    assert "Error test function: Function error" in caplog.text


# ==================== @safe_operation_optional Decorator Tests ====================


def test_safe_operation_optional_decorator_success():
    """Test @safe_operation_optional decorator with successful operation."""
    obj = SuccessOperation()
    result = obj.load_data()
    assert result == {"key": "value"}


def test_safe_operation_optional_decorator_exception(caplog: LogCaptureFixture):
    """Test @safe_operation_optional decorator with exception."""
    obj = FailingOperation()

    with caplog.at_level(logging.ERROR):
        result = obj.load_data()

    assert result is None
    assert "Error load data in FailingOperation: Load failed" in caplog.text


def test_safe_operation_optional_decorator_inferred_name(caplog: LogCaptureFixture):
    """Test @safe_operation_optional decorator with inferred name."""

    class TestClass:
        @safe_operation_optional()
        def parse_file(self) -> dict[str, str] | None:
            raise ValueError("Parse failed")

    obj = TestClass()
    with caplog.at_level(logging.ERROR):
        result = obj.parse_file()

    assert result is None
    # Function name "parse_file" should be converted to "parse file"
    assert "Error parse file in TestClass: Parse failed" in caplog.text


def test_safe_operation_optional_decorator_custom_context(caplog: LogCaptureFixture):
    """Test @safe_operation_optional decorator with custom context."""

    class TestClass:
        @safe_operation_optional("custom load", "FileLoader")
        def load(self) -> list[int] | None:
            raise RuntimeError("Load error")

    obj = TestClass()
    with caplog.at_level(logging.ERROR):
        result = obj.load()

    assert result is None
    assert "Error custom load in FileLoader: Load error" in caplog.text


def test_safe_operation_optional_decorator_none_result():
    """Test @safe_operation_optional decorator with None result."""

    class TestClass:
        @safe_operation_optional("load data")
        def load(self) -> dict[str, str] | None:
            return None

    obj = TestClass()
    result = obj.load()
    assert result is None


def test_safe_operation_optional_decorator_no_self():
    """Test @safe_operation_optional decorator on function."""

    @safe_operation_optional("load config")
    def load_config() -> dict[str, str] | None:
        return {"config": "value"}

    result = load_config()
    assert result == {"config": "value"}


# ==================== Integration Tests ====================


def test_nested_error_handling(caplog: LogCaptureFixture):
    """Test nested error handling with both utilities."""

    class OuterClass:
        @safe_operation("outer operation")
        def outer(self) -> bool:
            # Call inner operation
            result = self._inner()
            return result is not None

        @safe_operation_optional("inner operation")
        def _inner(self) -> dict[str, str] | None:
            raise ValueError("Inner error")

    obj = OuterClass()
    with caplog.at_level(logging.ERROR):
        result = obj.outer()

    # Both errors should be logged
    assert result is False
    assert "Error inner operation in OuterClass: Inner error" in caplog.text
    # outer() returns False because _inner() returns None


def test_error_handling_preserves_return_semantics():
    """Test that error handling preserves exact return type semantics."""

    # Boolean return - False is valid, not error
    @safe_operation("bool test")
    def bool_false() -> bool:
        return False

    assert bool_false() is False  # Not None, actual False

    # Optional return - None is valid, not error
    @safe_operation_optional("optional test")
    def optional_none() -> int | None:
        return None

    assert optional_none() is None  # Valid None result


def test_multiple_exceptions_in_sequence(caplog: LogCaptureFixture):
    """Test handling multiple exceptions in sequence."""

    @safe_operation("operation")
    def failing_op() -> bool:
        raise ValueError("Test error")

    with caplog.at_level(logging.ERROR):
        # Call multiple times
        result1 = failing_op()
        result2 = failing_op()
        result3 = failing_op()

    assert result1 is False
    assert result2 is False
    assert result3 is False
    # Should have 3 error log entries
    assert caplog.text.count("Error operation: Test error") == 3


# ==================== Edge Cases ====================


def test_safe_execute_with_args_and_kwargs():
    """Test safe_execute with operation that uses closure."""

    value = 42

    def operation() -> bool:
        # Access closure variable
        return value == 42

    result = safe_execute("closure test", operation)
    assert result is True


def test_decorator_with_method_args():
    """Test decorator on method with arguments."""

    class TestClass:
        @safe_operation("process")
        def process(self, value: int) -> bool:
            return value > 0

    obj = TestClass()
    assert obj.process(10) is True
    assert obj.process(-5) is False


def test_decorator_with_method_args_exception(caplog: LogCaptureFixture):
    """Test decorator on method with arguments that raises exception."""

    class TestClass:
        @safe_operation("process")
        def process(self, value: int) -> bool:
            if value < 0:
                raise ValueError("Negative value")
            return True

    obj = TestClass()
    with caplog.at_level(logging.ERROR):
        result = obj.process(-5)

    assert result is False
    assert "Error process in TestClass: Negative value" in caplog.text


def test_safe_execute_empty_operation_name(caplog: LogCaptureFixture):
    """Test error handling with empty operation name."""

    def operation() -> bool:
        raise ValueError("Test error")

    with caplog.at_level(logging.ERROR):
        result = safe_execute("", operation)

    assert result is False
    assert "Error : Test error" in caplog.text


def test_decorator_preserves_docstring():
    """Test that decorators preserve function docstrings."""

    @safe_operation("test")
    def documented_function() -> bool:
        """This is a docstring."""
        return True

    assert documented_function.__doc__ == "This is a docstring."
    assert documented_function.__name__ == "documented_function"


def test_error_message_format_consistency(caplog: LogCaptureFixture):
    """Test that all error messages follow consistent format.

    Expected formats:
        - "Error {operation}: {error}"
        - "Error {operation} in {context}: {error}"
    """
    # Test function variant
    def op1() -> bool:
        raise ValueError("error1")

    with caplog.at_level(logging.ERROR):
        safe_execute("op1", op1)
    assert "Error op1: error1" in caplog.text
    caplog.clear()

    # Test context variant
    def op2() -> bool:
        raise ValueError("error2")

    with caplog.at_level(logging.ERROR):
        safe_execute("op2", op2, "Context")
    assert "Error op2 in Context: error2" in caplog.text

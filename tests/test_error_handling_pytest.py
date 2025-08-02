#!/usr/bin/env python

"""
Pytest tests for error_handling.py
"""

import pytest

from utils.error_handling import safe_operation, show_error
from tests.conftest import BaseMockMainWindow


class MockMainWindow(BaseMockMainWindow):
    def __init__(self):
        super().__init__()
        self.last_message = None
        self.timeout = 0

    def showMessage(self, message, timeout=0):
        self.last_message = message
        self.timeout = timeout


@pytest.fixture
def main_window():
    """Fixture that provides a mock main window."""
    return MockMainWindow()


def test_safe_operation_with_history(main_window):
    """Test that safe_operation records history when specified."""

    @safe_operation("Test Operation", record_history=True)
    def sample_operation(main_window):
        return True

    # Execute the operation
    result = sample_operation(main_window)

    assert result is True
    assert main_window.history_added is True
    assert "completed successfully" in main_window.last_message


def test_safe_operation_without_history(main_window):
    """Test that safe_operation doesn't record history when specified."""

    @safe_operation("Test Operation", record_history=False)
    def sample_operation(main_window):
        return True

    # Execute the operation
    result = sample_operation(main_window)

    assert result is True
    assert main_window.history_added is False
    assert "completed successfully" in main_window.last_message


def test_safe_operation_with_exception(main_window, monkeypatch):
    """Test that safe_operation handles exceptions properly."""

    # Mock QMessageBox to avoid UI dialogs during tests
    class MockQMessageBox:
        @staticmethod
        def critical(*args, **kwargs):
            return None

    monkeypatch.setattr("error_handling.QMessageBox", MockQMessageBox)

    @safe_operation("Test Operation")
    def failing_operation(main_window):
        raise ValueError("Test error")

    # Execute the operation that will raise an exception
    result = failing_operation(main_window)

    assert result is None
    assert main_window.history_added is False
    assert "Error" in main_window.last_message


def test_show_error(monkeypatch):
    """Test the show_error function."""

    executed = False

    # Mock QMessageBox and its methods
    class MockQMessageBox:
        def __init__(self, *args):
            pass

        def setIcon(self, *args):
            pass

        def setWindowTitle(self, title):
            self.title = title

        def setText(self, text):
            self.text = text

        def setDetailedText(self, text):
            self.detailed_text = text

        def setStandardButtons(self, *args):
            pass

        def exec_(self):
            nonlocal executed
            executed = True

    monkeypatch.setattr("error_handling.QMessageBox", MockQMessageBox)

    # Test the function
    show_error(None, "Test Error", "This is a test error", "Detailed info")

    assert executed is True

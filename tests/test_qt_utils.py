"""Tests for Qt utility functions and decorators."""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

import logging
from unittest.mock import patch

from PySide6.QtWidgets import QWidget

from ui.qt_utils import safe_slot, safe_slot_logging


class TestSafeSlot:
    """Test cases for the safe_slot decorator."""

    def test_normal_execution(self, qtbot):
        """Decorator doesn't interfere with normal method execution."""

        class TestWidget(QWidget):
            def __init__(self):
                super().__init__()
                self.executed = False
                self.result = None

            @safe_slot
            def handler(self, value: int) -> int:
                self.executed = True
                return value * 2

        widget = TestWidget()
        qtbot.addWidget(widget)

        # Execute handler
        result = widget.handler(5)

        # Verify normal execution
        assert widget.executed is True
        assert result == 10

    def test_widget_being_destroyed(self, qtbot):
        """Returns None without executing when widget is being destroyed."""

        class TestWidget(QWidget):
            def __init__(self):
                super().__init__()
                self.executed = False

            @safe_slot
            def handler(self, value: int) -> int:
                self.executed = True
                return value * 2

        widget = TestWidget()
        qtbot.addWidget(widget)

        # Simulate widget being destroyed by mocking isVisible to raise RuntimeError
        with patch.object(widget, "isVisible", side_effect=RuntimeError("C++ object deleted")):
            result = widget.handler(5)

        # Verify handler didn't execute and returned None
        assert widget.executed is False
        assert result is None

    def test_non_widget_object(self):
        """Executes normally for non-widget objects (no isVisible attribute)."""

        class NonWidget:
            def __init__(self):
                self.executed = False

            @safe_slot
            def handler(self, value: int) -> int:
                self.executed = True
                return value * 2

        obj = NonWidget()

        # Execute handler on non-widget object
        result = obj.handler(5)

        # Verify normal execution (AttributeError on isVisible is caught)
        assert obj.executed is True
        assert result == 10

    def test_logging_on_destruction(self, qtbot, caplog):
        """Logs debug message when widget is being destroyed."""

        class TestWidget(QWidget):
            @safe_slot
            def handler(self) -> None:
                pass

        widget = TestWidget()
        qtbot.addWidget(widget)

        # Capture log messages at DEBUG level
        with caplog.at_level(logging.DEBUG), patch.object(widget, "isVisible", side_effect=RuntimeError("destroyed")):
            widget.handler()

        # Verify debug log message
        assert any("Skipped handler - widget being destroyed" in record.message for record in caplog.records)


class TestSafeSlotLogging:
    """Test cases for the safe_slot_logging decorator."""

    def test_verbose_logging(self, qtbot, caplog):
        """Logs at INFO level when verbose=True."""

        class TestWidget(QWidget):
            @safe_slot_logging(verbose=True)
            def handler(self) -> None:
                pass

        widget = TestWidget()
        qtbot.addWidget(widget)

        # Capture log messages at INFO level
        with caplog.at_level(logging.INFO), patch.object(widget, "isVisible", side_effect=RuntimeError("destroyed")):
            widget.handler()

        # Verify info-level log message
        info_messages = [record for record in caplog.records if record.levelname == "INFO"]
        assert len(info_messages) == 1
        assert "Widget destroyed - skipped handler" in info_messages[0].message

    def test_non_verbose_logging(self, qtbot, caplog):
        """Logs at DEBUG level when verbose=False."""

        class TestWidget(QWidget):
            @safe_slot_logging(verbose=False)
            def handler(self) -> None:
                pass

        widget = TestWidget()
        qtbot.addWidget(widget)

        # Capture log messages at DEBUG level
        with caplog.at_level(logging.DEBUG), patch.object(widget, "isVisible", side_effect=RuntimeError("destroyed")):
            widget.handler()

        # Verify debug-level log message
        debug_messages = [record for record in caplog.records if record.levelname == "DEBUG"]
        assert len(debug_messages) == 1
        assert "Widget destroyed - skipped handler" in debug_messages[0].message

    def test_widget_destruction_handling(self, qtbot):
        """Handles widget destruction same as safe_slot."""

        class TestWidget(QWidget):
            def __init__(self):
                super().__init__()
                self.executed = False

            @safe_slot_logging(verbose=True)
            def handler(self, value: int) -> int:
                self.executed = True
                return value * 2

        widget = TestWidget()
        qtbot.addWidget(widget)

        # Simulate widget being destroyed
        with patch.object(widget, "isVisible", side_effect=RuntimeError("destroyed")):
            result = widget.handler(5)

        # Verify handler didn't execute and returned None
        assert widget.executed is False
        assert result is None

    def test_normal_execution_with_verbose(self, qtbot):
        """Decorator doesn't interfere with normal execution (verbose mode)."""

        class TestWidget(QWidget):
            def __init__(self):
                super().__init__()
                self.executed = False

            @safe_slot_logging(verbose=True)
            def handler(self, value: int) -> int:
                self.executed = True
                return value * 2

        widget = TestWidget()
        qtbot.addWidget(widget)

        # Execute handler
        result = widget.handler(5)

        # Verify normal execution
        assert widget.executed is True
        assert result == 10

    def test_non_widget_object_with_logging(self):
        """Executes normally for non-widget objects with logging decorator."""

        class NonWidget:
            def __init__(self):
                self.executed = False

            @safe_slot_logging(verbose=False)
            def handler(self, value: int) -> int:
                self.executed = True
                return value * 2

        obj = NonWidget()

        # Execute handler on non-widget object
        result = obj.handler(5)

        # Verify normal execution (AttributeError on isVisible is caught)
        assert obj.executed is True
        assert result == 10

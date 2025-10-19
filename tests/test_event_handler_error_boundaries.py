#!/usr/bin/env python3
"""
Error boundary tests for event handlers in InteractionService.

This test suite verifies that all event handlers properly catch and log exceptions
without crashing the UI. Each handler should:
- Catch all exceptions within try/except block
- Log exceptions with exc_info=True for full stack traces
- Prevent exceptions from propagating to Qt event loop
- Maintain valid application state after errors

Phase 2 (Robustness & Complexity) requirement: Error boundaries for all 5 handlers.
"""

# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportUninitializedInstanceVariable=none

from typing import TYPE_CHECKING, Any
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent

from services import get_interaction_service
from stores.application_state import get_application_state
from tests.test_helpers import MockCurveView

if TYPE_CHECKING:
    from _pytest.logging import LogCaptureFixture

    from services.interaction_service import InteractionService


class TestMousePressErrorBoundary:
    """Test error boundary for handle_mouse_press."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp: Any) -> None:
        """Setup test environment."""
        self.service: InteractionService = get_interaction_service()
        self.app_state = get_application_state()

    def test_exception_is_caught_and_logged(self, caplog: "LogCaptureFixture") -> None:
        """Test that exceptions in mouse press handler are caught and logged."""
        view = MockCurveView([])

        # Patch to raise exception
        def raise_error(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("Injected mouse press error")

        with patch.object(self.service._selection, "find_point_at", side_effect=raise_error):
            event = Mock(spec=QMouseEvent)
            event.button.return_value = Qt.MouseButton.LeftButton
            event.position.return_value = QPoint(100, 100)
            event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

            # Should not raise
            with caplog.at_level("ERROR"):
                self.service.handle_mouse_press(view, event)

            # Verify logged
            assert "Error in mouse press handler" in caplog.text
            assert "Injected mouse press error" in caplog.text


class TestMouseMoveErrorBoundary:
    """Test error boundary for handle_mouse_move."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp: Any) -> None:
        """Setup test environment."""
        self.service: InteractionService = get_interaction_service()
        self.app_state = get_application_state()

    def test_exception_is_caught_and_logged(self, caplog: "LogCaptureFixture") -> None:
        """Test that exceptions in mouse move handler are caught."""
        view = MockCurveView([(1, 100.0, 100.0)])
        self.app_state.set_curve_data("test_curve", view.curve_data)
        self.app_state.set_active_curve("test_curve")

        # Set up drag state
        view.drag_active = True
        view.drag_start_pos = QPoint(100, 100)

        # Patch view.update to raise exception
        def raise_error(*args: Any, **kwargs: Any) -> None:
            raise RuntimeError("Injected move error")

        with patch.object(view, "update", side_effect=raise_error):
            event = Mock(spec=QMouseEvent)
            event.position.return_value = QPoint(110, 110)
            event.buttons.return_value = Qt.MouseButton.LeftButton

            with caplog.at_level("ERROR"):
                self.service.handle_mouse_move(view, event)

            assert "Error in mouse move handler" in caplog.text
            assert "Injected move error" in caplog.text


class TestMouseReleaseErrorBoundary:
    """Test error boundary for handle_mouse_release."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp: Any) -> None:
        """Setup test environment."""
        self.service: InteractionService = get_interaction_service()
        self.app_state = get_application_state()

    def test_exception_is_caught_and_logged(self, caplog: "LogCaptureFixture") -> None:
        """Test that exceptions in mouse release handler are caught."""
        view = MockCurveView([])

        # Set up rubber band state
        view.rubber_band_active = True
        view.rubber_band_start = QPoint(50, 50)

        # Patch view.update to raise exception
        def raise_error(*args: Any, **kwargs: Any) -> None:
            raise ValueError("Injected release error")

        with patch.object(view, "update", side_effect=raise_error):
            event = Mock(spec=QMouseEvent)
            event.button.return_value = Qt.MouseButton.LeftButton
            event.position.return_value = QPoint(150, 150)

            with caplog.at_level("ERROR"):
                self.service.handle_mouse_release(view, event)

            assert "Error in mouse release handler" in caplog.text
            assert "Injected release error" in caplog.text


class TestWheelEventErrorBoundary:
    """Test error boundary for handle_wheel_event."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp: Any) -> None:
        """Setup test environment."""
        self.service: InteractionService = get_interaction_service()
        self.app_state = get_application_state()

    def test_exception_is_caught_and_logged(self, caplog: "LogCaptureFixture") -> None:
        """Test that exceptions in wheel event handler are caught."""
        view = MockCurveView([])

        # Create event that raises exception
        event = Mock(spec=QWheelEvent)
        event.angleDelta.side_effect = RuntimeError("Injected wheel error")
        event.position.return_value = QPoint(100, 100)

        with caplog.at_level("ERROR"):
            self.service.handle_wheel_event(view, event)

        assert "Error in wheel event handler" in caplog.text
        assert "Injected wheel error" in caplog.text


class TestKeyEventErrorBoundary:
    """Test error boundary for handle_key_event."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp: Any) -> None:
        """Setup test environment."""
        self.service: InteractionService = get_interaction_service()
        self.app_state = get_application_state()

    def test_exception_is_caught_and_logged(self, caplog: "LogCaptureFixture") -> None:
        """Test that exceptions in key event handler are caught."""
        view = MockCurveView([])

        # Create event that raises exception when key() is called
        event = Mock(spec=QKeyEvent)
        event.key.side_effect = RuntimeError("Injected key error")
        event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

        with caplog.at_level("ERROR"):
            self.service.handle_key_event(view, event)

        assert "Error in key event handler" in caplog.text
        assert "Injected key error" in caplog.text


class TestErrorBoundaryLoggingFormat:
    """Test that error boundaries log with exc_info=True."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp: Any) -> None:
        """Setup test environment."""
        self.service: InteractionService = get_interaction_service()
        self.app_state = get_application_state()

    def test_exc_info_includes_traceback(self, caplog: "LogCaptureFixture") -> None:
        """Test that exc_info=True captures traceback."""
        view = MockCurveView([])

        # Create nested exception
        def raise_nested(*args: Any, **kwargs: Any) -> Any:
            def inner() -> None:
                raise RuntimeError("Deep error")

            inner()

        with patch.object(self.service._selection, "find_point_at", side_effect=raise_nested):
            event = Mock(spec=QMouseEvent)
            event.button.return_value = Qt.MouseButton.LeftButton
            event.position.return_value = QPoint(100, 100)
            event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

            with caplog.at_level("ERROR"):
                self.service.handle_mouse_press(view, event)

            # Verify traceback present
            assert "Error in mouse press handler" in caplog.text
            assert "Deep error" in caplog.text
            # Verify traceback indicators (exc_info=True)
            assert "Traceback" in caplog.text or "inner" in caplog.text


class TestErrorBoundaryStateConsistency:
    """Test that state remains valid after exceptions."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp: Any) -> None:
        """Setup test environment."""
        self.service: InteractionService = get_interaction_service()
        self.app_state = get_application_state()

    def test_state_unchanged_after_error(self, caplog: "LogCaptureFixture") -> None:
        """Test that state is unchanged after exception."""
        view = MockCurveView([(1, 100.0, 100.0)])
        self.app_state.set_curve_data("test_curve", view.curve_data)
        self.app_state.set_active_curve("test_curve")

        # Store original
        original_data = self.app_state.get_curve_data("test_curve")

        # Inject exception
        def raise_error(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("Test error")

        with patch.object(self.service._selection, "find_point_at", side_effect=raise_error):
            event = Mock(spec=QMouseEvent)
            event.button.return_value = Qt.MouseButton.LeftButton
            event.position.return_value = QPoint(100, 100)
            event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

            with caplog.at_level("ERROR"):
                self.service.handle_mouse_press(view, event)

        # Verify unchanged
        assert self.app_state.get_curve_data("test_curve") == original_data
        assert self.app_state.active_curve == "test_curve"

    def test_service_functional_after_error(self, caplog: "LogCaptureFixture") -> None:
        """Test that service works after exception."""
        view = MockCurveView([(1, 100.0, 100.0)])
        self.app_state.set_curve_data("test_curve", view.curve_data)
        self.app_state.set_active_curve("test_curve")

        # First call with exception
        def raise_error(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("First error")

        with patch.object(self.service._selection, "find_point_at", side_effect=raise_error):
            event = Mock(spec=QMouseEvent)
            event.button.return_value = Qt.MouseButton.LeftButton
            event.position.return_value = QPoint(100, 100)
            event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

            with caplog.at_level("ERROR"):
                self.service.handle_mouse_press(view, event)

            assert "Error in mouse press handler" in caplog.text

        # Second call without exception should work
        caplog.clear()
        event2 = Mock(spec=QMouseEvent)
        event2.button.return_value = Qt.MouseButton.LeftButton
        event2.position.return_value = QPoint(100, 100)
        event2.modifiers.return_value = Qt.KeyboardModifier.NoModifier

        self.service.handle_mouse_press(view, event2)
        assert "Error in mouse press handler" not in caplog.text

    def test_multiple_consecutive_errors_handled(self, caplog: "LogCaptureFixture") -> None:
        """Test that service handles multiple consecutive errors without state corruption."""
        view = MockCurveView([])

        def raise_error(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("Repeated error")

        with patch.object(self.service._selection, "find_point_at", side_effect=raise_error):
            # Trigger 3 errors in a row
            for i in range(3):
                event = Mock(spec=QMouseEvent)
                event.button.return_value = Qt.MouseButton.LeftButton
                event.position.return_value = QPoint(100, 100)
                event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

                with caplog.at_level("ERROR"):
                    self.service.handle_mouse_press(view, event)

        # Should have 3 error logs (verifies no state accumulation across errors)
        assert caplog.text.count("Error in mouse press handler") == 3

    def test_exception_during_state_update(self, caplog: "LogCaptureFixture") -> None:
        """Test that exceptions during ApplicationState updates are caught.

        This tests the critical path where data corruption is most likely - during
        actual state mutations in set_curve_data().
        """
        view = MockCurveView([(1, 100.0, 100.0)])
        self.app_state.set_curve_data("test_curve", view.curve_data)
        self.app_state.set_active_curve("test_curve")

        view.drag_active = True
        view.last_drag_pos = QPoint(100, 100)
        view.selected_points = {0}

        # Inject error during state mutation (critical untested path)
        with patch.object(self.app_state, "set_curve_data", side_effect=RuntimeError("State mutation error")):
            event = Mock(spec=QMouseEvent)
            event.position.return_value = QPoint(110, 110)
            event.buttons.return_value = Qt.MouseButton.LeftButton

            with caplog.at_level("ERROR"):
                self.service.handle_mouse_move(view, event)

        # Verify error was caught and logged
        assert "Error in mouse move handler" in caplog.text
        assert "State mutation error" in caplog.text

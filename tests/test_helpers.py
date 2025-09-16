#!/usr/bin/env python3
"""
Unified Test Helpers for CurveEditor

Following best practices from UNIFIED_TESTING_GUIDE_DO_NOT_DELETE.md:
- Real components over mocks
- Thread-safe image handling (QImage instead of QPixmap)
- Proper signal test doubles
- Test behavior, not implementation
"""

from collections.abc import Callable
from typing import Any
from unittest.mock import Mock

from core.models import CurvePoint

# Qt imports with fallback for non-GUI environments
try:
    from PySide6.QtCore import QObject, QSize
    from PySide6.QtGui import QColor, QImage
    from PySide6.QtWidgets import QMainWindow, QStatusBar

    HAS_QT = True
except ImportError:
    HAS_QT = False

    # Stub classes for non-Qt test environments
    class QObject:
        pass

    class QSize:
        def __init__(self, w: int, h: int) -> None:
            self.w = w
            self.h = h

    class QImage:
        Format_RGB32 = None

        def __init__(self, *args: Any) -> None:
            pass

        def fill(self, color: Any) -> None:
            pass

        def isNull(self) -> bool:
            return False

        def sizeInBytes(self) -> int:
            return 0

    class QColor:
        def __init__(self, *args: Any) -> None:
            pass


# ==================== Thread-Safe Image Handling ====================


class ThreadSafeTestImage:
    """
    Thread-safe test double for QPixmap using QImage internally.

    Based on Qt's canonical threading pattern from the testing guide.
    QPixmap is not thread-safe and can only be used in the main GUI thread.
    QImage is thread-safe and can be used in any thread.

    This class provides a QPixmap-like interface while using QImage internally
    for thread safety in tests.
    """

    def __init__(self, width: int = 100, height: int = 100) -> None:
        """Create a thread-safe test image."""
        # Use QImage which is thread-safe, unlike QPixmap
        if HAS_QT:
            self._image = QImage(width, height, QImage.Format_RGB32)
            self._image.fill(QColor(255, 255, 255))  # White by default
        else:
            self._image = None
        self._width = width
        self._height = height

    def fill(self, color: QColor | None = None) -> None:
        """Fill the image with a color."""
        if HAS_QT and self._image:
            if color is None:
                color = QColor(255, 255, 255)
            self._image.fill(color)

    def isNull(self) -> bool:
        """Check if the image is null."""
        if HAS_QT and self._image:
            return self._image.isNull()
        return False

    def sizeInBytes(self) -> int:
        """Return the size of the image in bytes."""
        if HAS_QT and self._image:
            return self._image.sizeInBytes()
        return self._width * self._height * 4  # Approximate

    def size(self) -> QSize:
        """Return the size of the image."""
        return QSize(self._width, self._height)

    def width(self) -> int:
        """Return image width."""
        return self._width

    def height(self) -> int:
        """Return image height."""
        return self._height

    def to_qimage(self) -> QImage | None:
        """Get the internal QImage for Qt operations."""
        return self._image if HAS_QT else None


class TestImagePool:
    """
    Reuse ThreadSafeTestImage instances for performance.

    Reduces object creation overhead in tests with many image operations.
    """

    def __init__(self):
        self._pool = []

    def get_test_image(self, width: int = 100, height: int = 100) -> ThreadSafeTestImage:
        """Get a test image from the pool or create a new one."""
        # For now, just create new ones (could optimize later)
        # Pool implementation would check dimensions and reuse
        return ThreadSafeTestImage(width, height)

    def return_image(self, image: ThreadSafeTestImage) -> None:
        """Return an image to the pool for reuse."""
        # Reset to white before returning to pool
        image.fill()
        self._pool.append(image)


# ==================== Signal Test Doubles ====================


class TestSignal:
    """
    Lightweight signal test double for non-Qt components.

    Use this instead of Mock for signal testing in test doubles.
    For real Qt widgets, use QSignalSpy instead.
    """

    def __init__(self):
        self.emissions = []
        self.callbacks = []

    def emit(self, *args):
        """Emit signal with arguments."""
        self.emissions.append(args)
        for callback in self.callbacks:
            try:
                callback(*args)
            except Exception as e:
                # Log but don't fail on callback errors
                print(f"TestSignal callback error: {e}")

    def connect(self, callback: Callable):
        """Connect callback to signal."""
        self.callbacks.append(callback)

    def disconnect(self, callback: Callable):
        """Disconnect callback from signal."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    @property
    def was_emitted(self) -> bool:
        """Check if signal was emitted at least once."""
        return len(self.emissions) > 0

    @property
    def emit_count(self) -> int:
        """Get number of times signal was emitted."""
        return len(self.emissions)

    @property
    def last_emission(self):
        """Get last emission arguments."""
        return self.emissions[-1] if self.emissions else None

    def reset(self):
        """Clear all emissions for reuse."""
        self.emissions.clear()


# ==================== Qt Component Test Doubles ====================


class MockUIComponents:
    """Mock UI components structure matching real MainWindow.ui interface."""

    def __init__(self):
        self.undo_button = Mock()
        self.redo_button = Mock()
        self.save_button = Mock()


class MockServices:
    """Mock services structure matching real ServiceFacade interface."""

    def __init__(self):
        self.workflow_state = None  # No workflow_state service in current architecture


class MockMainWindow(QMainWindow if HAS_QT else object):
    """
    Real Qt MainWindow for testing with tracking capabilities.

    Provides a real Qt widget hierarchy while tracking interactions
    for test assertions.
    """

    def __init__(self):
        if HAS_QT:
            super().__init__()
            self.status_bar = QStatusBar()
            self.setStatusBar(self.status_bar)
        else:
            self.status_bar = Mock()

        # Track status messages
        self.status_messages = []

        if HAS_QT:
            original_show = self.status_bar.showMessage

            def track_message(msg, timeout=0):
                self.status_messages.append((msg, timeout))
                original_show(msg, timeout)

            self.status_bar.showMessage = track_message

        # Common attributes - using actual MainWindow attribute names
        self.curve_widget = None  # Real MainWindow uses curve_widget
        self.curve_view = None  # Keep for backward compatibility
        self.undo_action = Mock()
        self.redo_action = Mock()

        # UI components structure (for InteractionService compatibility)
        self.ui = MockUIComponents()

        # Services structure (for InteractionService compatibility)
        self.services = MockServices()

        # History management (for MainWindowProtocol compatibility)
        self.history = []
        self.history_index = -1

    @property
    def curve_data(self):
        """Delegate to curve_widget's curve_data for MainWindowProtocol compatibility."""
        # Try curve_widget first (actual MainWindow interface), then curve_view (backward compatibility)
        curve_obj = self.curve_widget or self.curve_view
        if curve_obj and hasattr(curve_obj, "curve_data"):
            return curve_obj.curve_data
        return []

    @curve_data.setter
    def curve_data(self, value):
        """Set curve_data on curve_widget for MainWindowProtocol compatibility."""
        # Try curve_widget first (actual MainWindow interface), then curve_view (backward compatibility)
        curve_obj = self.curve_widget or self.curve_view
        if curve_obj and hasattr(curve_obj, "curve_data"):
            curve_obj.curve_data = value

    def get_curve_view(self):
        """Return the curve view (backward compatibility method)."""
        return self.curve_widget or self.curve_view


class MockCurveView:
    """
    Test double for CurveView with real behavior.

    Provides curve editing functionality without Qt dependencies
    for fast unit testing.
    """

    def __init__(self, points=None):
        """Initialize mock curve view with test data."""
        # Data
        self.curve_data = points or []
        self.selected_points = set()
        self.selected_point_idx = -1

        # Main window reference (for OptimizedCurveRenderer compatibility)
        self.main_window = None

        # CurveViewProtocol required attributes
        self.current_image_idx: int = 0
        self.points = self.curve_data  # Alias for curve_data

        # Transform and positioning attributes
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0
        self.x_offset: float = 0.0  # Alias for offset_x
        self.y_offset: float = 0.0  # Alias for offset_y
        self.zoom_factor: float = 1.0
        self.pan_offset_x: float = 0.0
        self.pan_offset_y: float = 0.0
        self.manual_offset_x: float = 0.0
        self.manual_offset_y: float = 0.0

        # Interaction state attributes
        self.drag_active: bool = False
        self.pan_active: bool = False
        self.last_drag_pos = None  # QtPointF | None
        self.last_pan_pos = None  # QtPointF | None

        # Rubber band selection attributes
        self.rubber_band = None  # QRubberBand | None
        self.rubber_band_active: bool = False
        self.rubber_band_origin = None  # QtPointF

        # Visualization settings
        self.show_grid: bool = False
        self.show_background: bool = True
        self.show_velocity_vectors: bool = False
        self.show_all_frame_numbers: bool = False

        # Background image (for rendering tests compatibility)
        self.background_image = None
        self.background_opacity: float = 1.0

        # Display properties
        self._width = 800
        self._height = 600
        self.image_width = 800
        self.image_height = 600
        self.scale_to_image = True
        self.flip_y_axis = False
        self.debug_mode: bool = False
        self.point_radius: int = 5

        # Interaction state
        self.update_called = False
        self.cursor = None

        # Mock signals for testing
        self.point_selected = TestSignal()
        self.point_moved = TestSignal()

        # Transform
        from services.transform_service import Transform

        self.transform = Transform(scale=1.0, center_offset_x=400, center_offset_y=300)

    def width(self) -> int:
        """Return widget width."""
        return self._width

    def height(self) -> int:
        """Return widget height."""
        return self._height

    def update(self):
        """Mock update method."""
        self.update_called = True

    def get_transform(self):
        """Return current transform."""
        return self.transform

    def mapToGlobal(self, point):
        """Mock mapToGlobal for context menu position."""
        return point

    def setCursor(self, cursor):
        """Mock setCursor method."""
        self.cursor = cursor

    def unsetCursor(self):
        """Mock unsetCursor method."""
        self.cursor = None

    def repaint(self) -> None:
        """Mock repaint method."""
        self.update_called = True

    def findPointAt(self, pos) -> int:
        """Mock findPointAt method."""
        # Simple mock implementation
        return -1

    def pan(self, dx: float, dy: float):
        """Apply pan offset."""
        self.pan_offset_x += dx
        self.pan_offset_y += dy

    def reset(self):
        """Reset view state for test reuse."""
        self.update_called = False
        self.selected_points.clear()
        self.selected_point_idx = -1


# ==================== Factory Fixtures ====================


def make_curve_point(frame: int = 1, x: float = 0.0, y: float = 0.0, point_type: str = "keyframe") -> CurvePoint:
    """
    Factory for creating CurvePoint objects.

    Args:
        frame: Frame number
        x: X coordinate
        y: Y coordinate
        point_type: Point type (keyframe/interpolated)

    Returns:
        CurvePoint instance
    """
    return CurvePoint(frame=frame, x=x, y=y, point_type=point_type)


def make_curve_data(num_points: int = 10) -> list:
    """
    Factory for creating test curve data.

    Args:
        num_points: Number of points to create

    Returns:
        List of CurvePoint instances
    """
    return [make_curve_point(frame=i, x=float(i * 10), y=float(i * 20)) for i in range(1, num_points + 1)]


# ==================== Test Utilities ====================


def assert_qt_container_exists(container, name: str = "container"):
    """
    Safely check Qt container exists (not None).

    Qt containers are falsy when empty, so explicit None check is needed.

    Args:
        container: Qt container to check
        name: Container name for error message
    """
    assert container is not None, f"{name} should not be None"


def safe_qt_cleanup(widget):
    """
    Safely cleanup Qt widget avoiding common pitfalls.

    Args:
        widget: Qt widget to cleanup
    """
    if widget is None:
        return

    try:
        if HAS_QT and hasattr(widget, "deleteLater"):
            widget.deleteLater()
    except RuntimeError:
        # Widget already deleted
        pass


def mock_dialog_exec(dialog_class, return_value=True):
    """
    Create a mock for dialog exec() to prevent blocking.

    Args:
        dialog_class: Dialog class to mock
        return_value: Value to return from exec()

    Returns:
        Mock function for monkeypatch
    """

    def mock_exec(self):
        if HAS_QT:
            from PySide6.QtWidgets import QDialog

            return QDialog.DialogCode.Accepted if return_value else QDialog.DialogCode.Rejected
        return 1 if return_value else 0

    return mock_exec


# ==================== Performance Test Helpers ====================


class PerformanceTimer:
    """
    Simple timer for performance testing.

    Usage:
        with PerformanceTimer("operation") as timer:
            # Do operation
            pass
        print(f"Took {timer.elapsed}ms")
    """

    def __init__(self, name: str = "operation"):
        self.name = name
        self.elapsed = 0

    def __enter__(self):
        import time

        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        import time

        self.elapsed = (time.perf_counter() - self.start) * 1000  # Convert to ms


# ==================== Assertion Helpers ====================


def assert_behavior_changed(obj, attribute: str, operation: Callable, expected_before=None, expected_after=None):
    """
    Assert that behavior changes after an operation.

    Tests behavior, not implementation details.

    Args:
        obj: Object to test
        attribute: Attribute to check
        operation: Operation to perform
        expected_before: Expected value before operation
        expected_after: Expected value after operation
    """
    if expected_before is not None:
        actual_before = getattr(obj, attribute)
        assert actual_before == expected_before, f"Before: expected {attribute}={expected_before}, got {actual_before}"

    operation()

    if expected_after is not None:
        actual_after = getattr(obj, attribute)
        assert actual_after == expected_after, f"After: expected {attribute}={expected_after}, got {actual_after}"


# ==================== Export all helpers ====================

__all__ = [
    # Thread-safe image handling
    "ThreadSafeTestImage",
    "TestImagePool",
    # Signal test doubles
    "TestSignal",
    # Qt component test doubles
    "MockMainWindow",
    "MockCurveView",
    # Factories
    "make_curve_point",
    "make_curve_data",
    # Utilities
    "assert_qt_container_exists",
    "safe_qt_cleanup",
    "mock_dialog_exec",
    # Performance
    "PerformanceTimer",
    # Assertions
    "assert_behavior_changed",
    # Constants
    "HAS_QT",
]

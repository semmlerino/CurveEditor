#!/usr/bin/env python
"""
Qt test helpers for thread-safe testing and proper resource management.

This module provides utilities to avoid common Qt threading issues and
segmentation faults in tests, particularly:
- QPaintDevice destruction while being painted
- QPixmap usage in non-GUI threads
- Proper QPainter lifecycle management
"""

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

from collections.abc import Callable
from contextlib import contextmanager

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage, QPaintDevice, QPainter


class ThreadSafeTestImage:
    """Thread-safe test double for QPixmap using QImage internally.

    QPixmap is not thread-safe and can only be used in the main GUI thread.
    QImage is thread-safe and can be used in any thread. This class provides
    a QPixmap-like interface while using QImage internally for thread safety.

    Based on Qt's canonical threading pattern for image operations.
    """

    def __init__(self, width: int = 100, height: int = 100):
        """Create a thread-safe test image."""
        # Use QImage which is thread-safe, unlike QPixmap
        self._image: QImage = QImage(width, height, QImage.Format.Format_RGB32)
        self._width: int = width
        self._height: int = height
        # Initialize image to prevent garbage data
        self._image.fill(QColor(255, 255, 255))

    def fill(self, color: QColor | None = None) -> None:
        """Fill the image with a color."""
        if color is None:
            color = QColor(255, 255, 255)
        self._image.fill(color)

    def isNull(self) -> bool:
        """Check if the image is null."""
        return self._image.isNull()

    def sizeInBytes(self) -> int:
        """Return the size of the image in bytes."""
        return self._image.sizeInBytes()

    def size(self) -> QSize:
        """Return the size of the image."""
        return QSize(self._width, self._height)

    def width(self) -> int:
        """Return the width of the image."""
        return self._width

    def height(self) -> int:
        """Return the height of the image."""
        return self._height

    def get_qimage(self) -> QImage:
        """Get the underlying QImage for painting operations."""
        return self._image


@contextmanager
def safe_painter(paint_device: QPaintDevice):
    """Context manager for safe QPainter usage.

    Ensures QPainter is properly ended even if exceptions occur,
    preventing "QPaintDevice: Cannot destroy paint device that is being painted" errors.

    Usage:
        image = QImage(800, 600, QImage.Format.Format_RGB32)
        with safe_painter(image) as painter:
            # Do painting operations
            painter.drawLine(0, 0, 100, 100)
        # painter.end() is automatically called

    Args:
        paint_device: QImage, QPixmap, or other QPaintDevice

    Yields:
        QPainter: Active painter for the device
    """
    painter = QPainter()
    try:
        if not painter.begin(paint_device):
            raise RuntimeError(f"Failed to begin painting on {paint_device}")
        yield painter
    finally:
        if painter.isActive():
            _ = painter.end()


def create_test_image(width: int = 800, height: int = 600, fill_color: QColor | None = None) -> QImage:
    """Create a properly initialized QImage for testing.

    Args:
        width: Image width in pixels
        height: Image height in pixels
        fill_color: Optional color to fill the image with

    Returns:
        QImage: Initialized image ready for painting
    """
    image = QImage(width, height, QImage.Format.Format_RGB32)

    # Always initialize to prevent garbage data
    if fill_color is None:
        fill_color = QColor(0, 0, 0)  # Default to black
    image.fill(fill_color)

    return image


def ensure_qapplication():
    """Ensure a QApplication exists for the test.

    Many Qt operations require a QApplication to exist.
    This function ensures one is created if needed.

    Returns:
        QApplication: The application instance
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


class TestSignal:
    """Complete signal test double for non-Qt objects.

    Use this class for testing signals on mock objects or non-Qt components.
    For real Qt objects, use QSignalSpy instead.

    Example usage:
        mock_object = Mock()
        mock_object.signal = TestSignal()

        # Test signal emission
        mock_object.signal.emit(42)
        assert mock_object.signal.was_emitted
        assert mock_object.signal.emit_count == 1
        assert mock_object.signal.emissions[0] == (42,)

        # Test signal connection
        result = []
        mock_object.signal.connect(lambda x: result.append(x))
        mock_object.signal.emit(100)
        assert result == [100]
    """

    def __init__(self):
        """Initialize empty signal test double."""
        self.emissions: list[tuple[object, ...]] = []
        self.callbacks: list[Callable[..., object]] = []

    def emit(self, *args):
        """Emit the signal with given arguments.

        Args:
            *args: Arguments to emit with the signal
        """
        self.emissions.append(args)
        for callback in self.callbacks:
            callback(*args)

    def connect(self, callback):
        """Connect a callback to the signal.

        Args:
            callback: Function to call when signal is emitted
        """
        self.callbacks.append(callback)

    def disconnect(self, callback):
        """Disconnect a callback from the signal.

        Args:
            callback: Function to remove from callbacks
        """
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    @property
    def was_emitted(self):
        """Check if the signal was emitted at least once.

        Returns:
            bool: True if signal was emitted, False otherwise
        """
        return len(self.emissions) > 0

    @property
    def emit_count(self):
        """Get the number of times the signal was emitted.

        Returns:
            int: Number of emissions
        """
        return len(self.emissions)

    def clear(self):
        """Clear all emissions and reset state.

        Useful for reusing the same TestSignal in multiple test phases.
        """
        self.emissions.clear()
        # Note: Keep callbacks connected for reuse

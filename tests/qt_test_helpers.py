#!/usr/bin/env python
"""
Qt test helpers for thread-safe testing and proper resource management.

This module provides utilities to avoid common Qt threading issues and
segmentation faults in tests, particularly:
- QPaintDevice destruction while being painted
- QPixmap usage in non-GUI threads
- Proper QPainter lifecycle management
"""

from contextlib import contextmanager

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QImage, QPainter


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
        self._image = QImage(width, height, QImage.Format.Format_RGB32)
        self._width = width
        self._height = height
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
def safe_painter(paint_device):
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
            painter.end()


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

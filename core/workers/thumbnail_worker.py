"""
Thumbnail generation worker for parallel processing.

This module provides QRunnable-based workers for generating thumbnails
in parallel using QThreadPool, preventing UI blocking.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QRunnable, QSize, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

if TYPE_CHECKING:
    pass

# Configure logger
from core.logger_utils import get_logger

logger = get_logger("thumbnail_worker")


class ThumbnailSignals(QObject):
    """
    Signals for thumbnail worker.

    QRunnable doesn't support signals directly, so we use a QObject wrapper.
    """

    thumbnail_ready = Signal(int, QWidget)  # index, thumbnail_widget
    thumbnail_failed = Signal(int, str)  # index, error_message
    progress = Signal(int, int)  # current, total


class ThumbnailWorker(QRunnable):
    """
    Worker for generating a single thumbnail in background thread pool.

    Use with QThreadPool for parallel thumbnail generation.
    """

    def __init__(
        self,
        index: int,
        image_path: str,
        frame_number: int,
        thumbnail_size: int = 150,
    ):
        """
        Initialize thumbnail worker.

        Args:
            index: Index of this thumbnail in the sequence
            image_path: Path to the image file
            frame_number: Frame number to display
            thumbnail_size: Size of thumbnail in pixels
        """
        super().__init__()
        self.index = index
        self.image_path = image_path
        self.frame_number = frame_number
        self.thumbnail_size = thumbnail_size
        self.signals = ThumbnailSignals()

    @Slot()
    def run(self) -> None:
        """Generate thumbnail in background thread."""
        try:
            logger.debug(f"Generating thumbnail {self.index}: {self.image_path}")

            # Check if file exists
            if not os.path.exists(self.image_path):
                self.signals.thumbnail_failed.emit(self.index, f"File not found: {self.image_path}")
                return

            # Load image (handle EXR specially)
            image_path_obj = Path(self.image_path)
            if image_path_obj.suffix.lower() == ".exr":
                from io_utils.exr_loader import load_exr_as_qpixmap

                pixmap = load_exr_as_qpixmap(self.image_path)
            else:
                pixmap = QPixmap(self.image_path)

            if pixmap is None or pixmap.isNull():
                self.signals.thumbnail_failed.emit(self.index, f"Failed to load: {self.image_path}")
                return

            # Create thumbnail widget
            thumbnail_widget = self._create_thumbnail_widget(pixmap)

            # Emit success signal
            self.signals.thumbnail_ready.emit(self.index, thumbnail_widget)

            logger.debug(f"Thumbnail {self.index} generated successfully")

        except Exception as e:
            logger.error(f"Error generating thumbnail {self.index}: {e}")
            self.signals.thumbnail_failed.emit(self.index, str(e))

    def _create_thumbnail_widget(self, pixmap: QPixmap) -> QWidget:
        """
        Create thumbnail widget from pixmap.

        Args:
            pixmap: Source image pixmap

        Returns:
            QWidget containing thumbnail and frame label
        """
        # Import Qt here to avoid issues with thread safety
        from PySide6.QtCore import Qt

        # Scale to thumbnail size while maintaining aspect ratio
        scaled_pixmap = pixmap.scaled(
            QSize(self.thumbnail_size, self.thumbnail_size),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # Create label with thumbnail
        thumbnail_label = QLabel()
        thumbnail_label.setPixmap(scaled_pixmap)
        thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumbnail_label.setFrameStyle(QLabel.Shape.Box)
        thumbnail_label.setStyleSheet("QLabel { background-color: #2b2b2b; padding: 5px; }")

        # Add frame number below thumbnail
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(thumbnail_label)

        frame_label = QLabel(f"Frame {self.frame_number}")
        frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        frame_label.setStyleSheet("font-size: 9pt; color: #aaa;")
        layout.addWidget(frame_label)

        return container


class ThumbnailBatchLoader(QObject):
    """
    Coordinator for loading multiple thumbnails in parallel.

    Uses QThreadPool to generate thumbnails concurrently while maintaining
    order and progress tracking.
    """

    # Signals
    all_thumbnails_loaded = Signal()  # All thumbnails completed
    thumbnail_ready = Signal(int, QWidget)  # index, widget
    progress_updated = Signal(int, int)  # current, total

    def __init__(self, thumbnail_size: int = 150, max_threads: int = 4):
        """
        Initialize batch loader.

        Args:
            thumbnail_size: Size of thumbnails in pixels
            max_threads: Maximum number of parallel threads
        """
        super().__init__()
        self.thumbnail_size = thumbnail_size
        self.max_threads = max_threads
        self._active_workers = 0
        self._total_workers = 0
        self._completed_workers = 0

    def load_thumbnails(
        self,
        image_paths: list[str],
        frame_numbers: list[int],
    ) -> None:
        """
        Load thumbnails for a list of images.

        Args:
            image_paths: List of image file paths
            frame_numbers: Corresponding frame numbers
        """
        from PySide6.QtCore import QThreadPool

        if len(image_paths) != len(frame_numbers):
            logger.error("Image paths and frame numbers lists must have same length")
            return

        self._total_workers = len(image_paths)
        self._completed_workers = 0
        self._active_workers = 0

        # Create and start workers
        thread_pool = QThreadPool.globalInstance()
        thread_pool.setMaxThreadCount(self.max_threads)

        for idx, (image_path, frame_num) in enumerate(zip(image_paths, frame_numbers)):
            worker = ThumbnailWorker(idx, image_path, frame_num, self.thumbnail_size)

            # Connect signals
            _ = worker.signals.thumbnail_ready.connect(self._on_thumbnail_ready)
            _ = worker.signals.thumbnail_failed.connect(self._on_thumbnail_failed)

            # Start worker
            self._active_workers += 1
            thread_pool.start(worker)

        logger.debug(f"Started batch loading {self._total_workers} thumbnails")

    def _on_thumbnail_ready(self, index: int, widget: QWidget) -> None:
        """Handle thumbnail completion."""
        self._completed_workers += 1
        self._active_workers -= 1

        # Forward signal
        self.thumbnail_ready.emit(index, widget)

        # Update progress
        self.progress_updated.emit(self._completed_workers, self._total_workers)

        # Check if all complete
        if self._completed_workers >= self._total_workers:
            self.all_thumbnails_loaded.emit()
            logger.debug("All thumbnails loaded")

    def _on_thumbnail_failed(self, index: int, error: str) -> None:
        """Handle thumbnail failure."""
        self._completed_workers += 1
        self._active_workers -= 1

        logger.warning(f"Thumbnail {index} failed: {error}")

        # Update progress
        self.progress_updated.emit(self._completed_workers, self._total_workers)

        # Check if all complete
        if self._completed_workers >= self._total_workers:
            self.all_thumbnails_loaded.emit()

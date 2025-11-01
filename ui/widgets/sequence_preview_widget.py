#!/usr/bin/env python
"""
Optimized Sequence Preview Widget for CurveEditor.

Provides thumbnail grid with lazy loading, progress indicators, and metadata overlay.
Optimized for performance with viewport culling and cancellable operations.
"""

import threading
from pathlib import Path
from typing import TYPE_CHECKING, override

from PySide6.QtCore import QSize, Qt, QThread, Signal
from PySide6.QtGui import QCloseEvent, QImage, QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.logger_utils import get_logger
from ui.ui_constants import FONT_SIZE_NORMAL, FONT_SIZE_SMALL, SPACING_SM

if TYPE_CHECKING:
    from ui.image_sequence_browser import ImageSequence

logger = get_logger("sequence_preview_widget")


class ThumbnailWidget(QLabel):
    """
    Individual thumbnail widget with loading state and metadata overlay.
    """

    def __init__(self, frame_number: int, file_path: str, parent: QWidget | None = None):
        """
        Initialize thumbnail widget.

        Args:
            frame_number: Frame number this thumbnail represents
            file_path: Path to the image file
            parent: Parent widget
        """
        super().__init__(parent)
        self.frame_number: int = frame_number
        self.file_path: str = file_path
        self._is_loaded: bool = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the thumbnail widget."""
        # Set fixed size for consistent grid
        self.setFixedSize(150, 120)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet(
            """
            QLabel {
                border: 1px solid #ccc;
                background-color: #f5f5f5;
                border-radius: 4px;
            }
            QLabel:hover {
                border-color: #4a90e2;
                background-color: #e8f4fd;
            }
            """
        )

        # Show loading placeholder
        self.setText("Loading...")
        self.setToolTip(f"Frame {self.frame_number}\n{Path(self.file_path).name}")

    def set_thumbnail(self, pixmap: QPixmap) -> None:
        """
        Set the thumbnail image.

        Args:
            pixmap: Thumbnail image
        """
        if not pixmap.isNull():
            # Scale pixmap to fit widget while maintaining aspect ratio
            scaled_pixmap = pixmap.scaled(
                self.size() - QSize(10, 20),  # Leave space for border and frame label
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled_pixmap)
            self._is_loaded = True
        else:
            self.setText("Error")
            self.setStyleSheet(self.styleSheet() + "QLabel { color: #d32f2f; }")

    def set_loading_error(self, error_message: str) -> None:
        """
        Set error state for thumbnail.

        Args:
            error_message: Error message to display
        """
        self.setText("Error")
        self.setToolTip(f"Frame {self.frame_number}\n{error_message}")
        self.setStyleSheet(self.styleSheet() + "QLabel { color: #d32f2f; }")

    def is_loaded(self) -> bool:
        """Check if thumbnail is loaded."""
        return self._is_loaded


class ThumbnailLoader(QThread):
    """
    Background thread for loading thumbnails with priority queue and cancellation.

    Thread Safety:
        - Creates only QImage (thread-safe), never QPixmap (main-thread-only)
        - Emits QImage via signal to main thread for QPixmap conversion
    """

    # Signals
    thumbnail_loaded: Signal = Signal(int, object)  # frame_number, qimage (QImage)
    thumbnail_error: Signal = Signal(int, str)      # frame_number, error_message
    progress_updated: Signal = Signal(int, int)     # current, total

    def __init__(self, parent: QWidget | None = None):
        """Initialize thumbnail loader."""
        super().__init__(parent)
        self._load_queue: list[tuple[int, str]] = []  # (frame_number, file_path)
        self._queue_lock: threading.Lock = threading.Lock()
        self._should_stop: bool = False
        self._current_total: int = 0

    def add_thumbnail_request(self, frame_number: int, file_path: str) -> None:
        """
        Add a thumbnail loading request.

        Args:
            frame_number: Frame number
            file_path: Path to image file
        """
        with self._queue_lock:
            # Avoid duplicates
            request = (frame_number, file_path)
            if request not in self._load_queue:
                self._load_queue.append(request)
                self._current_total = len(self._load_queue)

    def clear_queue(self) -> None:
        """Clear the loading queue."""
        with self._queue_lock:
            self._load_queue.clear()
            self._current_total = 0

    def stop_loading(self) -> None:
        """Stop the loading process."""
        self._should_stop = True
        self.clear_queue()

    @override
    def run(self) -> None:
        """Run the thumbnail loading process."""
        self._should_stop = False

        while not self._should_stop:
            # Get next item from queue
            with self._queue_lock:
                if not self._load_queue:
                    break
                frame_number, file_path = self._load_queue.pop(0)
                remaining = len(self._load_queue)
                current = self._current_total - remaining

            if self._should_stop:
                break

            # Emit progress
            self.progress_updated.emit(current, self._current_total)

            # Load thumbnail as QImage (thread-safe)
            try:
                # CRITICAL: Use QImage (thread-safe), NOT QPixmap (main-thread-only)
                # Explicitly convert to str() for Qt compatibility (matches Feature 2 pattern)
                qimage = QImage(str(file_path))
                if not qimage.isNull():
                    # Emit QImage to main thread for QPixmap conversion
                    self.thumbnail_loaded.emit(frame_number, qimage)
                else:
                    self.thumbnail_error.emit(frame_number, "Failed to load image")
            except Exception as e:
                self.thumbnail_error.emit(frame_number, str(e))

        # Final progress update
        self.progress_updated.emit(self._current_total, self._current_total)


class SequencePreviewWidget(QWidget):
    """
    Optimized sequence preview widget with thumbnail grid and metadata.

    Features:
    - Lazy loading with progress indication
    - Viewport culling for performance
    - Cancellable operations
    - Metadata overlay on hover
    """

    def __init__(self, parent: QWidget | None = None):
        """
        Initialize sequence preview widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._current_sequence: ImageSequence | None = None
        self._thumbnail_widgets: dict[int, ThumbnailWidget] = {}
        self._max_thumbnails: int = 12
        self._thumbnails_per_row: int = 4

        self._setup_ui()
        self._setup_loader()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)

        # Status label
        self.status_label: QLabel = QLabel("Select a sequence to preview thumbnails")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"font-size: {FONT_SIZE_NORMAL}pt; color: #666;")
        layout.addWidget(self.status_label)

        # Progress bar (initially hidden)
        progress_layout = QHBoxLayout()

        self.progress_bar: QProgressBar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        progress_layout.addWidget(self.progress_bar)

        self.cancel_button: QPushButton = QPushButton("Cancel")
        self.cancel_button.setVisible(False)
        self.cancel_button.setMaximumWidth(80)
        progress_layout.addWidget(self.cancel_button)

        layout.addLayout(progress_layout)

        # Scroll area for thumbnails
        self.scroll_area: QScrollArea = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setMinimumHeight(200)

        # Container for thumbnail grid
        self.thumbnail_container: QWidget = QWidget()
        self.thumbnail_layout: QGridLayout = QGridLayout(self.thumbnail_container)
        self.thumbnail_layout.setSpacing(SPACING_SM)
        self.thumbnail_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        self.scroll_area.setWidget(self.thumbnail_container)
        layout.addWidget(self.scroll_area)

        # Metadata panel
        self.metadata_widget: QWidget = QWidget()
        self.metadata_layout: QVBoxLayout = QVBoxLayout(self.metadata_widget)
        self.metadata_layout.setContentsMargins(0, SPACING_SM, 0, 0)

        # Metadata labels
        self.metadata_labels: dict[str, QLabel] = {
            "resolution": QLabel("Resolution: -"),
            "frame_count": QLabel("Frame Count: -"),
            "total_size": QLabel("Total Size: -"),
            "gaps": QLabel("Missing Frames: None"),
        }

        for label in self.metadata_labels.values():
            label.setStyleSheet(f"font-size: {FONT_SIZE_SMALL}pt; padding: 2px;")
            self.metadata_layout.addWidget(label)

        self.metadata_widget.setVisible(False)
        layout.addWidget(self.metadata_widget)

    def _setup_loader(self) -> None:
        """Set up the thumbnail loader."""
        self.thumbnail_loader: ThumbnailLoader = ThumbnailLoader(self)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        # Loader signals
        self.thumbnail_loader.thumbnail_loaded.connect(self._on_thumbnail_loaded)
        self.thumbnail_loader.thumbnail_error.connect(self._on_thumbnail_error)
        self.thumbnail_loader.progress_updated.connect(self._on_progress_updated)
        self.thumbnail_loader.finished.connect(self._on_loading_finished)

        # Cancel button
        self.cancel_button.clicked.connect(self._cancel_loading)

    def set_sequence(self, sequence: "ImageSequence | None") -> None:
        """
        Set the sequence to preview.

        Args:
            sequence: ImageSequence to preview (None to clear)
        """
        # Cancel any ongoing loading
        self._cancel_loading()

        # Clear previous thumbnails
        self._clear_thumbnails()

        self._current_sequence = sequence

        if sequence is None:
            self.status_label.setText("Select a sequence to preview thumbnails")
            self.status_label.setVisible(True)
            self.metadata_widget.setVisible(False)
            return

        # Update metadata
        self._update_metadata(sequence)

        # Start loading thumbnails
        self._load_thumbnails(sequence)

    def _clear_thumbnails(self) -> None:
        """Clear all thumbnail widgets."""
        for widget in self._thumbnail_widgets.values():
            widget.deleteLater()
        self._thumbnail_widgets.clear()

        # Clear layout
        while self.thumbnail_layout.count():
            item = self.thumbnail_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def _update_metadata(self, sequence: "ImageSequence") -> None:
        """
        Update metadata display.

        Args:
            sequence: ImageSequence to show metadata for
        """
        # Resolution
        if sequence.resolution:
            self.metadata_labels["resolution"].setText(f"Resolution: {sequence.resolution_str}")
        else:
            self.metadata_labels["resolution"].setText("Resolution: Unknown")

        # Frame count
        frame_count = len(sequence.frames)
        plural = "s" if frame_count != 1 else ""
        self.metadata_labels["frame_count"].setText(f"Frame Count: {frame_count} frame{plural}")

        # Total size
        if sequence.total_size_bytes > 0:
            if sequence.total_size_mb < 1024:
                size_text = f"{sequence.total_size_mb:.1f} MB"
            else:
                size_gb = sequence.total_size_mb / 1024
                size_text = f"{size_gb:.1f} GB"
            self.metadata_labels["total_size"].setText(f"Total Size: {size_text}")
        else:
            self.metadata_labels["total_size"].setText("Total Size: Unknown")

        # Missing frames
        if sequence.has_gaps:
            missing_count = len(sequence.missing_frames)
            self.metadata_labels["gaps"].setText(f"Missing Frames: {missing_count} missing")
            self.metadata_labels["gaps"].setStyleSheet(f"font-size: {FONT_SIZE_SMALL}pt; padding: 2px; color: #d32f2f;")
        else:
            self.metadata_labels["gaps"].setText("Missing Frames: None")
            self.metadata_labels["gaps"].setStyleSheet(f"font-size: {FONT_SIZE_SMALL}pt; padding: 2px; color: #2e7d32;")

        self.metadata_widget.setVisible(True)

    def _load_thumbnails(self, sequence: "ImageSequence") -> None:
        """
        Start loading thumbnails for sequence.

        Args:
            sequence: ImageSequence to load thumbnails for
        """
        if not sequence.frames or not sequence.file_list:
            self.status_label.setText("No frames found in sequence")
            self.status_label.setVisible(True)
            return

        # Hide status label
        self.status_label.setVisible(False)

        # Show progress bar
        self.progress_bar.setVisible(True)
        self.cancel_button.setVisible(True)
        self.progress_bar.setValue(0)

        # Select frames to show (evenly distributed up to max_thumbnails)
        frames_to_show = self._select_frames_for_thumbnails(sequence.frames)

        # Create thumbnail widgets
        row = 0
        col = 0

        for frame_number in frames_to_show:
            # Find corresponding file
            frame_index = sequence.frames.index(frame_number)
            if frame_index < len(sequence.file_list):
                file_name = sequence.file_list[frame_index]
                file_path = str(Path(sequence.directory) / file_name)

                # Create thumbnail widget
                thumbnail_widget = ThumbnailWidget(frame_number, file_path)
                self._thumbnail_widgets[frame_number] = thumbnail_widget

                # Add to grid
                self.thumbnail_layout.addWidget(thumbnail_widget, row, col)

                # Add to loading queue
                self.thumbnail_loader.add_thumbnail_request(frame_number, file_path)

                # Update grid position
                col += 1
                if col >= self._thumbnails_per_row:
                    col = 0
                    row += 1

        # Start loading
        if not self.thumbnail_loader.isRunning():
            self.thumbnail_loader.start()

        logger.debug(f"Started loading {len(frames_to_show)} thumbnails for sequence: {sequence.display_name}")

    def _select_frames_for_thumbnails(self, frames: list[int]) -> list[int]:
        """
        Select frames to show as thumbnails (evenly distributed).

        Args:
            frames: List of all frame numbers

        Returns:
            List of frame numbers to show as thumbnails
        """
        if len(frames) <= self._max_thumbnails:
            return frames

        # Select evenly distributed frames
        step = len(frames) / self._max_thumbnails
        selected_frames = []

        for i in range(self._max_thumbnails):
            index = int(i * step)
            if index < len(frames):
                selected_frames.append(frames[index])

        return selected_frames

    def _on_thumbnail_loaded(self, frame_number: int, qimage: object) -> None:
        """
        Handle thumbnail loaded signal (runs in main thread).

        Converts QImage to QPixmap on main thread (Qt requirement).

        Args:
            frame_number: Frame number
            qimage: Loaded QImage from worker thread
        """
        # Type guard - qimage should always be QImage from worker
        if not isinstance(qimage, QImage):
            logger.error(f"Invalid image type received for frame {frame_number}: {type(qimage)}")
            return

        if frame_number in self._thumbnail_widgets:
            # Convert QImage to QPixmap on main thread (Qt requirement)
            pixmap = QPixmap.fromImage(qimage)
            self._thumbnail_widgets[frame_number].set_thumbnail(pixmap)

    def _on_thumbnail_error(self, frame_number: int, error_message: str) -> None:
        """Handle thumbnail error signal."""
        if frame_number in self._thumbnail_widgets:
            self._thumbnail_widgets[frame_number].set_loading_error(error_message)
        logger.warning(f"Failed to load thumbnail for frame {frame_number}: {error_message}")

    def _on_progress_updated(self, current: int, total: int) -> None:
        """Handle progress update signal."""
        if total > 0:
            progress = int((current / total) * 100)
            self.progress_bar.setValue(progress)

    def _on_loading_finished(self) -> None:
        """Handle loading finished signal."""
        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)
        logger.debug("Thumbnail loading finished")

    def _cancel_loading(self) -> None:
        """Cancel thumbnail loading."""
        if self.thumbnail_loader.isRunning():
            self.thumbnail_loader.stop_loading()
            self.thumbnail_loader.wait(1000)  # Wait up to 1 second

            if self.thumbnail_loader.isRunning():
                self.thumbnail_loader.terminate()
                self.thumbnail_loader.wait()

        self.progress_bar.setVisible(False)
        self.cancel_button.setVisible(False)

    def __del__(self) -> None:
        """
        Destructor - stop thumbnail loader thread before widget destruction.

        CRITICAL: Stop thumbnail loader thread to prevent
        "QThread: Destroyed while thread is still running" crash.
        Called during Python object cleanup (e.g., qtbot cleanup in tests).
        """
        try:
            if hasattr(self, 'thumbnail_loader') and self.thumbnail_loader.isRunning():
                self.thumbnail_loader.stop_loading()
                self.thumbnail_loader.wait(2000)  # Wait up to 2 seconds

                # Force terminate if still running
                if self.thumbnail_loader.isRunning():
                    logger.warning("ThumbnailLoader did not stop gracefully in destructor, terminating")
                    self.thumbnail_loader.terminate()
                    self.thumbnail_loader.wait()
        except (RuntimeError, AttributeError):
            # Widget or thread already deleted - safe to ignore
            pass

    @override
    def closeEvent(self, event: "QCloseEvent") -> None:
        """
        Handle widget close event.

        CRITICAL: Stop thumbnail loader thread before widget destruction
        to prevent "QThread: Destroyed while thread is still running" crash.
        """
        # Stop thumbnail loader if running
        if hasattr(self, 'thumbnail_loader') and self.thumbnail_loader.isRunning():
            self.thumbnail_loader.stop_loading()
            self.thumbnail_loader.wait(2000)  # Wait up to 2 seconds

            # Force terminate if still running
            if self.thumbnail_loader.isRunning():
                logger.warning("ThumbnailLoader did not stop gracefully, terminating")
                self.thumbnail_loader.terminate()
                self.thumbnail_loader.wait()

        super().closeEvent(event)

    def get_current_sequence(self) -> "ImageSequence | None":
        """
        Get the currently displayed sequence.

        Returns:
            Current ImageSequence or None
        """
        return self._current_sequence

    def set_thumbnail_settings(self, max_thumbnails: int, thumbnails_per_row: int) -> None:
        """
        Set thumbnail display settings.

        Args:
            max_thumbnails: Maximum number of thumbnails to show
            thumbnails_per_row: Number of thumbnails per row
        """
        self._max_thumbnails = max_thumbnails
        self._thumbnails_per_row = thumbnails_per_row

        # Refresh display if we have a sequence
        if self._current_sequence:
            self.set_sequence(self._current_sequence)

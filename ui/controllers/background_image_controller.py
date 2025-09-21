#!/usr/bin/env python
"""
Background Image Controller for CurveEditor.

This controller manages background image sequences, including loading,
frame-based image switching, and synchronization with the curve widget.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

if TYPE_CHECKING:
    from ui.main_window import MainWindow

from core.logger_utils import get_logger

logger = get_logger("background_image_controller")


class BackgroundImageController:
    """
    Controller for managing background image sequences.

    Extracted from MainWindow to centralize all background image logic,
    including loading image sequences, updating images on frame changes,
    and managing the display in the curve widget.
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Initialize the background image controller.

        Args:
            main_window: Reference to the main window for UI access
        """
        self.main_window = main_window

        # Image sequence data
        self.image_directory: str | None = None
        self.image_filenames: list[str] = []
        self.current_image_idx: int = 0

        logger.info("BackgroundImageController initialized")

    @Slot(str, list)
    def on_image_sequence_loaded(self, image_dir: str, image_files: list[str]) -> None:
        """
        Handle image sequence loaded in background thread.

        This method processes loaded image sequences, updates the UI
        to match the frame range, and loads the first image as background.

        Args:
            image_dir: Directory containing the images
            image_files: List of image filenames
        """
        current_thread = QThread.currentThread()
        app_instance = QApplication.instance()
        main_thread = app_instance.thread() if app_instance is not None else None
        logger.info(
            f"[THREAD-DEBUG] on_image_sequence_loaded executing in thread: {current_thread} (main={current_thread == main_thread})"
        )

        if image_files and self.main_window.curve_widget:
            # Store image sequence info
            self.image_directory = image_dir
            self.image_filenames = image_files
            self.current_image_idx = 0

            # Update frame range to match image sequence
            num_images = len(image_files)
            self._update_frame_range_for_images(num_images)

            # Timeline now updates automatically from store signals
            # No manual update needed
            # self.main_window.timeline_controller.update_for_tracking_data(num_images)

            # Update state manager
            if self.main_window.state_manager:
                self.main_window.state_manager.set_image_files(image_files)

            # Load the first image as background
            self._load_initial_background(image_dir, image_files)

            logger.info(f"Loaded {len(image_files)} images from background thread")

            # Ensure background checkbox is checked when images are loaded
            if self.main_window.show_background_cb and image_files:
                self.main_window.show_background_cb.setChecked(True)
                logger.info("Enabled background display for loaded images")

    def update_background_for_frame(self, frame: int) -> None:
        """
        Update the background image based on the current frame.

        Args:
            frame: Frame number to display (1-based indexing)
        """
        if not self.image_filenames or not self.main_window.curve_widget:
            return

        # Convert to 0-based index
        image_idx = frame - 1

        # Clamp to valid range
        image_idx = max(0, min(image_idx, len(self.image_filenames) - 1))

        # Load the corresponding image
        if 0 <= image_idx < len(self.image_filenames):
            if self.image_directory:
                image_path = Path(self.image_directory) / self.image_filenames[image_idx]
                logger.debug(f"[THREAD-DEBUG] Creating QPixmap for frame {frame}")
                pixmap = QPixmap(str(image_path))

                if not pixmap.isNull():
                    self.main_window.curve_widget.background_image = pixmap
                    self.main_window.curve_widget.update()
                    logger.debug(f"Updated background to frame {frame}: {self.image_filenames[image_idx]}")
            else:
                logger.warning("Image directory not set")

    def _update_frame_range_for_images(self, num_images: int) -> None:
        """
        Update the frame range UI elements to match the image sequence.

        Args:
            num_images: Total number of images in the sequence
        """
        try:
            if self.main_window.frame_spinbox:
                self.main_window.frame_spinbox.setMaximum(num_images)
            if self.main_window.frame_slider:
                self.main_window.frame_slider.setMaximum(num_images)
            if self.main_window.total_frames_label:
                self.main_window.total_frames_label.setText(str(num_images))
            logger.info(f"Set frame range to match {num_images} images (1-{num_images})")
        except RuntimeError:
            # Widgets may have been deleted during application shutdown
            pass

    def _load_initial_background(self, image_dir: str, image_files: list[str]) -> None:
        """
        Load the first image as the initial background.

        Args:
            image_dir: Directory containing the images
            image_files: List of image filenames
        """
        if image_files and self.main_window.curve_widget:
            first_image_path = Path(image_dir) / image_files[0]
            app_instance = QApplication.instance()
            main_thread = app_instance.thread() if app_instance is not None else None
            logger.info(
                f"[THREAD-DEBUG] Creating QPixmap in thread: {QThread.currentThread()} (main={QThread.currentThread() == main_thread})"
            )
            pixmap = QPixmap(str(first_image_path))
            logger.info("[THREAD-DEBUG] QPixmap created successfully")

            if not pixmap.isNull():
                self.main_window.curve_widget.background_image = pixmap
                self.main_window.curve_widget.image_width = pixmap.width()
                self.main_window.curve_widget.image_height = pixmap.height()
                self.main_window.curve_widget.show_background = True

                # Fit the image to view
                self.main_window.curve_widget.fit_to_background_image()

                logger.info(f"Loaded background image: {image_files[0]} ({pixmap.width()}x{pixmap.height()})")

    def clear_background_images(self) -> None:
        """Clear all background image data."""
        self.image_directory = None
        self.image_filenames = []
        self.current_image_idx = 0

        if self.main_window.curve_widget:
            self.main_window.curve_widget.background_image = None
            self.main_window.curve_widget.show_background = False
            self.main_window.curve_widget.update()

        logger.info("Background images cleared")

    def get_image_count(self) -> int:
        """
        Get the number of loaded images.

        Returns:
            Number of images in the current sequence
        """
        return len(self.image_filenames)

    def get_current_image_info(self) -> tuple[str, int] | None:
        """
        Get information about the current image.

        Returns:
            Tuple of (filename, index) or None if no images loaded
        """
        if self.image_filenames and 0 <= self.current_image_idx < len(self.image_filenames):
            return (self.image_filenames[self.current_image_idx], self.current_image_idx)
        return None

    def has_images(self) -> bool:
        """
        Check if any images are loaded.

        Returns:
            True if images are loaded, False otherwise
        """
        return bool(self.image_filenames)

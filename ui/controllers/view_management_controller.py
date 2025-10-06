#!/usr/bin/env python
"""
View Management Controller for CurveEditor.

This unified controller manages all view-related functionality including:
- View options (checkboxes, sliders, tooltips)
- Background image sequences (loading, display, frame sync)
- Visual display settings (grid, point size, line width)
"""

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QThread, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QWidget

if TYPE_CHECKING:
    from ui.main_window import MainWindow

from core.logger_utils import get_logger

logger = get_logger("view_management_controller")


class ViewManagementController:
    """
    Unified controller for all view management and visual settings.

    Combines functionality from ViewOptionsController and BackgroundImageController
    into a single coherent controller managing all visual aspects of the application.
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Initialize the view management controller.

        Args:
            main_window: Reference to the main window for UI access
        """
        self.main_window = main_window

        # View options state
        self._stored_tooltips: dict[QWidget, str] = {}

        # Image sequence data
        self.image_directory: str | None = None
        self.image_filenames: list[str] = []
        self.current_image_idx: int = 0

        logger.info("ViewManagementController initialized")

    # ========== View Options Methods ==========

    @Slot()
    def update_curve_view_options(self) -> None:
        """Update curve view display options from checkboxes."""
        if not self.main_window.curve_widget:
            return

        # Update view options from checkboxes
        if self.main_window.show_background_cb:
            self.main_window.curve_widget.show_background = self.main_window.show_background_cb.isChecked()
        if self.main_window.show_grid_cb:
            self.main_window.curve_widget.show_grid = self.main_window.show_grid_cb.isChecked()
        # Note: show_info is not implemented on CurveViewWidget yet
        # TODO: Add show_info attribute to CurveViewWidget or map to existing attribute

        # Trigger repaint
        self.main_window.curve_widget.update()
        logger.debug("Updated curve view options")

    @Slot(int)
    def update_curve_point_size(self, value: int) -> None:
        """
        Update curve point size from slider.

        Args:
            value: New point size value
        """
        if not self.main_window.curve_widget:
            return

        self.main_window.curve_widget.point_radius = value
        self.main_window.curve_widget.selected_point_radius = value + 2  # Selected points slightly larger

        # Trigger repaint
        self.main_window.curve_widget.update()
        logger.debug(f"Updated point size to {value}")

    @Slot(int)
    def update_curve_line_width(self, value: int) -> None:
        """
        Update curve line width from slider.

        Args:
            value: New line width value
        """
        if not self.main_window.curve_widget:
            return

        self.main_window.curve_widget.line_width = value
        # Trigger repaint
        self.main_window.curve_widget.update()
        logger.debug(f"Updated line width to {value}")

    @Slot()
    def toggle_tooltips(self) -> None:
        """Toggle tooltips on/off for all widgets."""
        if not self.main_window.show_tooltips_cb:
            return

        enable_tooltips = self.main_window.show_tooltips_cb.isChecked()

        if enable_tooltips:
            # Restore stored tooltips
            for widget, tooltip in self._stored_tooltips.items():
                try:
                    widget.setToolTip(tooltip)
                except RuntimeError:
                    # Widget may have been deleted
                    pass
            self._stored_tooltips.clear()
            logger.info("Tooltips enabled")
        else:
            # Store and clear all tooltips
            for widget in self.main_window.findChildren(QWidget):
                tooltip = widget.toolTip()
                if tooltip:
                    self._stored_tooltips[widget] = tooltip
                    widget.setToolTip("")
            logger.info("Tooltips disabled")

    def get_view_options(self) -> dict[str, object]:
        """
        Get current view options as a dictionary.

        Returns:
            Dictionary of view option settings
        """
        options = {}

        if self.main_window.show_background_cb:
            options["show_background"] = self.main_window.show_background_cb.isChecked()
        if self.main_window.show_grid_cb:
            options["show_grid"] = self.main_window.show_grid_cb.isChecked()
        if self.main_window.show_info_cb:
            options["show_info"] = self.main_window.show_info_cb.isChecked()
        if self.main_window.show_tooltips_cb:
            options["show_tooltips"] = self.main_window.show_tooltips_cb.isChecked()
        if self.main_window.point_size_slider:
            options["point_size"] = self.main_window.point_size_slider.value()
        if self.main_window.line_width_slider:
            options["line_width"] = self.main_window.line_width_slider.value()

        return options

    def set_view_options(self, options: dict[str, object]) -> None:
        """
        Set view options from a dictionary.

        Args:
            options: Dictionary of view option settings to apply
        """
        if "show_background" in options and self.main_window.show_background_cb:
            self.main_window.show_background_cb.setChecked(bool(options["show_background"]))
        if "show_grid" in options and self.main_window.show_grid_cb:
            self.main_window.show_grid_cb.setChecked(bool(options["show_grid"]))
        if "show_info" in options and self.main_window.show_info_cb:
            self.main_window.show_info_cb.setChecked(bool(options["show_info"]))
        if "show_tooltips" in options and self.main_window.show_tooltips_cb:
            self.main_window.show_tooltips_cb.setChecked(bool(options["show_tooltips"]))
        if "point_size" in options and self.main_window.point_size_slider:
            # Convert to int safely - value should be numeric
            point_size_val = options["point_size"]
            if isinstance(point_size_val, int | float | str):
                self.main_window.point_size_slider.setValue(int(point_size_val))
        if "line_width" in options and self.main_window.line_width_slider:
            # Convert to int safely - value should be numeric
            line_width_val = options["line_width"]
            if isinstance(line_width_val, int | float | str):
                self.main_window.line_width_slider.setValue(int(line_width_val))

        # Apply the options
        self.update_curve_view_options()
        self.toggle_tooltips()

    # ========== Background Image Methods ==========

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

            # Update state manager
            if self.main_window.state_manager:
                self.main_window.state_manager.set_image_files(image_files)

            # Update timeline to reflect image sequence range
            if self.main_window.timeline_tabs:
                # Trigger timeline refresh with current ApplicationState data
                from stores.application_state import get_application_state

                app_state = get_application_state()
                self.main_window.timeline_tabs._on_curves_changed(app_state.get_all_curves())
                logger.info(f"Updated timeline to show {num_images} frames")

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

                # Check if this is an EXR file (requires special loader)
                if image_path.suffix.lower() == ".exr":
                    from io_utils.exr_loader import load_exr_as_qpixmap

                    pixmap = load_exr_as_qpixmap(str(image_path))
                else:
                    pixmap = QPixmap(str(image_path))

                if pixmap is not None and not pixmap.isNull():
                    self.main_window.curve_widget.background_image = pixmap
                    self.main_window.curve_widget.update()
                    logger.debug(f"Updated background to frame {frame}: {self.image_filenames[image_idx]}")
            else:
                logger.warning("Image directory not set")

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

    # ========== Private Helper Methods ==========

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

            # Check if this is an EXR file (requires special loader)
            if first_image_path.suffix.lower() == ".exr":
                from io_utils.exr_loader import load_exr_as_qpixmap

                pixmap = load_exr_as_qpixmap(str(first_image_path))
            else:
                pixmap = QPixmap(str(first_image_path))

            logger.info("[THREAD-DEBUG] QPixmap created successfully")

            if pixmap is not None and not pixmap.isNull():
                self.main_window.curve_widget.background_image = pixmap
                self.main_window.curve_widget.image_width = pixmap.width()
                self.main_window.curve_widget.image_height = pixmap.height()
                self.main_window.curve_widget.show_background = True

                # Fit the image to view
                self.main_window.curve_widget.fit_to_background_image()

                logger.info(f"Loaded background image: {image_files[0]} ({pixmap.width()}x{pixmap.height()})")

    # ========== Protocol Compliance Methods ==========

    @Slot(bool)
    def on_show_background_changed(self, checked: bool) -> None:
        """Handle show background checkbox change (ViewOptionsProtocol)."""
        if self.main_window.show_background_cb:
            self.main_window.show_background_cb.setChecked(checked)
        self.update_curve_view_options()

    @Slot(bool)
    def on_show_grid_changed(self, checked: bool) -> None:
        """Handle show grid checkbox change (ViewOptionsProtocol)."""
        if self.main_window.show_grid_cb:
            self.main_window.show_grid_cb.setChecked(checked)
        self.update_curve_view_options()

    @Slot(int)
    def on_point_size_changed(self, value: int) -> None:
        """Handle point size slider change (ViewOptionsProtocol)."""
        self.update_curve_point_size(value)

    @Slot(int)
    def on_line_width_changed(self, value: int) -> None:
        """Handle line width slider change (ViewOptionsProtocol)."""
        self.update_curve_line_width(value)

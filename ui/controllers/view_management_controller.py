#!/usr/bin/env python
"""
View Management Controller for CurveEditor.

This unified controller manages all view-related functionality including:
- View options (checkboxes, sliders, tooltips)
- Background image sequences (loading, display, frame sync)
- Visual display settings (grid, point size, line width)
"""

from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict
from weakref import WeakKeyDictionary

from PySide6.QtCore import QThread, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QWidget

if TYPE_CHECKING:
    from ui.main_window import MainWindow

from core.curve_data import CurveDataWithMetadata
from core.logger_utils import get_logger
from stores.application_state import get_application_state

logger = get_logger("view_management_controller")


class ViewOptions(TypedDict, total=False):
    """Type definition for view options dictionary.

    All fields are optional since not all UI widgets may be present.
    """

    show_background: bool
    show_grid: bool
    show_info: bool
    show_tooltips: bool
    point_size: int
    line_width: int


class ViewManagementController:
    """
    Unified controller for all view management and visual settings.

    Combines functionality from ViewOptionsController and BackgroundImageController
    into a single coherent controller managing all visual aspects of the application.

    NOTE: This controller uses concrete MainWindow type (not protocol) because it
    needs direct access to UI widgets (checkboxes, sliders) that aren't in MainWindowProtocol.
    """

    def __init__(self, main_window: "MainWindow"):
        """
        Initialize the view management controller.

        Args:
            main_window: Reference to the main window for UI access
        """
        self.main_window: MainWindow = main_window

        # View options state (WeakKeyDictionary prevents memory leaks)
        self._stored_tooltips: WeakKeyDictionary[QWidget, str] = WeakKeyDictionary()

        # Image sequence data
        self.image_directory: str | None = None
        self.image_filenames: list[str] = []
        self.current_image_idx: int = 0

        # Phase 2C: Image caching now handled by SafeImageCacheManager in DataService
        # Legacy _image_cache removed (superseded by Phase 2C integration)

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
            self.main_window.curve_widget.visual.show_grid = self.main_window.show_grid_cb.isChecked()
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
            value: Slider value (1-20), maps to point radius 0.25-5.0
        """
        if not self.main_window.curve_widget:
            return

        # Convert slider value (1-20) to point radius (0.25-5.0)
        # Each slider tick = 0.25 pixel increment
        point_radius = value * 0.25

        self.main_window.curve_widget.visual.point_radius = point_radius
        self.main_window.curve_widget.visual.selected_point_radius = point_radius + 0.5  # Selected points slightly larger

        # Trigger repaint
        self.main_window.curve_widget.update()
        logger.debug(f"Updated point size to {point_radius:.2f} (slider value: {value})")

    @Slot(int)
    def update_curve_line_width(self, value: int) -> None:
        """
        Update curve line width from slider.

        Args:
            value: New line width value
        """
        if not self.main_window.curve_widget:
            return

        self.main_window.curve_widget.visual.line_width = value
        # Trigger repaint
        self.main_window.curve_widget.update()
        logger.debug(f"Updated line width to {value}")

    @Slot()
    def toggle_tooltips(self) -> None:
        """Toggle tooltips on/off for all widgets.

        Uses WeakKeyDictionary to store tooltips, which automatically
        cleans up entries for deleted widgets, preventing memory leaks.
        """
        if not self.main_window.show_tooltips_cb:
            return

        enable_tooltips = self.main_window.show_tooltips_cb.isChecked()

        if enable_tooltips:
            # Restore stored tooltips (dead widgets auto-removed by WeakKeyDictionary)
            for widget, tooltip in self._stored_tooltips.items():
                widget.setToolTip(tooltip)
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

    @Slot()
    def toggle_current_point_only(self) -> None:
        """Toggle current point only mode (3DEqualizer-style).
        
        When enabled, only shows the point at the current frame,
        hiding the rest of the curve trajectory.
        """
        if not self.main_window.show_current_point_cb:
            return

        show_current_only = self.main_window.show_current_point_cb.isChecked()
        self.main_window.state_manager.show_current_point_only = show_current_only

        # Trigger curve view repaint
        if self.main_window.curve_widget:
            self.main_window.curve_widget.update()

        logger.info(f"Current point only mode: {'enabled' if show_current_only else 'disabled'}")

    def get_view_options(self) -> ViewOptions:
        """
        Get current view options as a dictionary.

        Returns:
            Dictionary of view option settings
        """
        options: ViewOptions = {}

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

    def set_view_options(self, options: ViewOptions) -> None:
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
            self.main_window.point_size_slider.setValue(options["point_size"])
        if "line_width" in options and self.main_window.line_width_slider:
            self.main_window.line_width_slider.setValue(options["line_width"])

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

            # Update StateManager for session persistence
            self.main_window.state_manager.image_directory = image_dir
            logger.debug(f"[IMAGE-LOAD] Set image_directory to: {image_dir}")

            # Update frame range to match image sequence
            num_images = len(image_files)
            self._update_frame_range_for_images(num_images)

            # Update ApplicationState with image sequence
            get_application_state().set_image_files(image_files, directory=image_dir)

            # Initialize image cache with full paths (Phase 2C)
            from services import get_data_service
            full_paths = [str(Path(image_dir) / fname) for fname in image_files]
            get_data_service().set_image_sequence(full_paths)
            logger.debug(f"Initialized image cache with {len(full_paths)} files")

            # Load the first image as background
            self._load_initial_background(image_dir, image_files)

            logger.info(f"Loaded {len(image_files)} images from background thread")

            # Ensure background checkbox is checked when images are loaded
            if self.main_window.show_background_cb and image_files:
                self.main_window.show_background_cb.setChecked(True)
                logger.info("Enabled background display for loaded images")

    # Phase 2C: Legacy cache methods removed (lines 258-319)
    # Image caching now handled by SafeImageCacheManager in DataService
    # Methods removed: _load_image_from_disk(), _get_cached_image(), clear_image_cache()

    def update_background_for_frame(self, frame: int) -> None:
        """
        Update the background image based on the current frame.

        Phase 2C: Uses SafeImageCacheManager for efficient caching with background preloading.
        First playthrough loads from disk, subsequent playback uses cached images (instant).

        Args:
            frame: Frame number to display (1-based indexing)
        """
        # Phase 2C: Delegate to cache-based implementation
        self._update_background_image(frame)

    def _update_background_image(self, frame: int) -> None:
        """
        Update background image with caching (Phase 2C integration).

        Uses DataService's SafeImageCacheManager for efficient on-demand loading
        with background preloading to eliminate first-pass lag.

        Args:
            frame: Frame number to display (1-based indexing)
        """
        from services import get_data_service

        if not self.main_window.curve_widget:
            return

        # Convert to 0-based index for cache lookup
        image_idx = frame - 1

        # Get cached image (returns QPixmap ready for display)
        pixmap = get_data_service().get_background_image(image_idx)

        if pixmap and not pixmap.isNull():
            self.main_window.curve_widget.background_image = pixmap
            # NOTE: Don't call update() here - FrameChangeCoordinator handles the repaint
            # in phase 3 after centering, preventing visual jumps during playback

        # Trigger preload of adjacent frames (background operation, non-blocking)
        get_data_service().preload_around_frame(image_idx)

    def clear_background_images(self) -> None:
        """Clear all background image data and cache."""
        self.image_directory = None
        self.image_filenames = []
        self.current_image_idx = 0

        # Phase 2C: Cache now managed by DataService (cleared on next sequence load)

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
        if self.main_window.timeline_controller:
            self.main_window.timeline_controller.update_frame_range(1, num_images)
            logger.info(f"Set frame range to match {num_images} images (1-{num_images})")

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

                # Update all curve metadata with real image dimensions
                real_width = pixmap.width()
                real_height = pixmap.height()
                state = get_application_state()

                for curve_name in state.get_all_curve_names():
                    curve_data = state.get_curve_data(curve_name)
                    if isinstance(curve_data, CurveDataWithMetadata):
                        # Update metadata with real dimensions
                        updated_metadata = replace(
                            curve_data.metadata,
                            width=real_width,
                            height=real_height
                        )
                        updated_curve = CurveDataWithMetadata(
                            data=curve_data.data,
                            metadata=updated_metadata,
                            is_normalized=curve_data.is_normalized
                        )
                        state.set_curve_data(curve_name, updated_curve)

                logger.info(f"Updated curve metadata for {len(state.get_all_curve_names())} curves with real dimensions: {real_width}x{real_height}")

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

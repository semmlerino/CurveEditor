#!/usr/bin/env python

"""
ImageState: Unified image state management for CurveEditor.

This module provides a single source of truth for all image-related state,
eliminating inconsistencies between sequence metadata and display state.
It replaces the dual system where StatusManager and ImageService check
different sources for image state.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any, TypeGuard

if TYPE_CHECKING:
    from collections.abc import Callable

    from services.service_protocols import CurveViewProtocol, MainWindowProtocol


try:
    from PySide6.QtGui import QPixmap
except ImportError:
    # Stub for when PySide6 is not available
    class QPixmap:
        def __init__(self, *args: object) -> None:
            pass

        def isNull(self) -> bool:
            return True

        def width(self) -> int:
            return 0

        def height(self) -> int:
            return 0



# Configure logger for this module
logger = logging.getLogger("image_state")


class ImageLoadingState(Enum):
    """Enumeration of possible image loading states."""

    NO_SEQUENCE = auto()  # No image sequence loaded
    SEQUENCE_LOADED = auto()  # Sequence metadata loaded but no current image
    IMAGE_LOADING = auto()  # Currently loading an image
    IMAGE_LOADED = auto()  # Image successfully loaded and displayed
    IMAGE_FAILED = auto()  # Image loading failed


@dataclass
class ImageSequenceInfo:
    """Information about an image sequence."""

    path: str = ""
    filenames: list[str] = field(default_factory=list)
    current_index: int = -1
    total_count: int = 0

    def __post_init__(self) -> None:
        """Initialize default values correctly."""
        if not isinstance(self.filenames, list):
            self.filenames = []
        self.total_count = len(self.filenames)

    @property
    def is_valid(self) -> bool:
        """Check if sequence info represents a valid sequence."""
        return bool(self.path and self.filenames and Path(self.path).is_dir())

    @property
    def current_filename(self) -> str | None:
        """Get the current image filename if valid."""
        if 0 <= self.current_index < len(self.filenames):
            return self.filenames[self.current_index]
        return None

    @property
    def current_filepath(self) -> str | None:
        """Get the full path to current image file."""
        filename = self.current_filename
        if filename and self.path:
            return str(Path(self.path) / filename)
        return None


@dataclass
class ImageDisplayInfo:
    """Information about currently displayed image."""

    pixmap: QPixmap | None = None
    width: int = 0
    height: int = 0
    filepath: str = ""
    load_error: str = ""

    @property
    def is_loaded(self) -> bool:
        """Check if image is successfully loaded."""
        return bool(self.pixmap and not self.pixmap.isNull())

    @property
    def has_error(self) -> bool:
        """Check if there was a loading error."""
        return bool(self.load_error)


def _is_curve_view_protocol(obj: object) -> TypeGuard[CurveViewProtocol]:
    """
    Type guard to check if an object conforms to CurveViewProtocol.

    Args:
        obj: Object to check

    Returns:
        True if object has the required CurveViewProtocol attributes
    """
    required_attrs = [
        'selected_point_idx', 'curve_data', 'current_image_idx',
        'points', 'selected_points', 'offset_x', 'offset_y'
    ]
    return all(hasattr(obj, attr) for attr in required_attrs)


class ImageState:
    """
    Unified image state management.

    This class serves as the single source of truth for all image-related state,
    providing consistent state detection and update mechanisms across the application.

    Key Features:
    - Single source of truth for image sequence and display state
    - Consistent state detection methods
    - Automatic state synchronization
    - Event-driven update notifications
    """

    # Type annotations for class attributes
    loading_state: ImageLoadingState
    sequence_info: ImageSequenceInfo
    display_info: ImageDisplayInfo
    _state_change_callbacks: list[Callable[[], None]]

    def __init__(self) -> None:
        """Initialize image state with default values."""
        self.loading_state = ImageLoadingState.NO_SEQUENCE
        self.sequence_info = ImageSequenceInfo()
        self.display_info = ImageDisplayInfo()

        # State change callbacks
        self._state_change_callbacks: list[Callable[[], None]] = []

        logger.debug("ImageState initialized")

    # === State Detection Methods (Single Source of Truth) ===

    def has_sequence_loaded(self) -> bool:
        """
        Check if an image sequence is loaded (metadata available).

        Returns:
            bool: True if sequence metadata is loaded and valid
        """
        return self.sequence_info.is_valid and self.loading_state != ImageLoadingState.NO_SEQUENCE

    def has_image_displayed(self) -> bool:
        """
        Check if an image is currently loaded and displayed.

        Returns:
            bool: True if image is successfully loaded and displayed
        """
        return self.loading_state == ImageLoadingState.IMAGE_LOADED and self.display_info.is_loaded

    def has_any_image_data(self) -> bool:
        """
        Check if there is any image-related data (sequence or display).

        Returns:
            bool: True if either sequence is loaded or image is displayed
        """
        return self.has_sequence_loaded() or self.has_image_displayed()

    def is_loading(self) -> bool:
        """
        Check if an image is currently being loaded.

        Returns:
            bool: True if image loading is in progress
        """
        return self.loading_state == ImageLoadingState.IMAGE_LOADING

    def has_loading_error(self) -> bool:
        """
        Check if there was an error loading the current image.

        Returns:
            bool: True if image loading failed
        """
        return self.loading_state == ImageLoadingState.IMAGE_FAILED or self.display_info.has_error

    # === Status Message Generation ===

    def get_status_message(self) -> str:
        """
        Get a consistent status message based on current state.

        Returns:
            str: Status message for display in UI
        """
        if self.has_loading_error():
            error_msg = self.display_info.load_error or "Image loading failed"
            return f"Error: {error_msg}"

        if self.is_loading():
            return "Loading image..."

        if self.has_image_displayed():
            return f"Image loaded: {self.sequence_info.current_filename or 'Unknown'}"

        if self.has_sequence_loaded():
            count = self.sequence_info.total_count
            return f"Sequence loaded ({count} images, none displayed)"

        return "No images loaded"

    def get_timeline_message(self) -> str:
        """
        Get timeline-specific status message.

        Returns:
            str: Timeline status message
        """
        if not self.has_sequence_loaded():
            return "No images loaded"

        if self.sequence_info.current_index >= 0:
            current = self.sequence_info.current_index + 1
            total = self.sequence_info.total_count
            filename = self.sequence_info.current_filename or "Unknown"
            return f"Image: {current}/{total} - {filename}"

        total = self.sequence_info.total_count
        return f"Sequence loaded ({total} images)"

    # === State Update Methods ===

    def set_sequence(self, path: str, filenames: list[str]) -> None:
        """
        Set the image sequence information.

        Args:
            path: Directory path containing the image sequence
            filenames: List of image filenames in the sequence
        """
        old_state = self.loading_state

        if not path or not filenames:
            self.clear_sequence()
            return

        self.sequence_info = ImageSequenceInfo(
            path=path, filenames=filenames.copy(), current_index=-1, total_count=len(filenames)
        )

        if self.sequence_info.is_valid:
            self.loading_state = ImageLoadingState.SEQUENCE_LOADED
            logger.info(f"Image sequence set: {len(filenames)} files in {path}")
        else:
            self.loading_state = ImageLoadingState.NO_SEQUENCE
            logger.warning(f"Invalid sequence set: path={path}, files={len(filenames)}")

        if old_state != self.loading_state:
            self._notify_state_change()

    def set_current_image_index(self, index: int) -> None:
        """
        Set the current image index in the sequence.

        Args:
            index: Index of the image to make current
        """
        if not self.has_sequence_loaded():
            logger.warning("Cannot set image index: no sequence loaded")
            return

        if 0 <= index < self.sequence_info.total_count:
            old_index = self.sequence_info.current_index
            self.sequence_info.current_index = index

            if old_index != index:
                logger.debug(f"Current image index changed from {old_index} to {index}")
                self._notify_state_change()
        else:
            logger.warning(f"Invalid image index: {index} (sequence has {self.sequence_info.total_count} images)")

    def set_image_loading(self) -> None:
        """Mark that an image is currently being loaded."""
        old_state = self.loading_state
        self.loading_state = ImageLoadingState.IMAGE_LOADING
        self.display_info.load_error = ""  # Clear previous errors

        if old_state != self.loading_state:
            logger.debug("Image loading started")
            self._notify_state_change()

    def set_image_loaded(self, pixmap: QPixmap, filepath: str = "") -> None:
        """
        Mark that an image has been successfully loaded.

        Args:
            pixmap: The loaded image pixmap
            filepath: Optional path to the loaded image file
        """
        old_state = self.loading_state

        self.loading_state = ImageLoadingState.IMAGE_LOADED
        self.display_info = ImageDisplayInfo(
            pixmap=pixmap,
            width=pixmap.width() if pixmap else 0,
            height=pixmap.height() if pixmap else 0,
            filepath=filepath,
            load_error="",
        )

        if old_state != self.loading_state:
            logger.debug(f"Image loaded successfully: {filepath}")
            self._notify_state_change()

    def set_image_load_failed(self, error_message: str = "") -> None:
        """
        Mark that image loading has failed.

        Args:
            error_message: Optional error message describing the failure
        """
        old_state = self.loading_state

        self.loading_state = ImageLoadingState.IMAGE_FAILED
        self.display_info.load_error = error_message
        self.display_info.pixmap = None

        if old_state != self.loading_state:
            logger.warning(f"Image loading failed: {error_message}")
            self._notify_state_change()

    def clear_sequence(self) -> None:
        """Clear all image sequence and display data."""
        old_state = self.loading_state

        self.loading_state = ImageLoadingState.NO_SEQUENCE
        self.sequence_info = ImageSequenceInfo()
        self.display_info = ImageDisplayInfo()

        if old_state != self.loading_state:
            logger.debug("Image sequence cleared")
            self._notify_state_change()

    def clear_display(self) -> None:
        """Clear only the displayed image, keeping sequence metadata."""
        if self.has_sequence_loaded():
            old_state = self.loading_state
            self.loading_state = ImageLoadingState.SEQUENCE_LOADED
            self.display_info = ImageDisplayInfo()

            if old_state != self.loading_state:
                logger.debug("Image display cleared, sequence retained")
                self._notify_state_change()
        else:
            self.clear_sequence()

    # === Legacy Compatibility Methods ===

    def sync_from_curve_view(self, curve_view: CurveViewProtocol) -> None:
        """
        Sync state from existing curve_view attributes for backward compatibility.

        Args:
            curve_view: The curve view instance to sync from
        """
        # Sync sequence information
        if hasattr(curve_view, "image_sequence_path") and hasattr(curve_view, "image_filenames"):
            path = getattr(curve_view, "image_sequence_path", "")
            filenames = getattr(curve_view, "image_filenames", [])
            if path and filenames:
                self.set_sequence(path, filenames)

        # Sync current index
        if hasattr(curve_view, "current_image_idx"):
            index = getattr(curve_view, "current_image_idx", -1)
            if index >= 0:
                self.set_current_image_index(index)

        # Sync display state
        if hasattr(curve_view, "background_image"):
            background_image = getattr(curve_view, "background_image")
            if background_image and not background_image.isNull():
                filepath = self.sequence_info.current_filepath or ""
                self.set_image_loaded(background_image, filepath)
            elif self.has_sequence_loaded():
                self.loading_state = ImageLoadingState.SEQUENCE_LOADED
            else:
                self.loading_state = ImageLoadingState.NO_SEQUENCE

    def sync_from_main_window(self, main_window: MainWindowProtocol) -> None:
        """
        Sync state from main window attributes for backward compatibility.

        Args:
            main_window: The main window instance to sync from
        """
        # Sync sequence information from main window
        if hasattr(main_window, "image_sequence_path") and hasattr(main_window, "image_filenames"):
            path = getattr(main_window, "image_sequence_path", "")
            filenames = getattr(main_window, "image_filenames", [])
            if path and filenames:
                self.set_sequence(path, filenames)

        # Sync current frame
        if hasattr(main_window, "current_frame"):
            frame = getattr(main_window, "current_frame", 0)
            if frame >= 0:
                self.set_current_image_index(frame)

        # Sync from curve view if available
        if hasattr(main_window, "curve_view") and main_window.curve_view:
            curve_view = main_window.curve_view
            if _is_curve_view_protocol(curve_view):
                self.sync_from_curve_view(curve_view)
            else:
                logger.warning("curve_view object does not conform to CurveViewProtocol")

    # === State Change Notifications ===

    def add_state_change_callback(self, callback: Callable[[], None]) -> None:
        """
        Add a callback to be notified when state changes.

        Args:
            callback: Function to call when state changes
        """
        if callback not in self._state_change_callbacks:
            self._state_change_callbacks.append(callback)

    def remove_state_change_callback(self, callback: Callable[[], None]) -> None:
        """
        Remove a state change callback.

        Args:
            callback: Function to remove from callbacks
        """
        if callback in self._state_change_callbacks:
            self._state_change_callbacks.remove(callback)

    def _notify_state_change(self) -> None:
        """Notify all registered callbacks of state change."""
        for callback in self._state_change_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")

    # === Debug and Inspection ===

    def get_state_summary(self) -> dict[str, Any]:
        """
        Get a summary of the current state for debugging.

        Returns:
            dict: Summary of current state
        """
        return {
            "loading_state": self.loading_state.name,
            "sequence_loaded": self.has_sequence_loaded(),
            "image_displayed": self.has_image_displayed(),
            "sequence_path": self.sequence_info.path,
            "sequence_count": self.sequence_info.total_count,
            "current_index": self.sequence_info.current_index,
            "current_filename": self.sequence_info.current_filename,
            "display_width": self.display_info.width,
            "display_height": self.display_info.height,
            "has_error": self.has_loading_error(),
            "error_message": self.display_info.load_error,
            "status_message": self.get_status_message(),
            "timeline_message": self.get_timeline_message(),
        }

    def __str__(self) -> str:
        """String representation for debugging."""
        return (
            f"ImageState({self.loading_state.name}, seq={self.has_sequence_loaded()}, img={self.has_image_displayed()})"
        )

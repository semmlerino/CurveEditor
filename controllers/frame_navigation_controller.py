"""
Frame navigation controller for timeline navigation.

Manages frame navigation including next/prev/first/last,
frame synchronization across UI components, and background
image updates for frame sequences.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QSlider, QSpinBox

if TYPE_CHECKING:
    from ui.timeline_tabs import TimelineTabWidget

logger = logging.getLogger(__name__)


class CurveWidgetProtocol(Protocol):
    """Protocol for CurveWidget interface."""

    def on_frame_changed(self, frame: int) -> None: ...
    def _invalidate_caches(self) -> None: ...
    def update(self) -> None: ...
    @property
    def background_image(self) -> QPixmap | None: ...
    @background_image.setter
    def background_image(self, value: QPixmap) -> None: ...


class StateManagerProtocol(Protocol):
    """Protocol for StateManager interface."""

    @property
    def current_frame(self) -> int: ...
    @current_frame.setter
    def current_frame(self, value: int) -> None: ...
    @property
    def image_directory(self) -> str | None: ...


class MainWindowProtocol(Protocol):
    """Protocol for MainWindow interface needed by FrameNavigationController."""

    @property
    def frame_spinbox(self) -> QSpinBox | None: ...
    @property
    def frame_slider(self) -> QSlider | None: ...
    @property
    def timeline_tabs(self) -> "TimelineTabWidget | None": ...
    @property
    def curve_widget(self) -> CurveWidgetProtocol | None: ...
    @property
    def state_manager(self) -> StateManagerProtocol: ...
    @property
    def image_filenames(self) -> list[str]: ...


class FrameNavigationController(QObject):
    """Controller for managing frame navigation."""

    # Signals
    frame_changed: Signal = Signal(int)

    def __init__(self, main_window: MainWindowProtocol, parent: QObject | None = None):
        """Initialize the frame navigation controller.

        Args:
            main_window: Reference to the main window
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self.main_window: MainWindowProtocol = main_window
        self._current_frame: int = 1

    def navigate_to_frame(self, frame: int, update_state_manager: bool = True) -> None:
        """Navigate to a specific frame with full UI update.

        Args:
            frame: Target frame number
            update_state_manager: Whether to update the state manager
        """
        self._current_frame = frame
        self._update_frame_display(frame, update_state_manager)
        self.frame_changed.emit(frame)

    def go_to_first_frame(self) -> None:
        """Navigate to the first frame."""
        self.navigate_to_frame(1)

    def go_to_last_frame(self) -> None:
        """Navigate to the last frame."""
        if self.main_window.frame_spinbox:
            max_frame = self.main_window.frame_spinbox.maximum()
            self.navigate_to_frame(max_frame)

    def go_to_next_frame(self) -> None:
        """Navigate to the next frame."""
        if self.main_window.frame_spinbox:
            current = self.main_window.frame_spinbox.value()
            max_frame = self.main_window.frame_spinbox.maximum()
            if current < max_frame:
                self.navigate_to_frame(current + 1)

    def go_to_previous_frame(self) -> None:
        """Navigate to the previous frame."""
        if self.main_window.frame_spinbox:
            current = self.main_window.frame_spinbox.value()
            if current > 1:
                self.navigate_to_frame(current - 1)

    def get_current_frame(self) -> int:
        """Get the current frame number.

        Returns:
            Current frame number
        """
        if self.main_window.frame_spinbox:
            return self.main_window.frame_spinbox.value()
        return self._current_frame

    def set_frame_range(self, min_frame: int, max_frame: int) -> None:
        """Set the valid frame range.

        Args:
            min_frame: Minimum frame number
            max_frame: Maximum frame number
        """
        if self.main_window.frame_spinbox:
            self.main_window.frame_spinbox.setMinimum(min_frame)
            self.main_window.frame_spinbox.setMaximum(max_frame)

        if self.main_window.frame_slider:
            self.main_window.frame_slider.setMinimum(min_frame)
            self.main_window.frame_slider.setMaximum(max_frame)

    def _update_frame_display(self, frame: int, update_state_manager: bool = True) -> None:
        """Shared method to update frame display across all UI components.

        Args:
            frame: Frame number to display
            update_state_manager: Whether to update the state manager
        """
        # Update UI controls
        if self.main_window.frame_spinbox:
            self.main_window.frame_spinbox.blockSignals(True)
            self.main_window.frame_spinbox.setValue(frame)
            self.main_window.frame_spinbox.blockSignals(False)

        if self.main_window.frame_slider:
            self.main_window.frame_slider.blockSignals(True)
            self.main_window.frame_slider.setValue(frame)
            self.main_window.frame_slider.blockSignals(False)

        # Update timeline tabs if available
        if self.main_window.timeline_tabs:
            self.main_window.timeline_tabs.set_current_frame(frame)

        # Update state manager (only when called from user input, not state sync)
        if update_state_manager:
            self.main_window.state_manager.current_frame = frame
            logger.debug(f"[FRAME] State manager current_frame set to: {frame}")

        # Update background image if image sequence is loaded
        self._update_background_image_for_frame(frame)

        # Update curve widget to highlight current frame's point
        if self.main_window.curve_widget:
            # Notify curve widget of frame change for centering mode
            self.main_window.curve_widget.on_frame_changed(frame)
            # Invalidate caches to ensure proper repainting with new frame highlight
            self.main_window.curve_widget._invalidate_caches()
            self.main_window.curve_widget.update()

    def _update_background_image_for_frame(self, frame: int) -> None:
        """Update the background image based on the current frame.

        Args:
            frame: Frame number to display
        """
        if not self.main_window.image_filenames:
            return

        if not self.main_window.curve_widget:
            return

        # Find the appropriate image for this frame (1-based indexing)
        image_idx = frame - 1  # Convert to 0-based index

        # Clamp to valid range
        if image_idx < 0:
            image_idx = 0
        elif image_idx >= len(self.main_window.image_filenames):
            image_idx = len(self.main_window.image_filenames) - 1

        # Load the corresponding image
        if 0 <= image_idx < len(self.main_window.image_filenames) and self.main_window.state_manager.image_directory:
            image_path = (
                Path(self.main_window.state_manager.image_directory) / self.main_window.image_filenames[image_idx]
            )
            logger.info(f"[THREAD-DEBUG] Creating QPixmap for frame update in thread: {QThread.currentThread()}")
            pixmap = QPixmap(str(image_path))

            if not pixmap.isNull():
                self.main_window.curve_widget.background_image = pixmap
                self.main_window.curve_widget.update()
                logger.debug(f"Updated background to frame {frame}: {self.main_window.image_filenames[image_idx]}")

    def on_frame_spinbox_changed(self, value: int) -> None:
        """Handle frame spinbox value change.

        Args:
            value: New frame value
        """
        logger.debug(f"[FRAME] Frame spinbox changed to: {value}")
        self.navigate_to_frame(value, update_state_manager=True)

    def on_frame_slider_changed(self, value: int) -> None:
        """Handle frame slider value change.

        Args:
            value: New frame value
        """
        logger.debug(f"[FRAME] Frame slider changed to: {value}")

        # Sync spinbox with slider
        if self.main_window.frame_spinbox:
            self.main_window.frame_spinbox.blockSignals(True)
            self.main_window.frame_spinbox.setValue(value)
            self.main_window.frame_spinbox.blockSignals(False)

        # Update timeline tabs if available
        if self.main_window.timeline_tabs:
            self.main_window.timeline_tabs.set_current_frame(value)

        self.main_window.state_manager.current_frame = value

        # Update background image if image sequence is loaded
        self._update_background_image_for_frame(value)

        # Update curve widget to highlight current frame's point
        if self.main_window.curve_widget:
            # Notify curve widget of frame change for centering mode
            self.main_window.curve_widget.on_frame_changed(value)
            # Invalidate caches to ensure proper repainting with new frame highlight
            self.main_window.curve_widget._invalidate_caches()
            self.main_window.curve_widget.update()

        self.frame_changed.emit(value)

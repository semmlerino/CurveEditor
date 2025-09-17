"""
Frame navigation controller for timeline control.

This module handles frame navigation including spinbox/slider synchronization,
navigation buttons, and frame range management.
"""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
    QSlider,
    QSpinBox,
    QStyle,
)

if TYPE_CHECKING:
    from ui.state_manager import StateManager

logger = logging.getLogger(__name__)


class FrameNavigationController(QObject):
    """
    Controller for managing frame navigation functionality.

    This controller handles frame spinbox/slider synchronization,
    navigation buttons, and frame updates extracted from MainWindow.
    """

    # Signals
    frame_changed = Signal(int)  # Emitted when frame changes
    status_message = Signal(str)  # Status bar updates

    def __init__(self, state_manager: "StateManager", parent: QObject | None = None):
        """
        Initialize the frame navigation controller.

        Args:
            state_manager: Application state manager
            parent: Parent QObject
        """
        super().__init__(parent)
        self.state_manager = state_manager

        # Create UI components
        self._create_widgets()

        # Connect signals
        self._connect_signals()

    def _create_widgets(self) -> None:
        """Create frame navigation widgets."""
        style = QApplication.style()

        # Frame spinbox
        self.frame_spinbox = QSpinBox()
        self.frame_spinbox.setMinimum(1)
        self.frame_spinbox.setMaximum(1000)  # Default max, will be updated based on data
        self.frame_spinbox.setValue(1)
        self.frame_spinbox.setToolTip("Current frame")

        # Frame slider
        self.frame_slider = QSlider(Qt.Orientation.Horizontal)
        self.frame_slider.setMinimum(1)
        self.frame_slider.setMaximum(1000)  # Match spinbox max
        self.frame_slider.setValue(1)
        self.frame_slider.setToolTip("Scrub through frames")

        # Navigation buttons
        self.btn_first = QPushButton()
        self.btn_first.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        self.btn_first.setToolTip("First frame")

        self.btn_prev = QPushButton()
        self.btn_prev.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaSeekBackward))
        self.btn_prev.setToolTip("Previous frame")

        self.btn_next = QPushButton()
        self.btn_next.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward))
        self.btn_next.setToolTip("Next frame")

        self.btn_last = QPushButton()
        self.btn_last.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        self.btn_last.setToolTip("Last frame")

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        # Frame controls
        self.frame_spinbox.valueChanged.connect(self._on_frame_changed)
        self.frame_slider.valueChanged.connect(self._on_slider_changed)

        # Navigation buttons
        self.btn_first.clicked.connect(self._on_first_frame)
        self.btn_prev.clicked.connect(self._on_prev_frame)
        self.btn_next.clicked.connect(self._on_next_frame)
        self.btn_last.clicked.connect(self._on_last_frame)

    def _on_frame_changed(self, value: int) -> None:
        """
        Handle frame spinbox value change.

        Args:
            value: New frame number
        """
        logger.debug(f"[FRAME] Spinbox changed to: {value}")

        # Update slider without triggering its signal
        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(value)
        self.frame_slider.blockSignals(False)

        # Update state and emit signal
        self._update_frame(value)

    def _on_slider_changed(self, value: int) -> None:
        """
        Handle timeline slider value change.

        Args:
            value: New slider value (frame number)
        """
        logger.debug(f"[FRAME] Slider changed to: {value}")

        # Update spinbox without triggering its signal
        self.frame_spinbox.blockSignals(True)
        self.frame_spinbox.setValue(value)
        self.frame_spinbox.blockSignals(False)

        # Update state and emit signal
        self._update_frame(value)

    def _update_frame(self, frame: int) -> None:
        """
        Update the current frame and notify listeners.

        Args:
            frame: Frame number to set
        """
        # Update state manager
        self.state_manager.current_frame = frame
        logger.debug(f"[FRAME] State manager current_frame set to: {frame}")

        # Emit signal for other components
        self.frame_changed.emit(frame)

        # Update status
        total = self.frame_spinbox.maximum()
        self.status_message.emit(f"Frame {frame}/{total}")

    def _on_first_frame(self) -> None:
        """Jump to first frame."""
        self.set_frame(1)

    def _on_prev_frame(self) -> None:
        """Go to previous frame."""
        current = self.frame_spinbox.value()
        if current > 1:
            self.set_frame(current - 1)

    def _on_next_frame(self) -> None:
        """Go to next frame."""
        current = self.frame_spinbox.value()
        if current < self.frame_spinbox.maximum():
            self.set_frame(current + 1)

    def _on_last_frame(self) -> None:
        """Jump to last frame."""
        self.set_frame(self.frame_spinbox.maximum())

    def set_frame(self, frame: int) -> None:
        """
        Set the current frame programmatically.

        This is the public API for setting frames from outside the controller,
        such as from playback or external commands.

        Args:
            frame: Frame number to set
        """
        # Clamp to valid range
        frame = max(1, min(frame, self.frame_spinbox.maximum()))

        # Update spinbox (will trigger the chain of updates)
        self.frame_spinbox.setValue(frame)

    def set_frame_range(self, min_frame: int, max_frame: int) -> None:
        """
        Set the valid frame range.

        Args:
            min_frame: Minimum frame number (usually 1)
            max_frame: Maximum frame number
        """
        # Update spinbox range
        self.frame_spinbox.setMinimum(min_frame)
        self.frame_spinbox.setMaximum(max_frame)

        # Update slider range
        self.frame_slider.setMinimum(min_frame)
        self.frame_slider.setMaximum(max_frame)

        # Ensure current value is within range
        current = self.frame_spinbox.value()
        if current < min_frame:
            self.set_frame(min_frame)
        elif current > max_frame:
            self.set_frame(max_frame)

        # Update state manager's total frames
        self.state_manager.total_frames = max_frame

        logger.debug(f"Frame range set to {min_frame}-{max_frame}")

    def update_frame_display(self, frame: int, update_state: bool = True) -> None:
        """
        Update frame display without emitting signals.

        This is used when the frame is changed externally and we just
        need to update the UI to reflect it.

        Args:
            frame: Frame number to display
            update_state: Whether to update state manager
        """
        # Block signals to prevent feedback loops
        self.frame_spinbox.blockSignals(True)
        self.frame_spinbox.setValue(frame)
        self.frame_spinbox.blockSignals(False)

        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(frame)
        self.frame_slider.blockSignals(False)

        if update_state:
            self.state_manager.current_frame = frame
            logger.debug(f"[FRAME] Display updated to: {frame}")

    def get_current_frame(self) -> int:
        """
        Get the current frame number.

        Returns:
            Current frame number
        """
        return self.frame_spinbox.value()

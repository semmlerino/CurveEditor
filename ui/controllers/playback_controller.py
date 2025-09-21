"""
Playback controller for oscillating timeline playback.

This module handles all playback-related functionality including play/pause,
FPS control, and oscillating playback modes.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QApplication, QPushButton, QSpinBox, QStyle

if TYPE_CHECKING:
    from ui.state_manager import StateManager

from core.logger_utils import get_logger

logger = get_logger(__name__)


class PlaybackMode(Enum):
    """Enumeration for oscillating playback modes."""

    STOPPED = auto()
    PLAYING_FORWARD = auto()
    PLAYING_BACKWARD = auto()


@dataclass
class PlaybackState:
    """State management for oscillating timeline playback."""

    mode: PlaybackMode = PlaybackMode.STOPPED
    fps: int = 12
    current_frame: int = 1
    min_frame: int = 1
    max_frame: int = 100
    loop_boundaries: bool = True  # True for oscillation, False for loop-to-start


class PlaybackController(QObject):
    """
    Controller for managing timeline playback functionality.

    This controller handles oscillating playback, FPS control, and
    play/pause functionality extracted from MainWindow.
    """

    # Signals
    frame_requested = Signal(int)  # Request a specific frame
    playback_started = Signal()
    playback_stopped = Signal()
    status_message = Signal(str)  # Status bar updates

    def __init__(self, state_manager: "StateManager", parent: QObject | None = None):
        """
        Initialize the playback controller.

        Args:
            state_manager: Application state manager
            parent: Parent QObject
        """
        super().__init__(parent)
        self.state_manager = state_manager
        self.playback_state = PlaybackState()

        # Create UI components
        self._create_widgets()

        # Setup timer
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._on_playback_timer)

        # Connect signals
        self._connect_signals()

    def _create_widgets(self) -> None:
        """Create playback control widgets."""
        style = QApplication.style()

        # Play/pause button
        self.btn_play_pause = QPushButton()
        self.btn_play_pause.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play_pause.setCheckable(True)
        self.btn_play_pause.setToolTip("Play/Pause (Spacebar)")

        # FPS spinbox
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setMinimum(1)
        self.fps_spinbox.setMaximum(120)
        self.fps_spinbox.setValue(24)
        self.fps_spinbox.setSuffix(" fps")
        self.fps_spinbox.setToolTip("Playback speed")

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        self.btn_play_pause.toggled.connect(self._on_play_pause)
        self.fps_spinbox.valueChanged.connect(self._on_fps_changed)

    def toggle_playback(self) -> None:
        """Toggle oscillating playback (public API for spacebar)."""
        if self.playback_state.mode == PlaybackMode.STOPPED:
            self._start_oscillating_playback()
        else:
            self._stop_oscillating_playback()

    def start_playback(self) -> None:
        """Start playback animation (Protocol API)."""
        self._start_oscillating_playback()

    def stop_playback(self) -> None:
        """Stop playback animation (Protocol API)."""
        self._stop_oscillating_playback()

    def set_frame_rate(self, fps: int) -> None:
        """Set playback frame rate (Protocol API)."""
        self.playback_state.fps = fps
        self._fps_spinbox.setValue(fps)
        if self.playback_timer.isActive():
            # Update timer interval if currently playing
            self.playback_timer.setInterval(int(1000 / fps))

    def _on_play_pause(self, checked: bool) -> None:
        """Handle play/pause button toggle."""
        if checked:
            self._start_oscillating_playback()
        else:
            self._stop_oscillating_playback()

    def _on_fps_changed(self, value: int) -> None:
        """Handle FPS change."""
        self.playback_state.fps = value
        # Update timer interval if playing
        if self.playback_state.mode != PlaybackMode.STOPPED:
            interval = int(1000 / value)
            self.playback_timer.setInterval(interval)
        logger.debug(f"FPS changed to {value}")

    def _start_oscillating_playback(self) -> None:
        """Start oscillating timeline playback."""
        style = QApplication.style()

        # Update playback bounds from current data
        self.update_playback_bounds()

        # Set initial mode
        self.playback_state.mode = PlaybackMode.PLAYING_FORWARD
        self.playback_state.current_frame = self.state_manager.current_frame

        # Start timer
        fps = self.fps_spinbox.value()
        interval = int(1000 / fps)
        self.playback_timer.start(interval)

        # Update UI (block signals to prevent recursive calls)
        self.btn_play_pause.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        self.btn_play_pause.blockSignals(True)
        self.btn_play_pause.setChecked(True)
        self.btn_play_pause.blockSignals(False)

        # Emit signals
        self.playback_started.emit()
        self.status_message.emit(
            f"Started oscillating playback at {fps} FPS "
            f"(bounds: {self.playback_state.min_frame}-{self.playback_state.max_frame})"
        )
        logger.info(
            f"Started oscillating playback at {fps} FPS "
            f"(bounds: {self.playback_state.min_frame}-{self.playback_state.max_frame})"
        )

    def _stop_oscillating_playback(self) -> None:
        """Stop oscillating timeline playback."""
        style = QApplication.style()

        self.playback_timer.stop()
        self.playback_state.mode = PlaybackMode.STOPPED

        # Update UI (block signals to prevent recursive calls)
        self.btn_play_pause.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.btn_play_pause.blockSignals(True)
        self.btn_play_pause.setChecked(False)
        self.btn_play_pause.blockSignals(False)

        # Emit signals
        self.playback_stopped.emit()
        self.status_message.emit("Stopped playback")
        logger.info("Stopped oscillating playback")

    def _on_playback_timer(self) -> None:
        """Handle oscillating playback timer tick."""
        # Only handle oscillating playback if mode is not stopped
        if self.playback_state.mode == PlaybackMode.STOPPED:
            return

        current = self.state_manager.current_frame

        # Handle forward playback
        if self.playback_state.mode == PlaybackMode.PLAYING_FORWARD:
            next_frame = current + 1
            if current >= self.playback_state.max_frame:
                # Reached end, reverse direction
                self.playback_state.mode = PlaybackMode.PLAYING_BACKWARD
                next_frame = current - 1
                logger.debug(f"Reached max frame {self.playback_state.max_frame}, reversing to backward")
            self.frame_requested.emit(next_frame)

        # Handle backward playback
        elif self.playback_state.mode == PlaybackMode.PLAYING_BACKWARD:
            next_frame = current - 1
            if current <= self.playback_state.min_frame:
                # Reached start, reverse direction
                self.playback_state.mode = PlaybackMode.PLAYING_FORWARD
                next_frame = current + 1
                logger.debug(f"Reached min frame {self.playback_state.min_frame}, reversing to forward")
            self.frame_requested.emit(next_frame)

    @property
    def is_playing(self) -> bool:
        """Check if playback is active."""
        return self.playback_state.mode != PlaybackMode.STOPPED

    def _advance_frame(self) -> None:
        """Advance one frame (for testing compatibility)."""
        self._on_playback_timer()

    def get_playback_mode(self) -> PlaybackMode:
        """Get the current playback mode."""
        return self.playback_state.mode

    def set_playback_mode(self, mode: PlaybackMode) -> None:
        """Set the playback mode (limited to oscillating behavior)."""
        # This controller only supports oscillating, so we just log
        logger.debug(f"PlaybackController only supports oscillating mode, ignoring mode: {mode}")

    def update_playback_bounds(self) -> None:
        """Update playback bounds based on current curve data."""
        # Get bounds from state manager or curve data
        # Use total frames from state manager (always present as a property)
        self.playback_state.min_frame = 1
        # Handle case where state_manager doesn't have total_frames (e.g., minimal test doubles)
        max_frame = getattr(self.state_manager, "total_frames", 100)  # Default to 100 if not present
        self.playback_state.max_frame = max_frame
        logger.debug(f"Updated playback bounds: {self.playback_state.min_frame}-{self.playback_state.max_frame}")

    def set_frame_range(self, min_frame: int, max_frame: int) -> None:
        """
        Set the frame range for playback.

        Args:
            min_frame: Minimum frame number
            max_frame: Maximum frame number
        """
        self.playback_state.min_frame = min_frame
        self.playback_state.max_frame = max_frame
        logger.debug(f"Frame range set to {min_frame}-{max_frame}")

"""
Playback controller for timeline animation.

Manages oscillating playback of timeline frames, including
play/pause state, FPS control, and boundary handling.
"""

import logging
from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtWidgets import QPushButton, QSpinBox, QTabWidget

logger = logging.getLogger(__name__)


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


class CurveViewProtocol(Protocol):
    """Protocol for CurveView interface."""

    @property
    def curve_data(self) -> list[tuple[int, float, float]] | None: ...


class MainWindowProtocol(Protocol):
    """Protocol for MainWindow interface needed by PlaybackController."""

    @property
    def fps_spinbox(self) -> QSpinBox | None: ...
    @property
    def playback_timer(self) -> QTimer | None: ...
    @property
    def btn_play_pause(self) -> QPushButton | None: ...
    @property
    def curve_view(self) -> CurveViewProtocol | None: ...
    @property
    def timeline_tabs(self) -> QTabWidget | None: ...
    @property
    def current_frame(self) -> int: ...
    @current_frame.setter
    def current_frame(self, value: int) -> None: ...

    def get_current_frame(self) -> int: ...
    def set_current_frame(self, frame: int) -> None: ...
    def _get_current_frame(self) -> int: ...
    def _set_current_frame(self, frame: int) -> None: ...
    def update_status(self, message: str) -> None: ...


class PlaybackController(QObject):
    """Controller for managing timeline playback."""

    # Signals
    playback_started: Signal = Signal()
    playback_stopped: Signal = Signal()
    frame_changed: Signal = Signal(int)

    def __init__(self, main_window: MainWindowProtocol, parent: QObject | None = None):
        """Initialize the playback controller.

        Args:
            main_window: Reference to the main window
            parent: Optional parent QObject
        """
        super().__init__(parent)
        self.main_window: MainWindowProtocol = main_window
        self.state: PlaybackState = PlaybackState()

        # Connect timer if available
        if self.main_window.playback_timer:
            self.main_window.playback_timer.timeout.connect(self._on_timer_tick)

    def toggle_playback(self) -> None:
        """Toggle oscillating playback on/off."""
        if self.state.mode == PlaybackMode.STOPPED:
            self.start_playback()
        else:
            self.stop_playback()

    def start_playback(self) -> None:
        """Start oscillating timeline playback."""
        # Update frame boundaries from current data
        self._update_bounds()

        # Get FPS from UI or use default
        fps = 12  # Default
        if self.main_window.fps_spinbox:
            fps = self.main_window.fps_spinbox.value()

        # Set FPS-based timer interval
        interval = int(1000 / fps)  # Convert to milliseconds

        # Start forward playback
        self.state.mode = PlaybackMode.PLAYING_FORWARD
        self.state.current_frame = self.main_window._get_current_frame()

        # Start the timer
        if self.main_window.playback_timer:
            self.main_window.playback_timer.start(interval)

        logger.info(
            f"Started oscillating playback at {fps} FPS (bounds: {self.state.min_frame}-{self.state.max_frame})"
        )

        self.playback_started.emit()
        self.main_window.update_status(f"Playing at {fps} FPS")

    def stop_playback(self) -> None:
        """Stop oscillating timeline playback."""
        if self.main_window.playback_timer:
            self.main_window.playback_timer.stop()

        self.state.mode = PlaybackMode.STOPPED
        logger.info("Stopped oscillating playback")

        self.playback_stopped.emit()
        self.main_window.update_status("Playback stopped")

    def set_fps(self, fps: int) -> None:
        """Update playback FPS.

        Args:
            fps: Frames per second
        """
        self.state.fps = fps

        # Update timer interval if playing
        if self.state.mode != PlaybackMode.STOPPED and self.main_window.playback_timer:
            interval = int(1000 / fps)
            self.main_window.playback_timer.setInterval(interval)

    def _on_timer_tick(self) -> None:
        """Handle playback timer tick."""
        # Only handle oscillating playback if mode is not stopped
        if self.state.mode == PlaybackMode.STOPPED:
            return

        current = self.main_window._get_current_frame()

        if self.state.mode == PlaybackMode.PLAYING_FORWARD:
            # Move forward
            if current >= self.state.max_frame:
                # Hit upper boundary - reverse direction
                self.state.mode = PlaybackMode.PLAYING_BACKWARD
                next_frame = max(current - 1, self.state.min_frame)
            else:
                next_frame = current + 1

        elif self.state.mode == PlaybackMode.PLAYING_BACKWARD:
            # Move backward
            if current <= self.state.min_frame:
                # Hit lower boundary - reverse direction
                self.state.mode = PlaybackMode.PLAYING_FORWARD
                next_frame = min(current + 1, self.state.max_frame)
            else:
                next_frame = current - 1
        else:
            # Fallback - shouldn't happen
            return

        # Update frame and UI
        self.main_window._set_current_frame(next_frame)
        self.frame_changed.emit(next_frame)

    def _update_bounds(self) -> None:
        """Update playback frame bounds based on current data."""
        # Get bounds from data service if available
        try:
            # curve_view is initialized as None in __init__
            if (
                self.main_window.curve_view is not None
                and getattr(self.main_window.curve_view, "curve_data", None) is not None
                and self.main_window.curve_view.curve_data
            ):
                # Calculate frame bounds directly from curve data
                frames = [int(point[0]) for point in self.main_window.curve_view.curve_data]
                if frames:
                    self.state.min_frame = max(1, min(frames))
                    self.state.max_frame = max(frames)
                else:
                    self.state.min_frame = 1
                    self.state.max_frame = 100
            else:
                # Use timeline widget bounds if available
                # timeline_tabs is Optional
                if self.main_window.timeline_tabs is not None:
                    self.state.min_frame = getattr(self.main_window.timeline_tabs, "min_frame", 1)
                    self.state.max_frame = getattr(self.main_window.timeline_tabs, "max_frame", 100)
                else:
                    # Default bounds
                    self.state.min_frame = 1
                    self.state.max_frame = 100
        except Exception as e:
            # Fallback to default bounds on any error
            logger.warning(f"Error getting playback bounds, using defaults: {e}")
            self.state.min_frame = 1
            self.state.max_frame = 100

        # Ensure current frame is within bounds
        current = self.main_window.current_frame
        if current < self.state.min_frame:
            self.main_window.current_frame = self.state.min_frame
        elif current > self.state.max_frame:
            self.main_window.current_frame = self.state.max_frame

    def get_state(self) -> PlaybackState:
        """Get current playback state.

        Returns:
            Current PlaybackState
        """
        return self.state

    def is_playing(self) -> bool:
        """Check if playback is active.

        Returns:
            True if playing, False if stopped
        """
        return self.state.mode != PlaybackMode.STOPPED

    def sync_current_frame(self, frame: int) -> None:
        """Sync the playback controller's current frame state.

        This method should be called when the main window's current_frame
        is changed externally to keep the playback controller in sync.

        Args:
            frame: The new current frame number
        """
        self.state.current_frame = frame
        logger.debug(f"Playback controller synced to frame {frame}")

    def on_playback_timer(self) -> None:
        """Public interface for handling playback timer events."""
        self._on_timer_tick()

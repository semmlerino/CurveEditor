"""
Unified timeline controller for playback and frame navigation.

This module combines timeline playback (play/pause, FPS, oscillating modes)
with frame navigation (spinbox/slider sync, navigation buttons, range management).
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QApplication,
    QPushButton,
    QSlider,
    QSpinBox,
    QStyle,
)

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

    @property
    def is_playing(self) -> bool:
        """Check if playback is active."""
        return self.mode != PlaybackMode.STOPPED

    @property
    def is_playing_forward(self) -> bool:
        """Check if playing forward."""
        return self.mode == PlaybackMode.PLAYING_FORWARD

    @property
    def is_playing_backward(self) -> bool:
        """Check if playing backward."""
        return self.mode == PlaybackMode.PLAYING_BACKWARD


class TimelineController(QObject):
    """
    Unified controller for timeline navigation and playback.

    Combines frame navigation (spinbox, slider, buttons) with
    playback functionality (play/pause, FPS, oscillating modes).
    """

    # Signals
    frame_changed = Signal(int)  # Emitted when frame changes
    playback_started = Signal()
    playback_stopped = Signal()
    playback_state_changed = Signal(PlaybackMode)  # For UI updates
    status_message = Signal(str)  # Status bar updates

    def __init__(self, state_manager: "StateManager", parent: QObject | None = None):
        """
        Initialize the timeline controller.

        Args:
            state_manager: Application state manager
            parent: Parent QObject (typically MainWindow)
        """
        super().__init__(parent)
        self.state_manager = state_manager
        self.playback_state = PlaybackState()
        # Store reference to MainWindow for accessing other components
        self.main_window = parent

        # Create UI components
        self._create_widgets()

        # Setup timer for playback
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._on_playback_timer)

        # Connect signals
        self._connect_signals()

    def _create_widgets(self) -> None:
        """Create all timeline control widgets."""
        style = QApplication.style()

        # ========== Navigation Widgets ==========
        # Frame spinbox
        self.frame_spinbox = QSpinBox()
        self.frame_spinbox.setMinimum(1)
        self.frame_spinbox.setMaximum(1000)  # Default max, will be updated
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

        # ========== Playback Widgets ==========
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
        # Navigation signals
        self.frame_spinbox.valueChanged.connect(self._on_frame_changed)
        self.frame_slider.valueChanged.connect(self._on_slider_changed)
        self.btn_first.clicked.connect(self._on_first_frame)
        self.btn_prev.clicked.connect(self._on_prev_frame)
        self.btn_next.clicked.connect(self._on_next_frame)
        self.btn_last.clicked.connect(self._on_last_frame)

        # Playback signals
        self.btn_play_pause.toggled.connect(self._on_play_pause)
        self.fps_spinbox.valueChanged.connect(self._on_fps_changed)

    # ========== Frame Navigation Methods ==========

    def _on_frame_changed(self, value: int) -> None:
        """Handle frame spinbox value change."""
        logger.debug(f"[FRAME] Spinbox changed to: {value}")

        # Update slider without triggering its signal
        self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(value)
        self.frame_slider.blockSignals(False)

        # Update state and emit signal
        self._update_frame(value)

    def _on_slider_changed(self, value: int) -> None:
        """Handle timeline slider value change."""
        logger.debug(f"[FRAME] Slider changed to: {value}")

        # Update spinbox without triggering its signal
        self.frame_spinbox.blockSignals(True)
        self.frame_spinbox.setValue(value)
        self.frame_spinbox.blockSignals(False)

        # Update state and emit signal
        self._update_frame(value)

    def _update_frame(self, frame: int) -> None:
        """Update the current frame and notify listeners."""
        # Update state manager
        self.state_manager.current_frame = frame
        self.playback_state.current_frame = frame
        logger.debug(f"[FRAME] Current frame set to: {frame}")

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

        Args:
            frame: Frame number to set
        """
        # Clamp to valid range
        frame = max(1, min(frame, self.frame_spinbox.maximum()))

        # Update spinbox (will trigger the chain of updates)
        self.frame_spinbox.setValue(frame)

    def update_frame_display(self, frame: int, update_state: bool = True) -> None:
        """
        Update frame display without emitting signals.

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
            self.playback_state.current_frame = frame
            logger.debug(f"[FRAME] Display updated to: {frame}")

    def get_current_frame(self) -> int:
        """Get the current frame number."""
        return self.frame_spinbox.value()

    # Navigation Protocol API
    def next_frame(self) -> None:
        """Navigate to next frame."""
        self._on_next_frame()

    def previous_frame(self) -> None:
        """Navigate to previous frame."""
        self._on_prev_frame()

    def first_frame(self) -> None:
        """Navigate to first frame."""
        self._on_first_frame()

    def last_frame(self) -> None:
        """Navigate to last frame."""
        self._on_last_frame()

    def go_to_frame(self, frame: int) -> None:
        """Navigate to specific frame."""
        self.set_frame(frame)

    # ========== Playback Methods ==========

    def toggle_playback(self) -> None:
        """Toggle oscillating playback (public API for spacebar)."""
        if self.playback_state.mode == PlaybackMode.STOPPED:
            self._start_oscillating_playback()
        else:
            self._stop_oscillating_playback()

    def start_playback(self) -> None:
        """Start playback animation."""
        self._start_oscillating_playback()

    def stop_playback(self) -> None:
        """Stop playback animation."""
        self._stop_oscillating_playback()

    def set_frame_rate(self, fps: int) -> None:
        """Set playback frame rate."""
        self.playback_state.fps = fps
        self.fps_spinbox.setValue(fps)
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
        self._update_playback_bounds()

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
        self.playback_state_changed.emit(PlaybackMode.PLAYING_FORWARD)
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
        self.playback_state_changed.emit(PlaybackMode.STOPPED)
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
                self.playback_state_changed.emit(PlaybackMode.PLAYING_BACKWARD)
            self.set_frame(next_frame)

        # Handle backward playback
        elif self.playback_state.mode == PlaybackMode.PLAYING_BACKWARD:
            next_frame = current - 1
            if current <= self.playback_state.min_frame:
                # Reached start, reverse direction
                self.playback_state.mode = PlaybackMode.PLAYING_FORWARD
                next_frame = current + 1
                logger.debug(f"Reached min frame {self.playback_state.min_frame}, reversing to forward")
                self.playback_state_changed.emit(PlaybackMode.PLAYING_FORWARD)
            self.set_frame(next_frame)

    @property
    def is_playing(self) -> bool:
        """Check if playback is active."""
        return self.playback_state.mode != PlaybackMode.STOPPED

    def get_playback_mode(self) -> PlaybackMode:
        """Get the current playback mode."""
        return self.playback_state.mode

    def _update_playback_bounds(self) -> None:
        """Update playback bounds based on current curve data."""
        # Use the frame range already set in the navigation controls
        self.playback_state.min_frame = self.frame_spinbox.minimum()
        self.playback_state.max_frame = self.frame_spinbox.maximum()

        # Try to get actual frame range from curve data if available
        parent = self.parent()
        if parent is not None:
            curve_widget = getattr(parent, "curve_widget", None)
            if curve_widget is not None:
                curve_data = curve_widget.curve_data
                if curve_data:
                    # Get actual frame range from curve data
                    frames = [point[0] for point in curve_data]
                    self.playback_state.min_frame = min(frames)
                    self.playback_state.max_frame = max(frames)

        logger.debug(f"Updated playback bounds: {self.playback_state.min_frame}-{self.playback_state.max_frame}")

    # ========== Shared Methods ==========

    def set_frame_range(self, min_frame: int, max_frame: int) -> None:
        """
        Set the valid frame range for both navigation and playback.

        Args:
            min_frame: Minimum frame number (usually 1)
            max_frame: Maximum frame number
        """
        # Update navigation controls
        self.frame_spinbox.setMinimum(min_frame)
        self.frame_spinbox.setMaximum(max_frame)
        self.frame_slider.setMinimum(min_frame)
        self.frame_slider.setMaximum(max_frame)

        # Update playback bounds
        self.playback_state.min_frame = min_frame
        self.playback_state.max_frame = max_frame

        # Ensure current value is within range
        current = self.frame_spinbox.value()
        if current < min_frame:
            self.set_frame(min_frame)
        elif current > max_frame:
            self.set_frame(max_frame)

        # Update state manager's total frames
        self.state_manager.total_frames = max_frame

        logger.debug(f"Frame range set to {min_frame}-{max_frame}")

    @Slot(int)
    def on_frame_changed(self, frame: int) -> None:
        """Handle frame change from external sources."""
        self._on_frame_changed(frame)

    # ========== Timeline Tabs Methods (Protocol Compatibility) ==========

    def on_timeline_tab_clicked(self, frame: int) -> None:
        """Handle timeline tab click."""
        self.set_frame(frame)
        logger.debug(f"Timeline tab clicked: frame {frame}")

    def on_timeline_tab_hovered(self, frame: int) -> None:
        """Handle timeline tab hover."""
        # Could show preview or status message
        logger.debug(f"Timeline tab hovered: frame {frame}")

    def update_for_tracking_data(self, num_images: int) -> None:
        """Update timeline for tracking data."""
        if num_images > 0:
            self.set_frame_range(1, num_images)
        logger.debug(f"Updated timeline for {num_images} tracking images")

    def update_for_current_frame(self, frame: int) -> None:
        """Update timeline to show current frame."""
        self.update_frame_display(frame)

        # Also update timeline tabs if available
        if hasattr(self.main_window, "timeline_tabs") and self.main_window.timeline_tabs:
            logger.debug(f"Updating timeline_tabs to frame {frame}")
            self.main_window.timeline_tabs.set_current_frame(frame)
        else:
            logger.debug(f"Timeline_tabs not available for update to frame {frame}")

        logger.debug(f"Updated timeline for frame {frame}")

    def update_timeline_tabs(self, curve_data: object | None = None) -> None:
        """Update timeline tabs with curve data."""
        # This would update the visual timeline tabs if we had them
        logger.debug("Timeline tabs update requested")

    def connect_signals(self) -> None:
        """Connect timeline-related signals."""
        # Compatibility method for old timeline controller
        pass

    def clear(self) -> None:
        """Clear the timeline tabs."""
        # Reset frame range to defaults
        self.set_frame_range(1, 1)
        logger.debug("Timeline cleared")

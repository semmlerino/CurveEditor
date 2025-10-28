"""
Unified timeline controller for playback and frame navigation.

This module combines timeline playback (play/pause, FPS, oscillating modes)
with frame navigation (spinbox/slider sync, navigation buttons, range management).
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Qt, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication, QStyle

from ui import widget_factory

if TYPE_CHECKING:
    from ui.state_manager import StateManager

from core.frame_utils import clamp_frame
from core.logger_utils import get_logger
from stores.application_state import get_application_state

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
    frame_changed: Signal = Signal(int)  # Emitted when frame changes
    playback_started: Signal = Signal()
    playback_stopped: Signal = Signal()
    playback_state_changed: Signal = Signal(PlaybackMode)  # For UI updates
    status_message: Signal = Signal(str)  # Status bar updates

    def __init__(self, state_manager: "StateManager", parent: QObject | None = None):
        """
        Initialize the timeline controller.

        Args:
            state_manager: Application state manager
            parent: Parent QObject (typically MainWindow)
        """
        super().__init__(parent)
        self.state_manager: StateManager = state_manager
        self.playback_state: PlaybackState = PlaybackState()
        # Store reference to MainWindow for accessing other components
        self.main_window: QObject | None = parent

        # Create UI components
        self._create_widgets()

        # Setup timer for playback
        self.playback_timer: QTimer = QTimer(self)
        _ = self.playback_timer.timeout.connect(self._on_playback_timer)

        # Connect signals
        self._connect_signals()

    def __del__(self) -> None:
        """Disconnect all signals to prevent memory leaks.

        TimelineController creates 9 signal connections to UI widgets and timers.
        Without cleanup, these connections would keep the controller alive,
        causing memory leaks.
        """
        # Disconnect playback timer
        try:
            if self.playback_timer:
                _ = self.playback_timer.timeout.disconnect(self._on_playback_timer)
                self.playback_timer.stop()
        except (RuntimeError, AttributeError):
            pass  # Already disconnected or objects destroyed

        # Disconnect navigation signals
        try:
            if self.frame_spinbox:
                _ = self.frame_spinbox.valueChanged.disconnect(self._on_frame_changed)
            if self.frame_slider:
                _ = self.frame_slider.valueChanged.disconnect(self._on_slider_changed)
            if self.btn_first:
                _ = self.btn_first.clicked.disconnect(self._on_first_frame)
            if self.btn_prev:
                _ = self.btn_prev.clicked.disconnect(self._on_prev_frame)
            if self.btn_next:
                _ = self.btn_next.clicked.disconnect(self._on_next_frame)
            if self.btn_last:
                _ = self.btn_last.clicked.disconnect(self._on_last_frame)
        except (RuntimeError, AttributeError):
            pass  # Already disconnected or objects destroyed

        # Disconnect playback signals
        try:
            if self.btn_play_pause:
                _ = self.btn_play_pause.toggled.disconnect(self._on_play_pause)
            if self.fps_spinbox:
                _ = self.fps_spinbox.valueChanged.disconnect(self._on_fps_changed)
        except (RuntimeError, AttributeError):
            pass  # Already disconnected or objects destroyed

    def _create_widgets(self) -> None:
        """Create all timeline control widgets."""
        style = QApplication.style()

        # ========== Navigation Widgets ==========
        # Frame spinbox
        self.frame_spinbox = widget_factory.create_spinbox(
            minimum=1, maximum=1000, value=1, tooltip="Current frame"  # Default max, will be updated
        )

        # Frame slider
        self.frame_slider = widget_factory.create_slider(
            minimum=1, maximum=1000, value=1, orientation=Qt.Orientation.Horizontal, tooltip="Scrub through frames"
        )

        # Navigation buttons
        self.btn_first = widget_factory.create_button_with_icon(
            icon=style.standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward), tooltip="First frame"
        )

        self.btn_prev = widget_factory.create_button_with_icon(
            icon=style.standardIcon(QStyle.StandardPixmap.SP_MediaSeekBackward), tooltip="Previous frame"
        )

        self.btn_next = widget_factory.create_button_with_icon(
            icon=style.standardIcon(QStyle.StandardPixmap.SP_MediaSeekForward), tooltip="Next frame"
        )

        self.btn_last = widget_factory.create_button_with_icon(
            icon=style.standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward), tooltip="Last frame"
        )

        # ========== Playback Widgets ==========
        # Play/pause button
        self.btn_play_pause = widget_factory.create_button_with_icon(
            icon=style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay), tooltip="Play/Pause (Spacebar)", checkable=True
        )

        # FPS spinbox
        self.fps_spinbox = widget_factory.create_spinbox(
            minimum=1, maximum=120, value=24, tooltip="Playback speed", suffix=" fps"
        )

    def _connect_signals(self) -> None:
        """Connect widget signals."""
        # Navigation signals
        _ = self.frame_spinbox.valueChanged.connect(self._on_frame_changed)
        _ = self.frame_slider.valueChanged.connect(self._on_slider_changed)
        _ = self.btn_first.clicked.connect(self._on_first_frame)
        _ = self.btn_prev.clicked.connect(self._on_prev_frame)
        _ = self.btn_next.clicked.connect(self._on_next_frame)
        _ = self.btn_last.clicked.connect(self._on_last_frame)

        # Playback signals
        _ = self.btn_play_pause.toggled.connect(self._on_play_pause)
        _ = self.fps_spinbox.valueChanged.connect(self._on_fps_changed)

    # ========== Frame Navigation Methods ==========

    def _on_frame_changed(self, value: int) -> None:
        """Handle frame spinbox value change."""
        # Update slider without triggering its signal
        _ = self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(value)
        _ = self.frame_slider.blockSignals(False)

        # Update state and emit signal
        self._update_frame(value)

    def _on_slider_changed(self, value: int) -> None:
        """Handle timeline slider value change."""
        # Update spinbox without triggering its signal
        _ = self.frame_spinbox.blockSignals(True)
        self.frame_spinbox.setValue(value)
        _ = self.frame_spinbox.blockSignals(False)

        # Update state and emit signal
        self._update_frame(value)

    def _update_frame(self, frame: int) -> None:
        """Update the current frame and notify listeners."""
        # Update ApplicationState (single source of truth)
        get_application_state().set_frame(frame)

        # REMOVED: self.frame_changed.emit(frame)
        # Reason: ApplicationState already emits frame_changed signal via StateManager.
        # This emission was redundant and only connected to dead code in MainWindow.
        # All real frame change handling is done via ApplicationState → StateManager
        # → FrameChangeCoordinator (with QueuedConnection for proper timing).

        # Update status
        total = self.frame_spinbox.maximum()
        self.status_message.emit(f"Frame {frame}/{total}")

    def _on_first_frame(self) -> None:
        """Jump to first frame."""
        self.set_frame(1)

    def _on_prev_frame(self) -> None:
        """Go to previous frame."""
        current = get_application_state().current_frame
        if current > 1:
            self.set_frame(current - 1)

    def _on_next_frame(self) -> None:
        """Go to next frame."""
        current = get_application_state().current_frame
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
        frame = clamp_frame(frame, 1, self.frame_spinbox.maximum())

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
        _ = self.frame_spinbox.blockSignals(True)
        self.frame_spinbox.setValue(frame)
        _ = self.frame_spinbox.blockSignals(False)

        _ = self.frame_slider.blockSignals(True)
        self.frame_slider.setValue(frame)
        _ = self.frame_slider.blockSignals(False)

        if update_state:
            get_application_state().set_frame(frame)
            logger.debug(f"[FRAME] Display updated to: {frame}")

    def get_current_frame(self) -> int:
        """Get the current frame number."""
        return get_application_state().current_frame

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

        # Start timer
        fps = self.fps_spinbox.value()
        interval = int(1000 / fps)
        self.playback_timer.start(interval)

        # Update UI (block signals to prevent recursive calls)
        self.btn_play_pause.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        _ = self.btn_play_pause.blockSignals(True)
        self.btn_play_pause.setChecked(True)
        _ = self.btn_play_pause.blockSignals(False)

        # Emit signals
        self.playback_started.emit()
        self.playback_state_changed.emit(PlaybackMode.PLAYING_FORWARD)
        self.status_message.emit(
            f"Started oscillating playback at {fps} FPS (bounds: {self.playback_state.min_frame}-{self.playback_state.max_frame})"
        )
        logger.info(
            f"Started oscillating playback at {fps} FPS (bounds: {self.playback_state.min_frame}-{self.playback_state.max_frame})"
        )

    def _stop_oscillating_playback(self) -> None:
        """Stop oscillating timeline playback."""
        style = QApplication.style()

        self.playback_timer.stop()
        self.playback_state.mode = PlaybackMode.STOPPED

        # Update UI (block signals to prevent recursive calls)
        self.btn_play_pause.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        _ = self.btn_play_pause.blockSignals(True)
        self.btn_play_pause.setChecked(False)
        _ = self.btn_play_pause.blockSignals(False)

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

        current = get_application_state().current_frame

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
        parent = self.parent()  # Returns non-None QObject
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

    def update_frame_range(self, min_frame: int, max_frame: int) -> None:
        """
        Update all frame range UI elements (spinbox, slider, label).

        Single source of truth for frame range UI updates across controllers.

        Args:
            min_frame: Minimum frame number
            max_frame: Maximum frame number
        """
        try:
            if self.frame_spinbox:
                self.frame_spinbox.setRange(min_frame, max_frame)
            if self.frame_slider:
                self.frame_slider.setRange(min_frame, max_frame)
            if self.main_window:
                total_frames_label = getattr(self.main_window, "total_frames_label", None)
                if total_frames_label:
                    total_frames_label.setText(str(max_frame))
            logger.debug(f"Frame range updated: {min_frame}-{max_frame}")
        except RuntimeError:
            # Widgets may have been deleted during application shutdown
            pass

    def set_frame_range(self, min_frame: int, max_frame: int) -> None:
        """
        Set the valid frame range for both navigation and playback.

        Args:
            min_frame: Minimum frame number (usually 1)
            max_frame: Maximum frame number
        """
        # Only update controls if we have a valid range
        # Setting spinbox.setMaximum(0) when current value > 0 causes Qt to
        # automatically change the value to 0, triggering unwanted frame changes
        if max_frame > 0:
            # Update UI elements via centralized method
            self.update_frame_range(min_frame, max_frame)

            # Update playback bounds
            self.playback_state.min_frame = min_frame
            self.playback_state.max_frame = max_frame

            # Ensure current value is within range
            current = get_application_state().current_frame
            if current < min_frame:
                self.set_frame(min_frame)
            elif current > max_frame:
                self.set_frame(max_frame)

            logger.debug(f"Frame range set to {min_frame}-{max_frame}")
        else:
            # Invalid range (max_frame <= 0) - skip update to preserve current state
            logger.debug(f"Skipping frame range update: invalid range {min_frame}-{max_frame}")

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
        """Handle timeline tab hover.

        Args:
            frame: Frame number (reserved for future preview functionality)
        """
        # Could show preview or status message
        _ = frame  # Suppress unused parameter warning

    def update_for_tracking_data(self, num_images: int) -> None:
        """Update timeline for tracking data."""
        if num_images > 0:
            self.set_frame_range(1, num_images)
        logger.debug(f"Updated timeline for {num_images} tracking images")

    def update_for_current_frame(self, frame: int) -> None:
        """Update timeline to show current frame."""
        self.update_frame_display(frame)

        # Timeline tabs will update themselves via StateManager.frame_changed signal

    def update_timeline_tabs(self, curve_data: object | None = None) -> None:
        """Update timeline tabs with curve data."""
        # Parameter kept for protocol compliance but intentionally unused
        _ = curve_data  # Suppress unused variable warning
        # This would update the visual timeline tabs if we had them
        logger.debug("Timeline tabs update requested")

    def connect_signals(self) -> None:
        """Connect timeline-related signals."""
        # Compatibility method for old timeline controller

    def clear(self) -> None:
        """Clear the timeline tabs."""
        # Reset frame range to defaults
        self.set_frame_range(1, 1)
        logger.debug("Timeline cleared")

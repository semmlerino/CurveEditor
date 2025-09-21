"""
Reactive frame state store for CurveEditor.

This store manages all frame-related state including current frame,
frame range, and playback state. It derives frame range from the
CurveDataStore to maintain a single source of truth.
"""

from PySide6.QtCore import QObject, Signal

from core.logger_utils import get_logger
from core.type_aliases import CurveDataList

logger = get_logger("frame_store")


class FrameStore(QObject):
    """
    Centralized store for frame-related state with reactive signals.

    This store manages:
    - Current frame position
    - Frame range (derived from curve data)
    - Playback state
    """

    # Signals for frame state changes
    current_frame_changed = Signal(int)  # New current frame
    frame_range_changed = Signal(int, int)  # min_frame, max_frame
    playback_state_changed = Signal(bool)  # is_playing

    def __init__(self):
        """Initialize the frame store."""
        super().__init__()

        # Frame state
        self._current_frame: int = 1
        self._min_frame: int = 1
        self._max_frame: int = 1
        self._is_playing: bool = False

        logger.info("FrameStore initialized")

    # ==================== Frame Access ====================

    @property
    def current_frame(self) -> int:
        """Get the current frame."""
        return self._current_frame

    @property
    def min_frame(self) -> int:
        """Get the minimum frame."""
        return self._min_frame

    @property
    def max_frame(self) -> int:
        """Get the maximum frame."""
        return self._max_frame

    @property
    def frame_count(self) -> int:
        """Get total number of frames."""
        return self._max_frame - self._min_frame + 1

    @property
    def is_playing(self) -> bool:
        """Get playback state."""
        return self._is_playing

    # ==================== Frame Modification ====================

    def set_current_frame(self, frame: int) -> None:
        """
        Set the current frame.

        Args:
            frame: Frame number to set (will be clamped to valid range)
        """
        # Clamp to valid range
        frame = max(self._min_frame, min(frame, self._max_frame))

        if self._current_frame != frame:
            self._current_frame = frame
            self.current_frame_changed.emit(frame)
            logger.debug(f"Current frame changed to: {frame}")

    def set_playback_state(self, is_playing: bool) -> None:
        """
        Set playback state.

        Args:
            is_playing: True if playing, False if stopped
        """
        if self._is_playing != is_playing:
            self._is_playing = is_playing
            self.playback_state_changed.emit(is_playing)
            logger.debug(f"Playback state changed to: {'playing' if is_playing else 'stopped'}")

    def next_frame(self) -> None:
        """Move to next frame."""
        self.set_current_frame(self._current_frame + 1)

    def previous_frame(self) -> None:
        """Move to previous frame."""
        self.set_current_frame(self._current_frame - 1)

    def first_frame(self) -> None:
        """Move to first frame."""
        self.set_current_frame(self._min_frame)

    def last_frame(self) -> None:
        """Move to last frame."""
        self.set_current_frame(self._max_frame)

    # ==================== Data Synchronization ====================

    def sync_with_curve_data(self, curve_data: CurveDataList) -> None:
        """
        Synchronize frame range with curve data.

        This method derives the frame range from the curve data,
        ensuring the frame store stays in sync with the actual data.

        Args:
            curve_data: Curve data to sync with
        """
        if not curve_data:
            # No data - reset to default
            self._update_frame_range(1, 1)
            return

        # Calculate frame range from data
        frames: list[int] = []
        for point in curve_data:
            if len(point) >= 3:
                try:
                    frame = int(point[0])
                    frames.append(frame)
                except (ValueError, TypeError):
                    continue

        if frames:
            min_frame = min(frames)
            max_frame = max(frames)
            self._update_frame_range(min_frame, max_frame)
        else:
            # No valid frames - reset to default
            self._update_frame_range(1, 1)

    def _update_frame_range(self, min_frame: int, max_frame: int) -> None:
        """
        Update the frame range.

        Args:
            min_frame: New minimum frame
            max_frame: New maximum frame
        """
        # Ensure valid range
        min_frame = max(1, min_frame)
        max_frame = max(min_frame, max_frame)

        range_changed = self._min_frame != min_frame or self._max_frame != max_frame

        if range_changed:
            self._min_frame = min_frame
            self._max_frame = max_frame

            # Ensure current frame is within new range
            if self._current_frame < min_frame:
                self.set_current_frame(min_frame)
            elif self._current_frame > max_frame:
                self.set_current_frame(max_frame)

            self.frame_range_changed.emit(min_frame, max_frame)
            logger.debug(f"Frame range changed to: {min_frame}-{max_frame}")

    def clear(self) -> None:
        """Clear the frame store to default state."""
        self._current_frame = 1
        self._min_frame = 1
        self._max_frame = 1
        self._is_playing = False

        # Emit signals for reset
        self.current_frame_changed.emit(1)
        self.frame_range_changed.emit(1, 1)
        self.playback_state_changed.emit(False)

        logger.debug("Frame store cleared")

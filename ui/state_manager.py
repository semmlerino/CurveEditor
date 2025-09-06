#!/usr/bin/env python
"""
State Manager for CurveEditor.

This module provides centralized state management for the application,
tracking current file, modification status, view state, and other
application-level state information.
"""

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("state_manager")


class StateManager(QObject):
    """
    Manages application state for the CurveEditor.

    This class provides a centralized location for tracking all application
    state including file information, modification status, view parameters,
    and user interface state.
    """

    # Signals for state changes
    file_changed = Signal(str)  # Emits new file path
    modified_changed = Signal(bool)  # Emits modification status
    view_state_changed = Signal()  # Emits when view state changes
    selection_changed = Signal(list)  # Emits list of selected indices
    frame_changed = Signal(int)  # Emits new frame number

    def __init__(self, parent: QObject | None = None):
        """
        Initialize the state manager.

        Args:
            parent: Parent QObject for proper cleanup
        """
        super().__init__(parent)

        # File state
        self._current_file: str | None = None
        self._is_modified: bool = False
        self._file_format: str = "txt"

        # Data state
        self._track_data: list[tuple[float, float]] = []
        self._original_data: list[tuple[float, float]] = []
        self._has_data: bool = False

        # Selection state - Single source of truth using set for O(1) operations
        self._selected_points: set[int] = set()
        self._hover_point: int | None = None

        # View state
        self._current_frame: int = 1
        self._total_frames: int = 1
        self._zoom_level: float = 1.0
        self._pan_offset: tuple[float, float] = (0.0, 0.0)
        self._view_bounds: tuple[float, float, float, float] = (0.0, 0.0, 100.0, 100.0)  # min_x, min_y, max_x, max_y

        # Image sequence state
        self._image_directory: str | None = None
        self._image_files: list[str] = []
        self._current_image: str | None = None

        # UI state
        self._window_size: tuple[int, int] = (1200, 800)
        self._window_position: tuple[int, int] = (100, 100)
        self._splitter_sizes: list[int] = []
        self._is_fullscreen: bool = False

        # Tools state
        self._current_tool: str = "select"
        self._tool_options: dict[str, object] = {}

        # History state
        self._history_position: int = 0
        self._history_size: int = 0
        self._can_undo: bool = False
        self._can_redo: bool = False

        logger.info("StateManager initialized")

    # ==================== File State Properties ====================

    @property
    def current_file(self) -> str | None:
        """Get the current file path."""
        return self._current_file

    @current_file.setter
    def current_file(self, file_path: str | None) -> None:
        """Set the current file path."""
        if self._current_file != file_path:
            self._current_file = file_path
            self.file_changed.emit(file_path or "")
            logger.debug(f"Current file changed to: {file_path}")

    @property
    def is_modified(self) -> bool:
        """Get the modification status."""
        return self._is_modified

    @is_modified.setter
    def is_modified(self, modified: bool) -> None:
        """Set the modification status."""
        if self._is_modified != modified:
            self._is_modified = modified
            self.modified_changed.emit(modified)
            logger.debug(f"Modified state changed to: {modified}")

    @property
    def file_format(self) -> str:
        """Get the current file format."""
        return self._file_format

    @file_format.setter
    def file_format(self, format_type: str) -> None:
        """Set the current file format."""
        if self._file_format != format_type:
            self._file_format = format_type
            logger.debug(f"File format changed to: {format_type}")

    def get_window_title(self) -> str:
        """Get the appropriate window title based on current state."""
        base_title = "CurveEditor"

        if self._current_file:
            filename = Path(self._current_file).name
            title = f"{filename} - {base_title}"
            if self._is_modified:
                title = f"* {title}"
        else:
            title = f"Untitled - {base_title}"
            if self._is_modified:
                title = f"* {title}"

        return title

    # ==================== Data State Properties ====================

    @property
    def track_data(self) -> list[tuple[float, float]]:
        """Get the current track data."""
        return self._track_data.copy()

    def set_track_data(self, data: list[tuple[float, float]], mark_modified: bool = True) -> None:
        """
        Set new track data.

        Args:
            data: List of (x, y) coordinate tuples
            mark_modified: Whether to mark the document as modified
        """
        self._track_data = data.copy()
        self._has_data = len(data) > 0

        if mark_modified:
            self.is_modified = True

        logger.debug(f"Track data updated: {len(data)} points")

    def set_original_data(self, data: list[tuple[float, float]]) -> None:
        """Set the original unmodified data (for comparison)."""
        self._original_data = data.copy()
        logger.debug(f"Original data stored: {len(data)} points")

    @property
    def has_data(self) -> bool:
        """Check if track data is loaded."""
        return self._has_data

    @property
    def data_bounds(self) -> tuple[float, float, float, float]:
        """Get data bounds as (min_x, min_y, max_x, max_y)."""
        if not self._track_data:
            return (0.0, 0.0, 1.0, 1.0)

        x_coords = [point[0] for point in self._track_data]
        y_coords = [point[1] for point in self._track_data]

        return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))

    # ==================== Selection State Properties ====================

    @property
    def selected_points(self) -> list[int]:
        """Get the list of selected point indices (returns sorted list for compatibility)."""
        return sorted(self._selected_points)

    def set_selected_points(self, indices: list[int] | set[int]) -> None:
        """Set the selected point indices (accepts list or set)."""
        new_selection = set(indices) if not isinstance(indices, set) else indices
        if self._selected_points != new_selection:
            self._selected_points = new_selection
            self.selection_changed.emit(sorted(new_selection))
            logger.debug(f"Selection changed: {len(new_selection)} points selected")

    def add_to_selection(self, index: int) -> None:
        """Add a point to the selection."""
        if index not in self._selected_points:
            self._selected_points.add(index)
            self.selection_changed.emit(sorted(self._selected_points))
            logger.debug(f"Added point {index} to selection")

    def remove_from_selection(self, index: int) -> None:
        """Remove a point from the selection."""
        if index in self._selected_points:
            self._selected_points.discard(index)
            self.selection_changed.emit(sorted(self._selected_points))
            logger.debug(f"Removed point {index} from selection")

    def clear_selection(self) -> None:
        """Clear the current selection."""
        if self._selected_points:
            self._selected_points.clear()
            self.selection_changed.emit([])
            logger.debug("Selection cleared")

    @property
    def hover_point(self) -> int | None:
        """Get the currently hovered point index."""
        return self._hover_point

    @hover_point.setter
    def hover_point(self, index: int | None) -> None:
        """Set the currently hovered point index."""
        if self._hover_point != index:
            self._hover_point = index
            # No signal emission for hover to avoid excessive updates

    # ==================== View State Properties ====================

    @property
    def current_frame(self) -> int:
        """Get the current frame number."""
        return self._current_frame

    @current_frame.setter
    def current_frame(self, frame: int) -> None:
        """Set the current frame number."""
        frame = max(1, min(frame, self._total_frames))
        if self._current_frame != frame:
            self._current_frame = frame
            self.frame_changed.emit(frame)
            logger.debug(f"Current frame changed to: {frame}")

    @property
    def total_frames(self) -> int:
        """Get the total number of frames."""
        return self._total_frames

    @total_frames.setter
    def total_frames(self, count: int) -> None:
        """Set the total number of frames."""
        if self._total_frames != count:
            self._total_frames = max(1, count)
            # Ensure current frame is within bounds
            if self._current_frame > self._total_frames:
                self.current_frame = self._total_frames
            logger.debug(f"Total frames changed to: {self._total_frames}")

    @property
    def zoom_level(self) -> float:
        """Get the current zoom level."""
        return self._zoom_level

    @zoom_level.setter
    def zoom_level(self, level: float) -> None:
        """Set the current zoom level."""
        level = max(0.01, min(level, 100.0))  # Clamp between 0.01x and 100x
        if abs(self._zoom_level - level) > 0.001:
            self._zoom_level = level
            self.view_state_changed.emit()
            logger.debug(f"Zoom level changed to: {level:.3f}")

    @property
    def pan_offset(self) -> tuple[float, float]:
        """Get the current pan offset."""
        return self._pan_offset

    @pan_offset.setter
    def pan_offset(self, offset: tuple[float, float]) -> None:
        """Set the current pan offset."""
        if self._pan_offset != offset:
            self._pan_offset = offset
            self.view_state_changed.emit()
            logger.debug(f"Pan offset changed to: {offset}")

    @property
    def view_bounds(self) -> tuple[float, float, float, float]:
        """Get the current view bounds."""
        return self._view_bounds

    @view_bounds.setter
    def view_bounds(self, bounds: tuple[float, float, float, float]) -> None:
        """Set the current view bounds."""
        if self._view_bounds != bounds:
            self._view_bounds = bounds
            self.view_state_changed.emit()
            logger.debug(f"View bounds changed to: {bounds}")

    # ==================== Image Sequence Properties ====================

    @property
    def image_directory(self) -> str | None:
        """Get the current image directory."""
        return self._image_directory

    @image_directory.setter
    def image_directory(self, directory: str | None) -> None:
        """Set the current image directory."""
        if self._image_directory != directory:
            self._image_directory = directory
            logger.debug(f"Image directory changed to: {directory}")

    @property
    def image_files(self) -> list[str]:
        """Get the list of image files."""
        return self._image_files.copy()

    def set_image_files(self, files: list[str]) -> None:
        """Set the list of image files."""
        self._image_files = files.copy()
        self.total_frames = len(files) if files else 1
        logger.debug(f"Image files updated: {len(files)} files")

    @property
    def current_image(self) -> str | None:
        """Get the current image file path."""
        if self._image_files and 1 <= self._current_frame <= len(self._image_files):
            return self._image_files[self._current_frame - 1]
        return None

    # ==================== UI State Properties ====================

    @property
    def window_size(self) -> tuple[int, int]:
        """Get the window size."""
        return self._window_size

    @window_size.setter
    def window_size(self, size: tuple[int, int]) -> None:
        """Set the window size."""
        if self._window_size != size:
            self._window_size = size
            logger.debug(f"Window size changed to: {size}")

    @property
    def current_tool(self) -> str:
        """Get the current tool."""
        return self._current_tool

    @current_tool.setter
    def current_tool(self, tool: str) -> None:
        """Set the current tool."""
        if self._current_tool != tool:
            self._current_tool = tool
            logger.debug(f"Current tool changed to: {tool}")

    # ==================== History State Properties ====================

    def set_history_state(self, can_undo: bool, can_redo: bool, position: int = 0, size: int = 0) -> None:
        """Update history state information."""
        self._can_undo = can_undo
        self._can_redo = can_redo
        self._history_position = position
        self._history_size = size

    @property
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self._can_undo

    @property
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self._can_redo

    # ==================== Utility Methods ====================

    def reset_to_defaults(self) -> None:
        """Reset all state to default values."""
        # File state
        self._current_file = None
        self._is_modified = False
        self._file_format = "txt"

        # Data state
        self._track_data.clear()
        self._original_data.clear()
        self._has_data = False

        # Selection state
        self._selected_points.clear()
        self._hover_point = None

        # View state
        self._current_frame = 1
        self._total_frames = 1
        self._zoom_level = 1.0
        self._pan_offset = (0.0, 0.0)

        # Image sequence state
        self._image_directory = None
        self._image_files.clear()

        # Tools state
        self._current_tool = "select"
        self._tool_options.clear()

        # History state
        self._history_position = 0
        self._history_size = 0
        self._can_undo = False
        self._can_redo = False

        # Emit relevant signals
        self.file_changed.emit("")
        self.modified_changed.emit(False)
        self.selection_changed.emit([])
        self.frame_changed.emit(1)
        self.view_state_changed.emit()

        logger.info("State manager reset to defaults")

    def get_state_summary(self) -> dict[str, object]:
        """Get a summary of the current state for debugging."""
        return {
            "file": {
                "current_file": self._current_file,
                "is_modified": self._is_modified,
                "file_format": self._file_format,
            },
            "data": {
                "has_data": self._has_data,
                "point_count": len(self._track_data),
                "data_bounds": self.data_bounds if self._has_data else None,
            },
            "selection": {
                "selected_count": len(self._selected_points),
                "hover_point": self._hover_point,
            },
            "view": {
                "current_frame": self._current_frame,
                "total_frames": self._total_frames,
                "zoom_level": self._zoom_level,
                "pan_offset": self._pan_offset,
            },
            "images": {
                "image_directory": self._image_directory,
                "image_count": len(self._image_files),
                "current_image": self.current_image,
            },
            "history": {
                "can_undo": self._can_undo,
                "can_redo": self._can_redo,
                "position": self._history_position,
                "size": self._history_size,
            },
        }

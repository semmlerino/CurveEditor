#!/usr/bin/env python
"""
State Manager for CurveEditor.

This module provides centralized state management for the application,
tracking current file, modification status, view state, and other
application-level state information.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from core.logger_utils import get_logger

logger = get_logger("state_manager")


class PlaybackMode(Enum):
    """Playback modes for the timeline."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass
class UserPreferences:
    """User preferences for the application.

    This is a minimal implementation to support progressive disclosure
    and smart location selector features.
    """
    interface_mode: str = "simple"  # "simple" or "advanced"
    recent_directories: dict[str, list[str]] = field(default_factory=dict)  # project_name -> [directories]


class StateManager(QObject):
    """
    Manages application state for the CurveEditor.

    This class provides a centralized location for tracking all application
    state including file information, modification status, view parameters,
    and user interface state.
    """

    # Signals for state changes
    file_changed: Signal = Signal(str)  # Emits new file path
    modified_changed: Signal = Signal(bool)  # Emits modification status
    view_state_changed: Signal = Signal()  # Emits when view state changes
    selection_changed: Signal = Signal(set)  # Emits set of selected indices
    frame_changed: Signal = Signal(int)  # Emits new frame number
    total_frames_changed: Signal = Signal(int)  # Emits new total_frames value
    playback_state_changed: Signal = Signal(object)  # Emits PlaybackMode
    active_timeline_point_changed: Signal = Signal(object)  # Emits str | None - active tracking point name

    # History UI state signals (for toolbar button enable/disable)
    undo_state_changed: Signal = Signal(bool)  # Emits can_undo
    redo_state_changed: Signal = Signal(bool)  # Emits can_redo

    # Tool state signal
    tool_state_changed: Signal = Signal(str)  # Emits new tool name

    def __init__(self, parent: QObject | None = None):
        """
        Initialize the state manager.

        Args:
            parent: Parent QObject for proper cleanup
        """
        super().__init__(parent)

        # Get centralized ApplicationState (Week 5 migration)
        from stores.application_state import ApplicationState, get_application_state

        self._app_state: ApplicationState = get_application_state()

        # Forward ApplicationState signals (subscribers use Qt.QueuedConnection)
        # StateManager forwards immediately; subscribers defer with QueuedConnection
        # to prevent synchronous nested execution
        _ = self._app_state.frame_changed.connect(self.frame_changed.emit)
        _ = self._app_state.selection_changed.connect(self._on_app_state_selection_changed)

        # File state
        self._current_file: str | None = None
        self._is_modified: bool = False
        self._file_format: str = "txt"

        # Data state - DEPRECATED: Migrated to ApplicationState (Phases 1-3)
        # track_data and has_data delegate to ApplicationState
        # original_data removed (Phase 3) - use ApplicationState.set_original_data() directly

        # Selection state - MIGRATED to ApplicationState (Week 5)
        # Removed: self._selected_points (now delegated to ApplicationState per-curve selection)
        self._hover_point: int | None = None

        # Multi-point tracking state
        self._active_timeline_point: str | None = None  # Which tracking point's timeline is being viewed

        # View state
        # Removed: self._current_frame (now delegated to ApplicationState)
        # Removed: self._total_frames (now delegated to ApplicationState - Phase 2)
        self._zoom_level: float = 1.0
        self._pan_offset: tuple[float, float] = (0.0, 0.0)
        self._view_bounds: tuple[float, float, float, float] = (0.0, 0.0, 100.0, 100.0)  # min_x, min_y, max_x, max_y
        self._show_current_point_only: bool = False  # 3DEqualizer-style: show only point at current frame

        # Image sequence state
        self._image_directory: str | None = None
        # Removed: self._image_files (now delegated to ApplicationState - Phase 2)
        self._current_image: str | None = None

        # Recent directories tracking (for quick access)
        self._recent_directories: list[str] = []
        self._max_recent_directories: int = 10

        # User preferences (minimal implementation for new features)
        self._user_preferences: UserPreferences = UserPreferences()
        self._current_project_context: str | None = None

        # UI state
        self._window_size: tuple[int, int] = (1200, 800)
        self._window_position: tuple[int, int] = (100, 100)
        self._splitter_sizes: list[int] = []
        self._is_fullscreen: bool = False

        # Tools state
        self._current_tool: str = "select"
        self._tool_options: dict[str, object] = {}

        # Smoothing state
        self._smoothing_window_size: int = 5
        self._smoothing_filter_type: str = "moving_average"

        # History state
        self._history_position: int = 0
        self._history_size: int = 0
        self._can_undo: bool = False
        self._can_redo: bool = False

        # Playback state
        self._playback_mode: PlaybackMode = PlaybackMode.STOPPED

        # Batch update state
        self._batch_mode: bool = False
        self._pending_signals: list[tuple[Signal, object]] = []

        logger.info("StateManager initialized")

    # ==================== Signal Forwarding Adapters ====================

    def _on_app_state_selection_changed(self, indices: set[int], curve_name: str) -> None:
        """Adapter to forward ApplicationState selection_changed signal.

        ApplicationState emits (indices, curve_name), StateManager emits just indices.
        Only forward if selection is for the active timeline point (or fallback curve).

        Phase 4: Added None check for curve name.

        Args:
            indices: Selected point indices
            curve_name: Curve name the selection belongs to
        """
        # Forward if it matches the curve we're tracking
        expected_curve = self._get_curve_name_for_selection()
        if expected_curve is None:
            logger.debug("No active curve for selection - ignoring signal")
            return

        if curve_name == expected_curve:
            self.selection_changed.emit(indices)

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

    # ==================== Selection State Properties ====================

    def _get_curve_name_for_selection(self) -> str | None:
        """Determine which curve name to use for selection operations.

        Phase 4: Removed __default__ fallback. Returns None if no active curve.

        Returns:
            Curve name for selection, or None if no curve is active
        """
        if self._active_timeline_point:
            return self._active_timeline_point
        if self._app_state.active_curve:
            return self._app_state.active_curve
        # No active curve - caller should handle None
        return None

    @property
    def selected_points(self) -> list[int]:
        """Get the list of selected point indices (delegated to ApplicationState)."""
        curve_name = self._get_curve_name_for_selection()
        if not curve_name:
            logger.warning("No active curve for selection - returning empty selection")
            return []
        return sorted(self._app_state.get_selection(curve_name))

    def set_selected_points(self, indices: list[int] | set[int]) -> None:
        """Set the selected point indices (delegated to ApplicationState)."""
        curve_name = self._get_curve_name_for_selection()
        if not curve_name:
            logger.warning("No active curve for selection - ignoring set_selected_points")
            return
        new_selection = set(indices) if not isinstance(indices, set) else indices
        self._app_state.set_selection(curve_name, new_selection)
        # Signal already forwarded in __init__
        logger.debug(f"Selection changed for '{curve_name}': {len(new_selection)} points selected")

    def add_to_selection(self, index: int) -> None:
        """Add a point to the selection (delegated to ApplicationState)."""
        curve_name = self._get_curve_name_for_selection()
        if not curve_name:
            logger.warning("No active curve for selection - ignoring add_to_selection")
            return
        self._app_state.add_to_selection(curve_name, index)
        # Signal already forwarded in __init__
        logger.debug(f"Added point {index} to selection in '{curve_name}'")

    @property
    def active_timeline_point(self) -> str | None:
        """Get the active timeline point name (which tracking point's timeline is displayed)."""
        return self._active_timeline_point

    @active_timeline_point.setter
    def active_timeline_point(self, point_name: str | None) -> None:
        """Set the active timeline point name (which tracking point's timeline to display)."""
        if self._active_timeline_point != point_name:
            self._active_timeline_point = point_name
            self._emit_signal(self.active_timeline_point_changed, point_name)  # pyright: ignore[reportArgumentType]
            logger.debug(f"Active timeline point changed to: {point_name}")

    def remove_from_selection(self, index: int) -> None:
        """Remove a point from the selection (delegated to ApplicationState)."""
        curve_name = self._get_curve_name_for_selection()
        if not curve_name:
            logger.warning("No active curve for selection - ignoring remove_from_selection")
            return
        self._app_state.remove_from_selection(curve_name, index)
        # Signal already forwarded in __init__
        logger.debug(f"Removed point {index} from selection in '{curve_name}'")

    def clear_selection(self) -> None:
        """Clear the current selection (delegated to ApplicationState)."""
        curve_name = self._get_curve_name_for_selection()
        if not curve_name:
            logger.warning("No active curve for selection - ignoring clear_selection")
            return
        self._app_state.clear_selection(curve_name)
        # Signal already forwarded in __init__
        logger.debug(f"Selection cleared for '{curve_name}'")

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

    # ==================== Frame State Properties ====================

    @property
    def current_frame(self) -> int:
        """Get the current frame number (delegated to ApplicationState)."""
        return self._app_state.current_frame

    @current_frame.setter
    def current_frame(self, frame: int) -> None:
        """Set the current frame number with clamping to [1, total_frames]."""
        total_frames = self._app_state.get_total_frames()
        clamped_frame = max(1, min(frame, total_frames))
        self._app_state.set_frame(clamped_frame)
        logger.debug(f"Frame set (clamped): {frame} -> {clamped_frame}")

    # ==================== View State Properties ====================

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

    @property
    def show_current_point_only(self) -> bool:
        """Get the show current point only mode (3DEqualizer-style)."""
        return self._show_current_point_only

    @show_current_point_only.setter
    def show_current_point_only(self, value: bool) -> None:
        """Set the show current point only mode."""
        if self._show_current_point_only != value:
            self._show_current_point_only = value
            self.view_state_changed.emit()
            logger.debug(f"Show current point only mode: {value}")

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
    def recent_directories(self) -> list[str]:
        """Get list of recent directories (most recent first)."""
        return self._recent_directories.copy()

    def add_recent_directory(self, directory: str) -> None:
        """Add directory to recent list, moving to top if already exists.

        Args:
            directory: Directory path to add to recent list
        """
        directory = str(Path(directory).resolve())  # Normalize path

        # Remove if already exists (will re-add at top)
        if directory in self._recent_directories:
            self._recent_directories.remove(directory)

        # Add to beginning
        self._recent_directories.insert(0, directory)

        # Trim to max size
        self._recent_directories = self._recent_directories[: self._max_recent_directories]

        logger.debug(f"Added recent directory: {directory}")

    def set_recent_directories(self, directories: list[str]) -> None:
        """Set recent directories list (for session restoration).

        Args:
            directories: List of directory paths to set
        """
        self._recent_directories = directories[: self._max_recent_directories]
        logger.debug(f"Set recent directories: {len(self._recent_directories)} entries")

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
        """Set the current tool and emit signal if changed.

        Signals:
            Emits tool_state_changed if tool value changes.
        """
        if self._current_tool != tool:
            self._current_tool = tool
            self._emit_signal(self.tool_state_changed, tool)  # pyright: ignore[reportArgumentType]
            logger.debug(f"Current tool changed to: {tool}")

    # ==================== History State Properties ====================

    def set_history_state(self, can_undo: bool, can_redo: bool, position: int = 0, size: int = 0) -> None:
        """Update history state information.

        Args:
            can_undo: Whether undo is available
            can_redo: Whether redo is available
            position: Current position in history (optional)
            size: Total history size (optional)

        Signals:
            Emits undo_state_changed if can_undo value changes.
            Emits redo_state_changed if can_redo value changes.
        """
        self._history_position = position
        self._history_size = size

        # Emit signals only if values changed (prevent unnecessary UI updates)
        if self._can_undo != can_undo:
            self._can_undo = can_undo
            self._emit_signal(self.undo_state_changed, can_undo)  # pyright: ignore[reportArgumentType]

        if self._can_redo != can_redo:
            self._can_redo = can_redo
            self._emit_signal(self.redo_state_changed, can_redo)  # pyright: ignore[reportArgumentType]

    @property
    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self._can_undo

    @property
    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self._can_redo

    # ==================== Smoothing State Properties ====================

    @property
    def smoothing_window_size(self) -> int:
        """Get the smoothing window size."""
        return self._smoothing_window_size

    @smoothing_window_size.setter
    def smoothing_window_size(self, size: int) -> None:
        """Set the smoothing window size."""
        # Clamp to valid range
        self._smoothing_window_size = max(3, min(15, size))
        logger.debug(f"Smoothing window size set to: {self._smoothing_window_size}")

    @property
    def smoothing_filter_type(self) -> str:
        """Get the smoothing filter type."""
        return self._smoothing_filter_type

    @smoothing_filter_type.setter
    def smoothing_filter_type(self, filter_type: str) -> None:
        """Set the smoothing filter type."""
        valid_types = ["moving_average", "median", "butterworth"]
        if filter_type in valid_types:
            self._smoothing_filter_type = filter_type
            logger.debug(f"Smoothing filter type set to: {self._smoothing_filter_type}")
        else:
            logger.warning(f"Invalid filter type: {filter_type}. Keeping current: {self._smoothing_filter_type}")

    # ==================== Playback State Properties ====================

    @property
    def playback_mode(self) -> PlaybackMode:
        """Get the current playback mode."""
        return self._playback_mode

    @playback_mode.setter
    def playback_mode(self, mode: PlaybackMode) -> None:
        """Set the current playback mode."""
        if self._playback_mode != mode:
            self._playback_mode = mode
            self._emit_signal(self.playback_state_changed, mode)  # pyright: ignore[reportArgumentType]
            logger.debug(f"Playback mode changed to: {mode.value}")

    # ==================== Batch Update Support ====================

    @contextmanager
    def batch_update(self):
        """
        Batch multiple state changes into single signal emissions.

        This prevents signal storms during complex operations by deferring
        signal emission until the context exits.

        Example:
            with state_manager.batch_update():
                get_application_state().current_frame = 10
                state_manager.set_selected_points([1, 2, 3])
                # Signals are emitted here when context exits
        """
        self._batch_mode = True
        self._pending_signals = []
        # Also enable ApplicationState batch mode for delegated operations
        with self._app_state.batch_updates():
            try:
                yield
            finally:
                # ApplicationState batch ends automatically, then emit StateManager's own signals
                self._batch_mode = False
                for signal, value in self._pending_signals:
                    signal.emit(value)  # pyright: ignore[reportAttributeAccessIssue]
                self._pending_signals.clear()

    def _emit_signal(self, signal: Signal, value: object) -> None:
        """
        Emit a signal, potentially batching if in batch mode.

        Args:
            signal: The signal to emit
            value: The value to emit with the signal
        """
        if self._batch_mode:
            # In batch mode, queue the signal
            self._pending_signals.append((signal, value))
        else:
            # Normal mode, emit immediately
            signal.emit(value)  # pyright: ignore[reportAttributeAccessIssue]

    # ==================== User Preferences Methods ====================

    def get_user_preferences(self) -> UserPreferences:
        """Get the current user preferences.

        Returns:
            UserPreferences object with current settings
        """
        return self._user_preferences

    def save_user_preferences(self, preferences: UserPreferences) -> None:
        """Save user preferences.

        Args:
            preferences: UserPreferences object to save

        Note:
            This is a minimal stub implementation. Preferences are stored
            in memory but not persisted to disk yet.
        """
        self._user_preferences = preferences
        logger.debug(f"User preferences saved: interface_mode={preferences.interface_mode}")

    def get_recent_directories_for_project(self) -> list[str]:
        """Get recent directories for the current project context.

        Returns:
            List of recent directory paths for current project
        """
        if self._current_project_context:
            return self._user_preferences.recent_directories.get(self._current_project_context, [])
        # Fallback to global recent directories if no project context
        return self._recent_directories

    def add_recent_directory_for_project(self, directory: str) -> None:
        """Add directory to recent list for current project context.

        Args:
            directory: Directory path to add
        """
        directory = str(Path(directory).resolve())

        if self._current_project_context:
            # Add to project-specific recent directories
            if self._current_project_context not in self._user_preferences.recent_directories:
                self._user_preferences.recent_directories[self._current_project_context] = []

            recent_list = self._user_preferences.recent_directories[self._current_project_context]

            # Remove if already exists (will re-add at top)
            if directory in recent_list:
                recent_list.remove(directory)

            # Add to beginning
            recent_list.insert(0, directory)

            # Trim to max size
            self._user_preferences.recent_directories[self._current_project_context] = \
                recent_list[:self._max_recent_directories]

            logger.debug(f"Added recent directory for project '{self._current_project_context}': {directory}")
        else:
            # Fallback to global recent directories
            self.add_recent_directory(directory)

    def set_project_context(self, project_name: str | None) -> None:
        """Set the current project context.

        Args:
            project_name: Name of the current project, or None to clear
        """
        self._current_project_context = project_name
        logger.debug(f"Project context set to: {project_name}")

    # ==================== Utility Methods ====================

    def reset_to_defaults(self) -> None:
        """Reset StateManager UI state to default values.

        NOTE: This does NOT reset ApplicationState data (curves, images, frame).
        ApplicationState is the single source of truth for data and must be reset separately.
        StateManager only owns UI preferences and view state.
        """
        # File state
        self._current_file = None
        self._is_modified = False
        self._file_format = "txt"

        # Selection state (UI concern only - clear hover and local selection state)
        self._hover_point = None
        # Clear selection for active curve (if any) - this will emit signal via forwarding
        curve_name = self._get_curve_name_for_selection()
        if curve_name:
            self._app_state.clear_selection(curve_name)
            # Signal already forwarded from ApplicationState, don't emit again
        else:
            # No active curve, emit empty selection directly
            self.selection_changed.emit(set())

        # View state (UI preferences only - zoom, pan, view bounds)
        # NOTE: current_frame is NOT reset - that's ApplicationState data
        self._zoom_level = 1.0
        self._pan_offset = (0.0, 0.0)

        # Image directory (UI preference, not the image files themselves)
        self._image_directory = None

        # Recent directories (UI preference)
        self._recent_directories.clear()

        # Tools state (use setter to emit signal)
        self.current_tool = "select"
        self._tool_options.clear()

        # Smoothing state (UI preference)
        self._smoothing_window_size = 5
        self._smoothing_filter_type = "moving_average"

        # History state (use method to emit signals)
        self.set_history_state(can_undo=False, can_redo=False, position=0, size=0)

        # Reset playback mode (UI state)
        self._playback_mode = PlaybackMode.STOPPED

        # Emit relevant signals for changed UI state
        # Note: tool_state_changed, undo_state_changed, redo_state_changed emitted above via setters
        self.file_changed.emit("")
        self.modified_changed.emit(False)
        self.view_state_changed.emit()
        self.playback_state_changed.emit(PlaybackMode.STOPPED)

        logger.info("StateManager UI state reset to defaults (ApplicationState data preserved)")

    def get_state_summary(self) -> dict[str, object]:
        """Get a summary of the current state for debugging (Phase 3.3: Updated to use ApplicationState)."""
        # Get data from ApplicationState for active curve - use active_curve_data property
        has_data = False
        point_count = 0
        data_bounds = None

        if (cd := self._app_state.active_curve_data) is not None:
            _curve_name, curve_data = cd
            if curve_data:
                has_data = True
                point_count = len(curve_data)
                # Calculate bounds
                x_coords = [float(point[1]) for point in curve_data]
                y_coords = [float(point[2]) for point in curve_data]
                data_bounds = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))

        # Get image info from ApplicationState
        image_files = self._app_state.get_image_files()
        current_frame = self._app_state.current_frame
        current_image = None
        if image_files and 1 <= current_frame <= len(image_files):
            current_image = image_files[current_frame - 1]

        return {
            "file": {
                "current_file": self._current_file,
                "is_modified": self._is_modified,
                "file_format": self._file_format,
            },
            "data": {
                "has_data": has_data,
                "point_count": point_count,
                "data_bounds": data_bounds,
            },
            "selection": {
                "selected_count": len(self.selected_points),  # Uses ApplicationState via delegated property
                "hover_point": self._hover_point,
            },
            "view": {
                "current_frame": current_frame,
                "total_frames": self._app_state.get_total_frames(),
                "zoom_level": self._zoom_level,
                "pan_offset": self._pan_offset,
            },
            "images": {
                "image_directory": self._image_directory,
                "image_count": len(image_files),
                "current_image": current_image,
            },
            "history": {
                "can_undo": self._can_undo,
                "can_redo": self._can_redo,
                "position": self._history_position,
                "size": self._history_size,
            },
        }

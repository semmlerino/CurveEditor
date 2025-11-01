#!/usr/bin/env python
"""
ApplicationState - Centralized State Management for CurveEditor

Single source of truth for all application state:
- Multi-curve data (dict[str, CurveDataList])
- Per-curve selection (dict[str, set[int]])
- Active curve (str)
- Current frame (int)
- Curve metadata (visibility, color, etc.)

Key Design Principles:
- Immutable external interface (returns copies)
- Qt Signal-based reactivity (no polling needed)
- Batch operations (prevent signal storms)
- Main thread only (enforced by runtime assertions)

Thread Safety:
- All methods MUST be called from main thread
- Batch operations are main-thread-only (no locking needed)
- Worker threads should emit signals, handlers then update state
- _assert_main_thread() validates correct thread usage

Usage:
    from stores.application_state import get_application_state

    state = get_application_state()
    state.set_curve_data("pp56_TM_138G", curve_data)
    data = state.get_application_state("pp56_TM_138G")

Batching Multiple Updates:
    When changing multiple related fields, use batch mode to emit single signal:

    # ❌ Bad: Multiple signals, multiple repaints
    state.set_show_all_curves(False)
    state.set_selected_curves({"Track1", "Track2"})

    # ✅ Good: One signal, one repaint (context manager - recommended)
    with state.batch_updates():
        state.set_show_all_curves(False)
        state.set_selected_curves({"Track1", "Track2"})

    # ✅ Good: One signal, one repaint (context manager - recommended)
    with state.batch_updates():
        state.set_show_all_curves(False)
        state.set_selected_curves({"Track1", "Track2"})

    Batch mode is especially important for coordinated selection state changes
    where display_mode transitions require updating both show_all and selected_curves.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, TypeVar

from PySide6.QtCore import QCoreApplication, QObject, QThread, Signal, SignalInstance

from core.display_mode import DisplayMode
from core.models import CurvePoint, PointStatus

if TYPE_CHECKING:
    from core.type_aliases import CurveDataInput, CurveDataList

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ApplicationState(QObject):
    """
    Centralized application state container for multi-curve editing.

    This is the ONLY location that stores application data.
    All components read from here via getters and subscribe
    to signals for updates. No component maintains local copies.

    Protocol Compatibility (Interface Segregation Principle):
        ApplicationState structurally implements these protocols from protocols/state.py:
        - FrameProvider: Current frame access (current_frame property)
        - CurveDataProvider: Curve data read (get_curve_data, get_all_curve_names, active_curve)
        - CurveDataModifier: Curve data write (set_curve_data, delete_curve)
        - SelectionProvider: Selection read (get_selection, selection_changed signal)
        - SelectionModifier: Selection write (set_selection, clear_selection)
        - ImageSequenceProvider: Image info (get_image_files, get_image_directory, get_total_frames)

        Clients can depend on minimal protocols instead of full ApplicationState.
        See protocols/state.py for usage examples and testing patterns.

    Thread Safety Contract:
    - All data access methods MUST be called from main thread only
    - _assert_main_thread() enforces this at runtime for all modifications
    - Batch operations are main-thread-only (no locking needed)
    - Signal emission is thread-safe (Qt handles cross-thread automatically)
    - DO NOT access _private attributes directly (no synchronization guarantee)

    Correct Usage:
        # ✅ Call from main thread slot
        @Slot()
        def on_data_loaded(self, data):
            state = get_application_state()
            state.set_curve_data("curve1", data)

        # ❌ Wrong: Direct call from worker thread
        def worker_thread():
            state = get_application_state()
            state.set_curve_data("curve1", data)  # Will raise AssertionError!
    """

    # State change signals
    state_changed: Signal = Signal()  # Emitted on any state change
    curves_changed: Signal = Signal(dict)  # curves_data changed: dict[str, CurveDataList]
    selection_changed: Signal = Signal(set, str)  # Point-level (frame indices)
    active_curve_changed: Signal = Signal(object)  # active_curve_name: str | None (matches StateManager pattern)
    frame_changed: Signal = Signal(int)  # current_frame: int
    curve_visibility_changed: Signal = Signal(str, bool)  # (curve_name, visible)

    # NEW: Curve-level selection state changed (selected_curves, show_all)
    selection_state_changed: Signal = Signal(set, bool)

    # Image sequence signal (total_frames is derived, no separate signal needed)
    image_sequence_changed: Signal = Signal()

    def __init__(self) -> None:
        super().__init__()

        # Core state (private - access via getters only)
        self._curves_data: dict[str, CurveDataList] = {}
        self._curve_metadata: dict[str, dict[str, Any]] = {}
        self._active_curve: str | None = None
        self._selection: dict[str, set[int]] = {}  # Point-level selection (indices within curves)
        self._current_frame: int = 1

        # NEW: Curve-level selection state (which trajectories to display)
        # Note: This is DISTINCT from _selection above:
        #   - _selected_curves: which curve trajectories to show (curve names)
        #   - _selection: which points within active curve are selected (frame indices)
        self._selected_curves: set[str] = set()
        self._show_all_curves: bool = False

        # Batch operation support (no QMutex needed - main-thread-only)
        self._batching: bool = False
        self._emitting: bool = False  # Prevent reentrancy during signal emission
        self._pending_signals: dict[SignalInstance, tuple[Any, ...]] = {}

        # Image sequence state
        self._image_files: list[str] = []
        self._image_directory: str | None = None
        self._total_frames: int = 1

        # Original data for undo/comparison
        self._original_data: dict[str, CurveDataList] = {}

        logger.info("ApplicationState initialized")

    def _assert_main_thread(self) -> None:
        """
        Verify we're on the main thread.

        ApplicationState is not thread-safe and must only be accessed from
        the main thread. This assertion catches threading violations early.

        Raises:
            AssertionError: If called from non-main thread
        """
        app = QCoreApplication.instance()
        if app is not None:  # Only check if QApplication exists
            current_thread = QThread.currentThread()
            main_thread = app.thread()
            assert current_thread == main_thread, (
                f"ApplicationState must be accessed from main thread only. "
                f"Current thread: {current_thread}, Main thread: {main_thread}"
            )

    # ==================== Curve Data Operations ====================

    def get_curve_data(self, curve_name: str | None = None) -> CurveDataList:
        """
        Get curve data for specified curve (or active curve if None).

        Returns a COPY for safety. Modifying returned list won't affect state.
        Use set_curve_data() or update_point() to modify state.

        Args:
            curve_name: Curve to retrieve, or None for active curve

        Returns:
            Copy of curve data

        Raises:
            ValueError: If curve_name is None and no active curve is set
        """
        self._assert_main_thread()  # Prevent read tearing from wrong thread
        if curve_name is None:
            curve_name = self._active_curve
            if curve_name is None:
                raise ValueError(
                    "No active curve set. Call set_active_curve() first or provide explicit curve_name parameter."
                )
        if curve_name not in self._curves_data:
            return []
        return self._curves_data[curve_name].copy()

    def get_all_curves(self) -> dict[str, CurveDataList]:
        """
        Get all curves data as dictionary.

        Returns a COPY for safety. Modifying returned dict won't affect state.

        Returns:
            Dict mapping curve names to curve data (copies)
        """
        self._assert_main_thread()  # Prevent read tearing from wrong thread
        return {name: data.copy() for name, data in self._curves_data.items()}

    def set_curve_data(self, curve_name: str, data: CurveDataInput, metadata: dict[str, Any] | None = None) -> None:
        """
        Replace entire curve data.

        Creates internal copy for safety. Original data not retained.

        Args:
            curve_name: Name of curve to set
            data: New curve data (accepts any sequence of point data)
            metadata: Optional metadata (visibility, color, etc.)

        Raises:
            TypeError: If data is not a valid sequence (e.g., string or dict)
            ValueError: If curve_name is None or empty
        """
        self._assert_main_thread()
        # Validate curve_name
        if not curve_name:
            raise ValueError("curve_name cannot be None or empty")
        # Validate data type - reject strings and dicts which are iterable but invalid
        if isinstance(data, (str, dict)):
            raise TypeError(f"data must be a sequence of point data, not {type(data).__name__}")
        # Store copy (immutability) - convert Sequence to list
        self._curves_data[curve_name] = list(data)

        # Update metadata
        if metadata is not None:
            if curve_name not in self._curve_metadata:
                self._curve_metadata[curve_name] = {}
            self._curve_metadata[curve_name].update(metadata)
        elif curve_name not in self._curve_metadata:
            # Initialize default metadata
            self._curve_metadata[curve_name] = {"visible": True}

        logger.info(f"[APP_STATE] Emitting curves_changed for '{curve_name}' with {len(data)} points")
        self._emit(self.curves_changed, (self._curves_data.copy(),))

        logger.debug(f"Set curve data for '{curve_name}': {len(data)} points")

    def update_point(self, curve_name: str, index: int, point: CurvePoint) -> None:
        """
        Update single point in curve.

        More efficient than set_curve_data() for single point changes.

        Args:
            curve_name: Curve containing point
            index: Point index to update
            point: New point data
        """
        self._assert_main_thread()
        if curve_name not in self._curves_data:
            logger.warning(f"Cannot update point: curve '{curve_name}' not found")
            return

        curve = self._curves_data[curve_name]
        if not (0 <= index < len(curve)):
            logger.warning(f"Cannot update point: index {index} out of range (0-{len(curve)-1})")
            return

        # Create new list (immutability)
        new_curve = curve.copy()
        new_curve[index] = point.to_tuple4()
        self._curves_data[curve_name] = new_curve

        self._emit(self.curves_changed, (self._curves_data.copy(),))

        logger.debug(f"Updated point {index} in curve '{curve_name}'")

    def add_point(self, curve_name: str, point: CurvePoint) -> int:
        """
        Add point to end of curve.

        Args:
            curve_name: Curve to add point to
            point: Point to add

        Returns:
            Index of added point
        """
        self._assert_main_thread()

        # Get or create curve
        curve = self._curves_data.get(curve_name, [])

        # Create new list with appended point (immutability)
        new_curve = curve.copy()
        new_curve.append(point.to_tuple4())
        self._curves_data[curve_name] = new_curve

        # Initialize metadata if new curve
        if curve_name not in self._curve_metadata:
            self._curve_metadata[curve_name] = {"visible": True}

        self._emit(self.curves_changed, (self._curves_data.copy(),))

        index = len(new_curve) - 1
        logger.debug(f"Added point to curve '{curve_name}' at index {index}")
        return index

    def remove_point(self, curve_name: str, index: int) -> bool:
        """
        Remove point from curve.

        Updates selection indices by shifting down indices after removed point.

        Args:
            curve_name: Curve containing point
            index: Point index to remove

        Returns:
            True if removed, False if invalid
        """
        self._assert_main_thread()

        if curve_name not in self._curves_data:
            logger.warning(f"Cannot remove point: curve '{curve_name}' not found")
            return False

        curve = self._curves_data[curve_name]
        if not (0 <= index < len(curve)):
            logger.warning(f"Cannot remove point: index {index} out of range (0-{len(curve)-1})")
            return False

        # Create new list without the point (immutability)
        new_curve = curve.copy()
        del new_curve[index]
        self._curves_data[curve_name] = new_curve

        # Update selection: remove index and shift down indices after it
        if curve_name in self._selection:
            old_selection = self._selection[curve_name]
            new_selection = {i - 1 if i > index else i for i in old_selection if i != index}
            if new_selection != old_selection:
                self._selection[curve_name] = new_selection
                self._emit(self.selection_changed, (new_selection.copy(), curve_name))

        self._emit(self.curves_changed, (self._curves_data.copy(),))

        logger.debug(f"Removed point {index} from curve '{curve_name}'")
        return True

    def set_point_status(self, curve_name: str, index: int, status: str | PointStatus) -> bool:
        """
        Change point status.

        Args:
            curve_name: Curve containing point
            index: Point index to update
            status: New status (string or PointStatus enum)

        Returns:
            True if changed, False if invalid
        """
        self._assert_main_thread()

        if curve_name not in self._curves_data:
            logger.warning(f"Cannot set point status: curve '{curve_name}' not found")
            return False

        curve = self._curves_data[curve_name]
        if not (0 <= index < len(curve)):
            logger.warning(f"Cannot set point status: index {index} out of range (0-{len(curve)-1})")
            return False

        # Convert status to PointStatus enum
        status_enum = PointStatus.from_legacy(status) if isinstance(status, str) else status

        # Get current point and create new point with updated status
        current_point_tuple = curve[index]
        current_point = CurvePoint.from_tuple(current_point_tuple)
        new_point = current_point.with_status(status_enum)

        # Create new list with updated point (immutability)
        new_curve = curve.copy()
        new_curve[index] = new_point.to_tuple4()
        self._curves_data[curve_name] = new_curve

        self._emit(self.curves_changed, (self._curves_data.copy(),))

        logger.debug(f"Set point {index} status to '{status_enum.value}' in curve '{curve_name}'")
        return True

    def select_all(self, curve_name: str | None = None) -> None:
        """
        Select all points in curve.

        Args:
            curve_name: Curve to select all points in (defaults to active curve)
        """
        self._assert_main_thread()

        # Default to active curve
        if curve_name is None:
            curve_name = self._active_curve

        if curve_name is None:
            logger.warning("Cannot select all: no curve specified and no active curve")
            return

        if curve_name not in self._curves_data:
            logger.warning(f"Cannot select all: curve '{curve_name}' not found")
            return

        # Select all indices
        curve = self._curves_data[curve_name]
        all_indices = set(range(len(curve)))
        self.set_selection(curve_name, all_indices)

        logger.debug(f"Selected all {len(all_indices)} points in curve '{curve_name}'")

    def select_range(self, curve_name: str, start: int, end: int) -> None:
        """
        Select range of points (inclusive).

        Clamps indices to valid range.

        Args:
            curve_name: Curve to select points in
            start: Start index (inclusive)
            end: End index (inclusive)
        """
        self._assert_main_thread()

        if curve_name not in self._curves_data:
            logger.warning(f"Cannot select range: curve '{curve_name}' not found")
            return

        curve = self._curves_data[curve_name]
        curve_len = len(curve)

        if curve_len == 0:
            logger.warning(f"Cannot select range: curve '{curve_name}' is empty")
            return

        # Clamp to valid range
        start = max(0, min(start, curve_len - 1))
        end = max(0, min(end, curve_len - 1))

        # Ensure start <= end
        if start > end:
            start, end = end, start

        # Select range
        range_indices = set(range(start, end + 1))
        self.set_selection(curve_name, range_indices)

        logger.debug(f"Selected points {start}-{end} in curve '{curve_name}'")

    def delete_curve(self, curve_name: str) -> None:
        """
        Remove curve from state.

        Also removes associated metadata, selection, and curve-level selection.

        Args:
            curve_name: Curve to delete
        """
        self._assert_main_thread()
        if curve_name in self._curves_data:
            del self._curves_data[curve_name]
        if curve_name in self._curve_metadata:
            del self._curve_metadata[curve_name]
        if curve_name in self._selection:
            del self._selection[curve_name]

        # Remove from curve-level selection if present
        selection_modified = False
        if curve_name in self._selected_curves:
            self._selected_curves.discard(curve_name)
            selection_modified = True

        # If active curve was deleted, clear it
        if self._active_curve == curve_name:
            self._active_curve = None
            self._emit(self.active_curve_changed, (None,))  # Pass None as-is

        # Emit selection state changed if curve was in selection
        if selection_modified:
            self._emit(self.selection_state_changed, (self._selected_curves.copy(), self._show_all_curves))

        self._emit(self.curves_changed, (self._curves_data.copy(),))

        logger.info(f"Deleted curve '{curve_name}'")

    def get_all_curve_names(self) -> list[str]:
        """Get list of all curve names."""
        return list(self._curves_data.keys())

    # ==================== Selection Operations ====================

    def get_selection(self, curve_name: str | None = None) -> set[int]:
        """
        Get selected point indices for curve.

        Returns a COPY for safety.

        Args:
            curve_name: Curve to get selection for, or None for active curve

        Returns:
            Copy of selected indices set
        """
        self._assert_main_thread()  # Prevent inconsistent reads from wrong thread
        if curve_name is None:
            curve_name = self._active_curve
        if curve_name is None or curve_name not in self._selection:
            return set()
        return self._selection[curve_name].copy()

    def set_selection(self, curve_name: str, indices: set[int]) -> None:
        """
        Replace selection for curve.

        Args:
            curve_name: Curve to set selection for
            indices: New selection (copied internally)
        """
        self._assert_main_thread()
        new_selection = indices.copy()
        old_selection = self._selection.get(curve_name, set())

        # Only update and emit if selection actually changed
        if new_selection != old_selection:
            self._selection[curve_name] = new_selection
            self._emit(self.selection_changed, (new_selection.copy(), curve_name))
            logger.debug(f"Set selection for '{curve_name}': {len(indices)} points")
        else:
            logger.debug(f"Selection for '{curve_name}' unchanged, no signal emitted")

    def add_to_selection(self, curve_name: str, index: int) -> None:
        """
        Add single point to selection.

        Args:
            curve_name: Curve containing point
            index: Point index to select
        """
        self._assert_main_thread()
        if curve_name not in self._selection:
            self._selection[curve_name] = set()

        # Only add and emit if not already in selection
        if index not in self._selection[curve_name]:
            self._selection[curve_name].add(index)
            self._emit(self.selection_changed, (self._selection[curve_name].copy(), curve_name))
            logger.debug(f"Added point {index} to selection in '{curve_name}'")
        else:
            logger.debug(f"Point {index} already in selection for '{curve_name}', no signal emitted")

    def remove_from_selection(self, curve_name: str, index: int) -> None:
        """
        Remove single point from selection.

        Args:
            curve_name: Curve containing point
            index: Point index to deselect
        """
        self._assert_main_thread()
        if curve_name in self._selection and index in self._selection[curve_name]:
            # Only remove and emit if index was actually in selection
            self._selection[curve_name].discard(index)
            self._emit(self.selection_changed, (self._selection[curve_name].copy(), curve_name))
            logger.debug(f"Removed point {index} from selection in '{curve_name}'")
        else:
            logger.debug(f"Point {index} not in selection for '{curve_name}', no signal emitted")

    def clear_selection(self, curve_name: str | None = None) -> None:
        """
        Clear selection for curve(s).

        Args:
            curve_name: Curve to clear, or None to clear all curves
        """
        self._assert_main_thread()
        if curve_name is None:
            # Clear all - only emit if there were selections
            if self._selection:
                self._selection.clear()
                self._emit(self.selection_changed, (set(), ""))
                logger.debug("Cleared all selections")
            else:
                logger.debug("No selections to clear, no signal emitted")
        else:
            # Clear specific curve - only emit if it had a non-empty selection
            if self._selection.get(curve_name):
                self._selection[curve_name] = set()
                self._emit(self.selection_changed, (set(), curve_name))
                logger.debug(f"Cleared selection for '{curve_name}'")
            else:
                logger.debug(f"No selection to clear for '{curve_name}', no signal emitted")

    # ==================== Active Curve ====================

    @property
    def active_curve(self) -> str | None:
        """Get name of active curve (currently being edited)."""
        return self._active_curve

    def set_active_curve(self, curve_name: str | None) -> None:
        """
        Set active curve.

        Active curve is the one currently being edited and displayed.

        Args:
            curve_name: Curve to make active, or None to clear
        """
        self._assert_main_thread()
        if self._active_curve != curve_name:
            old_curve = self._active_curve
            self._active_curve = curve_name
            self._emit(self.active_curve_changed, (curve_name,))

            logger.info(f"Active curve changed: '{old_curve}' -> '{curve_name}'")

    # ==================== Frame Navigation ====================

    @property
    def current_frame(self) -> int:
        """Get current frame number."""
        return self._current_frame

    def set_frame(self, frame: int) -> None:
        """
        Set current frame.

        Args:
            frame: Frame number (1-based)
        """
        self._assert_main_thread()
        if frame < 1:
            logger.warning(f"Invalid frame {frame}, using 1")
            frame = 1

        if self._current_frame != frame:
            self._current_frame = frame
            self._emit(self.frame_changed, (frame,))

    # ==================== Image Sequence Methods ====================

    def set_image_files(self, files: list[str], directory: str | None = None) -> None:
        """
        Set the image file sequence.

        Args:
            files: List of image file paths
            directory: Optional base directory (if None, keeps current)

        Raises:
            ValueError: If files list is too large
        """
        self._assert_main_thread()

        # Validation
        max_files = 10_000
        if len(files) > max_files:
            raise ValueError(f"Too many files: {len(files)} (max: {max_files})")

        # Store copy (immutability) - consistent with set_curve_data() pattern
        old_files = self._image_files
        old_dir = self._image_directory
        self._image_files = list(files)  # Defensive copy

        if directory is not None:
            self._image_directory = directory

        # Update derived state (internal only - no signal needed)
        self._total_frames = len(files) if files else 1

        # Emit single signal if image sequence changed
        if old_files != self._image_files or (directory is not None and old_dir != directory):
            self._emit(self.image_sequence_changed, ())

        logger.debug(f"Image files updated: {len(files)} files, total_frames={self._total_frames}")

    def get_image_files(self) -> list[str]:
        """Get the image file sequence (defensive copy for safety)."""
        self._assert_main_thread()
        return self._image_files.copy()

    def get_image_directory(self) -> str | None:
        """Get the image base directory."""
        self._assert_main_thread()
        return self._image_directory

    def set_image_directory(self, directory: str | None) -> None:
        """Set the image base directory (emits signal if changed)."""
        self._assert_main_thread()

        if self._image_directory != directory:
            self._image_directory = directory
            self._emit(self.image_sequence_changed, ())
            logger.debug(f"Image directory changed to: {directory}")

    def get_total_frames(self) -> int:
        """
        Get total frame count (derived from image sequence length).

        This is derived state - always consistent with image_files.
        Subscribe to image_sequence_changed to be notified of changes.
        """
        self._assert_main_thread()
        return self._total_frames

    # ==================== Original Data (Undo/Comparison) ====================

    def set_original_data(self, curve_name: str, data: CurveDataInput) -> None:
        """
        Store original unmodified data for comparison/undo.

        Args:
            curve_name: Curve to store original data for
            data: Original curve data before modifications
        """
        self._assert_main_thread()
        self._original_data[curve_name] = list(data)
        logger.debug(f"Stored original data for '{curve_name}': {len(data)} points")

    def get_original_data(self, curve_name: str) -> CurveDataList:
        """
        Get original unmodified data for curve.

        Args:
            curve_name: Curve to get original data for

        Returns:
            Copy of original data, or empty list if not set
        """
        self._assert_main_thread()
        return self._original_data.get(curve_name, []).copy()

    def clear_original_data(self, curve_name: str | None = None) -> None:
        """
        Clear original data (after committing changes).

        Args:
            curve_name: Curve to clear, or None to clear all
        """
        self._assert_main_thread()

        if curve_name is None:
            self._original_data.clear()
            logger.debug("Cleared all original data")
        elif curve_name in self._original_data:
            del self._original_data[curve_name]
            logger.debug(f"Cleared original data for '{curve_name}'")

    # ==================== Metadata ====================

    def get_curve_metadata(self, curve_name: str) -> dict[str, Any]:
        """
        Get metadata for curve (visibility, color, etc.).

        Returns a COPY for safety.

        Args:
            curve_name: Curve to get metadata for

        Returns:
            Copy of metadata dict
        """
        if curve_name not in self._curve_metadata:
            return {"visible": True}
        return self._curve_metadata[curve_name].copy()

    def set_curve_visibility(self, curve_name: str, visible: bool) -> None:
        """
        Set curve visibility.

        Args:
            curve_name: Curve to modify
            visible: True to show, False to hide
        """
        self._assert_main_thread()
        if curve_name not in self._curve_metadata:
            self._curve_metadata[curve_name] = {}
        self._curve_metadata[curve_name]["visible"] = visible
        self._emit(self.curve_visibility_changed, (curve_name, visible))

        logger.debug(f"Curve '{curve_name}' visibility: {visible}")

    # ========================================
    # Curve-Level Selection State (NEW)
    # ========================================

    def get_selected_curves(self) -> set[str]:
        """
        Get selected curves for display (returns copy).

        This is curve-level selection (which trajectories to show),
        distinct from point-level selection (which points within active curve).

        Note on terminology:
        - get_selected_curves() → which curve trajectories to display (this method)
        - get_selection(curve_name) → which frame indices within a curve are selected

        Returns:
            Set of selected curve names (copy for safety)
        """
        self._assert_main_thread()
        return self._selected_curves.copy()

    def set_selected_curves(self, curve_names: set[str] | None) -> None:
        """
        Set which curves are selected for display.

        Automatically updates derived display_mode property via signal.

        Validation: Filters out non-existent curves if data is loaded.
        Allows setting selection before curves load (for session restoration).

        Args:
            curve_names: Set of curve names to select

        Raises:
            TypeError: If curve_names is None
            ValueError: If any curve name is empty or whitespace-only
        """
        self._assert_main_thread()

        if curve_names is None:
            raise TypeError("curve_names cannot be None (use empty set for no selection)")

        new_selection = curve_names.copy()

        # Validate non-empty strings (defensive programming)
        invalid_names = {name for name in new_selection if not name or not name.strip()}
        if invalid_names:
            raise ValueError(f"Curve names cannot be empty or whitespace-only: {invalid_names}")

        # Validate curve existence - filter invalid curves (fail-fast)
        if self._curves_data:  # Only validate if curves loaded
            all_curves = set(self._curves_data.keys())
            invalid = new_selection - all_curves
            if invalid:
                logger.warning(f"Filtering invalid curves from selection: {invalid}. Available curves: {all_curves}")
                # Filter to only valid curves to prevent persistent invalid references
                new_selection = new_selection & all_curves

        if new_selection != self._selected_curves:
            self._selected_curves = new_selection
            self._emit(self.selection_state_changed, (new_selection.copy(), self._show_all_curves))
            logger.debug(f"Curve selection changed: {len(new_selection)} curves selected")

    def get_show_all_curves(self) -> bool:
        """Get show-all-curves mode state."""
        self._assert_main_thread()
        return self._show_all_curves

    def set_show_all_curves(self, show_all: bool | None) -> None:
        """
        Set show-all-curves mode.

        Automatically updates derived display_mode property via signal.

        Args:
            show_all: Whether to show all visible curves

        Raises:
            TypeError: If show_all is None
        """
        self._assert_main_thread()

        if show_all is None:
            raise TypeError("show_all cannot be None (use True or False)")

        if show_all != self._show_all_curves:
            self._show_all_curves = show_all
            self._emit(self.selection_state_changed, (self._selected_curves.copy(), show_all))
            logger.debug(f"Show all curves mode: {show_all}")

    @property
    def display_mode(self) -> DisplayMode:
        """
        Compute display mode from selection inputs.

        This is DERIVED STATE - always consistent with inputs, no storage.

        Logic:
        - Show-all enabled → ALL_VISIBLE
        - Curves selected → SELECTED
        - Otherwise → ACTIVE_ONLY

        Important: This property reflects state immediately, even during batch mode.
        Batch mode only defers signal emissions, not state visibility.

        Returns:
            DisplayMode enum computed from current selection state

        Example:
            >>> app_state = get_application_state()
            >>> app_state.set_show_all_curves(True)
            >>> app_state.display_mode
            <DisplayMode.ALL_VISIBLE: 1>

            >>> app_state.set_show_all_curves(False)
            >>> app_state.set_selected_curves({"Track1", "Track2"})
            >>> app_state.display_mode
            <DisplayMode.SELECTED: 2>

            >>> # Batch mode: state visible immediately, signals deferred
            >>> with app_state.batch_updates():
            ...     app_state.set_selected_curves(set())
            ...     app_state.display_mode  # Returns ACTIVE_ONLY immediately!
            <DisplayMode.ACTIVE_ONLY: 3>
            # Signals emit when context exits
        """
        # Optional enhancement: Add thread safety assertion for consistency
        self._assert_main_thread()

        if self._show_all_curves:
            return DisplayMode.ALL_VISIBLE
        elif self._selected_curves:
            return DisplayMode.SELECTED
        else:
            return DisplayMode.ACTIVE_ONLY

    # ==================== Batch Operations ====================

    @contextmanager
    def batch_updates(self) -> Generator[None, None, None]:
        """
        Context manager for batch operations.

        Signals are queued during batch operations and emitted once at the end.
        Multiple signals of the same type are deduplicated (last state wins).

        Simple nested support: If already batching, inner context is a no-op.
        This is safe for single-threaded applications.

        Example:
            with state.batch_updates():
                state.set_curve_data("Track1", data1)
                state.set_curve_data("Track2", data2)
                # curves_changed emitted once at end with final state
        """
        self._assert_main_thread()

        # If already batching, just pass through (simple nested support)
        if self._batching:
            yield
            return

        # Start batch mode
        self._batching = True
        self._pending_signals.clear()
        logger.debug("Batch mode started")

        try:
            yield
        except Exception:
            # On exception, clear pending signals
            self._pending_signals.clear()
            raise
        finally:
            self._batching = False

            # Emit accumulated signals with reentrancy protection
            # (prevents infinite loops if signal handlers modify state)
            if not self._emitting:
                self._emitting = True
                try:
                    # Emit accumulated signals (dict ensures deduplication, last args wins)
                    # Iterate over a copy to allow dict modification during signal emission
                    for signal, args in list(self._pending_signals.items()):
                        signal.emit(*args)
                finally:
                    self._emitting = False

            self._pending_signals.clear()
            logger.debug("Batch mode ended")

    def _emit(self, signal: SignalInstance, args: tuple[Any, ...]) -> None:
        """
        Emit signal immediately or queue if in batch/emitting mode.

        In batch mode, signals are queued and deduplicated by signal type.
        During emission, reentrancy is prevented (signals queued, not emitted).
        Last emission wins for each signal type.
        """
        if self._batching or self._emitting:
            # Queue signal with args (dict deduplicates, last one wins)
            self._pending_signals[signal] = args
        else:
            # Emit immediately
            signal.emit(*args)

    # ==================== Helper Methods ====================

    def with_active_curve(self, callback: Callable[[str, CurveDataInput], T]) -> T | None:
        """Execute callback with active curve data, returning None if inactive/no data.

        Simplifies the common pattern:
            active = state.active_curve
            if active is None:
                return None
            data = state.get_curve_data(active)
            if not data:
                return None
            return callback(active, data)

        Args:
            callback: Function taking (curve_name: str, data: CurveDataInput) returning T

        Returns:
            Result of callback, or None if active curve missing or has no data

        Example:
            # Before (6 lines):
            active = state.active_curve
            if not active:
                return
            data = state.get_curve_data(active)
            if not data:
                return
            self.display_curve(active, data)

            # After (1 line):
            state.with_active_curve(lambda name, data: self.display_curve(name, data))
        """
        active = self.active_curve
        if not active:
            return None
        data = self.get_curve_data(active)
        if not data:
            return None
        return callback(active, data)

    @property
    def active_curve_data(self) -> tuple[str, CurveDataList] | None:
        """Get (curve_name, data) for active curve, or None if unavailable.

        Returns curve data even if empty (empty list is valid for new curves).
        Only returns None if no active curve is set.

        Use this to safely access active curve AND its data in one operation.

        Pattern established by Phase 4 Task 4.4:
        Complex state retrieval should use @property or service methods,
        not repeated in business logic.

        Returns:
            Tuple of (curve_name, curve_data) or None if no active curve set.
            Note: curve_data may be an empty list [] for new curves.

        Example:
            # Modern property-based approach (recommended):
            if (curve_data := state.active_curve_data) is None:
                return
            curve_name, data = curve_data
            # Use curve_name and data (data may be empty [])

            # Old 4-step pattern (avoid in new code):
            active = state.active_curve
            if not active:
                return
            data = state.get_curve_data(active)
            if not data:
                return
            # Use active and data
        """
        active = self.active_curve
        if not active:
            return None

        try:
            data = self.get_curve_data(active)
            return (active, data)
        except ValueError as e:
            # Defensive: get_curve_data() raises ValueError if no active curve,
            # but we already checked, so this should never happen
            logger.error(f"Unexpected error getting curve data: {e}")
            return None

    # ==================== State Inspection ====================

    def get_state_summary(self) -> dict[str, Any]:
        """
        Get summary of current state (for debugging).

        Returns:
            Dict with state statistics
        """
        total_points = sum(len(data) for data in self._curves_data.values())
        total_selected = sum(len(sel) for sel in self._selection.values())

        return {
            "num_curves": len(self._curves_data),
            "total_points": total_points,
            "total_selected": total_selected,
            "active_curve": self._active_curve,
            "current_frame": self._current_frame,
            "is_batching": self._batching,
        }


# ==================== Singleton Pattern ====================

_app_state: ApplicationState | None = None


def get_application_state() -> ApplicationState:
    """
    Get global ApplicationState instance.

    Singleton pattern ensures single source of truth.

    Returns:
        Global ApplicationState instance
    """
    global _app_state
    if _app_state is None:
        _app_state = ApplicationState()
    return _app_state


def reset_application_state() -> None:
    """
    Reset ApplicationState singleton (for testing).

    WARNING: Only call from tests! Resets all application state.

    CRITICAL: Properly cleans up QObject to prevent resource exhaustion.
    Without deleteLater() + processEvents(), QObjects accumulate in session-scope
    QApplication causing segfaults after 850+ tests (see UNIFIED_TESTING_GUIDE).
    """
    global _app_state
    if _app_state is not None:
        logger.warning("ApplicationState reset (should only happen in tests)")

        # CRITICAL: Properly clean up QObject to prevent accumulation
        try:
            # Remove parent if any (usually None, but safe to call)
            _app_state.setParent(None)
            # Schedule for deletion
            _app_state.deleteLater()
            # Process events to ensure deleteLater() is handled
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                app.processEvents()
        except RuntimeError:
            # QObject may already be deleted, that's okay
            pass

    _app_state = None

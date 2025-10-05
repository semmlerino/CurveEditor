#!/usr/bin/env python
"""
ApplicationState - Centralized State Management for CurveEditor

Single source of truth for all application state:
- Multi-curve data (dict[str, CurveDataList])
- Per-curve selection (dict[str, set[int]])
- Active curve (str)
- Current frame (int)
- View transformation state (ViewState)
- Curve metadata (visibility, color, etc.)

Key Design Principles:
- Immutable external interface (returns copies)
- Qt Signal-based reactivity (no polling needed)
- Batch operations (prevent signal storms, QMutex-protected)
- Main thread only (enforced by runtime assertions)

Thread Safety:
- All methods MUST be called from main thread
- Batch operations protected by QMutex for thread safety
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

    # ✅ Good: One signal, one repaint
    state.begin_batch()
    try:
        state.set_show_all_curves(False)
        state.set_selected_curves({"Track1", "Track2"})
    finally:
        state.end_batch()

    Batch mode is especially important for coordinated selection state changes
    where display_mode transitions require updating both show_all and selected_curves.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QCoreApplication, QMutex, QMutexLocker, QObject, QThread, Signal, SignalInstance

from core.display_mode import DisplayMode
from core.models import CurvePoint
from core.type_aliases import CurveDataInput, CurveDataList

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ViewState:
    """
    Immutable view transformation state.

    Uses dataclass with frozen=True for immutability.
    Helper methods create new instances rather than modifying.
    """

    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0
    flip_y: bool = True
    scale_to_image: bool = True

    def with_zoom(self, zoom: float) -> ViewState:
        """Create new ViewState with updated zoom."""
        return ViewState(
            zoom=zoom, pan_x=self.pan_x, pan_y=self.pan_y, flip_y=self.flip_y, scale_to_image=self.scale_to_image
        )

    def with_pan(self, pan_x: float, pan_y: float) -> ViewState:
        """Create new ViewState with updated pan."""
        return ViewState(
            zoom=self.zoom, pan_x=pan_x, pan_y=pan_y, flip_y=self.flip_y, scale_to_image=self.scale_to_image
        )


class ApplicationState(QObject):
    """
    Centralized application state container for multi-curve editing.

    This is the ONLY location that stores application data.
    All components read from here via getters and subscribe
    to signals for updates. No component maintains local copies.

    Thread Safety Contract:
    - All data access methods MUST be called from main thread only
    - _assert_main_thread() enforces this at runtime for all modifications
    - Batch operations are thread-safe (protected by internal QMutex)
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
    state_changed = Signal()  # Emitted on any state change
    curves_changed = Signal(dict)  # curves_data changed: dict[str, CurveDataList]
    selection_changed = Signal(set, str)  # Point-level (frame indices)
    active_curve_changed = Signal(str)  # active_curve_name: str
    frame_changed = Signal(int)  # current_frame: int
    view_changed = Signal(object)  # view_state: ViewState
    curve_visibility_changed = Signal(str, bool)  # (curve_name, visible)

    # NEW: Curve-level selection state changed (selected_curves, show_all)
    selection_state_changed = Signal(set, bool)

    def __init__(self) -> None:
        super().__init__()

        # Core state (private - access via getters only)
        self._curves_data: dict[str, CurveDataList] = {}
        self._curve_metadata: dict[str, dict[str, Any]] = {}
        self._active_curve: str | None = None
        self._selection: dict[str, set[int]] = {}  # Point-level selection (indices within curves)
        self._current_frame: int = 1
        self._view_state: ViewState = ViewState()

        # NEW: Curve-level selection state (which trajectories to display)
        # Note: This is DISTINCT from _selection above:
        #   - _selected_curves: which curve trajectories to show (curve names)
        #   - _selection: which points within active curve are selected (frame indices)
        self._selected_curves: set[str] = set()
        self._show_all_curves: bool = False

        # Batch operation support (thread-safe with mutex)
        self._mutex = QMutex()  # Protects batch mode flag and pending signals
        self._batch_mode: bool = False
        self._pending_signals: list[tuple[SignalInstance, tuple[Any, ...]]] = []

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
            Copy of curve data, or empty list if curve doesn't exist
        """
        self._assert_main_thread()  # Prevent read tearing from wrong thread
        if curve_name is None:
            curve_name = self._active_curve
        if curve_name is None or curve_name not in self._curves_data:
            return []
        return self._curves_data[curve_name].copy()

    def set_curve_data(self, curve_name: str, data: CurveDataInput, metadata: dict[str, Any] | None = None) -> None:
        """
        Replace entire curve data.

        Creates internal copy for safety. Original data not retained.

        Args:
            curve_name: Name of curve to set
            data: New curve data (accepts any sequence of point data)
            metadata: Optional metadata (visibility, color, etc.)
        """
        self._assert_main_thread()
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

    def delete_curve(self, curve_name: str) -> None:
        """
        Remove curve from state.

        Also removes associated metadata and selection.

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

        # If active curve was deleted, clear it
        if self._active_curve == curve_name:
            self._active_curve = None
            self._emit(self.active_curve_changed, ("",))

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
            if curve_name in self._selection and self._selection[curve_name]:
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
            self._emit(self.active_curve_changed, (curve_name or "",))

            logger.info(f"Active curve changed: '{old_curve}' → '{curve_name}'")

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
            old_frame = self._current_frame
            self._current_frame = frame
            self._emit(self.frame_changed, (frame,))

            logger.debug(f"Frame changed: {old_frame} → {frame}")

    # ==================== View State ====================

    @property
    def view_state(self) -> ViewState:
        """Get current view state (copy)."""
        return self._view_state

    def set_view_state(self, view_state: ViewState) -> None:
        """
        Set view state.

        Args:
            view_state: New view state
        """
        self._assert_main_thread()
        self._view_state = view_state
        self._emit(self.view_changed, (view_state,))

        logger.debug(
            f"View state updated: zoom={view_state.zoom:.2f}, pan=({view_state.pan_x:.1f}, {view_state.pan_y:.1f})"
        )

    def set_zoom(self, zoom: float) -> None:
        """Update only zoom level."""
        self.set_view_state(self._view_state.with_zoom(zoom))

    def set_pan(self, pan_x: float, pan_y: float) -> None:
        """Update only pan offset."""
        self.set_view_state(self._view_state.with_pan(pan_x, pan_y))

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

    def set_selected_curves(self, curve_names: set[str]) -> None:
        """
        Set which curves are selected for display.

        Automatically updates derived display_mode property via signal.

        Validation: Filters out non-existent curves if data is loaded.
        Allows setting selection before curves load (for session restoration).

        Args:
            curve_names: Set of curve names to select

        Raises:
            ValueError: If any curve name is empty or whitespace-only
        """
        self._assert_main_thread()
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
                logger.warning(
                    f"Filtering invalid curves from selection: {invalid}. " f"Available curves: {all_curves}"
                )
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

    def set_show_all_curves(self, show_all: bool) -> None:
        """
        Set show-all-curves mode.

        Automatically updates derived display_mode property via signal.

        Args:
            show_all: Whether to show all visible curves
        """
        self._assert_main_thread()

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
            >>> app_state.begin_batch()
            >>> app_state.set_selected_curves(set())
            >>> app_state.display_mode  # Returns ACTIVE_ONLY immediately!
            <DisplayMode.ACTIVE_ONLY: 3>
            >>> app_state.end_batch()  # Signals emit now
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

    def begin_batch(self) -> None:
        """
        Begin batch operation mode.

        In batch mode, signals are deferred until end_batch() is called.
        This prevents signal storms when making multiple related changes.

        Thread-safe: Protected by internal mutex for concurrent access safety.

        Example:
            state.begin_batch()
            try:
                for curve in curves:
                    state.set_curve_data(curve, data)
            finally:
                state.end_batch()
        """
        self._assert_main_thread()

        # Critical section: protected by mutex
        with QMutexLocker(self._mutex):
            if self._batch_mode:
                logger.warning("Already in batch mode")
                return

            self._batch_mode = True
            self._pending_signals.clear()

        logger.debug("Batch mode started")

    def end_batch(self) -> None:
        """
        End batch operation mode and emit all pending signals.

        Signals are emitted in order they were triggered.
        Duplicate signals are eliminated.

        Thread-safe: Protected by internal mutex for concurrent access safety.
        Signals are emitted outside the lock to prevent deadlock.
        """
        self._assert_main_thread()

        # Critical section: copy pending signals while holding lock
        with QMutexLocker(self._mutex):
            if not self._batch_mode:
                logger.warning("Not in batch mode")
                return

            self._batch_mode = False
            # Copy pending signals to emit outside lock (prevents deadlock)
            signals_to_emit = self._pending_signals.copy()
            self._pending_signals.clear()

        # Emit signals outside lock to prevent deadlock
        seen_signals: set[int] = set()
        for signal, args in signals_to_emit:
            signal_id = id(signal)
            if signal_id not in seen_signals:
                signal.emit(*args)
                seen_signals.add(signal_id)

        # Always emit state_changed last
        self.state_changed.emit()

        logger.debug(f"Batch mode ended: {len(seen_signals)} unique signals emitted")

    def _emit(self, signal: SignalInstance, args: tuple[Any, ...]) -> None:
        """
        Emit signal (or defer if in batch mode).

        Internal method used by all state modification methods.

        Thread-safe: Protected by internal mutex when checking/modifying batch state.

        Args:
            signal: Qt signal to emit
            args: Signal arguments as tuple
        """
        # Critical section: check batch mode and append if needed
        with QMutexLocker(self._mutex):
            if self._batch_mode:
                # Defer signal (append while holding lock)
                self._pending_signals.append((signal, args))
                return

        # Emit immediately (outside lock to prevent deadlock)
        signal.emit(*args)
        self.state_changed.emit()

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
            "view_zoom": self._view_state.zoom,
            "batch_mode": self._batch_mode,
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

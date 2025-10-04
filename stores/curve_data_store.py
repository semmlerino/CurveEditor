from __future__ import annotations

"""
COMPATIBILITY LAYER - Gradual Migration Support

This store provides backward compatibility during ApplicationState migration.
New code should use ApplicationState directly via get_application_state().

DEPRECATED: This module will be removed in a future major version (v2.0).

For new code, use:
    from stores.application_state import get_application_state
    state = get_application_state()
    state.set_curve_data("curve_name", data)

See: ApplicationState (stores/application_state.py) for the modern API with
native multi-curve support, batch operations, and better type safety.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from core.logger_utils import get_logger
from core.models import PointStatus
from core.type_aliases import CurveDataInput, CurveDataList, LegacyPointData

if TYPE_CHECKING:
    from core.curve_data import CurveDataWithMetadata

logger = get_logger("curve_data_store")


class CurveDataStore(QObject):
    """
    DEPRECATED: Legacy single-curve data store (compatibility layer).

    This class is maintained for backward compatibility during the ApplicationState
    migration. It provides reactive signal-based updates for single-curve editing.

    LIMITATIONS:
    - Single-curve only (not designed for multi-curve workflows)
    - No batch operations (can cause signal storms)
    - Limited type safety compared to ApplicationState

    For new code, use ApplicationState instead:
        from stores.application_state import get_application_state
        state = get_application_state()

    This class will be removed in v2.0.
    """

    # Comprehensive signals for all data changes
    data_changed = Signal()  # Full data replacement
    point_added = Signal(int, object)  # index, point data
    point_updated = Signal(int, float, float)  # index, new_x, new_y
    point_removed = Signal(int)  # index
    point_status_changed = Signal(int, str)  # index, new_status
    selection_changed = Signal(set)  # set of selected indices
    batch_operation_started = Signal()  # For performance optimization
    batch_operation_ended = Signal()  # Triggers single update

    def __init__(self):
        """Initialize the curve data store."""
        super().__init__()
        self._data: CurveDataList = []
        self._selection: set[int] = set()
        self._undo_stack: list[CurveDataList] = []
        self._redo_stack: list[CurveDataList] = []
        self._max_undo_levels = 50
        self._batch_mode = False

        logger.info("CurveDataStore initialized")

    # ==================== Data Access ====================

    def get_data(self) -> CurveDataList:
        """
        Get a copy of the current curve data.

        Returns:
            Copy of curve data to prevent external mutation
        """
        return self._data.copy()

    def get_point(self, index: int) -> LegacyPointData | None:
        """
        Get a specific point by index.

        Args:
            index: Point index

        Returns:
            Point data or None if index invalid
        """
        if 0 <= index < len(self._data):
            return self._data[index]
        return None

    def get_selection(self) -> set[int]:
        """Get current selection."""
        return self._selection.copy()

    def point_count(self) -> int:
        """Get number of points."""
        return len(self._data)

    # ==================== Data Modification ====================

    def set_data(self, data: CurveDataInput | "CurveDataWithMetadata", preserve_selection_on_sync: bool = False) -> None:
        """
        Replace all curve data.

        Args:
            data: New curve data (can be CurveDataList or CurveDataWithMetadata)
            preserve_selection_on_sync: If True, preserve selection when data is structurally
                equivalent (for syncing status changes from ApplicationState)
        """
        if not self._batch_mode:
            self._add_to_undo()

        # Handle CurveDataWithMetadata wrapper
        from core.curve_data import CurveDataWithMetadata

        if isinstance(data, CurveDataWithMetadata):
            data = data.data  # Extract the actual data list

        old_data = self._data
        old_selection = self._selection.copy()
        new_data = list(data)  # Store a copy to prevent external mutation

        # Only preserve selection if explicitly requested AND data is structurally equivalent
        preserve_selection = False
        if preserve_selection_on_sync and len(old_data) == len(new_data) and len(old_selection) > 0:
            # Check if frames AND x,y coords match (only status may differ)
            frames_and_coords_match = all(
                old_data[i][0] == new_data[i][0]  # Same frame
                and old_data[i][1] == new_data[i][1]  # Same x
                and old_data[i][2] == new_data[i][2]  # Same y
                for i in range(len(old_data))
            )
            if frames_and_coords_match:
                preserve_selection = True
                logger.debug("Preserving selection across set_data (status-only sync)")

        self._data = new_data

        if preserve_selection:
            # Keep valid selection indices
            self._selection = {i for i in old_selection if i < len(self._data)}
        else:
            self._selection.clear()  # Clear selection when data structure changes

        if not self._batch_mode:
            self.data_changed.emit()
            if not preserve_selection:
                self.selection_changed.emit(set())
            # If preserving selection, don't emit selection_changed since it didn't change

        logger.debug(f"Set {len(data)} points")

    def add_point(self, point: tuple[int, float, float] | tuple[int, float, float, str]) -> int:
        """
        Add a point to the curve.

        Args:
            point: Point data (frame, x, y, [status])

        Returns:
            Index of added point
        """
        if not self._batch_mode:
            self._add_to_undo()

        # Ensure point has status
        if len(point) == 3:
            point = (*point, "keyframe")

        self._data.append(point)
        index = len(self._data) - 1

        if not self._batch_mode:
            self.point_added.emit(index, point)

        logger.debug(f"Added point at index {index}: {point}")
        return index

    def update_point(self, index: int, x: float, y: float) -> bool:
        """
        Update a point's coordinates.

        Args:
            index: Point index
            x: New x coordinate
            y: New y coordinate

        Returns:
            True if updated, False if index invalid
        """
        if not 0 <= index < len(self._data):
            logger.warning(f"Invalid index {index} for update")
            return False

        if not self._batch_mode:
            self._add_to_undo()

        point = self._data[index]
        frame = point[0]
        status = point[3] if len(point) > 3 else "keyframe"

        self._data[index] = (frame, x, y, status)

        if not self._batch_mode:
            self.point_updated.emit(index, x, y)

        logger.debug(f"Updated point {index} to ({x}, {y})")
        return True

    def remove_point(self, index: int) -> bool:
        """
        Remove a point.

        Args:
            index: Point index

        Returns:
            True if removed, False if index invalid
        """
        if not 0 <= index < len(self._data):
            logger.warning(f"Invalid index {index} for removal")
            return False

        if not self._batch_mode:
            self._add_to_undo()

        del self._data[index]

        # Update selection indices
        self._selection = {i - 1 if i > index else i for i in self._selection if i != index}

        if not self._batch_mode:
            self.point_removed.emit(index)
            if index in self._selection:
                self.selection_changed.emit(self._selection)

        logger.debug(f"Removed point at index {index}")
        return True

    def set_point_status(self, index: int, status: str | PointStatus) -> bool:
        """
        Change a point's status.

        Args:
            index: Point index
            status: New status (string or PointStatus enum)

        Returns:
            True if changed, False if index invalid
        """
        if not 0 <= index < len(self._data):
            logger.warning(f"Invalid index {index} for status change")
            return False

        if not self._batch_mode:
            self._add_to_undo()

        # Convert PointStatus to string if needed
        if isinstance(status, PointStatus):
            status = status.value

        point = self._data[index]
        self._data[index] = (point[0], point[1], point[2], status)

        if not self._batch_mode:
            self.point_status_changed.emit(index, status)

        logger.debug(f"Changed point {index} status to {status}")
        return True

    # ==================== Selection Management ====================

    def select(self, index: int, add_to_selection: bool = False) -> None:
        """
        Select a point.

        Args:
            index: Point index
            add_to_selection: Add to existing selection if True (toggle), replace if False
        """
        if not 0 <= index < len(self._data):
            return

        if add_to_selection:
            # Toggle: add if not selected, remove if already selected
            if index in self._selection:
                self._selection.discard(index)
            else:
                self._selection.add(index)
        else:
            self._selection = {index}

        self.selection_changed.emit(self._selection)
        logger.debug(f"Selected point {index}, total selected: {len(self._selection)}")

    def deselect(self, index: int) -> None:
        """Deselect a point."""
        if index in self._selection:
            self._selection.remove(index)
            self.selection_changed.emit(self._selection)

    def select_range(self, start: int, end: int) -> None:
        """Select a range of points."""
        start = max(0, start)
        end = min(len(self._data) - 1, end)

        self._selection = set(range(start, end + 1))
        self.selection_changed.emit(self._selection)

    def clear_selection(self) -> None:
        """Clear all selection."""
        self._selection.clear()
        self.selection_changed.emit(self._selection)

    def select_all(self) -> None:
        """Select all points."""
        self._selection = set(range(len(self._data)))
        self.selection_changed.emit(self._selection)

    # ==================== Batch Operations ====================

    def begin_batch_operation(self) -> None:
        """
        Start a batch operation.

        Suspends signals until end_batch_operation() is called.
        Useful for multiple operations that should trigger only one UI update.
        """
        if not self._batch_mode:
            self._add_to_undo()
            self._batch_mode = True
            self.batch_operation_started.emit()
            logger.debug("Batch operation started")

    def end_batch_operation(self) -> None:
        """
        End a batch operation and emit update signal.
        """
        if self._batch_mode:
            self._batch_mode = False
            self.batch_operation_ended.emit()
            self.data_changed.emit()  # Single update for entire batch
            logger.debug("Batch operation ended")

    # ==================== Undo/Redo ====================

    def _add_to_undo(self) -> None:
        """Add current state to undo stack."""
        if len(self._undo_stack) >= self._max_undo_levels:
            self._undo_stack.pop(0)

        self._undo_stack.append(self._data.copy())
        self._redo_stack.clear()  # Clear redo when new action performed

    def undo(self) -> bool:
        """
        Undo last operation.

        Returns:
            True if undone, False if nothing to undo
        """
        if not self._undo_stack:
            return False

        self._redo_stack.append(self._data.copy())
        self._data = self._undo_stack.pop()
        self.data_changed.emit()

        logger.debug("Undo performed")
        return True

    def redo(self) -> bool:
        """
        Redo last undone operation.

        Returns:
            True if redone, False if nothing to redo
        """
        if not self._redo_stack:
            return False

        self._undo_stack.append(self._data.copy())
        self._data = self._redo_stack.pop()
        self.data_changed.emit()

        logger.debug("Redo performed")
        return True

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return bool(self._undo_stack)

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return bool(self._redo_stack)

    # ==================== Utility Methods ====================

    def clear(self) -> None:
        """Clear all data."""
        self.set_data([])

    def get_frame_range(self) -> tuple[int, int] | None:
        """
        Get min and max frame numbers.

        Returns:
            (min_frame, max_frame) or None if no data
        """
        if not self._data:
            return None

        frames = [point[0] for point in self._data]
        return (min(frames), max(frames))

    def get_points_at_frame(self, frame: int) -> list[int]:
        """
        Get indices of all points at a specific frame.

        Args:
            frame: Frame number

        Returns:
            List of point indices at that frame
        """
        return [i for i, point in enumerate(self._data) if point[0] == frame]

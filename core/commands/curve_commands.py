#!/usr/bin/env python
"""
Curve-specific commands for undo/redo functionality.

This module contains command implementations for all curve editing operations
including point manipulation, smoothing, filtering, and data modifications.
"""
# pyright: reportImportCycles=false

from __future__ import annotations

import copy
from abc import ABC
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from typing_extensions import override

if TYPE_CHECKING:
    from protocols.ui import MainWindowProtocol

from core.commands.base_command import Command
from core.logger_utils import get_logger
from core.type_aliases import CurveDataInput, CurveDataList, LegacyPointData
from stores.application_state import get_application_state

logger = get_logger("curve_commands")


class CurveDataCommand(Command, ABC):
    """Base class for commands that modify curve data.

    Provides common patterns for:
    - Active curve validation and retrieval
    - Target curve storage for undo/redo
    - Standardized error handling
    - Point tuple manipulation helpers
    """

    def __init__(self, description: str):
        """Initialize base curve data command.

        Args:
            description: Human-readable command description
        """
        super().__init__(description)
        self._target_curve: str | None = None  # Store target curve for undo (Bug #2 fix)

    def _get_active_curve_data(self) -> tuple[str, CurveDataList] | None:
        """Get and validate active curve data.

        Returns:
            Tuple of (curve_name, curve_data) if successful, None if no active curve

        Note:
            Does NOT store target curve - caller must do this explicitly in execute().
            Does NOT log errors - caller should handle logging as needed.
        """
        app_state = get_application_state()
        if (cd := app_state.active_curve_data) is None:
            return None
        return cd  # Return tuple directly, no side effects

    def _safe_execute(self, operation_name: str, operation: Callable[[], bool]) -> bool:
        """Execute operation with standardized error handling.

        Args:
            operation_name: Name of operation (e.g., "executing", "undoing", "redoing")
            operation: Callable that performs the operation and returns success bool

        Returns:
            True if operation succeeded, False if failed or raised exception
        """
        try:
            return operation()
        except Exception as e:
            logger.error(f"Error {operation_name} {self.__class__.__name__}: {e}")
            return False

    def _update_point_position(self, point: LegacyPointData, new_pos: tuple[float, float]) -> LegacyPointData:
        """Update point position while preserving frame and status.

        Args:
            point: Original point tuple (frame, x, y) or (frame, x, y, status)
            new_pos: New (x, y) position

        Returns:
            Updated point tuple with same structure as input
        """
        if len(point) >= 4:
            return (point[0], new_pos[0], new_pos[1], point[3])
        elif len(point) == 3:
            return (point[0], new_pos[0], new_pos[1])
        else:  # Invalid tuple (< 3 elements) - return unchanged
            return point  # pyright: ignore[reportUnreachable]

    def _update_point_at_index(
        self, curve_data: list[LegacyPointData], index: int, updater: Callable[[LegacyPointData], LegacyPointData]
    ) -> bool:
        """Update point at index with bounds checking.

        Helper method available for future commands requiring functional-style indexed updates.
        Currently not used by existing commands but provides a reusable pattern for
        commands that need to apply transformations to points at specific indices.

        Args:
            curve_data: Curve data list
            index: Point index
            updater: Function that takes old point and returns new point

        Returns:
            True if update successful, False if index out of bounds
        """
        if 0 <= index < len(curve_data):
            curve_data[index] = updater(curve_data[index])
            return True
        logger.warning(f"Point index {index} out of range (len={len(curve_data)})")
        return False


class SetCurveDataCommand(CurveDataCommand):
    """
    Command to set the entire curve data.

    This is the most basic command that stores the complete before/after
    state of curve data. Used for operations that modify large portions
    of the curve.
    """

    def __init__(self, description: str, new_data: CurveDataInput, old_data: CurveDataInput | None = None) -> None:
        """
        Initialize the set curve data command.

        Args:
            description: Human-readable description of the operation
            new_data: The new curve data to set
            old_data: The previous curve data (captured during execution if None)
        """
        super().__init__(description)
        self.new_data: list[LegacyPointData] = list(copy.deepcopy(new_data))
        self.old_data: list[LegacyPointData] | None = list(copy.deepcopy(old_data)) if old_data is not None else None

    @override
    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute the command by setting new curve data."""

        def _execute_operation() -> bool:
            # Get active curve data (validation only - no side effects)
            if (result := self._get_active_curve_data()) is None:
                logger.error("No active curve")
                return False
            curve_name, curve_data = result

            # Explicitly store target curve at start of execute()
            self._target_curve = curve_name

            # Capture old data if not provided
            if self.old_data is None:
                self.old_data = copy.deepcopy(curve_data)

            # Set new data in ApplicationState (signals update view)
            app_state = get_application_state()
            app_state.set_curve_data(curve_name, list(self.new_data))
            self.executed = True
            return True

        return self._safe_execute("executing", _execute_operation)

    @override
    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo by restoring the old curve data."""

        def _undo_operation() -> bool:
            if not self._target_curve or self.old_data is None:
                logger.error("Missing target curve or old data for undo")
                return False

            app_state = get_application_state()
            app_state.set_curve_data(self._target_curve, list(self.old_data))
            self.executed = False
            return True

        return self._safe_execute("undoing", _undo_operation)

    @override
    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo by setting the new curve data again."""

        def _redo_operation() -> bool:
            if not self._target_curve:
                logger.error("Missing target curve for redo")
                return False

            app_state = get_application_state()
            app_state.set_curve_data(self._target_curve, list(self.new_data))
            self.executed = True
            return True

        return self._safe_execute("redoing", _redo_operation)


class SmoothCommand(CurveDataCommand):
    """
    Command for smoothing operations.

    Stores the specific points that were smoothed, the smoothing parameters,
    and the before/after states for those points.
    """

    def __init__(
        self,
        description: str,
        indices: Sequence[int],
        filter_type: str,
        window_size: int,
        old_points: Sequence[LegacyPointData] | None = None,
        new_points: Sequence[LegacyPointData] | None = None,
    ) -> None:
        """
        Initialize the smooth command.

        Args:
            description: Human-readable description
            indices: Indices of points that were smoothed
            filter_type: Type of smoothing filter used
            window_size: Size of the smoothing window
            old_points: Original point values before smoothing
            new_points: Smoothed point values after smoothing
        """
        super().__init__(description)
        self.indices: list[int] = list(indices)
        self.filter_type: str = filter_type
        self.window_size: int = window_size
        self.old_points: list[LegacyPointData] | None = list(copy.deepcopy(old_points)) if old_points else None
        self.new_points: list[LegacyPointData] | None = list(copy.deepcopy(new_points)) if new_points else None

    @override
    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute smoothing operation."""

        def _execute_operation() -> bool:
            # Get active curve data
            if (result := self._get_active_curve_data()) is None:
                logger.error("No active curve")
                return False
            curve_name, curve_data = result

            # Store target curve for undo
            self._target_curve = curve_name

            # Capture old points if not provided
            if self.old_points is None:
                self.old_points = [curve_data[i] for i in self.indices if 0 <= i < len(curve_data)]

            # If new points not provided, perform smoothing
            if self.new_points is None:
                from services import get_data_service

                data_service = get_data_service()
                if not data_service:
                    logger.error("Data service not available")
                    return False

                points_to_smooth = [curve_data[i] for i in self.indices if 0 <= i < len(curve_data)]

                # Adjust window size if necessary for the number of points
                effective_window_size = min(self.window_size, len(points_to_smooth))
                if effective_window_size < self.window_size:
                    logger.debug(
                        f"Adjusted smoothing window size from {self.window_size} to {effective_window_size} for {len(points_to_smooth)} points"
                    )

                # Apply smoothing based on filter type
                if self.filter_type == "moving_average":
                    self.new_points = data_service.smooth_moving_average(points_to_smooth, effective_window_size)
                elif self.filter_type == "median":
                    self.new_points = data_service.filter_median(points_to_smooth, effective_window_size)
                elif self.filter_type == "butterworth":
                    # For butterworth, use order parameter
                    effective_order = max(1, effective_window_size // 2)
                    self.new_points = data_service.filter_butterworth(points_to_smooth, order=effective_order)
                else:
                    logger.error(f"Unknown filter type: {self.filter_type}")
                    return False

            # Apply smoothed points using ApplicationState batch mode
            new_curve_data = list(curve_data)
            for i, idx in enumerate(self.indices):
                if i < len(self.new_points) and 0 <= idx < len(new_curve_data):
                    new_curve_data[idx] = self.new_points[i]

            # Update ApplicationState (signals update view, preserves view state)
            app_state = get_application_state()
            app_state.set_curve_data(curve_name, new_curve_data)
            self.executed = True
            return True

        return self._safe_execute("executing", _execute_operation)

    @override
    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo smoothing by restoring original points."""

        def _undo_operation() -> bool:
            if not self._target_curve or not self.old_points:
                logger.error("Missing target curve or old points for undo")
                return False

            app_state = get_application_state()
            curve_data = list(app_state.get_curve_data(self._target_curve))

            for i, idx in enumerate(self.indices):
                if i < len(self.old_points) and 0 <= idx < len(curve_data):
                    curve_data[idx] = self.old_points[i]

            # Update ApplicationState (signals update view, preserves view state)
            app_state.set_curve_data(self._target_curve, curve_data)
            self.executed = False
            return True

        return self._safe_execute("undoing", _undo_operation)

    @override
    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo smoothing by applying smoothed points."""

        def _redo_operation() -> bool:
            if not self._target_curve or not self.new_points:
                logger.error("Missing target curve or new points for redo")
                return False

            app_state = get_application_state()
            curve_data = list(app_state.get_curve_data(self._target_curve))

            for i, idx in enumerate(self.indices):
                if i < len(self.new_points) and 0 <= idx < len(curve_data):
                    curve_data[idx] = self.new_points[i]

            # Update ApplicationState (signals update view, preserves view state)
            app_state.set_curve_data(self._target_curve, curve_data)
            self.executed = True
            return True

        return self._safe_execute("redoing", _redo_operation)

    @override
    def can_merge_with(self, other: Command) -> bool:
        """Check if this smooth command can be merged with another."""
        if not isinstance(other, SmoothCommand):
            return False

        # Can merge if using same filter type and similar indices
        return (
            self.filter_type == other.filter_type
            and self.window_size == other.window_size
            and bool(set(self.indices) & set(other.indices))  # Overlapping indices
        )

    @override
    def merge_with(self, other: Command) -> Command:
        """Merge with another smooth command."""
        if not isinstance(other, SmoothCommand) or not self.can_merge_with(other):
            raise ValueError("Cannot merge incompatible commands")

        # Combine indices and use the latest new_points
        combined_indices = list(set(self.indices) | set(other.indices))
        return SmoothCommand(
            description=f"Smooth {len(combined_indices)} points ({self.filter_type})",
            indices=combined_indices,
            filter_type=self.filter_type,
            window_size=self.window_size,
            old_points=self.old_points,  # Keep original old points
            new_points=other.new_points,  # Use latest new points
        )


class MovePointCommand(CurveDataCommand):
    """
    Command for moving individual points.

    This command is optimized for frequent point movements and supports
    merging consecutive moves of the same point.
    """

    def __init__(
        self, description: str, index: int, old_pos: tuple[float, float], new_pos: tuple[float, float]
    ) -> None:
        """
        Initialize the move point command.

        Args:
            description: Human-readable description
            index: Index of the point being moved
            old_pos: Original (x, y) position
            new_pos: New (x, y) position
        """
        super().__init__(description)
        self.index: int = index
        self.old_pos: tuple[float, float] = old_pos
        self.new_pos: tuple[float, float] = new_pos

    @override
    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute point movement."""

        def _execute_operation() -> bool:
            # Get active curve data
            if (result := self._get_active_curve_data()) is None:
                logger.error("No active curve")
                return False
            curve_name, curve_data = result

            # Store target curve for undo
            self._target_curve = curve_name

            curve_data = list(curve_data)
            if 0 <= self.index < len(curve_data):
                # Use helper to update point position
                curve_data[self.index] = self._update_point_position(curve_data[self.index], self.new_pos)

                app_state = get_application_state()
                app_state.set_curve_data(curve_name, curve_data)
                self.executed = True
                return True

            return False

        return self._safe_execute("executing", _execute_operation)

    @override
    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo point movement."""

        def _undo_operation() -> bool:
            if not self._target_curve:
                return False

            app_state = get_application_state()
            curve_data = list(app_state.get_curve_data(self._target_curve))

            if 0 <= self.index < len(curve_data):
                # Use helper to restore original position
                curve_data[self.index] = self._update_point_position(curve_data[self.index], self.old_pos)

                app_state.set_curve_data(self._target_curve, curve_data)
                self.executed = False
                return True

            return False

        return self._safe_execute("undoing", _undo_operation)

    @override
    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo point movement."""

        def _redo_operation() -> bool:
            if not self._target_curve:
                logger.error("Missing target curve for redo")
                return False

            app_state = get_application_state()
            curve_data = list(app_state.get_curve_data(self._target_curve))

            if 0 <= self.index < len(curve_data):
                # Use helper to apply new position
                curve_data[self.index] = self._update_point_position(curve_data[self.index], self.new_pos)

                app_state.set_curve_data(self._target_curve, curve_data)
                self.executed = True
                return True

            return False

        return self._safe_execute("redoing", _redo_operation)

    @override
    def can_merge_with(self, other: Command) -> bool:
        """Check if this move can be merged with another move of the same point."""
        return isinstance(other, MovePointCommand) and self.index == other.index

    @override
    def merge_with(self, other: Command) -> Command:
        """Merge with another move command for the same point."""
        if not isinstance(other, MovePointCommand) or self.index != other.index:
            raise ValueError("Cannot merge moves of different points")

        # Create new command that moves from original old_pos to other's new_pos
        return MovePointCommand(
            description=f"Move point {self.index}",
            index=self.index,
            old_pos=self.old_pos,
            new_pos=other.new_pos,
        )


class DeletePointsCommand(CurveDataCommand):
    """
    Command for deleting points from the curve.

    Stores the deleted points and their positions for restoration.
    """

    def __init__(
        self,
        description: str,
        indices: Sequence[int],
        deleted_points: Sequence[tuple[int, LegacyPointData]] | None = None,
    ) -> None:
        """
        Initialize the delete points command.

        Args:
            description: Human-readable description
            indices: Indices of points to delete
            deleted_points: The points that were deleted (captured during execution if None)
        """
        super().__init__(description)
        self.indices: list[int] = sorted(indices, reverse=True)  # Delete in reverse order to maintain indices
        self.deleted_points: list[tuple[int, LegacyPointData]] | None = (
            list(copy.deepcopy(deleted_points)) if deleted_points else None
        )

    @override
    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute point deletion."""

        def _execute_operation() -> bool:
            # Get active curve data
            if (result := self._get_active_curve_data()) is None:
                logger.error("No active curve")
                return False
            curve_name, curve_data = result

            # Store target curve for undo
            self._target_curve = curve_name

            curve_data = list(curve_data)

            # Capture points being deleted if not provided
            if self.deleted_points is None:
                self.deleted_points = []
                for idx in sorted(self.indices):  # Store in original order
                    if 0 <= idx < len(curve_data):
                        self.deleted_points.append((idx, curve_data[idx]))

            # Delete points in reverse order to maintain indices
            for idx in self.indices:
                if 0 <= idx < len(curve_data):
                    del curve_data[idx]

            app_state = get_application_state()
            app_state.set_curve_data(curve_name, curve_data)

            # Clear selection after deletion
            app_state.set_selection(curve_name, set())

            self.executed = True
            return True

        return self._safe_execute("executing", _execute_operation)

    @override
    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo point deletion by restoring deleted points."""

        def _undo_operation() -> bool:
            if not self._target_curve or not self.deleted_points:
                return False

            app_state = get_application_state()
            curve_data = list(app_state.get_curve_data(self._target_curve))

            # Insert points back in their original positions
            for idx, point in self.deleted_points:
                if 0 <= idx <= len(curve_data):
                    curve_data.insert(idx, point)

            app_state.set_curve_data(self._target_curve, curve_data)
            self.executed = False
            return True

        return self._safe_execute("undoing", _undo_operation)

    @override
    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo point deletion."""

        def _redo_operation() -> bool:
            if not self._target_curve or not self.deleted_points:
                logger.error("Missing target curve or deleted points for redo")
                return False

            app_state = get_application_state()
            curve_data = list(app_state.get_curve_data(self._target_curve))

            # Delete points in reverse order to maintain indices
            for idx in self.indices:
                if 0 <= idx < len(curve_data):
                    del curve_data[idx]

            app_state.set_curve_data(self._target_curve, curve_data)

            # Clear selection after deletion
            app_state.set_selection(self._target_curve, set())

            self.executed = True
            return True

        return self._safe_execute("redoing", _redo_operation)


class BatchMoveCommand(CurveDataCommand):
    """
    Command for moving multiple points at once.

    This command is used for operations that move several points simultaneously,
    such as dragging multiple selected points or nudging a selection.
    """

    def __init__(
        self,
        description: str,
        moves: Sequence[tuple[int, tuple[float, float], tuple[float, float]]],
    ) -> None:
        """
        Initialize the batch move command.

        Args:
            description: Human-readable description
            moves: List of (index, old_pos, new_pos) tuples
        """
        super().__init__(description)
        self.moves: list[tuple[int, tuple[float, float], tuple[float, float]]] = list(
            moves
        )  # List of (index, old_pos, new_pos)

    @override
    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute batch point movement."""

        def _execute_operation() -> bool:
            # Get active curve data
            if (result := self._get_active_curve_data()) is None:
                logger.error("No active curve")
                return False
            curve_name, curve_data = result

            # Store target curve for undo
            self._target_curve = curve_name

            curve_data = list(curve_data)

            # Apply all moves using helper
            for index, _, new_pos in self.moves:
                if 0 <= index < len(curve_data):
                    curve_data[index] = self._update_point_position(curve_data[index], new_pos)

            app_state = get_application_state()
            app_state.set_curve_data(curve_name, curve_data)
            self.executed = True
            return True

        return self._safe_execute("executing", _execute_operation)

    @override
    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo batch point movement."""

        def _undo_operation() -> bool:
            if not self._target_curve:
                return False

            app_state = get_application_state()
            curve_data = list(app_state.get_curve_data(self._target_curve))

            # Restore all original positions using helper
            for index, old_pos, _ in self.moves:
                if 0 <= index < len(curve_data):
                    curve_data[index] = self._update_point_position(curve_data[index], old_pos)

            app_state.set_curve_data(self._target_curve, curve_data)
            self.executed = False
            return True

        return self._safe_execute("undoing", _undo_operation)

    @override
    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo batch point movement."""

        def _redo_operation() -> bool:
            if not self._target_curve:
                logger.error("Missing target curve for redo")
                return False

            app_state = get_application_state()
            curve_data = list(app_state.get_curve_data(self._target_curve))

            # Apply all moves using helper
            for index, _, new_pos in self.moves:
                if 0 <= index < len(curve_data):
                    curve_data[index] = self._update_point_position(curve_data[index], new_pos)

            app_state.set_curve_data(self._target_curve, curve_data)
            self.executed = True
            return True

        return self._safe_execute("redoing", _redo_operation)

    @override
    def can_merge_with(self, other: Command) -> bool:
        """Check if this batch move can be merged with another."""
        if not isinstance(other, BatchMoveCommand):
            return False

        # Can merge if moving the same set of points
        self_indices = {move[0] for move in self.moves}
        other_indices = {move[0] for move in other.moves}
        return self_indices == other_indices

    @override
    def merge_with(self, other: Command) -> Command:
        """Merge with another batch move command."""
        if not isinstance(other, BatchMoveCommand) or not self.can_merge_with(other):
            raise ValueError("Cannot merge incompatible batch moves")

        # Create new moves using original positions from self and new positions from other
        merged_moves: list[tuple[int, tuple[float, float], tuple[float, float]]] = []
        other_dict = {move[0]: move[2] for move in other.moves}  # index -> new_pos

        for index, old_pos, _ in self.moves:
            new_pos = other_dict[index]
            merged_moves.append((index, old_pos, new_pos))

        return BatchMoveCommand(
            description=f"Move {len(merged_moves)} points",
            moves=merged_moves,
        )


class SetPointStatusCommand(CurveDataCommand):
    """
    Command for changing the status of points.

    This command is used for operations that change point status,
    such as converting between keyframe, tracked, interpolated, and endframe.
    """

    def __init__(
        self,
        description: str,
        changes: Sequence[tuple[int, str, str]],  # (index, old_status, new_status)
    ) -> None:
        """
        Initialize the set point status command.

        Args:
            description: Human-readable description
            changes: List of (index, old_status, new_status) tuples
        """
        super().__init__(description)
        self.changes: list[tuple[int, str, str]] = list(changes)

    @override
    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute status changes."""

        def _execute_operation() -> bool:
            # Get active curve data
            if (result := self._get_active_curve_data()) is None:
                logger.error("No active curve")
                return False
            curve_name, curve_data = result

            # Store target curve for undo
            self._target_curve = curve_name

            # Get current curve data from ApplicationState
            curve_data = list(curve_data)

            # Apply all status changes
            for index, _, new_status in self.changes:
                if 0 <= index < len(curve_data):
                    point = curve_data[index]
                    # Update status while preserving frame, x, y
                    # Note: This intentionally normalizes 3-element to 4-element format
                    # because status operations require a status field
                    if len(point) >= 3:
                        curve_data[index] = (point[0], point[1], point[2], new_status)
                    else:
                        logger.warning(f"Point {index} has invalid format (need at least 3 elements)")
                else:
                    logger.warning(f"Point index {index} out of range")

            # Update ApplicationState with modified data
            app_state = get_application_state()
            app_state.set_curve_data(curve_name, curve_data)
            self.executed = True

            # Trigger widget update (CurveDataStore removed in Phase 6.3)
            if main_window.curve_widget:
                main_window.curve_widget.update()

            return True

        return self._safe_execute("executing", _execute_operation)

    @override
    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo status changes."""

        def _undo_operation() -> bool:
            if not self._target_curve:
                logger.error("Missing target curve for undo")
                return False

            app_state = get_application_state()

            # Get current curve data from ApplicationState
            curve_data = list(app_state.get_curve_data(self._target_curve))

            # Restore all original statuses
            for index, old_status, _ in self.changes:
                if 0 <= index < len(curve_data):
                    point = curve_data[index]
                    # Restore old status while preserving frame, x, y
                    # Note: Data is already 4-element from execute() normalization
                    if len(point) >= 3:
                        curve_data[index] = (point[0], point[1], point[2], old_status)
                    else:
                        logger.warning(f"Point {index} has invalid format (need at least 3 elements)")
                else:
                    logger.warning(f"Point index {index} out of range")

            # Update ApplicationState with restored data
            app_state.set_curve_data(self._target_curve, curve_data)
            self.executed = False

            # Trigger widget update (CurveDataStore removed in Phase 6.3)
            if main_window.curve_widget:
                main_window.curve_widget.update()

            return True

        return self._safe_execute("undoing", _undo_operation)

    @override
    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo status changes."""

        def _redo_operation() -> bool:
            if not self._target_curve:
                logger.error("Missing target curve for redo")
                return False

            app_state = get_application_state()
            curve_data = list(app_state.get_curve_data(self._target_curve))

            # Apply all status changes
            for index, _, new_status in self.changes:
                if 0 <= index < len(curve_data):
                    point = curve_data[index]
                    # Update status while preserving frame, x, y
                    # Note: This intentionally normalizes 3-element to 4-element format
                    # because status operations require a status field
                    if len(point) >= 3:
                        curve_data[index] = (point[0], point[1], point[2], new_status)
                    else:
                        logger.warning(f"Point {index} has invalid format (need at least 3 elements)")
                else:
                    logger.warning(f"Point index {index} out of range")

            # Update ApplicationState with modified data
            app_state.set_curve_data(self._target_curve, curve_data)
            self.executed = True

            # Trigger widget update (CurveDataStore removed in Phase 6.3)
            if main_window.curve_widget:
                main_window.curve_widget.update()

            return True

        return self._safe_execute("redoing", _redo_operation)

    @override
    def can_merge_with(self, other: Command) -> bool:
        """Check if this status change can be merged with another."""
        if not isinstance(other, SetPointStatusCommand):
            return False

        # Can merge if changing the same set of points
        self_indices = {change[0] for change in self.changes}
        other_indices = {change[0] for change in other.changes}
        return self_indices == other_indices

    @override
    def merge_with(self, other: Command) -> Command:
        """Merge with another status change command."""
        if not isinstance(other, SetPointStatusCommand) or not self.can_merge_with(other):
            raise ValueError("Cannot merge incompatible status changes")

        # Create new changes using original statuses from self and new statuses from other
        merged_changes: list[tuple[int, str, str]] = []
        other_dict = {change[0]: change[2] for change in other.changes}  # index -> new_status

        for index, old_status, _ in self.changes:
            new_status = other_dict[index]
            merged_changes.append((index, old_status, new_status))

        return SetPointStatusCommand(
            description=f"Change status of {len(merged_changes)} points",
            changes=merged_changes,
        )


class AddPointCommand(CurveDataCommand):
    """
    Command for adding new points to the curve.
    """

    def __init__(self, description: str, index: int, point: LegacyPointData) -> None:
        """
        Initialize the add point command.

        Args:
            description: Human-readable description
            index: Index where to insert the point
            point: The point data to add
        """
        super().__init__(description)
        self.index: int = index
        self.point: LegacyPointData = copy.deepcopy(point)

    @override
    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute point addition."""

        def _execute_operation() -> bool:
            # Get active curve data (allows empty curves!)
            if (result := self._get_active_curve_data()) is None:
                logger.error("No active curve")
                return False
            curve_name, curve_data = result

            # Store target curve for undo
            self._target_curve = curve_name

            curve_data = list(curve_data)
            if 0 <= self.index <= len(curve_data):
                curve_data.insert(self.index, self.point)
                app_state = get_application_state()
                app_state.set_curve_data(curve_name, curve_data)
                self.executed = True
                return True

            return False

        return self._safe_execute("executing", _execute_operation)

    @override
    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo point addition by removing the added point."""

        def _undo_operation() -> bool:
            if not self._target_curve:
                return False

            app_state = get_application_state()
            curve_data = list(app_state.get_curve_data(self._target_curve))

            if 0 <= self.index < len(curve_data):
                del curve_data[self.index]
                app_state.set_curve_data(self._target_curve, curve_data)
                self.executed = False
                return True

            return False

        return self._safe_execute("undoing", _undo_operation)

    @override
    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo point addition."""

        def _redo_operation() -> bool:
            if not self._target_curve:
                logger.error("Missing target curve for redo")
                return False

            app_state = get_application_state()
            curve_data = list(app_state.get_curve_data(self._target_curve))

            if 0 <= self.index <= len(curve_data):
                curve_data.insert(self.index, self.point)
                app_state.set_curve_data(self._target_curve, curve_data)
                self.executed = True
                return True

            return False

        return self._safe_execute("redoing", _redo_operation)


class ConvertToInterpolatedCommand(CurveDataCommand):
    """
    Command for converting a keyframe to an interpolated point.

    This command:
    1. Calculates the interpolated position at the keyframe's frame
    2. Updates the point's coordinates to the interpolated values
    3. Changes the status to INTERPOLATED
    """

    def __init__(
        self,
        description: str,
        index: int,
        old_point: tuple[int, float, float, str],
        new_point: tuple[int, float, float, str],
    ) -> None:
        """
        Initialize the convert to interpolated command.

        Args:
            description: Human-readable description
            index: Index of the point to convert
            old_point: Original point (frame, x, y, status)
            new_point: New interpolated point (frame, x, y, status)
        """
        super().__init__(description)
        self.index: int = index
        self.old_point: tuple[int, float, float, str] = old_point
        self.new_point: tuple[int, float, float, str] = new_point

    @override
    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute the conversion to interpolated."""

        def _execute_operation() -> bool:
            # Get active curve data
            if (result := self._get_active_curve_data()) is None:
                logger.error("No active curve")
                return False
            curve_name, curve_data = result

            # Store target curve for undo
            self._target_curve = curve_name

            curve_data = list(curve_data)
            if 0 <= self.index < len(curve_data):
                # Replace the point with the interpolated version
                curve_data[self.index] = self.new_point

                app_state = get_application_state()
                app_state.set_curve_data(curve_name, curve_data)
                self.executed = True
                return True

            return False

        return self._safe_execute("executing", _execute_operation)

    @override
    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo the conversion by restoring the original point."""

        def _undo_operation() -> bool:
            if not self._target_curve:
                return False

            app_state = get_application_state()
            curve_data = list(app_state.get_curve_data(self._target_curve))

            if 0 <= self.index < len(curve_data):
                # Restore the original point
                curve_data[self.index] = self.old_point

                app_state.set_curve_data(self._target_curve, curve_data)
                self.executed = False
                return True

            return False

        return self._safe_execute("undoing", _undo_operation)

    @override
    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo the conversion."""

        def _redo_operation() -> bool:
            if not self._target_curve:
                logger.error("Missing target curve for redo")
                return False

            app_state = get_application_state()
            curve_data = list(app_state.get_curve_data(self._target_curve))

            if 0 <= self.index < len(curve_data):
                # Replace the point with the interpolated version
                curve_data[self.index] = self.new_point

                app_state.set_curve_data(self._target_curve, curve_data)
                self.executed = True
                return True

            return False

        return self._safe_execute("redoing", _redo_operation)

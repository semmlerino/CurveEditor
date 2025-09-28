#!/usr/bin/env python
"""
Curve-specific commands for undo/redo functionality.

This module contains command implementations for all curve editing operations
including point manipulation, smoothing, filtering, and data modifications.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.service_protocols import MainWindowProtocol

from core.commands.base_command import Command
from core.logger_utils import get_logger
from core.type_aliases import CurveDataList

logger = get_logger("curve_commands")


class SetCurveDataCommand(Command):
    """
    Command to set the entire curve data.

    This is the most basic command that stores the complete before/after
    state of curve data. Used for operations that modify large portions
    of the curve.
    """

    def __init__(self, description: str, new_data: CurveDataList, old_data: CurveDataList | None = None) -> None:
        """
        Initialize the set curve data command.

        Args:
            description: Human-readable description of the operation
            new_data: The new curve data to set
            old_data: The previous curve data (captured during execution if None)
        """
        super().__init__(description)
        self.new_data = copy.deepcopy(new_data)
        self.old_data = copy.deepcopy(old_data) if old_data is not None else None

    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute the command by setting new curve data."""
        try:
            # Capture old data if not provided
            if self.old_data is None:
                if main_window.curve_widget and hasattr(main_window.curve_widget, "curve_data"):
                    self.old_data = copy.deepcopy(main_window.curve_widget.curve_data)
                else:
                    self.old_data = []

            # Set new data
            if main_window.curve_widget:
                main_window.curve_widget.set_curve_data(self.new_data)
                self.executed = True
                return True
            else:
                logger.error("No curve widget available")
                return False

        except Exception as e:
            logger.error(f"Error executing SetCurveDataCommand: {e}")
            return False

    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo by restoring the old curve data."""
        try:
            if self.old_data is not None and main_window.curve_widget:
                main_window.curve_widget.set_curve_data(self.old_data)
                self.executed = False
                return True
            else:
                logger.error("No old data or curve widget for undo")
                return False

        except Exception as e:
            logger.error(f"Error undoing SetCurveDataCommand: {e}")
            return False

    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo by setting the new curve data again."""
        return self.execute(main_window)


class SmoothCommand(Command):
    """
    Command for smoothing operations.

    Stores the specific points that were smoothed, the smoothing parameters,
    and the before/after states for those points.
    """

    def __init__(
        self,
        description: str,
        indices: list[int],
        filter_type: str,
        window_size: int,
        old_points: list[Any] | None = None,
        new_points: list[Any] | None = None,
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
        self.indices = list(indices)
        self.filter_type = filter_type
        self.window_size = window_size
        self.old_points = copy.deepcopy(old_points) if old_points else None
        self.new_points = copy.deepcopy(new_points) if new_points else None

    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute smoothing operation."""
        try:
            if not main_window.curve_widget or not hasattr(main_window.curve_widget, "curve_data"):
                logger.error("No curve widget or curve data available")
                return False

            curve_data = main_window.curve_widget.curve_data

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

            # Apply the smoothed points
            new_curve_data = list(curve_data)
            for i, idx in enumerate(self.indices):
                if i < len(self.new_points) and 0 <= idx < len(new_curve_data):
                    new_curve_data[idx] = self.new_points[i]

            # Preserve view state when updating data
            old_zoom = main_window.curve_widget.zoom_factor
            old_pan_x = main_window.curve_widget.pan_offset_x
            old_pan_y = main_window.curve_widget.pan_offset_y

            main_window.curve_widget.set_curve_data(new_curve_data)

            # Restore view state
            main_window.curve_widget.zoom_factor = old_zoom
            main_window.curve_widget.pan_offset_x = old_pan_x
            main_window.curve_widget.pan_offset_y = old_pan_y
            self.executed = True
            return True

        except Exception as e:
            logger.error(f"Error executing SmoothCommand: {e}")
            return False

    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo smoothing by restoring original points."""
        try:
            if not self.old_points or not main_window.curve_widget:
                logger.error("No old points or curve widget for undo")
                return False

            curve_data = list(main_window.curve_widget.curve_data)
            for i, idx in enumerate(self.indices):
                if i < len(self.old_points) and 0 <= idx < len(curve_data):
                    curve_data[idx] = self.old_points[i]

            # Preserve view state when updating data
            old_zoom = main_window.curve_widget.zoom_factor
            old_pan_x = main_window.curve_widget.pan_offset_x
            old_pan_y = main_window.curve_widget.pan_offset_y

            main_window.curve_widget.set_curve_data(curve_data)

            # Restore view state
            main_window.curve_widget.zoom_factor = old_zoom
            main_window.curve_widget.pan_offset_x = old_pan_x
            main_window.curve_widget.pan_offset_y = old_pan_y
            self.executed = False
            return True

        except Exception as e:
            logger.error(f"Error undoing SmoothCommand: {e}")
            return False

    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo smoothing by applying smoothed points."""
        try:
            if not self.new_points or not main_window.curve_widget:
                logger.error("No new points or curve widget for redo")
                return False

            curve_data = list(main_window.curve_widget.curve_data)
            for i, idx in enumerate(self.indices):
                if i < len(self.new_points) and 0 <= idx < len(curve_data):
                    curve_data[idx] = self.new_points[i]

            # Preserve view state when updating data
            old_zoom = main_window.curve_widget.zoom_factor
            old_pan_x = main_window.curve_widget.pan_offset_x
            old_pan_y = main_window.curve_widget.pan_offset_y

            main_window.curve_widget.set_curve_data(curve_data)

            # Restore view state
            main_window.curve_widget.zoom_factor = old_zoom
            main_window.curve_widget.pan_offset_x = old_pan_x
            main_window.curve_widget.pan_offset_y = old_pan_y
            self.executed = True
            return True

        except Exception as e:
            logger.error(f"Error redoing SmoothCommand: {e}")
            return False

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


class MovePointCommand(Command):
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
        self.index = index
        self.old_pos = old_pos
        self.new_pos = new_pos

    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute point movement."""
        try:
            if not main_window.curve_widget or not hasattr(main_window.curve_widget, "curve_data"):
                return False

            curve_data = list(main_window.curve_widget.curve_data)
            if 0 <= self.index < len(curve_data):
                point = curve_data[self.index]
                # Preserve frame and status, update x and y
                if len(point) >= 4:
                    curve_data[self.index] = (point[0], self.new_pos[0], self.new_pos[1], point[3])
                elif len(point) == 3:
                    curve_data[self.index] = (point[0], self.new_pos[0], self.new_pos[1])

                main_window.curve_widget.set_curve_data(curve_data)
                self.executed = True
                return True

            return False

        except Exception as e:
            logger.error(f"Error executing MovePointCommand: {e}")
            return False

    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo point movement."""
        try:
            if not main_window.curve_widget:
                return False

            curve_data = list(main_window.curve_widget.curve_data)
            if 0 <= self.index < len(curve_data):
                point = curve_data[self.index]
                # Restore original position
                if len(point) >= 4:
                    curve_data[self.index] = (point[0], self.old_pos[0], self.old_pos[1], point[3])
                elif len(point) == 3:
                    curve_data[self.index] = (point[0], self.old_pos[0], self.old_pos[1])

                main_window.curve_widget.set_curve_data(curve_data)
                self.executed = False
                return True

            return False

        except Exception as e:
            logger.error(f"Error undoing MovePointCommand: {e}")
            return False

    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo point movement."""
        return self.execute(main_window)

    def can_merge_with(self, other: Command) -> bool:
        """Check if this move can be merged with another move of the same point."""
        return isinstance(other, MovePointCommand) and self.index == other.index

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


class DeletePointsCommand(Command):
    """
    Command for deleting points from the curve.

    Stores the deleted points and their positions for restoration.
    """

    def __init__(self, description: str, indices: list[int], deleted_points: list[Any] | None = None) -> None:
        """
        Initialize the delete points command.

        Args:
            description: Human-readable description
            indices: Indices of points to delete
            deleted_points: The points that were deleted (captured during execution if None)
        """
        super().__init__(description)
        self.indices = sorted(indices, reverse=True)  # Delete in reverse order to maintain indices
        self.deleted_points = copy.deepcopy(deleted_points) if deleted_points else None

    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute point deletion."""
        try:
            if not main_window.curve_widget or not hasattr(main_window.curve_widget, "curve_data"):
                return False

            curve_data = list(main_window.curve_widget.curve_data)

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

            main_window.curve_widget.set_curve_data(curve_data)
            self.executed = True
            return True

        except Exception as e:
            logger.error(f"Error executing DeletePointsCommand: {e}")
            return False

    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo point deletion by restoring deleted points."""
        try:
            if not self.deleted_points or not main_window.curve_widget:
                return False

            curve_data = list(main_window.curve_widget.curve_data)

            # Insert points back in their original positions
            for idx, point in self.deleted_points:
                if 0 <= idx <= len(curve_data):
                    curve_data.insert(idx, point)

            main_window.curve_widget.set_curve_data(curve_data)
            self.executed = False
            return True

        except Exception as e:
            logger.error(f"Error undoing DeletePointsCommand: {e}")
            return False

    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo point deletion."""
        return self.execute(main_window)


class BatchMoveCommand(Command):
    """
    Command for moving multiple points at once.

    This command is used for operations that move several points simultaneously,
    such as dragging multiple selected points or nudging a selection.
    """

    def __init__(
        self,
        description: str,
        moves: list[tuple[int, tuple[float, float], tuple[float, float]]],
    ) -> None:
        """
        Initialize the batch move command.

        Args:
            description: Human-readable description
            moves: List of (index, old_pos, new_pos) tuples
        """
        super().__init__(description)
        self.moves = moves  # List of (index, old_pos, new_pos)

    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute batch point movement."""
        try:
            if not main_window.curve_widget or not hasattr(main_window.curve_widget, "curve_data"):
                return False

            curve_data = list(main_window.curve_widget.curve_data)

            # Apply all moves
            for index, _, new_pos in self.moves:
                if 0 <= index < len(curve_data):
                    point = curve_data[index]
                    # Preserve frame and status, update x and y
                    if len(point) >= 4:
                        curve_data[index] = (point[0], new_pos[0], new_pos[1], point[3])
                    elif len(point) == 3:
                        curve_data[index] = (point[0], new_pos[0], new_pos[1])

            main_window.curve_widget.set_curve_data(curve_data)
            self.executed = True
            return True

        except Exception as e:
            logger.error(f"Error executing BatchMoveCommand: {e}")
            return False

    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo batch point movement."""
        try:
            if not main_window.curve_widget:
                return False

            curve_data = list(main_window.curve_widget.curve_data)

            # Restore all original positions
            for index, old_pos, _ in self.moves:
                if 0 <= index < len(curve_data):
                    point = curve_data[index]
                    # Restore original position
                    if len(point) >= 4:
                        curve_data[index] = (point[0], old_pos[0], old_pos[1], point[3])
                    elif len(point) == 3:
                        curve_data[index] = (point[0], old_pos[0], old_pos[1])

            main_window.curve_widget.set_curve_data(curve_data)
            self.executed = False
            return True

        except Exception as e:
            logger.error(f"Error undoing BatchMoveCommand: {e}")
            return False

    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo batch point movement."""
        return self.execute(main_window)

    def can_merge_with(self, other: Command) -> bool:
        """Check if this batch move can be merged with another."""
        if not isinstance(other, BatchMoveCommand):
            return False

        # Can merge if moving the same set of points
        self_indices = {move[0] for move in self.moves}
        other_indices = {move[0] for move in other.moves}
        return self_indices == other_indices

    def merge_with(self, other: Command) -> Command:
        """Merge with another batch move command."""
        if not isinstance(other, BatchMoveCommand) or not self.can_merge_with(other):
            raise ValueError("Cannot merge incompatible batch moves")

        # Create new moves using original positions from self and new positions from other
        merged_moves = []
        other_dict = {move[0]: move[2] for move in other.moves}  # index -> new_pos

        for index, old_pos, _ in self.moves:
            new_pos = other_dict[index]
            merged_moves.append((index, old_pos, new_pos))

        return BatchMoveCommand(
            description=f"Move {len(merged_moves)} points",
            moves=merged_moves,
        )


class SetPointStatusCommand(Command):
    """
    Command for changing the status of points.

    This command is used for operations that change point status,
    such as converting between keyframe, tracked, interpolated, and endframe.
    """

    def __init__(
        self,
        description: str,
        changes: list[tuple[int, str, str]],  # (index, old_status, new_status)
    ) -> None:
        """
        Initialize the set point status command.

        Args:
            description: Human-readable description
            changes: List of (index, old_status, new_status) tuples
        """
        super().__init__(description)
        self.changes = changes

    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute status changes."""
        try:
            if not main_window.curve_widget or not hasattr(main_window.curve_widget, "curve_data"):
                return False

            curve_data = list(main_window.curve_widget.curve_data)

            # Apply all status changes
            for index, _, new_status in self.changes:
                if 0 <= index < len(curve_data):
                    point = curve_data[index]
                    # Update status, preserve other fields
                    if len(point) >= 4:
                        curve_data[index] = (point[0], point[1], point[2], new_status)
                    elif len(point) == 3:
                        curve_data[index] = (point[0], point[1], point[2], new_status)

            main_window.curve_widget.set_curve_data(curve_data)
            self.executed = True
            return True

        except Exception as e:
            logger.error(f"Error executing SetPointStatusCommand: {e}")
            return False

    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo status changes."""
        try:
            if not main_window.curve_widget:
                return False

            curve_data = list(main_window.curve_widget.curve_data)

            # Restore all original statuses
            for index, old_status, _ in self.changes:
                if 0 <= index < len(curve_data):
                    point = curve_data[index]
                    # Restore original status
                    if len(point) >= 4:
                        curve_data[index] = (point[0], point[1], point[2], old_status)
                    elif len(point) == 3:
                        curve_data[index] = (point[0], point[1], point[2], old_status)

            main_window.curve_widget.set_curve_data(curve_data)
            self.executed = False
            return True

        except Exception as e:
            logger.error(f"Error undoing SetPointStatusCommand: {e}")
            return False

    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo status changes."""
        return self.execute(main_window)

    def can_merge_with(self, other: Command) -> bool:
        """Check if this status change can be merged with another."""
        if not isinstance(other, SetPointStatusCommand):
            return False

        # Can merge if changing the same set of points
        self_indices = {change[0] for change in self.changes}
        other_indices = {change[0] for change in other.changes}
        return self_indices == other_indices

    def merge_with(self, other: Command) -> Command:
        """Merge with another status change command."""
        if not isinstance(other, SetPointStatusCommand) or not self.can_merge_with(other):
            raise ValueError("Cannot merge incompatible status changes")

        # Create new changes using original statuses from self and new statuses from other
        merged_changes = []
        other_dict = {change[0]: change[2] for change in other.changes}  # index -> new_status

        for index, old_status, _ in self.changes:
            new_status = other_dict[index]
            merged_changes.append((index, old_status, new_status))

        return SetPointStatusCommand(
            description=f"Change status of {len(merged_changes)} points",
            changes=merged_changes,
        )


class AddPointCommand(Command):
    """
    Command for adding new points to the curve.
    """

    def __init__(self, description: str, index: int, point: Any) -> None:
        """
        Initialize the add point command.

        Args:
            description: Human-readable description
            index: Index where to insert the point
            point: The point data to add
        """
        super().__init__(description)
        self.index = index
        self.point = copy.deepcopy(point)

    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute point addition."""
        try:
            if not main_window.curve_widget or not hasattr(main_window.curve_widget, "curve_data"):
                return False

            curve_data = list(main_window.curve_widget.curve_data)
            if 0 <= self.index <= len(curve_data):
                curve_data.insert(self.index, self.point)
                main_window.curve_widget.set_curve_data(curve_data)
                self.executed = True
                return True

            return False

        except Exception as e:
            logger.error(f"Error executing AddPointCommand: {e}")
            return False

    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo point addition by removing the added point."""
        try:
            if not main_window.curve_widget:
                return False

            curve_data = list(main_window.curve_widget.curve_data)
            if 0 <= self.index < len(curve_data):
                del curve_data[self.index]
                main_window.curve_widget.set_curve_data(curve_data)
                self.executed = False
                return True

            return False

        except Exception as e:
            logger.error(f"Error undoing AddPointCommand: {e}")
            return False

    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo point addition."""
        return self.execute(main_window)

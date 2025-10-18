"""Smooth command implementation for curve point smoothing."""

import logging
from typing import Any

from commands.base import Command

logger = logging.getLogger(__name__)


class SmoothCommand(Command):
    """Command to apply smoothing to curve points.

    This command encapsulates the smoothing operation, allowing it to be
    undone and redone. It stores both the original and smoothed data.
    """

    def __init__(
        self,
        curve_widget: Any,  # CurveViewWidget
        selected_indices: list[int],
        window_size: int,
        description: str = "Smooth curve points",
    ):
        """Initialize the smooth command.

        Args:
            curve_widget: The curve widget to operate on
            selected_indices: Indices of points to smooth
            window_size: Size of the smoothing window
            description: Human-readable description
        """
        super().__init__(description)
        self.curve_widget = curve_widget
        self.selected_indices = selected_indices
        self.window_size = window_size

        # Store original data for undo
        self.original_data: list[tuple[int, float, float] | tuple[int, float, float, str]] | None = None
        self.smoothed_data: list[tuple[int, float, float] | tuple[int, float, float, str]] | None = None

    def execute(self) -> bool:
        """Execute the smoothing operation.

        Returns:
            True if execution was successful, False otherwise
        """
        try:
            if self.curve_widget is None:
                logger.warning("No curve widget available for smoothing")
                return False

            # Get the current curve data
            curve_data = getattr(self.curve_widget, "curve_data", [])
            if not curve_data:
                logger.warning("No curve data to smooth")
                return False

            # Store original data for undo (make a deep copy)
            self.original_data = list(curve_data)

            # Get data service for smoothing
            from services import get_data_service

            data_service = get_data_service()
            if not data_service:
                logger.error("Data service not available for smoothing")
                return False

            # Extract points to smooth
            points_to_smooth = [curve_data[i] for i in self.selected_indices]

            # Apply smoothing
            smoothed_points = data_service.smooth_moving_average(points_to_smooth, self.window_size)

            # Create new curve data with smoothed points
            new_curve_data = list(curve_data)
            for i, idx in enumerate(self.selected_indices):
                if i < len(smoothed_points):
                    new_curve_data[idx] = smoothed_points[i]

            # Store smoothed data for potential redo
            self.smoothed_data = new_curve_data

            # Apply the new data
            self.curve_widget.set_curve_data(new_curve_data)

            # Mark as modified
            parent_method = getattr(self.curve_widget, "parent", None)
            if parent_method is not None and callable(parent_method):
                parent = parent_method()
                if parent is not None:
                    state_manager = getattr(parent, "state_manager", None)
                    if state_manager is not None:
                        state_manager.is_modified = True

            logger.info(f"Applied smoothing to {len(self.selected_indices)} points (window size: {self.window_size})")
            return True

        except Exception as e:
            logger.error(f"Error executing smooth command: {e}")
            return False

    def undo(self) -> bool:
        """Undo the smoothing operation.

        Returns:
            True if undo was successful, False otherwise
        """
        try:
            if self.original_data is None:
                logger.error("No original data stored for undo")
                return False

            if self.curve_widget is None:
                logger.warning("Curve widget no longer available")
                return False

            # Restore original data
            self.curve_widget.set_curve_data(self.original_data)

            # Mark as modified
            parent_method = getattr(self.curve_widget, "parent", None)
            if parent_method is not None and callable(parent_method):
                parent = parent_method()
                if parent is not None:
                    state_manager = getattr(parent, "state_manager", None)
                    if state_manager is not None:
                        state_manager.is_modified = True

            logger.info(f"Undid smoothing of {len(self.selected_indices)} points")
            return True

        except Exception as e:
            logger.error(f"Error undoing smooth command: {e}")
            return False

    def redo(self) -> bool:
        """Redo the smoothing operation.

        Returns:
            True if redo was successful, False otherwise
        """
        try:
            if self.smoothed_data is None:
                # If we don't have cached smoothed data, re-execute
                return self.execute()

            if self.curve_widget is None:
                logger.warning("Curve widget no longer available")
                return False

            # Apply smoothed data
            self.curve_widget.set_curve_data(self.smoothed_data)

            # Mark as modified
            parent_method = getattr(self.curve_widget, "parent", None)
            if parent_method is not None and callable(parent_method):
                parent = parent_method()
                if parent is not None:
                    state_manager = getattr(parent, "state_manager", None)
                    if state_manager is not None:
                        state_manager.is_modified = True

            logger.info(f"Redid smoothing of {len(self.selected_indices)} points")
            return True

        except Exception as e:
            logger.error(f"Error redoing smooth command: {e}")
            return False

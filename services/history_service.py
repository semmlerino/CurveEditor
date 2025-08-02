#!/usr/bin/env python

"""
HistoryService: Manages undo/redo functionality for the application.

This service handles:
1. Adding current application state to the history stack
2. Navigating through history with undo/redo operations
3. Restoring application state from saved history
4. Managing history size limits
"""

import copy
from typing import Any

from core.protocols import HistoryContainerProtocol


class HistoryService:
    """Service for managing application history stack and undo/redo operations."""

    @staticmethod
    def add_to_history(main_window: HistoryContainerProtocol) -> None:
        """Add current state to history.

        This method:
        1. If not at end of history, truncates history at current position
        2. Adds current application state to history stack
        3. Updates history index
        4. Enforces history size limits
        5. Updates UI button states

        Args:
            main_window: The main application window containing state
        """
        # If we're not at the end of the history, truncate it
        if main_window.history_index < len(main_window.history) - 1:
            main_window.history = main_window.history[: main_window.history_index + 1]

        # Add current state to history
        current_state = {
            "curve_data": copy.deepcopy(main_window.curve_data),
            "point_name": main_window.point_name,
            "point_color": main_window.point_color,
        }

        main_window.history.append(current_state)
        main_window.history_index = len(main_window.history) - 1

        # Limit history size
        if len(main_window.history) > main_window.max_history_size:
            main_window.history = main_window.history[1:]
            main_window.history_index = len(main_window.history) - 1

        # Update undo/redo buttons
        HistoryService.update_history_buttons(main_window)

    @staticmethod
    def update_history_buttons(main_window: HistoryContainerProtocol) -> None:
        """Update the state of undo/redo buttons based on history position.

        Args:
            main_window: The main application window containing undo/redo buttons
        """
        main_window.undo_button.setEnabled(main_window.history_index > 0)
        main_window.redo_button.setEnabled(main_window.history_index < len(main_window.history) - 1)

    @staticmethod
    def undo_action(main_window: HistoryContainerProtocol) -> None:
        """Undo the last action by moving back in history.

        Args:
            main_window: The main application window
        """
        if main_window.history_index <= 0:
            return

        main_window.history_index -= 1
        HistoryService.restore_state(main_window, main_window.history[main_window.history_index])
        HistoryService.update_history_buttons(main_window)

    @staticmethod
    def undo(main_window: HistoryContainerProtocol) -> None:
        """Undo the last action by moving back in history.

        Alias for undo_action to maintain API compatibility.

        Args:
            main_window: The main application window
        """
        HistoryService.undo_action(main_window)

    @staticmethod
    def redo_action(main_window: HistoryContainerProtocol) -> None:
        """Redo the previously undone action by moving forward in history.

        Args:
            main_window: The main application window
        """
        if main_window.history_index >= len(main_window.history) - 1:
            return

        main_window.history_index += 1
        HistoryService.restore_state(main_window, main_window.history[main_window.history_index])
        HistoryService.update_history_buttons(main_window)

    @staticmethod
    def redo(main_window: HistoryContainerProtocol) -> None:
        """Redo the previously undone action by moving forward in history.

        Alias for redo_action to maintain API compatibility.

        Args:
            main_window: The main application window
        """
        HistoryService.redo_action(main_window)

    @staticmethod
    def restore_state(main_window: HistoryContainerProtocol, state: dict[str, Any]) -> None:
        """Restore application state from history.

        Applies saved state to the main window and updates the curve view
        while preserving view position.

        Args:
            main_window: The main application window
            state: The saved application state to restore
        """
        main_window.curve_data = copy.deepcopy(state["curve_data"])
        main_window.point_name = state["point_name"]
        main_window.point_color = state["point_color"]

        # Update view without resetting zoom/pan
        if hasattr(main_window.curve_view, "set_curve_data"):
            main_window.curve_view.set_curve_data(main_window.curve_data)
        elif hasattr(main_window.curve_view, "setPoints"):
            # Get image dimensions if available, else use defaults
            image_width = getattr(main_window, "image_width", 0)
            image_height = getattr(main_window, "image_height", 0)

            main_window.curve_view.setPoints(main_window.curve_data, image_width, image_height, preserve_view=True)
        else:
            main_window.curve_view.update()

        # Update info
        main_window.info_label.setText(f"Loaded: {main_window.point_name} ({len(main_window.curve_data)} frames)")

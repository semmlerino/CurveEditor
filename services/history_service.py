#!/usr/bin/env python

"""
HistoryService: Manages undo/redo functionality for the application.

This service handles:
1. Adding current application state to the history stack
2. Navigating through history with undo/redo operations
3. Restoring application state from saved history
4. Managing history size limits
"""

from typing import Any, Protocol

class HistoryContainerProtocol(Protocol):
    """Protocol for objects that can be saved and restored in history."""
    
    curve_data: list
    point_name: str
    point_color: str
    
    def restore_state(self, state: dict) -> None:
        """Restore state from history."""
        ...

class HistoryCommand(Protocol):
    """Protocol for history commands that can be undone and redone."""

    def undo(self, main_window: HistoryContainerProtocol) -> None:
        """Undo this command."""
        ...

    def redo(self, main_window: HistoryContainerProtocol) -> None:
        """Redo this command."""
        ...

class StateSnapshot:
    """Efficient state snapshot using minimal data storage while maintaining dict-like interface."""

    def __init__(self, curve_data, point_name: str, point_color: str):
        # Performance optimization: Store shallow copy instead of deepcopy
        self._data = {
            "curve_data": list(curve_data),  # Shallow copy - tuples are immutable
            "point_name": point_name,
            "point_color": point_color,
        }

    def __getitem__(self, key: str) -> object:
        """Support dict-like access for backward compatibility."""
        return self._data[key]

    def __setitem__(self, key: str, value: object) -> None:
        """Support dict-like assignment for backward compatibility."""
        self._data[key] = value

    def get(self, key: str, default: object = None) -> object:
        """Support dict.get() method for backward compatibility."""
        return self._data.get(key, default)

    def keys(self):
        """Support dict.keys() for backward compatibility."""
        return self._data.keys()

    def values(self):
        """Support dict.values() for backward compatibility."""
        return self._data.values()

    def items(self):
        """Support dict.items() for backward compatibility."""
        return self._data.items()

class HistoryService:
    """Service for managing application history stack and undo/redo operations."""

    def add_to_history(self, main_window: HistoryContainerProtocol) -> None:
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

        # Performance optimization: Use efficient state snapshot instead of deepcopy
        current_state = StateSnapshot(main_window.curve_data, main_window.point_name, main_window.point_color)

        main_window.history.append(current_state)
        main_window.history_index = len(main_window.history) - 1

        # Limit history size
        if len(main_window.history) > main_window.max_history_size:
            main_window.history = main_window.history[1:]
            main_window.history_index = len(main_window.history) - 1

        # Update undo/redo buttons
        self.update_history_buttons(main_window)

        # Update workflow state - data has been modified
        if hasattr(main_window, "services") and hasattr(main_window.services, "workflow_state"):
            main_window.services.workflow_state.on_data_modified(main_window, "Edit operation")

    def update_history_buttons(self, main_window: HistoryContainerProtocol) -> None:
        """Update the state of undo/redo buttons based on history position.

        Args:
            main_window: The main application window containing undo/redo buttons
        """
        main_window.ui_components.undo_button.setEnabled(main_window.history_index > 0)
        main_window.ui_components.redo_button.setEnabled(main_window.history_index < len(main_window.history) - 1)

    def undo_action(self, main_window: HistoryContainerProtocol) -> None:
        """Undo the last action by moving back in history.

        Args:
            main_window: The main application window
        """
        if main_window.history_index <= 0:
            return

        main_window.history_index -= 1
        self.restore_state(main_window, main_window.history[main_window.history_index])
        self.update_history_buttons(main_window)

    def undo(self, main_window: HistoryContainerProtocol) -> None:
        """Undo the last action by moving back in history.

        Alias for undo_action to maintain API compatibility.

        Args:
            main_window: The main application window
        """
        self.undo_action(main_window)

    def redo_action(self, main_window: HistoryContainerProtocol) -> None:
        """Redo the previously undone action by moving forward in history.

        Args:
            main_window: The main application window
        """
        if main_window.history_index >= len(main_window.history) - 1:
            return

        main_window.history_index += 1
        self.restore_state(main_window, main_window.history[main_window.history_index])
        self.update_history_buttons(main_window)

    def redo(self, main_window: HistoryContainerProtocol) -> None:
        """Redo the previously undone action by moving forward in history.

        Alias for redo_action to maintain API compatibility.

        Args:
            main_window: The main application window
        """
        self.redo_action(main_window)

    def restore_state(self, main_window: HistoryContainerProtocol, state: Any) -> None:
        """Restore application state from history.

        Applies saved state to the main window and updates the curve view
        while preserving view position.

        Args:
            main_window: The main application window
            state: The saved application state to restore (StateSnapshot or legacy dict)
        """
        # Performance optimization: Always use shallow copy instead of deepcopy
        # StateSnapshot provides dict-like interface, so this works for both formats
        main_window.curve_data = list(state["curve_data"])  # Shallow copy instead of deepcopy
        main_window.point_name = state["point_name"]
        main_window.point_color = state["point_color"]

        # Update view without resetting zoom/pan
        try:
            if hasattr(main_window.curve_view, "set_points"):
                main_window.curve_view.set_points(main_window.curve_data)
            elif hasattr(main_window.curve_view, "setPoints"):
                # Get image dimensions if available, else use defaults
                image_width = getattr(main_window, "image_width", 0)
                image_height = getattr(main_window, "image_height", 0)

                main_window.curve_view.setPoints(main_window.curve_data, image_width, image_height, preserve_view=True)
            else:
                main_window.curve_view.update()
        except AttributeError:
            # Fallback if all methods are missing (edge case in testing)
            if hasattr(main_window.curve_view, "update"):
                main_window.curve_view.update()

        # Update info using unified status service
        # Note: Status service integration would go here
        
    def save_state(self, main_window: HistoryContainerProtocol) -> None:
        """Save current state to history.
        
        Alias for add_to_history for backward compatibility.
        
        Args:
            main_window: The main application window containing state
        """
        self.add_to_history(main_window)

# Module-level singleton instance
_instance = HistoryService()

def get_history_service() -> HistoryService:
    """Get the singleton instance of HistoryService."""
    return _instance

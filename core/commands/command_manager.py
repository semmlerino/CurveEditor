#!/usr/bin/env python
"""
Command Manager for undo/redo functionality.

This module provides the CommandManager class that manages the execution,
undo, and redo of commands throughout the application.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow

from core.commands.base_command import Command
from core.logger_utils import get_logger

logger = get_logger("command_manager")


class CommandManager:
    """
    Manages command execution and undo/redo history.

    The CommandManager maintains a history of executed commands and provides
    methods to undo and redo operations. It also handles command merging
    and memory management.
    """

    def __init__(self, max_history_size: int = 100) -> None:
        """
        Initialize the command manager.

        Args:
            max_history_size: Maximum number of commands to keep in history
        """
        self._history: list[Command] = []
        self._current_index: int = -1
        self._max_history_size = max_history_size
        self._merge_timeout: float = 1.0  # Seconds to allow command merging

        logger.info(f"CommandManager initialized with max_history_size={max_history_size}")

    def execute_command(self, command: Command, main_window: MainWindow) -> bool:
        """
        Execute a command and add it to the history.

        Args:
            command: Command to execute
            main_window: Reference to the main application window

        Returns:
            True if command executed successfully, False otherwise
        """
        try:
            # Try to merge with the last command if possible
            if self._can_merge_with_last_command(command):
                last_command = self._history[self._current_index]
                merged_command = last_command.merge_with(command)
                if merged_command:
                    # Replace the last command with the merged one
                    if merged_command.execute(main_window):
                        self._history[self._current_index] = merged_command
                        logger.debug(f"Merged and executed command: {merged_command}")
                        return True
                    else:
                        logger.error(f"Failed to execute merged command: {merged_command}")
                        return False

            # Execute the command
            if not command.execute(main_window):
                logger.error(f"Failed to execute command: {command}")
                return False

            # Clear any redo history
            if self._current_index < len(self._history) - 1:
                self._history = self._history[: self._current_index + 1]

            # Add command to history
            self._history.append(command)
            self._current_index += 1

            # Enforce history size limit
            self._enforce_history_limit()

            # Update UI state
            self._update_ui_state(main_window)

            logger.info(
                f"Command executed and added to history: {command} "
                f"(history size: {len(self._history)}, index: {self._current_index})"
            )
            return True

        except Exception as e:
            logger.error(f"Error executing command {command}: {e}")
            return False

    def add_executed_command(self, command: Command, main_window: MainWindow) -> bool:
        """
        Add an already-executed command to history without re-executing it.

        This is used for operations where the action has already been performed
        (e.g., during interactive dragging) and we just need to record it for undo.

        Args:
            command: Command that has already been executed
            main_window: Reference to the main application window

        Returns:
            True if command was successfully added, False otherwise
        """
        try:
            # Command should already be marked as executed
            if not command.executed:
                logger.warning(f"Command {command} is not marked as executed")
                command.executed = True

            # Clear any redo history
            if self._current_index < len(self._history) - 1:
                self._history = self._history[: self._current_index + 1]

            # Add command to history
            self._history.append(command)
            self._current_index += 1

            # Enforce history size limit
            self._enforce_history_limit()

            # Update UI state
            self._update_ui_state(main_window)

            logger.info(
                f"Already-executed command added to history: {command} "
                f"(history size: {len(self._history)}, index: {self._current_index})"
            )
            return True

        except Exception as e:
            logger.error(f"Error adding executed command {command}: {e}")
            return False

    def undo(self, main_window: MainWindow) -> bool:
        """
        Undo the last command.

        Args:
            main_window: Reference to the main application window

        Returns:
            True if undo was successful, False otherwise
        """
        logger.info(
            f"Undo requested: history size={len(self._history)}, "
            f"current_index={self._current_index}, can_undo={self.can_undo()}"
        )

        if not self.can_undo():
            logger.warning("Cannot undo: no commands in history")
            return False

        try:
            command = self._history[self._current_index]
            if command.undo(main_window):
                self._current_index -= 1
                self._update_ui_state(main_window)
                logger.debug(f"Undid command: {command}")
                return True
            else:
                logger.error(f"Failed to undo command: {command}")
                return False

        except Exception as e:
            logger.error(f"Error undoing command: {e}")
            return False

    def redo(self, main_window: MainWindow) -> bool:
        """
        Redo the next command.

        Args:
            main_window: Reference to the main application window

        Returns:
            True if redo was successful, False otherwise
        """
        if not self.can_redo():
            logger.debug("Cannot redo: no commands to redo")
            return False

        try:
            self._current_index += 1
            command = self._history[self._current_index]
            if command.redo(main_window):
                self._update_ui_state(main_window)
                logger.debug(f"Redid command: {command}")
                return True
            else:
                logger.error(f"Failed to redo command: {command}")
                self._current_index -= 1  # Revert index change
                return False

        except Exception as e:
            logger.error(f"Error redoing command: {e}")
            self._current_index -= 1  # Revert index change
            return False

    def can_undo(self) -> bool:
        """
        Check if undo is possible.

        Returns:
            True if there are commands that can be undone
        """
        return self._current_index >= 0

    def can_redo(self) -> bool:
        """
        Check if redo is possible.

        Returns:
            True if there are commands that can be redone
        """
        return self._current_index < len(self._history) - 1

    def clear_history(self, main_window: MainWindow) -> None:
        """
        Clear all command history.

        Args:
            main_window: Reference to the main application window
        """
        self._history.clear()
        self._current_index = -1
        self._update_ui_state(main_window)
        logger.info("Command history cleared")

    def get_history_info(self) -> dict[str, object]:
        """
        Get information about the command history.

        Returns:
            Dictionary with history statistics
        """
        total_memory = sum(cmd.get_memory_usage() for cmd in self._history)
        return {
            "total_commands": len(self._history),
            "current_index": self._current_index,
            "can_undo": self.can_undo(),
            "can_redo": self.can_redo(),
            "memory_usage_bytes": total_memory,
            "memory_usage_mb": total_memory / (1024 * 1024),
        }

    def get_undo_description(self) -> str | None:
        """
        Get description of the command that would be undone.

        Returns:
            Description string or None if no undo available
        """
        if self.can_undo():
            return self._history[self._current_index].description
        return None

    def get_redo_description(self) -> str | None:
        """
        Get description of the command that would be redone.

        Returns:
            Description string or None if no redo available
        """
        if self.can_redo():
            return self._history[self._current_index + 1].description
        return None

    def _can_merge_with_last_command(self, command: Command) -> bool:
        """
        Check if a command can be merged with the last command in history.

        Args:
            command: Command to check for merging

        Returns:
            True if commands can be merged
        """
        if self._current_index < 0:
            return False

        last_command = self._history[self._current_index]
        return last_command.can_merge_with(command)

    def _enforce_history_limit(self) -> None:
        """Enforce the maximum history size limit."""
        while len(self._history) > self._max_history_size:
            self._history.pop(0)
            self._current_index -= 1
            self._current_index = max(-1, self._current_index)

    def _update_ui_state(self, main_window: MainWindow) -> None:
        """
        Update UI state to reflect current undo/redo availability.

        Args:
            main_window: Reference to the main application window
        """
        try:
            # Update state manager if available
            if hasattr(main_window, "state_manager") and main_window.state_manager:
                main_window.state_manager.set_history_state(
                    can_undo=self.can_undo(),
                    can_redo=self.can_redo(),
                    position=self._current_index,
                    size=len(self._history),
                )

            # Update main window UI state (includes QActions)
            if hasattr(main_window, "update_ui_state"):
                main_window.update_ui_state()

            # Update UI buttons if available - use safe access pattern
            try:
                ui = getattr(main_window, "ui", None)
                if ui:
                    # Look for undo/redo buttons in various UI sections
                    undo_button = getattr(ui, "undo_button", None)
                    if undo_button and hasattr(undo_button, "setEnabled"):
                        undo_button.setEnabled(self.can_undo())

                    redo_button = getattr(ui, "redo_button", None)
                    if redo_button and hasattr(redo_button, "setEnabled"):
                        redo_button.setEnabled(self.can_redo())
            except AttributeError:
                # UI structure may vary, ignore button update errors
                pass

        except Exception as e:
            logger.warning(f"Error updating UI state: {e}")

    def __str__(self) -> str:
        """String representation of the command manager."""
        return f"CommandManager(commands={len(self._history)}, index={self._current_index})"

    def __repr__(self) -> str:
        """Detailed string representation of the command manager."""
        return (
            f"CommandManager(history_size={len(self._history)}, "
            f"current_index={self._current_index}, "
            f"can_undo={self.can_undo()}, "
            f"can_redo={self.can_redo()})"
        )

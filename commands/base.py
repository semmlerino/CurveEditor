"""Base command pattern implementation for undoable operations."""

import logging
from abc import ABC, abstractmethod
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)


class Command(ABC):
    """Abstract base class for all undoable commands.

    Each command encapsulates an operation that can be executed, undone, and redone.
    Commands should be self-contained and store all necessary state for undo/redo.
    """

    def __init__(self, description: str = ""):
        """Initialize the command.

        Args:
            description: Human-readable description of the command for logging/UI
        """
        self.description = description
        self._executed = False

    @abstractmethod
    def execute(self) -> bool:
        """Execute the command.

        Returns:
            True if execution was successful, False otherwise
        """
        pass

    @abstractmethod
    def undo(self) -> bool:
        """Undo the command.

        Returns:
            True if undo was successful, False otherwise
        """
        pass

    def redo(self) -> bool:
        """Redo the command.

        Default implementation just calls execute again.
        Override if redo logic differs from initial execution.

        Returns:
            True if redo was successful, False otherwise
        """
        return self.execute()

    @property
    def is_executed(self) -> bool:
        """Check if the command has been executed."""
        return self._executed

    def __str__(self) -> str:
        """String representation of the command."""
        return self.description or self.__class__.__name__


class CommandManager:
    """Manages command history and provides undo/redo functionality.

    This class maintains two stacks:
    - undo_stack: Commands that can be undone
    - redo_stack: Commands that can be redone
    """

    def __init__(self, max_history: int = 100):
        """Initialize the command manager.

        Args:
            max_history: Maximum number of commands to keep in history
        """
        self.undo_stack: deque[Command] = deque(maxlen=max_history)
        self.redo_stack: deque[Command] = deque(maxlen=max_history)
        self.max_history = max_history
        self._is_executing = False  # Prevent recursive execution

    def execute(self, command: Command) -> bool:
        """Execute a command and add it to the undo stack.

        Args:
            command: The command to execute

        Returns:
            True if execution was successful, False otherwise
        """
        if self._is_executing:
            logger.warning("Command execution already in progress, skipping")
            return False

        self._is_executing = True
        try:
            # Execute the command
            success = command.execute()

            if success:
                # Add to undo stack
                self.undo_stack.append(command)
                command._executed = True

                # Clear redo stack (new commands invalidate redo history)
                self.redo_stack.clear()

                logger.info(f"Executed command: {command}")
                return True
            else:
                logger.warning(f"Command execution failed: {command}")
                return False

        except Exception as e:
            logger.error(f"Error executing command {command}: {e}")
            return False
        finally:
            self._is_executing = False

    def undo(self) -> bool:
        """Undo the last executed command.

        Returns:
            True if undo was successful, False otherwise
        """
        if not self.can_undo():
            logger.debug("Nothing to undo")
            return False

        command = self.undo_stack.pop()

        try:
            success = command.undo()

            if success:
                # Move to redo stack
                self.redo_stack.append(command)
                logger.info(f"Undid command: {command}")
                return True
            else:
                # If undo failed, put it back
                self.undo_stack.append(command)
                logger.warning(f"Failed to undo command: {command}")
                return False

        except Exception as e:
            # If undo failed, put it back
            self.undo_stack.append(command)
            logger.error(f"Error undoing command {command}: {e}")
            return False

    def redo(self) -> bool:
        """Redo the last undone command.

        Returns:
            True if redo was successful, False otherwise
        """
        if not self.can_redo():
            logger.debug("Nothing to redo")
            return False

        command = self.redo_stack.pop()

        try:
            success = command.redo()

            if success:
                # Move back to undo stack
                self.undo_stack.append(command)
                logger.info(f"Redid command: {command}")
                return True
            else:
                # If redo failed, put it back
                self.redo_stack.append(command)
                logger.warning(f"Failed to redo command: {command}")
                return False

        except Exception as e:
            # If redo failed, put it back
            self.redo_stack.append(command)
            logger.error(f"Error redoing command {command}: {e}")
            return False

    def can_undo(self) -> bool:
        """Check if there are commands to undo."""
        return len(self.undo_stack) > 0

    def can_redo(self) -> bool:
        """Check if there are commands to redo."""
        return len(self.redo_stack) > 0

    def clear_history(self) -> None:
        """Clear all command history."""
        self.undo_stack.clear()
        self.redo_stack.clear()
        logger.info("Cleared command history")

    def get_undo_description(self) -> str | None:
        """Get description of the command that would be undone."""
        if self.can_undo():
            return str(self.undo_stack[-1])
        return None

    def get_redo_description(self) -> str | None:
        """Get description of the command that would be redone."""
        if self.can_redo():
            return str(self.redo_stack[-1])
        return None

    def get_history_info(self) -> dict[str, Any]:
        """Get information about the command history.

        Returns:
            Dictionary with history information
        """
        return {
            "undo_count": len(self.undo_stack),
            "redo_count": len(self.redo_stack),
            "max_history": self.max_history,
            "can_undo": self.can_undo(),
            "can_redo": self.can_redo(),
            "next_undo": self.get_undo_description(),
            "next_redo": self.get_redo_description(),
        }

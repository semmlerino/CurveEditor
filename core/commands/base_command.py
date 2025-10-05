#!/usr/bin/env python
"""
Base Command classes for undo/redo functionality.

This module provides the foundation for the command pattern implementation
used throughout the CurveEditor application for undo/redo operations.
"""
# pyright: reportImportCycles=false

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from typing_extensions import override

if TYPE_CHECKING:
    from protocols.ui import MainWindowProtocol

from core.logger_utils import get_logger

logger = get_logger("commands")


class Command(ABC):
    """
    Abstract base class for all undoable commands.

    Each command encapsulates a single operation that can be executed,
    undone, and redone. Commands store all necessary data to perform
    these operations without external dependencies.
    """

    def __init__(self, description: str) -> None:
        """
        Initialize the command.

        Args:
            description: Human-readable description of the command
        """
        self.description: str = description
        self.executed: bool = False

    @abstractmethod
    def execute(self, main_window: MainWindowProtocol) -> bool:
        """
        Execute the command.

        Args:
            main_window: Reference to the main application window

        Returns:
            True if execution was successful, False otherwise
        """
        pass

    @abstractmethod
    def undo(self, main_window: MainWindowProtocol) -> bool:
        """
        Undo the command.

        Args:
            main_window: Reference to the main application window

        Returns:
            True if undo was successful, False otherwise
        """
        pass

    @abstractmethod
    def redo(self, main_window: MainWindowProtocol) -> bool:
        """
        Redo the command (same as execute but may have optimizations).

        Args:
            main_window: Reference to the main application window

        Returns:
            True if redo was successful, False otherwise
        """
        pass

    def can_merge_with(self, other: Command) -> bool:
        """
        Check if this command can be merged with another command.

        This is used for optimization to merge consecutive similar operations
        (e.g., multiple point movements) into a single undo step.

        Args:
            other: Another command to potentially merge with

        Returns:
            True if commands can be merged, False otherwise
        """
        return False

    def merge_with(self, other: Command) -> Command:
        """
        Merge this command with another command.

        Args:
            other: Another command to merge with

        Returns:
            A new command representing the merged operation

        Raises:
            NotImplementedError: If merging is not supported
        """
        raise NotImplementedError("Command merging not implemented")

    def get_memory_usage(self) -> int:
        """
        Get approximate memory usage of this command in bytes.

        Returns:
            Estimated memory usage in bytes
        """
        import sys

        return sys.getsizeof(self)

    @override
    def __str__(self) -> str:
        """String representation of the command."""
        return f"{self.__class__.__name__}: {self.description}"

    @override
    def __repr__(self) -> str:
        """Detailed string representation of the command."""
        return f"{self.__class__.__name__}(description='{self.description}', executed={self.executed})"


class CompositeCommand(Command):
    """
    A command that groups multiple commands together.

    This is useful for operations that consist of multiple atomic steps
    that should be undone/redone as a single unit.
    """

    def __init__(self, description: str, commands: list[Command] | None = None) -> None:
        """
        Initialize the composite command.

        Args:
            description: Human-readable description of the composite operation
            commands: List of commands to group together
        """
        super().__init__(description)
        self.commands: list[Command] = commands or []

    def add_command(self, command: Command) -> None:
        """
        Add a command to the composite.

        Args:
            command: Command to add
        """
        self.commands.append(command)

    @override
    def execute(self, main_window: MainWindowProtocol) -> bool:
        """
        Execute all commands in order.

        If any command fails, attempts to undo all previously executed commands.

        Args:
            main_window: Reference to the main application window

        Returns:
            True if all commands executed successfully, False otherwise
        """
        executed_commands: list[Command] = []

        try:
            for command in self.commands:
                if not command.execute(main_window):
                    # Rollback previously executed commands
                    for rollback_cmd in reversed(executed_commands):
                        _ = rollback_cmd.undo(main_window)
                    return False
                executed_commands.append(command)

            self.executed = True
            return True

        except Exception as e:
            logger.error(f"Error executing composite command: {e}")
            # Rollback previously executed commands
            for rollback_cmd in reversed(executed_commands):
                try:
                    _ = rollback_cmd.undo(main_window)
                except Exception as rollback_error:
                    logger.error(f"Error during rollback: {rollback_error}")
            return False

    @override
    def undo(self, main_window: MainWindowProtocol) -> bool:
        """
        Undo all commands in reverse order.

        Args:
            main_window: Reference to the main application window

        Returns:
            True if all commands were undone successfully, False otherwise
        """
        success = True
        for command in reversed(self.commands):
            if command.executed and not command.undo(main_window):
                success = False
                logger.error(f"Failed to undo command: {command}")

        if success:
            self.executed = False

        return success

    @override
    def redo(self, main_window: MainWindowProtocol) -> bool:
        """
        Redo all commands in order.

        Args:
            main_window: Reference to the main application window

        Returns:
            True if all commands were redone successfully, False otherwise
        """
        return self.execute(main_window)

    @override
    def get_memory_usage(self) -> int:
        """
        Get total memory usage of all contained commands.

        Returns:
            Estimated total memory usage in bytes
        """
        return sum(cmd.get_memory_usage() for cmd in self.commands) + super().get_memory_usage()

    @override
    def __str__(self) -> str:
        """String representation of the composite command."""
        return f"CompositeCommand: {self.description} ({len(self.commands)} commands)"


class NullCommand(Command):
    """
    A command that does nothing.

    Used as a placeholder or for testing purposes.
    """

    def __init__(self) -> None:
        """Initialize the null command."""
        super().__init__("No operation")

    @override
    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Do nothing and report success."""
        self.executed = True
        return True

    @override
    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Do nothing and report success."""
        self.executed = False
        return True

    @override
    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Do nothing and report success."""
        return self.execute(main_window)

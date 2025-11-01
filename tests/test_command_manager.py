#!/usr/bin/env python
"""Tests for CommandManager.

Comprehensive test suite covering undo/redo functionality including:
- Command execution and history management
- Undo and redo operations
- History size limits and overflow handling
- Command merging
- Undo/redo state tracking
- UI state updates

Focus Areas:
- History pointer management
- Redo history clearing on new command
- Maximum history size enforcement
- Can undo/redo state accuracy
- Multiple command sequences
- History info retrieval
"""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none



import pytest

from typing_extensions import override

from core.commands.command_manager import CommandManager
from tests.test_helpers import MockMainWindow


class SimpleTestCommand:
    """Simple test command for testing CommandManager."""

    executed: bool = False

    def __init__(self, description: str = "TestCommand", should_fail: bool = False):
        """Initialize test command.

        Args:
            description: Command description
            should_fail: Whether execute should fail
        """
        self.description = description
        self.should_fail = should_fail
        self.executed = False
        self.undo_called = False
        self.redo_called = False
        self.execute_count = 0
        self.undo_count = 0
        self.redo_count = 0

    def execute(self, main_window):
        """Execute command."""
        self.execute_count += 1
        self.executed = True
        return not self.should_fail

    def undo(self, main_window):
        """Undo command."""
        self.undo_count += 1
        self.undo_called = True
        return True

    def redo(self, main_window):
        """Redo command."""
        self.redo_count += 1
        self.redo_called = True
        return True

    def can_merge_with(self, other) -> bool:
        """Check if this command can be merged with another."""
        return False  # Don't merge by default

    def merge_with(self, other):
        """Try to merge with another command."""
        raise NotImplementedError("Command merging not implemented")

    def get_memory_usage(self) -> int:
        """Get approximate memory usage of this command in bytes."""
        import sys
        return sys.getsizeof(self)

    @override
    def __str__(self) -> str:
        """String representation."""
        return self.description

    @override
    def __repr__(self) -> str:
        """Repr."""
        return f"SimpleTestCommand({self.description})"


class MergeableTestCommand(SimpleTestCommand):
    """Test command that can be merged."""

    def __init__(self, description: str = "MergeableCommand", merge_target=None):
        """Initialize mergeable command.

        Args:
            description: Command description
            merge_target: Command to merge with (if compatible)
        """
        super().__init__(description)
        self.merge_target = merge_target
        self.merged_with = None

    @override
    def can_merge_with(self, other) -> bool:
        """Check if this command can be merged with another."""
        return isinstance(other, MergeableTestCommand)

    @override
    def merge_with(self, other):
        """Merge with another command if compatible."""
        if isinstance(other, MergeableTestCommand):
            # Create merged command
            merged = MergeableTestCommand(
                f"{self.description}+{other.description}"
            )
            merged.merged_with = other
            return merged
        raise NotImplementedError("Cannot merge with non-MergeableTestCommand")


@pytest.fixture
def command_manager() -> CommandManager:
    """Create CommandManager instance."""
    return CommandManager(max_history_size=100)


@pytest.fixture
def main_window() -> MockMainWindow:
    """Create mock main window."""
    return MockMainWindow()


@pytest.fixture
def test_command() -> SimpleTestCommand:
    """Create simple test command."""
    return SimpleTestCommand("TestCommand")


class TestCommandManagerInitialization:
    """Test CommandManager initialization."""

    def test_manager_initializes_with_default_size(self) -> None:
        """Test CommandManager initializes with default history size.

        Verifies:
        - Manager created successfully
        - Default max_history_size is 100
        - Empty history on init
        """
        manager = CommandManager()
        assert manager._max_history_size == 100
        assert manager._current_index == -1
        assert len(manager._history) == 0

    def test_manager_initializes_with_custom_size(self) -> None:
        """Test CommandManager initializes with custom history size.

        Verifies:
        - Custom max_history_size accepted
        - Applied correctly
        """
        manager = CommandManager(max_history_size=50)
        assert manager._max_history_size == 50

    def test_manager_cannot_undo_initially(
        self, command_manager: CommandManager, main_window: MockMainWindow
    ) -> None:
        """Test that undo is not possible with empty history.

        Verifies:
        - can_undo() returns False
        - undo() fails gracefully
        """
        assert command_manager.can_undo() is False
        assert command_manager.undo(main_window) is False

    def test_manager_cannot_redo_initially(
        self, command_manager: CommandManager, main_window: MockMainWindow
    ) -> None:
        """Test that redo is not possible with empty history.

        Verifies:
        - can_redo() returns False
        - redo() fails gracefully
        """
        assert command_manager.can_redo() is False
        assert command_manager.redo(main_window) is False


class TestCommandExecution:
    """Test command execution and history management."""

    def test_execute_command_adds_to_history(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
        test_command: SimpleTestCommand,
    ) -> None:
        """Test that executed command is added to history.

        Verifies:
        - Command executed
        - Added to history
        - History index updated
        """
        # Act
        result = command_manager.execute_command(test_command, main_window)

        # Assert
        assert result is True
        assert test_command.executed is True
        assert command_manager._current_index == 0
        assert len(command_manager._history) == 1

    def test_execute_command_marks_command_as_executed(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
    ) -> None:
        """Test that command.executed flag is set.

        Verifies:
        - Command has executed = True after execute_command
        """
        # Arrange
        command = SimpleTestCommand()
        assert command.executed is False

        # Act
        command_manager.execute_command(command, main_window)

        # Assert
        assert command.executed is True

    def test_execute_multiple_commands_builds_history(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
    ) -> None:
        """Test executing multiple commands builds history sequence.

        Verifies:
        - All commands added to history
        - Index increments correctly
        - History size matches command count
        """
        # Arrange
        cmd1 = SimpleTestCommand("Cmd1")
        cmd2 = SimpleTestCommand("Cmd2")
        cmd3 = SimpleTestCommand("Cmd3")

        # Act
        assert command_manager.execute_command(cmd1, main_window) is True
        assert command_manager.execute_command(cmd2, main_window) is True
        assert command_manager.execute_command(cmd3, main_window) is True

        # Assert
        assert command_manager._current_index == 2
        assert len(command_manager._history) == 3
        assert command_manager._history[0] is cmd1
        assert command_manager._history[1] is cmd2
        assert command_manager._history[2] is cmd3

    def test_execute_command_failure_not_added_to_history(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
    ) -> None:
        """Test that failed command is not added to history.

        Verifies:
        - Failed command not in history
        - Index unchanged
        - History size unchanged
        """
        # Arrange
        cmd_fail = SimpleTestCommand("FailCommand", should_fail=True)

        # Act
        result = command_manager.execute_command(cmd_fail, main_window)

        # Assert
        assert result is False
        assert cmd_fail.executed is True
        assert len(command_manager._history) == 0
        assert command_manager._current_index == -1

    def test_execute_command_clears_redo_history(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
    ) -> None:
        """Test that new command clears redo history.

        Verifies:
        - Execute undo to create redo history
        - Execute new command clears redo entries
        - History truncated at current index
        """
        # Arrange
        cmd1 = SimpleTestCommand("Cmd1")
        cmd2 = SimpleTestCommand("Cmd2")
        cmd3 = SimpleTestCommand("Cmd3")

        # Execute commands
        command_manager.execute_command(cmd1, main_window)
        command_manager.execute_command(cmd2, main_window)
        command_manager.execute_command(cmd3, main_window)
        assert len(command_manager._history) == 3

        # Undo to create redo history
        command_manager.undo(main_window)  # Index = 1
        assert command_manager._current_index == 1
        assert len(command_manager._history) == 3

        # Act - Execute new command
        cmd4 = SimpleTestCommand("Cmd4")
        command_manager.execute_command(cmd4, main_window)

        # Assert
        assert command_manager._current_index == 2
        assert len(command_manager._history) == 3  # cmd1, cmd2, cmd4
        assert command_manager._history[2] is cmd4


class TestUndoOperations:
    """Test undo functionality."""

    def test_undo_single_command(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
        test_command: SimpleTestCommand,
    ) -> None:
        """Test undoing a single command.

        Verifies:
        - Undo succeeds
        - Command.undo() called
        - Index decremented
        """
        # Arrange
        command_manager.execute_command(test_command, main_window)
        assert command_manager._current_index == 0

        # Act
        result = command_manager.undo(main_window)

        # Assert
        assert result is True
        assert test_command.undo_count == 1
        assert command_manager._current_index == -1

    def test_undo_multiple_commands_in_sequence(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
    ) -> None:
        """Test undoing multiple commands in sequence.

        Verifies:
        - Each undo decrements index
        - Commands undone in reverse order
        - Index tracks correctly
        """
        # Arrange
        cmd1 = SimpleTestCommand("Cmd1")
        cmd2 = SimpleTestCommand("Cmd2")
        cmd3 = SimpleTestCommand("Cmd3")

        command_manager.execute_command(cmd1, main_window)
        command_manager.execute_command(cmd2, main_window)
        command_manager.execute_command(cmd3, main_window)

        # Act - Undo all
        assert command_manager.undo(main_window) is True
        assert command_manager._current_index == 1
        assert cmd3.undo_count == 1

        assert command_manager.undo(main_window) is True
        assert command_manager._current_index == 0
        assert cmd2.undo_count == 1

        assert command_manager.undo(main_window) is True
        assert command_manager._current_index == -1
        assert cmd1.undo_count == 1

        # Assert - Can't undo further
        assert command_manager.undo(main_window) is False

    def test_undo_stops_at_history_start(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
        test_command: SimpleTestCommand,
    ) -> None:
        """Test that undo stops at beginning of history.

        Verifies:
        - Index can't go below -1
        - Second undo returns False
        """
        # Arrange
        command_manager.execute_command(test_command, main_window)

        # Act
        assert command_manager.undo(main_window) is True
        result = command_manager.undo(main_window)

        # Assert
        assert result is False
        assert command_manager._current_index == -1

    def test_undo_marks_can_undo_false_at_start(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
        test_command: SimpleTestCommand,
    ) -> None:
        """Test that can_undo is False when at history start.

        Verifies:
        - can_undo() returns False after full undo
        """
        # Arrange
        command_manager.execute_command(test_command, main_window)
        command_manager.undo(main_window)

        # Assert
        assert command_manager.can_undo() is False


class TestRedoOperations:
    """Test redo functionality."""

    def test_redo_single_command(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
        test_command: SimpleTestCommand,
    ) -> None:
        """Test redoing a single command.

        Verifies:
        - Redo succeeds after undo
        - Command.redo() called
        - Index incremented
        """
        # Arrange
        command_manager.execute_command(test_command, main_window)
        command_manager.undo(main_window)

        # Act
        result = command_manager.redo(main_window)

        # Assert
        assert result is True
        assert test_command.redo_count == 1
        assert command_manager._current_index == 0

    def test_redo_multiple_commands_in_sequence(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
    ) -> None:
        """Test redoing multiple commands in sequence.

        Verifies:
        - Each redo increments index
        - Commands redone in order
        - Correct sequence maintained
        """
        # Arrange
        cmd1 = SimpleTestCommand("Cmd1")
        cmd2 = SimpleTestCommand("Cmd2")
        cmd3 = SimpleTestCommand("Cmd3")

        command_manager.execute_command(cmd1, main_window)
        command_manager.execute_command(cmd2, main_window)
        command_manager.execute_command(cmd3, main_window)

        # Undo all
        command_manager.undo(main_window)
        command_manager.undo(main_window)
        command_manager.undo(main_window)
        assert command_manager._current_index == -1

        # Act - Redo all
        assert command_manager.redo(main_window) is True
        assert command_manager._current_index == 0
        assert cmd1.redo_count == 1

        assert command_manager.redo(main_window) is True
        assert command_manager._current_index == 1
        assert cmd2.redo_count == 1

        assert command_manager.redo(main_window) is True
        assert command_manager._current_index == 2
        assert cmd3.redo_count == 1

    def test_redo_stops_at_history_end(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
        test_command: SimpleTestCommand,
    ) -> None:
        """Test that redo stops at end of history.

        Verifies:
        - Can't redo beyond last command
        - Returns False
        """
        # Arrange
        command_manager.execute_command(test_command, main_window)
        command_manager.undo(main_window)
        command_manager.redo(main_window)

        # Act
        result = command_manager.redo(main_window)

        # Assert
        assert result is False
        assert command_manager._current_index == 0

    def test_redo_marks_can_redo_false_at_end(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
        test_command: SimpleTestCommand,
    ) -> None:
        """Test that can_redo is False when at history end.

        Verifies:
        - can_redo() returns False after full redo
        """
        # Arrange
        command_manager.execute_command(test_command, main_window)
        command_manager.undo(main_window)
        command_manager.redo(main_window)

        # Assert
        assert command_manager.can_redo() is False


class TestHistoryManagement:
    """Test history size and limit enforcement."""

    def test_enforce_history_limit_with_overflow(self) -> None:
        """Test that history size is limited.

        Verifies:
        - History limited to max_history_size
        - Oldest commands removed
        """
        # Arrange
        manager = CommandManager(max_history_size=5)
        main_window = MockMainWindow()

        # Act - Add more commands than limit
        for i in range(10):
            cmd = SimpleTestCommand(f"Cmd{i}")
            manager.execute_command(cmd, main_window)

        # Assert
        assert len(manager._history) <= 5
        assert manager._current_index == 4

    def test_history_limit_enforced_after_each_command(self) -> None:
        """Test that history limit checked after every command.

        Verifies:
        - Size never exceeds max during normal usage
        """
        # Arrange
        manager = CommandManager(max_history_size=3)
        main_window = MockMainWindow()

        # Act
        for i in range(5):
            cmd = SimpleTestCommand(f"Cmd{i}")
            manager.execute_command(cmd, main_window)
            # Check after each
            assert len(manager._history) <= 3

        # Assert
        assert len(manager._history) == 3

    def test_clear_history(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
    ) -> None:
        """Test clearing history.

        Verifies:
        - clear_history() empties history
        - Index reset to -1
        """
        # Arrange
        for i in range(3):
            cmd = SimpleTestCommand(f"Cmd{i}")
            command_manager.execute_command(cmd, main_window)

        # Act
        command_manager.clear_history(main_window)

        # Assert
        assert len(command_manager._history) == 0
        assert command_manager._current_index == -1


class TestCanUndoRedo:
    """Test can_undo and can_redo state tracking."""

    def test_can_undo_true_with_history(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
        test_command: SimpleTestCommand,
    ) -> None:
        """Test can_undo returns True when undo available.

        Verifies:
        - can_undo() = True after execute
        """
        # Arrange
        command_manager.execute_command(test_command, main_window)

        # Assert
        assert command_manager.can_undo() is True

    def test_can_redo_true_after_undo(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
        test_command: SimpleTestCommand,
    ) -> None:
        """Test can_redo returns True after undo.

        Verifies:
        - can_redo() = True after undo
        """
        # Arrange
        command_manager.execute_command(test_command, main_window)
        command_manager.undo(main_window)

        # Assert
        assert command_manager.can_redo() is True

    def test_can_redo_false_after_new_command(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
    ) -> None:
        """Test can_redo returns False after new command clears redo.

        Verifies:
        - can_redo() = False after new command
        """
        # Arrange
        cmd1 = SimpleTestCommand("Cmd1")
        cmd2 = SimpleTestCommand("Cmd2")

        command_manager.execute_command(cmd1, main_window)
        command_manager.undo(main_window)
        assert command_manager.can_redo() is True

        # Act - New command clears redo history
        command_manager.execute_command(cmd2, main_window)

        # Assert
        assert command_manager.can_redo() is False


class TestAddExecutedCommand:
    """Test add_executed_command for already-executed operations."""

    def test_add_executed_command_adds_to_history(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
    ) -> None:
        """Test adding already-executed command to history.

        Verifies:
        - Command added without re-executing
        - execute() not called (assumed done externally)
        """
        # Arrange
        cmd = SimpleTestCommand("AlreadyDone")
        cmd.executed = True

        # Act
        result = command_manager.add_executed_command(cmd, main_window)

        # Assert
        assert result is True
        assert len(command_manager._history) == 1
        assert command_manager._current_index == 0

    def test_add_executed_command_marks_executed(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
    ) -> None:
        """Test that add_executed_command marks command as executed.

        Verifies:
        - command.executed set to True if not already
        """
        # Arrange
        cmd = SimpleTestCommand("NotMarked")
        assert cmd.executed is False

        # Act
        command_manager.add_executed_command(cmd, main_window)

        # Assert
        assert cmd.executed is True


class TestCommandDescriptions:
    """Test command description retrieval."""

    def test_get_undo_description(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
    ) -> None:
        """Test getting description of command to undo.

        Verifies:
        - Returns correct description
        - Empty when nothing to undo
        """
        # Arrange
        cmd = SimpleTestCommand("TestAction")
        command_manager.execute_command(cmd, main_window)

        # Act
        desc = command_manager.get_undo_description()

        # Assert
        assert desc == "TestAction"

    def test_get_undo_description_empty(
        self, command_manager: CommandManager
    ) -> None:
        """Test get_undo_description with empty history.

        Verifies:
        - Returns None when no undo available
        """
        # Act
        desc = command_manager.get_undo_description()

        # Assert
        assert desc is None

    def test_get_redo_description(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
    ) -> None:
        """Test getting description of command to redo.

        Verifies:
        - Returns correct description
        - Empty when nothing to redo
        """
        # Arrange
        cmd = SimpleTestCommand("TestAction")
        command_manager.execute_command(cmd, main_window)
        command_manager.undo(main_window)

        # Act
        desc = command_manager.get_redo_description()

        # Assert
        assert desc == "TestAction"

    def test_get_redo_description_empty(
        self, command_manager: CommandManager, main_window: MockMainWindow
    ) -> None:
        """Test get_redo_description with no redo available.

        Verifies:
        - Returns None when no redo available
        """
        # Act
        desc = command_manager.get_redo_description()

        # Assert
        assert desc is None


class TestHistoryInfo:
    """Test history information retrieval."""

    def test_get_history_info(
        self,
        command_manager: CommandManager,
        main_window: MockMainWindow,
    ) -> None:
        """Test getting history information.

        Verifies:
        - History info contains size, index, can_undo, can_redo
        """
        # Arrange
        cmd1 = SimpleTestCommand("Cmd1")
        cmd2 = SimpleTestCommand("Cmd2")
        command_manager.execute_command(cmd1, main_window)
        command_manager.execute_command(cmd2, main_window)

        # Act
        info = command_manager.get_history_info()

        # Assert - Verify actual keys returned by get_history_info()
        assert "total_commands" in info
        assert "current_index" in info
        assert "can_undo" in info
        assert "can_redo" in info
        assert "memory_usage_bytes" in info
        assert "memory_usage_mb" in info
        # Verify values
        assert info["total_commands"] == 2
        assert info["current_index"] == 1
        assert info["can_undo"] is True
        assert info["can_redo"] is False

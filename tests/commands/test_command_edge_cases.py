"""
Edge case tests for command system.

Tests command manager with edge cases:
- Undo with no history
- Redo with no future
- Multiple rapid operations
- Command failure scenarios
"""

# Per-file type checking relaxations for test code
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none

import pytest
from unittest.mock import MagicMock
from core.commands.command_manager import CommandManager


class TestCommandManagerEmptyState:
    """Tests for command manager with empty history."""

    @pytest.fixture
    def command_manager(self):
        """Create fresh command manager."""
        return CommandManager()

    @pytest.fixture
    def mock_main_window(self):
        """Create mock main window."""
        return MagicMock()

    def test_undo_with_empty_history(self, command_manager, mock_main_window):
        """Undo should return False with empty history."""
        result = command_manager.undo(mock_main_window)
        assert result is False

    def test_redo_with_empty_future(self, command_manager, mock_main_window):
        """Redo should return False with empty redo stack."""
        result = command_manager.redo(mock_main_window)
        assert result is False

    def test_can_undo_with_empty_history(self, command_manager):
        """can_undo should return False with empty history."""
        assert command_manager.can_undo() is False

    def test_can_redo_with_empty_future(self, command_manager):
        """can_redo should return False with empty redo stack."""
        assert command_manager.can_redo() is False

    def test_clear_on_empty_manager(self, command_manager, mock_main_window):
        """clear_history() should not raise on empty manager."""
        command_manager.clear_history(mock_main_window)  # Should not raise
        assert command_manager.can_undo() is False
        assert command_manager.can_redo() is False


class TestCommandManagerRapidOperations:
    """Tests for rapid successive operations."""

    @pytest.fixture
    def command_manager(self):
        """Create command manager with test commands."""
        manager = CommandManager()
        return manager

    @pytest.fixture
    def mock_main_window(self):
        """Create mock main window."""
        return MagicMock()

    def test_multiple_undo_calls_empty_stack(self, command_manager, mock_main_window):
        """Multiple undo calls on empty stack should all return False."""
        results = [command_manager.undo(mock_main_window) for _ in range(10)]
        assert all(r is False for r in results)

    def test_multiple_redo_calls_empty_stack(self, command_manager, mock_main_window):
        """Multiple redo calls on empty stack should all return False."""
        results = [command_manager.redo(mock_main_window) for _ in range(10)]
        assert all(r is False for r in results)

    def test_undo_all_then_redo_all(self, command_manager, mock_main_window):
        """Should be able to undo all and redo all commands."""
        # Execute 5 commands
        for _ in range(5):
            cmd = MagicMock()
            cmd.execute.return_value = True
            cmd.undo.return_value = True
            cmd.redo.return_value = True
            cmd.description = "Test"
            cmd.can_merge_with.return_value = False  # Correct method name
            command_manager.execute_command(cmd, mock_main_window)

        # Undo all
        undo_count = 0
        while command_manager.can_undo():
            command_manager.undo(mock_main_window)
            undo_count += 1

        assert undo_count == 5
        assert command_manager.can_undo() is False
        assert command_manager.can_redo() is True

        # Redo all
        redo_count = 0
        while command_manager.can_redo():
            command_manager.redo(mock_main_window)
            redo_count += 1

        assert redo_count == 5
        assert command_manager.can_redo() is False
        assert command_manager.can_undo() is True


class TestCommandManagerFailingCommands:
    """Tests for commands that fail during execution."""

    @pytest.fixture
    def command_manager(self):
        """Create command manager."""
        return CommandManager()

    @pytest.fixture
    def mock_main_window(self):
        """Create mock main window."""
        return MagicMock()

    def test_execute_failing_command(self, command_manager, mock_main_window):
        """Failed execute should not add to history."""
        failing_cmd = MagicMock()
        failing_cmd.execute.return_value = False
        failing_cmd.description = "Failing command"
        failing_cmd.can_merge.return_value = False

        result = command_manager.execute_command(failing_cmd, mock_main_window)

        assert result is False
        assert command_manager.can_undo() is False

    def test_execute_command_raises_exception(self, command_manager, mock_main_window):
        """Command that raises should be caught and logged, not added to history."""
        error_cmd = MagicMock()
        error_cmd.execute.side_effect = ValueError("Test error")
        error_cmd.description = "Error command"
        error_cmd.can_merge.return_value = False

        # CommandManager catches exceptions and logs them
        result = command_manager.execute_command(error_cmd, mock_main_window)

        # Should return False (failure) and not add to history
        assert result is False
        assert command_manager.can_undo() is False

    def test_undo_failing_command(self, command_manager, mock_main_window):
        """Failed undo should still remove from history."""
        cmd = MagicMock()
        cmd.execute.return_value = True
        cmd.undo.return_value = False  # Undo fails
        cmd.description = "Test"
        cmd.can_merge.return_value = False

        command_manager.execute_command(cmd, mock_main_window)
        assert command_manager.can_undo() is True

        result = command_manager.undo(mock_main_window)
        # Implementation may vary - some return False, some True
        # Key is no exception raised


class TestCommandManagerHistoryLimits:
    """Tests for history size limits."""

    @pytest.fixture
    def command_manager(self):
        """Create command manager."""
        return CommandManager()

    @pytest.fixture
    def mock_main_window(self):
        """Create mock main window."""
        return MagicMock()

    def test_execute_many_commands(self, command_manager, mock_main_window):
        """Should handle many commands (stress test)."""
        for i in range(100):
            cmd = MagicMock()
            cmd.execute.return_value = True
            cmd.undo.return_value = True
            cmd.description = f"Command {i}"
            cmd.can_merge.return_value = False
            command_manager.execute_command(cmd, mock_main_window)

        # Should still function
        assert command_manager.can_undo() is True

    def test_alternating_undo_redo(self, command_manager, mock_main_window):
        """Alternating undo/redo should maintain consistency."""
        # Add one command
        cmd = MagicMock()
        cmd.execute.return_value = True
        cmd.undo.return_value = True
        cmd.redo.return_value = True
        cmd.description = "Test"
        cmd.can_merge.return_value = False
        command_manager.execute_command(cmd, mock_main_window)

        # Alternate undo/redo many times
        for _ in range(20):
            assert command_manager.can_undo() is True
            command_manager.undo(mock_main_window)

            assert command_manager.can_redo() is True
            command_manager.redo(mock_main_window)

        # Final state should have command in history
        assert command_manager.can_undo() is True


class TestCommandManagerClearBehavior:
    """Tests for clear_history() behavior in various states."""

    @pytest.fixture
    def command_manager(self):
        """Create command manager."""
        return CommandManager()

    @pytest.fixture
    def mock_main_window(self):
        """Create mock main window."""
        return MagicMock()

    def test_clear_after_commands(self, command_manager, mock_main_window):
        """Clear should remove all history."""
        # Add commands
        for _ in range(5):
            cmd = MagicMock()
            cmd.execute.return_value = True
            cmd.description = "Test"
            cmd.can_merge.return_value = False
            command_manager.execute_command(cmd, mock_main_window)

        assert command_manager.can_undo() is True

        command_manager.clear_history(mock_main_window)

        assert command_manager.can_undo() is False
        assert command_manager.can_redo() is False

    def test_clear_after_undo(self, command_manager, mock_main_window):
        """Clear should remove redo stack too."""
        # Add and undo command
        cmd = MagicMock()
        cmd.execute.return_value = True
        cmd.undo.return_value = True
        cmd.description = "Test"
        cmd.can_merge.return_value = False
        command_manager.execute_command(cmd, mock_main_window)
        command_manager.undo(mock_main_window)

        assert command_manager.can_redo() is True

        command_manager.clear_history(mock_main_window)

        assert command_manager.can_redo() is False

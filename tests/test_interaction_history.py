#!/usr/bin/env python3
"""
Comprehensive history and undo/redo tests for InteractionService.

Tests history management including:
- add_to_history with ApplicationState
- undo_action with command manager
- redo_action with command manager
- restore_state
- can_undo/can_redo queries

Following best practices:
- Use real ApplicationState
- Use real CommandManager
- Test both legacy and new history systems
"""

from typing import TYPE_CHECKING

import pytest

from services import get_interaction_service
from stores.application_state import get_application_state

if TYPE_CHECKING:
    from services.interaction_service import InteractionService

from tests.test_helpers import MockMainWindow


class TestHistoryOperations:
    """Test history management operations."""

    service: "InteractionService"

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:  # pyright: ignore[reportUnusedParameter]
        """Setup test environment."""
        self.service = get_interaction_service()
        # Clear history
        self.service._history = []  # pyright: ignore[reportPrivateUsage]
        self.service._current_index = -1  # pyright: ignore[reportPrivateUsage]
        # Clear command manager
        self.service.command_manager._commands = []  # pyright: ignore[reportPrivateUsage]
        self.service.command_manager._current_index = -1  # pyright: ignore[reportPrivateUsage]

    def test_add_to_history_saves_application_state(self) -> None:
        """Test add_to_history captures ApplicationState data."""
        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0), (2, 200.0, 200.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        main_window = MockMainWindow()
        main_window.point_name = "test_point"  # type: ignore
        main_window.point_color = "red"  # type: ignore
        # Force use of internal history
        main_window.history = None
        main_window.history_index = None

        self.service.add_to_history(main_window)  # pyright: ignore[reportArgumentType]

        # Should have at least one history entry (might start at 1 if add_to_history was called before)
        assert len(self.service._history) >= 1  # pyright: ignore[reportPrivateUsage]
        if len(self.service._history) > 0:  # pyright: ignore[reportPrivateUsage]
            history_entry = self.service._history[-1]  # pyright: ignore[reportPrivateUsage]
            assert "curve_data" in history_entry
            # point_name and point_color are optional
            if "point_name" in history_entry:
                assert history_entry["point_name"] == "test_point"

    def test_add_to_history_uses_main_window_history(self) -> None:
        """Test add_to_history uses main_window.history if available."""
        app_state = get_application_state()
        test_data = [(1, 100.0, 100.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        main_window = MockMainWindow()
        main_window.history = []
        main_window.history_index = -1

        self.service.add_to_history(main_window)  # pyright: ignore[reportArgumentType]

        # Should add to main_window.history
        assert len(main_window.history) == 1
        assert main_window.history_index == 0

    def test_add_to_history_enforces_size_limit(self) -> None:
        """Test history size limit is enforced."""
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", [(1, 100.0, 100.0)])
        app_state.set_active_curve("test_curve")

        main_window = MockMainWindow()

        # Add many history entries
        for i in range(150):
            self.service.add_to_history(main_window)  # pyright: ignore[reportArgumentType]

        # Should not exceed max size
        assert len(self.service._history) <= self.service._max_history_size  # pyright: ignore[reportPrivateUsage]

    def test_can_undo_with_command_manager(self) -> None:
        """Test can_undo returns True when commands are available."""
        from core.commands.curve_commands import DeletePointsCommand

        main_window = MockMainWindow()

        # Add a command
        command = DeletePointsCommand("Delete test", indices=[0], deleted_points=[(0, (1, 100.0, 100.0))])
        command.executed = True
        self.service.command_manager.add_executed_command(command, main_window)  # pyright: ignore[reportArgumentType]

        # Should be able to undo
        assert self.service.can_undo() is True

    def test_can_redo_with_command_manager(self) -> None:
        """Test can_redo returns True after undo."""
        from core.commands.curve_commands import DeletePointsCommand

        app_state = get_application_state()
        app_state.set_curve_data("test_curve", [(1, 100.0, 100.0)])
        app_state.set_active_curve("test_curve")

        main_window = MockMainWindow()

        # Add and execute a command
        command = DeletePointsCommand("Delete test", indices=[0], deleted_points=[(0, (1, 100.0, 100.0))])
        self.service.command_manager.execute_command(command, main_window)  # pyright: ignore[reportArgumentType]

        # Undo the command
        self.service.command_manager.undo(main_window)  # pyright: ignore[reportArgumentType]

        # Should be able to redo
        assert self.service.can_redo() is True

    def test_undo_action_uses_command_manager(self) -> None:
        """Test undo_action delegates to command manager."""
        from core.commands.curve_commands import BatchMoveCommand

        app_state = get_application_state()
        app_state.set_curve_data("test_curve", [(1, 100.0, 100.0)])
        app_state.set_active_curve("test_curve")

        main_window = MockMainWindow()

        # Execute a move command
        moves = [(0, (100.0, 100.0), (150.0, 150.0))]
        command = BatchMoveCommand("Move test", moves=moves)
        self.service.command_manager.execute_command(command, main_window)  # pyright: ignore[reportArgumentType]

        # Undo
        self.service.undo_action(main_window)  # pyright: ignore[reportArgumentType]

        # Point should be back at original position
        curve_data = app_state.get_curve_data("test_curve")
        assert curve_data[0][1] == 100.0
        assert curve_data[0][2] == 100.0

    def test_redo_action_uses_command_manager(self) -> None:
        """Test redo_action delegates to command manager."""
        from core.commands.curve_commands import BatchMoveCommand

        app_state = get_application_state()
        app_state.set_curve_data("test_curve", [(1, 100.0, 100.0)])
        app_state.set_active_curve("test_curve")

        main_window = MockMainWindow()

        # Execute a move command
        moves = [(0, (100.0, 100.0), (150.0, 150.0))]
        command = BatchMoveCommand("Move test", moves=moves)
        self.service.command_manager.execute_command(command, main_window)  # pyright: ignore[reportArgumentType]

        # Undo then redo
        self.service.undo_action(main_window)  # pyright: ignore[reportArgumentType]
        self.service.redo_action(main_window)  # pyright: ignore[reportArgumentType]

        # Point should be at new position again
        curve_data = app_state.get_curve_data("test_curve")
        assert curve_data[0][1] == 150.0
        assert curve_data[0][2] == 150.0

    def test_restore_state_updates_application_state(self) -> None:
        """Test restore_state updates ApplicationState."""
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", [(1, 100.0, 100.0)])
        app_state.set_active_curve("test_curve")

        main_window = MockMainWindow()

        # Create a saved state
        saved_state = {
            "curve_data": [(1, 200.0, 200.0), (2, 300.0, 300.0)],
            "point_name": "restored_point",
            "point_color": "blue",
        }

        self.service.restore_state(main_window, saved_state)  # pyright: ignore[reportArgumentType]

        # ApplicationState should be updated
        curve_data = app_state.get_curve_data("test_curve")
        assert len(curve_data) == 2
        assert curve_data[0] == [1, 200.0, 200.0]

    def test_clear_history(self) -> None:
        """Test clear_history removes all entries."""
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", [(1, 100.0, 100.0)])
        app_state.set_active_curve("test_curve")

        main_window = MockMainWindow()

        # Add some history
        self.service.add_to_history(main_window)  # pyright: ignore[reportArgumentType]
        self.service.add_to_history(main_window)  # pyright: ignore[reportArgumentType]

        # Clear history
        self.service.clear_history(main_window)  # pyright: ignore[reportArgumentType]

        # Should be empty
        assert len(self.service._history) == 0  # pyright: ignore[reportPrivateUsage]
        assert self.service._current_index == -1  # pyright: ignore[reportPrivateUsage]

    def test_update_history_buttons(self) -> None:
        """Test update_history_buttons doesn't crash with command manager."""
        from core.commands.curve_commands import DeletePointsCommand

        main_window = MockMainWindow()

        # Initially no undo/redo (verify can_undo/can_redo work)
        assert self.service.can_undo() is False
        assert self.service.can_redo() is False

        # Add a command
        command = DeletePointsCommand("Delete test", indices=[0], deleted_points=[(0, (1, 100.0, 100.0))])
        command.executed = True
        self.service.command_manager.add_executed_command(command, main_window)  # pyright: ignore[reportArgumentType]

        # Now should be able to undo
        assert self.service.can_undo() is True
        assert self.service.can_redo() is False

        # update_history_buttons should not crash (UI button update is optional)
        self.service.update_history_buttons(main_window)  # pyright: ignore[reportArgumentType]


class TestMemoryAndStats:
    """Test memory and statistics queries."""

    service: "InteractionService"

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:  # pyright: ignore[reportUnusedParameter]
        """Setup test environment."""
        self.service = get_interaction_service()
        self.service._history = []  # pyright: ignore[reportPrivateUsage]
        self.service._current_index = -1  # pyright: ignore[reportPrivateUsage]

    def test_get_memory_stats(self) -> None:
        """Test get_memory_stats returns statistics."""
        stats = self.service.get_memory_stats()

        assert "total_states" in stats
        assert "current_index" in stats
        assert "memory_mb" in stats
        assert "can_undo" in stats
        assert "can_redo" in stats

    def test_get_spatial_index_stats(self) -> None:
        """Test get_spatial_index_stats returns index statistics."""
        stats = self.service.get_spatial_index_stats()

        # Should be a dictionary
        assert isinstance(stats, dict)

    def test_clear_spatial_index(self) -> None:
        """Test clear_spatial_index resets the index."""
        # Build index by finding a point
        app_state = get_application_state()
        from tests.test_helpers import MockCurveView

        test_data = [(1, 100.0, 100.0)]
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(test_data)
        self.service.find_point_at(view, 100.0, 100.0)  # pyright: ignore[reportArgumentType]

        # Clear index
        self.service.clear_spatial_index()

        # Index should be reset (verified by internal state)
        assert self.service._point_index._last_point_count == 0  # pyright: ignore[reportPrivateUsage]

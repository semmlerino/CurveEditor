#!/usr/bin/env python3
"""
Tests for curve command classes - undo/redo functionality.

This test module provides comprehensive coverage of all curve manipulation commands,
testing execute, undo, and redo operations with proper state management.
Follows the testing guide patterns for Qt components and command testing.
"""

import copy
from unittest.mock import Mock

import pytest

from core.commands.curve_commands import (
    AddPointCommand,
    BatchMoveCommand,
    DeletePointsCommand,
    MovePointCommand,
    SetCurveDataCommand,
    SetPointStatusCommand,
    SmoothCommand,
)
from core.type_aliases import CurveDataList


class MockDataService:
    """Mock data service for testing smoothing operations."""

    def smooth_moving_average(self, points: CurveDataList, window_size: int) -> CurveDataList:
        """Mock moving average smoothing."""
        # Return points with slightly different Y values to simulate smoothing
        result = []
        for i, point in enumerate(points):
            if len(point) >= 3:
                smoothed_y = point[2] + 0.1  # Simple smoothing simulation
                if len(point) == 3:
                    result.append((point[0], point[1], smoothed_y))
                else:
                    result.append((point[0], point[1], smoothed_y, point[3]))
            else:
                result.append(point)
        return result

    def filter_median(self, points: CurveDataList, window_size: int) -> CurveDataList:
        """Mock median filter."""
        result = []
        for i, point in enumerate(points):
            if len(point) >= 3:
                filtered_y = point[2] + 0.2  # Simple filter simulation
                if len(point) == 3:
                    result.append((point[0], point[1], filtered_y))
                else:
                    result.append((point[0], point[1], filtered_y, point[3]))
            else:
                result.append(point)
        return result

    def filter_butterworth(self, points: CurveDataList, order: int = 2) -> CurveDataList:
        """Mock butterworth filter."""
        result = []
        for i, point in enumerate(points):
            if len(point) >= 3:
                filtered_y = point[2] + 0.3  # Simple filter simulation
                if len(point) == 3:
                    result.append((point[0], point[1], filtered_y))
                else:
                    result.append((point[0], point[1], filtered_y, point[3]))
            else:
                result.append(point)
        return result


class MockCurveWidget:
    """Mock curve widget for testing commands."""

    def __init__(self, initial_data: CurveDataList | None = None):
        self.curve_data = initial_data or []
        self.zoom_factor = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.set_curve_data_calls = []

    def set_curve_data(self, data: CurveDataList) -> None:
        """Set curve data and track calls."""
        self.curve_data = copy.deepcopy(data)
        self.set_curve_data_calls.append(copy.deepcopy(data))


class MockMainWindow:
    """Mock main window for testing commands."""

    def __init__(self, curve_widget: MockCurveWidget | None = None):
        self.curve_widget = curve_widget


class TestSetCurveDataCommand:
    """Test SetCurveDataCommand class."""

    def test_command_creation(self):
        """Test command can be created with proper attributes."""
        old_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        new_data = [(1, 110.0, 210.0), (2, 160.0, 260.0)]

        cmd = SetCurveDataCommand("Test set curve data", new_data, old_data)

        assert cmd.description == "Test set curve data"
        assert not cmd.executed
        assert cmd.new_data == new_data
        assert cmd.old_data == old_data

    def test_command_creation_without_old_data(self):
        """Test command creation without providing old data."""
        new_data = [(1, 110.0, 210.0), (2, 160.0, 260.0)]

        cmd = SetCurveDataCommand("Test set curve data", new_data)

        assert cmd.description == "Test set curve data"
        assert not cmd.executed
        assert cmd.new_data == new_data
        assert cmd.old_data is None

    def test_execute_success(self):
        """Test successful command execution."""
        initial_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        new_data = [(1, 110.0, 210.0), (2, 160.0, 260.0)]

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = SetCurveDataCommand("Test set curve data", new_data)

        result = cmd.execute(main_window)

        assert result is True
        assert cmd.executed
        assert cmd.old_data == initial_data  # Should capture old data
        assert curve_widget.curve_data == new_data

    def test_execute_no_curve_widget(self):
        """Test execution failure when no curve widget."""
        new_data = [(1, 110.0, 210.0)]
        main_window = MockMainWindow(None)

        cmd = SetCurveDataCommand("Test set curve data", new_data)

        result = cmd.execute(main_window)

        assert result is False
        assert not cmd.executed

    def test_undo_success(self):
        """Test successful command undo."""
        initial_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        new_data = [(1, 110.0, 210.0), (2, 160.0, 260.0)]

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = SetCurveDataCommand("Test set curve data", new_data, initial_data)

        # Execute first
        cmd.execute(main_window)
        assert curve_widget.curve_data == new_data

        # Then undo
        result = cmd.undo(main_window)

        assert result is True
        assert not cmd.executed
        assert curve_widget.curve_data == initial_data

    def test_undo_no_old_data(self):
        """Test undo failure when no old data."""
        new_data = [(1, 110.0, 210.0)]
        curve_widget = MockCurveWidget([])
        main_window = MockMainWindow(curve_widget)

        cmd = SetCurveDataCommand("Test set curve data", new_data)
        # Don't execute first, so old_data remains None

        result = cmd.undo(main_window)

        assert result is False

    def test_redo_success(self):
        """Test successful command redo."""
        initial_data = [(1, 100.0, 200.0)]
        new_data = [(1, 110.0, 210.0)]

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = SetCurveDataCommand("Test set curve data", new_data, initial_data)

        # Execute, undo, then redo
        cmd.execute(main_window)
        cmd.undo(main_window)

        result = cmd.redo(main_window)

        assert result is True
        assert cmd.executed
        assert curve_widget.curve_data == new_data


class TestSmoothCommand:
    """Test SmoothCommand class."""

    @pytest.fixture
    def mock_data_service(self, monkeypatch):
        """Create mock data service."""
        mock_service = MockDataService()

        def mock_get_data_service():
            return mock_service

        monkeypatch.setattr("services.get_data_service", mock_get_data_service)
        return mock_service

    def test_command_creation(self):
        """Test command can be created with proper attributes."""
        indices = [0, 1, 2]
        old_points = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        new_points = [(1, 100.1, 200.1), (2, 150.1, 250.1)]

        cmd = SmoothCommand("Smooth points", indices, "moving_average", 3, old_points, new_points)

        assert cmd.description == "Smooth points"
        assert not cmd.executed
        assert cmd.indices == indices
        assert cmd.filter_type == "moving_average"
        assert cmd.window_size == 3
        assert cmd.old_points == old_points
        assert cmd.new_points == new_points

    def test_execute_moving_average(self, mock_data_service):
        """Test smooth command execution with moving average."""
        initial_data = [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)]
        indices = [0, 1]

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = SmoothCommand("Smooth with moving average", indices, "moving_average", 3)

        result = cmd.execute(main_window)

        assert result is True
        assert cmd.executed
        assert cmd.old_points == [initial_data[0], initial_data[1]]
        assert len(cmd.new_points) == 2

        # Verify smoothed data was applied (mock adds 0.1 to Y values)
        assert curve_widget.curve_data[0][2] == 200.1  # 200.0 + 0.1
        assert curve_widget.curve_data[1][2] == 250.1  # 250.0 + 0.1
        assert curve_widget.curve_data[2] == initial_data[2]  # Unchanged

    def test_execute_median_filter(self, mock_data_service):
        """Test smooth command execution with median filter."""
        initial_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        indices = [0, 1]

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = SmoothCommand("Smooth with median", indices, "median", 3)

        result = cmd.execute(main_window)

        assert result is True
        assert cmd.executed

        # Verify median filtered data was applied (mock adds 0.2 to Y values)
        assert curve_widget.curve_data[0][2] == 200.2  # 200.0 + 0.2
        assert curve_widget.curve_data[1][2] == 250.2  # 250.0 + 0.2

    def test_execute_butterworth_filter(self, mock_data_service):
        """Test smooth command execution with butterworth filter."""
        initial_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        indices = [0, 1]

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = SmoothCommand("Smooth with butterworth", indices, "butterworth", 4)

        result = cmd.execute(main_window)

        assert result is True
        assert cmd.executed

        # Verify butterworth filtered data was applied (mock adds 0.3 to Y values)
        assert curve_widget.curve_data[0][2] == 200.3  # 200.0 + 0.3
        assert curve_widget.curve_data[1][2] == 250.3  # 250.0 + 0.3

    def test_execute_unknown_filter(self, mock_data_service):
        """Test smooth command execution with unknown filter type."""
        initial_data = [(1, 100.0, 200.0)]
        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = SmoothCommand("Smooth with unknown", [0], "unknown_filter", 3)

        result = cmd.execute(main_window)

        assert result is False
        assert not cmd.executed

    def test_execute_no_curve_widget(self):
        """Test execution failure when no curve widget."""
        main_window = MockMainWindow(None)

        cmd = SmoothCommand("Smooth points", [0], "moving_average", 3)

        result = cmd.execute(main_window)

        assert result is False
        assert not cmd.executed

    def test_execute_preserves_view_state(self, mock_data_service):
        """Test that execution preserves view state."""
        initial_data = [(1, 100.0, 200.0)]
        curve_widget = MockCurveWidget(initial_data)
        curve_widget.zoom_factor = 2.0
        curve_widget.pan_offset_x = 50.0
        curve_widget.pan_offset_y = 75.0

        main_window = MockMainWindow(curve_widget)

        cmd = SmoothCommand("Smooth points", [0], "moving_average", 3)

        result = cmd.execute(main_window)

        assert result is True
        # View state should be preserved
        assert curve_widget.zoom_factor == 2.0
        assert curve_widget.pan_offset_x == 50.0
        assert curve_widget.pan_offset_y == 75.0

    def test_undo_success(self, mock_data_service):
        """Test successful smooth command undo."""
        initial_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        indices = [0, 1]

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = SmoothCommand("Smooth points", indices, "moving_average", 3)

        # Execute first
        cmd.execute(main_window)

        # Then undo
        result = cmd.undo(main_window)

        assert result is True
        assert not cmd.executed
        assert curve_widget.curve_data == initial_data

    def test_redo_success(self, mock_data_service):
        """Test successful smooth command redo."""
        initial_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        indices = [0, 1]

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = SmoothCommand("Smooth points", indices, "moving_average", 3)

        # Execute, undo, then redo
        cmd.execute(main_window)
        smoothed_data = copy.deepcopy(curve_widget.curve_data)
        cmd.undo(main_window)

        result = cmd.redo(main_window)

        assert result is True
        assert cmd.executed
        assert curve_widget.curve_data == smoothed_data


class TestMovePointCommand:
    """Test MovePointCommand class."""

    def test_command_creation(self):
        """Test command can be created with proper attributes."""
        old_pos = (100.0, 200.0)
        new_pos = (110.0, 210.0)
        cmd = MovePointCommand("Move point", 0, old_pos, new_pos)

        assert cmd.description == "Move point"
        assert not cmd.executed
        assert cmd.index == 0
        assert cmd.old_pos == old_pos
        assert cmd.new_pos == new_pos

    def test_execute_success(self):
        """Test successful point movement."""
        initial_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        old_pos = (100.0, 200.0)
        new_pos = (110.0, 210.0)

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = MovePointCommand("Move point", 0, old_pos, new_pos)

        result = cmd.execute(main_window)

        assert result is True
        assert cmd.executed
        # First point should be updated with new position
        assert curve_widget.curve_data[0] == (1, 110.0, 210.0)
        # Second point unchanged
        assert curve_widget.curve_data[1] == (2, 150.0, 250.0)

    def test_execute_with_status(self):
        """Test point movement preserves status."""
        initial_data = [(1, 100.0, 200.0, "KEYFRAME"), (2, 150.0, 250.0)]
        old_pos = (100.0, 200.0)
        new_pos = (110.0, 210.0)

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = MovePointCommand("Move point", 0, old_pos, new_pos)

        result = cmd.execute(main_window)

        assert result is True
        # Status should be preserved
        assert curve_widget.curve_data[0] == (1, 110.0, 210.0, "KEYFRAME")

    def test_execute_invalid_index(self):
        """Test execution with invalid index."""
        initial_data = [(1, 100.0, 200.0)]
        old_pos = (100.0, 200.0)
        new_pos = (110.0, 210.0)

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = MovePointCommand("Move point", 5, old_pos, new_pos)  # Index out of range

        result = cmd.execute(main_window)

        assert result is False
        assert not cmd.executed
        # Data should be unchanged
        assert curve_widget.curve_data == initial_data

    def test_undo_success(self):
        """Test successful point movement undo."""
        initial_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        old_pos = (100.0, 200.0)
        new_pos = (110.0, 210.0)

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = MovePointCommand("Move point", 0, old_pos, new_pos)

        # Execute first
        cmd.execute(main_window)
        assert curve_widget.curve_data[0] == (1, 110.0, 210.0)

        # Then undo
        result = cmd.undo(main_window)

        assert result is True
        assert not cmd.executed
        assert curve_widget.curve_data[0] == (1, 100.0, 200.0)


class TestDeletePointsCommand:
    """Test DeletePointsCommand class."""

    def test_command_creation(self):
        """Test command can be created with proper attributes."""
        indices = [0, 2, 4]
        points = [(1, 100.0, 200.0), (3, 300.0, 400.0), (5, 500.0, 600.0)]

        cmd = DeletePointsCommand("Delete points", indices, points)

        assert cmd.description == "Delete points"
        assert not cmd.executed
        assert cmd.indices == [4, 2, 0]  # Should be sorted in reverse order
        assert cmd.deleted_points == points

    def test_execute_success(self):
        """Test successful point deletion."""
        initial_data = [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)]
        indices = [0, 2]  # Delete first and third points

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = DeletePointsCommand("Delete points", indices)

        result = cmd.execute(main_window)

        assert result is True
        assert cmd.executed
        # Should have captured deleted points
        assert cmd.deleted_points is not None
        assert len(cmd.deleted_points) == 2
        # Only middle point should remain
        assert len(curve_widget.curve_data) == 1
        assert curve_widget.curve_data[0] == (2, 150.0, 250.0)


class TestBatchMoveCommand:
    """Test BatchMoveCommand class."""

    def test_command_creation(self):
        """Test command can be created with proper attributes."""
        moves = [
            (0, (100.0, 200.0), (110.0, 210.0)),
            (1, (150.0, 250.0), (160.0, 260.0)),
        ]

        cmd = BatchMoveCommand("Batch move", moves)

        assert cmd.description == "Batch move"
        assert not cmd.executed
        assert cmd.moves == moves

    def test_execute_success(self):
        """Test successful batch movement."""
        initial_data = [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)]
        moves = [
            (0, (100.0, 200.0), (110.0, 210.0)),
            (2, (200.0, 300.0), (220.0, 320.0)),
        ]

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = BatchMoveCommand("Batch move", moves)

        result = cmd.execute(main_window)

        assert result is True
        assert cmd.executed
        # First and third points should be moved
        assert curve_widget.curve_data[0] == (1, 110.0, 210.0)
        assert curve_widget.curve_data[1] == (2, 150.0, 250.0)  # Unchanged
        assert curve_widget.curve_data[2] == (3, 220.0, 320.0)


class TestSetPointStatusCommand:
    """Test SetPointStatusCommand class."""

    def test_command_creation(self):
        """Test command can be created with proper attributes."""
        changes = [
            (0, "NORMAL", "KEYFRAME"),
            (1, "INTERPOLATED", "NORMAL"),
        ]

        cmd = SetPointStatusCommand("Set status", changes)

        assert cmd.description == "Set status"
        assert not cmd.executed
        assert cmd.changes == changes


class TestAddPointCommand:
    """Test AddPointCommand class."""

    def test_command_creation(self):
        """Test command can be created with proper attributes."""
        new_point = (1, 100.0, 200.0, "NORMAL")

        cmd = AddPointCommand("Add point", 5, new_point)

        assert cmd.description == "Add point"
        assert not cmd.executed
        assert cmd.index == 5
        assert cmd.point == new_point

    def test_execute_success(self):
        """Test successful point addition."""
        initial_data = [(1, 100.0, 200.0), (3, 200.0, 300.0)]
        new_point = (2, 150.0, 250.0)

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = AddPointCommand("Add point", 1, new_point)

        result = cmd.execute(main_window)

        assert result is True
        assert cmd.executed
        # Point should be inserted at index 1
        assert len(curve_widget.curve_data) == 3
        assert curve_widget.curve_data[0] == (1, 100.0, 200.0)
        assert curve_widget.curve_data[1] == (2, 150.0, 250.0)  # New point
        assert curve_widget.curve_data[2] == (3, 200.0, 300.0)

    def test_undo_success(self):
        """Test successful point addition undo."""
        initial_data = [(1, 100.0, 200.0), (3, 200.0, 300.0)]
        new_point = (2, 150.0, 250.0)

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = AddPointCommand("Add point", 1, new_point)

        # Execute first
        cmd.execute(main_window)
        assert len(curve_widget.curve_data) == 3

        # Then undo
        result = cmd.undo(main_window)

        assert result is True
        assert not cmd.executed
        assert curve_widget.curve_data == initial_data


class TestCommandErrorHandling:
    """Test error handling in commands."""

    def test_set_curve_data_command_exception_handling(self):
        """Test SetCurveDataCommand handles exceptions gracefully."""
        new_data = [(1, 110.0, 210.0)]

        # Create a curve widget that raises an exception
        curve_widget = Mock()
        curve_widget.curve_data = []
        curve_widget.set_curve_data.side_effect = Exception("Test exception")

        main_window = MockMainWindow(curve_widget)

        cmd = SetCurveDataCommand("Test error handling", new_data)

        result = cmd.execute(main_window)

        assert result is False
        assert not cmd.executed

    def test_smooth_command_no_data_service(self, monkeypatch):
        """Test SmoothCommand handles missing data service."""

        def mock_get_data_service():
            return None

        monkeypatch.setattr("services.get_data_service", mock_get_data_service)

        initial_data = [(1, 100.0, 200.0)]
        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = SmoothCommand("Smooth points", [0], "moving_average", 3)

        result = cmd.execute(main_window)

        assert result is False
        assert not cmd.executed


class TestCommandIntegration:
    """Integration tests for command interactions."""

    def test_command_sequence_execute_undo_redo(self):
        """Test a sequence of command operations."""
        initial_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        new_data = [(1, 110.0, 210.0), (2, 160.0, 260.0)]

        curve_widget = MockCurveWidget(initial_data)
        main_window = MockMainWindow(curve_widget)

        cmd = SetCurveDataCommand("Test sequence", new_data)

        # Execute
        result1 = cmd.execute(main_window)
        assert result1 is True
        assert cmd.executed
        assert curve_widget.curve_data == new_data

        # Undo
        result2 = cmd.undo(main_window)
        assert result2 is True
        assert not cmd.executed
        assert curve_widget.curve_data == initial_data

        # Redo
        result3 = cmd.redo(main_window)
        assert result3 is True
        assert cmd.executed
        assert curve_widget.curve_data == new_data

    def test_command_data_immutability(self):
        """Test that commands don't modify input data."""
        original_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        new_data = [(1, 110.0, 210.0), (2, 160.0, 260.0)]

        # Keep references to original lists
        original_data_ref = original_data
        new_data_ref = new_data

        cmd = SetCurveDataCommand("Test immutability", new_data, original_data)

        # Verify command made deep copies
        assert cmd.old_data is not original_data_ref
        assert cmd.new_data is not new_data_ref
        assert cmd.old_data == original_data_ref
        assert cmd.new_data == new_data_ref

        # Modify original lists
        original_data.append((3, 300.0, 400.0))
        new_data.append((3, 310.0, 410.0))

        # Command data should be unchanged
        assert len(cmd.old_data) == 2
        assert len(cmd.new_data) == 2

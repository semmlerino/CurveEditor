#!/usr/bin/env python
"""
Comprehensive tests for StateManager.

Tests UI state management: view state, selection, file state, history state.
StateManager owns UI state only - ApplicationState owns data.
Following UNIFIED_TESTING_GUIDE principles: real components, behavior testing.
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

from pathlib import Path

import pytest
from PySide6.QtTest import QSignalSpy

from stores.application_state import get_application_state
from ui.state_manager import StateManager


@pytest.fixture
def state_manager():
    """Create a StateManager instance for testing."""
    # Ensure clean ApplicationState for this StateManager
    from stores.application_state import reset_application_state

    reset_application_state()
    sm = StateManager()
    # StateManager is a QObject, doesn't need qtbot registration
    return sm


@pytest.fixture
def state_manager_with_curve(state_manager):
    """Create a StateManager with active curve set for selection tests."""
    from core.models import CurvePoint
    from stores.application_state import get_application_state, reset_application_state

    app_state = get_application_state()

    # Set up test curve data
    test_data = [
        CurvePoint(frame=1, x=100.0, y=200.0),
        CurvePoint(frame=2, x=110.0, y=210.0),
        CurvePoint(frame=3, x=120.0, y=220.0),
        CurvePoint(frame=4, x=130.0, y=230.0),
        CurvePoint(frame=5, x=140.0, y=240.0),
    ]
    # Convert CurvePoint objects to legacy tuple format
    test_data_tuples = [point.to_legacy_tuple() for point in test_data]
    app_state.set_curve_data("TestCurve", test_data_tuples)
    app_state.set_active_curve("TestCurve")

    yield state_manager

    # Clean up ApplicationState to prevent test pollution
    reset_application_state()


class TestStateManagerInitialization:
    """Test StateManager initialization and defaults."""

    def test_initialization_defaults(self, state_manager):
        """Test StateManager initializes with correct defaults."""
        # File state (StateManager)
        assert state_manager.current_file is None
        assert state_manager.is_modified is False
        assert state_manager.file_format == "txt"

        # Selection state (point-level, from StateManager)
        assert state_manager.selected_points == []
        assert state_manager.hover_point is None

        # View state (UI state from StateManager)
        assert state_manager.zoom_level == 1.0
        assert state_manager.pan_offset == (0.0, 0.0)
        assert state_manager.view_bounds == (0.0, 0.0, 100.0, 100.0)

        # UI state (StateManager)
        assert state_manager.window_size == (1200, 800)
        assert state_manager.current_tool == "select"

        # History state (StateManager)
        assert state_manager.can_undo is False
        assert state_manager.can_redo is False

    def test_signals_exist(self, state_manager):
        """Test all expected signals are defined."""
        assert hasattr(state_manager, "file_changed")
        assert hasattr(state_manager, "modified_changed")
        assert hasattr(state_manager, "view_state_changed")
        assert hasattr(state_manager, "selection_changed")
        assert hasattr(state_manager, "frame_changed")
        assert hasattr(state_manager, "undo_state_changed")
        assert hasattr(state_manager, "redo_state_changed")
        assert hasattr(state_manager, "tool_state_changed")


class TestStateManagerFileState:
    """Test file state management."""

    def test_current_file_property(self, state_manager, qtbot):
        """Test current_file property and signal emission."""
        file_spy = QSignalSpy(state_manager.file_changed)

        state_manager.current_file = "/path/to/file.txt"

        assert state_manager.current_file == "/path/to/file.txt"
        assert file_spy.count() == 1
        assert file_spy.at(0)[0] == "/path/to/file.txt"

    def test_current_file_none_emits_empty_string(self, state_manager, qtbot):
        """Test setting current_file to None emits empty string."""
        state_manager.current_file = "/some/file.txt"
        file_spy = QSignalSpy(state_manager.file_changed)

        state_manager.current_file = None

        assert state_manager.current_file is None
        assert file_spy.count() == 1
        assert file_spy.at(0)[0] == ""

    def test_is_modified_property(self, state_manager, qtbot):
        """Test is_modified property and signal emission."""
        modified_spy = QSignalSpy(state_manager.modified_changed)

        state_manager.is_modified = True

        assert state_manager.is_modified is True
        assert modified_spy.count() == 1
        assert modified_spy.at(0)[0] is True

        state_manager.is_modified = False

        assert state_manager.is_modified is False
        assert modified_spy.count() == 2
        assert modified_spy.at(1)[0] is False

    def test_file_format_property(self, state_manager):
        """Test file_format property."""
        state_manager.file_format = "json"
        assert state_manager.file_format == "json"

        state_manager.file_format = "csv"
        assert state_manager.file_format == "csv"

    def test_window_title_generation(self, state_manager):
        """Test window title generation based on state."""
        # Default state
        assert state_manager.get_window_title() == "Untitled - CurveEditor"

        # With file
        state_manager.current_file = "/home/user/data.txt"
        assert state_manager.get_window_title() == "data.txt - CurveEditor"

        # Modified with file
        state_manager.is_modified = True
        assert state_manager.get_window_title() == "* data.txt - CurveEditor"

        # Modified without file
        state_manager.current_file = None
        assert state_manager.get_window_title() == "* Untitled - CurveEditor"

    def test_no_signal_on_same_value(self, state_manager, qtbot):
        """Test signals don't emit when value doesn't change."""
        state_manager.current_file = "/test.txt"

        file_spy = QSignalSpy(state_manager.file_changed)
        modified_spy = QSignalSpy(state_manager.modified_changed)

        # Set same values
        state_manager.current_file = "/test.txt"
        state_manager.is_modified = False

        assert file_spy.count() == 0
        assert modified_spy.count() == 0


class TestStateManagerSelectionState:
    """Test selection state management."""

    def test_selected_points_property(self, state_manager_with_curve):
        """Test selected_points property returns sorted list."""
        state_manager_with_curve.set_selected_points([3, 1, 2])
        assert state_manager_with_curve.selected_points == [1, 2, 3]

    def test_set_selected_points_with_list(self, state_manager_with_curve, qtbot):
        """Test setting selected points with list."""
        selection_spy = QSignalSpy(state_manager_with_curve.selection_changed)

        state_manager_with_curve.set_selected_points([5, 2, 8])

        # Note: Only indices 0-4 exist in test data, but selection doesn't validate
        assert state_manager_with_curve.selected_points == [2, 5, 8]
        assert selection_spy.count() == 1
        assert selection_spy.at(0)[0] == {2, 5, 8}

    def test_set_selected_points_with_set(self, state_manager_with_curve, qtbot):
        """Test setting selected points with set."""
        selection_spy = QSignalSpy(state_manager_with_curve.selection_changed)

        state_manager_with_curve.set_selected_points({7, 3, 5})

        assert state_manager_with_curve.selected_points == [3, 5, 7]
        assert selection_spy.count() == 1

    def test_add_to_selection(self, state_manager_with_curve, qtbot):
        """Test adding points to selection."""
        selection_spy = QSignalSpy(state_manager_with_curve.selection_changed)

        state_manager_with_curve.add_to_selection(5)
        assert state_manager_with_curve.selected_points == [5]
        assert selection_spy.count() == 1

        state_manager_with_curve.add_to_selection(3)
        assert state_manager_with_curve.selected_points == [3, 5]
        assert selection_spy.count() == 2

        # Adding existing point doesn't change
        state_manager_with_curve.add_to_selection(5)
        assert state_manager_with_curve.selected_points == [3, 5]
        assert selection_spy.count() == 2

    def test_remove_from_selection(self, state_manager_with_curve, qtbot):
        """Test removing points from selection."""
        state_manager_with_curve.set_selected_points([1, 2, 3, 4])
        selection_spy = QSignalSpy(state_manager_with_curve.selection_changed)

        state_manager_with_curve.remove_from_selection(2)
        assert state_manager_with_curve.selected_points == [1, 3, 4]
        assert selection_spy.count() == 1

        # Removing non-existent point doesn't change
        state_manager_with_curve.remove_from_selection(10)
        assert state_manager_with_curve.selected_points == [1, 3, 4]
        assert selection_spy.count() == 1

    def test_clear_selection(self, state_manager_with_curve, qtbot):
        """Test clearing selection."""
        state_manager_with_curve.set_selected_points([1, 2, 3])
        selection_spy = QSignalSpy(state_manager_with_curve.selection_changed)

        state_manager_with_curve.clear_selection()

        assert state_manager_with_curve.selected_points == []
        assert selection_spy.count() == 1
        assert selection_spy.at(0)[0] == set()

        # Clearing empty selection doesn't emit
        state_manager_with_curve.clear_selection()
        assert selection_spy.count() == 1

    def test_hover_point_property(self, state_manager):
        """Test hover_point property."""
        assert state_manager.hover_point is None

        state_manager.hover_point = 5
        assert state_manager.hover_point == 5

        state_manager.hover_point = None
        assert state_manager.hover_point is None

    def test_selection_no_signal_on_same_value(self, state_manager_with_curve, qtbot):
        """Test selection doesn't emit when unchanged."""
        state_manager_with_curve.set_selected_points([1, 2, 3])
        selection_spy = QSignalSpy(state_manager_with_curve.selection_changed)

        state_manager_with_curve.set_selected_points([3, 2, 1])  # Same set, different order

        assert selection_spy.count() == 0


class TestStateManagerViewState:
    """Test view state management."""

    def test_zoom_level_property(self, state_manager, qtbot):
        """Test zoom_level property with clamping."""
        view_spy = QSignalSpy(state_manager.view_state_changed)

        state_manager.zoom_level = 2.5
        assert state_manager.zoom_level == 2.5
        assert view_spy.count() == 1

        # Test clamping
        state_manager.zoom_level = 0.001
        assert state_manager.zoom_level == 0.01  # Min clamp

        state_manager.zoom_level = 200.0
        assert state_manager.zoom_level == 100.0  # Max clamp

    def test_pan_offset_property(self, state_manager, qtbot):
        """Test pan_offset property."""
        view_spy = QSignalSpy(state_manager.view_state_changed)

        state_manager.pan_offset = (10.0, 20.0)

        assert state_manager.pan_offset == (10.0, 20.0)
        assert view_spy.count() == 1

    def test_view_bounds_property(self, state_manager, qtbot):
        """Test view_bounds property."""
        view_spy = QSignalSpy(state_manager.view_state_changed)

        bounds = (5.0, 10.0, 95.0, 90.0)
        state_manager.view_bounds = bounds

        assert state_manager.view_bounds == bounds
        assert view_spy.count() == 1

    def test_view_state_no_signal_on_same_value(self, state_manager, qtbot):
        """Test view state doesn't emit when unchanged."""
        state_manager.zoom_level = 1.5
        state_manager.pan_offset = (5.0, 5.0)

        view_spy = QSignalSpy(state_manager.view_state_changed)

        # Set same values
        state_manager.pan_offset = (5.0, 5.0)
        state_manager.view_bounds = (0.0, 0.0, 100.0, 100.0)

        assert view_spy.count() == 0


class TestStateManagerUIState:
    """Test UI state management."""

    def test_window_size_property(self, state_manager):
        """Test window_size property."""
        state_manager.window_size = (1920, 1080)
        assert state_manager.window_size == (1920, 1080)

    def test_current_tool_property(self, state_manager):
        """Test current_tool property."""
        assert state_manager.current_tool == "select"

        state_manager.current_tool = "pen"
        assert state_manager.current_tool == "pen"

        state_manager.current_tool = "eraser"
        assert state_manager.current_tool == "eraser"

    def test_tool_state_changed_signal(self, state_manager, qtbot):
        """Tool changes emit signal."""
        with qtbot.waitSignal(state_manager.tool_state_changed, timeout=1000) as blocker:
            state_manager.current_tool = "smooth"

        assert state_manager.current_tool == "smooth"
        assert blocker.args == ["smooth"]

    def test_tool_no_signal_when_unchanged(self, state_manager, qtbot):
        """Tool state doesn't emit signal if value doesn't change."""
        state_manager.current_tool = "select"

        # Try to set same tool - should not emit signal
        with qtbot.assertNotEmitted(state_manager.tool_state_changed):
            state_manager.current_tool = "select"


class TestStateManagerHistory:
    """Test history state management."""

    def test_set_history_state(self, state_manager):
        """Test setting history state."""
        state_manager.set_history_state(can_undo=True, can_redo=False, position=5, size=10)

        assert state_manager.can_undo is True
        assert state_manager.can_redo is False
        # position and size are internal

    def test_history_properties(self, state_manager):
        """Test history properties."""
        assert state_manager.can_undo is False
        assert state_manager.can_redo is False

        state_manager.set_history_state(True, True)

        assert state_manager.can_undo is True
        assert state_manager.can_redo is True

    def test_undo_state_changed_signal(self, state_manager, qtbot):
        """Undo state changes emit signal."""
        with qtbot.waitSignal(state_manager.undo_state_changed, timeout=1000) as blocker:
            state_manager.set_history_state(can_undo=True, can_redo=False)

        assert state_manager.can_undo is True
        assert blocker.args == [True]

    def test_redo_state_changed_signal(self, state_manager, qtbot):
        """Redo state changes emit signal."""
        with qtbot.waitSignal(state_manager.redo_state_changed, timeout=1000) as blocker:
            state_manager.set_history_state(can_undo=False, can_redo=True)

        assert state_manager.can_redo is True
        assert blocker.args == [True]

    def test_history_state_no_signal_when_unchanged(self, state_manager, qtbot):
        """History state doesn't emit signals if values don't change."""
        # Set initial state
        state_manager.set_history_state(can_undo=True, can_redo=False)

        # Try to set same state - should not emit signals
        with qtbot.assertNotEmitted(state_manager.undo_state_changed), qtbot.assertNotEmitted(state_manager.redo_state_changed):
            state_manager.set_history_state(can_undo=True, can_redo=False)

    def test_history_state_emits_only_changed_signals(self, state_manager, qtbot):
        """Only changed history values emit signals."""
        # Set initial state
        state_manager.set_history_state(can_undo=True, can_redo=False)

        # Change only redo state - undo shouldn't emit, redo should
        with qtbot.assertNotEmitted(state_manager.undo_state_changed), qtbot.waitSignal(state_manager.redo_state_changed, timeout=1000) as blocker:
            state_manager.set_history_state(can_undo=True, can_redo=True)

        # Verify redo signal payload
        assert blocker.args == [True]


class TestStateManagerReset:
    """Test reset functionality."""

    def test_reset_to_defaults(self, state_manager_with_curve, qtbot):
        """Test resetting StateManager to default UI state."""
        app_state = get_application_state()

        # Set various StateManager UI states
        state_manager_with_curve.current_file = "/test.txt"
        state_manager_with_curve.is_modified = True
        state_manager_with_curve.set_selected_points([1, 2, 3])
        state_manager_with_curve.zoom_level = 2.0
        state_manager_with_curve.current_tool = "pen"

        # Setup spies
        file_spy = QSignalSpy(state_manager_with_curve.file_changed)
        modified_spy = QSignalSpy(state_manager_with_curve.modified_changed)
        selection_spy = QSignalSpy(state_manager_with_curve.selection_changed)
        view_spy = QSignalSpy(state_manager_with_curve.view_state_changed)

        # Reset StateManager (ApplicationState remains unchanged)
        state_manager_with_curve.reset_to_defaults()

        # Verify StateManager defaults
        assert state_manager_with_curve.current_file is None
        assert state_manager_with_curve.is_modified is False
        assert state_manager_with_curve.selected_points == []
        assert state_manager_with_curve.zoom_level == 1.0
        assert state_manager_with_curve.current_tool == "select"
        assert state_manager_with_curve.can_undo is False
        assert state_manager_with_curve.can_redo is False

        # Verify StateManager signals emitted
        assert file_spy.count() == 1
        assert file_spy.at(0)[0] == ""
        assert modified_spy.count() == 1
        assert modified_spy.at(0)[0] is False
        assert selection_spy.count() == 1
        assert selection_spy.at(0)[0] == set()
        assert view_spy.count() == 1

        # Note: ApplicationState is NOT reset by StateManager.reset_to_defaults()
        # It retains its data (frame, image files, curve data, etc.)
        assert app_state.active_curve is not None  # Curve data preserved


class TestStateManagerSummary:
    """Test state summary generation."""

    def test_get_state_summary_default(self, state_manager):
        """Test state summary with default values."""
        summary = state_manager.get_state_summary()

        assert summary["file"]["current_file"] is None
        assert summary["file"]["is_modified"] is False
        assert summary["file"]["file_format"] == "txt"

        assert summary["selection"]["selected_count"] == 0
        assert summary["selection"]["hover_point"] is None

        assert summary["view"]["zoom_level"] == 1.0

        assert summary["history"]["can_undo"] is False
        assert summary["history"]["can_redo"] is False

    def test_get_state_summary_with_data(self, state_manager_with_curve):
        """Test state summary with populated StateManager UI state."""
        # Set up StateManager UI state
        state_manager_with_curve.current_file = "/data/test.json"
        state_manager_with_curve.is_modified = True
        state_manager_with_curve.set_selected_points([0, 1])
        state_manager_with_curve.hover_point = 1
        state_manager_with_curve.zoom_level = 1.5
        state_manager_with_curve.set_history_state(True, False, 3, 5)

        summary = state_manager_with_curve.get_state_summary()

        # StateManager state
        assert summary["file"]["current_file"] == "/data/test.json"
        assert summary["file"]["is_modified"] is True
        assert summary["selection"]["selected_count"] == 2
        assert summary["selection"]["hover_point"] == 1
        assert summary["view"]["zoom_level"] == 1.5
        assert summary["history"]["can_undo"] is True
        assert summary["history"]["can_redo"] is False


class TestStateManagerEdgeCases:
    """Test edge cases and error conditions."""

    def test_zoom_level_precision(self, state_manager):
        """Test zoom_level precision handling."""
        state_manager.zoom_level = 1.0

        # Very small change shouldn't trigger signal
        view_spy = QSignalSpy(state_manager.view_state_changed)
        state_manager.zoom_level = 1.0001  # Less than 0.001 difference

        assert view_spy.count() == 0

        # Larger change should trigger
        state_manager.zoom_level = 1.002
        assert view_spy.count() == 1

    def test_path_object_in_file_name(self, state_manager):
        """Test using Path object for file names."""
        path = Path("/home/user/data.csv")
        state_manager.current_file = str(path)

        title = state_manager.get_window_title()
        assert "data.csv" in title

    def test_very_long_file_path(self, state_manager):
        """Test handling very long file paths."""
        long_path = "/very/long/path/" + "subdir/" * 20 + "file.txt"
        state_manager.current_file = long_path

        title = state_manager.get_window_title()
        assert "file.txt" in title  # Should still extract filename

    def test_selection_operations_performance(self, state_manager_with_curve):
        """Test selection operations are efficient with sets."""
        # Large selection
        large_selection = list(range(1000))
        state_manager_with_curve.set_selected_points(large_selection)

        # Add should be O(1)
        state_manager_with_curve.add_to_selection(1000)
        assert 1000 in state_manager_with_curve.selected_points

        # Remove should be O(1)
        state_manager_with_curve.remove_from_selection(500)
        assert 500 not in state_manager_with_curve.selected_points

        # Clear
        state_manager_with_curve.clear_selection()
        assert state_manager_with_curve.selected_points == []

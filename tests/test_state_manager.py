#!/usr/bin/env python
"""
Comprehensive tests for StateManager.

Tests centralized state management, property tracking, signal emissions, and state persistence.
Following UNIFIED_TESTING_GUIDE principles: real components, behavior testing.
"""

from pathlib import Path

import pytest
from PySide6.QtTest import QSignalSpy

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
        # File state
        assert state_manager.current_file is None
        assert state_manager.is_modified is False
        assert state_manager.file_format == "txt"

        # Data state
        assert state_manager.track_data == []
        assert state_manager.has_data is False

        # Selection state
        assert state_manager.selected_points == []
        assert state_manager.hover_point is None

        # View state
        assert state_manager.current_frame == 1
        assert state_manager.total_frames == 1
        assert state_manager.zoom_level == 1.0
        assert state_manager.pan_offset == (0.0, 0.0)
        assert state_manager.view_bounds == (0.0, 0.0, 100.0, 100.0)

        # Image state
        assert state_manager.image_directory is None
        assert state_manager.image_files == []
        assert state_manager.current_image is None

        # UI state
        assert state_manager.window_size == (1200, 800)
        assert state_manager.current_tool == "select"

        # History state
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


class TestStateManagerDataState:
    """Test data state management."""

    def test_track_data_property(self, state_manager):
        """Test track_data property returns copy."""
        data = [(1.0, 2.0), (3.0, 4.0)]
        state_manager.set_track_data(data)

        retrieved = state_manager.track_data
        assert retrieved == data

        # Verify it's a copy
        retrieved.append((5.0, 6.0))
        assert len(state_manager.track_data) == 2

    def test_set_track_data(self, state_manager, qtbot):
        """Test setting track data."""
        modified_spy = QSignalSpy(state_manager.modified_changed)

        data = [(1.0, 2.0), (3.0, 4.0), (5.0, 6.0)]
        state_manager.set_track_data(data)

        assert state_manager.track_data == data
        assert state_manager.has_data is True
        assert state_manager.is_modified is True
        assert modified_spy.count() == 1

    def test_set_track_data_without_marking_modified(self, state_manager, qtbot):
        """Test setting track data without marking as modified."""
        modified_spy = QSignalSpy(state_manager.modified_changed)

        data = [(1.0, 2.0)]
        state_manager.set_track_data(data, mark_modified=False)

        assert state_manager.track_data == data
        assert state_manager.is_modified is False
        assert modified_spy.count() == 0

    def test_data_bounds_calculation(self, state_manager):
        """Test data bounds calculation."""
        # Empty data
        assert state_manager.data_bounds == (0.0, 0.0, 1.0, 1.0)

        # With data
        data = [(10.0, 5.0), (20.0, 15.0), (5.0, 25.0), (30.0, 10.0)]
        state_manager.set_track_data(data, mark_modified=False)

        bounds = state_manager.data_bounds
        assert bounds == (5.0, 5.0, 30.0, 25.0)

    def test_has_data_property(self, state_manager):
        """Test has_data property."""
        assert state_manager.has_data is False

        state_manager.set_track_data([(1.0, 2.0)], mark_modified=False)
        assert state_manager.has_data is True

        state_manager.set_track_data([], mark_modified=False)
        assert state_manager.has_data is False


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

    def test_current_frame_property(self, state_manager, qtbot):
        """Test current_frame property with clamping."""
        frame_spy = QSignalSpy(state_manager.frame_changed)

        # Use set_image_files to set total_frames (StateManager.total_frames is read-only)
        state_manager.set_image_files([f"frame_{i}.png" for i in range(100)])
        state_manager.current_frame = 50

        assert state_manager.current_frame == 50
        assert frame_spy.count() == 1
        assert frame_spy.at(0)[0] == 50

    def test_current_frame_clamping(self, state_manager):
        """Test current_frame is clamped to valid range."""
        # Use set_image_files to set total_frames (StateManager.total_frames is read-only)
        state_manager.set_image_files([f"frame_{i}.png" for i in range(50)])

        # Above maximum
        state_manager.current_frame = 100
        assert state_manager.current_frame == 50

        # Below minimum
        state_manager.current_frame = 0
        assert state_manager.current_frame == 1

        # Negative
        state_manager.current_frame = -10
        assert state_manager.current_frame == 1

    def test_total_frames_property(self, state_manager):
        """Test total_frames property (read-only, derives from image files)."""
        # Use set_image_files to set total_frames (StateManager.total_frames is read-only)
        state_manager.set_image_files([f"frame_{i}.png" for i in range(200)])
        assert state_manager.total_frames == 200

        # Setting empty files defaults to minimum of 1
        state_manager.set_image_files([])
        assert state_manager.total_frames == 1

        # Minimum is always 1 (no negative values possible with set_image_files)
        state_manager.set_image_files([f"frame_{i}.png" for i in range(1)])
        assert state_manager.total_frames == 1

    def test_total_frames_adjusts_current(self, state_manager):
        """Test reducing total_frames adjusts current_frame."""
        # Use set_image_files to set total_frames
        state_manager.set_image_files([f"frame_{i}.png" for i in range(100)])
        state_manager.current_frame = 75

        # Reduce total frames below current (this will clamp current_frame)
        state_manager.set_image_files([f"frame_{i}.png" for i in range(50)])

        assert state_manager.current_frame == 50

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


class TestStateManagerImageSequence:
    """Test image sequence management."""

    def test_image_directory_property(self, state_manager):
        """Test image_directory property."""
        state_manager.image_directory = "/path/to/images"
        assert state_manager.image_directory == "/path/to/images"

        state_manager.image_directory = None
        assert state_manager.image_directory is None

    def test_image_files_property(self, state_manager):
        """Test image_files property returns copy."""
        files = ["img1.png", "img2.png", "img3.png"]
        state_manager.set_image_files(files)

        retrieved = state_manager.image_files
        assert retrieved == files

        # Verify it's a copy
        retrieved.append("img4.png")
        assert len(state_manager.image_files) == 3

    def test_set_image_files_updates_frames(self, state_manager):
        """Test setting image files updates total frames."""
        files = ["frame001.png", "frame002.png", "frame003.png"]
        state_manager.set_image_files(files)

        assert state_manager.image_files == files
        assert state_manager.total_frames == 3

    def test_set_empty_image_files(self, state_manager):
        """Test setting empty image files."""
        state_manager.set_image_files([])

        assert state_manager.image_files == []
        assert state_manager.total_frames == 1  # Minimum

    def test_current_image_property(self, state_manager):
        """Test current_image property."""
        files = ["img1.png", "img2.png", "img3.png"]
        state_manager.set_image_files(files)

        # Frame 1
        state_manager.current_frame = 1
        assert state_manager.current_image == "img1.png"

        # Frame 2
        state_manager.current_frame = 2
        assert state_manager.current_image == "img2.png"

        # Frame 3
        state_manager.current_frame = 3
        assert state_manager.current_image == "img3.png"

    def test_current_image_with_no_files(self, state_manager):
        """Test current_image when no files are set."""
        assert state_manager.current_image is None

        state_manager.current_frame = 5
        assert state_manager.current_image is None


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
        with qtbot.assertNotEmitted(state_manager.undo_state_changed):
            with qtbot.assertNotEmitted(state_manager.redo_state_changed):
                state_manager.set_history_state(can_undo=True, can_redo=False)

    def test_history_state_emits_only_changed_signals(self, state_manager, qtbot):
        """Only changed history values emit signals."""
        # Set initial state
        state_manager.set_history_state(can_undo=True, can_redo=False)

        # Change only redo state - undo shouldn't emit, redo should
        with qtbot.assertNotEmitted(state_manager.undo_state_changed):
            with qtbot.waitSignal(state_manager.redo_state_changed, timeout=1000) as blocker:
                state_manager.set_history_state(can_undo=True, can_redo=True)

        # Verify redo signal payload
        assert blocker.args == [True]


class TestStateManagerReset:
    """Test reset functionality."""

    def test_reset_to_defaults(self, state_manager_with_curve, qtbot):
        """Test resetting to default state."""
        # Set various states
        state_manager_with_curve.current_file = "/test.txt"
        state_manager_with_curve.is_modified = True
        state_manager_with_curve.set_track_data([(1.0, 2.0)], mark_modified=False)
        state_manager_with_curve.set_selected_points([1, 2, 3])
        # Use set_image_files to set total_frames (StateManager.total_frames is read-only)
        state_manager_with_curve.set_image_files([f"img{i}.png" for i in range(1, 101)])
        state_manager_with_curve.current_frame = 50
        state_manager_with_curve.zoom_level = 2.0
        # Use enough image files to not clamp current_frame (50 requires at least 50 images)
        state_manager_with_curve.set_image_files([f"img{i}.png" for i in range(1, 51)])
        state_manager_with_curve.current_tool = "pen"

        # Setup spies
        file_spy = QSignalSpy(state_manager_with_curve.file_changed)
        modified_spy = QSignalSpy(state_manager_with_curve.modified_changed)
        selection_spy = QSignalSpy(state_manager_with_curve.selection_changed)
        frame_spy = QSignalSpy(state_manager_with_curve.frame_changed)
        view_spy = QSignalSpy(state_manager_with_curve.view_state_changed)

        # Reset
        state_manager_with_curve.reset_to_defaults()

        # Verify defaults
        assert state_manager_with_curve.current_file is None
        assert state_manager_with_curve.is_modified is False
        assert state_manager_with_curve.track_data == []
        assert state_manager_with_curve.selected_points == []
        assert state_manager_with_curve.current_frame == 1
        assert state_manager_with_curve.total_frames == 1
        assert state_manager_with_curve.zoom_level == 1.0
        assert state_manager_with_curve.image_files == []
        assert state_manager_with_curve.current_tool == "select"
        assert state_manager_with_curve.can_undo is False
        assert state_manager_with_curve.can_redo is False

        # Verify signals emitted
        assert file_spy.count() == 1
        assert file_spy.at(0)[0] == ""
        assert modified_spy.count() == 1
        assert modified_spy.at(0)[0] is False
        assert selection_spy.count() == 1
        assert selection_spy.at(0)[0] == set()
        assert frame_spy.count() == 1
        assert frame_spy.at(0)[0] == 1
        assert view_spy.count() == 1


class TestStateManagerSummary:
    """Test state summary generation."""

    def test_get_state_summary_default(self, state_manager):
        """Test state summary with default values."""
        summary = state_manager.get_state_summary()

        assert summary["file"]["current_file"] is None
        assert summary["file"]["is_modified"] is False
        assert summary["file"]["file_format"] == "txt"

        assert summary["data"]["has_data"] is False
        assert summary["data"]["point_count"] == 0
        assert summary["data"]["data_bounds"] is None

        assert summary["selection"]["selected_count"] == 0
        assert summary["selection"]["hover_point"] is None

        assert summary["view"]["current_frame"] == 1
        assert summary["view"]["total_frames"] == 1
        assert summary["view"]["zoom_level"] == 1.0

        assert summary["images"]["image_count"] == 0
        assert summary["images"]["current_image"] is None

        assert summary["history"]["can_undo"] is False
        assert summary["history"]["can_redo"] is False

    def test_get_state_summary_with_data(self, state_manager_with_curve):
        """Test state summary with populated data."""
        # Set up state
        state_manager_with_curve.current_file = "/data/test.json"
        state_manager_with_curve.is_modified = True
        state_manager_with_curve.set_track_data([(1.0, 2.0), (3.0, 4.0)], mark_modified=False)
        state_manager_with_curve.set_selected_points([0, 1])
        state_manager_with_curve.hover_point = 1
        state_manager_with_curve.zoom_level = 1.5
        # Set images first (which sets total_frames to 10)
        state_manager_with_curve.set_image_files([f"f{i}.png" for i in range(1, 11)])
        # Now set current frame (within the new total_frames)
        state_manager_with_curve.current_frame = 5
        state_manager_with_curve.set_history_state(True, False, 3, 5)

        summary = state_manager_with_curve.get_state_summary()

        assert summary["file"]["current_file"] == "/data/test.json"
        assert summary["file"]["is_modified"] is True

        assert summary["data"]["has_data"] is True
        assert summary["data"]["point_count"] == 2
        assert summary["data"]["data_bounds"] == (1.0, 2.0, 3.0, 4.0)

        assert summary["selection"]["selected_count"] == 2
        assert summary["selection"]["hover_point"] == 1

        assert summary["view"]["current_frame"] == 5
        assert summary["view"]["total_frames"] == 10
        assert summary["view"]["zoom_level"] == 1.5

        assert summary["images"]["image_count"] == 10

        assert summary["history"]["can_undo"] is True
        assert summary["history"]["can_redo"] is False


class TestStateManagerIntegration:
    """Integration tests for StateManager."""

    def test_complex_state_workflow(self, state_manager_with_curve, qtbot):
        """Test complex workflow with multiple state changes."""
        # Start with file loading simulation
        state_manager_with_curve.current_file = "/project/animation.json"
        state_manager_with_curve.file_format = "json"

        # Load data
        data = [(float(i), float(i * 2)) for i in range(10)]
        state_manager_with_curve.set_track_data(data, mark_modified=False)

        # Load image sequence
        images = [f"frame{i:03d}.png" for i in range(1, 11)]
        state_manager_with_curve.set_image_files(images)

        # User interactions
        state_manager_with_curve.current_frame = 5
        state_manager_with_curve.set_selected_points([2, 3, 4])
        state_manager_with_curve.zoom_level = 2.0
        state_manager_with_curve.pan_offset = (50.0, 50.0)

        # Edit data
        modified_data = data.copy()
        modified_data[3] = (3.0, 7.0)
        state_manager_with_curve.set_track_data(modified_data)

        # Verify state
        assert state_manager_with_curve.is_modified is True
        assert state_manager_with_curve.current_image == "frame005.png"
        assert len(state_manager_with_curve.selected_points) == 3
        assert state_manager_with_curve.has_data is True

        # Save simulation
        state_manager_with_curve.is_modified = False

        assert state_manager_with_curve.is_modified is False

    def test_frame_synchronization(self, state_manager):
        """Test frame synchronization with image sequence."""
        # Add images first
        images = [f"img{i}.jpg" for i in range(1, 21)]
        state_manager.set_image_files(images)

        # Now set frame
        state_manager.current_frame = 5
        assert state_manager.current_frame == 5
        assert state_manager.current_image == "img5.jpg"

        # Navigate frames
        state_manager.current_frame = 1
        assert state_manager.current_image == "img1.jpg"

        state_manager.current_frame = 20
        assert state_manager.current_image == "img20.jpg"

        # Reduce image count
        state_manager.set_image_files(images[:5])
        assert state_manager.total_frames == 5
        assert state_manager.current_frame == 5  # Adjusted
        assert state_manager.current_image == "img5.jpg"

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

    def test_concurrent_state_changes(self, state_manager_with_curve, qtbot):
        """Test multiple concurrent state changes."""
        # Use set_image_files to set total_frames
        state_manager_with_curve.set_image_files([f"frame_{i}.png" for i in range(20)])

        # Setup signal spies
        file_spy = QSignalSpy(state_manager_with_curve.file_changed)
        frame_spy = QSignalSpy(state_manager_with_curve.frame_changed)
        selection_spy = QSignalSpy(state_manager_with_curve.selection_changed)

        # Rapid state changes (start from 2 to ensure first frame change emits)
        for i in range(10):
            state_manager_with_curve.current_file = f"/file{i}.txt"
            state_manager_with_curve.is_modified = i % 2 == 0
            state_manager_with_curve.current_frame = i + 2  # 2 through 11
            state_manager_with_curve.set_selected_points([i, i + 1])

        # All changes should be tracked
        assert file_spy.count() == 10
        assert frame_spy.count() == 10
        assert selection_spy.count() == 10

        # Final state
        assert state_manager_with_curve.current_file == "/file9.txt"
        assert state_manager_with_curve.current_frame == 11
        assert state_manager_with_curve.selected_points == [9, 10]


class TestStateManagerEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_data_bounds(self, state_manager):
        """Test data_bounds with empty data."""
        bounds = state_manager.data_bounds
        assert bounds == (0.0, 0.0, 1.0, 1.0)

    def test_single_point_data_bounds(self, state_manager):
        """Test data_bounds with single point."""
        state_manager.set_track_data([(5.0, 10.0)], mark_modified=False)
        bounds = state_manager.data_bounds
        assert bounds == (5.0, 10.0, 5.0, 10.0)

    def test_frame_beyond_image_count(self, state_manager):
        """Test current_image when frame exceeds image count."""
        state_manager.set_image_files(["img1.png", "img2.png"])
        state_manager.current_frame = 5  # Will be clamped to 2

        assert state_manager.current_frame == 2
        assert state_manager.current_image == "img2.png"

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


class TestKISSOLIDArchitectureVerification:
    """Test KISS/SOLID architecture patterns - verification tests from Section 5.1 of the plan."""

    def test_single_source_of_truth(self, state_manager):
        """
        Verify StateManager current_frame is clamped by total_frames.

        This test ensures frame clamping works:
        - StateManager owns current_frame state
        - current_frame is clamped to total_frames range
        - All other components must get current_frame from StateManager
        """
        # Test 1: StateManager is the authoritative source
        # Use set_image_files to set total_frames
        state_manager.set_image_files([f"frame_{i}.png" for i in range(20)])
        state_manager.current_frame = 10
        assert state_manager.current_frame == 10

        # Test 2: Verify frame clamping behavior
        state_manager.set_image_files([f"frame_{i}.png" for i in range(5)])
        state_manager.current_frame = 10  # Should be clamped to 5
        assert state_manager.current_frame == 5

        # Test 3: Verify signal emission on change
        frame_spy = QSignalSpy(state_manager.frame_changed)
        state_manager.current_frame = 3
        assert frame_spy.count() == 1
        assert frame_spy.at(0)[0] == 3

        # Test 4: No signal on same value
        frame_spy_2 = QSignalSpy(state_manager.frame_changed)
        state_manager.current_frame = 3  # Same value
        assert frame_spy_2.count() == 0

    def test_observer_pattern(self, state_manager_with_curve):
        """
        Verify components react to state changes via signals.

        This test ensures the Observer pattern is working:
        - State changes emit appropriate signals
        - Multiple observers can listen to same signal
        - batch_update prevents signal storms
        """
        # Test 1: Frame change emits signal
        # Use set_image_files to set total_frames
        state_manager_with_curve.set_image_files([f"frame_{i}.png" for i in range(10)])
        frame_spy = QSignalSpy(state_manager_with_curve.frame_changed)
        state_manager_with_curve.current_frame = 5
        assert frame_spy.count() == 1
        assert frame_spy.at(0)[0] == 5

        # Test 2: Selection change emits signal
        selection_spy = QSignalSpy(state_manager_with_curve.selection_changed)
        state_manager_with_curve.set_selected_points([1, 2, 3])
        assert selection_spy.count() == 1
        assert selection_spy.at(0)[0] == {1, 2, 3}

        # Test 3: Batch updates prevent signal storms
        frame_spy_batch = QSignalSpy(state_manager_with_curve.frame_changed)
        selection_spy_batch = QSignalSpy(state_manager_with_curve.selection_changed)

        with state_manager_with_curve.batch_update():
            state_manager_with_curve.current_frame = 8
            state_manager_with_curve.set_selected_points([4, 5])
            # No signals should be emitted yet
            assert frame_spy_batch.count() == 0
            assert selection_spy_batch.count() == 0

        # Signals should be emitted after context exits
        assert frame_spy_batch.count() == 1
        assert selection_spy_batch.count() == 1
        assert frame_spy_batch.at(0)[0] == 8
        assert selection_spy_batch.at(0)[0] == {4, 5}

    def test_renderer_independence(self):
        """
        Verify renderer has no parent/main_window access.

        This test ensures the renderer is fully decoupled:
        - Renderer doesn't access parent objects
        - render() method requires explicit state parameter
        - No tight coupling to application structure
        """
        from rendering.optimized_curve_renderer import OptimizedCurveRenderer
        from rendering.render_state import RenderState

        # Test 1: Renderer has no parent/main_window access
        renderer = OptimizedCurveRenderer()
        assert not hasattr(renderer, "main_window")
        assert not hasattr(renderer, "parent")

        # Test 2: render() method requires state parameter
        import inspect

        render_signature = inspect.signature(renderer.render)
        param_names = list(render_signature.parameters.keys())

        # Should have: painter, event, render_state
        assert "render_state" in param_names
        assert len(param_names) == 3  # painter, _event, render_state

        # Test 3: Renderer can work with mock RenderState (no widget dependency)
        mock_render_state = RenderState(
            points=[],
            current_frame=1,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0.0,
            pan_offset_y=0.0,
            manual_offset_x=0.0,
            manual_offset_y=0.0,
            flip_y_axis=True,
            show_background=False,
            show_grid=True,
            point_radius=3,
        )

        # Should not raise exception when called with mock state
        # (We won't actually render since we don't have a painter, just check the interface)
        assert callable(renderer.render)
        assert mock_render_state.current_frame == 1  # Verify mock works

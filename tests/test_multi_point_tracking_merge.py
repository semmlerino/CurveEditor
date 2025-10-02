#!/usr/bin/env python
"""
Tests for multi-point tracking data merging functionality.

Tests that loading multiple tracking files merges data instead of replacing it.
Following UNIFIED_TESTING_GUIDE best practices:
- Test behavior, not implementation
- Use real components when possible
- Factory fixtures for test data
- Clear test names describing behavior
- Edge case coverage
"""

import pytest

from core.type_aliases import CurveDataInput, CurveDataList
from ui.controllers.action_handler_controller import ActionHandlerController
from ui.controllers.multi_point_tracking_controller import MultiPointTrackingController

# ============================================================================
# TEST SIGNAL CLASS
# ============================================================================


class MockSignal:
    """Lightweight signal test double for non-Qt components."""

    def __init__(self):
        self.emissions = []
        self.callbacks = []

    def emit(self, *args):
        self.emissions.append(args)
        for callback in self.callbacks:
            callback(*args)

    def connect(self, callback):
        self.callbacks.append(callback)

    @property
    def was_emitted(self):
        return len(self.emissions) > 0

    @property
    def emission_count(self):
        return len(self.emissions)

    def reset(self):
        self.emissions.clear()


# ============================================================================
# FACTORY FIXTURES
# ============================================================================


@pytest.fixture
def make_tracking_point():
    """Factory for creating tracking point tuples."""

    def _make_point(frame: int, x: float = 100.0, y: float = 200.0, status: str = "tracked"):
        """Create a tracking point tuple.

        Args:
            frame: Frame number
            x: X coordinate
            y: Y coordinate
            status: Point status (tracked, keyframe, etc.)

        Returns:
            Tuple representing a tracking point
        """
        return (frame, x, y, status)

    return _make_point


@pytest.fixture
def make_tracking_data():
    """Factory for creating tracking data lists."""

    def _make_data(points_count: int = 5, start_frame: int = 1):
        """Create a list of tracking points.

        Args:
            points_count: Number of points to create
            start_frame: Starting frame number

        Returns:
            List of tracking point tuples
        """
        data = []
        for i in range(points_count):
            frame = start_frame + i
            x = 100.0 + (i * 10)
            y = 200.0 + (i * 20)
            status = "keyframe" if i % 3 == 0 else "tracked"
            data.append((frame, x, y, status))
        return data

    return _make_data


@pytest.fixture
def make_multi_point_data():
    """Factory for creating multi-point tracking data."""

    def _make_multi_data(point_names: list[str] = None, points_per_trajectory: int = 3):
        """Create multi-point tracking data dictionary.

        Args:
            point_names: Names of tracking points (default: ["Point1", "Point2"])
            points_per_trajectory: Number of points per trajectory

        Returns:
            Dictionary of point names to tracking data
        """
        if point_names is None:
            point_names = ["Point1", "Point2"]

        multi_data = {}
        for idx, name in enumerate(point_names):
            start_frame = idx * 10
            trajectory = []
            for i in range(points_per_trajectory):
                frame = start_frame + i
                x = 100.0 + (idx * 50) + (i * 5)
                y = 200.0 + (idx * 50) + (i * 10)
                trajectory.append((frame, x, y))
            multi_data[name] = trajectory

        return multi_data

    return _make_multi_data


# ============================================================================
# MOCK COMPONENTS
# ============================================================================


class MockCurveWidget:
    """Mock curve widget for testing."""

    def __init__(self):
        self.data: CurveDataList = []
        self.curves_data = {}
        self.setup_called = False
        # Mock curve_data property for auto-selection
        self.curve_data: CurveDataList = []
        # Mock curve store for auto-selection
        self._curve_store = MockCurveStore()

    def setup_for_pixel_tracking(self):
        self.setup_called = True

    def set_curve_data(self, data: CurveDataInput):
        self.data = list(data)
        self.curve_data = list(data)  # Update both for compatibility

    def set_curves_data(self, curves: dict[str, CurveDataList], metadata=None, active_curve=None, selected_curves=None):
        """Mock implementation of set_curves_data."""
        self.curves_data = curves


class MockCurveStore:
    """Mock curve store for testing auto-selection."""

    def __init__(self):
        self.selection = set()

    def select(self, index: int) -> None:
        """Mock select method."""
        self.selection = {index}


class MockStateManager:
    """Mock state manager for testing."""

    def __init__(self):
        self.track_data: CurveDataList = []
        self.modified = False
        self.total_frames = 0
        self.current_frame = 0
        self.is_modified = False
        self.current_file = None

    def set_track_data(self, data: CurveDataList, mark_modified: bool = True):
        self.track_data = data
        self.modified = mark_modified

    def reset_to_defaults(self):
        self.track_data = []
        self.modified = False
        self.total_frames = 0
        self.current_frame = 0


class MockTrackingPanel:
    """Mock tracking panel for testing."""

    def __init__(self):
        self.tracked_data = {}
        self.selected_points = []

    def set_tracked_data(self, data: dict[str, CurveDataList]):
        self.tracked_data = data

    def set_selected_points(self, point_names: list[str]) -> None:
        """Mock implementation of set_selected_points."""
        self.selected_points = point_names

    def get_point_visibility(self, point_name: str) -> bool:
        """Mock implementation of get_point_visibility."""
        return True  # Default to visible for testing

    def get_point_color(self, point_name: str) -> str:
        """Mock implementation of get_point_color."""
        return "#FFFFFF"  # Default to white for testing


class MockFileOperations:
    """Mock file operations for testing."""

    def __init__(self):
        self.next_data = None
        self.file_loaded_signal = MockSignal()

    def open_file(self, parent):
        """Simulate opening a file."""
        if self.next_data is not None:
            self.file_loaded_signal.emit(self.next_data)
        return self.next_data

    def set_next_file_data(self, data):
        """Set data to return on next open_file call."""
        self.next_data = data


class MockMainWindow:
    """Mock main window for testing."""

    def __init__(self):
        self.curve_widget = MockCurveWidget()
        self.tracking_panel = MockTrackingPanel()
        self.state_manager = MockStateManager()
        self.file_operations = MockFileOperations()
        self.frame_slider = None
        self.frame_spinbox = None
        self.total_frames_label = None
        self.status_label = None
        self.tracking_controller: object = None  # MultiPointTrackingController | None - Set after creation

    def update_tracking_panel(self):
        """Update tracking panel."""
        if self.tracking_controller is not None:
            self.tracking_controller.update_tracking_panel()

    def update_timeline_tabs(self, data):
        """Mock timeline update."""
        pass

    def update_ui_state(self):
        """Mock UI state update."""
        pass


# ============================================================================
# UNIT TESTS - Core Functionality
# ============================================================================


class TestUniqueNameGeneration:
    """Test unique name generation for avoiding conflicts."""

    def test_unique_name_when_no_conflict(self):
        """Should return the same name when there's no conflict."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)

        # No existing data
        unique_name = controller._get_unique_point_name("NewPoint")
        assert unique_name == "NewPoint"

    def test_unique_name_with_conflict(self, make_multi_point_data):
        """Should append suffix when name conflicts."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)

        # Add existing data
        controller.tracked_data = make_multi_point_data(["Point1", "Point2"])

        # Try to add conflicting name
        unique_name = controller._get_unique_point_name("Point1")
        assert unique_name == "Point1_2"

    def test_unique_name_with_multiple_conflicts(self, make_multi_point_data):
        """Should increment suffix for multiple conflicts."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)

        # Add existing data with conflicts
        controller.tracked_data = {
            "Track": [(1, 10.0, 20.0)],
            "Track_2": [(2, 20.0, 30.0)],
            "Track_3": [(3, 30.0, 40.0)],
        }

        unique_name = controller._get_unique_point_name("Track")
        assert unique_name == "Track_4"

    @pytest.mark.parametrize(
        "base_name,existing_names,expected",
        [
            ("Point", ["Point", "Point_2"], "Point_3"),
            ("Track", ["Track", "Track_2", "Track_4"], "Track_3"),
            ("NewName", [], "NewName"),
            ("Data", ["Data", "Data_2", "Data_3", "Data_4"], "Data_5"),
        ],
    )
    def test_unique_name_parametrized(self, base_name, existing_names, expected):
        """Test various conflict scenarios."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)

        # Set up existing names
        controller.tracked_data = {name: [] for name in existing_names}

        unique_name = controller._get_unique_point_name(base_name)
        assert unique_name == expected


# ============================================================================
# INTEGRATION TESTS - Data Loading and Merging
# ============================================================================


class TestMultiPointDataMerging:
    """Test merging of multi-point tracking data."""

    def test_load_first_multi_point_data(self, make_multi_point_data):
        """Loading first multi-point file should set data directly."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = controller

        # Load first multi-point data
        first_data = make_multi_point_data(["Point1", "Point2"])
        controller.on_multi_point_data_loaded(first_data)

        # Should have exact data
        assert len(controller.tracked_data) == 2
        assert "Point1" in controller.tracked_data
        assert "Point2" in controller.tracked_data
        assert controller.active_points == ["Point1"]

    def test_merge_multi_point_data_no_conflicts(self, make_multi_point_data):
        """Merging multi-point data without conflicts should preserve all points."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = controller

        # Load first data
        first_data = make_multi_point_data(["Point1", "Point2"])
        controller.on_multi_point_data_loaded(first_data)

        # Load second data with different names
        second_data = make_multi_point_data(["Point3", "Point4"])
        controller.on_multi_point_data_loaded(second_data)

        # Should have all 4 points
        assert len(controller.tracked_data) == 4
        assert all(name in controller.tracked_data for name in ["Point1", "Point2", "Point3", "Point4"])

    def test_merge_multi_point_data_with_conflicts(self, make_multi_point_data):
        """Merging with conflicting names should rename duplicates."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = controller

        # Load first data
        first_data = make_multi_point_data(["Point1", "Point2"])
        controller.on_multi_point_data_loaded(first_data)

        # Load second data with conflicting names
        second_data = make_multi_point_data(["Point1", "Point3"])
        controller.on_multi_point_data_loaded(second_data)

        # Should have renamed Point1 to Point1_2
        assert len(controller.tracked_data) == 4
        assert "Point1" in controller.tracked_data  # Original
        assert "Point1_2" in controller.tracked_data  # Renamed duplicate
        assert "Point2" in controller.tracked_data
        assert "Point3" in controller.tracked_data

    def test_preserve_existing_selection_when_merging(self, make_multi_point_data):
        """Active selection should be preserved when merging new data."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = controller

        # Load first data and select Point2
        first_data = make_multi_point_data(["Point1", "Point2"])
        controller.on_multi_point_data_loaded(first_data)
        controller.active_points = ["Point2"]

        # Load second data
        second_data = make_multi_point_data(["Point3"])
        controller.on_multi_point_data_loaded(second_data)

        # Selection should remain Point2
        assert controller.active_points == ["Point2"]


class TestSingleTrajectoryMerging:
    """Test merging of single trajectory data."""

    def test_load_first_single_trajectory(self, make_tracking_data):
        """First single trajectory should create Track1."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = controller

        # Load single trajectory
        data = make_tracking_data(5)
        controller.on_tracking_data_loaded(data)

        # Should create Track1
        assert len(controller.tracked_data) == 1
        assert "Track1" in controller.tracked_data
        assert controller.active_points == ["Track1"]

    def test_add_single_trajectory_to_existing(self, make_tracking_data, make_multi_point_data):
        """Single trajectory should be added to existing multi-point data."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = controller

        # Load multi-point data first
        multi_data = make_multi_point_data(["Point1", "Point2"])
        controller.on_multi_point_data_loaded(multi_data)

        # Add single trajectory
        single_data = make_tracking_data(3)
        controller.on_tracking_data_loaded(single_data)

        # Should have 3 points total
        assert len(controller.tracked_data) == 3
        assert "Track" in controller.tracked_data  # New single trajectory
        assert "Point1" in controller.tracked_data
        assert "Point2" in controller.tracked_data

    def test_multiple_single_trajectories_get_unique_names(self, make_tracking_data):
        """Multiple single trajectories should get unique Track names."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = controller

        # Load first single trajectory
        data1 = make_tracking_data(3, start_frame=1)
        controller.on_tracking_data_loaded(data1)
        assert "Track1" in controller.tracked_data

        # Load second single trajectory
        data2 = make_tracking_data(3, start_frame=10)
        controller.on_tracking_data_loaded(data2)
        assert "Track" in controller.tracked_data

        # Load third single trajectory
        data3 = make_tracking_data(3, start_frame=20)
        controller.on_tracking_data_loaded(data3)

        # Should have unique names
        assert len(controller.tracked_data) == 3
        assert "Track1" in controller.tracked_data
        assert "Track" in controller.tracked_data
        assert "Track_2" in controller.tracked_data


# ============================================================================
# FILE OPERATIONS INTEGRATION TESTS
# ============================================================================


class TestFileOpenMerging:
    """Test that File > Open properly merges data."""

    def test_open_single_file_routes_through_tracking_controller(self, make_tracking_data):
        """Opening single curve file should go through tracking controller."""
        main_window = MockMainWindow()
        state_manager = MockStateManager()
        tracking_controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = tracking_controller

        action_controller = ActionHandlerController(state_manager, main_window)

        # Simulate opening a single curve file
        single_data = make_tracking_data(5)
        main_window.file_operations.set_next_file_data(single_data)
        action_controller._on_action_open()

        # Should have routed through tracking controller
        assert len(tracking_controller.tracked_data) == 1
        assert "Track1" in tracking_controller.tracked_data

    def test_open_multi_point_file_routes_correctly(self, make_multi_point_data):
        """Opening multi-point file should go through tracking controller."""
        main_window = MockMainWindow()
        state_manager = MockStateManager()
        tracking_controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = tracking_controller

        action_controller = ActionHandlerController(state_manager, main_window)

        # Simulate opening a multi-point file
        multi_data = make_multi_point_data(["Point1", "Point2"])
        main_window.file_operations.set_next_file_data(multi_data)
        action_controller._on_action_open()

        # Should have routed through tracking controller
        assert len(tracking_controller.tracked_data) == 2
        assert "Point1" in tracking_controller.tracked_data
        assert "Point2" in tracking_controller.tracked_data

    def test_sequential_file_opens_merge_data(self, make_tracking_data, make_multi_point_data):
        """Opening multiple files sequentially should merge all data."""
        main_window = MockMainWindow()
        state_manager = MockStateManager()
        tracking_controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = tracking_controller

        action_controller = ActionHandlerController(state_manager, main_window)

        # Open first single file
        single_data1 = make_tracking_data(3)
        main_window.file_operations.set_next_file_data(single_data1)
        action_controller._on_action_open()

        assert len(tracking_controller.tracked_data) == 1

        # Open multi-point file
        multi_data = make_multi_point_data(["Point1", "Point2"])
        main_window.file_operations.set_next_file_data(multi_data)
        action_controller._on_action_open()

        assert len(tracking_controller.tracked_data) == 3

        # Open another single file
        single_data2 = make_tracking_data(2)
        main_window.file_operations.set_next_file_data(single_data2)
        action_controller._on_action_open()

        # Should have all data merged
        assert len(tracking_controller.tracked_data) == 4
        expected_names = {"Track1", "Point1", "Point2", "Track"}
        assert set(tracking_controller.tracked_data.keys()) == expected_names


# ============================================================================
# EDGE CASE TESTS
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_data_handled_gracefully(self):
        """Empty data should not cause errors."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = controller

        # Load empty multi-point data
        controller.on_multi_point_data_loaded({})

        # Should handle gracefully
        assert len(controller.tracked_data) == 0
        assert controller.active_points == []

    def test_none_data_handled_gracefully(self):
        """None data should not cause errors."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = controller

        # Load None data
        controller.on_tracking_data_loaded([])

        # Should handle gracefully
        assert len(controller.tracked_data) == 0

    def test_large_dataset_merging(self, make_multi_point_data):
        """Large datasets should merge efficiently."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = controller

        # Create large dataset
        large_names = [f"Point{i}" for i in range(50)]
        large_data = make_multi_point_data(large_names, points_per_trajectory=100)

        import time

        start_time = time.time()

        controller.on_multi_point_data_loaded(large_data)

        elapsed = time.time() - start_time

        # Should complete quickly (< 100ms)
        assert elapsed < 0.1
        assert len(controller.tracked_data) == 50

    def test_deep_conflict_resolution(self):
        """Should handle deep naming conflicts correctly."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = controller

        # Create data with many conflicts
        for i in range(10):
            if i == 0:
                data = {"Track": [(1, 10.0, 20.0)]}
            else:
                data = {"Track": [(i, i * 10.0, i * 20.0)]}

            controller.on_multi_point_data_loaded(data)

        # Should have all unique names
        assert len(controller.tracked_data) == 10
        assert "Track" in controller.tracked_data
        for i in range(2, 11):
            assert f"Track_{i}" in controller.tracked_data


# ============================================================================
# PANEL UPDATE TESTS
# ============================================================================


class TestPanelUpdates:
    """Test that tracking panel is properly updated."""

    def test_panel_updated_on_data_load(self, make_multi_point_data):
        """Panel should be updated when data is loaded."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = controller

        # Load data
        data = make_multi_point_data(["Point1", "Point2"])
        controller.on_multi_point_data_loaded(data)

        # Panel should have the data
        assert main_window.tracking_panel.tracked_data == controller.tracked_data

    def test_panel_updated_on_merge(self, make_multi_point_data):
        """Panel should be updated when data is merged."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = controller

        # Load first data
        data1 = make_multi_point_data(["Point1"])
        controller.on_multi_point_data_loaded(data1)

        # Load second data
        data2 = make_multi_point_data(["Point2"])
        controller.on_multi_point_data_loaded(data2)

        # Panel should have merged data
        assert len(main_window.tracking_panel.tracked_data) == 2


# ============================================================================
# PARAMETRIZED COMPREHENSIVE TESTS
# ============================================================================


class TestParametrizedMerging:
    """Comprehensive parametrized tests for various scenarios."""

    @pytest.mark.parametrize(
        "first_data,second_data,expected_count,expected_names",
        [
            # No conflicts
            ({"A": []}, {"B": []}, 2, ["A", "B"]),
            # Single conflict
            ({"Point": []}, {"Point": []}, 2, ["Point", "Point_2"]),
            # Multiple conflicts
            ({"A": [], "B": []}, {"A": [], "B": [], "C": []}, 5, ["A", "B", "A_2", "B_2", "C"]),
            # Empty first
            ({}, {"A": []}, 1, ["A"]),
            # Empty second
            ({"A": []}, {}, 1, ["A"]),
        ],
    )
    def test_various_merge_scenarios(self, first_data, second_data, expected_count, expected_names):
        """Test various merge scenarios."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)
        main_window.tracking_controller = controller

        # Load first data if not empty
        if first_data:
            controller.on_multi_point_data_loaded(first_data)

        # Load second data if not empty
        if second_data:
            controller.on_multi_point_data_loaded(second_data)

        # Verify results
        assert len(controller.tracked_data) == expected_count
        assert sorted(controller.tracked_data.keys()) == sorted(expected_names)

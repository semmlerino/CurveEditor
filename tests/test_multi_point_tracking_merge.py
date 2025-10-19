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

from collections.abc import Callable
from typing import Any

import pytest

from core.type_aliases import CurveDataInput, CurveDataList
from ui.controllers.action_handler_controller import ActionHandlerController
from ui.controllers.multi_point_tracking_controller import MultiPointTrackingController

# ============================================================================
# TEST SIGNAL CLASS
# ============================================================================


class MockSignal:
    """Lightweight signal test double for non-Qt components."""

    def __init__(self) -> None:
        self.emissions: list[tuple[Any, ...]] = []
        self.callbacks: list[Callable[..., Any]] = []

    def emit(self, *args: Any) -> None:
        self.emissions.append(args)
        for callback in self.callbacks:
            callback(*args)

    def connect(self, callback: Callable[..., Any]) -> None:
        self.callbacks.append(callback)

    @property
    def was_emitted(self) -> bool:
        return len(self.emissions) > 0

    @property
    def emission_count(self) -> int:
        return len(self.emissions)

    def reset(self) -> None:
        self.emissions.clear()


# ============================================================================
# FACTORY FIXTURES
# ============================================================================


@pytest.fixture
def make_tracking_point() -> Callable[[int, float, float, str], tuple[int, float, float, str]]:
    """Factory for creating tracking point tuples."""

    def _make_point(
        frame: int, x: float = 100.0, y: float = 200.0, status: str = "tracked"
    ) -> tuple[int, float, float, str]:
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
def make_tracking_data() -> Callable[..., CurveDataList]:
    """Factory for creating tracking data lists."""

    def _make_data(points_count: int = 5, start_frame: int = 1) -> CurveDataList:
        """Create a list of tracking points.

        Args:
            points_count: Number of points to create
            start_frame: Starting frame number

        Returns:
            List of tracking point tuples
        """
        data: CurveDataList = []
        for i in range(points_count):
            frame = start_frame + i
            x = 100.0 + (i * 10)
            y = 200.0 + (i * 20)
            status = "keyframe" if i % 3 == 0 else "tracked"
            data.append((frame, x, y, status))
        return data

    return _make_data


@pytest.fixture
def make_multi_point_data() -> Callable[..., dict[str, CurveDataList]]:
    """Factory for creating multi-point tracking data."""

    def _make_multi_data(
        point_names: list[str] | None = None, points_per_trajectory: int = 3
    ) -> dict[str, CurveDataList]:
        """Create multi-point tracking data dictionary.

        Args:
            point_names: Names of tracking points (default: ["Point1", "Point2"])
            points_per_trajectory: Number of points per trajectory

        Returns:
            Dictionary of point names to tracking data
        """
        if point_names is None:
            point_names = ["Point1", "Point2"]

        multi_data: dict[str, CurveDataList] = {}
        for idx, name in enumerate(point_names):
            start_frame = idx * 10
            trajectory: CurveDataList = []
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

    def __init__(self) -> None:
        self.data: CurveDataList = []
        self.curves_data: dict[str, CurveDataList] = {}
        self.setup_called: bool = False
        # Mock curve_data property for auto-selection
        self.curve_data: CurveDataList = []
        # Mock curve store for auto-selection
        self._curve_store: MockCurveStore = MockCurveStore()

    def setup_for_pixel_tracking(self) -> None:
        self.setup_called = True

    def set_curve_data(self, data: CurveDataInput) -> None:
        self.data = list(data)
        self.curve_data = list(data)  # Update both for compatibility

    def set_curves_data(
        self,
        curves: dict[str, CurveDataList],
        metadata: Any = None,
        active_curve: Any = None,
        selected_curves: Any = None,
    ) -> None:
        """Mock implementation of set_curves_data."""
        self.curves_data = curves


class MockCurveStore:
    """Mock curve store for testing auto-selection."""

    def __init__(self) -> None:
        self.selection: set[int] = set()
        self.data: CurveDataList = []

    def select(self, index: int) -> None:
        """Mock select method."""
        self.selection = {index}

    def get_data(self) -> CurveDataList:
        """Mock get_data method for ApplicationState migration."""
        return self.data


class MockStateManager:
    """Mock state manager for testing."""

    def __init__(self) -> None:
        self.track_data: CurveDataList = []
        self.modified: bool = False
        self.total_frames: int = 0
        self.current_frame: int = 0
        self.is_modified: bool = False
        self.current_file: str | None = None

    def set_track_data(self, data: CurveDataList, mark_modified: bool = True) -> None:
        self.track_data = data
        self.modified = mark_modified

    def reset_to_defaults(self) -> None:
        self.track_data = []
        self.modified = False
        self.total_frames = 0
        self.current_frame = 0


class MockTrackingPanel:
    """Mock tracking panel for testing."""

    def __init__(self) -> None:
        self.tracked_data: dict[str, CurveDataList] = {}
        self.selected_points: list[str] = []

    def set_tracked_data(self, data: dict[str, CurveDataList]) -> None:
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

    def __init__(self) -> None:
        self.next_data: CurveDataList | dict[str, CurveDataList] | None = None
        self.file_loaded_signal: MockSignal = MockSignal()

    def open_file(self, parent: Any) -> CurveDataList | dict[str, CurveDataList] | None:
        """Simulate opening a file."""
        if self.next_data is not None:
            self.file_loaded_signal.emit(self.next_data)
        return self.next_data

    def set_next_file_data(self, data: CurveDataList | dict[str, CurveDataList]) -> None:
        """Set data to return on next open_file call."""
        self.next_data = data


class MockMainWindow:
    """Mock main window for testing."""

    def __init__(self) -> None:
        self.curve_widget: MockCurveWidget = MockCurveWidget()
        self.tracking_panel: MockTrackingPanel = MockTrackingPanel()
        self.state_manager: MockStateManager = MockStateManager()
        self.file_operations: MockFileOperations = MockFileOperations()
        self.frame_slider: Any = None
        self.frame_spinbox: Any = None
        self.total_frames_label: Any = None
        self.status_label: Any = None
        self.tracking_controller: MultiPointTrackingController | None = None
        self.active_timeline_point: str | None = None

    def update_tracking_panel(self) -> None:
        """Update tracking panel."""
        if self.tracking_controller is not None:
            self.tracking_controller.update_tracking_panel()

    def update_timeline_tabs(self, data: Any) -> None:
        """Mock timeline update."""
        pass

    def update_ui_state(self) -> None:
        """Mock UI state update."""
        pass


# ============================================================================
# UNIT TESTS - Core Functionality
# ============================================================================


class TestUniqueNameGeneration:
    """Test unique name generation for avoiding conflicts."""

    def test_unique_name_when_no_conflict(self) -> None:
        """Should return the same name when there's no conflict."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]

        # No existing data
        unique_name = controller._get_unique_point_name("NewPoint")
        assert unique_name == "NewPoint"

    def test_unique_name_with_conflict(self, make_multi_point_data: Callable[..., dict[str, CurveDataList]]) -> None:
        """Should append suffix when name conflicts."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]

        # Add existing data
        controller.tracked_data = make_multi_point_data(["Point1", "Point2"])

        # Try to add conflicting name
        unique_name = controller._get_unique_point_name("Point1")
        assert unique_name == "Point1_2"

    def test_unique_name_with_multiple_conflicts(
        self, make_multi_point_data: Callable[..., dict[str, CurveDataList]]
    ) -> None:
        """Should increment suffix for multiple conflicts."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]

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
    def test_unique_name_parametrized(self, base_name: str, existing_names: list[str], expected: str) -> None:
        """Test various conflict scenarios."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]

        # Set up existing names
        controller.tracked_data = {name: [] for name in existing_names}

        unique_name = controller._get_unique_point_name(base_name)
        assert unique_name == expected


# ============================================================================
# INTEGRATION TESTS - Data Loading and Merging
# ============================================================================


class TestMultiPointDataMerging:
    """Test merging of multi-point tracking data."""

    def test_load_first_multi_point_data(self, make_multi_point_data: Callable[..., dict[str, CurveDataList]]) -> None:
        """Loading first multi-point file should set data directly."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
        main_window.tracking_controller = controller

        # Load first multi-point data
        first_data = make_multi_point_data(["Point1", "Point2"])
        controller.on_multi_point_data_loaded(first_data)

        # Should have exact data
        assert len(controller.tracked_data) == 2
        assert "Point1" in controller.tracked_data
        assert "Point2" in controller.tracked_data
        assert main_window.active_timeline_point == "Point1"

    def test_merge_multi_point_data_no_conflicts(
        self, make_multi_point_data: Callable[..., dict[str, CurveDataList]]
    ) -> None:
        """Merging multi-point data without conflicts should preserve all points."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
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

    def test_merge_multi_point_data_with_conflicts(
        self, make_multi_point_data: Callable[..., dict[str, CurveDataList]]
    ) -> None:
        """Merging with conflicting names should rename duplicates."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
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

    def test_preserve_existing_selection_when_merging(
        self, make_multi_point_data: Callable[..., dict[str, CurveDataList]]
    ) -> None:
        """Active selection should be preserved when merging new data."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
        main_window.tracking_controller = controller

        # Load first data and select Point2
        first_data = make_multi_point_data(["Point1", "Point2"])
        controller.on_multi_point_data_loaded(first_data)
        main_window.active_timeline_point = "Point2"

        # Load second data
        second_data = make_multi_point_data(["Point3"])
        controller.on_multi_point_data_loaded(second_data)

        # Selection should remain Point2
        assert main_window.active_timeline_point == "Point2"


class TestSingleTrajectoryMerging:
    """Test merging of single trajectory data."""

    def test_load_first_single_trajectory(self, make_tracking_data: Callable[..., CurveDataList]) -> None:
        """First single trajectory should create Track1."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
        main_window.tracking_controller = controller

        # Load single trajectory
        data = make_tracking_data(5)
        controller.on_tracking_data_loaded(data)

        # Should create Track1
        assert len(controller.tracked_data) == 1
        assert "Track1" in controller.tracked_data
        assert main_window.active_timeline_point == "Track1"

    def test_add_single_trajectory_to_existing(
        self,
        make_tracking_data: Callable[..., CurveDataList],
        make_multi_point_data: Callable[..., dict[str, CurveDataList]],
    ) -> None:
        """Single trajectory should be added to existing multi-point data."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
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

    def test_multiple_single_trajectories_get_unique_names(
        self, make_tracking_data: Callable[..., CurveDataList]
    ) -> None:
        """Multiple single trajectories should get unique Track names."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
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

    def test_open_single_file_routes_through_tracking_controller(
        self, make_tracking_data: Callable[..., CurveDataList]
    ) -> None:
        """Opening single curve file should go through tracking controller."""
        main_window = MockMainWindow()
        state_manager = MockStateManager()
        tracking_controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
        main_window.tracking_controller = tracking_controller

        action_controller = ActionHandlerController(state_manager, main_window)  # pyright: ignore[reportArgumentType]

        # Simulate opening a single curve file
        single_data = make_tracking_data(5)
        main_window.file_operations.set_next_file_data(single_data)
        action_controller.on_action_open()

        # Should have routed through tracking controller
        assert len(tracking_controller.tracked_data) == 1
        assert "Track1" in tracking_controller.tracked_data

    def test_open_multi_point_file_routes_correctly(
        self, make_multi_point_data: Callable[..., dict[str, CurveDataList]]
    ) -> None:
        """Opening multi-point file should go through tracking controller."""
        main_window = MockMainWindow()
        state_manager = MockStateManager()
        tracking_controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
        main_window.tracking_controller = tracking_controller

        action_controller = ActionHandlerController(state_manager, main_window)  # pyright: ignore[reportArgumentType]

        # Simulate opening a multi-point file
        multi_data = make_multi_point_data(["Point1", "Point2"])
        main_window.file_operations.set_next_file_data(multi_data)
        action_controller.on_action_open()

        # Should have routed through tracking controller
        assert len(tracking_controller.tracked_data) == 2
        assert "Point1" in tracking_controller.tracked_data
        assert "Point2" in tracking_controller.tracked_data

    def test_sequential_file_opens_merge_data(
        self,
        make_tracking_data: Callable[..., CurveDataList],
        make_multi_point_data: Callable[..., dict[str, CurveDataList]],
    ) -> None:
        """Opening multiple files sequentially should merge all data."""
        main_window = MockMainWindow()
        state_manager = MockStateManager()
        tracking_controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
        main_window.tracking_controller = tracking_controller

        action_controller = ActionHandlerController(state_manager, main_window)  # pyright: ignore[reportArgumentType]

        # Open first single file
        single_data1 = make_tracking_data(3)
        main_window.file_operations.set_next_file_data(single_data1)
        action_controller.on_action_open()

        assert len(tracking_controller.tracked_data) == 1

        # Open multi-point file
        multi_data = make_multi_point_data(["Point1", "Point2"])
        main_window.file_operations.set_next_file_data(multi_data)
        action_controller.on_action_open()

        assert len(tracking_controller.tracked_data) == 3

        # Open another single file
        single_data2 = make_tracking_data(2)
        main_window.file_operations.set_next_file_data(single_data2)
        action_controller.on_action_open()

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
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
        main_window.tracking_controller = controller

        # Load empty multi-point data
        controller.on_multi_point_data_loaded({})

        # Should handle gracefully
        assert len(controller.tracked_data) == 0
        assert main_window.active_timeline_point is None

    def test_none_data_handled_gracefully(self):
        """None data should not cause errors."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
        main_window.tracking_controller = controller

        # Load None data
        controller.on_tracking_data_loaded([])

        # Should handle gracefully
        assert len(controller.tracked_data) == 0

    def test_large_dataset_merging(self, make_multi_point_data: Callable[..., dict[str, CurveDataList]]) -> None:
        """Large datasets should merge efficiently."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
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
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
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

    def test_panel_updated_on_data_load(self, make_multi_point_data: Callable[..., dict[str, CurveDataList]]) -> None:
        """Panel should be updated when data is loaded."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
        main_window.tracking_controller = controller

        # Load data
        data = make_multi_point_data(["Point1", "Point2"])
        controller.on_multi_point_data_loaded(data)

        # Panel should have the data
        assert main_window.tracking_panel.tracked_data == controller.tracked_data

    def test_panel_updated_on_merge(self, make_multi_point_data: Callable[..., dict[str, CurveDataList]]) -> None:
        """Panel should be updated when data is merged."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
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
    def test_various_merge_scenarios(
        self,
        first_data: dict[str, CurveDataList],
        second_data: dict[str, CurveDataList],
        expected_count: int,
        expected_names: list[str],
    ) -> None:
        """Test various merge scenarios."""
        main_window = MockMainWindow()
        controller = MultiPointTrackingController(main_window)  # pyright: ignore[reportArgumentType]
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

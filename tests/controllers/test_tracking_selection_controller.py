#!/usr/bin/env python
"""Tests for TrackingSelectionController.

Comprehensive test suite covering selection synchronization including:
- Data loading with auto-selection at current frame
- Panel selection synchronization to ApplicationState
- Curve selection change handling
- Point auto-selection logic
- Selection sync between tracking panel and curve store

Focus Areas:
- Frame-based point auto-selection
- TrackingPanel → CurveStore synchronization
- Curve store → panel updates
- Selection state consistency
- Edge cases (no data, missing curves, invalid frames)
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

from stores.application_state import get_application_state
from tests.test_helpers import MockMainWindow
from ui.controllers.tracking_selection_controller import TrackingSelectionController


@pytest.fixture
def main_window(mock_main_window: MockMainWindow) -> MockMainWindow:
    """Provide a MockMainWindow for testing."""
    return mock_main_window


@pytest.fixture
def controller(main_window: MockMainWindow) -> TrackingSelectionController:
    """Create TrackingSelectionController with mock main window."""
    return TrackingSelectionController(main_window)


@pytest.fixture
def app_state():
    """Get the application state for verification."""
    return get_application_state()


@pytest.fixture
def sample_curve_data() -> list[tuple[int, float, float, str]]:
    """Create sample curve tracking data."""
    return [
        (1, 100.0, 200.0, "keyframe"),
        (5, 105.0, 205.0, "normal"),
        (10, 110.0, 210.0, "normal"),
        (15, 115.0, 215.0, "normal"),
        (20, 120.0, 220.0, "normal"),
    ]


@pytest.fixture
def multi_curve_data() -> dict[str, list[tuple[int, float, float, str]]]:
    """Create multi-curve test data."""
    return {
        "pp56_TM_138G": [
            (1, 100.0, 200.0, "keyframe"),
            (5, 105.0, 205.0, "normal"),
            (10, 110.0, 210.0, "normal"),
        ],
        "pp56_TM_139H": [
            (1, 150.0, 250.0, "keyframe"),
            (5, 155.0, 255.0, "normal"),
            (10, 160.0, 260.0, "normal"),
        ],
    }


class TestTrackingSelectionControllerInitialization:
    """Test controller initialization and setup."""

    def test_controller_initializes_with_main_window(
        self, controller: TrackingSelectionController, main_window: MockMainWindow
    ) -> None:
        """Test that controller initializes with proper main window reference.

        Verifies:
        - main_window reference is stored
        - ApplicationState is accessible
        """
        assert controller.main_window is main_window
        assert controller._app_state is not None

    def test_controller_has_app_state_access(
        self, controller: TrackingSelectionController
    ) -> None:
        """Test that controller can access ApplicationState methods.

        Verifies:
        - Basic ApplicationState methods accessible
        - get_all_curve_names works
        """
        assert callable(getattr(controller._app_state, "get_all_curve_names", None))
        assert callable(getattr(controller._app_state, "set_selection", None))


class TestDataLoadedHandling:
    """Test data loading and auto-selection."""

    def test_on_data_loaded_does_not_auto_select_points(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
        sample_curve_data: list[tuple[int, float, float, str]],
    ) -> None:
        """Test that loading data does NOT auto-select points.

        Verifies:
        - Curve-level selection (loading data) doesn't affect point-level selection
        - Selection remains empty after loading data
        - Prevents conflict between curve selection and point selection

        Context:
        Auto-selection was removed to fix conflict where selecting a curve from
        the list would auto-select a point, which persisted across frame navigation.
        """
        # Arrange
        curve_name = "TestPoint001"
        app_state.set_curve_data(curve_name, sample_curve_data)
        app_state.set_active_curve(curve_name)
        app_state.set_frame(5)  # Frame 5 is in the data

        assert main_window.curve_widget is not None
        main_window.curve_widget.curve_data = sample_curve_data

        # Act
        controller.on_data_loaded(curve_name, sample_curve_data)

        # Assert - No points should be auto-selected
        selection = app_state.get_selection(curve_name)
        assert len(selection) == 0, "on_data_loaded should not auto-select points"

    def test_on_data_loaded_with_no_point_at_frame(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
        sample_curve_data: list[tuple[int, float, float, str]],
    ) -> None:
        """Test that loading data doesn't select points even with non-matching frame.

        Verifies:
        - No auto-selection even when current frame has no point
        - No crash with non-existent frame
        - Consistent behavior regardless of frame
        """
        # Arrange
        curve_name = "TestPoint002"
        app_state.set_curve_data(curve_name, sample_curve_data)
        app_state.set_active_curve(curve_name)
        app_state.set_frame(999)  # No point at frame 999

        assert main_window.curve_widget is not None
        main_window.curve_widget.curve_data = sample_curve_data

        # Act
        controller.on_data_loaded(curve_name, sample_curve_data)

        # Assert - No points should be selected
        selection = app_state.get_selection(curve_name)
        assert len(selection) == 0, "on_data_loaded should not auto-select points"

    def test_on_data_loaded_handles_empty_data(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
    ) -> None:
        """Test that loading empty data doesn't crash.

        Verifies:
        - Empty data handled gracefully
        - No selection made
        - No exception raised
        """
        # Arrange
        curve_name = "TestPoint003"
        empty_data: list[tuple[int, float, float, str]] = []
        app_state.set_active_curve(curve_name)

        assert main_window.curve_widget is not None
        main_window.curve_widget.curve_data = empty_data

        # Act - Should not raise
        controller.on_data_loaded(curve_name, empty_data)

        # Assert - No exception raised

    def test_on_data_loaded_handles_missing_curve_widget(
        self, app_state, sample_curve_data: list[tuple[int, float, float, str]]
    ) -> None:
        """Test that missing curve widget is handled gracefully.

        Verifies:
        - No crash when curve_widget is None
        - Method returns early
        """
        # Arrange
        main_window = MockMainWindow()
        main_window.curve_widget = None
        controller = TrackingSelectionController(main_window)

        curve_name = "TestPoint004"
        app_state.set_curve_data(curve_name, sample_curve_data)

        # Act - Should not raise
        controller.on_data_loaded(curve_name, sample_curve_data)

        # Assert - No exception raised


class TestAutoSelectPointAtFrame:
    """Test automatic point selection at current frame."""

    def test_auto_select_finds_point_at_exact_frame(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
        sample_curve_data: list[tuple[int, float, float, str]],
    ) -> None:
        """Test that auto-select finds point at exact frame match.

        Verifies:
        - Correct point index selected
        - Matches current frame
        """
        # Arrange
        curve_name = "TestPoint005"
        app_state.set_curve_data(curve_name, sample_curve_data)
        app_state.set_active_curve(curve_name)
        app_state.set_frame(10)  # Frame 10 is at index 2

        assert main_window.curve_widget is not None
        main_window.curve_widget.curve_data = sample_curve_data

        # Act
        controller._auto_select_point_at_current_frame()

        # Assert
        selection = app_state.get_selection(curve_name)
        assert len(selection) == 1
        selected_index = next(iter(selection))
        assert sample_curve_data[selected_index][0] == 10

    def test_auto_select_fallback_to_first_point(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
        sample_curve_data: list[tuple[int, float, float, str]],
    ) -> None:
        """Test fallback to first point when no exact match.

        Verifies:
        - First point (index 0) selected as fallback
        - Selection is not empty
        """
        # Arrange
        curve_name = "TestPoint006"
        app_state.set_curve_data(curve_name, sample_curve_data)
        app_state.set_active_curve(curve_name)
        app_state.set_frame(7)  # No point at frame 7

        assert main_window.curve_widget is not None
        main_window.curve_widget.curve_data = sample_curve_data

        # Act
        controller._auto_select_point_at_current_frame()

        # Assert
        selection = app_state.get_selection(curve_name)
        assert len(selection) == 1
        selected_index = next(iter(selection))
        # Should be first point (frame 1)
        assert sample_curve_data[selected_index][0] == 1

    def test_auto_select_with_no_active_curve(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
        sample_curve_data: list[tuple[int, float, float, str]],
    ) -> None:
        """Test auto-select returns early when no active curve.

        Verifies:
        - No crash with no active curve
        - Method handles gracefully
        """
        # Arrange
        app_state.set_frame(5)
        assert main_window.curve_widget is not None
        main_window.curve_widget.curve_data = sample_curve_data

        # Act - Should not raise
        controller._auto_select_point_at_current_frame()

        # Assert - No exception raised

    def test_auto_select_with_missing_widget(
        self, app_state, sample_curve_data: list[tuple[int, float, float, str]]
    ) -> None:
        """Test auto-select with missing curve widget.

        Verifies:
        - Returns early without error
        """
        # Arrange
        main_window = MockMainWindow()
        main_window.curve_widget = None
        controller = TrackingSelectionController(main_window)

        curve_name = "TestPoint007"
        app_state.set_curve_data(curve_name, sample_curve_data)
        app_state.set_active_curve(curve_name)
        app_state.set_frame(5)

        # Act - Should not raise
        controller._auto_select_point_at_current_frame()

        # Assert - No exception raised


class TestSyncTrackingSelectionToCurveStore:
    """Test synchronization from tracking panel to curve store."""

    def test_sync_point_names_to_curve_store(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
        sample_curve_data: list[tuple[int, float, float, str]],
    ) -> None:
        """Test synchronizing TrackingPanel selection to CurveStore.

        Verifies:
        - Point name converted to point index
        - Selection updated in ApplicationState
        - Frame-based lookup works
        """
        # Arrange
        curve_name = "TestPoint008"
        app_state.set_curve_data(curve_name, sample_curve_data)
        app_state.set_frame(5)

        point_names = [curve_name]

        # Act
        controller._sync_tracking_selection_to_curve_store(point_names)

        # Assert
        selection = app_state.get_selection(curve_name)
        # Should have selected a point
        assert len(selection) > 0

    def test_sync_with_multiple_point_names(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
        multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test sync with multiple point names (sets selection for last curve).

        Verifies:
        - Selection set for last curve name at current frame
        - Method processes last point name in list
        """
        # Arrange
        for curve_name, data in multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        app_state.set_frame(5)
        point_names = ["pp56_TM_138G", "pp56_TM_139H"]

        # Act
        controller._sync_tracking_selection_to_curve_store(point_names)

        # Assert
        # Selection should be set for last curve at frame 5 (index 1)
        last_curve = "pp56_TM_139H"
        selection = app_state.get_selection(last_curve)
        assert selection == {1}  # Point at frame 5 is at index 1

    def test_sync_with_invalid_point_name(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
    ) -> None:
        """Test sync with point names not in ApplicationState.

        Verifies:
        - Invalid names handled gracefully
        - No crash or state corruption
        """
        # Arrange
        app_state.set_frame(5)
        invalid_names = ["NonExistentCurve001"]

        # Act - Should not raise
        controller._sync_tracking_selection_to_curve_store(invalid_names)

        # Assert - No exception raised

    def test_sync_with_empty_point_names(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
    ) -> None:
        """Test sync with empty point names list.

        Verifies:
        - Empty list handled gracefully
        """
        # Arrange
        app_state.set_frame(5)

        # Act - Should not raise
        controller._sync_tracking_selection_to_curve_store([])

        # Assert - No exception raised


class TestTrackingPointsSelection:
    """Test on_tracking_points_selected handling."""

    def test_on_tracking_points_selected_sets_active_timeline_point(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
        sample_curve_data: list[tuple[int, float, float, str]],
    ) -> None:
        """Test that panel selection sets active timeline point.

        Verifies:
        - Last selected point becomes active
        - active_timeline_point updated
        """
        # Arrange
        curve_name = "TestPoint009"
        app_state.set_curve_data(curve_name, sample_curve_data)
        app_state.set_active_curve(curve_name)

        from ui.controllers.tracking_display_controller import TrackingDisplayController

        display_controller = TrackingDisplayController(main_window)
        point_names = [curve_name]

        # Act
        controller.on_tracking_points_selected(point_names, display_controller)

        # Assert
        assert main_window.active_timeline_point == curve_name

    def test_on_tracking_points_selected_sets_active_curve(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
        multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test that point selection updates active curve in ApplicationState.

        Verifies:
        - Active curve set to selected point name
        - state synchronization works
        """
        # Arrange
        for curve_name, data in multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        from ui.controllers.tracking_display_controller import TrackingDisplayController

        display_controller = TrackingDisplayController(main_window)
        point_names = ["pp56_TM_139H"]

        # Act
        controller.on_tracking_points_selected(point_names, display_controller)

        # Assert
        assert app_state.active_curve == "pp56_TM_139H"

    def test_on_tracking_points_selected_with_multiple_points(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
        multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test selecting multiple points - last becomes active.

        Verifies:
        - Last selected point in list becomes active
        - Multi-selection last-wins behavior
        """
        # Arrange
        for curve_name, data in multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        from ui.controllers.tracking_display_controller import TrackingDisplayController

        display_controller = TrackingDisplayController(main_window)
        point_names = ["pp56_TM_138G", "pp56_TM_139H"]

        # Act
        controller.on_tracking_points_selected(point_names, display_controller)

        # Assert - Last point should be active
        assert app_state.active_curve == "pp56_TM_139H"
        assert main_window.active_timeline_point == "pp56_TM_139H"

    def test_on_tracking_points_selected_with_invalid_display_controller(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
    ) -> None:
        """Test handling invalid display_controller parameter.

        Verifies:
        - Type check prevents errors
        - Error logged gracefully
        """
        # Arrange
        invalid_controller = "not_a_display_controller"
        point_names = ["SomePoint"]

        # Act - Should not raise
        controller.on_tracking_points_selected(point_names, invalid_controller)

        # Assert - Method returns without error

    def test_on_tracking_points_selected_with_empty_point_list(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
    ) -> None:
        """Test selecting with empty point list.

        Verifies:
        - Empty list handled gracefully
        """
        # Arrange
        from ui.controllers.tracking_display_controller import TrackingDisplayController

        display_controller = TrackingDisplayController(main_window)

        # Act - Should not raise
        controller.on_tracking_points_selected([], display_controller)

        # Assert - No exception raised


class TestCurveSelectionChanged:
    """Test on_curve_selection_changed handling."""

    def test_on_curve_selection_changed_updates_state(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
        multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test that curve selection change is handled.

        Verifies:
        - Method executes without error
        - Selection state can be updated
        """
        # Arrange
        for curve_name, data in multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        selected_curves = {"pp56_TM_138G"}

        # Act - Should not raise
        controller.on_curve_selection_changed(selected_curves)

        # Assert - No exception raised

    def test_on_curve_selection_changed_with_multiple_curves(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
        multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test curve selection with multiple curves.

        Verifies:
        - Multiple curves handled correctly
        - Selection state updated
        """
        # Arrange
        for curve_name, data in multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        selected_curves = {"pp56_TM_138G", "pp56_TM_139H"}

        # Act - Should not raise
        controller.on_curve_selection_changed(selected_curves)

        # Assert - No exception raised

    def test_on_curve_selection_changed_with_empty_selection(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
    ) -> None:
        """Test curve selection change with empty selection.

        Verifies:
        - Empty selection handled gracefully
        """
        # Arrange
        selected_curves: set[str] = set()

        # Act - Should not raise
        controller.on_curve_selection_changed(selected_curves)

        # Assert - No exception raised


class TestSelectionStateConsistency:
    """Test selection state consistency across operations."""

    def test_selection_persists_across_multiple_operations(
        self,
        controller: TrackingSelectionController,
        main_window: MockMainWindow,
        app_state,
        sample_curve_data: list[tuple[int, float, float, str]],
    ) -> None:
        """Test that manual selection is maintained across operations.

        Verifies:
        - Manual selection doesn't get lost
        - on_data_loaded doesn't clear existing selection
        - _auto_select_point_at_current_frame works when called directly
        - State remains consistent
        """
        # Arrange
        curve_name = "TestPoint010"
        app_state.set_curve_data(curve_name, sample_curve_data)
        app_state.set_active_curve(curve_name)
        app_state.set_frame(5)

        assert main_window.curve_widget is not None
        main_window.curve_widget.curve_data = sample_curve_data

        # Manually select a point first
        app_state.set_selection(curve_name, {1})
        selection_initial = app_state.get_selection(curve_name)

        # Act - Verify selection persists through on_data_loaded
        controller.on_data_loaded(curve_name, sample_curve_data)
        selection_after_load = app_state.get_selection(curve_name)

        # Simulate manual auto-select operation
        controller._auto_select_point_at_current_frame()
        selection_after_auto = app_state.get_selection(curve_name)

        # Assert
        assert len(selection_initial) > 0, "Initial selection should exist"
        # on_data_loaded should NOT clear existing selection
        assert selection_after_load == selection_initial, "on_data_loaded should not modify selection"
        # _auto_select_point_at_current_frame should update selection when called directly
        assert len(selection_after_auto) > 0, "_auto_select_point_at_current_frame should select points"

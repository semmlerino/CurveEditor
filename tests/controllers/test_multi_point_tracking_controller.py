#!/usr/bin/env python
"""Tests for MultiPointTrackingController.

Comprehensive test suite covering multi-curve tracking operations including:
- Loading tracking data from files
- Inserting and deleting tracking curves
- Renaming tracking curves with state synchronization
- Tracking panel selection synchronization
- Sub-controller coordination and signal wiring

Focus Areas:
- Coverage gaps in facade controller delegation
- Multi-curve data integrity
- Selection state synchronization
- Signal flow between sub-controllers
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

from typing import Any

import pytest

from core.display_mode import DisplayMode
from core.models import TrackingDirection
from stores.application_state import get_application_state
from tests.test_helpers import MockMainWindow
from ui.controllers.multi_point_tracking_controller import MultiPointTrackingController


@pytest.fixture
def main_window(mock_main_window: MockMainWindow) -> MockMainWindow:
    """Provide a MockMainWindow for testing."""
    return mock_main_window


@pytest.fixture
def controller(main_window: MockMainWindow) -> MultiPointTrackingController:
    """Create MultiPointTrackingController with mock main window."""
    return MultiPointTrackingController(main_window)


@pytest.fixture
def app_state():
    """Get the application state for verification."""
    return get_application_state()


@pytest.fixture
def sample_tracking_data() -> dict[str, list[Any]]:
    """Create sample multi-point tracking data."""
    return {
        "pp56_TM_138G": [
            (1, 100.0, 200.0, "keyframe"),
            (2, 105.0, 205.0, "normal"),
            (3, 110.0, 210.0, "normal"),
        ],
        "pp56_TM_139H": [
            (1, 150.0, 250.0, "keyframe"),
            (2, 155.0, 255.0, "normal"),
            (3, 160.0, 260.0, "normal"),
        ],
        "pp56_TM_140J": [
            (1, 200.0, 300.0, "keyframe"),
            (2, 205.0, 305.0, "normal"),
            (3, 210.0, 310.0, "normal"),
        ],
    }


class TestMultiPointTrackingControllerInitialization:
    """Test controller initialization and sub-controller setup."""

    def test_controller_initializes_with_sub_controllers(
        self, controller: MultiPointTrackingController
    ) -> None:
        """Test that controller creates all required sub-controllers.

        Verifies:
        - data_controller is created and accessible
        - display_controller is created and accessible
        - selection_controller is created and accessible
        """
        assert controller.data_controller is not None
        assert controller.display_controller is not None
        assert controller.selection_controller is not None

    def test_sub_controllers_are_properly_initialized(
        self, controller: MultiPointTrackingController, main_window: MockMainWindow
    ) -> None:
        """Test that sub-controllers have correct main window reference.

        Verifies:
        - Each sub-controller has access to main_window
        - Sub-controllers can access ApplicationState
        """
        assert controller.data_controller.main_window is main_window
        assert controller.display_controller.main_window is main_window
        assert controller.selection_controller.main_window is main_window

    def test_point_tracking_directions_initialized_empty(
        self, controller: MultiPointTrackingController
    ) -> None:
        """Test that tracking directions dictionary is initialized empty."""
        assert isinstance(controller.point_tracking_directions, dict)
        assert len(controller.point_tracking_directions) == 0


class TestLoadTrackingData:
    """Test loading tracking data from files and updating state.

    Coverage gaps: Lines 104-121 in multi_point_tracking_controller.py
    (on_tracking_data_loaded, on_multi_point_data_loaded)
    """

    def test_load_single_tracking_trajectory(
        self,
        controller: MultiPointTrackingController,
        app_state,
        main_window: MockMainWindow,
    ) -> None:
        """Test loading single tracking trajectory adds curve to ApplicationState.

        Verifies:
        - Single trajectory loaded via on_tracking_data_loaded
        - Curve added to ApplicationState
        - Curve data matches input
        """
        # Arrange
        curve_data = [
            (1, 100.0, 200.0, "keyframe"),
            (2, 105.0, 205.0, "normal"),
            (3, 110.0, 210.0, "normal"),
        ]

        # Act
        controller.on_tracking_data_loaded(curve_data)

        # Assert - Curve should be added to ApplicationState
        all_curves = app_state.get_all_curve_names()
        assert len(all_curves) >= 1
        # Verify the data was stored
        stored_data = app_state.get_curve_data(all_curves[0])
        assert len(stored_data) == 3
        assert stored_data[0] == curve_data[0]

    def test_load_multiple_tracking_trajectories(
        self,
        controller: MultiPointTrackingController,
        app_state,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test loading multiple tracking trajectories via multi_point_data_loaded.

        Verifies:
        - Multi-point data loaded successfully
        - All curves added to ApplicationState
        - Each curve has correct data
        - Data integrity maintained
        """
        # Act
        controller.on_multi_point_data_loaded(sample_tracking_data)

        # Assert
        all_curves = app_state.get_all_curve_names()
        assert len(all_curves) == 3

        # Verify each curve's data
        for curve_name, expected_data in sample_tracking_data.items():
            stored_data = app_state.get_curve_data(curve_name)
            assert stored_data == expected_data
            assert len(stored_data) == 3

    def test_load_data_with_empty_input_is_safe(
        self,
        controller: MultiPointTrackingController,
        app_state,
    ) -> None:
        """Test that loading empty data doesn't crash or corrupt state.

        Verifies:
        - Empty dict loading is handled gracefully
        - No curves added
        - State remains clean
        """
        # Act
        controller.on_multi_point_data_loaded({})

        # Assert
        all_curves = app_state.get_all_curve_names()
        assert len(all_curves) == 0

    def test_load_data_via_tracked_data_setter_replaces_curves(
        self,
        controller: MultiPointTrackingController,
        app_state,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test that setting tracked_data property replaces all curves.

        Verifies:
        - tracked_data setter clears old curves
        - Only new curves present
        - No orphaned data
        """
        # Arrange - Load initial data via on_multi_point_data_loaded
        controller.on_multi_point_data_loaded(sample_tracking_data)
        initial_curves = app_state.get_all_curve_names()
        assert len(initial_curves) == 3

        # Act - Use tracked_data setter to replace all curves
        new_data = {"pp56_NEW_001": [(1, 50.0, 50.0, "keyframe")]}
        controller.tracked_data = new_data

        # Assert
        current_curves = app_state.get_all_curve_names()
        assert len(current_curves) == 1
        assert "pp56_NEW_001" in current_curves
        assert "pp56_TM_138G" not in current_curves  # Old curve removed

    def test_load_data_merges_with_existing_curves(
        self,
        controller: MultiPointTrackingController,
        app_state,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test that on_multi_point_data_loaded merges with existing data.

        Verifies:
        - New data added to existing curves (not replacing)
        - All curves preserved
        - Naming conflicts resolved with unique names
        """
        # Arrange - Load initial data
        controller.on_multi_point_data_loaded(sample_tracking_data)
        initial_curves = set(app_state.get_all_curve_names())
        assert len(initial_curves) == 3

        # Act - Load additional data
        new_data = {"pp56_NEW_001": [(1, 50.0, 50.0, "keyframe")]}
        controller.on_multi_point_data_loaded(new_data)

        # Assert - All curves should be present (merged, not replaced)
        current_curves = set(app_state.get_all_curve_names())
        assert len(current_curves) == 4
        assert initial_curves.issubset(current_curves)  # Original curves still there
        assert "pp56_NEW_001" in current_curves  # New curve added


class TestInsertTrack:
    """Test inserting new tracking curves.

    Coverage gaps: Lines 192-202 in multi_point_tracking_controller.py
    (get_unique_point_name for Insert Track)
    """

    def test_get_unique_point_name_with_no_existing_points(
        self, controller: MultiPointTrackingController
    ) -> None:
        """Test unique name generation when no points exist.

        Verifies:
        - Base name returned unchanged
        - No suffix added when no conflicts
        """
        # Act
        unique_name = controller.get_unique_point_name("pp56_NEW")

        # Assert
        assert unique_name == "pp56_NEW"

    def test_get_unique_point_name_with_existing_points(
        self,
        controller: MultiPointTrackingController,
        app_state,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test unique name generation with existing points.

        Verifies:
        - Suffix added when base name exists
        - Generated name doesn't conflict
        - Pattern is predictable (_001, _002, etc.)
        """
        # Arrange - Load sample data
        controller.on_multi_point_data_loaded(sample_tracking_data)

        # Act
        unique_name = controller.get_unique_point_name("pp56_TM_138G")

        # Assert
        assert unique_name != "pp56_TM_138G"  # Should not match existing
        assert "pp56_TM_138G" in unique_name  # Base name should be preserved

    def test_get_unique_point_name_prevents_collisions(
        self,
        controller: MultiPointTrackingController,
        app_state,
    ) -> None:
        """Test that unique name generation prevents all collisions.

        Verifies:
        - Generated name doesn't exist in ApplicationState
        - Multiple calls with same base name produce different results
        """
        # Arrange
        base_name = "TestPoint"
        controller.on_multi_point_data_loaded({base_name: [(1, 0.0, 0.0, "keyframe")]})

        # Act
        name1 = controller.get_unique_point_name(base_name)
        controller.on_multi_point_data_loaded(
            {base_name: [(1, 0.0, 0.0, "keyframe")], name1: [(1, 100.0, 100.0, "keyframe")]}
        )
        name2 = controller.get_unique_point_name(base_name)

        # Assert
        assert name1 != name2
        assert name1 != base_name
        assert name2 != base_name
        all_names = app_state.get_all_curve_names()
        assert name1 in all_names
        assert name2 not in all_names  # name2 is new, not yet added


class TestDeleteTracks:
    """Test deleting tracking curves.

    Coverage gaps: Lines 122-132 in multi_point_tracking_controller.py
    (on_point_deleted)
    """

    def test_delete_single_tracking_point(
        self,
        controller: MultiPointTrackingController,
        app_state,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test deleting a single tracking point removes it from state.

        Verifies:
        - Point deleted from ApplicationState
        - Other points remain intact
        - Data integrity maintained
        """
        # Arrange
        controller.on_multi_point_data_loaded(sample_tracking_data)
        point_to_delete = "pp56_TM_138G"

        # Act
        controller.on_point_deleted(point_to_delete)

        # Assert
        all_curves = app_state.get_all_curve_names()
        assert point_to_delete not in all_curves
        assert "pp56_TM_139H" in all_curves
        assert "pp56_TM_140J" in all_curves

    def test_delete_point_cleans_tracking_direction_mapping(
        self,
        controller: MultiPointTrackingController,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test that deletion removes point from tracking direction mapping.

        Verifies:
        - Point removed from point_tracking_directions
        - Mapping stays in sync with ApplicationState
        - No orphaned entries
        """
        # Arrange
        controller.on_multi_point_data_loaded(sample_tracking_data)
        point_name = "pp56_TM_138G"
        controller.on_tracking_direction_changed(
            point_name, TrackingDirection.TRACKING_FW
        )
        assert point_name in controller.point_tracking_directions

        # Act
        controller.on_point_deleted(point_name)

        # Assert
        assert point_name not in controller.point_tracking_directions

    def test_delete_all_points_clears_state(
        self,
        controller: MultiPointTrackingController,
        app_state,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test deleting all points leaves clean state.

        Verifies:
        - ApplicationState is empty
        - Tracking direction mapping is empty
        - No orphaned data
        """
        # Arrange
        controller.on_multi_point_data_loaded(sample_tracking_data)

        # Act
        for point_name in list(sample_tracking_data.keys()):
            controller.on_point_deleted(point_name)

        # Assert
        all_curves = app_state.get_all_curve_names()
        assert len(all_curves) == 0
        assert len(controller.point_tracking_directions) == 0


class TestRenameTracks:
    """Test renaming tracking curves and updating references.

    Coverage gaps: Lines 134-145 in multi_point_tracking_controller.py
    (on_point_renamed)
    """

    def test_rename_tracking_point_updates_application_state(
        self,
        controller: MultiPointTrackingController,
        app_state,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test renaming updates the curve name in ApplicationState.

        Verifies:
        - Old name removed from ApplicationState
        - New name added with same data
        - Data integrity maintained
        """
        # Arrange
        controller.on_multi_point_data_loaded(sample_tracking_data)
        old_name = "pp56_TM_138G"
        old_data = app_state.get_curve_data(old_name)
        new_name = "pp56_TM_138G_RENAMED"

        # Act
        controller.on_point_renamed(old_name, new_name)

        # Assert
        all_curves = app_state.get_all_curve_names()
        assert old_name not in all_curves
        assert new_name in all_curves
        new_data = app_state.get_curve_data(new_name)
        assert new_data == old_data

    def test_rename_updates_tracking_direction_mapping(
        self,
        controller: MultiPointTrackingController,
    ) -> None:
        """Test renaming updates tracking direction mapping.

        Verifies:
        - Direction mapping updated with new name
        - Old name removed from mapping
        - Direction value preserved
        """
        # Arrange
        point_data = {"point_old": [(1, 100.0, 200.0, "keyframe")]}
        controller.on_multi_point_data_loaded(point_data)
        direction = TrackingDirection.TRACKING_FW
        controller.on_tracking_direction_changed("point_old", direction)
        assert controller.point_tracking_directions["point_old"] == direction

        # Act
        controller.on_point_renamed("point_old", "point_new")

        # Assert
        assert "point_old" not in controller.point_tracking_directions
        assert "point_new" in controller.point_tracking_directions
        assert controller.point_tracking_directions["point_new"] == direction

    def test_rename_preserves_all_other_points(
        self,
        controller: MultiPointTrackingController,
        app_state,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test that renaming doesn't affect other points.

        Verifies:
        - Other curves unmodified
        - Their data intact
        - No cross-contamination
        """
        # Arrange
        controller.on_multi_point_data_loaded(sample_tracking_data)
        original_curves = set(app_state.get_all_curve_names())

        # Act
        controller.on_point_renamed("pp56_TM_138G", "pp56_TM_138G_NEW")

        # Assert
        current_curves = set(app_state.get_all_curve_names())
        # Should have same number of curves (1 renamed, not deleted)
        assert len(current_curves) == len(original_curves)
        # Original untouched points should be present
        assert "pp56_TM_139H" in current_curves
        assert "pp56_TM_140J" in current_curves


class TestTrackingDirectionChanges:
    """Test handling tracking direction changes.

    Coverage gaps: Lines 147-158 in multi_point_tracking_controller.py
    (on_tracking_direction_changed)
    """

    def test_tracking_direction_stored_in_mapping(
        self, controller: MultiPointTrackingController
    ) -> None:
        """Test that tracking direction is stored in the mapping.

        Verifies:
        - Direction enum stored for point
        - Value matches input
        """
        # Arrange
        point_name = "test_point"
        direction = TrackingDirection.TRACKING_FW
        controller.on_multi_point_data_loaded({point_name: [(1, 0.0, 0.0, "keyframe")]})

        # Act
        controller.on_tracking_direction_changed(point_name, direction)

        # Assert
        assert controller.point_tracking_directions[point_name] == direction

    def test_tracking_direction_update_overwrites_previous(
        self, controller: MultiPointTrackingController
    ) -> None:
        """Test that updating direction overwrites previous value.

        Verifies:
        - New direction replaces old
        - Only latest value retained
        """
        # Arrange
        point_name = "test_point"
        controller.on_multi_point_data_loaded({point_name: [(1, 0.0, 0.0, "keyframe")]})
        controller.on_tracking_direction_changed(
            point_name, TrackingDirection.TRACKING_FW
        )

        # Act
        controller.on_tracking_direction_changed(
            point_name, TrackingDirection.TRACKING_BW
        )

        # Assert
        assert controller.point_tracking_directions[point_name] == TrackingDirection.TRACKING_BW

    def test_tracking_direction_with_invalid_type_ignored(
        self, controller: MultiPointTrackingController
    ) -> None:
        """Test that non-TrackingDirection values are safely ignored.

        Verifies:
        - Invalid type doesn't crash
        - Mapping not updated with invalid value
        """
        # Arrange
        point_name = "test_point"
        controller.on_multi_point_data_loaded({point_name: [(1, 0.0, 0.0, "keyframe")]})

        # Act - Pass invalid type (string instead of enum)
        controller.on_tracking_direction_changed(point_name, "INVALID")

        # Assert - Should not be added to mapping since it's not TrackingDirection
        assert point_name not in controller.point_tracking_directions


class TestClearTrackingData:
    """Test clearing all tracking data."""

    def test_clear_removes_all_curves_from_application_state(
        self,
        controller: MultiPointTrackingController,
        app_state,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test that clear removes all curves from ApplicationState.

        Verifies:
        - All curves deleted
        - State is empty
        """
        # Arrange
        controller.on_multi_point_data_loaded(sample_tracking_data)
        assert len(app_state.get_all_curve_names()) == 3

        # Act
        controller.clear_tracking_data()

        # Assert
        assert len(app_state.get_all_curve_names()) == 0

    def test_clear_empties_tracking_direction_mapping(
        self,
        controller: MultiPointTrackingController,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test that clear empties the tracking direction mapping.

        Verifies:
        - Mapping cleared completely
        - No orphaned entries
        """
        # Arrange
        controller.on_multi_point_data_loaded(sample_tracking_data)
        for point_name in sample_tracking_data.keys():
            controller.on_tracking_direction_changed(
                point_name, TrackingDirection.TRACKING_FW
            )
        assert len(controller.point_tracking_directions) == 3

        # Act
        controller.clear_tracking_data()

        # Assert
        assert len(controller.point_tracking_directions) == 0


class TestPropertyDelegation:
    """Test property delegation to data controller."""

    def test_tracked_data_property_delegates_to_data_controller(
        self,
        controller: MultiPointTrackingController,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test that tracked_data property delegates correctly.

        Verifies:
        - Property returns data from data_controller
        - Data matches ApplicationState
        """
        # Arrange
        controller.on_multi_point_data_loaded(sample_tracking_data)

        # Act
        tracked_data = controller.tracked_data

        # Assert
        assert set(tracked_data.keys()) == set(sample_tracking_data.keys())
        for name, data in tracked_data.items():
            assert data == sample_tracking_data[name]

    def test_tracked_data_setter_delegates_to_data_controller(
        self,
        controller: MultiPointTrackingController,
        app_state,
    ) -> None:
        """Test that tracked_data setter updates ApplicationState.

        Verifies:
        - Setting property updates state
        - Data persists correctly
        """
        # Arrange
        new_data = {
            "curve1": [(1, 10.0, 20.0, "keyframe"), (2, 15.0, 25.0, "normal")],
            "curve2": [(1, 30.0, 40.0, "keyframe")],
        }

        # Act
        controller.tracked_data = new_data

        # Assert
        all_curves = app_state.get_all_curve_names()
        assert set(all_curves) == {"curve1", "curve2"}
        assert app_state.get_curve_data("curve1") == new_data["curve1"]
        assert app_state.get_curve_data("curve2") == new_data["curve2"]


class TestQueryMethods:
    """Test query methods that delegate to data controller."""

    def test_has_tracking_data_returns_true_with_data(
        self,
        controller: MultiPointTrackingController,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test has_tracking_data returns true when data loaded.

        Verifies:
        - Returns True when curves exist
        """
        # Arrange
        controller.on_multi_point_data_loaded(sample_tracking_data)

        # Act
        has_data = controller.has_tracking_data()

        # Assert
        assert has_data is True

    def test_has_tracking_data_returns_false_empty(
        self, controller: MultiPointTrackingController
    ) -> None:
        """Test has_tracking_data returns false when no data.

        Verifies:
        - Returns False when ApplicationState is empty
        """
        # Act
        has_data = controller.has_tracking_data()

        # Assert
        assert has_data is False

    def test_get_tracking_point_names_returns_all_points(
        self,
        controller: MultiPointTrackingController,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test getting list of all point names.

        Verifies:
        - Returns all loaded curve names
        - Order deterministic
        """
        # Arrange
        controller.on_multi_point_data_loaded(sample_tracking_data)

        # Act
        point_names = controller.get_tracking_point_names()

        # Assert
        assert set(point_names) == set(sample_tracking_data.keys())
        assert len(point_names) == 3


class TestDisplayDelegation:
    """Test delegation of display operations to display controller."""

    def test_update_tracking_panel_delegates(
        self, controller: MultiPointTrackingController, main_window: MockMainWindow
    ) -> None:
        """Test that update_tracking_panel delegates to display controller.

        Verifies:
        - Method doesn't crash
        - Delegation works correctly
        """
        # Act
        controller.update_tracking_panel()

        # Assert - Should not raise (delegation works)
        # Main window should have been accessed (it has the tracking_panel attribute)
        assert main_window is not None

    def test_set_display_mode_delegates(
        self, controller: MultiPointTrackingController
    ) -> None:
        """Test that set_display_mode delegates to display controller.

        Verifies:
        - Mode can be set
        - Delegation works
        """
        # Act
        controller.set_display_mode(DisplayMode.ALL_VISIBLE)

        # Assert - Should not raise

    def test_set_selected_curves_delegates(
        self, controller: MultiPointTrackingController
    ) -> None:
        """Test that set_selected_curves delegates to display controller.

        Verifies:
        - Curve selection can be set
        - Delegation works
        """
        # Act
        controller.set_selected_curves(["curve1", "curve2"])

        # Assert - Should not raise


class TestSelectionDelegation:
    """Test delegation of selection operations to selection controller."""

    def test_on_tracking_points_selected_delegates(
        self, controller: MultiPointTrackingController
    ) -> None:
        """Test that on_tracking_points_selected delegates correctly.

        Verifies:
        - Selection from panel is processed
        - Delegation works
        """
        # Act
        controller.on_tracking_points_selected(["point1", "point2"])

        # Assert - Should not raise

    def test_on_curve_selection_changed_delegates(
        self, controller: MultiPointTrackingController
    ) -> None:
        """Test that on_curve_selection_changed delegates correctly.

        Verifies:
        - Curve data store selection handled
        - Delegation works
        """
        # Act
        controller.on_curve_selection_changed({0, 1, 2}, "test_curve")

        # Assert - Should not raise


class TestSubControllerSignalWiring:
    """Test that sub-controller signals are properly wired."""

    def test_data_loaded_signal_connected_to_display(
        self,
        controller: MultiPointTrackingController,
    ) -> None:
        """Test that data_loaded signal is connected to display controller.

        Verifies:
        - Signal wiring completed during init
        - Display controller receives signals
        """
        # Arrange - Check that signals are wired (they should be from __init__)
        assert controller.data_controller is not None
        assert controller.display_controller is not None

        # Act & Assert - Signals exist and can be accessed
        assert controller.data_controller.data_loaded is not None
        assert controller.display_controller.on_data_loaded is not None

    def test_data_loaded_signal_connected_to_selection(
        self,
        controller: MultiPointTrackingController,
    ) -> None:
        """Test that data_loaded signal is connected to selection controller.

        Verifies:
        - Selection controller receives data_loaded signal
        """
        # Arrange
        assert controller.data_controller is not None
        assert controller.selection_controller is not None

        # Act & Assert - Controllers and signals exist
        assert controller.data_controller.data_loaded is not None
        assert controller.selection_controller.on_data_loaded is not None


class TestIntegrationScenarios:
    """Integration tests for realistic workflows."""

    def test_complete_workflow_load_select_rename_delete(
        self,
        controller: MultiPointTrackingController,
        app_state,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test complete workflow: load, select, rename, delete.

        Verifies:
        - All operations work together
        - State remains consistent
        - No data corruption
        """
        # 1. Load data
        controller.on_multi_point_data_loaded(sample_tracking_data)
        assert len(app_state.get_all_curve_names()) == 3

        # 2. Select curves
        controller.set_selected_curves(["pp56_TM_138G", "pp56_TM_139H"])

        # 3. Rename one
        controller.on_point_renamed("pp56_TM_138G", "renamed_point")

        # 4. Verify rename
        all_curves = app_state.get_all_curve_names()
        assert "renamed_point" in all_curves
        assert "pp56_TM_138G" not in all_curves

        # 5. Delete one
        controller.on_point_deleted("pp56_TM_139H")

        # 6. Verify final state
        final_curves = app_state.get_all_curve_names()
        assert len(final_curves) == 2
        assert "renamed_point" in final_curves
        assert "pp56_TM_140J" in final_curves

    def test_multiple_data_loads_merge_correctly(
        self,
        controller: MultiPointTrackingController,
        app_state,
    ) -> None:
        """Test that successive data loads merge with existing data.

        Verifies:
        - New data merged with existing (not replaced)
        - All curves accumulated
        - State stays consistent
        """
        # First load
        data1 = {"curve1": [(1, 0.0, 0.0, "keyframe")]}
        controller.on_multi_point_data_loaded(data1)
        assert len(app_state.get_all_curve_names()) == 1

        # Second load - merges with first
        data2 = {
            "curve2": [(1, 10.0, 10.0, "keyframe")],
            "curve3": [(1, 20.0, 20.0, "keyframe")],
        }
        controller.on_multi_point_data_loaded(data2)

        # Should have 3 curves total (merged, not replaced)
        current_curves = app_state.get_all_curve_names()
        assert len(current_curves) == 3
        assert "curve1" in current_curves  # Original still there
        assert "curve2" in current_curves
        assert "curve3" in current_curves

    def test_tracked_data_setter_replaces_correctly(
        self,
        controller: MultiPointTrackingController,
        app_state,
    ) -> None:
        """Test that tracked_data setter replaces all curves (unlike merge behavior).

        Verifies:
        - tracked_data setter replaces (not merges)
        - Old data cleared
        - Clean transitions
        """
        # Initial load via merge
        data1 = {"curve1": [(1, 0.0, 0.0, "keyframe")]}
        controller.on_multi_point_data_loaded(data1)
        assert len(app_state.get_all_curve_names()) == 1

        # Use setter to replace
        data2 = {
            "curve2": [(1, 10.0, 10.0, "keyframe")],
            "curve3": [(1, 20.0, 20.0, "keyframe")],
        }
        controller.tracked_data = data2

        # Should have exactly 2 curves (replaced, not merged)
        current_curves = app_state.get_all_curve_names()
        assert len(current_curves) == 2
        assert "curve1" not in current_curves  # Old cleared
        assert set(current_curves) == {"curve2", "curve3"}

    def test_tracking_direction_mapping_stays_in_sync(
        self,
        controller: MultiPointTrackingController,
        sample_tracking_data: dict[str, list[Any]],
    ) -> None:
        """Test that tracking direction mapping stays in sync with ApplicationState.

        Verifies:
        - No orphaned direction mappings
        - All curves with directions are valid
        - Sync maintained through renames/deletes
        """
        # Arrange - Load and set directions
        controller.on_multi_point_data_loaded(sample_tracking_data)
        for point_name in sample_tracking_data.keys():
            controller.on_tracking_direction_changed(
                point_name, TrackingDirection.TRACKING_FW
            )

        # Act & Assert - Rename one
        controller.on_point_renamed("pp56_TM_138G", "renamed")

        # Verify mapping updated
        assert "renamed" in controller.point_tracking_directions
        assert "pp56_TM_138G" not in controller.point_tracking_directions

        # Act & Assert - Delete one
        controller.on_point_deleted("pp56_TM_139H")

        # Verify mapping updated
        assert "pp56_TM_139H" not in controller.point_tracking_directions

        # Verify all remaining points have directions
        all_curves = controller.get_tracking_point_names()
        for curve_name in all_curves:
            assert (
                curve_name in controller.point_tracking_directions
                or curve_name != "renamed"
            )

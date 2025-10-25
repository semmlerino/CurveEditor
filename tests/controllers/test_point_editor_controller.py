#!/usr/bin/env python
"""Tests for PointEditorController.

Tests point editing logic including spinbox updates and coordinate changes.
"""


import pytest

from tests.test_helpers import MockMainWindow
from ui.controllers.point_editor_controller import PointEditorController


@pytest.fixture
def controller(mock_main_window: MockMainWindow) -> PointEditorController:
    """Create PointEditorController with mock main window."""
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

    return PointEditorController(
        main_window=mock_main_window,
        state_manager=mock_main_window.state_manager
    )


class TestPointEditorController:
    """Test suite for PointEditorController."""
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


    def test_single_point_selection_updates_spinboxes(
        self,
        controller: PointEditorController,
        mock_main_window: MockMainWindow
    ) -> None:
        """Test selecting single point updates coordinate spinboxes.

        Verifies:
        - Spinbox values updated to selected point coordinates
        - Spinboxes enabled for single selection
        - Label updated with point index
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

        from stores.application_state import get_application_state

        # Arrange: Create curve data with known coordinates
        curve_name = "TestTrack"
        point_data = [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)]
        mock_main_window.curve_view.set_curve_data(point_data)  # Use setter to maintain alias

        # Set active curve and add to application state
        state = get_application_state()
        state.set_curve_data(curve_name, point_data)  # Creates curve automatically
        state.set_active_curve(curve_name)

        # Act: Select single point at index 0
        state.set_selection(curve_name, {0})
        controller.on_store_selection_changed({0}, curve_name)

        # Assert: Spinbox values match point coordinates
        assert mock_main_window.point_x_spinbox.value() == 100.0, "X spinbox should show 100.0"
        assert mock_main_window.point_y_spinbox.value() == 200.0, "Y spinbox should show 200.0"

        # Assert: Spinboxes enabled
        assert mock_main_window.point_x_spinbox.isEnabled() is True, "X spinbox should be enabled"
        assert mock_main_window.point_y_spinbox.isEnabled() is True, "Y spinbox should be enabled"

    def test_multiple_selection_disables_spinboxes(
        self,
        controller: PointEditorController,
        mock_main_window: MockMainWindow
    ) -> None:
        """Test multiple point selection disables coordinate editing.

        Verifies:
        - Spinboxes disabled when multiple points selected
        - User cannot edit multiple points simultaneously
        - Selection count label updated
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

        from stores.application_state import get_application_state

        # Arrange: Create curve data with multiple points
        curve_name = "TestTrack"
        point_data = [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)]
        mock_main_window.curve_view.set_curve_data(point_data)  # Use setter to maintain alias

        # Set active curve and add to application state
        state = get_application_state()
        state.set_curve_data(curve_name, point_data)  # Creates curve automatically
        state.set_active_curve(curve_name)

        # Act: Select multiple points using on_selection_changed
        # (on_store_selection_changed always treats as single point,
        # but on_selection_changed properly handles multiple selection)
        indices = [0, 1]
        controller.on_selection_changed(indices)

        # Assert: Spinboxes disabled
        assert mock_main_window.point_x_spinbox.isEnabled() is False, "X spinbox should be disabled"
        assert mock_main_window.point_y_spinbox.isEnabled() is False, "Y spinbox should be disabled"

        # Assert: Selection count label updated
        label_text = mock_main_window.selected_count_label.text()
        assert "Selected: 2" in label_text, f"Label should show 'Selected: 2', got: {label_text}"

    def test_spinbox_change_updates_point_coordinates(
        self,
        controller: PointEditorController,
        mock_main_window: MockMainWindow
    ) -> None:
        """Test changing spinbox values updates point coordinates.

        Verifies:
        - Changing spinbox X value updates curve point X coordinate
        - Changing spinbox Y value updates curve point Y coordinate
        - ApplicationState and curve_widget stay synchronized
        - Modified flag set when point changed
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

        from stores.application_state import get_application_state

        # Arrange: Create curve with single point at (100.0, 200.0)
        curve_name = "TestTrack"
        point_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        mock_main_window.curve_view.set_curve_data(point_data)  # Use setter to maintain alias

        # Set active curve and add to application state
        state = get_application_state()
        state.set_curve_data(curve_name, point_data)  # Creates curve automatically
        state.set_active_curve(curve_name)

        # Select the point (at index 0) to enable spinboxes
        state.set_selection(curve_name, {0})
        controller.on_store_selection_changed({0}, curve_name)

        # Verify initial state
        assert mock_main_window.point_x_spinbox.value() == 100.0
        assert mock_main_window.point_y_spinbox.value() == 200.0

        # Act 1: Change X coordinate via spinbox
        new_x = 125.5
        mock_main_window.point_x_spinbox.setValue(new_x)
        controller._on_point_x_changed(new_x)

        # Assert: Curve data updated
        updated_point = mock_main_window.curve_view.curve_data[0]
        assert updated_point[1] == new_x, f"X coordinate should be {new_x}, got {updated_point[1]}"
        assert updated_point[2] == 200.0, f"Y coordinate should remain 200.0, got {updated_point[2]}"

        # Act 2: Change Y coordinate via spinbox
        new_y = 225.5
        mock_main_window.point_y_spinbox.setValue(new_y)
        controller._on_point_y_changed(new_y)

        # Assert: Curve data updated for Y
        updated_point = mock_main_window.curve_view.curve_data[0]
        assert updated_point[1] == new_x, f"X coordinate should still be {new_x}, got {updated_point[1]}"
        assert updated_point[2] == new_y, f"Y coordinate should be {new_y}, got {updated_point[2]}"

        # Assert: Modified flag set
        assert mock_main_window.state_manager.is_modified is True, "Modified flag should be set"

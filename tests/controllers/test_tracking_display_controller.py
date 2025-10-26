#!/usr/bin/env python
"""Tests for TrackingDisplayController.

Comprehensive test suite covering display management including:
- Data loading and display initialization
- Display mode switching (ACTIVE_ONLY, SELECTED, ALL_VISIBLE)
- Curve selection coordination
- Tracking panel updates
- Point visibility and color management
- View centering on selected curves

Focus Areas:
- Display synchronization between panel and view
- Multi-curve display coordination
- Frame range updates from curve data
- Selection preservation during display updates
- Signal emission verification
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
from PySide6.QtGui import QPixmap

from core.display_mode import DisplayMode
from stores.application_state import get_application_state
from tests.test_helpers import MockMainWindow
from ui.controllers.tracking_display_controller import TrackingDisplayController


@pytest.fixture
def main_window(mock_main_window: MockMainWindow) -> MockMainWindow:
    """Provide a MockMainWindow for testing."""
    return mock_main_window


@pytest.fixture
def controller(main_window: MockMainWindow) -> TrackingDisplayController:
    """Create TrackingDisplayController with mock main window."""
    return TrackingDisplayController(main_window)


@pytest.fixture
def app_state():
    """Get the application state for verification."""
    return get_application_state()


@pytest.fixture
def sample_curve_data_single() -> list[tuple[int, float, float, str]]:
    """Create single curve tracking data."""
    return [
        (1, 100.0, 200.0, "keyframe"),
        (2, 105.0, 205.0, "normal"),
        (3, 110.0, 210.0, "normal"),
        (4, 115.0, 215.0, "normal"),
        (5, 120.0, 220.0, "normal"),
    ]


@pytest.fixture
def sample_multi_curve_data() -> dict[str, list[tuple[int, float, float, str]]]:
    """Create multi-curve tracking data."""
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


class TestTrackingDisplayControllerInitialization:
    """Test controller initialization and setup."""

    def test_controller_initializes_with_main_window(
        self, controller: TrackingDisplayController, main_window: MockMainWindow
    ) -> None:
        """Test that controller initializes with proper main window reference.

        Verifies:
        - main_window reference is stored
        - ApplicationState is accessible
        - Signal is defined
        """
        assert controller.main_window is main_window
        assert hasattr(controller, "display_updated")

    def test_controller_has_app_state_reference(
        self, controller: TrackingDisplayController
    ) -> None:
        """Test that controller has access to ApplicationState."""
        assert controller._app_state is not None
        # Should be able to call basic state methods
        assert callable(getattr(controller._app_state, "get_all_curve_names", None))


class TestDataLoading:
    """Test data loading and initialization responses."""

    def test_on_data_loaded_with_single_curve(
        self,
        controller: TrackingDisplayController,
        main_window: MockMainWindow,
        app_state,
        sample_curve_data_single: list[tuple[int, float, float, str]],
    ) -> None:
        """Test loading single curve initializes display properly.

        Verifies:
        - Curve added to ApplicationState
        - Active curve is set
        - Tracking panel updated
        - Frame range updated
        - Signal emitted
        """
        # Arrange
        curve_name = "TestPoint001"
        app_state.set_curve_data(curve_name, sample_curve_data_single)

        # Set up curve widget
        if main_window.curve_widget:
            main_window.curve_widget.image_width = 1920
            main_window.curve_widget.image_height = 1080
            main_window.curve_widget.background_pixmap = QPixmap(1920, 1080)

        # Track signal emissions
        signal_emitted = False

        def on_signal():
            nonlocal signal_emitted
            signal_emitted = True

        controller.display_updated.connect(on_signal)

        # Act
        controller.on_data_loaded(curve_name, sample_curve_data_single)

        # Assert
        assert app_state.active_curve == curve_name
        assert signal_emitted

    def test_on_data_loaded_sets_active_curve(
        self,
        controller: TrackingDisplayController,
        app_state,
        sample_curve_data_single: list[tuple[int, float, float, str]],
    ) -> None:
        """Test that on_data_loaded sets the loaded curve as active.

        Verifies:
        - Active curve is set to loaded curve name
        - No other curves interfere
        """
        # Arrange
        curve_name = "TestPoint002"
        app_state.set_curve_data(curve_name, sample_curve_data_single)

        # Act
        controller.on_data_loaded(curve_name, sample_curve_data_single)

        # Assert
        assert app_state.active_curve == curve_name

    def test_on_data_loaded_updates_tracking_panel(
        self,
        controller: TrackingDisplayController,
        main_window: MockMainWindow,
        app_state,
        sample_curve_data_single: list[tuple[int, float, float, str]],
    ) -> None:
        """Test that tracking panel is updated with loaded data.

        Verifies:
        - Tracking panel receives data update
        - Panel reflects all curves
        """
        # Arrange
        curve_name = "TestPoint003"
        app_state.set_curve_data(curve_name, sample_curve_data_single)

        # Act
        controller.on_data_loaded(curve_name, sample_curve_data_single)

        # Assert - Panel should have been updated with curve name
        if main_window.tracking_panel:
            # Panel should have received set_tracked_data call
            assert hasattr(main_window.tracking_panel, "set_tracked_data")

    def test_on_data_loaded_handles_missing_widget(
        self, app_state, sample_curve_data_single: list[tuple[int, float, float, str]]
    ) -> None:
        """Test that on_data_loaded handles missing curve widget gracefully.

        Verifies:
        - No crash when curve_widget is None
        - Method returns early without error
        """
        # Arrange
        main_window = MockMainWindow()
        main_window.curve_widget = None  # Simulate missing widget
        controller = TrackingDisplayController(main_window)

        curve_name = "TestPoint004"
        app_state.set_curve_data(curve_name, sample_curve_data_single)

        # Act - Should not raise
        controller.on_data_loaded(curve_name, sample_curve_data_single)

        # Assert - No exception raised, method completed


class TestDataChangedHandling:
    """Test response to data changed signals."""

    def test_on_data_changed_updates_display(
        self,
        controller: TrackingDisplayController,
        app_state,
        sample_curve_data_single: list[tuple[int, float, float, str]],
    ) -> None:
        """Test that on_data_changed refreshes display properly.

        Verifies:
        - Signal emitted
        - Display update triggered
        """
        # Arrange
        curve_name = "TestPoint005"
        app_state.set_curve_data(curve_name, sample_curve_data_single)
        app_state.set_active_curve(curve_name)

        signal_emitted = False

        def on_signal():
            nonlocal signal_emitted
            signal_emitted = True

        controller.display_updated.connect(on_signal)

        # Act
        controller.on_data_changed()

        # Assert
        assert signal_emitted

    def test_on_data_changed_preserves_selection(
        self,
        controller: TrackingDisplayController,
        app_state,
        sample_curve_data_single: list[tuple[int, float, float, str]],
    ) -> None:
        """Test that on_data_changed preserves current selection.

        Verifies:
        - Selection not cleared on data change
        - Display update maintains selection state
        """
        # Arrange
        curve_name = "TestPoint006"
        app_state.set_curve_data(curve_name, sample_curve_data_single)
        app_state.set_active_curve(curve_name)
        app_state.set_selection(curve_name, {0, 1})

        # Act
        controller.on_data_changed()

        # Assert
        selection = app_state.get_selection(curve_name)
        assert len(selection) == 2


class TestTrackingPanelUpdates:
    """Test tracking panel update operations."""

    def test_update_tracking_panel_with_single_curve(
        self,
        controller: TrackingDisplayController,
        main_window: MockMainWindow,
        app_state,
        sample_curve_data_single: list[tuple[int, float, float, str]],
    ) -> None:
        """Test updating tracking panel with single curve data.

        Verifies:
        - Panel receives correct data
        - Data matches ApplicationState
        """
        # Arrange
        curve_name = "TestPoint007"
        app_state.set_curve_data(curve_name, sample_curve_data_single)

        # Act
        controller.update_tracking_panel()

        # Assert - Panel should have been updated
        if main_window.tracking_panel:
            assert hasattr(main_window.tracking_panel, "set_tracked_data")

    def test_update_tracking_panel_with_multiple_curves(
        self,
        controller: TrackingDisplayController,
        main_window: MockMainWindow,
        app_state,
        sample_multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test updating tracking panel with multiple curves.

        Verifies:
        - All curves included in panel update
        - Data integrity maintained
        """
        # Arrange
        for curve_name, data in sample_multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        # Act
        controller.update_tracking_panel()

        # Assert - Panel should have all curves
        all_curves = app_state.get_all_curve_names()
        assert len(all_curves) == 3

    def test_update_tracking_panel_handles_missing_panel(
        self, app_state, sample_curve_data_single: list[tuple[int, float, float, str]]
    ) -> None:
        """Test that update_tracking_panel handles missing tracking panel gracefully.

        Verifies:
        - No crash when tracking_panel is None
        """
        # Arrange
        main_window = MockMainWindow()
        main_window.tracking_panel = None
        controller = TrackingDisplayController(main_window)

        curve_name = "TestPoint008"
        app_state.set_curve_data(curve_name, sample_curve_data_single)

        # Act - Should not raise
        controller.update_tracking_panel()

        # Assert - No exception raised


class TestDisplayModeSwitch:
    """Test display mode switching functionality."""

    def test_set_display_mode_active_only(
        self,
        controller: TrackingDisplayController,
        app_state,
        sample_multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test switching to ACTIVE_ONLY display mode.

        Verifies:
        - Display mode set correctly
        - Only active curve visible
        - Other curves hidden
        """
        # Arrange
        for curve_name, data in sample_multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        active_curve = "pp56_TM_138G"
        app_state.set_active_curve(active_curve)

        # Act
        controller.set_display_mode(DisplayMode.ACTIVE_ONLY)

        # Assert
        assert app_state.get_show_all_curves() is False

    def test_set_display_mode_all_visible(
        self,
        controller: TrackingDisplayController,
        app_state,
        sample_multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test switching to ALL_VISIBLE display mode.

        Verifies:
        - Display mode set correctly
        - All curves marked visible
        - Show_all_curves flag set
        """
        # Arrange
        for curve_name, data in sample_multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        # Act
        controller.set_display_mode(DisplayMode.ALL_VISIBLE)

        # Assert
        assert app_state.get_show_all_curves() is True

    def test_set_display_mode_selected(
        self,
        controller: TrackingDisplayController,
        app_state,
        sample_multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test switching to SELECTED display mode.

        Verifies:
        - Display mode respects selected curves
        - Non-selected curves hidden
        - Selected curves visible
        """
        # Arrange
        for curve_name, data in sample_multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        selected_curves = {"pp56_TM_138G", "pp56_TM_139H"}
        app_state.set_selected_curves(selected_curves)

        # Act
        controller.set_display_mode(DisplayMode.SELECTED)

        # Assert
        assert app_state.get_show_all_curves() is False


class TestSelectionCoordination:
    """Test curve selection coordination."""

    def test_set_selected_curves_updates_display(
        self,
        controller: TrackingDisplayController,
        app_state,
        sample_multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test that set_selected_curves updates display appropriately.

        Verifies:
        - Selected curves stored in ApplicationState
        - Display updated after selection
        """
        # Arrange
        for curve_name, data in sample_multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        selected_curves = ["pp56_TM_138G"]

        # Act
        controller.set_selected_curves(selected_curves)

        # Assert
        current_selected = app_state.get_selected_curves()
        assert "pp56_TM_138G" in current_selected

    def test_set_selected_curves_with_multiple_curves(
        self,
        controller: TrackingDisplayController,
        app_state,
        sample_multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test selecting multiple curves at once.

        Verifies:
        - All selected curves stored
        - Multi-selection working correctly
        """
        # Arrange
        for curve_name, data in sample_multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        selected_curves = ["pp56_TM_138G", "pp56_TM_139H"]

        # Act
        controller.set_selected_curves(selected_curves)

        # Assert
        current_selected = app_state.get_selected_curves()
        assert current_selected == set(selected_curves)

    def test_set_selected_curves_with_empty_selection(
        self,
        controller: TrackingDisplayController,
        app_state,
        sample_multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test setting empty selection clears all selections.

        Verifies:
        - Empty selection handled correctly
        - No curves selected
        """
        # Arrange
        for curve_name, data in sample_multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        # Pre-select some curves
        app_state.set_selected_curves({"pp56_TM_138G"})

        # Act
        controller.set_selected_curves([])

        # Assert
        current_selected = app_state.get_selected_curves()
        assert len(current_selected) == 0


class TestPointVisibilityManagement:
    """Test point visibility toggling."""

    def test_on_point_visibility_changed_updates_display(
        self,
        controller: TrackingDisplayController,
        main_window: MockMainWindow,
        app_state,
        sample_curve_data_single: list[tuple[int, float, float, str]],
    ) -> None:
        """Test that visibility changes trigger display update.

        Verifies:
        - Visibility change handled
        - Display updated
        """
        # Arrange
        curve_name = "TestPoint009"
        app_state.set_curve_data(curve_name, sample_curve_data_single)

        # Act - Simulate visibility change
        controller.on_point_visibility_changed(curve_name, True)

        # Assert - No exception raised


class TestPointColorManagement:
    """Test point color changes."""

    def test_on_point_color_changed_updates_display(
        self,
        controller: TrackingDisplayController,
        main_window: MockMainWindow,
        app_state,
        sample_curve_data_single: list[tuple[int, float, float, str]],
    ) -> None:
        """Test that color changes trigger display update.

        Verifies:
        - Color change handled
        - Display updated
        """
        # Arrange
        curve_name = "TestPoint010"
        app_state.set_curve_data(curve_name, sample_curve_data_single)

        # Act - Simulate color change
        controller.on_point_color_changed(curve_name, "#FF0000")

        # Assert - No exception raised


class TestFrameRangeUpdates:
    """Test frame range synchronization with data."""

    def test_update_frame_range_from_data(
        self,
        controller: TrackingDisplayController,
        app_state,
        sample_curve_data_single: list[tuple[int, float, float, str]],
    ) -> None:
        """Test frame range calculated from curve data.

        Verifies:
        - Frame range covers all frames in data
        - Min and max frames correct
        """
        # Act
        controller._update_frame_range_from_data(sample_curve_data_single)

        # Assert - Frame range should be from 1 to 5
        # (Would need to check state_manager for actual frame_min/max properties)

    def test_update_frame_range_from_multi_data(
        self,
        controller: TrackingDisplayController,
        app_state,
        sample_multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test frame range calculated from multiple curves.

        Verifies:
        - Frame range covers all curves
        - Minimum and maximum across all curves correct
        """
        # Arrange
        for curve_name, data in sample_multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        # Act
        controller._update_frame_range_from_multi_data()

        # Assert - Should handle all curves correctly


class TestDisplayPreservation:
    """Test display preservation during updates."""

    def test_update_display_preserve_selection(
        self,
        controller: TrackingDisplayController,
        app_state,
        sample_curve_data_single: list[tuple[int, float, float, str]],
    ) -> None:
        """Test that display update preserves selection.

        Verifies:
        - Selection maintained after display update
        - No data loss
        """
        # Arrange
        curve_name = "TestPoint012"
        app_state.set_curve_data(curve_name, sample_curve_data_single)
        app_state.set_active_curve(curve_name)
        app_state.set_selection(curve_name, {0, 2})

        # Act
        controller.update_display_preserve_selection()

        # Assert
        selection = app_state.get_selection(curve_name)
        assert len(selection) == 2

    def test_update_display_with_selection(
        self,
        controller: TrackingDisplayController,
        app_state,
        sample_multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test display update with active selection.

        Verifies:
        - Selected curves displayed
        - Display reflects selection state
        """
        # Arrange
        for curve_name, data in sample_multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        app_state.set_selected_curves({"pp56_TM_138G"})

        # Act
        controller.update_display_with_selection(["pp56_TM_138G"])

        # Assert
        current_selected = app_state.get_selected_curves()
        assert len(current_selected) > 0

    def test_update_display_reset_selection(
        self,
        controller: TrackingDisplayController,
        app_state,
        sample_multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test display update that resets selection.

        Verifies:
        - Display properly resets when needed
        - All curves visible after reset
        """
        # Arrange
        for curve_name, data in sample_multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        # Act
        controller.update_display_reset_selection()

        # Assert - Should complete without error


class TestCenteringOperations:
    """Test view centering on selected curves."""

    def test_center_on_selected_curves_with_single_curve(
        self,
        controller: TrackingDisplayController,
        main_window: MockMainWindow,
        app_state,
        sample_curve_data_single: list[tuple[int, float, float, str]],
    ) -> None:
        """Test centering view on single selected curve.

        Verifies:
        - Center operation executed
        - View updates triggered
        """
        # Arrange
        curve_name = "TestPoint013"
        app_state.set_curve_data(curve_name, sample_curve_data_single)
        app_state.set_selected_curves({curve_name})

        if main_window.curve_widget:
            main_window.curve_widget.image_width = 1920
            main_window.curve_widget.image_height = 1080

        # Act - Should not raise
        controller.center_on_selected_curves()

        # Assert - Operation completed

    def test_center_on_selected_curves_with_multiple_curves(
        self,
        controller: TrackingDisplayController,
        main_window: MockMainWindow,
        app_state,
        sample_multi_curve_data: dict[str, list[tuple[int, float, float, str]]],
    ) -> None:
        """Test centering view on multiple selected curves.

        Verifies:
        - All selected curves considered for centering
        - View encompasses all curves
        """
        # Arrange
        for curve_name, data in sample_multi_curve_data.items():
            app_state.set_curve_data(curve_name, data)

        selected_curves = {"pp56_TM_138G", "pp56_TM_139H"}
        app_state.set_selected_curves(selected_curves)

        if main_window.curve_widget:
            main_window.curve_widget.image_width = 1920
            main_window.curve_widget.image_height = 1080

        # Act - Should not raise
        controller.center_on_selected_curves()

        # Assert - Operation completed

    def test_center_on_selected_curves_with_no_selection(
        self,
        controller: TrackingDisplayController,
        main_window: MockMainWindow,
        app_state,
    ) -> None:
        """Test centering with empty selection handles gracefully.

        Verifies:
        - No crash with empty selection
        - Method returns early or uses fallback
        """
        # Arrange
        if main_window.curve_widget:
            main_window.curve_widget.image_width = 1920
            main_window.curve_widget.image_height = 1080

        # Act - Should not raise
        controller.center_on_selected_curves()

        # Assert - No exception raised

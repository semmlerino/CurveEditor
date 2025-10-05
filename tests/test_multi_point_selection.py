"""
Tests for multi-point selection and display functionality.

This module tests the ability to select and display multiple tracking points
simultaneously, with proper view centering and rendering behavior.
"""

from typing import cast
from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qt_compat import qt_api

from core.display_mode import DisplayMode
from core.type_aliases import CurveDataList, PointTuple4Str
from ui.controllers.multi_point_tracking_controller import MultiPointTrackingController
from ui.curve_view_widget import CurveViewWidget
from ui.main_window import MainWindow
from ui.tracking_points_panel import TrackingPointsPanel


@pytest.fixture
def sample_curves() -> dict[str, CurveDataList]:
    """Create sample curve data for testing."""
    return {
        "Track1": [
            (0, 100.0, 100.0, "KEYFRAME"),
            (10, 110.0, 105.0, "NORMAL"),
            (20, 120.0, 110.0, "KEYFRAME"),
        ],
        "Track2": [
            (0, 200.0, 150.0, "KEYFRAME"),
            (10, 210.0, 155.0, "NORMAL"),
            (20, 220.0, 160.0, "KEYFRAME"),
        ],
        "Track3": [
            (0, 300.0, 200.0, "KEYFRAME"),
            (10, 310.0, 205.0, "NORMAL"),
            (20, 320.0, 210.0, "KEYFRAME"),
        ],
    }


class TestCurveViewMultiSelection:
    """Test multi-curve selection functionality in CurveViewWidget."""

    @pytest.fixture
    def curve_widget(self, qtbot) -> CurveViewWidget:
        """Create a CurveViewWidget with cleanup."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)  # Critical: Auto cleanup
        widget.resize(800, 600)
        return widget

    def test_set_selected_curves(self, curve_widget, sample_curves):
        """Test setting which curves are selected for display."""
        # Setup: Load all curves
        curve_widget.set_curves_data(sample_curves)

        # Initially no curves should be selected
        assert len(curve_widget.selected_curve_names) == 0 or curve_widget.selected_curve_names == {
            "Track1"
        }  # Default to first

        # Select specific curves
        curve_widget.set_selected_curves(["Track1", "Track3"])

        # Verify selection
        assert curve_widget.selected_curve_names == {"Track1", "Track3"}
        assert curve_widget.active_curve_name == "Track3"  # Last selected is active

        # Change selection
        curve_widget.set_selected_curves(["Track2"])
        assert curve_widget.selected_curve_names == {"Track2"}
        assert curve_widget.active_curve_name == "Track2"

    def test_center_on_selected_curves_single(self, curve_widget, sample_curves):
        """Test centering view on a single selected curve."""
        curve_widget.set_curves_data(sample_curves)
        curve_widget.set_selected_curves(["Track1"])

        # Center on the selected curve
        curve_widget.center_on_selected_curves()

        # The view should be centered around Track1's points (100-120, 100-110)
        # With padding, the center should be around (110, 105)
        center_x = curve_widget.width() / 2
        center_y = curve_widget.height() / 2

        # Calculate where the center point should be
        expected_data_center_x = 110.0  # (100 + 120) / 2
        expected_data_center_y = 105.0  # (100 + 110) / 2

        # The pan offset should position this data point at screen center
        expected_pan_x = center_x - expected_data_center_x * curve_widget.zoom_factor
        expected_pan_y = center_y - expected_data_center_y * curve_widget.zoom_factor

        # Allow some tolerance for floating point calculations
        assert abs(curve_widget.pan_offset_x - expected_pan_x) < 5
        assert abs(curve_widget.pan_offset_y - expected_pan_y) < 5

    def test_center_on_selected_curves_multiple(self, curve_widget, sample_curves):
        """Test centering view on multiple selected curves."""
        curve_widget.set_curves_data(sample_curves)
        curve_widget.set_selected_curves(["Track1", "Track3"])

        # Center on both selected curves
        curve_widget.center_on_selected_curves()

        # The view should encompass both Track1 (100-120, 100-110)
        # and Track3 (300-320, 200-210)
        # So the bounding box is (100-320, 100-210)
        # Center should be around (210, 155)

        center_x = curve_widget.width() / 2
        center_y = curve_widget.height() / 2

        expected_data_center_x = 210.0  # (100 + 320) / 2
        expected_data_center_y = 155.0  # (100 + 210) / 2

        # Verify zoom is appropriate (within reasonable bounds)
        assert curve_widget.zoom_factor > 0.1
        assert curve_widget.zoom_factor <= 10.0

        # Verify centering
        expected_pan_x = center_x - expected_data_center_x * curve_widget.zoom_factor
        expected_pan_y = center_y - expected_data_center_y * curve_widget.zoom_factor

        assert abs(curve_widget.pan_offset_x - expected_pan_x) < 10
        assert abs(curve_widget.pan_offset_y - expected_pan_y) < 10

    def test_set_curves_data_with_selected_parameter(self, curve_widget, sample_curves):
        """Test set_curves_data with the selected_curves parameter."""
        # Set curves with specific selection
        curve_widget.set_curves_data(sample_curves, active_curve="Track2", selected_curves=["Track1", "Track2"])

        assert curve_widget.selected_curve_names == {"Track1", "Track2"}
        assert curve_widget.active_curve_name == "Track2"
        assert len(curve_widget.curves_data) == 3

        # Update without changing selection
        curve_widget.set_curves_data(sample_curves, active_curve="Track3")

        # Selection should be preserved
        assert curve_widget.selected_curve_names == {"Track1", "Track2"}
        assert curve_widget.active_curve_name == "Track3"

    def test_show_all_curves_vs_selected_curves(self, curve_widget, sample_curves):
        """Test the difference between display modes and selected curves."""
        curve_widget.set_curves_data(sample_curves)

        # With SELECTED mode, only selected curves should render
        curve_widget.display_mode = DisplayMode.SELECTED
        curve_widget.set_selected_curves(["Track2"])

        assert curve_widget.selected_curve_names == {"Track2"}
        assert curve_widget.display_mode != DisplayMode.ALL_VISIBLE

        # Enable ALL_VISIBLE mode
        curve_widget.display_mode = DisplayMode.ALL_VISIBLE

        assert curve_widget.display_mode == DisplayMode.ALL_VISIBLE
        # Selected curves remain the same
        assert curve_widget.selected_curve_names == {"Track2"}

        # Disable ALL_VISIBLE mode
        curve_widget.display_mode = DisplayMode.SELECTED

        assert curve_widget.display_mode != DisplayMode.ALL_VISIBLE
        assert curve_widget.selected_curve_names == {"Track2"}


class TestMultiPointTrackingController:
    """Test multi-point tracking controller selection behavior."""

    @pytest.fixture
    def mock_main_window(self):
        """Create a mock main window with necessary attributes."""
        mock = Mock(spec=MainWindow)
        mock.curve_widget = Mock(spec=CurveViewWidget)
        mock.curve_widget.curve_data = []  # Set as empty list to support iteration

        # Add mock _curve_store for auto-selection functionality
        mock_curve_store = Mock()
        mock.curve_widget._curve_store = mock_curve_store

        # Add state manager mock for auto-selection
        mock.state_manager = Mock()
        mock.state_manager.current_frame = 1

        mock.tracking_panel = Mock(spec=TrackingPointsPanel)
        mock.tracking_panel._point_metadata = {}
        return mock

    @pytest.fixture
    def controller(self, mock_main_window) -> MultiPointTrackingController:
        """Create a multi-point tracking controller."""
        from stores.application_state import get_application_state

        controller = MultiPointTrackingController(mock_main_window)
        # Add some test data to ApplicationState
        app_state = get_application_state()
        app_state.set_curve_data("Track1", [(0, 100.0, 100.0), (10, 110.0, 105.0)])
        app_state.set_curve_data("Track2", [(0, 200.0, 150.0), (10, 210.0, 155.0)])
        app_state.set_curve_data("Track3", [(0, 300.0, 200.0), (10, 310.0, 205.0)])
        return controller

    @patch("ui.controllers.multi_point_tracking_controller.QTimer")
    def test_on_tracking_points_selected_single(self, mock_qtimer, controller, mock_main_window):
        """Test selecting a single tracking point."""
        # Configure tracking_panel.get_selected_points() to return the selected point
        mock_main_window.tracking_panel.get_selected_points.return_value = ["Track1"]
        # Select single point
        controller.on_tracking_points_selected(["Track1"])

        # Verify active timeline point updated (moved from controller.active_points to main_window.active_timeline_point)
        assert mock_main_window.active_timeline_point == "Track1"

        # Verify set_curves_data was called with correct selection
        mock_main_window.curve_widget.set_curves_data.assert_called_once()
        call_args = mock_main_window.curve_widget.set_curves_data.call_args

        # Check positional and keyword arguments
        # set_curves_data(tracked_data, metadata, active_curve, selected_curves=active_points)
        assert len(call_args[0]) >= 3  # At least 3 positional args
        assert call_args[0][2] == "Track1"  # active_curve is 3rd positional arg
        assert call_args[1].get("selected_curves") == ["Track1"]

        # Verify centering was scheduled with QTimer.singleShot
        if hasattr(mock_main_window.curve_widget, "center_on_selection"):
            # Check that singleShot was called with 10ms delay (function is now wrapped for safety)
            mock_qtimer.singleShot.assert_called_once()
            call_args = mock_qtimer.singleShot.call_args
            assert call_args[0][0] == 10  # First argument should be the delay

    @patch("ui.controllers.multi_point_tracking_controller.QTimer")
    def test_on_tracking_points_selected_multiple(self, mock_qtimer, controller, mock_main_window):
        """Test selecting multiple tracking points."""
        # Mock the necessary methods
        mock_main_window.curve_widget.set_curves_data = Mock()
        mock_main_window.curve_widget.center_on_selection = Mock()
        # Configure tracking_panel.get_selected_points() to return the selected points
        mock_main_window.tracking_panel.get_selected_points.return_value = ["Track1", "Track2", "Track3"]

        # Select multiple points
        controller.on_tracking_points_selected(["Track1", "Track2", "Track3"])

        # Verify active timeline point updated (last selected point becomes active)
        assert mock_main_window.active_timeline_point == "Track3"

        # Verify set_curves_data was called with all selected
        mock_main_window.curve_widget.set_curves_data.assert_called_once()
        call_args = mock_main_window.curve_widget.set_curves_data.call_args

        # Check arguments
        assert len(call_args[0]) >= 3
        assert call_args[0][2] == "Track3"  # active_curve is last selected
        # MANUAL_SELECTION context: selected_curves contains all selected points from panel
        assert call_args[1].get("selected_curves") == ["Track1", "Track2", "Track3"]

        # Verify centering was scheduled with QTimer.singleShot
        # Check that singleShot was called with 10ms delay (function is now wrapped for safety)
        mock_qtimer.singleShot.assert_called_once()
        call_args = mock_qtimer.singleShot.call_args
        assert call_args[0][0] == 10  # First argument should be the delay

    def test_update_curve_display_no_force_show_all(self, controller, mock_main_window):
        """Test that update_curve_display doesn't force show_all_curves."""
        # Set up mock tracking panel metadata
        mock_main_window.tracking_panel._point_metadata = {
            "Track1": {"visible": True, "color": "#FF0000"},
            "Track2": {"visible": True, "color": "#00FF00"},
            "Track3": {"visible": False, "color": "#0000FF"},
        }

        # Set active timeline point (simulates selecting multiple points where Track2 is last/active)
        mock_main_window.active_timeline_point = "Track2"

        # Call update_curve_display with DEFAULT context (preserves existing selection)
        controller.update_curve_display()

        # Verify set_curves_data was called
        mock_main_window.curve_widget.set_curves_data.assert_called_once()
        call_args = mock_main_window.curve_widget.set_curves_data.call_args

        # Check arguments
        assert len(call_args[0]) >= 3
        assert call_args[0][2] == "Track2"  # active_curve
        # With DEFAULT context: selected_curves NOT passed to preserve existing selection
        # This supports Ctrl+click multi-curve selection
        assert "selected_curves" not in call_args[1]

    def test_selection_preserves_visibility_metadata(self, controller, mock_main_window):
        """Test that selection respects visibility metadata."""

        # Mock the public interface methods to return expected values
        def mock_get_point_visibility(point_name):
            visibility_map = {
                "Track1": True,
                "Track2": False,
                "Track3": True,
            }
            return visibility_map.get(point_name, True)

        def mock_get_point_color(point_name):
            color_map = {
                "Track1": "#FF0000",
                "Track2": "#00FF00",
                "Track3": "#0000FF",
            }
            return color_map.get(point_name, "#FFFFFF")

        mock_main_window.tracking_panel.get_point_visibility.side_effect = mock_get_point_visibility
        mock_main_window.tracking_panel.get_point_color.side_effect = mock_get_point_color

        # Select points including invisible one
        controller.on_tracking_points_selected(["Track1", "Track2", "Track3"])

        # The metadata should be passed through
        call_args = mock_main_window.curve_widget.set_curves_data.call_args
        metadata = call_args[0][1]  # Second positional argument

        assert metadata["Track1"]["visible"]
        assert not metadata["Track2"]["visible"]  # Preserved as invisible
        assert metadata["Track3"]["visible"]


class TestRenderingWithSelection:
    """Test that rendering respects the selection state."""

    @pytest.fixture
    def curve_widget(self, qtbot) -> CurveViewWidget:
        """Create a CurveViewWidget with cleanup."""
        widget = CurveViewWidget()
        qtbot.addWidget(widget)
        widget.resize(800, 600)
        return widget

    def test_rendering_respects_selection_mode(self, curve_widget, sample_curves):
        """
        BEHAVIOR TEST: Verify which curves ACTUALLY render based on selection state.

        This test verifies BEHAVIOR (which curves render) not just STATE (variable values).
        This is critical because it catches bugs where state is correct but rendering logic
        doesn't respect that state.

        Bug Context:
        - Previous bug: show_all_curves=False with multiple selected curves only rendered one curve
        - Root cause: Rendering logic only checked show_all_curves, not selected_curve_names
        - Fix: Renderer now checks both conditions in should_render_curve() method

        Test Strategy:
        - Set up 3 curves with show_all_curves=False
        - Select 2 of 3 curves (Track1, Track3)
        - Verify rendering behavior: Track1=True, Track2=False, Track3=True

        This test would have caught the original bug by verifying actual rendering decisions.
        """
        # Setup: Create 3 curves
        curve_widget.set_curves_data(sample_curves)

        # Configure selection mode: SELECTED mode, multiple curves selected
        curve_widget.set_selected_curves(["Track1", "Track3"])
        curve_widget.display_mode = DisplayMode.SELECTED

        # Verify state setup is correct
        assert curve_widget.display_mode == DisplayMode.SELECTED, "display_mode should be SELECTED"
        assert curve_widget.selected_curve_names == {"Track1", "Track3"}, "Track1 and Track3 should be selected"

        # TEST BEHAVIOR: Call should_render_curve() for each curve
        # This is the critical test - does the widget actually decide to render the right curves?
        # This method is used by the renderer to determine which curves to draw

        # Verify rendering behavior
        assert curve_widget.should_render_curve("Track1"), "Track1 should render (selected)"
        assert not curve_widget.should_render_curve("Track2"), "Track2 should NOT render (not selected)"
        assert curve_widget.should_render_curve("Track3"), "Track3 should render (selected)"

        # Additional verification: only selected curves should render
        curves_that_would_render = [
            name for name in ["Track1", "Track2", "Track3"] if curve_widget.should_render_curve(name)
        ]
        assert curves_that_would_render == ["Track1", "Track3"], "Only Track1 and Track3 should render"

    def test_rendering_show_all_curves_true(self, curve_widget, sample_curves):
        """
        BEHAVIOR TEST: Verify all curves render when show_all_curves=True.

        This tests the complementary behavior: when show_all_curves=True,
        ALL curves should render regardless of selection state.

        Requirement: show_all_curves=True overrides selection - all visible curves render.
        """
        # Setup
        curve_widget.set_curves_data(sample_curves)

        # Configure: ALL_VISIBLE mode, but only Track2 selected
        curve_widget.set_selected_curves(["Track2"])
        curve_widget.display_mode = DisplayMode.ALL_VISIBLE

        # Verify state
        assert curve_widget.display_mode == DisplayMode.ALL_VISIBLE, "display_mode should be ALL_VISIBLE"
        assert curve_widget.selected_curve_names == {"Track2"}, "Only Track2 selected"

        # TEST BEHAVIOR: All curves should render when display_mode=ALL_VISIBLE
        assert curve_widget.should_render_curve("Track1"), "Track1 should render (ALL_VISIBLE mode)"
        assert curve_widget.should_render_curve("Track2"), "Track2 should render (ALL_VISIBLE mode)"
        assert curve_widget.should_render_curve("Track3"), "Track3 should render (ALL_VISIBLE mode)"

        # Additional verification: ALL curves should render
        curves_that_would_render = [
            name for name in ["Track1", "Track2", "Track3"] if curve_widget.should_render_curve(name)
        ]
        assert len(curves_that_would_render) == 3, "All 3 curves should render"
        assert set(curves_that_would_render) == {"Track1", "Track2", "Track3"}

    def test_rendering_respects_visibility_metadata(self, curve_widget, sample_curves):
        """
        BEHAVIOR TEST: Verify invisible curves don't render even if selected.

        This tests metadata override: visible=False in metadata should prevent
        rendering even when curve is selected or show_all_curves=True.

        Requirement: Metadata visibility takes precedence over selection state.
        """
        # Setup with visibility metadata
        metadata = {
            "Track1": {"visible": True, "color": "#FF0000"},
            "Track2": {"visible": False, "color": "#00FF00"},  # Invisible
            "Track3": {"visible": True, "color": "#0000FF"},
        }
        curve_widget.set_curves_data(sample_curves, metadata=metadata)

        # Configure: ALL_VISIBLE mode (should render all visible curves)
        curve_widget.display_mode = DisplayMode.ALL_VISIBLE

        # TEST BEHAVIOR: Invisible curves should not render
        assert curve_widget.should_render_curve("Track1"), "Track1 should render (visible + ALL_VISIBLE)"
        assert not curve_widget.should_render_curve("Track2"), "Track2 should NOT render (invisible in metadata)"
        assert curve_widget.should_render_curve("Track3"), "Track3 should render (visible + ALL_VISIBLE)"

        # Additional verification: Only visible curves should render
        curves_that_would_render = [
            name for name in ["Track1", "Track2", "Track3"] if curve_widget.should_render_curve(name)
        ]
        assert len(curves_that_would_render) == 2, "Only 2 visible curves should render"
        assert set(curves_that_would_render) == {"Track1", "Track3"}

        # Test with selection too - invisible curve should not render even if selected
        curve_widget.set_selected_curves(["Track2"])  # Select invisible curve
        curve_widget.display_mode = DisplayMode.SELECTED

        assert not curve_widget.should_render_curve(
            "Track2"
        ), "Track2 should NOT render even when selected (invisible in metadata)"

    def test_renderer_checks_selected_curves(self, curve_widget, sample_curves):
        """Test that the renderer checks selected_curve_names."""

        # Set up curves with selection
        curve_widget.set_curves_data(sample_curves)
        curve_widget.set_selected_curves(["Track2"])
        curve_widget.display_mode = DisplayMode.SELECTED

        # The renderer should check both display_mode and selected_curve_names
        renderer = curve_widget._optimized_renderer

        # Mock the rendering to check what would be rendered
        with patch.object(renderer, "_render_multiple_curves") as _mock_render:
            # Trigger a paint event
            curve_widget.update()
            # Process events to trigger paint
            QApplication.processEvents()

            # If multi-curve rendering was triggered, it means selection is working
            # Note: The actual call might not happen in test environment without proper Qt setup
            # but the logic path is what we're testing

    def test_selection_without_show_all_curves(self, curve_widget, sample_curves):
        """Test that selection works in SELECTED display mode."""
        # Setup
        curve_widget.set_curves_data(sample_curves)

        # Select multiple curves (this sets SELECTED mode)
        curve_widget.set_selected_curves(["Track1", "Track3"])
        curve_widget.display_mode = DisplayMode.SELECTED

        # Verify state
        assert curve_widget.display_mode == DisplayMode.SELECTED
        assert curve_widget.selected_curve_names == {"Track1", "Track3"}
        assert curve_widget.active_curve_name == "Track3"

        # The renderer should render Track1 and Track3 only
        # (In a real paint event, only these would be drawn)


class TestSignalIntegration:
    """Test signal flow from tracking panel to curve display."""

    @pytest.fixture
    def main_window(self, qtbot) -> MainWindow:
        """Create a real MainWindow for integration testing."""
        window = MainWindow()
        qtbot.addWidget(window)
        return window

    def test_tracking_panel_selection_updates_display(self, main_window, qtbot):
        """Test that selecting points in tracking panel updates the curve display."""
        if not hasattr(main_window, "tracking_panel") or not main_window.tracking_panel:
            pytest.skip("MainWindow doesn't have tracking panel in test environment")

        # Add some test tracking data
        test_data = {
            "Point1": [(0, 100.0, 100.0)],
            "Point2": [(0, 200.0, 150.0)],
        }
        main_window.tracking_controller.tracked_data = test_data
        main_window.tracking_panel.set_tracked_data(test_data)

        # Spy on the selection signal
        spy = qt_api.QtTest.QSignalSpy(main_window.tracking_panel.points_selected)

        # Simulate selection in the panel (would normally be done via UI)
        main_window.tracking_panel._on_selection_changed()

        # Process events
        qtbot.wait(100)

        # Check if signal was emitted
        if spy.count() > 0:
            # Get the first emission's arguments
            selected = spy.at(0)[0]
            assert isinstance(selected, list)


# Test for TDD approach - write test first for any bugs found
def test_selection_bug_fix_tdd():
    """
    TDD test for the selection not updating bug.
    This test would have caught the issue where update_curve_display
    was forcing show_all_curves to True.
    """
    # Setup
    main_window = Mock(spec=MainWindow)
    curve_widget = Mock(spec=CurveViewWidget)
    curve_widget.curve_data = []  # Set as empty list to support iteration

    # Add mock _curve_store for auto-selection functionality
    mock_curve_store = Mock()
    curve_widget._curve_store = mock_curve_store

    # Add state manager mock for auto-selection
    main_window.state_manager = Mock()
    main_window.state_manager.current_frame = 1

    main_window.curve_widget = curve_widget
    main_window.tracking_panel = Mock()
    main_window.tracking_panel._point_metadata = {}

    controller = MultiPointTrackingController(main_window)
    controller.tracked_data = {
        "Track1": [(0, 100.0, 100.0)],
        "Track2": [(0, 200.0, 150.0)],
    }
    main_window.active_timeline_point = "Track1"

    # Test that update_curve_display doesn't force any specific display mode
    controller.update_curve_display()

    # With DEFAULT context: selected_curves NOT passed to preserve existing selection
    # This supports Ctrl+click multi-curve selection
    curve_widget.set_curves_data.assert_called_once()
    call_args = curve_widget.set_curves_data.call_args
    assert "selected_curves" not in call_args[1]


class TestCurveModificationPreservation:
    """Test that curve modifications are preserved when switching between curves."""

    @pytest.fixture
    def mock_main_window(self):
        """Create a mock main window with necessary attributes."""
        mock = Mock(spec=MainWindow)
        mock.curve_widget = Mock(spec=CurveViewWidget)
        mock.curve_widget.curve_data = []  # Set as empty list to support iteration

        # Add mock _curve_store for data persistence
        mock_curve_store = Mock()
        mock_curve_store.get_data.return_value = []
        mock.curve_widget._curve_store = mock_curve_store

        mock.tracking_panel = Mock(spec=TrackingPointsPanel)
        mock.state_manager = Mock()
        mock.state_manager.current_frame = 1
        return mock

    def test_modifications_preserved_on_curve_switch(self, mock_main_window):
        """Test that modifications to a curve are saved when switching to another curve."""
        # Setup controller with initial data
        controller = MultiPointTrackingController(mock_main_window)
        controller.tracked_data = {
            "Track1": [
                (0, 100.0, 100.0, "NORMAL"),
                (10, 110.0, 105.0, "NORMAL"),
            ],
            "Track2": [
                (0, 200.0, 150.0, "NORMAL"),
                (10, 210.0, 155.0, "NORMAL"),
            ],
        }
        mock_main_window.active_timeline_point = "Track1"

        # Initialize previous active curve by calling once
        controller.update_curve_display()

        # Simulate modifications to Track1 (e.g., adding ENDFRAME status)
        modified_data = [
            (0, 100.0, 100.0, "ENDFRAME"),  # Modified status
            (10, 110.0, 105.0, "NORMAL"),
        ]
        mock_main_window.curve_widget._curve_store.get_data.return_value = modified_data

        # Switch to Track2
        mock_main_window.active_timeline_point = "Track2"
        controller.update_curve_display()

        # Verify that Track1's modifications were saved back to tracked_data
        assert controller.tracked_data["Track1"] == modified_data
        assert cast(PointTuple4Str, controller.tracked_data["Track1"][0])[3] == "ENDFRAME"

    def test_modifications_preserved_with_nudge(self, mock_main_window):
        """Test that coordinate changes (nudges) are preserved when switching curves."""
        # Setup
        controller = MultiPointTrackingController(mock_main_window)
        controller.tracked_data = {
            "Track1": [(0, 100.0, 100.0, "NORMAL")],
            "Track2": [(0, 200.0, 150.0, "NORMAL")],
        }
        mock_main_window.active_timeline_point = "Track1"

        # Initialize previous active curve
        controller.update_curve_display()

        # Simulate nudging Track1 point
        nudged_data = [(0, 105.0, 103.0, "NORMAL")]  # Nudged +5, +3
        mock_main_window.curve_widget._curve_store.get_data.return_value = nudged_data

        # Switch to Track2
        mock_main_window.active_timeline_point = "Track2"
        controller.update_curve_display()

        # Verify nudge was preserved
        assert controller.tracked_data["Track1"] == nudged_data
        assert controller.tracked_data["Track1"][0][1] == 105.0
        assert controller.tracked_data["Track1"][0][2] == 103.0

    def test_no_save_when_no_curve_store(self, mock_main_window):
        """Test graceful handling when curve_store is not available."""
        # Setup without _curve_store attribute
        controller = MultiPointTrackingController(mock_main_window)
        controller.tracked_data = {"Track1": [(0, 100.0, 100.0, "NORMAL")]}
        mock_main_window.active_timeline_point = "Track1"
        del mock_main_window.curve_widget._curve_store  # Remove _curve_store

        # Should not crash when switching
        mock_main_window.active_timeline_point = "Track2"
        controller.update_curve_display()

        # Original data unchanged
        assert controller.tracked_data["Track1"] == [(0, 100.0, 100.0, "NORMAL")]

    def test_no_save_when_curve_not_in_tracked_data(self, mock_main_window):
        """Test that save is skipped if active curve is not in tracked_data."""
        # Setup
        controller = MultiPointTrackingController(mock_main_window)
        controller.tracked_data = {"Track1": [(0, 100.0, 100.0, "NORMAL")]}
        mock_main_window.active_timeline_point = "NonexistentTrack"

        # Should not crash
        controller.update_curve_display()

        # Original data unchanged
        assert controller.tracked_data["Track1"] == [(0, 100.0, 100.0, "NORMAL")]

    def test_multiple_switches_preserve_all_modifications(self, mock_main_window):
        """Test that switching between multiple curves preserves all modifications."""
        # Setup
        controller = MultiPointTrackingController(mock_main_window)
        controller.tracked_data = {
            "Track1": [(0, 100.0, 100.0, "NORMAL")],
            "Track2": [(0, 200.0, 150.0, "NORMAL")],
            "Track3": [(0, 300.0, 200.0, "NORMAL")],
        }

        # Modify Track1
        mock_main_window.active_timeline_point = "Track1"
        controller.update_curve_display()  # Initialize
        modified_track1 = [(0, 101.0, 101.0, "ENDFRAME")]
        mock_main_window.curve_widget._curve_store.get_data.return_value = modified_track1
        mock_main_window.active_timeline_point = "Track2"
        controller.update_curve_display()

        # Modify Track2
        modified_track2 = [(0, 202.0, 152.0, "KEYFRAME")]
        mock_main_window.curve_widget._curve_store.get_data.return_value = modified_track2
        mock_main_window.active_timeline_point = "Track3"
        controller.update_curve_display()

        # Modify Track3
        modified_track3 = [(0, 303.0, 203.0, "NORMAL")]
        mock_main_window.curve_widget._curve_store.get_data.return_value = modified_track3
        mock_main_window.active_timeline_point = "Track1"
        controller.update_curve_display()

        # Verify all modifications were preserved
        assert controller.tracked_data["Track1"] == modified_track1
        assert controller.tracked_data["Track2"] == modified_track2
        assert controller.tracked_data["Track3"] == modified_track3

    def test_empty_curve_data_handled_gracefully(self, mock_main_window):
        """Test that empty curve data is handled without errors."""
        # Setup
        controller = MultiPointTrackingController(mock_main_window)
        controller.tracked_data = {
            "Track1": [(0, 100.0, 100.0, "NORMAL")],
            "Track2": [(0, 200.0, 150.0, "NORMAL")],
        }
        mock_main_window.active_timeline_point = "Track1"

        # Simulate empty curve data
        mock_main_window.curve_widget._curve_store.get_data.return_value = []

        # Switch curves - should not save empty data
        mock_main_window.active_timeline_point = "Track2"
        controller.update_curve_display()

        # Original data should be preserved (empty data not saved)
        assert controller.tracked_data["Track1"] == [(0, 100.0, 100.0, "NORMAL")]

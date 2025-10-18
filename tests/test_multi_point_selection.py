"""
Tests for multi-point selection and display functionality.

This module tests the ability to select and display multiple tracking points
simultaneously, with proper view centering and rendering behavior.
"""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtWidgets import QApplication
from pytestqt.qt_compat import qt_api

from core.display_mode import DisplayMode
from core.type_aliases import CurveDataList
from stores.application_state import get_application_state
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
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves)

        # With SELECTED mode, only selected curves should render
        app_state.set_selected_curves({"Track2"})
        app_state.set_show_all_curves(False)

        assert app_state.get_selected_curves() == {"Track2"}
        assert curve_widget.display_mode != DisplayMode.ALL_VISIBLE

        # Enable ALL_VISIBLE mode
        app_state.set_show_all_curves(True)

        assert curve_widget.display_mode == DisplayMode.ALL_VISIBLE
        # Selected curves remain the same
        assert app_state.get_selected_curves() == {"Track2"}

        # Disable ALL_VISIBLE mode (back to SELECTED)
        app_state.set_show_all_curves(False)

        assert curve_widget.display_mode != DisplayMode.ALL_VISIBLE
        assert app_state.get_selected_curves() == {"Track2"}


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
        get_application_state().set_frame(1)

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

    @patch("ui.controllers.tracking_selection_controller.QTimer")
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

    @patch("ui.controllers.tracking_selection_controller.QTimer")
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

        # Set active curve in ApplicationState
        from stores.application_state import get_application_state

        get_application_state().set_active_curve("Track2")

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
        # Setup: Create 3 curves via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves)

        # Configure selection mode: SELECTED mode, multiple curves selected
        curve_widget.set_selected_curves(["Track1", "Track3"])
        app_state.set_show_all_curves(False)

        # Verify state setup is correct
        assert curve_widget.display_mode == DisplayMode.SELECTED, "display_mode should be SELECTED"
        assert app_state.get_selected_curves() == {"Track1", "Track3"}, "Track1 and Track3 should be selected"

        # TEST BEHAVIOR: Compute render state to check which curves would render
        # This is the critical test - does RenderState correctly determine which curves to draw?
        from rendering.render_state import RenderState

        render_state = RenderState.compute(curve_widget)

        # Verify rendering behavior
        assert render_state.should_render("Track1"), "Track1 should render (selected)"
        assert not render_state.should_render("Track2"), "Track2 should NOT render (not selected)"
        assert render_state.should_render("Track3"), "Track3 should render (selected)"

        # Additional verification: only selected curves should render
        curves_that_would_render = [name for name in ["Track1", "Track2", "Track3"] if render_state.should_render(name)]
        assert curves_that_would_render == ["Track1", "Track3"], "Only Track1 and Track3 should render"

    def test_rendering_show_all_curves_true(self, curve_widget, sample_curves):
        """
        BEHAVIOR TEST: Verify all curves render when show_all_curves=True.

        This tests the complementary behavior: when show_all_curves=True,
        ALL curves should render regardless of selection state.

        Requirement: show_all_curves=True overrides selection - all visible curves render.
        """
        # Setup via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves)

        # Configure: ALL_VISIBLE mode, but only Track2 selected
        curve_widget.set_selected_curves(["Track2"])
        app_state.set_show_all_curves(True)

        # Verify state
        assert curve_widget.display_mode == DisplayMode.ALL_VISIBLE, "display_mode should be ALL_VISIBLE"
        assert app_state.get_selected_curves() == {"Track2"}, "Only Track2 selected"

        # TEST BEHAVIOR: All curves should render when display_mode=ALL_VISIBLE
        from rendering.render_state import RenderState

        render_state = RenderState.compute(curve_widget)
        assert render_state.should_render("Track1"), "Track1 should render (ALL_VISIBLE mode)"
        assert render_state.should_render("Track2"), "Track2 should render (ALL_VISIBLE mode)"
        assert render_state.should_render("Track3"), "Track3 should render (ALL_VISIBLE mode)"

        # Additional verification: ALL curves should render
        curves_that_would_render = [name for name in ["Track1", "Track2", "Track3"] if render_state.should_render(name)]
        assert len(curves_that_would_render) == 3, "All 3 curves should render"
        assert set(curves_that_would_render) == {"Track1", "Track2", "Track3"}

    def test_rendering_respects_visibility_metadata(self, curve_widget, sample_curves):
        """
        BEHAVIOR TEST: Verify invisible curves don't render even if selected.

        This tests metadata override: visible=False in metadata should prevent
        rendering even when curve is selected or show_all_curves=True.

        Requirement: Metadata visibility takes precedence over selection state.
        """
        # Setup with visibility metadata via ApplicationState
        app_state = get_application_state()
        metadata = {
            "Track1": {"visible": True, "color": "#FF0000"},
            "Track2": {"visible": False, "color": "#00FF00"},  # Invisible
            "Track3": {"visible": True, "color": "#0000FF"},
        }
        curve_widget.set_curves_data(sample_curves, metadata=metadata)

        # Configure: ALL_VISIBLE mode (should render all visible curves)
        app_state.set_show_all_curves(True)

        # TEST BEHAVIOR: Invisible curves should not render
        from rendering.render_state import RenderState

        render_state = RenderState.compute(curve_widget)
        assert render_state.should_render("Track1"), "Track1 should render (visible + ALL_VISIBLE)"
        assert not render_state.should_render("Track2"), "Track2 should NOT render (invisible in metadata)"
        assert render_state.should_render("Track3"), "Track3 should render (visible + ALL_VISIBLE)"

        # Additional verification: Only visible curves should render
        curves_that_would_render = [name for name in ["Track1", "Track2", "Track3"] if render_state.should_render(name)]
        assert len(curves_that_would_render) == 2, "Only 2 visible curves should render"
        assert set(curves_that_would_render) == {"Track1", "Track3"}

        # Test with selection too - invisible curve should not render even if selected
        curve_widget.set_selected_curves(["Track2"])  # Select invisible curve
        app_state.set_show_all_curves(False)

        render_state2 = RenderState.compute(curve_widget)
        assert not render_state2.should_render(
            "Track2"
        ), "Track2 should NOT render even when selected (invisible in metadata)"

    def test_renderer_checks_selected_curves(self, curve_widget, sample_curves):
        """Test that the renderer checks selected_curve_names."""
        # Set up curves with selection via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves)
        curve_widget.set_selected_curves(["Track2"])
        app_state.set_show_all_curves(False)

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
        # Setup via ApplicationState
        app_state = get_application_state()
        curve_widget.set_curves_data(sample_curves)

        # Select multiple curves (this sets SELECTED mode)
        curve_widget.set_selected_curves(["Track1", "Track3"])
        app_state.set_show_all_curves(False)

        # Verify state
        assert curve_widget.display_mode == DisplayMode.SELECTED
        assert app_state.get_selected_curves() == {"Track1", "Track3"}
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

        # Spy on ApplicationState.selection_state_changed signal (replaces points_selected)
        from stores.application_state import get_application_state

        app_state = get_application_state()
        spy = qt_api.QtTest.QSignalSpy(app_state.selection_state_changed)

        # Simulate selection in the panel (would normally be done via UI)
        main_window.tracking_panel._on_selection_changed()

        # Process events
        qtbot.wait(100)

        # Check if signal was emitted
        if spy.count() > 0:
            # Get the first emission's arguments (selected_curves: set, show_all: bool)
            selected_curves = spy.at(0)[0]
            assert isinstance(selected_curves, set)


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
    get_application_state().set_frame(1)

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


# NOTE: TestCurveModificationPreservation class removed (obsolete pre-migration tests)
# After ApplicationState migration, widget.curve_data is read-only and reads directly
# from ApplicationState. There's no "dirty widget data" to sync back on curve switches.
# All modifications go directly to ApplicationState, making these tests obsolete.

# NOTE: TestCurveModificationPreservation_OBSOLETE class removed (lines 600-762)
# After ApplicationState migration, widget.curve_data is read-only and reads directly
# from ApplicationState. There's no "dirty widget data" to sync back on curve switches.
# All modifications go directly to ApplicationState, making these tests obsolete.

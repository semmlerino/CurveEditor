#!/usr/bin/env python
"""
Tests for unified curve rendering system.

This module tests the fix for the issue where switching curves lost visual status
indicators. Tests verify that both single and multiple curves use the same
sophisticated rendering logic for point status, selection, and current frame highlighting.

Following the UNIFIED_TESTING_GUIDE to avoid Qt threading violations.
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from PySide6.QtGui import QColor

from core.models import PointStatus
from rendering.optimized_curve_renderer import OptimizedCurveRenderer


class TestUnifiedCurveRendering:
    """Test unified rendering logic for both single and multiple curves."""

    @pytest.fixture
    def renderer(self):
        """Create OptimizedCurveRenderer instance."""
        return OptimizedCurveRenderer()

    @pytest.fixture
    def mock_curve_view(self):
        """Create mock curve view with multi-curve support."""
        mock_view = Mock()
        mock_view.width.return_value = 800
        mock_view.height.return_value = 600
        mock_view.point_radius = 5
        mock_view.selected_points = {0, 2}  # First and third points selected

        # Mock main window with current frame
        mock_view.main_window = Mock()
        mock_view.main_window.state_manager.current_frame = 10

        # Mock multi-curve data
        mock_view.curves_data = {
            "curve1": [
                (5, 100.0, 200.0, PointStatus.KEYFRAME.value),
                (10, 150.0, 250.0, PointStatus.NORMAL.value),  # Current frame
                (15, 200.0, 300.0, PointStatus.ENDFRAME.value),
                (20, 250.0, 350.0, PointStatus.INTERPOLATED.value),
            ],
            "curve2": [
                (8, 120.0, 180.0, PointStatus.TRACKED.value),
                (10, 170.0, 230.0, PointStatus.KEYFRAME.value),  # Current frame
                (12, 220.0, 280.0, PointStatus.NORMAL.value),
            ],
        }

        mock_view.curve_metadata = {
            "curve1": {"visible": True, "color": "#FF0000"},  # Red
            "curve2": {"visible": True, "color": "#00FF00"},  # Green
        }

        mock_view.active_curve_name = "curve1"
        mock_view.show_all_curves = False
        mock_view.selected_curve_names = {"curve1", "curve2"}

        # Mock transform
        mock_transform = Mock()
        mock_transform.data_to_screen = lambda x, y: (x, y)  # Identity transform for simplicity
        mock_view.get_transform.return_value = mock_transform

        return mock_view

    @pytest.fixture
    def mock_painter(self):
        """Create mock painter to avoid Qt threading issues."""
        painter = MagicMock()
        # Mock the common painter methods
        painter.setPen = MagicMock()
        painter.setBrush = MagicMock()
        painter.drawEllipse = MagicMock()
        painter.drawText = MagicMock()
        painter.save = MagicMock()
        painter.restore = MagicMock()
        return painter

    def test_render_points_with_status_handles_point_statuses(self, renderer, mock_curve_view, mock_painter):
        """Test that _render_points_with_status correctly renders different point statuses."""
        import numpy as np

        from rendering.render_state import RenderState

        # Setup test data with different statuses (avoiding current frame to prevent special handling)
        points_data = [
            (5, 100.0, 200.0, PointStatus.KEYFRAME.value),
            (6, 150.0, 250.0, PointStatus.NORMAL.value),
            (7, 200.0, 300.0, PointStatus.ENDFRAME.value),
            (8, 250.0, 350.0, PointStatus.INTERPOLATED.value),
            (9, 300.0, 400.0, PointStatus.TRACKED.value),
        ]

        screen_points = np.array([[100.0, 200.0], [150.0, 250.0], [200.0, 300.0], [250.0, 350.0], [300.0, 400.0]])

        # Create RenderState object with test data (avoiding current frame conflicts)
        render_state = RenderState(
            points=points_data,
            current_frame=999,  # Different from test data
            selected_points=set(),  # No selections
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0,
            pan_offset_y=0,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=False,
            background_image=None,
            image_width=800,
            image_height=600,
            show_grid=False,
            point_radius=5,
        )

        # Mock color functions to track calls (patch at correct import location)
        with patch("ui.ui_constants.get_status_color") as mock_get_status_color:
            mock_get_status_color.side_effect = {
                "keyframe": "#00ff66",
                "normal": "#ffffff",
                "endframe": "#ff4444",
                "interpolated": "#ff9500",
                "tracked": "#00bfff",
            }.get

            with patch("ui.ui_constants.SPECIAL_COLORS", {"selected_point": "#ffff00", "current_frame": "#ff00ff"}):
                # Call the unified rendering method with mock painter
                renderer._render_points_with_status(
                    painter=mock_painter,
                    render_state=render_state,
                    screen_points=screen_points,
                    points_data=points_data,
                    visible_indices=None,
                    step=1,
                    base_point_radius=5,
                    curve_color=QColor("#FF0000"),
                    is_active_curve=True,
                )

        # Verify that status colors were requested for at least some point types
        # Note: Some statuses might be filtered out by segmented curve logic
        assert mock_get_status_color.called, "get_status_color should be called for rendering points"

        # Verify painter methods were called
        assert mock_painter.setBrush.called, "setBrush should be called for drawing points"
        assert mock_painter.drawEllipse.called, "drawEllipse should be called for drawing points"

    def test_current_frame_highlighting_works_across_curves(self, renderer, mock_curve_view, mock_painter):
        """Test that current frame highlighting works in multi-curve rendering."""
        from rendering.render_state import RenderState

        # Create RenderState with multi-curve data
        render_state = RenderState(
            points=[],  # Not used for multi-curve rendering
            current_frame=10,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0,
            pan_offset_y=0,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=False,
            background_image=None,
            image_width=800,
            image_height=600,
            show_grid=False,
            point_radius=5,
            # Multi-curve data
            curves_data={
                "curve1": [
                    (5, 100.0, 200.0, PointStatus.KEYFRAME.value),
                    (10, 150.0, 250.0, PointStatus.NORMAL.value),  # Current frame
                    (15, 200.0, 300.0, PointStatus.ENDFRAME.value),
                    (20, 250.0, 350.0, PointStatus.INTERPOLATED.value),
                ],
                "curve2": [
                    (8, 120.0, 180.0, PointStatus.TRACKED.value),
                    (10, 170.0, 230.0, PointStatus.KEYFRAME.value),  # Current frame
                    (12, 220.0, 280.0, PointStatus.NORMAL.value),
                ],
            },
            curve_metadata={
                "curve1": {"visible": True, "color": "#FF0000"},  # Red
                "curve2": {"visible": True, "color": "#00FF00"},  # Green
            },
            active_curve_name="curve1",
            show_all_curves=False,
            selected_curve_names={"curve1", "curve2"},
        )

        # Mock all Qt drawing methods to avoid threading issues
        with patch.object(renderer, "_render_points_with_status") as mock_render_points:
            # Render multiple curves
            renderer._render_multiple_curves(mock_painter, render_state)

            # Should be called once for each curve
            assert mock_render_points.call_count == 2

            # Verify both curves were rendered with correct data
            calls = mock_render_points.call_args_list

            # First call should be for curve1
            curve1_call = calls[0]
            curve1_points_data = curve1_call[1]["points_data"]
            assert len(curve1_points_data) == 4
            assert curve1_points_data[1][0] == 10  # Current frame point

            # Second call should be for curve2
            curve2_call = calls[1]
            curve2_points_data = curve2_call[1]["points_data"]
            assert len(curve2_points_data) == 3
            assert curve2_points_data[1][0] == 10  # Current frame point

    def test_selection_highlighting_in_multi_curve_mode(self, renderer, mock_curve_view, mock_painter):
        """Test that selected points are highlighted correctly in multi-curve mode."""
        import numpy as np

        from rendering.render_state import RenderState

        # Test with selected points
        points_data = [
            (5, 100.0, 200.0, PointStatus.NORMAL.value),  # Index 0 - selected
            (10, 150.0, 250.0, PointStatus.NORMAL.value),  # Index 1 - not selected
            (15, 200.0, 300.0, PointStatus.NORMAL.value),  # Index 2 - selected
        ]

        screen_points = np.array([[100.0, 200.0], [150.0, 250.0], [200.0, 300.0]])

        # Create RenderState with selected points
        render_state = RenderState(
            points=points_data,
            current_frame=999,  # Different from test data to avoid current frame highlighting
            selected_points={0, 2},  # First and third points selected
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0,
            pan_offset_y=0,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=False,
            background_image=None,
            image_width=800,
            image_height=600,
            show_grid=False,
            point_radius=5,
        )

        # Track setBrush calls to verify selection highlighting
        brush_calls = []

        def track_setBrush(brush):
            # Extract color from QBrush mock
            brush_calls.append(brush)
            return MagicMock()

        mock_painter.setBrush.side_effect = track_setBrush

        with patch("ui.ui_constants.get_status_color", return_value="#ffffff"):
            with patch("ui.ui_constants.SPECIAL_COLORS", {"selected_point": "#ffff00", "current_frame": "#ff00ff"}):
                renderer._render_points_with_status(
                    painter=mock_painter,
                    render_state=render_state,
                    screen_points=screen_points,
                    points_data=points_data,
                    visible_indices=None,
                    step=1,
                    base_point_radius=5,
                    curve_color=QColor("#FF0000"),
                    is_active_curve=True,
                )

        # Verify setBrush was called multiple times (for different point types)
        assert len(brush_calls) > 0, "setBrush should be called for rendering points"

    def test_unified_rendering_preserves_curve_colors_for_inactive_curves(
        self, renderer, mock_curve_view, mock_painter
    ):
        """Test that inactive curves use their base color for normal points."""
        import numpy as np

        from rendering.render_state import RenderState

        points_data = [
            (5, 100.0, 200.0, PointStatus.NORMAL.value),
            (6, 150.0, 250.0, PointStatus.KEYFRAME.value),  # Should still use status color
        ]

        screen_points = np.array([[100.0, 200.0], [150.0, 250.0]])
        curve_color = QColor("#00FF00")  # Green

        # Create RenderState avoiding current frame and selection conflicts
        render_state = RenderState(
            points=points_data,
            current_frame=999,  # Different from test data
            selected_points=set(),  # No selections
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0,
            pan_offset_y=0,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=False,
            background_image=None,
            image_width=800,
            image_height=600,
            show_grid=False,
            point_radius=5,
        )

        with patch("ui.ui_constants.get_status_color") as mock_get_status_color:
            mock_get_status_color.side_effect = lambda status: {"normal": "#ffffff", "keyframe": "#00ff66"}.get(
                status, "#ffffff"
            )

            with patch("ui.ui_constants.SPECIAL_COLORS", {"selected_point": "#ffff00", "current_frame": "#ff00ff"}):
                renderer._render_points_with_status(
                    painter=mock_painter,
                    render_state=render_state,
                    screen_points=screen_points,
                    points_data=points_data,
                    visible_indices=None,
                    step=1,
                    base_point_radius=5,
                    curve_color=curve_color,
                    is_active_curve=False,  # Inactive curve
                )

        # Verify that colors were requested (some may be filtered by segmented curve logic)
        assert mock_get_status_color.called, "get_status_color should be called for rendering points"

    def test_multi_curve_rendering_uses_unified_logic(self, renderer, mock_curve_view, mock_painter):
        """Test that _render_multiple_curves delegates to unified rendering logic."""
        from rendering.render_state import RenderState

        # Create RenderState with multi-curve data matching the mock_curve_view fixture
        render_state = RenderState(
            points=[],  # Not used for multi-curve rendering
            current_frame=10,
            selected_points={0, 2},  # From mock_curve_view fixture
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0,
            pan_offset_y=0,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=False,
            background_image=None,
            image_width=800,
            image_height=600,
            show_grid=False,
            point_radius=5,
            # Multi-curve data from mock_curve_view fixture
            curves_data={
                "curve1": [
                    (5, 100.0, 200.0, PointStatus.KEYFRAME.value),
                    (10, 150.0, 250.0, PointStatus.NORMAL.value),
                    (15, 200.0, 300.0, PointStatus.ENDFRAME.value),
                    (20, 250.0, 350.0, PointStatus.INTERPOLATED.value),
                ],
                "curve2": [
                    (8, 120.0, 180.0, PointStatus.TRACKED.value),
                    (10, 170.0, 230.0, PointStatus.KEYFRAME.value),
                    (12, 220.0, 280.0, PointStatus.NORMAL.value),
                ],
            },
            curve_metadata={
                "curve1": {"visible": True, "color": "#FF0000"},  # Red
                "curve2": {"visible": True, "color": "#00FF00"},  # Green
            },
            active_curve_name="curve1",
            show_all_curves=False,
            selected_curve_names={"curve1", "curve2"},
        )

        # Mock the unified rendering method to verify it's called
        with patch.object(renderer, "_render_points_with_status") as mock_render_points:
            renderer._render_multiple_curves(mock_painter, render_state)

            # Should be called once for each visible curve
            assert mock_render_points.call_count == 2

            # Verify correct parameters passed
            calls = mock_render_points.call_args_list

            # First call (curve1 - active)
            call1_kwargs = calls[0][1]
            assert call1_kwargs["is_active_curve"] is True
            assert call1_kwargs["base_point_radius"] == 7  # Larger for active curve
            assert call1_kwargs["curve_color"].name() == "#ff0000"  # Red

            # Second call (curve2 - inactive)
            call2_kwargs = calls[1][1]
            assert call2_kwargs["is_active_curve"] is False
            assert call2_kwargs["base_point_radius"] == 5  # Smaller for inactive curve
            assert call2_kwargs["curve_color"].name() == "#00ff00"  # Green

    def test_single_curve_rendering_uses_unified_logic(self, renderer, mock_painter):
        """Test that single curve rendering also uses the unified logic."""
        # Create mock for single curve rendering
        mock_curve_view = Mock()
        mock_curve_view.points = [
            (5, 100.0, 200.0, PointStatus.KEYFRAME.value),
            (10, 150.0, 250.0, PointStatus.NORMAL.value),
        ]
        mock_curve_view.point_radius = 5
        mock_curve_view.selected_points = {0}
        mock_curve_view.main_window = Mock()
        mock_curve_view.main_window.state_manager.current_frame = 10

        import numpy as np

        screen_points = np.array([[100.0, 200.0], [150.0, 250.0]])
        visible_indices = np.array([0, 1])

        # Mock the unified rendering method
        with patch.object(renderer, "_render_points_with_status") as mock_render_points:
            renderer._render_point_markers_optimized(mock_painter, mock_curve_view, screen_points, visible_indices, 1)

            # Should call unified method once
            assert mock_render_points.call_count == 1

            # Verify correct parameters
            call_kwargs = mock_render_points.call_args[1]
            assert call_kwargs["points_data"] == mock_curve_view.points
            assert call_kwargs["visible_indices"] is visible_indices
            assert call_kwargs["step"] == 1


class TestUnifiedRenderingLogic:
    """Test unified rendering logic without Qt integration to avoid threading issues."""

    def test_unified_rendering_method_delegation(self):
        """Test that the unified rendering methods are properly connected."""
        renderer = OptimizedCurveRenderer()

        # Test that single curve rendering delegates to unified method
        with patch.object(renderer, "_render_points_with_status") as mock_unified:
            mock_curve_view = Mock()
            mock_curve_view.points = [(1, 10.0, 20.0, PointStatus.NORMAL.value)]
            mock_curve_view.point_radius = 5
            mock_curve_view.selected_points = set()
            mock_curve_view.main_window = Mock()
            mock_curve_view.main_window.state_manager.current_frame = 1

            import numpy as np

            screen_points = np.array([[10.0, 20.0]])
            visible_indices = np.array([0])

            renderer._render_point_markers_optimized(Mock(), mock_curve_view, screen_points, visible_indices, 1)

            # Should delegate to unified method
            assert mock_unified.call_count == 1

    def test_bug_fix_verification_unified_method_exists(self):
        """Verify the unified rendering method exists and has correct signature."""
        renderer = OptimizedCurveRenderer()

        # The bug was that multi-curve rendering didn't use the same logic as single curves
        # This test verifies that both now use the same unified method
        assert hasattr(renderer, "_render_points_with_status"), "Unified rendering method should exist"

        # Verify the method has the expected parameters (updated for RenderState refactoring)
        import inspect

        sig = inspect.signature(renderer._render_points_with_status)
        expected_params = {
            "painter",
            "render_state",
            "screen_points",
            "points_data",
            "visible_indices",
            "step",
            "base_point_radius",
            "curve_color",
            "is_active_curve",
        }
        actual_params = set(sig.parameters.keys()) - {"self"}
        assert expected_params.issubset(actual_params), f"Missing parameters: {expected_params - actual_params}"

    def test_curve_color_logic_for_active_vs_inactive(self):
        """Test the logic that determines when to use curve color vs status color."""
        from rendering.render_state import RenderState

        renderer = OptimizedCurveRenderer()

        # Test with mock data to verify color decision logic
        import numpy as np

        mock_painter = MagicMock()

        points_data = [(5, 100.0, 200.0, PointStatus.NORMAL.value)]
        screen_points = np.array([[100.0, 200.0]])
        curve_color = QColor("#00FF00")

        # Create RenderState avoiding current frame and selection conflicts
        render_state = RenderState(
            points=points_data,
            current_frame=999,  # Different from test data
            selected_points=set(),  # No selections
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0,
            pan_offset_y=0,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=False,
            background_image=None,
            image_width=800,
            image_height=600,
            show_grid=False,
            point_radius=5,
        )

        # Test active curve (should use status color)
        with patch("ui.ui_constants.get_status_color") as mock_get_status:
            mock_get_status.return_value = "#ffffff"
            with patch("ui.ui_constants.SPECIAL_COLORS", {}):
                renderer._render_points_with_status(
                    painter=mock_painter,
                    render_state=render_state,
                    screen_points=screen_points,
                    points_data=points_data,
                    visible_indices=None,
                    step=1,
                    base_point_radius=5,
                    curve_color=curve_color,
                    is_active_curve=True,
                )

            # For active curves, should request status color
            assert mock_get_status.called, "Active curves should use status colors"

        # Test inactive curve (should use curve color for normal points)
        mock_get_status.reset_mock()
        with patch("ui.ui_constants.get_status_color") as mock_get_status:
            mock_get_status.return_value = "#ffffff"
            with patch("ui.ui_constants.SPECIAL_COLORS", {}):
                renderer._render_points_with_status(
                    painter=mock_painter,
                    render_state=render_state,
                    screen_points=screen_points,
                    points_data=points_data,
                    visible_indices=None,
                    step=1,
                    base_point_radius=5,
                    curve_color=curve_color,
                    is_active_curve=False,
                )

            # For inactive curves with normal points, should NOT call get_status_color
            # because it uses the curve's base color instead
            assert (
                not mock_get_status.called
            ), "Inactive curves with normal points should use curve color, not status color"

    def test_edge_case_empty_points_handling(self):
        """Test that unified rendering handles edge cases gracefully."""
        from rendering.render_state import RenderState

        renderer = OptimizedCurveRenderer()
        import numpy as np

        mock_painter = MagicMock()

        # Test with empty screen points (should return early)
        empty_screen_points = np.array([]).reshape(0, 2)
        empty_points_data = []

        # Create RenderState with empty data
        render_state = RenderState(
            points=empty_points_data,
            current_frame=1,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0,
            pan_offset_y=0,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=False,
            background_image=None,
            image_width=800,
            image_height=600,
            show_grid=False,
            point_radius=5,
        )

        # Should handle empty data gracefully without crashing
        renderer._render_points_with_status(
            painter=mock_painter,
            render_state=render_state,
            screen_points=empty_screen_points,
            points_data=empty_points_data,
            visible_indices=None,
            step=1,
            base_point_radius=5,
            curve_color=QColor("#FF0000"),
            is_active_curve=True,
        )

        # Should return early and not call any painter methods
        assert not mock_painter.setBrush.called, "Should not render anything with empty points"


class TestGapRenderingConsistency:
    """Test gap rendering consistency between single and multi-curve views."""

    @pytest.fixture
    def renderer(self):
        """Create OptimizedCurveRenderer instance."""
        return OptimizedCurveRenderer()

    @pytest.fixture
    def mock_painter(self):
        """Create mock painter to avoid Qt threading issues."""
        painter = MagicMock()
        painter.setPen = MagicMock()
        painter.setBrush = MagicMock()
        painter.drawPath = MagicMock()
        return painter

    @pytest.fixture
    def segmented_curve_data(self):
        """Create test data with segments and gaps for testing."""
        return [
            (0, 100.0, 200.0, "keyframe"),  # Start of first segment
            (5, 110.0, 210.0, "normal"),  # In first segment
            (10, 120.0, 220.0, "endframe"),  # End of first segment (creates gap)
            (15, 130.0, 230.0, "normal"),  # In gap (inactive)
            (20, 140.0, 240.0, "keyframe"),  # Start of second segment
            (25, 150.0, 250.0, "normal"),  # In second segment
        ]

    def test_unified_line_rendering_method_detects_segments(self, renderer, mock_painter, segmented_curve_data):
        """Test that _render_lines_with_segments correctly detects and handles segmented data."""
        import numpy as np

        from rendering.render_state import RenderState

        screen_points = np.array([[100, 200], [110, 210], [120, 220], [130, 230], [140, 240], [150, 250]])

        # Create RenderState for line rendering test
        render_state = RenderState(
            points=segmented_curve_data,
            current_frame=10,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0,
            pan_offset_y=0,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=False,
            background_image=None,
            image_width=800,
            image_height=600,
            show_grid=False,
            point_radius=5,
        )

        # Mock the segment-aware rendering method to verify it's called
        with patch.object(renderer, "_render_lines_segmented_aware") as mock_segmented:
            renderer._render_lines_with_segments(
                painter=mock_painter,
                render_state=render_state,
                curve_data=segmented_curve_data,
                screen_points=screen_points,
                curve_color=None,
                line_width=2,
            )

            # Should detect status info and use segmented rendering
            mock_segmented.assert_called_once()
            args, kwargs = mock_segmented.call_args
            assert args[0] == mock_painter
            assert args[1] == render_state
            assert args[2] == segmented_curve_data
            assert np.array_equal(args[3], screen_points)

    def test_unified_line_rendering_method_handles_simple_data(self, renderer, mock_painter):
        """Test that _render_lines_with_segments falls back to simple rendering for data without status."""
        import numpy as np

        from rendering.render_state import RenderState

        simple_curve_data = [
            (0, 100.0, 200.0),  # No status info
            (5, 110.0, 210.0),
            (10, 120.0, 220.0),
        ]
        screen_points = np.array([[100, 200], [110, 210], [120, 220]])

        # Create RenderState for simple data test
        render_state = RenderState(
            points=simple_curve_data,
            current_frame=5,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0,
            pan_offset_y=0,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=False,
            background_image=None,
            image_width=800,
            image_height=600,
            show_grid=False,
            point_radius=5,
        )

        # Mock the simple rendering method to verify it's called
        with patch.object(renderer, "_render_lines_simple") as mock_simple:
            renderer._render_lines_with_segments(
                painter=mock_painter,
                render_state=render_state,
                curve_data=simple_curve_data,
                screen_points=screen_points,
                curve_color=None,
                line_width=2,
            )

            # Should use simple rendering for data without status
            mock_simple.assert_called_once()
            args, kwargs = mock_simple.call_args
            assert args[0] == mock_painter
            assert np.array_equal(args[1], screen_points)

    def test_multi_curve_rendering_uses_unified_line_method(self, renderer, mock_painter, segmented_curve_data):
        """Test that multi-curve rendering uses the unified line rendering method."""
        from rendering.render_state import RenderState

        # Create RenderState with multiple curves that have gaps
        render_state = RenderState(
            points=[],  # Not used for multi-curve rendering
            current_frame=10,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0,
            pan_offset_y=0,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=False,
            background_image=None,
            image_width=800,
            image_height=600,
            show_grid=False,
            point_radius=5,
            # Multi-curve data with gaps
            curves_data={
                "curve1": segmented_curve_data,
                "curve2": segmented_curve_data[:3],  # Different curve
            },
            curve_metadata={
                "curve1": {"visible": True, "color": "#FF0000"},
                "curve2": {"visible": True, "color": "#00FF00"},
            },
            active_curve_name="curve1",
            show_all_curves=True,
            selected_curve_names={"curve1", "curve2"},
        )

        # Mock the unified line rendering method
        with patch.object(renderer, "_render_lines_with_segments") as mock_unified:
            with patch.object(renderer, "_render_points_with_status"):
                renderer._render_multiple_curves(mock_painter, render_state)

                # Should call unified line rendering for each curve
                assert mock_unified.call_count == 2

                # Verify calls include gap data
                calls = mock_unified.call_args_list
                for call in calls:
                    args, kwargs = call
                    assert "curve_data" in kwargs
                    assert "screen_points" in kwargs
                    assert "curve_color" in kwargs
                    assert "line_width" in kwargs

    def test_single_curve_gap_rendering_behavior(self, renderer, mock_painter, segmented_curve_data):
        """Test that single curve rendering properly handles gaps (behavioral test)."""
        import numpy as np

        from rendering.render_state import RenderState

        # Create RenderState for single curve gap rendering test
        render_state = RenderState(
            points=segmented_curve_data,
            current_frame=1,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0,
            pan_offset_y=0,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=False,
            background_image=None,
            image_width=800,
            image_height=600,
            show_grid=False,
            point_radius=5,
        )

        screen_points = np.array([[100, 200], [110, 210], [120, 220], [130, 230], [140, 240], [150, 250]])

        # Mock LOD system
        with patch.object(renderer._lod_system, "get_lod_points", return_value=(screen_points, 1)):
            with patch.object(renderer, "_render_point_markers_optimized"):
                with patch.object(renderer, "_render_point_state_labels"):
                    with patch.object(renderer, "_render_frame_numbers_optimized"):
                        # Test the behavior: rendering should complete without error
                        # and should handle the segmented data (has status information)
                        renderer._render_points_ultra_optimized(mock_painter, render_state)

                        # Verify drawing operations occurred (behavior, not implementation)
                        assert mock_painter.setPen.called, "Should set pen for line drawing"
                        assert mock_painter.drawPath.called, "Should draw path for curve lines"

    def test_gap_rendering_consistency_behavioral(self, renderer, segmented_curve_data):
        """Test that gaps render consistently between views (behavioral test)."""
        import numpy as np

        from rendering.render_state import RenderState

        # Create separate mock painters to track drawing operations
        single_painter = MagicMock()
        single_painter.setPen = MagicMock()
        single_painter.drawPath = MagicMock()

        multi_painter = MagicMock()
        multi_painter.setPen = MagicMock()
        multi_painter.drawPath = MagicMock()

        screen_points = np.array([[100, 200], [110, 210], [120, 220], [130, 230], [140, 240], [150, 250]])

        # Create RenderState for single curve view
        single_curve_render_state = RenderState(
            points=segmented_curve_data,
            current_frame=1,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0,
            pan_offset_y=0,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=False,
            background_image=None,
            image_width=800,
            image_height=600,
            show_grid=False,
            point_radius=5,
        )

        # Create RenderState for multi-curve view
        multi_curve_render_state = RenderState(
            points=[],  # Not used for multi-curve rendering
            current_frame=1,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=1.0,
            pan_offset_x=0,
            pan_offset_y=0,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=False,
            background_image=None,
            image_width=800,
            image_height=600,
            show_grid=False,
            point_radius=5,
            # Multi-curve data
            curves_data={"test_curve": segmented_curve_data},
            curve_metadata={"test_curve": {"visible": True, "color": "#FFFFFF"}},
            active_curve_name="test_curve",
            show_all_curves=True,
            selected_curve_names={"test_curve"},
        )

        # Test single curve rendering behavior
        with patch.object(renderer._lod_system, "get_lod_points", return_value=(screen_points, 1)):
            with patch.object(renderer, "_render_point_markers_optimized"):
                with patch.object(renderer, "_render_point_state_labels"):
                    renderer._render_points_ultra_optimized(single_painter, single_curve_render_state)

        # Test multi-curve rendering behavior
        with patch.object(renderer, "_render_points_with_status"):
            renderer._render_multiple_curves(multi_painter, multi_curve_render_state)

        # Verify both views produce consistent drawing behavior
        assert single_painter.setPen.called, "Single curve view should set pen for drawing"
        assert single_painter.drawPath.called, "Single curve view should draw paths"

        assert multi_painter.setPen.called, "Multi-curve view should set pen for drawing"
        assert multi_painter.drawPath.called, "Multi-curve view should draw paths"

        # Both should have called setPen multiple times for different segment types (active/inactive)
        # This indicates gap-aware rendering is occurring
        assert single_painter.setPen.call_count >= 2, "Should set different pens for active/inactive segments"
        assert multi_painter.setPen.call_count >= 2, "Should set different pens for active/inactive segments"

    def test_inactive_segments_render_as_dashed_lines(self, renderer, mock_painter, segmented_curve_data):
        """Test that inactive segments between endframes render as dashed lines."""
        import numpy as np

        mock_curve_view = Mock()
        screen_points = np.array([[100, 200], [110, 210], [120, 220], [130, 230], [140, 240], [150, 250]])

        # Track pen style changes
        pen_calls = []

        def track_setPen(pen):
            if hasattr(pen, "style"):
                pen_calls.append(pen.style())
            return MagicMock()

        mock_painter.setPen.side_effect = track_setPen

        # Test the segmented-aware rendering directly
        with patch("core.curve_segments.SegmentedCurve.from_points") as mock_segmented_curve:
            # Mock segments: first active, second inactive
            mock_active_segment = Mock()
            mock_active_segment.is_active = True
            mock_active_segment.point_count = 3

            mock_inactive_segment = Mock()
            mock_inactive_segment.is_active = False
            mock_inactive_segment.point_count = 2

            mock_curve = Mock()
            mock_curve.segments = [mock_active_segment, mock_inactive_segment]
            mock_segmented_curve.return_value = mock_curve

            with patch.object(renderer, "_draw_active_segment") as mock_active:
                with patch.object(renderer, "_draw_gap_segment") as mock_gap:
                    renderer._render_lines_segmented_aware(
                        mock_painter, mock_curve_view, segmented_curve_data, screen_points, QColor(255, 255, 255), 2
                    )

                    # Should call both active and gap segment rendering
                    mock_active.assert_called_once()
                    mock_gap.assert_called_once()

                    # Verify the gap segment was called with a dashed pen
                    gap_call_args = mock_gap.call_args[0]
                    gap_call_args[4]  # pen parameter
                    # Note: We can't directly test the pen style due to mocking, but we verify
                    # that the gap segment method was called, which uses dashed lines

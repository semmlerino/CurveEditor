#!/usr/bin/env python

"""
Tests for the new rendering system architecture.

These tests verify that the rendering refactoring preserves functionality
while providing a clean, testable architecture.
"""

import os
import sys
from unittest.mock import Mock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from PySide6.QtCore import QRect
from PySide6.QtGui import QPaintEvent

from data.curve_view import CurveView
from rendering.background_renderer import BackgroundRenderer
from rendering.curve_renderer import CurveRenderer
from rendering.info_renderer import InfoRenderer
from rendering.point_renderer import PointRenderer


class TestRenderingSystemArchitecture:
    """Test the new modular rendering system."""

    def test_curve_renderer_initialization(self):
        """Test that CurveRenderer properly initializes all sub-renderers."""
        renderer = CurveRenderer()

        assert hasattr(renderer, "background_renderer")
        assert hasattr(renderer, "point_renderer")
        assert hasattr(renderer, "info_renderer")

        assert isinstance(renderer.background_renderer, BackgroundRenderer)
        assert isinstance(renderer.point_renderer, PointRenderer)
        assert isinstance(renderer.info_renderer, InfoRenderer)

    def test_curve_view_uses_new_renderer(self, qapp):
        """Test that CurveView uses the new rendering system."""
        curve_view = CurveView()

        # Verify the curve view has the new renderer
        assert hasattr(curve_view, "_curve_renderer")
        assert isinstance(curve_view._curve_renderer, CurveRenderer)

    @patch("rendering.curve_renderer.QPainter")
    def test_rendering_pipeline_calls(self, mock_painter_class, qapp):
        """Test that the rendering pipeline calls all components correctly."""
        # Create mocks for the rendering components
        mock_background_renderer = Mock()
        mock_point_renderer = Mock()
        mock_info_renderer = Mock()

        # Create curve renderer with mocked components
        curve_renderer = CurveRenderer()
        curve_renderer.background_renderer = mock_background_renderer
        curve_renderer.point_renderer = mock_point_renderer
        curve_renderer.info_renderer = mock_info_renderer

        # Create a mock curve view with all required attributes for ViewState
        curve_view = Mock()
        curve_view.width.return_value = 800
        curve_view.height.return_value = 600
        curve_view.rect.return_value = QRect(0, 0, 800, 600)
        curve_view.hasFocus.return_value = False
        curve_view.points = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
        curve_view.background_image = None
        curve_view._needs_initial_fit = False

        # Mock attributes needed by ViewState.from_curve_view
        curve_view.image_width = 1920
        curve_view.image_height = 1080
        curve_view.zoom_factor = 1.0
        curve_view.offset_x = 0.0
        curve_view.offset_y = 0.0
        curve_view.scale_to_image = True
        curve_view.flip_y_axis = False
        curve_view.x_offset = 0.0
        curve_view.y_offset = 0.0

        # Mock painter
        mock_painter = Mock()
        mock_paint_event = Mock()

        # Call the render method
        curve_renderer.render(mock_painter, mock_paint_event, curve_view)

        # Verify all renderers were called
        mock_background_renderer.render_background.assert_called_once()
        mock_point_renderer.render_points.assert_called_once()
        mock_info_renderer.render_info.assert_called_once()

    def test_background_renderer_functionality(self):
        """Test that BackgroundRenderer can be instantiated and has correct methods."""
        renderer = BackgroundRenderer()

        assert hasattr(renderer, "render_background")
        assert callable(renderer.render_background)

    def test_point_renderer_functionality(self):
        """Test that PointRenderer can be instantiated and has correct methods."""
        renderer = PointRenderer()

        assert hasattr(renderer, "render_points")
        assert callable(renderer.render_points)

    def test_info_renderer_functionality(self):
        """Test that InfoRenderer can be instantiated and has correct methods."""
        renderer = InfoRenderer()

        assert hasattr(renderer, "render_info")
        assert callable(renderer.render_info)

    def test_paint_event_delegation(self, qapp):
        """Test that paintEvent properly delegates to the new rendering system."""
        curve_view = CurveView()

        # Mock the curve renderer
        mock_renderer = Mock()
        curve_view._curve_renderer = mock_renderer

        # Create a real paint event
        paint_event = QPaintEvent(QRect(0, 0, 800, 600))

        # Mock QPainter to avoid actual painting
        with patch("curve_view.QPainter") as mock_painter_class:
            mock_painter = Mock()
            mock_painter_class.return_value = mock_painter

            # Mock the super().paintEvent call to avoid PySide6 type checking issues
            with patch("PySide6.QtWidgets.QWidget.paintEvent"):
                # Call paintEvent
                curve_view.paintEvent(paint_event)

                # Verify the renderer was called with correct arguments
                mock_renderer.render.assert_called_once_with(mock_painter, paint_event, curve_view)


class TestRenderingSystemIntegration:
    """Integration tests for the rendering system."""

    def test_rendering_with_real_data(self, qapp):
        """Test rendering with actual curve data."""
        curve_view = CurveView()

        # Add some test data
        test_points = [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)]
        curve_view.setPoints(test_points)

        # Mock QPainter to capture rendering calls
        with patch("curve_view.QPainter") as mock_painter_class:
            mock_painter = Mock()
            mock_painter_class.return_value = mock_painter

            # Create a real paint event
            paint_event = QPaintEvent(QRect(0, 0, 800, 600))

            # Mock the super().paintEvent call
            with patch("PySide6.QtWidgets.QWidget.paintEvent"):
                # This should not raise any exceptions
                curve_view.paintEvent(paint_event)

                # Verify painter was configured correctly
                mock_painter.setRenderHint.assert_called()
                mock_painter.fillRect.assert_called()

    def test_empty_state_rendering(self, qapp):
        """Test rendering when there are no points or background image."""
        curve_view = CurveView()

        # Ensure no data
        curve_view.points = []
        curve_view.background_image = None

        # Mock QPainter to capture rendering calls
        with patch("curve_view.QPainter") as mock_painter_class:
            mock_painter = Mock()
            mock_painter_class.return_value = mock_painter

            # Mock the empty state drawing
            with patch.object(curve_view, "_draw_empty_state") as mock_empty_state:
                paint_event = QPaintEvent(QRect(0, 0, 800, 600))

                # Mock the super().paintEvent call
                with patch("PySide6.QtWidgets.QWidget.paintEvent"):
                    # This should not raise any exceptions and should call empty state
                    curve_view.paintEvent(paint_event)

                    mock_empty_state.assert_called_once_with(mock_painter)


if __name__ == "__main__":
    pytest.main([__file__])

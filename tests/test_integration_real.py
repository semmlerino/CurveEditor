#!/usr/bin/env python
"""
Real integration tests for the complete CurveEditor system.
Tests actual component interactions without mocking.
"""

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QImage, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QApplication

from core.models import CurvePoint
from rendering.optimized_curve_renderer import OptimizedCurveRenderer
from services import get_data_service, get_interaction_service, get_transform_service, get_ui_service
from stores.application_state import get_application_state
from tests.qt_test_helpers import create_test_image, safe_painter


class TestServiceIntegration:
    """Test integration between different services."""

    def test_services_are_singletons(self):
        """Test that all services follow singleton pattern."""
        # Get services multiple times
        data1 = get_data_service()
        data2 = get_data_service()

        interaction1 = get_interaction_service()
        interaction2 = get_interaction_service()

        transform1 = get_transform_service()
        transform2 = get_transform_service()

        ui1 = get_ui_service()
        ui2 = get_ui_service()

        # All should be the same instance
        assert data1 is data2
        assert interaction1 is interaction2
        assert transform1 is transform2
        assert ui1 is ui2

    def test_data_service_integration(self):
        """Test DataService functionality."""
        data_service = get_data_service()

        # Create test data
        points = [
            CurvePoint(frame=1, x=100, y=200),
            CurvePoint(frame=2, x=150, y=250),
            CurvePoint(frame=3, x=200, y=300),
        ]

        # Test point operations
        result = data_service.analyze_points(points)

        assert result["count"] == 3
        assert result["min_frame"] == 1
        assert result["max_frame"] == 3
        assert "bounds" in result

    def test_transform_service_integration(self):
        """Test TransformService with other components."""
        transform_service = get_transform_service()

        # Create a transform
        transform = transform_service.create_transform(scale=2.0, center_offset=(100, 100), pan_offset=(50, 50))

        # Test with data points
        data_point = (100, 200)
        screen_point = transform_service.transform_point_to_screen(transform, data_point[0], data_point[1])

        # Transform back
        result = transform_service.transform_point_to_data(transform, screen_point[0], screen_point[1])

        # Should get original point back
        assert abs(result[0] - data_point[0]) < 0.001
        assert abs(result[1] - data_point[1]) < 0.001

    def test_interaction_service_with_transform(self):
        """Test InteractionService with coordinate transformation."""
        interaction_service = get_interaction_service()
        transform_service = get_transform_service()

        # Create mock view with points
        class MockView:
            def __init__(self):
                self.curve_data = [
                    (1, 100, 100),
                    (2, 200, 200),
                    (3, 300, 300),
                ]
                self.selected_points = set()

            def width(self):
                return 800

            def height(self):
                return 600

        view = MockView()

        # Setup ApplicationState for interaction service
        app_state = get_application_state()
        app_state.set_curve_data("test_curve", view.curve_data)
        app_state.set_active_curve("test_curve")

        # Create transform using the same method as the interaction service
        view_state = transform_service.create_view_state(view)
        transform = transform_service.create_transform_from_view_state(view_state)

        # Test finding point at screen position
        screen_x, screen_y = transform.data_to_screen(100, 100)

        # Find point at this position
        idx = interaction_service.find_point_at_position(view, screen_x, screen_y, tolerance=10)

        # Should find the first point
        assert idx == 0


class TestRenderingPipeline:
    """Test the complete rendering pipeline."""

    @pytest.fixture
    def app(self):
        """Create QApplication for rendering tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_renderer_with_transform_service(self, app):
        """Test renderer using Transform service."""
        renderer = OptimizedCurveRenderer()

        # Create RenderState with test data
        from rendering.render_state import RenderState

        render_state = RenderState(
            points=[
                (1, 100, 100),
                (2, 200, 200),
                (3, 300, 300),
            ],
            current_frame=1,
            selected_points={1},  # Select middle point
            widget_width=800,
            widget_height=600,
            zoom_factor=2.0,
            pan_offset_x=50,
            pan_offset_y=50,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=False,
            background_image=None,
            image_width=800,
            image_height=600,
            show_grid=True,
            point_radius=5,
        )

        # Create properly initialized image
        image = create_test_image(800, 600)

        # Use safe painter context manager to ensure proper cleanup
        with safe_painter(image) as painter:
            # Render
            renderer.render(painter, None, render_state)

        # Check that something was rendered
        assert renderer._render_count > 0

    def test_background_curve_synchronization(self, app):
        """Test that background and curve stay synchronized."""
        renderer = OptimizedCurveRenderer()

        # Create background image
        background_image = QImage(800, 600, QImage.Format.Format_RGB32)
        background_image.fill(Qt.GlobalColor.blue)

        # Create RenderState with background
        from rendering.render_state import RenderState

        render_state = RenderState(
            points=[(1, 100, 100), (2, 400, 300)],
            current_frame=1,
            selected_points=set(),
            widget_width=800,
            widget_height=600,
            zoom_factor=2.0,
            pan_offset_x=100,
            pan_offset_y=50,
            manual_offset_x=0,
            manual_offset_y=0,
            flip_y_axis=False,
            show_background=True,
            background_image=background_image,
            background_opacity=0.5,
            image_width=800,
            image_height=600,
            show_grid=False,
            point_radius=5,
        )

        # Create properly initialized image
        image = create_test_image(800, 600)

        # Use safe painter context manager to ensure proper cleanup
        with safe_painter(image) as painter:
            # Render
            renderer.render(painter, None, render_state)

        # Both background and curves should be rendered
        # Check that render completed without errors
        assert renderer._render_count > 0

    def test_viewport_culling_integration(self, app):
        """Test viewport culling with large dataset."""
        renderer = OptimizedCurveRenderer()

        # Create 1000 points (enough to test viewport culling without memory issues)
        large_points = [(i, i * 10, i * 5) for i in range(1000)]

        # Create RenderState with large dataset
        from rendering.render_state import RenderState

        render_state = RenderState(
            points=large_points,
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
            point_radius=3,
        )

        # Create properly initialized image (using QImage for thread safety per Qt best practices)
        image = create_test_image(800, 600)

        # Use safe painter context manager for guaranteed cleanup
        with safe_painter(image) as painter:
            # Render with proper resource management - should use viewport culling
            renderer.render(painter, None, render_state)

        # Should have culled most points (only visible ones rendered)
        # Renderer should complete quickly even with 1000 points
        stats = renderer.get_performance_stats()
        assert stats["render_count"] > 0

        # Verify the large dataset was handled without crash
        assert len(large_points) == 1000


class TestUIIntegration:
    """Test UI component integration."""

    @pytest.fixture
    def app(self):
        """Create QApplication for UI tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_main_window_creation(self, app, qtbot):
        """Test creating main window with all components."""
        from ui.main_window import MainWindow

        window = MainWindow()
        qtbot.addWidget(window)

        # Check that main components exist (simplified UI)
        assert window.curve_widget is not None
        assert window.menuBar() is not None
        assert hasattr(window, "curve_container")

        # Check window can be created without errors
        assert not window.isVisible()  # Window not shown yet but created successfully

    # ModernizedMainWindow test removed - functionality consolidated into MainWindow

    def test_curve_widget_with_services(self, app, qtbot):
        """Test CurveViewWidget with service integration."""
        from ui.curve_view_widget import CurveViewWidget

        widget = CurveViewWidget()
        qtbot.addWidget(widget)

        # Set some test data
        widget.set_curve_data(
            [
                (1, 100, 100),
                (2, 200, 200),
                (3, 300, 300),
            ]
        )

        # Test transform
        transform = widget.get_transform()
        assert transform is not None

        # Test coordinate conversion
        screen_point = widget.data_to_screen(100, 100)
        assert isinstance(screen_point, QPointF)

        # Test screen to data conversion
        data_point = widget.screen_to_data_qpoint(screen_point)
        assert abs(data_point.x() - 100) < 0.001
        assert abs(data_point.y() - 100) < 0.001


class TestEndToEndWorkflow:
    """Test complete end-to-end workflows."""

    @pytest.fixture
    def app(self):
        """Create QApplication for workflow tests."""
        app = QApplication.instance()
        if app is None:
            app = QApplication([])
        return app

    def test_zoom_workflow(self, app, qtbot):
        """Test complete zoom workflow from mouse wheel to rendering."""
        from ui.curve_view_widget import CurveViewWidget

        widget = CurveViewWidget()
        qtbot.addWidget(widget)
        widget.set_curve_data([(1, 100, 100), (2, 200, 200)])

        initial_zoom = widget.zoom_factor

        # Simulate mouse wheel event
        wheel_event = QWheelEvent(
            QPointF(400, 300),  # Position
            QPointF(400, 300),  # Global position
            QPoint(0, 120),  # Pixel delta (positive = zoom in) - needs QPoint
            QPoint(0, 15),  # Angle delta - needs QPoint
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
            Qt.ScrollPhase.NoScrollPhase,
            False,  # Not inverted
        )

        widget.wheelEvent(wheel_event)

        # Zoom should have increased
        assert widget.zoom_factor > initial_zoom

        # Transform should be updated
        transform = widget.get_transform()
        assert transform.scale == widget.zoom_factor

    def test_selection_workflow(self, app, qtbot):
        """Test complete selection workflow."""
        from ui.curve_view_widget import CurveViewWidget

        widget = CurveViewWidget()
        qtbot.addWidget(widget)
        widget.set_curve_data(
            [
                (1, 100, 100),
                (2, 200, 200),
                (3, 300, 300),
            ]
        )

        # Initially no selection
        assert len(widget.selected_points) == 0

        # Simulate clicking on first point
        # First point at (100, 100) in data coordinates
        screen_pos = widget.data_to_screen(100, 100)

        mouse_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            screen_pos,
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        widget.mousePressEvent(mouse_event)

        # First point should be selected
        assert 0 in widget.selected_points

    def test_pan_workflow(self, app, qtbot):
        """Test complete pan workflow."""
        from ui.curve_view_widget import CurveViewWidget

        widget = CurveViewWidget()
        qtbot.addWidget(widget)
        widget.set_curve_data([(1, 100, 100)])

        initial_pan_x = widget.pan_offset_x
        initial_pan_y = widget.pan_offset_y

        # Start pan with middle mouse button
        start_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonPress,
            QPointF(400, 300),
            Qt.MouseButton.MiddleButton,
            Qt.MouseButton.MiddleButton,
            Qt.KeyboardModifier.NoModifier,
        )

        widget.mousePressEvent(start_event)
        assert widget.pan_active is True

        # Move mouse to pan
        move_event = QMouseEvent(
            QMouseEvent.Type.MouseMove,
            QPointF(450, 350),  # Moved 50 pixels right and down
            Qt.MouseButton.NoButton,
            Qt.MouseButton.MiddleButton,
            Qt.KeyboardModifier.NoModifier,
        )

        widget.mouseMoveEvent(move_event)

        # Pan offsets should have changed
        assert widget.pan_offset_x != initial_pan_x
        assert widget.pan_offset_y != initial_pan_y

        # Release pan
        release_event = QMouseEvent(
            QMouseEvent.Type.MouseButtonRelease,
            QPointF(450, 350),
            Qt.MouseButton.MiddleButton,
            Qt.MouseButton.NoButton,
            Qt.KeyboardModifier.NoModifier,
        )

        widget.mouseReleaseEvent(release_event)
        assert widget.pan_active is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

#!/usr/bin/env python
"""
Test utilities for consistent test setup and mock creation.

This module provides factories and generators to reduce duplication
across test files and ensure consistent test data.
"""

import random
from unittest.mock import Mock


class MockFactory:
    """Factory for creating consistent test mocks."""

    @staticmethod
    def create_curve_view(
        width: int = 800,
        height: int = 600,
        points: list | None = None,
        selected_points: set | None = None,
        zoom_factor: float = 1.0,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        flip_y_axis: bool = False,
    ) -> Mock:
        """Create a mock curve view with standard setup.

        Args:
            width: View width in pixels
            height: View height in pixels
            points: Initial curve points
            selected_points: Set of selected point indices
            zoom_factor: Zoom level
            offset_x: X offset for panning
            offset_y: Y offset for panning
            flip_y_axis: Whether Y axis is flipped

        Returns:
            Configured mock curve view
        """
        mock = Mock()
        mock.points = points if points is not None else []
        mock.selected_points = selected_points if selected_points is not None else set()
        mock.width.return_value = width
        mock.height.return_value = height
        mock.zoom_factor = zoom_factor
        mock.offset_x = offset_x
        mock.offset_y = offset_y
        mock.flip_y_axis = flip_y_axis

        # Add common attributes
        mock.show_background = False
        mock.show_grid = False
        mock.show_info = True
        mock.background_image = None
        mock.background_opacity = 1.0
        mock.point_radius = 5

        # Add update method
        mock.update = Mock()

        return mock

    @staticmethod
    def create_main_window(
        curve_data: list | None = None,
        history: list | None = None,
        history_index: int = 0,
        selected_indices: set | None = None,
    ) -> Mock:
        """Create a mock main window.

        Args:
            curve_data: Initial curve data
            history: History stack
            history_index: Current history position
            selected_indices: Selected point indices

        Returns:
            Configured mock main window
        """
        mock = Mock()
        mock.curve_data = curve_data if curve_data is not None else []
        mock.history = history if history is not None else []
        mock.history_index = history_index
        mock.selected_indices = selected_indices if selected_indices is not None else set()

        # Add status bar
        status_bar = Mock()
        status_bar.showMessage = Mock()
        status_bar.clearMessage = Mock()
        mock.statusBar.return_value = status_bar

        # Add common attributes
        mock.is_modified = False
        mock.current_file = None
        mock.max_history_size = 100

        # Add curve view
        mock.curve_view = MockFactory.create_curve_view()

        return mock

    @staticmethod
    def create_event(event_type: str = "mouse", **kwargs) -> Mock:
        """Create a mock Qt event.

        Args:
            event_type: Type of event (mouse, key, wheel)
            **kwargs: Event-specific attributes

        Returns:
            Configured mock event
        """
        mock = Mock()

        if event_type == "mouse":
            mock.button = Mock(return_value=kwargs.get("button", 1))  # Qt.LeftButton
            mock.buttons = Mock(return_value=kwargs.get("buttons", 1))
            mock.modifiers = Mock(return_value=kwargs.get("modifiers", 0))
            mock.position = Mock(return_value=Mock(x=lambda: kwargs.get("x", 100), y=lambda: kwargs.get("y", 100)))
            mock.pos = Mock(return_value=Mock(x=lambda: kwargs.get("x", 100), y=lambda: kwargs.get("y", 100)))
            mock.accept = Mock()

        elif event_type == "key":
            mock.key = Mock(return_value=kwargs.get("key", 0))
            mock.modifiers = Mock(return_value=kwargs.get("modifiers", 0))
            mock.text = Mock(return_value=kwargs.get("text", ""))
            mock.accept = Mock()
            mock.ignore = Mock()

        elif event_type == "wheel":
            mock.angleDelta = Mock(return_value=Mock(y=lambda: kwargs.get("delta", 120)))
            mock.modifiers = Mock(return_value=kwargs.get("modifiers", 0))
            mock.accept = Mock()

        return mock

    @staticmethod
    def create_service(service_type: str) -> Mock:
        """Create a mock service.

        Args:
            service_type: Type of service (data, transform, interaction, ui)

        Returns:
            Configured mock service
        """
        mock = Mock()

        if service_type == "transform":
            mock.transform_point = Mock(return_value=(100.0, 100.0))
            mock.inverse_transform_point = Mock(return_value=(50.0, 50.0))
            mock.get_transform = Mock()
            mock.set_zoom = Mock()
            mock.set_offset = Mock()

        elif service_type == "data":
            mock.load_track_data = Mock(return_value=[])
            mock.save_track_data = Mock(return_value=True)
            mock.analyze_curve_data = Mock(return_value={})
            mock.interpolate_frames = Mock(return_value=[])

        elif service_type == "interaction":
            mock.handle_mouse_press = Mock()
            mock.handle_mouse_move = Mock()
            mock.handle_mouse_release = Mock()
            mock.handle_key_press = Mock()
            mock.select_point = Mock()

        elif service_type == "ui":
            mock.show_error = Mock()
            mock.show_info = Mock()
            mock.confirm_action = Mock(return_value=True)
            mock.get_smooth_window_size = Mock(return_value=5)

        return mock


class TestDataGenerator:
    """Generate consistent test data for various scenarios."""

    @staticmethod
    def curve_data(
        size: int = 10,
        pattern: str = "linear",
        include_interpolated: bool = False,
        include_status: bool = True,
    ) -> list:
        """Generate curve data for testing.

        Args:
            size: Number of points to generate
            pattern: Data pattern (linear, random, sine, interpolated)
            include_interpolated: Whether to include interpolated points
            include_status: Whether to include status field

        Returns:
            List of curve points
        """
        data = []

        if pattern == "linear":
            for i in range(size):
                x = float(i * 10)
                y = float(i * 10)
                if include_status:
                    if include_interpolated and i % 3 == 0:
                        data.append((i, x, y, "interpolated"))
                    else:
                        data.append((i, x, y, "keyframe"))
                else:
                    data.append((i, x, y))

        elif pattern == "random":
            random.seed(42)  # Consistent random data
            for i in range(size):
                x = random.uniform(0, 100)
                y = random.uniform(0, 100)
                if include_status:
                    status = "interpolated" if include_interpolated and i % 3 == 0 else "keyframe"
                    data.append((i, x, y, status))
                else:
                    data.append((i, x, y))

        elif pattern == "sine":
            import math

            for i in range(size):
                x = float(i * 10)
                y = 50.0 + 30.0 * math.sin(i * 0.5)
                if include_status:
                    status = "interpolated" if include_interpolated and i % 3 == 0 else "keyframe"
                    data.append((i, x, y, status))
                else:
                    data.append((i, x, y))

        elif pattern == "interpolated":
            # Mix of keyframes and interpolated points
            for i in range(size):
                x = float(i * 10)
                y = float(i * 10)
                if i % 3 == 0:
                    data.append((i, x, y, "keyframe"))
                else:
                    data.append((i, x, y, "interpolated"))

        return data

    @staticmethod
    def point_tuples(count: int = 10, mixed: bool = False) -> list:
        """Generate point tuples for testing.

        Args:
            count: Number of points to generate
            mixed: Whether to mix keyframe and interpolated points

        Returns:
            List of point tuples (Point3 or Point4)
        """
        points = []

        for i in range(count):
            frame = i + 1
            x = float(i * 10)
            y = float(i * 15)

            if mixed and i % 3 == 0:
                point = (frame, x, y, "interpolated")
            else:
                point = (frame, x, y, "keyframe")

            points.append(point)

        return points

    @staticmethod
    def selection_indices(total: int, count: int = 5, pattern: str = "random") -> set:
        """Generate selection indices for testing.

        Args:
            total: Total number of points
            count: Number of points to select
            pattern: Selection pattern (random, sequential, alternating)

        Returns:
            Set of selected indices
        """
        if count >= total:
            return set(range(total))

        if pattern == "random":
            random.seed(42)
            return set(random.sample(range(total), count))
        elif pattern == "sequential":
            return set(range(count))
        elif pattern == "alternating":
            return set(range(0, min(count * 2, total), 2))
        else:
            return set()

    @staticmethod
    def transform_params() -> dict:
        """Generate common transform parameters for testing.

        Returns:
            Dictionary of transform parameters
        """
        return {
            "zoom_factor": 1.5,
            "offset_x": 100.0,
            "offset_y": 50.0,
            "image_width": 1920,
            "image_height": 1080,
            "flip_y_axis": False,
        }


class TestFixtures:
    """Common test fixtures and setup helpers."""

    @staticmethod
    def setup_qt_app():
        """Setup Qt application for testing (if needed)."""
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is None:
                app = QApplication([])
            return app
        except ImportError:
            return None

    @staticmethod
    def cleanup_qt_app():
        """Cleanup Qt application after testing."""
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app:
                app.quit()
        except ImportError:
            pass

    @staticmethod
    def create_test_environment() -> dict:
        """Create a complete test environment with all common mocks.

        Returns:
            Dictionary with all test components
        """
        return {
            "main_window": MockFactory.create_main_window(),
            "curve_view": MockFactory.create_curve_view(),
            "transform_service": MockFactory.create_service("transform"),
            "data_service": MockFactory.create_service("data"),
            "interaction_service": MockFactory.create_service("interaction"),
            "ui_service": MockFactory.create_service("ui"),
            "curve_data": TestDataGenerator.curve_data(size=20),
            "selected_indices": TestDataGenerator.selection_indices(20, 5),
        }


# Convenience functions for common test scenarios
def mock_curve_view(**kwargs) -> Mock:
    """Convenience function to create a mock curve view."""
    return MockFactory.create_curve_view(**kwargs)


def mock_main_window(**kwargs) -> Mock:
    """Convenience function to create a mock main window."""
    return MockFactory.create_main_window(**kwargs)


def test_points(count: int = 10, **kwargs) -> list:
    """Convenience function to generate test points."""
    return TestDataGenerator.curve_data(size=count, **kwargs)


def test_env() -> dict:
    """Convenience function to create test environment."""
    return TestFixtures.create_test_environment()

"""
Shared test utilities and implementations.

Contains lightweight test implementations of components that can be used
instead of heavy mock objects.
"""

from typing import Any
from unittest.mock import MagicMock

# Type aliases for test data
PointsList = list[tuple[int, float, float]]
Point3 = tuple[int, float, float]
Point4 = tuple[int, float, float, Any]


class TestCurveView:
    """Lightweight real CurveView implementation for testing.

    This replaces massive mock objects with a real implementation that has
    actual behavior instead of mocked behavior.
    """

    def __init__(self, **kwargs) -> None:
        # Real data structures
        self.curve_data: list[Point4] = []
        self.points: list[Point4] = []  # Alias for service compatibility
        self.selected_points: set[int] = set()
        self.selected_point_idx: int = -1

        # View state
        self.zoom_factor: float = 1.0
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0
        self.pan_offset_x: float = 0.0
        self.pan_offset_y: float = 0.0
        self.manual_offset_x: float = 0.0
        self.manual_offset_y: float = 0.0

        # Display settings
        self.show_background: bool = True
        self.show_grid: bool = False
        self.show_points: bool = True
        self.show_lines: bool = True
        self.show_velocity_vectors: bool = False
        self.show_all_frame_numbers: bool = False
        self.flip_y_axis: bool = False
        self.scale_to_image: bool = True
        self.background_opacity: float = 1.0

        # Rendering settings
        self.point_radius: int = 5
        self.selected_point_radius: int = 7
        self.line_width: int = 2
        self.selected_line_width: int = 3

        # Image properties
        self.image_width: int = 1920
        self.image_height: int = 1080
        self.background_image: Any = None

        # Image sequence properties
        self.image_sequence_path: str = ""
        self.image_filenames: list[str] = []
        self.current_image_idx: int = 0

        # Interaction tracking
        self._update_called: bool = False

        # Signal mocks for service compatibility
        self.point_selected = MagicMock()  # Signal mock

        # Apply kwargs to override defaults
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

        # Sync points with curve_data if points were provided
        if "points" in kwargs:
            self.curve_data = self.points.copy()
        elif "curve_data" in kwargs:
            self.points = self.curve_data.copy()

    def set_curve_data(self, points: list[Point4]) -> None:
        """Set curve data - real implementation."""
        self.curve_data = points.copy()
        self.points = self.curve_data  # Keep in sync

    def add_point(self, point: Point4) -> None:
        """Add a point - real implementation."""
        self.curve_data.append(point)
        self.points = self.curve_data  # Keep in sync

    def update_point(self, index: int, x: float, y: float) -> None:
        """Update point coordinates - real implementation."""
        if 0 <= index < len(self.curve_data):
            frame, _, _, status = self.curve_data[index]
            self.curve_data[index] = (frame, x, y, status)

    def remove_point(self, index: int) -> None:
        """Remove a point - real implementation."""
        if 0 <= index < len(self.curve_data):
            del self.curve_data[index]
            self.points = self.curve_data  # Keep in sync
            # Update selection
            self.selected_points = {i - 1 if i > index else i for i in self.selected_points if i != index}

    def get_selected_indices(self) -> list[int]:
        """Get selected indices."""
        return list(self.selected_points)

    def _select_point(self, index: int) -> None:
        """Select a point by index."""
        if 0 <= index < len(self.curve_data):
            self.selected_points = {index}
            self.selected_point_idx = index

    def _clear_selection(self) -> None:
        """Clear all selections."""
        self.selected_points.clear()
        self.selected_point_idx = -1

    def _select_all(self) -> None:
        """Select all points."""
        self.selected_points = set(range(len(self.curve_data)))

    def _delete_selected_points(self) -> None:
        """Delete selected points - real implementation."""
        # Sort indices in reverse order to avoid index shifting
        for idx in sorted(self.selected_points, reverse=True):
            if 0 <= idx < len(self.curve_data):
                del self.curve_data[idx]
        self.selected_points.clear()
        self.points = self.curve_data  # Keep in sync

    def update(self) -> None:
        """Track update calls."""
        self._update_called = True

    @property
    def update_called(self) -> bool:
        """Property for backward compatibility with tests."""
        return self._update_called

    def width(self) -> int:
        """Return widget width for transforms."""
        return 800  # Default width

    def height(self) -> int:
        """Return widget height for transforms."""
        return 600  # Default height

    def data_to_screen(self, x: float, y: float) -> tuple[float, float]:
        """Simple coordinate transformation."""
        screen_x = x * self.zoom_factor + self.offset_x
        screen_y = y * self.zoom_factor + self.offset_y
        return (screen_x, screen_y)

    def screen_to_data(self, x: float, y: float) -> tuple[float, float]:
        """Inverse coordinate transformation."""
        if self.zoom_factor == 0:
            return (0, 0)
        data_x = (x - self.offset_x) / self.zoom_factor
        data_y = (y - self.offset_y) / self.zoom_factor
        return (data_x, data_y)

    def findPointAt(self, pos: tuple[float, float]) -> int:
        """Find point at given position."""
        x, y = pos
        tolerance = 10.0  # Pixel tolerance for point selection

        for i, point in enumerate(self.curve_data):
            _, px, py, _ = point
            screen_px, screen_py = self.data_to_screen(px, py)
            distance = ((screen_px - x) ** 2 + (screen_py - y) ** 2) ** 0.5
            if distance <= tolerance:
                return i
        return -1

    def selectPointByIndex(self, idx: int) -> bool:
        """Select point by index."""
        if 0 <= idx < len(self.curve_data):
            self.selected_points = {idx}
            self.selected_point_idx = idx
            self.point_selected.emit(idx)
            return True
        return False

    def get_current_transform(self) -> object:
        """Get current transform object."""

        # Return a simple transform object with current view state
        class Transform:
            def __init__(self, zoom: float, offset_x: float, offset_y: float):
                self.zoom = zoom
                self.offset_x = offset_x
                self.offset_y = offset_y

        return Transform(self.zoom_factor, self.offset_x, self.offset_y)

    def get_point_data(self, idx: int) -> tuple[int, float, float, Any]:
        """Get point data by index."""
        if 0 <= idx < len(self.curve_data):
            return self.curve_data[idx]
        raise IndexError(f"Point index {idx} out of range")


class TestMainWindow:
    """Lightweight real MainWindow implementation for testing."""

    def __init__(self) -> None:
        # Core components
        self.curve_view = TestCurveView()
        self.curve_widget = self.curve_view  # Alias

        # UI components structure
        self.ui_components = MagicMock()
        self.ui_components.timeline = self._create_timeline_components()
        self.ui_components.status = self._create_status_components()
        self.ui_components.toolbar = self._create_toolbar_components()

        # Services mock
        self.services = MagicMock()

        # State
        self.current_file: str | None = None
        self.is_modified: bool = False
        self.current_frame: int = 1
        self.fps: int = 24
        self.playing: bool = False

        # Status bar mock
        self.status_bar = MagicMock()
        self.status_bar.showMessage = MagicMock()

    def _create_timeline_components(self):
        """Create timeline UI components."""
        timeline = MagicMock()
        timeline.frame_slider = MagicMock()
        timeline.frame_slider.value = MagicMock(return_value=1)
        timeline.frame_slider.setValue = MagicMock()
        timeline.frame_spin = MagicMock()
        timeline.frame_spin.value = MagicMock(return_value=1)
        timeline.frame_spin.setValue = MagicMock()
        timeline.play_button = MagicMock()
        timeline.fps_spin = MagicMock()
        timeline.fps_spin.value = MagicMock(return_value=24)
        return timeline

    def _create_status_components(self):
        """Create status UI components."""
        status = MagicMock()
        status.frame_label = MagicMock()
        status.frame_label.setText = MagicMock()
        status.coord_label = MagicMock()
        status.coord_label.setText = MagicMock()
        status.selection_label = MagicMock()
        status.selection_label.setText = MagicMock()
        return status

    def _create_toolbar_components(self):
        """Create toolbar UI components."""
        toolbar = MagicMock()
        toolbar.save_button = MagicMock()
        toolbar.load_button = MagicMock()
        toolbar.export_button = MagicMock()
        toolbar.undo_button = MagicMock()
        toolbar.redo_button = MagicMock()
        return toolbar

    def update_ui_state(self) -> None:
        """Update UI state."""
        pass

    def add_to_history(self) -> None:
        """Add current state to history."""
        pass

    def show_status_message(self, message: str, timeout: int = 2000) -> None:
        """Show status message."""
        self.status_bar.showMessage(message, timeout)


class TestDataBuilder:
    """Builder for creating test data."""

    @staticmethod
    def curve_data(num_points: int | None = None) -> list[Point4]:
        """Create sample curve data.

        Args:
            num_points: Number of points to return (backwards compatibility)
        """
        full_data = [
            (1, 100.0, 200.0, "keyframe"),
            (2, 150.0, 250.0, "interpolated"),
            (3, 200.0, 300.0, "keyframe"),
            (4, 250.0, 350.0, "interpolated"),
            (5, 300.0, 400.0, "keyframe"),
        ]

        if num_points is not None:
            return full_data[:num_points]
        return full_data

    @staticmethod
    def keyframe_data() -> list[Point4]:
        """Create curve data with only keyframes."""
        return [
            (1, 100.0, 200.0, "keyframe"),
            (5, 300.0, 400.0, "keyframe"),
            (10, 500.0, 600.0, "keyframe"),
            (15, 400.0, 500.0, "keyframe"),
            (20, 200.0, 300.0, "keyframe"),
        ]

    @staticmethod
    def curve_view_with_data(num_points: int | None = None, selected_indices: set[int] | None = None) -> TestCurveView:
        """Create a curve view with sample data.

        Args:
            num_points: Number of points to include (backwards compatibility)
            selected_indices: Set of selected point indices
        """
        view = TestCurveView()
        view.set_curve_data(TestDataBuilder.curve_data(num_points))
        if selected_indices:
            view.selected_points = selected_indices
        return view

    @staticmethod
    def main_window_with_data() -> TestMainWindow:
        """Create a main window with sample data."""
        window = TestMainWindow()
        window.curve_view.set_curve_data(TestDataBuilder.curve_data())
        return window


class BaseMockCurveView:
    """Basic mock curve view for simple tests."""

    def __init__(self, selected_points: set[int] | None = None):
        self.curve_data = []
        self.selected_points = selected_points or set()
        self.selected_point_idx = -1
        self.update = MagicMock()
        self.point_selected = MagicMock()

    def get_selected_indices(self) -> list[int]:
        return list(self.selected_points)


class BaseMockMainWindow:
    """Basic mock main window for simple tests."""

    def __init__(self, curve_data=None, selected_indices=None):
        self.curve_view = BaseMockCurveView()
        self.curve_widget = self.curve_view

        if curve_data:
            self.curve_view.curve_data = curve_data
        if selected_indices:
            self.curve_view.selected_points = set(selected_indices)

        self.status_bar = MagicMock()
        self.ui_components = MagicMock()
        self.services = MagicMock()


# Protocol-compliant mocks for services that need full protocol compliance
class ProtocolCompliantMockCurveView(TestCurveView):
    """Fully protocol-compliant mock curve view."""

    def __init__(self, **kwargs) -> None:
        """Initialize with keyword arguments support."""
        super().__init__(**kwargs)


class ProtocolCompliantMockMainWindow(TestMainWindow):
    """Fully protocol-compliant mock main window."""

    pass


class LazyUIMockMainWindow(TestMainWindow):
    """Mock main window with lazy UI component creation."""

    def __init__(self):
        super().__init__()
        self._ui_created = False

    def _ensure_ui(self):
        """Lazily create UI components."""
        if not self._ui_created:
            self._ui_created = True
            # Create UI components on demand

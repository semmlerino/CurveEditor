#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for all tests.

This module provides common test fixtures and configurations, including
proper Qt application initialization for tests that require Qt components.
"""

from collections.abc import Generator
from typing import Any
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPointF, QRect
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication, QRubberBand

# Global variable to track QApplication instance
_qapp_instance: QApplication | None = None


@pytest.fixture(scope="session")
def qapp() -> Generator[QApplication, None, None]:
    """
    Create a QApplication instance for the entire test session.

    This fixture ensures that only one QApplication instance exists
    throughout the test session, preventing Qt crashes when running
    multiple tests that use Qt components.

    The fixture has session scope, meaning it's created once at the
    beginning of the test session and destroyed at the end.

    Yields:
        QApplication: The Qt application instance
    """
    global _qapp_instance

    # Check if QApplication instance already exists
    app = QApplication.instance()

    if app is None:
        # Create new QApplication instance
        app = QApplication([])
        _qapp_instance = app

    yield app

    # Cleanup is handled automatically by Qt when Python exits


@pytest.fixture(autouse=True)
def qt_cleanup(qapp: QApplication) -> Generator[None, None, None]:
    """
    Automatically clean up Qt resources after each test.

    This fixture runs automatically for every test (autouse=True) and
    ensures that Qt resources are properly cleaned up between tests.
    It depends on the qapp fixture to ensure QApplication exists.

    Args:
        qapp: The QApplication instance from the qapp fixture

    Yields:
        None
    """
    # Let the test run
    yield

    # Process any pending Qt events after the test
    qapp.processEvents()

    # Clean up singleton services to prevent test interference
    try:
        from services.logging_service import LoggingService

        LoggingService.close()
    except ImportError:
        pass  # LoggingService might not be available in all tests

    # Clear transformation service caches to prevent test contamination
    try:
        from services.transformation_service import TransformationService

        TransformationService.clear_cache()
    except ImportError:
        pass  # TransformationService might not be available in all tests

    # Clear any other service caches that might cause test contamination
    try:
        from ui.ui_scaling import UIScaling

        if hasattr(UIScaling, "clear_cache"):
            UIScaling.clear_cache()
    except (ImportError, AttributeError):
        pass  # UIScaling cache might not exist or be available

    # Force garbage collection of Qt objects
    import gc

    gc.collect()


def pytest_configure(config: pytest.Config) -> None:
    """
    Configure pytest with custom markers and settings.

    Args:
        config: The pytest configuration object
    """
    # Add custom markers
    config.addinivalue_line("markers", "qt_required: mark test as requiring Qt (QApplication)")
    config.addinivalue_line("markers", "skip_qt_cleanup: mark test to skip automatic Qt cleanup")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """
    Modify test items during collection phase.

    This hook automatically marks tests that import Qt modules as requiring Qt.

    Args:
        config: The pytest configuration object
        items: list of collected test items
    """
    for item in items:
        # Check if the test module imports Qt
        test_module = item.module
        if hasattr(test_module, "__file__"):
            # Read the test file to check for Qt imports
            try:
                with open(test_module.__file__) as f:
                    content = f.read()
                    if "QFileDialog" in content or "QApplication" in content or "from PySide6" in content:
                        # Mark test as requiring Qt
                        item.add_marker(pytest.mark.qt_required)
            except Exception:
                pass


# Common fixture types used across tests
try:
    from data.curve_view import CurveView

    PointsList = list[tuple[int, float, float]]
except ImportError:
    PointsList = list


@pytest.fixture
def curve_view(qapp) -> "CurveView":
    """Create a CurveView instance for testing."""
    from data.curve_view import CurveView

    return CurveView()


@pytest.fixture
def sample_points() -> PointsList:
    """Sample point data for testing."""
    return [(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)]


@pytest.fixture
def large_sample_points() -> PointsList:
    """Larger sample point data for testing."""
    return [
        (1, 100.0, 200.0),
        (2, 150.0, 250.0),
        (3, 200.0, 300.0),
        (4, 250.0, 350.0),
        (5, 300.0, 400.0),
        (6, 350.0, 450.0),
    ]


# =============================================================================
# Shared Mock Classes for Testing
# =============================================================================


class BaseMockCurveView:
    """Base mock CurveView with common attributes and methods for testing.

    This class provides the minimal common functionality needed by most tests.
    Specific test files can inherit and extend this for their needs.
    """

    def __init__(
        self,
        width: int = 800,
        height: int = 600,
        img_width: int = 1920,
        img_height: int = 1080,
        zoom_factor: float = 1.0,
        offset_x: float = 0.0,
        offset_y: float = 0.0,
        selected_points: set[int] | None = None,
    ):
        # Core dimensions
        self.width_val = width
        self.height_val = height
        self.image_width = img_width
        self.image_height = img_height

        # Transformation state
        self.zoom_factor = zoom_factor
        self.offset_x = offset_x
        self.offset_y = offset_y
        self.x_offset = 0.0  # Manual pan offset
        self.y_offset = 0.0  # Manual pan offset

        # Data and selection
        self.points = []
        self.curve_data = []
        self.selected_points = selected_points or set()
        self.selected_point_idx = min(selected_points) if selected_points else -1

        # Display flags
        self.show_background = True
        self.show_grid = False
        self.show_velocity_vectors = False
        self.show_all_frame_numbers = False
        self.show_crosshair = False
        self.background_visible = True
        self.grid_visible = True

        # UI state
        self.update_called = False
        self.background_opacity = 1.0
        self.point_radius = 5
        self.grid_line_width = 1
        self.grid_color = QColor(100, 100, 100)

        # Mock UI components
        self.frame_marker_label = MagicMock()
        self.timeline_slider = MagicMock()
        self.timeline_slider.minimum.return_value = 1
        self.timeline_slider.maximum.return_value = 100

    def width(self) -> int:
        return self.width_val

    def height(self) -> int:
        return self.height_val

    def update(self) -> None:
        self.update_called = True

    def setPoints(
        self,
        points: list[tuple[int, float, float] | tuple[int, float, float, bool | str]],
        image_width: int = 0,
        image_height: int = 0,
        preserve_view: bool = False,
    ) -> None:
        self.points = points
        if image_width:
            self.image_width = image_width
        if image_height:
            self.image_height = image_height

    def get_selected_points(self) -> list[int]:
        return list(self.selected_points)

    def is_point_selected(self, idx: int) -> bool:
        return idx in self.selected_points

    def selectPointByIndex(self, idx: int) -> None:
        self.selected_point_idx = idx
        self.selected_points = {idx}

    def get_point_data(self, idx: int) -> tuple[int, float, float, str | None]:
        if not self.points or idx >= len(self.points):
            return (0, 0.0, 0.0, None)
        point = self.points[idx]
        if len(point) == 3:
            return (point[0], point[1], point[2], None)
        else:
            return point


class ProtocolCompliantMockCurveView(BaseMockCurveView):
    """Mock CurveView that fully implements CurveViewProtocol.

    Use this when tests require full protocol compliance.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Additional protocol requirements
        self.flip_y_axis = kwargs.get("flip_y_axis", True)
        self.scale_to_image = kwargs.get("scale_to_image", False)
        self.background_image = MagicMock() if self.scale_to_image else None
        self.main_window = None

        # Image sequence
        self.image_sequence_path = ""
        self.current_image_idx = -1
        self.image_filenames = []
        self.image_changed = None

        # Rubber band selection
        self.rubber_band: QRubberBand | None = None
        self.rubber_band_origin: QPointF = QPointF(0, 0)
        self.rubber_band_active: bool = False

        # Drag/pan state
        self.drag_active: bool = False
        self.last_drag_pos: QPointF | None = None
        self.pan_active: bool = False
        self.last_pan_pos: QPointF | None = None

        # Additional UI elements
        self.nudge_increment = 1.0
        self.current_increment_index = 0
        self.available_increments = [0.1, 1.0, 10.0]
        self.selection_rect = QRect()

        # Callbacks
        self._on_point_moved: int | None = None
        self._on_point_selected: int = -1
        self._on_selection_changed: bool = False

        # Colors and pens
        self.point_color = MagicMock()
        self.selected_point_color = MagicMock()
        self.interpolated_point_color = MagicMock()
        self.selected_interpolated_point_color = MagicMock()
        self.frame_number_color = MagicMock()
        self.line_pen = MagicMock()
        self.selected_line_pen = MagicMock()
        self.point_pen = MagicMock()
        self.selected_point_pen = MagicMock()
        self.interpolated_point_pen = MagicMock()
        self.selected_interpolated_point_pen = MagicMock()
        self.crosshair_pen = MagicMock()

        # Additional state
        self.velocity_data: dict[int, dict[str, float]] = {}
        self.info_label = MagicMock()
        self.current_frame = 0
        self.point_status_callback = MagicMock()

    # Protocol required methods
    def point_selected(self, index: int) -> None:
        self._on_point_selected = index

    def selection_changed(self) -> None:
        self._on_selection_changed = True

    def point_moved(self, index: int, x: float, y: float) -> None:
        pass

    def findPointAt(self, pos: QPointF) -> int:
        return -1

    def setFocus(self) -> None:
        pass

    def setCurrentImageByIndex(self, idx: int) -> None:
        self.current_image_idx = idx

    def setBackgroundOpacity(self, opacity: float) -> None:
        self.background_opacity = opacity

    def centerOnSelectedPoint(self) -> bool:
        return True

    def setImageSequence(self, path: str, filenames: list[str]) -> None:
        self.image_sequence_path = path
        self.image_filenames = filenames

    def set_curve_data(self, curve_data: list[tuple[int, float, float] | tuple[int, float, float, bool | str]]) -> None:
        self.curve_data = curve_data

    def get_selected_indices(self) -> list[int]:
        return list(self.selected_points)

    def setVelocityData(self, velocities: list[tuple[float, float]]) -> None:
        pass

    def toggleVelocityVectors(self, enabled: bool = True) -> None:
        self.show_velocity_vectors = enabled

    def toggle_point_interpolation(self, idx: int) -> None:
        pass

    def toggleBackgroundVisible(self, visible: bool = True) -> None:
        self.background_visible = visible

    def setCursor(self, cursor: Any) -> None:
        pass

    def unsetCursor(self) -> None:
        pass

    def setToolTip(self, tooltip: str) -> None:
        pass

    def set_background_image(self, img_path: str) -> bool:
        return True

    # Qt event handlers
    def resizeEvent(self, event: Any) -> None:
        pass

    def closeEvent(self, event: Any) -> None:
        pass

    def wheelEvent(self, event: Any) -> None:
        pass

    def paintEvent(self, event: Any) -> None:
        pass

    def mousePressEvent(self, event: Any) -> None:
        pass

    def mouseMoveEvent(self, event: Any) -> None:
        pass

    def mouseReleaseEvent(self, event: Any) -> None:
        pass

    def keyPressEvent(self, event: Any) -> None:
        pass

    @property
    def qwidget(self) -> Any:
        return self

    def update_image_label(self) -> None:
        pass

    def statusBar(self) -> Any:
        if not hasattr(self, "status_bar"):
            self.status_bar = MagicMock()
        return self.status_bar

    def update_status_message(self, message: str) -> None:
        pass

    def refresh_point_edit_controls(self) -> None:
        pass

    def add_to_history(self) -> None:
        pass

    def setup_timeline(self, start_frame: int, end_frame: int) -> None:
        pass

    def emit(self, *args: Any, **kwargs: Any) -> None:
        pass


class BaseMockMainWindow:
    """Base mock MainWindow with common attributes for testing."""

    def __init__(self, curve_data: PointsList | None = None, selected_indices: list[int] | None = None):
        # Core data
        self.curve_data = curve_data or [(1, 100.0, 200.0), (2, 300.0, 400.0), (3, 500.0, 600.0)]
        self.selected_indices = selected_indices or []

        # UI references
        self.curve_view = None
        self.qwidget = MagicMock()

        # State tracking
        self.history_added = False
        self.status_bar_message = None
        self.history = []
        self.history_index = -1

        # Image data
        self.image_width = 1920
        self.image_height = 1080
        self.default_directory = ""
        self.image_sequence_path = ""
        self.image_filenames = []

    def add_to_history(self) -> None:
        self.history_added = True
        self.history_index += 1
        self.history = self.history[: self.history_index] + [{"state": "mock"}]

    def statusBar(self):
        """Return a mock status bar object."""

        class MockStatusBar:
            def __init__(self, main_window):
                self.main_window = main_window

            def showMessage(self, message: str, timeout: int = 0) -> None:
                self.main_window.status_bar_message = message

        return MockStatusBar(self)

    def update_status_message(self, message: str) -> None:
        self.status_bar_message = message

    def update_image_label(self) -> None:
        pass

    def refresh_point_edit_controls(self) -> None:
        pass

    def setup_timeline(self, start_frame: int, end_frame: int) -> None:
        pass


class LazyUIMockMainWindow(BaseMockMainWindow):
    """Mock MainWindow with lazy UI component creation (inspired by test_main_window_clean.py)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._mock_cache = {}

        # Define which attributes should be buttons with 'clicked' signal
        self._button_attrs = {
            "save_button",
            "add_point_button",
            "update_point_button",
            "next_frame_button",
            "prev_frame_button",
            "first_frame_button",
            "last_frame_button",
            "play_button",
            "scale_button",
            "offset_button",
            "rotate_button",
            "smooth_batch_button",
            "select_all_button",
            "smooth_button",
            "filter_button",
            "fill_gaps_button",
            "extrapolate_button",
            "detect_problems_button",
            "shortcuts_button",
            "undo_button",
            "redo_button",
            "toggle_bg_button",
            "load_images_button",
            "next_image_button",
            "prev_image_button",
            "analyze_button",
            "go_button",
        }

        # Define attributes that need specific mock behaviors
        self._special_attrs = {
            "point_size_spin": lambda: MagicMock(value=MagicMock(return_value=5)),
            "x_edit": lambda: MagicMock(text=MagicMock(return_value="0.0")),
            "y_edit": lambda: MagicMock(text=MagicMock(return_value="0.0")),
            "z_edit": lambda: MagicMock(text=MagicMock(return_value="0.0")),
            "frame_edit": lambda: MagicMock(text=MagicMock(return_value="1")),
            "timeline_slider": lambda: MagicMock(value=MagicMock(return_value=1)),
            "opacity_slider": lambda: MagicMock(value=MagicMock(return_value=100)),
        }

    def __getattr__(self, name: str) -> Any:
        """Lazy creation of UI components."""
        if name not in self._mock_cache:
            if name in self._button_attrs:
                # Create button with clicked signal
                mock = MagicMock()
                mock.clicked = MagicMock()
                self._mock_cache[name] = mock
            elif name in self._special_attrs:
                # Create special mock
                self._mock_cache[name] = self._special_attrs[name]()
            else:
                # Create generic mock
                self._mock_cache[name] = MagicMock()

        return self._mock_cache[name]


# Fixture factories for common mock objects
@pytest.fixture
def mock_curve_view():
    """Create a basic mock curve view for testing."""
    return BaseMockCurveView()


@pytest.fixture
def mock_curve_view_with_selection():
    """Create a mock curve view with selected points."""
    return BaseMockCurveView(selected_points={1, 2})


@pytest.fixture
def protocol_compliant_mock_curve_view():
    """Create a fully protocol-compliant mock curve view."""
    return ProtocolCompliantMockCurveView()


@pytest.fixture
def mock_main_window():
    """Create a basic mock main window for testing."""
    return BaseMockMainWindow()


@pytest.fixture
def mock_main_window_with_data():
    """Create a mock main window with sample curve data."""
    return BaseMockMainWindow(
        curve_data=[(1, 100.0, 200.0), (2, 150.0, 250.0), (3, 200.0, 300.0)], selected_indices=[1]
    )


@pytest.fixture
def lazy_mock_main_window():
    """Create a mock main window with lazy UI component creation."""
    return LazyUIMockMainWindow()

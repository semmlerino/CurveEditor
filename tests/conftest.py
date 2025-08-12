#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for all tests.

This module provides common test fixtures and configurations, including
proper Qt application initialization for tests that require Qt components.
"""

from collections.abc import Generator
from typing import Any, cast, final
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QPointF, QRect
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QApplication

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
    else:
        # Use existing instance, cast to QApplication for type safety
        app = cast(QApplication, app)

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
        from services import get_transform_service, get_data_service, get_interaction_service, get_ui_service
        
        # Clear caches for consolidated services if they exist
        transform_service = get_transform_service()
        if transform_service and hasattr(transform_service, 'clear_cache'):
            transform_service.clear_cache()
            
        data_service = get_data_service()
        if data_service and hasattr(data_service, 'clear_cache'):
            data_service.clear_cache()
            
        interaction_service = get_interaction_service()
        if interaction_service and hasattr(interaction_service, 'clear_cache'):
            interaction_service.clear_cache()
            
        ui_service = get_ui_service()
        if ui_service and hasattr(ui_service, 'clear_cache'):
            ui_service.clear_cache()
            
    except ImportError:
        pass  # Services might not be available in all tests

    # Force garbage collection of Qt objects
    import gc

    _ = gc.collect()

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
        if hasattr(item, "module") and item.module is not None:
            test_module = item.module
            if hasattr(test_module, "__file__") and test_module.__file__ is not None:
                # Read the test file to check for Qt imports
                try:
                    with open(test_module.__file__, encoding="utf-8") as f:
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
def curve_view(qapp: QApplication) -> "CurveView":
    """Create a CurveView instance for testing (legacy)."""
    from data.curve_view import CurveView

    # qapp parameter ensures Qt application is initialized
    _ = qapp  # Acknowledge parameter usage for type checker
    return CurveView()

@pytest.fixture
def curve_view_widget(qapp: QApplication) -> "CurveViewWidget":
    """Create a CurveViewWidget instance for testing."""
    from ui.curve_view_widget import CurveViewWidget

    # qapp parameter ensures Qt application is initialized
    _ = qapp  # Acknowledge parameter usage for type checker
    return CurveViewWidget()

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
# Protocol-Compliant Mock Infrastructure for Testing
# =============================================================================

# Import the latest protocols for full compliance

@final
class ProtocolCompliantMockCurveView:
    """Full protocol-compliant mock CurveView that implements CurveViewProtocol.

    This mock implements ALL attributes and methods required by CurveViewProtocol
    in protocols_v2.py, including properties with proper getters and setters.

    Use this as a base class for test-specific curve view mocks.
    """

    def __init__(self, **kwargs: Any) -> None:
        # Extract constructor parameters
        width = kwargs.get("width", 800)
        height = kwargs.get("height", 600)
        img_width = kwargs.get("image_width", 1920)
        img_height = kwargs.get("image_height", 1080)
        selected_points = kwargs.get("selected_points", set())
        selected_point_idx = kwargs.get("selected_point_idx", -1)

        # Core dimensions
        self.width_val = width
        self.height_val = height
        self.image_width = img_width
        self.image_height = img_height

        # ImageSequenceProtocol attributes (plain attributes)
        self.image_sequence_path = ""
        self.current_image_idx = -1
        self.image_filenames = []
        self.background_image: Any = None
        self.image_changed = MagicMock()

        # CurveViewProtocol attributes (plain attributes)
        self.show_background = True
        self.show_grid = False
        self.show_velocity_vectors = False
        self.show_all_frame_numbers = False
        self.show_crosshair = False
        self.background_opacity = 1.0
        self.point_radius = 5
        self.grid_color = QColor(100, 100, 100)
        self.grid_line_width = 1
        # Create proper mocks for UI components that tests interact with
        self.frame_marker_label = MagicMock()
        self.frame_marker_label.setToolTip = MagicMock()
        # Create ui_components mock if it doesn't exist
        self.ui_components = MagicMock()
        self.ui_components.timeline_slider = MagicMock()
        self.ui_components.timeline_slider.value = MagicMock(return_value=1)
        self.ui_components.timeline_slider.setValue = MagicMock()
        self.ui_components.timeline_slider.minimum = MagicMock(return_value=1)
        self.ui_components.timeline_slider.maximum = MagicMock(return_value=100)
        self.nudge_increment = 1.0
        self.current_increment_index = 0
        self.available_increments = [0.1, 1.0, 10.0]
        self.main_window = None
        self.last_action_was_fit = False
        self.selection_rect = QRect()

        # Selection rectangle support
        self.rubber_band = None
        self.rubber_band_origin = QPointF(0, 0)
        self.rubber_band_active = False

        # Interaction state
        self.drag_active = False
        self.last_drag_pos = None
        self.pan_active = False
        self.last_pan_pos = None

        # Debug attributes
        self.debug_mode = False
        self.debug_img_pos = None
        self.debug_origin_pos = None
        self.debug_origin_no_scale_pos = None
        self.debug_width_pt = 0.0

        # Transformation attributes for testing
        self.center_offset_x = 0.0
        self.center_offset_y = 0.0
        self.auto_center_enabled = True

        # Signals
        self.point_selected = MagicMock()
        self.point_moved = MagicMock()
        self.selection_changed = MagicMock()

        # Private state for properties
        self._zoom_factor = kwargs.get("zoom_factor", 1.0)
        self._offset_x = kwargs.get("offset_x", 0.0)
        self._offset_y = kwargs.get("offset_y", 0.0)
        self._x_offset = kwargs.get("x_offset", 0.0)
        self._y_offset = kwargs.get("y_offset", 0.0)
        self._flip_y_axis = kwargs.get("flip_y_axis", True)
        self._scale_to_image = kwargs.get("scale_to_image", False)
        self._selected_point_idx = selected_point_idx
        self._points = kwargs.get("points", [])
        self._curve_data = kwargs.get("curve_data", [])
        self._selected_points = selected_points

        # Private attributes for rendering
        self._needs_initial_fit = True
        self._has_fitted = False

        # Update methods - track calls with update_called flag
        self.update_called = False

        # Create a callable mock that also tracks calls
        self.update = self._create_update_mock()

    # Properties required by protocols_v2.py (ImageSequenceProtocol)
    @property
    def zoom_factor(self) -> float:
        return self._zoom_factor

    @zoom_factor.setter
    def zoom_factor(self, value: float) -> None:
        self._zoom_factor = value

    @property
    def offset_x(self) -> float:
        return self._offset_x

    @offset_x.setter
    def offset_x(self, value: float) -> None:
        self._offset_x = value

    @property
    def offset_y(self) -> float:
        return self._offset_y

    @offset_y.setter
    def offset_y(self, value: float) -> None:
        self._offset_y = value

    @property
    def selected_point_idx(self) -> int:
        return self._selected_point_idx

    @selected_point_idx.setter
    def selected_point_idx(self, value: int) -> None:
        self._selected_point_idx = value

    @property
    def scale_to_image(self) -> bool:
        return self._scale_to_image

    @scale_to_image.setter
    def scale_to_image(self, value: bool) -> None:
        self._scale_to_image = value

    # Properties required by CurveViewProtocol
    @property
    def x_offset(self) -> float:
        return self._x_offset

    @x_offset.setter
    def x_offset(self, value: float) -> None:
        self._x_offset = value

    @property
    def y_offset(self) -> float:
        return self._y_offset

    @y_offset.setter
    def y_offset(self, value: float) -> None:
        self._y_offset = value

    @property
    def flip_y_axis(self) -> bool:
        return self._flip_y_axis

    @flip_y_axis.setter
    def flip_y_axis(self, value: bool) -> None:
        self._flip_y_axis = value

    @property
    def points(self) -> PointsList:
        return self._points

    @points.setter
    def points(self, value: PointsList) -> None:
        self._points = value

    @property
    def selected_points(self) -> set[int]:
        return self._selected_points

    @selected_points.setter
    def selected_points(self, value: set[int]) -> None:
        self._selected_points = value

    @property
    def curve_data(self) -> PointsList:
        return self._curve_data

    @curve_data.setter
    def curve_data(self, value: PointsList) -> None:
        self._curve_data = value

    # Qt Widget methods
    def width(self) -> int:
        return self.width_val

    def height(self) -> int:
        return self.height_val

    def rect(self) -> QRect:
        return QRect(0, 0, self.width_val, self.height_val)

    def hasFocus(self) -> bool:
        return False

    def setCursor(self, cursor: Any) -> None:
        pass

    def unsetCursor(self) -> None:
        pass

    def _create_update_mock(self) -> MagicMock:
        """Create a mock that acts like both a method and a MagicMock."""

        def update_impl(*args: Any, **kwargs: Any) -> None:
            self.update_called = True

        mock = MagicMock(side_effect=update_impl)
        return mock

    # ImageSequenceProtocol methods
    def setFocus(self) -> None:
        pass

    def setCurrentImageByIndex(self, idx: int) -> None:
        self.current_image_idx = idx

    def centerOnSelectedPoint(self) -> bool:
        return True

    def setImageSequence(self, path: str, filenames: list[str]) -> None:
        self.image_sequence_path = path
        self.image_filenames = filenames

    def emit(self, *args: Any, **kwargs: Any) -> bool:
        return True

    # CurveViewProtocol methods
    def setCurrentImageByFrame(self, frame: int) -> None:
        # Find image index from frame
        self.current_image_idx = max(0, frame - 1)

    def toggleBackgroundVisible(self, visible: bool) -> None:
        self.show_background = visible

    def setBackgroundOpacity(self, opacity: float) -> None:
        self.background_opacity = opacity

    def get_selected_points(self) -> list[int]:
        return list(self.selected_points)

    def selectPointByIndex(self, idx: int) -> None:
        self.selected_point_idx = idx
        self.selected_points = {idx}

    def clearSelection(self) -> None:
        self.selected_points = set()
        self.selected_point_idx = -1

    def addToSelection(self, idx: int) -> None:
        self.selected_points.add(idx)

    def removeFromSelection(self, idx: int) -> None:
        self.selected_points.discard(idx)

    def set_points(self, points: PointsList) -> None:
        self.points = points

    def setPoints(
        self, points: PointsList, image_width: int = 0, image_height: int = 0, preserve_view: bool = False
    ) -> None:
        """Protocol-required setPoints method with full signature."""
        self.points = points
        if image_width:
            self.image_width = image_width
        if image_height:
            self.image_height = image_height
        # preserve_view is handled at the service level

    def add_point(self, frame: int, x: float, y: float) -> None:
        self.points.append((frame, x, y))

    def delete_selected_points(self) -> None:
        # Remove selected points from points list
        indices_to_remove = sorted(self.selected_points, reverse=True)
        for idx in indices_to_remove:
            if 0 <= idx < len(self.points):
                del self.points[idx]
        self.selected_points = set()

    def get_point_at_position(self, pos: Any) -> int:
        return -1

    def get_selected_point_data(self) -> tuple[int, float, float] | None:
        if self.selected_point_idx >= 0 and self.selected_point_idx < len(self.points):
            point = self.points[self.selected_point_idx]
            return (point[0], point[1], point[2])
        return None

    def update_point(self, idx: int, x: float, y: float) -> None:
        if 0 <= idx < len(self.points):
            frame = self.points[idx][0]
            self.points[idx] = (frame, x, y)

    def get_point_data(self, idx: int) -> tuple[int, float, float, str | None]:
        if 0 <= idx < len(self.points):
            point = self.points[idx]
            return (point[0], point[1], point[2], None)
        return (0, 0.0, 0.0, None)

    # Event handlers
    def paintEvent(self, event: Any) -> None:
        pass

    def resizeEvent(self, event: Any) -> None:
        pass

    def fitToWindow(self) -> None:
        pass

    def fit_to_window(self) -> None:
        pass

    def zoom(self, factor: float, center: Any = None) -> None:
        self.zoom_factor *= factor

    def pan(self, dx: float, dy: float) -> None:
        self.offset_x += dx
        self.offset_y += dy

    def mousePressEvent(self, event: Any) -> None:
        pass

    def mouseMoveEvent(self, event: Any) -> None:
        pass

    def mouseReleaseEvent(self, event: Any) -> None:
        pass

    def wheelEvent(self, event: Any) -> None:
        pass

    def keyPressEvent(self, event: Any) -> None:
        pass

    # Visualization methods
    def toggleGrid(self, show: bool) -> None:
        self.show_grid = show

    def toggleVelocityVectors(self, show: bool) -> None:
        self.show_velocity_vectors = show

    def setPointRadius(self, radius: int) -> None:
        self.point_radius = radius

    def setVelocityData(self, velocities: Any) -> None:
        pass

    def toggleAllFrameNumbers(self, enabled: bool) -> None:
        self.show_all_frame_numbers = enabled

    def centerOnPoint(self, frame: int, x: float, y: float) -> None:
        pass

    def get_bounds(self) -> tuple[int, int, float, float, float, float] | None:
        if not self.points:
            return None
        frames = [p[0] for p in self.points]
        xs = [p[1] for p in self.points]
        ys = [p[2] for p in self.points]
        return (min(frames), max(frames), min(xs), max(xs), min(ys), max(ys))

    def reset_view(self) -> None:
        self.zoom_factor = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

    def toggle_y_flip(self) -> None:
        self.flip_y_axis = not self.flip_y_axis

    def toggle_scale_to_image(self) -> None:
        self.scale_to_image = not self.scale_to_image

    def getCurrentImagePath(self) -> str | None:
        if 0 <= self.current_image_idx < len(self.image_filenames):
            return self.image_filenames[self.current_image_idx]
        return None

    def toggleBackgroundImage(self) -> None:
        self.show_background = not self.show_background

    def setBackgroundImage(self, image_path: str) -> None:
        pass

    def clearBackgroundImage(self) -> None:
        self.background_image = None

    def loadCurrentImage(self) -> None:
        pass

    def get_selected_indices(self) -> list[int]:
        return list(self.selected_points)

    def setSizePolicy(self, policy: Any) -> None:
        pass

    def set_selected_indices(self, indices: list[int]) -> None:
        self.selected_points = set(indices)

    def _draw_empty_state(self, painter: Any) -> None:
        pass

    def findPointAt(self, pos: Any) -> int:
        return -1

    def toggle_point_interpolation(self, idx: int) -> None:
        pass

    def transform_point(self, point: Any) -> Any:
        """Mock implementation of transform_point method for protocol compliance."""
        return MagicMock()

@final
class ProtocolCompliantMockMainWindow:
    """Full protocol-compliant mock MainWindow that implements MainWindowProtocol.

    This mock implements ALL attributes and methods required by MainWindowProtocol
    in protocols_v2.py, using lazy creation to avoid unnecessary mock instances.

    Use this as a base class for test-specific main window mocks.
    """

    def __init__(self, **kwargs: Any) -> None:
        # Core data attributes that are frequently accessed
        self.curve_data = kwargs.get("curve_data", [])
        self.selected_indices = kwargs.get("selected_indices", [])
        self.curve_view = kwargs.get("curve_view", ProtocolCompliantMockCurveView())

        # Image and file attributes
        self.image_sequence_path = ""
        self.image_filenames = []
        self.default_directory = ""
        self.last_opened_file = ""
        self.image_width = 1920
        self.image_height = 1080
        self.track_data_loaded = False

        # Point attributes
        self.point_name = "Test Point"
        self.point_color = "red"

        # State tracking
        self.current_frame = 0
        self.history = []
        self.history_index = -1
        self.max_history_size = 20

        # Additional required attributes
        self.original_curve_view = None
        self.curve_view_class = type(ProtocolCompliantMockCurveView)

        # Cache for lazy UI component creation
        self._ui_cache: dict[str, Any] = {}

        # Pre-create commonly used components
        self._status_bar = MagicMock()
        self._status_bar.showMessage = MagicMock()

    def __getattr__(self, name: str) -> Any:
        """Lazy creation of UI components to implement MainWindowProtocol."""
        if name in self._ui_cache:
            return self._ui_cache[name]

        # Create appropriate mock based on component type
        if name.endswith("_button"):
            mock = MagicMock()
            mock.clicked = MagicMock()  # QPushButton signal
            self._ui_cache[name] = mock
        elif name.endswith("_label"):
            mock = MagicMock()
            mock.setText = MagicMock()
            mock.text = MagicMock(return_value="")
            self._ui_cache[name] = mock
        elif name.endswith("_slider"):
            mock = MagicMock()
            mock.value = MagicMock(return_value=0)
            mock.setValue = MagicMock()
            mock.valueChanged = MagicMock()  # QSlider signal
            self._ui_cache[name] = mock
        elif name.endswith("_edit"):
            mock = MagicMock()
            mock.text = MagicMock(return_value="")
            mock.setText = MagicMock()
            mock.textChanged = MagicMock()  # QLineEdit signal
            self._ui_cache[name] = mock
        elif name.endswith("_spinbox") or name.endswith("_spin"):
            mock = MagicMock()
            mock.value = MagicMock(return_value=0)
            mock.setValue = MagicMock()
            mock.valueChanged = MagicMock()  # QSpinBox signal
            self._ui_cache[name] = mock
        elif name.endswith("_combo"):
            mock = MagicMock()
            mock.currentText = MagicMock(return_value="")
            mock.setCurrentText = MagicMock()
            mock.currentTextChanged = MagicMock()  # QComboBox signal
            self._ui_cache[name] = mock
        elif name.endswith("_splitter"):
            mock = MagicMock()
            mock.setSizes = MagicMock()
            mock.sizes = MagicMock(return_value=[])
            self._ui_cache[name] = mock
        elif name.endswith("_container") or name.endswith("_widget"):
            mock = MagicMock()
            self._ui_cache[name] = mock
        elif name.endswith("_timer"):
            mock = MagicMock()
            mock.start = MagicMock()
            mock.stop = MagicMock()
            mock.timeout = MagicMock()  # QTimer signal
            self._ui_cache[name] = mock
        elif name.startswith("_"):
            # Private attributes - create generic mock
            mock = MagicMock()
            self._ui_cache[name] = mock
        else:
            # Generic UI component
            mock = MagicMock()
            self._ui_cache[name] = mock

        return self._ui_cache[name]

    # Required methods from MainWindowProtocol
    @property
    def qwidget(self) -> Any:
        """Return the underlying QWidget."""
        return self

    def update_image_label(self) -> None:
        pass

    def statusBar(self) -> Any:
        return self._status_bar

    def update_status_message(self, message: str) -> None:
        self._status_bar.showMessage(message)

    def refresh_point_edit_controls(self) -> None:
        pass

    def add_to_history(self) -> None:
        self.history_index += 1
        self.history = self.history[: self.history_index] + [{"state": "mock"}]

    def setup_timeline(self) -> None:
        pass

    def setImageSequence(self, filenames: list[str]) -> None:
        self.image_filenames = filenames

    def enable_point_controls(self, enabled: bool) -> None:
        pass

    def on_image_changed(self, index: int) -> None:
        pass

    def apply_ui_smoothing(self) -> None:
        pass

    def setCentralWidget(self, widget: Any) -> None:
        pass

    def setStatusBar(self, statusbar: Any) -> None:
        self._status_bar = statusbar

    def set_centering_enabled(self, enabled: bool) -> None:
        pass

    def centralWidget(self) -> Any:
        return None

    def restoreGeometry(self, geometry: bytes) -> bool:
        return True

    def restoreState(self, state: bytes, version: int = 0) -> bool:
        return True

    def saveGeometry(self) -> bytes:
        return b""

    def saveState(self, version: int = 0) -> bytes:
        return b""

@final
class BaseMockCurveView:
    """Base mock CurveView with common attributes and methods for testing.

    This class provides the minimal common functionality needed by most tests.
    Specific test files can inherit and extend this for their needs.
    """

    # Type annotations for all attributes
    width_val: int
    height_val: int
    image_width: int
    image_height: int
    zoom_factor: float
    offset_x: float
    offset_y: float
    x_offset: float
    y_offset: float
    points: PointsList
    curve_data: PointsList
    selected_points: set[int]
    selected_point_idx: int
    show_background: bool
    show_grid: bool
    show_velocity_vectors: bool
    show_all_frame_numbers: bool
    show_crosshair: bool
    background_visible: bool
    grid_visible: bool
    update_called: bool
    background_opacity: float
    point_radius: int
    grid_line_width: int
    grid_color: QColor
    frame_marker_label: MagicMock
    timeline_slider: MagicMock

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
    ) -> None:
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
        self.ui_components = MagicMock()
        self.ui_components.timeline_slider = MagicMock()
        self.ui_components.timeline_slider.minimum.return_value = 1
        self.ui_components.timeline_slider.maximum.return_value = 100

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
        self.points = cast(PointsList, points)
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
        elif len(point) == 4:
            # Cast to ensure proper types
            return (int(point[0]), float(point[1]), float(point[2]), str(point[3]) if point[3] is not None else None)
        else:
            # Handle unexpected point formats
            return (0, 0.0, 0.0, None)

class BaseMockMainWindow:
    """Base mock MainWindow with common attributes for testing."""

    # Type annotations for all attributes
    curve_data: PointsList
    selected_indices: list[int]
    curve_view: Any | None
    history_added: bool
    status_bar_message: str | None
    history: list[dict[str, Any]]
    history_index: int
    image_width: int
    image_height: int
    default_directory: str
    image_sequence_path: str
    image_filenames: list[str]

    def __init__(self, curve_data: PointsList | None = None, selected_indices: list[int] | None = None) -> None:
        # Core data
        self.curve_data = curve_data or [(1, 100.0, 200.0), (2, 300.0, 400.0), (3, 500.0, 600.0)]
        self.selected_indices = selected_indices or []

        # UI references
        self.curve_view = None

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
            def __init__(self, main_window: "BaseMockMainWindow") -> None:
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

    @property
    def qwidget(self) -> Any:
        """Return the underlying QWidget - for MainWindow this is self."""
        return self

@final
class LazyUIMockMainWindow(BaseMockMainWindow):
    """Mock MainWindow with lazy UI component creation (inspired by test_main_window_clean.py)."""

    # Type annotations for additional attributes
    _mock_cache: dict[str, Any]
    _button_attrs: set[str]
    _special_attrs: dict[str, Any]

    def __init__(self, **kwargs: Any) -> None:
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
def protocol_compliant_mock_main_window():
    """Create a fully protocol-compliant mock main window."""
    return ProtocolCompliantMockMainWindow()

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

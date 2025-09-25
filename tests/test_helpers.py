#!/usr/bin/env python3
"""
Unified Test Helpers for CurveEditor

Following best practices from UNIFIED_TESTING_GUIDE_DO_NOT_DELETE.md:
- Real components over mocks
- Thread-safe image handling (QImage instead of QPixmap)
- Proper signal test doubles
- Test behavior, not implementation
"""

from collections.abc import Callable
from typing import Any
from unittest.mock import Mock

from core.models import CurvePoint
from tests.qt_test_helpers import ThreadSafeTestImage

# Qt imports with fallback for non-GUI environments
try:
    from PySide6.QtCore import QObject, QSize
    from PySide6.QtGui import QAction, QColor, QImage
    from PySide6.QtWidgets import QLabel, QPushButton, QSlider, QSpinBox, QStatusBar, QWidget

    HAS_QT = True
except ImportError:
    HAS_QT = False

    # Stub classes for non-Qt test environments
    class QObject:
        pass

    class QSize:
        def __init__(self, w: int, h: int) -> None:
            self.w = w
            self.h = h

    class QImage:
        Format_RGB32 = None

        def __init__(self, *args: Any) -> None:
            pass

        def fill(self, color: Any) -> None:
            pass

        def isNull(self) -> bool:
            return False

        def sizeInBytes(self) -> int:
            return 0

    class QColor:
        def __init__(self, *args: Any) -> None:
            pass

    class QWidget:
        def __init__(self, *args: Any) -> None:
            pass

        def setText(self, text: str) -> None:
            pass

        def setMaximum(self, value: int) -> None:
            pass

        def setMinimum(self, value: int) -> None:
            pass

        def setValue(self, value: int) -> None:
            pass

        def value(self) -> int:
            return 0

        def showMessage(self, message: str, timeout: int = 0) -> None:
            pass

    class QPushButton:
        def __init__(self, *args: Any) -> None:
            pass

    class QAction:
        def __init__(self, *args: Any) -> None:
            pass

    QLabel = QSlider = QSpinBox = QStatusBar = QWidget


# ==================== Type Aliases ====================

# Type aliases for test data - aligned with core.type_aliases
Point3 = tuple[int, float, float]
Point4 = tuple[int, float, float, str | bool]
PointsList = list[Point3 | Point4]  # Matches CurveDataList


# ==================== Thread-Safe Image Handling ====================


class TestImagePool:
    """
    Reuse ThreadSafeTestImage instances for performance.

    Reduces object creation overhead in tests with many image operations.
    """

    def __init__(self):
        self._pool = []

    def get_test_image(self, width: int = 100, height: int = 100) -> ThreadSafeTestImage:
        """Get a test image from the pool or create a new one."""
        # For now, just create new ones (could optimize later)
        # Pool implementation would check dimensions and reuse
        return ThreadSafeTestImage(width, height)

    def return_image(self, image: ThreadSafeTestImage) -> None:
        """Return an image to the pool for reuse."""
        # Reset to white before returning to pool
        image.fill()
        self._pool.append(image)


# ==================== Signal Test Doubles ====================


class TestSignal:
    """
    Lightweight signal test double for non-Qt components.

    Use this instead of Mock for signal testing in test doubles.
    For real Qt widgets, use QSignalSpy instead.
    """

    def __init__(self):
        self.emissions = []
        self.callbacks = []

    def emit(self, *args):
        """Emit signal with arguments."""
        self.emissions.append(args)
        for callback in self.callbacks:
            try:
                callback(*args)
            except Exception as e:
                # Log but don't fail on callback errors
                print(f"TestSignal callback error: {e}")

    def connect(self, callback: Callable):
        """Connect callback to signal."""
        self.callbacks.append(callback)

    def disconnect(self, callback: Callable):
        """Disconnect callback from signal."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    @property
    def was_emitted(self) -> bool:
        """Check if signal was emitted at least once."""
        return len(self.emissions) > 0

    @property
    def emit_count(self) -> int:
        """Get number of times signal was emitted."""
        return len(self.emissions)

    @property
    def last_emission(self):
        """Get last emission arguments."""
        return self.emissions[-1] if self.emissions else None

    def reset(self):
        """Clear all emissions for reuse."""
        self.emissions.clear()


# ==================== Qt Component Test Doubles ====================


class MockUIComponents:
    """Real UI components structure matching real MainWindow.ui interface."""

    def __init__(self):
        # Use real Qt widgets instead of mocks
        if HAS_QT:
            self.undo_button = QPushButton("Undo")
            self.redo_button = QPushButton("Redo")
            self.save_button = QPushButton("Save")
        else:
            # Fallback to mock only in non-Qt environments
            self.undo_button = Mock()
            self.redo_button = Mock()
            self.save_button = Mock()


class MockServices:
    """Mock services structure matching real ServiceFacade interface."""

    def __init__(self):
        self.workflow_state = None  # No workflow_state service in current architecture

    def analyze_curve_bounds(self, data):
        """Return proper curve analysis structure instead of Mock."""
        return {
            "count": len(data) if data else 0,
            "min_frame": min(point[0] for point in data) if data else 0,
            "max_frame": max(point[0] for point in data) if data else 0,
            "bounds": {
                "min_x": min(point[1] for point in data) if data else 0,
                "max_x": max(point[1] for point in data) if data else 0,
                "min_y": min(point[2] for point in data) if data else 0,
                "max_y": max(point[2] for point in data) if data else 0,
            },
        }

    def confirm_action(self, message):
        """Mock confirmation dialog - always return True for tests."""
        return True

    def add_to_history(self):
        """Mock history addition."""
        pass

    def load_track_data_from_file(self, file_path):
        """Mock load track data - return empty list."""
        return []

    def save_track_data_to_file(self, data, file_path):
        """Mock save track data - return success."""
        return True

    def load_track_data(self, parent_widget=None):
        """Mock load track data from dialog."""
        return []


# ==================== Test Implementation Classes ====================


class MockCurveView:
    """Lightweight real CurveView implementation for testing.

    This replaces massive mock objects with a real implementation that has
    actual behavior instead of mocked behavior.
    """

    def __init__(self, curve_data: list[Point3 | Point4] | None = None, **kwargs) -> None:
        # Real data structures - preserve original format
        if curve_data is not None:
            self.curve_data: list[Point3 | Point4] = list(curve_data)  # pyright: ignore[reportAssignmentType]
        else:
            self.curve_data: list[Point3 | Point4] = []  # pyright: ignore[reportAssignmentType]
        self.points: list[Point3 | Point4] = self.curve_data  # Alias for service compatibility
        self.selected_points: set[int] = set()
        self.selected_point_idx: int = -1
        self.current_image_idx: int = 0

        # View state
        self.zoom_factor: float = 1.0
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0
        self.x_offset: float = 0.0  # Protocol alias for offset_x
        self.y_offset: float = 0.0  # Protocol alias for offset_y
        self.pan_offset_x: float = 0.0
        self.pan_offset_y: float = 0.0
        self.manual_offset_x: float = 0.0
        self.manual_offset_y: float = 0.0

        # Interaction state attributes (required by CurveViewProtocol)
        self.drag_active: bool = False
        self.pan_active: bool = False
        self.last_drag_pos: object = None  # QtPointF | None
        self.last_pan_pos: object = None  # QtPointF | None

        # Rubber band selection attributes (required by CurveViewProtocol)
        self.rubber_band: object = None  # QRubberBand | None
        self.rubber_band_active: bool = False
        self.rubber_band_origin: object = None  # QtPointF

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
        self.background_image: object = None

        # Image sequence properties
        self.image_sequence_path: str = ""
        self.image_filenames: list[str] = []
        self.current_image_idx: int = 0

        # Interaction tracking
        self._update_called: bool = False

        # Mouse and keyboard state for testing
        self._mouse_position: tuple[float, float] = (0.0, 0.0)
        self._pressed_keys: set[object] = set()
        self._mouse_buttons: set[object] = set()

        # Initialize with any provided data
        if "curve_data" in kwargs:
            self.set_curve_data(kwargs["curve_data"])

        # Process kwargs to set attributes
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            elif key == "points":
                # Handle points as alias for curve_data
                self.set_curve_data(value)

        # Handle special attribute mappings for ViewState compatibility
        if "offset_x" in kwargs:
            self.pan_offset_x = kwargs["offset_x"]
            self.x_offset = kwargs["offset_x"]
        if "offset_y" in kwargs:
            self.pan_offset_y = kwargs["offset_y"]
            self.y_offset = kwargs["offset_y"]

    def set_curve_data(self, data: list[Point4]) -> None:
        """Set the curve data."""
        self.curve_data = data[:]
        self.points = self.curve_data[:]  # Keep in sync

    def add_point(self, point: Point4) -> None:
        """Add a point to the curve."""
        self.curve_data.append(point)
        # self.points is an alias to self.curve_data, no need to add twice

    def remove_point(self, index: int) -> None:
        """Remove a point by index."""
        if 0 <= index < len(self.curve_data):
            self.curve_data.pop(index)
            # self.points is an alias to self.curve_data, automatically updated

    def update_point(self, index: int, x: float, y: float) -> None:
        """Update a point's position."""
        if 0 <= index < len(self.curve_data):
            old_point = self.curve_data[index]
            if len(old_point) >= 4:
                new_point = (old_point[0], x, y, old_point[3])
            else:
                new_point = (old_point[0], x, y)
            self.curve_data[index] = new_point
            self.points[index] = new_point

    def select_point(self, index: int) -> None:
        """Select a point by index."""
        if 0 <= index < len(self.curve_data):
            self.selected_points.add(index)
            self.selected_point_idx = index

    def deselect_all(self) -> None:
        """Deselect all points."""
        self.selected_points.clear()
        self.selected_point_idx = -1

    def width(self) -> int:
        """Widget width for protocol compatibility."""
        return self.image_width

    def height(self) -> int:
        """Widget height for protocol compatibility."""
        return self.image_height

    def update(self) -> None:
        """Mock update method."""
        self._update_called = True

    @property
    def update_called(self) -> bool:
        """Check if update was called."""
        return self._update_called

    def reset_update_flag(self) -> None:
        """Reset update tracking flag."""
        self._update_called = False

    def repaint(self) -> None:
        """Mock repaint method."""
        self._update_called = True

    def data_to_screen(self, x: float, y: float) -> tuple[float, float]:
        """Simple coordinate transformation."""
        screen_x = x * self.zoom_factor + self.offset_x
        screen_y = y * self.zoom_factor + self.offset_y
        return screen_x, screen_y

    def screen_to_data(self, x: float, y: float) -> tuple[float, float]:
        """Inverse coordinate transformation."""
        if self.zoom_factor == 0:
            return (0, 0)
        data_x = (x - self.offset_x) / self.zoom_factor
        data_y = (y - self.offset_y) / self.zoom_factor
        return data_x, data_y

    def findPointAt(self, x: float, y: float, tolerance: float = 5.0) -> int:
        """Find point near given coordinates."""
        for i, point in enumerate(self.curve_data):
            px, py = self.data_to_screen(point[1], point[2])
            distance = ((px - x) ** 2 + (py - y) ** 2) ** 0.5
            if distance <= tolerance:
                return i
        return -1

    def zoom_in(self, factor: float = 1.2) -> None:
        """Zoom in by factor."""
        self.zoom_factor *= factor

    def zoom_out(self, factor: float = 1.2) -> None:
        """Zoom out by factor."""
        self.zoom_factor /= factor

    def pan(self, dx: float, dy: float) -> None:
        """Pan the view."""
        self.offset_x += dx
        self.offset_y += dy

    def reset_view(self) -> None:
        """Reset view to default."""
        self.zoom_factor = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0

    def center_on_point(self, index: int) -> None:
        """Center view on a point."""
        if 0 <= index < len(self.curve_data):
            point = self.curve_data[index]
            self.offset_x = -point[1] * self.zoom_factor + self.width() / 2
            self.offset_y = -point[2] * self.zoom_factor + self.height() / 2

    def mapToGlobal(self, point: object) -> object:
        """Mock mapToGlobal method."""
        return point

    def setCursor(self, cursor: object) -> None:
        """Mock setCursor method."""
        pass

    def unsetCursor(self) -> None:
        """Mock unsetCursor method."""
        pass

    def get_transform(self) -> object:
        """Get transform object (alias for compatibility)."""
        return self.get_current_transform()

    def get_current_transform(self) -> object:
        """Get current transform object."""
        from unittest.mock import Mock

        transform = Mock()
        transform.data_to_screen = self.data_to_screen
        transform.screen_to_data = self.screen_to_data
        return transform

    def _invalidate_caches(self) -> None:
        """Invalidate any cached data."""
        pass

    def toggleBackgroundVisible(self, visible: bool) -> None:
        """Toggle background visibility."""
        self.show_background = visible

    def toggle_point_interpolation(self, idx: int) -> None:
        """Toggle interpolation status of a point."""
        pass

    def setPoints(self, data: list[Point4], width: int, height: int) -> None:
        """Set points with image dimensions (legacy compatibility)."""
        self.set_curve_data(data)
        self.image_width = width
        self.image_height = height

    def set_selected_indices(self, indices: list[int]) -> None:
        """Set the selected point indices."""
        self.selected_points = set(indices)


class MockMainWindow:
    """Lightweight real MainWindow implementation for testing."""

    def __init__(self) -> None:
        # Core components
        self.curve_view = MockCurveView()
        self.curve_widget = self.curve_view  # Alias

        # UI components structure using real widgets
        class UIComponents:
            def __init__(self, parent):
                self.timeline = parent._create_timeline_components()
                self.status = parent._create_status_components()
                self.toolbar = parent._create_toolbar_components()

        self.ui_components = UIComponents(self)

        # Services mock
        from unittest.mock import MagicMock

        self.services = MagicMock()

        # State
        self.current_file: str | None = None
        self._is_modified: bool = False
        self._current_frame: int = 1
        self.fps: int = 24
        self.playing: bool = False

        # Status bar using real Qt widget
        self.status_bar = QStatusBar()

        # History management (for MainWindowProtocol compatibility)
        self.history: list[object] = []
        self.history_index: int = -1
        self.max_history_size: int = 50

        # Protocol required attributes
        self.selected_indices: list[int] = []
        self.point_name: str = "Point"
        self.point_color: str = "#FF0000"

        # UI component references (required by MainWindowProtocol)
        self.undo_button: object = None  # QPushButton | None
        self.redo_button: object = None  # QPushButton | None
        self.save_button: object = None  # QPushButton | None

        # State manager (required by MainWindowProtocol)
        from unittest.mock import MagicMock

        self.state_manager = MagicMock()
        self.state_manager.is_modified = False
        self.state_manager.auto_center_enabled = True

    @property
    def curve_data(self) -> list[Point4]:
        """Delegate to curve_view's curve_data for MainWindowProtocol compatibility."""
        return self.curve_view.curve_data

    @curve_data.setter
    def curve_data(self, value: list[Point4]) -> None:
        """Set curve_data on curve_view for MainWindowProtocol compatibility."""
        self.curve_view.curve_data = value
        self.curve_view.points = value  # Keep in sync

    @property
    def current_frame(self) -> int:
        """Get the current frame number."""
        return self._current_frame

    @current_frame.setter
    def current_frame(self, value: int) -> None:
        """Set the current frame number."""
        self._current_frame = value

    @property
    def is_modified(self) -> bool:
        """Get modified state."""
        return self._is_modified

    @is_modified.setter
    def is_modified(self, value: bool) -> None:
        """Set modified state."""
        self.state_manager.is_modified = value

    def _create_timeline_components(self):
        """Create timeline UI components using real Qt widgets."""

        class TimelineComponents:
            def __init__(self):
                # Real Qt widgets instead of mocks
                self.frame_slider = QSlider()
                self.frame_slider.setMinimum(1)
                self.frame_slider.setMaximum(100)
                self.frame_slider.setValue(1)

                self.frame_spin = QSpinBox()
                self.frame_spin.setMinimum(1)
                self.frame_spin.setMaximum(100)
                self.frame_spin.setValue(1)

                self.fps_spin = QSpinBox()
                self.fps_spin.setMinimum(1)
                self.fps_spin.setMaximum(120)
                self.fps_spin.setValue(24)

        return TimelineComponents()

    def _create_status_components(self):
        """Create status UI components using real Qt widgets."""

        class StatusComponents:
            def __init__(self):
                # Real Qt widgets instead of mocks
                self.frame_label = QLabel("Frame: 1")
                self.coord_label = QLabel("Coord: (0, 0)")
                self.selection_label = QLabel("Selection: None")

        return StatusComponents()

    def _create_toolbar_components(self):
        """Create toolbar UI components using real Qt widgets."""

        class ToolbarComponents:
            def __init__(self):
                # Real Qt widgets instead of mocks
                self.save_button = QPushButton("Save")
                self.load_button = QPushButton("Load")
                self.export_button = QPushButton("Export")
                self.undo_button = QPushButton("Undo")
                self.redo_button = QPushButton("Redo")

        return ToolbarComponents()

    def update_ui_state(self) -> None:
        """Update UI state for testing."""
        pass

    def get_curve_view(self) -> MockCurveView:
        """Get the curve view component."""
        return self.curve_view

    def show_status_message(self, message: str, timeout: int = 0) -> None:
        """Show message in status bar."""
        if HAS_QT:
            self.status_bar.showMessage(message, timeout)

    def update_status(self, message: str) -> None:
        """Update status message."""
        self.show_status_message(message)

    def add_to_history(self, action: object) -> None:
        """Add action to history."""
        self.history.append(action)
        if len(self.history) > self.max_history_size:
            self.history.pop(0)
        self.history_index = len(self.history) - 1

    def can_undo(self) -> bool:
        """Check if undo is available."""
        return self.history_index >= 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        return self.history_index < len(self.history) - 1


class MockDataBuilder:
    """Builder for creating test data with various configurations."""

    def __init__(self) -> None:
        self.points: list[Point4] = []
        self.frame_start: int = 1
        self.frame_step: int = 1

    def with_points(self, count: int) -> "MockDataBuilder":
        """Add specified number of points."""
        for i in range(count):
            frame = self.frame_start + (i * self.frame_step)
            x = float(i * 100)
            y = float(i * 50)
            self.points.append((frame, x, y, "normal"))
        return self

    def with_keyframes(self, frames: list[int]) -> "MockDataBuilder":
        """Add keyframes at specific frames."""
        for frame in frames:
            x = float(frame * 10)
            y = float(frame * 20)
            self.points.append((frame, x, y, "keyframe"))
        return self

    def with_frame_range(self, start: int, step: int = 1) -> "MockDataBuilder":
        """Set frame start and step."""
        self.frame_start = start
        self.frame_step = step
        return self

    def build(self) -> list[Point4]:
        """Build the final point list."""
        return self.points[:]


class BaseMockCurveView:
    """Basic mock for CurveView with minimal behavior."""

    def __init__(self, **kwargs) -> None:
        from unittest.mock import MagicMock

        # Use MagicMock for most functionality
        self._mock = MagicMock()
        self.curve_data = kwargs.get("curve_data", [])
        self.selected_points = kwargs.get("selected_points", set())


class BaseMockMainWindow:
    """Basic mock for MainWindow with minimal behavior."""

    def __init__(self, **kwargs) -> None:
        from unittest.mock import MagicMock

        # Use MagicMock for most functionality
        self._mock = MagicMock()
        self.curve_data = kwargs.get("curve_data", [])
        self.selected_indices = kwargs.get("selected_indices", [])


class ProtocolCompliantMockCurveView(MockCurveView):
    """Protocol-compliant mock CurveView for service testing."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Additional protocol compliance if needed


class ProtocolCompliantMockMainWindow(MockMainWindow):
    """Protocol-compliant mock MainWindow for service testing."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Additional protocol compliance if needed


class LazyUIMockMainWindow(MockMainWindow):
    """MainWindow mock with lazy UI component creation."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # UI components created on demand
        self._ui_created = False

    def _ensure_ui(self) -> None:
        """Ensure UI components are created."""
        if not self._ui_created:
            # Recreate UI components
            class UIComponents:
                def __init__(self, parent):
                    self.timeline = parent._create_timeline_components()
                    self.status = parent._create_status_components()
                    self.toolbar = parent._create_toolbar_components()

            self.ui_components = UIComponents(self)
            self._ui_created = True

    @property
    def ui(self):
        """Get UI components, creating them if needed."""
        self._ensure_ui()
        return self.ui_components


# ==================== Factory Fixtures ====================


def make_curve_point(frame: int = 1, x: float = 0.0, y: float = 0.0, point_type: str = "keyframe") -> CurvePoint:
    """
    Factory for creating CurvePoint objects.

    Args:
        frame: Frame number
        x: X coordinate
        y: Y coordinate
        point_type: Point type (keyframe/interpolated)

    Returns:
        CurvePoint instance
    """
    return CurvePoint(frame=frame, x=x, y=y, point_type=point_type)


def make_curve_data(num_points: int = 10) -> list:
    """
    Factory for creating test curve data.

    Args:
        num_points: Number of points to create

    Returns:
        List of CurvePoint instances
    """
    return [make_curve_point(frame=i, x=float(i * 10), y=float(i * 20)) for i in range(1, num_points + 1)]


# ==================== Test Utilities ====================


def assert_qt_container_exists(container, name: str = "container"):
    """
    Safely check Qt container exists (not None).

    Qt containers are falsy when empty, so explicit None check is needed.

    Args:
        container: Qt container to check
        name: Container name for error message
    """
    assert container is not None, f"{name} should not be None"


def safe_qt_cleanup(widget):
    """
    Safely cleanup Qt widget avoiding common pitfalls.

    Args:
        widget: Qt widget to cleanup
    """
    if widget is None:
        return

    try:
        if HAS_QT and hasattr(widget, "deleteLater"):
            widget.deleteLater()
    except RuntimeError:
        # Widget already deleted
        pass


def mock_dialog_exec(dialog_class, return_value=True):
    """
    Create a mock for dialog exec() to prevent blocking.

    Args:
        dialog_class: Dialog class to mock
        return_value: Value to return from exec()

    Returns:
        Mock function for monkeypatch
    """

    def mock_exec(self):
        if HAS_QT:
            from PySide6.QtWidgets import QDialog

            return QDialog.DialogCode.Accepted if return_value else QDialog.DialogCode.Rejected
        return 1 if return_value else 0

    return mock_exec


# ==================== Performance Test Helpers ====================


class PerformanceTimer:
    """
    Simple timer for performance testing.

    Usage:
        with PerformanceTimer("operation") as timer:
            # Do operation
            pass
        print(f"Took {timer.elapsed}ms")
    """

    def __init__(self, name: str = "operation"):
        self.name = name
        self.elapsed = 0

    def __enter__(self):
        import time

        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        import time

        self.elapsed = (time.perf_counter() - self.start) * 1000  # Convert to ms


# ==================== Assertion Helpers ====================


def assert_behavior_changed(obj, attribute: str, operation: Callable, expected_before=None, expected_after=None):
    """
    Assert that behavior changes after an operation.

    Tests behavior, not implementation details.

    Args:
        obj: Object to test
        attribute: Attribute to check
        operation: Operation to perform
        expected_before: Expected value before operation
        expected_after: Expected value after operation
    """
    if expected_before is not None:
        actual_before = getattr(obj, attribute)
        assert actual_before == expected_before, f"Before: expected {attribute}={expected_before}, got {actual_before}"

    operation()

    if expected_after is not None:
        actual_after = getattr(obj, attribute)
        assert actual_after == expected_after, f"After: expected {attribute}={expected_after}, got {actual_after}"


# ==================== Export all helpers ====================

__all__ = [
    # Type aliases
    "PointsList",
    "Point3",
    "Point4",
    # Thread-safe image handling
    "ThreadSafeTestImage",
    "TestImagePool",
    # Signal test doubles
    "TestSignal",
    # Test implementation classes
    "MockCurveView",
    "MockMainWindow",
    "MockDataBuilder",
    "BaseMockCurveView",
    "BaseMockMainWindow",
    "ProtocolCompliantMockCurveView",
    "ProtocolCompliantMockMainWindow",
    "LazyUIMockMainWindow",
    # Factories
    "make_curve_point",
    "make_curve_data",
    # Utilities
    "assert_qt_container_exists",
    "safe_qt_cleanup",
    "mock_dialog_exec",
    # Performance
    "PerformanceTimer",
    # Assertions
    "assert_behavior_changed",
    # Constants
    "HAS_QT",
]

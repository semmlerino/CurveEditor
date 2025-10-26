#!/usr/bin/env python3
"""
Unified Test Helpers for CurveEditor

Following best practices from UNIFIED_TESTING_GUIDE_DO_NOT_DELETE.md:
- Real components over mocks
- Thread-safe image handling (QImage instead of QPixmap)
- Proper signal test doubles
- Test behavior, not implementation
"""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

from collections.abc import Callable
from typing import TYPE_CHECKING, Any
from unittest.mock import Mock

from core.models import CurvePoint
from core.type_aliases import CurveDataInput, CurveDataList, LegacyPointData, QtPointF
from tests.qt_test_helpers import ThreadSafeTestImage
from tests.test_utils import safe_cleanup_widget as safe_qt_cleanup

if TYPE_CHECKING:
    from PySide6.QtWidgets import QRubberBand as QtRubberBand
else:
    QtRubberBand = None  # Runtime placeholder

# Qt imports with fallback for non-GUI environments
try:
    from PySide6.QtWidgets import (
        QLabel,
        QPushButton,
        QSlider,
        QSpinBox,
        QStatusBar,
        QWidget,
    )
    from PySide6.QtWidgets import QRubberBand as _QRubberBandRuntime

    _has_qt_internal = True
    if not TYPE_CHECKING:
        QtRubberBand = _QRubberBandRuntime  # Use real class at runtime
except ImportError:
    _has_qt_internal = False

    # Stub classes for non-Qt test environments
    class QObject:
        pass

    class QRubberBand:
        def __init__(self, *args: Any) -> None:
            pass

    if not TYPE_CHECKING:
        QtRubberBand = QRubberBand  # Use stub in non-Qt environment

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

    class _QWidgetStub:
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

    class _QPushButtonStub:
        def __init__(self, *args: Any) -> None:
            pass

    class QAction:
        def __init__(self, *args: Any) -> None:
            pass

    # Type-safe stub assignments
    QWidget = _QWidgetStub
    QPushButton = _QPushButtonStub
    QLabel = QSlider = QSpinBox = QStatusBar = _QWidgetStub

# Export HAS_QT constant (computed once from internal flag)
HAS_QT: bool = _has_qt_internal


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

    Implements SignalProtocol for type-safe testing.
    Signature must exactly match protocols.services.SignalProtocol.
    """

    def __init__(self) -> None:
        self.emissions: list[tuple[object, ...]] = []
        self.callbacks: list[object] = []

    def emit(self, *args: object) -> None:
        """Emit signal with arguments (implements SignalProtocol)."""
        self.emissions.append(args)
        for callback in self.callbacks:
            try:
                # Runtime: we know callback is callable, but static type is object
                # to match SignalProtocol signature (slot: object)
                callback(*args)  # pyright: ignore[reportCallIssue]
            except Exception as e:
                # Log but don't fail on callback errors
                print(f"TestSignal callback error: {e}")

    def connect(self, slot: object) -> object:
        """Connect signal to slot (implements SignalProtocol).

        Note: Signature matches protocols.services.SignalProtocol exactly (slot: object).
        """
        self.callbacks.append(slot)
        return slot  # Return connection object (slot itself)

    def disconnect(self, slot: object | None = None) -> None:
        """Disconnect signal from slot (implements SignalProtocol).

        Note: Signature matches protocols.services.SignalProtocol exactly (slot: object | None).
        """
        if slot is not None and slot in self.callbacks:
            self.callbacks.remove(slot)

    @property
    def was_emitted(self) -> bool:
        """Check if signal was emitted at least once."""
        return len(self.emissions) > 0

    @property
    def emit_count(self) -> int:
        """Get number of times signal was emitted."""
        return len(self.emissions)

    @property
    def last_emission(self) -> tuple[object, ...] | None:
        """Get last emission arguments."""
        return self.emissions[-1] if self.emissions else None

    def reset(self) -> None:
        """Clear all emissions for reuse."""
        self.emissions.clear()

    def receivers(self) -> int:
        """Return the number of connected receivers (Qt-like interface).

        Used for testing signal connection verification.
        """
        return len(self.callbacks)


# ==================== Qt Component Test Doubles ====================


class MockStateManager:
    """Mock StateManager with TestSignal attributes for proper signal testing."""

    def __init__(self):
        from unittest.mock import MagicMock

        self.is_modified = False
        self.auto_center_enabled = True
        self.current_frame = 1
        self.zoom_level = 1.0  # Default zoom
        self.pan_offset = (0.0, 0.0)  # Default pan
        # History state
        self._history_position = 0
        self._history_size = 0
        # Signals for testing
        self.file_changed = TestSignal()
        self.modified_changed = TestSignal()
        self.selection_changed = TestSignal()
        self.view_state_changed = TestSignal()
        self.total_frames_changed = TestSignal()
        self.undo_state_changed = TestSignal()
        self.redo_state_changed = TestSignal()
        # Mock reset_to_defaults for testing
        self.reset_to_defaults = MagicMock(side_effect=self._reset_to_defaults)

    def _reset_to_defaults(self) -> None:
        """Reset state to default values."""
        self.is_modified = False
        self.auto_center_enabled = True
        self.current_frame = 1
        self.zoom_level = 1.0
        self.pan_offset = (0.0, 0.0)

    def set_history_state(self, can_undo: bool, can_redo: bool, position: int = 0, size: int = 0) -> None:
        """Update history state information.

        Args:
            can_undo: Whether undo is available
            can_redo: Whether redo is available
            position: Current position in history (optional)
            size: Total history size (optional)
        """
        self._history_position = position
        self._history_size = size
        # Emit signals if needed (for test verification)
        self.undo_state_changed.emit(can_undo)
        self.redo_state_changed.emit(can_redo)


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

    def __init__(self, curve_data: CurveDataList | None = None, **kwargs: Any) -> None:
        # Real data structures - preserve original format
        if curve_data is not None:
            self.curve_data: CurveDataList = list(curve_data)
        else:
            self.curve_data = []
        self.points: CurveDataList = self.curve_data  # Alias for service compatibility
        self.selected_points: set[int] = set()
        self.selected_point_idx: int = -1
        self.current_image_idx: int = 0

        # MultiCurveViewProtocol required attributes
        self.active_curve_name: str | None = None
        self.curves_data: dict[str, CurveDataList] = {}
        self.selected_curve_names: set[str] = set()
        self.selected_curves_ordered: list[str] = []

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
        self.last_drag_pos: QtPointF | None = None
        self.last_pan_pos: QtPointF | None = None

        # Rubber band selection attributes (required by CurveViewProtocol)
        self.rubber_band: QtRubberBand | None = None
        self.rubber_band_active: bool = False
        # Create a dummy origin point - protocol requires non-None QtPointF
        if TYPE_CHECKING:
            self.rubber_band_origin: QtPointF
        else:
            try:
                from PySide6.QtCore import QPointF

                self.rubber_band_origin = QPointF(0.0, 0.0)
            except ImportError:
                # Fallback for non-Qt environments - use object
                self.rubber_band_origin = object()

        # Display settings
        self.show_background: bool = True
        # Visual settings (deprecated on real widget, exist in visual)
        # Keep them here for backward compatibility with old protocol tests
        self.show_grid: bool = False
        self.show_points: bool = True
        self.show_lines: bool = True
        self.show_velocity_vectors: bool = False
        self.show_all_frame_numbers: bool = False
        self.flip_y_axis: bool = False
        self.scale_to_image: bool = True

        # Rendering settings (deprecated on real widget, exist in visual)
        # Keep them here for backward compatibility with old protocol tests
        self.point_radius: int = 5
        self.selected_point_radius: int = 7
        self.line_width: int = 2
        self.selected_line_width: int = 3

        # Image properties
        self.image_width: int = 1920
        self.image_height: int = 1080
        # Type needs to match protocol exactly for invariant attribute
        if TYPE_CHECKING:
            from PySide6.QtGui import QPixmap

            self.background_image: QPixmap | None = None
        else:
            self.background_image: object = None

        # Image sequence properties
        self.image_sequence_path: str = ""
        self.image_filenames: list[str] = []

        # Transform (for spatial index tests)
        self.transform: object = None  # Transform object - set by tests

        # Protocol required attributes
        # Type needs to match protocol exactly for invariant attribute
        # Use cast via object to satisfy type checker while keeping None at runtime for tests
        from typing import cast

        if TYPE_CHECKING:
            from protocols.ui import MainWindowProtocol

            # Type checker sees MainWindowProtocol (required by protocol)
            # But at runtime it's None (fine for tests)
            self.main_window: MainWindowProtocol = cast("MainWindowProtocol", cast(object, None))
        else:
            self.main_window: object = None
        # TestSignal now properly implements SignalProtocol
        # Cast needed because instance attributes are invariant in Python's type system
        from typing import cast

        from protocols.services import SignalProtocol

        self.point_selected: SignalProtocol = cast(SignalProtocol, TestSignal())
        self.point_moved: SignalProtocol = cast(SignalProtocol, TestSignal())
        self.selection_changed: SignalProtocol = cast(SignalProtocol, TestSignal())
        self.zoom_changed: SignalProtocol = cast(SignalProtocol, TestSignal())
        self.view_changed: SignalProtocol = cast(SignalProtocol, TestSignal())

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

    def set_curve_data(self, data: CurveDataInput) -> None:
        """Set the curve data."""
        self.curve_data = list(data)
        self.points = self.curve_data  # Keep in sync

    def add_point(self, point: LegacyPointData) -> None:
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
            new_point = (old_point[0], x, y, old_point[3]) if len(old_point) >= 4 else (old_point[0], x, y)
            self.curve_data[index] = new_point
            self.points[index] = new_point

    def select_point(self, point_index: int, add_to_selection: bool = False, curve_name: str | None = None) -> None:
        """Select a point by index (matches MultiCurveViewProtocol signature)."""
        if 0 <= point_index < len(self.curve_data):
            if not add_to_selection:
                self.selected_points.clear()
            self.selected_points.add(point_index)
            self.selected_point_idx = point_index

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

    def get_display_size(self) -> tuple[int, int]:
        """Get display dimensions for transform calculations."""
        return (self.image_width, self.image_height)

    def _get_display_dimensions(self) -> tuple[int, int]:
        """Get display dimensions (private method used by ViewCameraController)."""
        return (self.image_width, self.image_height)

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

    def findPointAt(self, pos: QtPointF) -> int:
        """Find point near given coordinates."""
        # Extract x, y from QtPointF (supports both QPoint and QPointF)
        if hasattr(pos, "x") and hasattr(pos, "y"):
            x = pos.x() if callable(pos.x) else pos.x
            y = pos.y() if callable(pos.y) else pos.y
        else:
            # Fallback for tuple-like objects
            x, y = float(pos[0]), float(pos[1])  # pyright: ignore[reportIndexIssue]

        tolerance = 5.0
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
        """Reset view to default zoom and pan.

        This mirrors CurveViewWidget.reset_view() which resets zoom_factor,
        pan_offset, and emits signals to notify MainWindow. Also calls update()
        for compatibility with InteractionService tests.
        """
        # Reset zoom and pan to defaults
        self.zoom_factor = 1.0
        self.pan_offset = (0.0, 0.0)
        self.manual_offset_x = 0.0
        self.manual_offset_y = 0.0

        # Also reset legacy offset attributes for old tests
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.x_offset = 0.0
        self.y_offset = 0.0

        # Invalidate caches and update
        self._invalidate_caches()
        self.update()

        # Emit signals (MainWindow listens to zoom_changed)
        self.zoom_changed.emit(self.zoom_factor)
        self.view_changed.emit()

    def reset_transform(self) -> None:
        """Reset transform (delegates to reset_view for InteractionService compatibility)."""
        self.reset_view()

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

    def unsetCursor(self) -> None:
        """Mock unsetCursor method."""

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

    def invalidate_caches(self) -> None:
        """Public wrapper for invalidating caches (called by controllers)."""
        self._invalidate_caches()

    @property
    def pan_offset(self) -> tuple[float, float]:
        """Get pan offset as tuple (matches production ViewCameraController pattern)."""
        return (self.pan_offset_x, self.pan_offset_y)

    @pan_offset.setter
    def pan_offset(self, value: tuple[float, float]) -> None:
        """Set pan offset from tuple (matches production ViewCameraController pattern)."""
        self.pan_offset_x, self.pan_offset_y = value

    def toggleBackgroundVisible(self, visible: bool) -> None:
        """Toggle background visibility."""
        self.show_background = visible

    def toggle_point_interpolation(self, idx: int) -> None:
        """Toggle interpolation status of a point."""

    def setPoints(self, data: CurveDataList, width: int, height: int) -> None:
        """Set points with image dimensions (legacy compatibility)."""
        self.set_curve_data(data)
        self.image_width = width
        self.image_height = height

    def set_selected_indices(self, indices: list[int]) -> None:
        """Set the selected point indices."""
        self.selected_points = set(indices)

    def selectPointByIndex(self, idx: int) -> bool:
        """Select a point by its index."""
        if 0 <= idx < len(self.curve_data):
            self.selected_points.add(idx)
            self.selected_point_idx = idx
            return True
        return False

    def get_point_data(self, idx: int) -> tuple[int, float, float, str | None]:
        """Get point data for the given index."""
        if 0 <= idx < len(self.curve_data):
            point = self.curve_data[idx]
            if len(point) >= 4:
                return (point[0], point[1], point[2], str(point[3]))
            else:
                return (point[0], point[1], point[2], None)
        return (0, 0.0, 0.0, None)

    def setup_for_3dequalizer_data(self) -> None:
        """Set up the view for 3DEqualizer coordinate tracking data."""
        self.flip_y_axis = True
        self.scale_to_image = True

    def setup_for_pixel_tracking(self) -> None:
        """Set up the view for screen/pixel-coordinate tracking data."""
        self.flip_y_axis = False
        self.scale_to_image = False

    # MultiCurveViewProtocol stub methods
    def set_curves_data(
        self,
        curves: dict[str, CurveDataList],
        metadata: dict[str, dict[str, object]] | None = None,
        active_curve: str | None = None,
        selected_curves: list[str] | None = None,
    ) -> None:
        """Set multiple curves with optional metadata (stub for testing)."""
        self.curves_data = curves
        if active_curve:
            self.active_curve_name = active_curve
        if selected_curves:
            self.selected_curve_names = set(selected_curves)
            self.selected_curves_ordered = selected_curves

    def add_curve(self, name: str, data: CurveDataList, metadata: dict[str, object] | None = None) -> None:
        """Add a single curve to the view (stub for testing)."""
        self.curves_data[name] = data

    def remove_curve(self, name: str) -> None:
        """Remove a curve from the view (stub for testing)."""
        if name in self.curves_data:
            del self.curves_data[name]

    def set_active_curve(self, name: str) -> None:
        """Set the active curve for editing (stub for testing)."""
        self.active_curve_name = name

    def set_selected_curves(self, curve_names: list[str]) -> None:
        """Set the selected curves (stub for testing)."""
        self.selected_curve_names = set(curve_names)
        self.selected_curves_ordered = curve_names

    def update_curve_visibility(self, curve_name: str, visible: bool) -> None:
        """Update visibility of a specific curve (stub for testing)."""

    def update_curve_color(self, curve_name: str, color: tuple[int, int, int]) -> None:
        """Update color of a specific curve (stub for testing)."""

    def get_curve_metadata(self, curve_name: str) -> dict[str, object]:
        """Get metadata for a specific curve (stub for testing)."""
        return {}

    def center_on_selected_curves(self) -> None:
        """Center the view on all selected curves (stub for testing)."""


class MockMainWindow:
    """Lightweight real MainWindow implementation for testing.

    Implements MainWindowProtocol to avoid type ignores in tests.
    """

    def __init__(self) -> None:
        from typing import TYPE_CHECKING

        if TYPE_CHECKING:
            from protocols.ui import MultiCurveViewProtocol

        # Core components
        self.curve_view = MockCurveView()
        # curve_widget must be typed as MultiCurveViewProtocol | None for protocol compliance
        # MockCurveView is compatible with MultiCurveViewProtocol at runtime
        self.curve_widget: MultiCurveViewProtocol | None = self.curve_view

        # UI components structure using real widgets
        class UIComponents:
            def __init__(self, parent):
                self.timeline = parent._create_timeline_components()
                self.status = parent._create_status_components()
                self.toolbar = parent._create_toolbar_components()

        self.ui_components = UIComponents(self)

        # Services mock
        from unittest.mock import MagicMock

        self._services = MagicMock()

        # State
        self.current_file: str | None = None
        self._is_modified: bool = False
        self._current_frame: int = 1
        self.fps: int = 24
        self.playing: bool = False

        # Status bar using real Qt widget
        self.status_bar = QStatusBar()

        # History management (for MainWindowProtocol compatibility)
        # Optional to allow tests to force internal history usage
        self.history: list[object] | None = []
        self.history_index: int | None = -1
        self.max_history_size: int = 50

        # Protocol required attributes
        self._selected_indices: list[int] = []
        self.point_name: str = "Point"
        self.point_color: str = "#FF0000"

        # UI component references (required by MainWindowProtocol)
        self.undo_button: object = None  # QPushButton | None
        self.redo_button: object = None  # QPushButton | None
        self.save_button: object = None  # QPushButton | None

        # State manager (required by MainWindowProtocol)
        # Use module-level MockStateManager with TestSignal attributes for proper signal testing
        self._state_manager = MockStateManager()

        # Additional MainWindowProtocol required attributes
        self._point_spinbox_connected: bool = False
        self.file_operations: object = MagicMock()
        self.fps_spinbox: object = None
        self.btn_play_pause: object = None
        self.timeline_tabs: object = None
        self.shortcut_manager: object = None
        self.multi_point_controller: object = None

        # More protocol attributes
        self.tracking_panel: object = None
        self.frame_spinbox: object = None
        self.frame_slider: object = None
        self.image_filenames: list[str] = []
        self.file_load_worker: object = None
        self.total_frames_label: object = None
        self.tracked_data: object = None
        self.active_points: object = None
        self.active_timeline_point: str | None = None
        self.current_image_idx: int = 0
        self.session_manager: object = None
        self.view_update_manager: object = None

        # Controller references (needed by some controllers)
        self.view_management_controller: object = MagicMock()
        self.timeline_controller: object = MagicMock()
        self.frame_change_coordinator: object = MagicMock()

        # UI label widgets
        self.zoom_label: object = MagicMock()
        self.status_label: object = MagicMock()

        # Point editor spinbox widgets
        if HAS_QT:
            from PySide6.QtWidgets import QDoubleSpinBox, QLabel

            self.point_x_spinbox = QDoubleSpinBox()
            self.point_x_spinbox.setMinimum(-99999.0)
            self.point_x_spinbox.setMaximum(99999.0)
            self.point_x_spinbox.setValue(0.0)

            self.point_y_spinbox = QDoubleSpinBox()
            self.point_y_spinbox.setMinimum(-99999.0)
            self.point_y_spinbox.setMaximum(99999.0)
            self.point_y_spinbox.setValue(0.0)

            self.selected_point_label = QLabel("No point selected")
            self.selected_count_label = QLabel("Selected: 0")
        else:
            # Fallback for non-Qt environments
            self.point_x_spinbox = MagicMock()
            self.point_y_spinbox = MagicMock()
            self.selected_point_label = MagicMock()
            self.selected_count_label = MagicMock()

        # UI checkbox widgets
        self.show_background_cb: object = MagicMock()
        self.show_grid_cb: object = MagicMock()
        self.show_info_cb: object = MagicMock()
        self.show_tooltips_cb: object = MagicMock()
        self.point_size_slider: object = MagicMock()
        self.line_width_slider: object = MagicMock()

        # Connect zoom_changed signal to sync state_manager (matches production)
        # Production: SignalConnectionManager connects zoom_changed → MainWindow.on_curve_zoom_changed
        # This ensures state_manager.zoom_level stays in sync with curve_widget.zoom_factor
        self.curve_view.zoom_changed.connect(self.on_curve_zoom_changed)

        # Connect view_changed signal to sync pan_offset (exposes production bug)
        # Production connects view_changed but only updates zoom display, not pan_offset
        # This test implementation properly syncs pan_offset for session save/restore
        self.curve_view.view_changed.connect(self.on_curve_view_changed)

    @property
    def selected_indices(self) -> list[int]:
        """Get selected point indices (MainWindowProtocol)."""
        return self._selected_indices

    @selected_indices.setter
    def selected_indices(self, value: list[int]) -> None:
        """Set selected point indices (MainWindowProtocol)."""
        self._selected_indices = value

    @property
    def curve_data(self) -> CurveDataList:
        """Delegate to curve_view's curve_data for MainWindowProtocol compatibility."""
        return self.curve_view.curve_data

    @curve_data.setter
    def curve_data(self, value: CurveDataList) -> None:
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
        self._state_manager.current_frame = value

    @property
    def is_modified(self) -> bool:
        """Get modified state."""
        return self._is_modified

    @is_modified.setter
    def is_modified(self, value: bool) -> None:
        """Set modified state."""
        self._is_modified = value
        self._state_manager.is_modified = value

    @property
    def services(self) -> object:
        """Get services facade (MainWindowProtocol)."""
        return self._services

    @property
    def state_manager(self) -> MockStateManager:
        """Get state manager (MainWindowProtocol)."""
        return self._state_manager

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

    def setWindowTitle(self, title: str) -> None:
        """Set window title (MainWindowProtocol)."""
        # Mock implementation

    def statusBar(self) -> object:
        """Get status bar widget (MainWindowProtocol)."""
        return self.status_bar

    def close(self) -> bool:
        """Close the window (MainWindowProtocol)."""
        return True

    def set_centering_enabled(self, enabled: bool) -> None:
        """Enable or disable auto-centering (MainWindowProtocol)."""
        if self._state_manager:
            self._state_manager.auto_center_enabled = enabled

    def apply_smooth_operation(self) -> None:
        """Apply smoothing operation (MainWindowProtocol)."""
        # Mock implementation

    def update_point_status_label(self) -> None:
        """Update point status label (MainWindowProtocol)."""
        # Mock implementation

    def _get_current_frame(self) -> int:
        """Get current frame (controller friend method)."""
        return self._current_frame

    def _set_current_frame(self, frame: int) -> None:
        """Set current frame (controller friend method)."""
        self._current_frame = frame
        self._state_manager.current_frame = frame

    def update_timeline_tabs(self, curve_data: object | None) -> None:
        """Update timeline tabs (MainWindowProtocol)."""
        # Mock implementation

    def update_tracking_panel(self) -> None:
        """Update tracking panel (MainWindowProtocol)."""
        # Mock implementation

    def update_zoom_label(self) -> None:
        """Update zoom level label (MainWindowProtocol)."""
        # Mock implementation

    def _update_point_status_label(self) -> None:
        """Update point status label (needed by FrameChangeCoordinator)."""
        # Mock implementation

    def on_curve_zoom_changed(self, zoom: float) -> None:
        """Handle zoom changes from curve widget (syncs state_manager).

        This mirrors MainWindow.on_curve_zoom_changed() which keeps
        state_manager.zoom_level in sync with curve_widget.zoom_factor.
        """
        self._state_manager.zoom_level = zoom

    def on_curve_view_changed(self) -> None:
        """Handle view changes from curve widget (syncs pan_offset to state_manager).

        This mirrors MainWindow.on_curve_view_changed(). Production only updates
        zoom display, but should also sync pan_offset for session save/restore.
        This test implementation exposes the missing pan_offset sync in production.
        """
        # Sync pan_offset from curve_widget to state_manager
        if self.curve_widget:
            self._state_manager.pan_offset = self.curve_widget.pan_offset

    def _get_current_curve_data(self) -> CurveDataList:
        """Get current curve data (controller friend method)."""
        return self.curve_view.curve_data

    def restore_state(self, state: dict[str, object]) -> None:
        """Restore state from history (MainWindowProtocol)."""
        # Mock implementation - tests may override

    def add_to_history(self, action: object | None = None) -> None:
        """Add action to history (MainWindowProtocol)."""
        if self.history is not None:
            self.history.append(action)
            if len(self.history) > self.max_history_size:
                self.history.pop(0)
            self.history_index = len(self.history) - 1

    def can_undo(self) -> bool:
        """Check if undo is available."""
        if self.history_index is None:
            return False
        return self.history_index >= 0

    def can_redo(self) -> bool:
        """Check if redo is available."""
        if self.history is None or self.history_index is None:
            return False
        return self.history_index < len(self.history) - 1

    def set_tracked_data_atomic(self, data: object) -> None:
        """Set tracked data atomically (MainWindowProtocol)."""
        self.tracked_data = data

    def geometry(self) -> object:
        """Get window geometry (MainWindowProtocol)."""
        return None

    def set_file_loading_state(self, loading: bool) -> None:
        """Set file loading state (MainWindowProtocol)."""

    # Signal protocol attributes
    @property
    def play_toggled(self) -> object:
        """Play toggled signal (MainWindowProtocol)."""
        return TestSignal()

    @property
    def frame_rate_changed(self) -> object:
        """Frame rate changed signal (MainWindowProtocol)."""
        return TestSignal()

    # Signal handler methods for SignalConnectionManager
    def on_tracking_data_loaded(self, data: object) -> None:
        """Handle tracking data loaded signal (MainWindowProtocol)."""

    def on_multi_point_data_loaded(self, data: object) -> None:
        """Handle multi-point data loaded signal (MainWindowProtocol)."""

    def on_file_load_progress(self, progress: int) -> None:
        """Handle file load progress signal (MainWindowProtocol)."""

    def on_file_load_error(self, error: str) -> None:
        """Handle file load error signal (MainWindowProtocol)."""

    def on_file_load_finished(self) -> None:
        """Handle file load finished signal (MainWindowProtocol)."""

    def on_file_loaded(self, filepath: str) -> None:
        """Handle file loaded signal (MainWindowProtocol)."""

    def on_file_saved(self, filepath: str) -> None:
        """Handle file saved signal (MainWindowProtocol)."""

    def on_file_changed(self, filepath: str) -> None:
        """Handle file changed signal (MainWindowProtocol)."""

    def on_modified_changed(self, is_modified: bool) -> None:
        """Handle modified state changed signal (MainWindowProtocol)."""

    def on_selection_changed(self, indices: object) -> None:
        """Handle selection changed signal (MainWindowProtocol)."""

    def on_view_state_changed(self) -> None:
        """Handle view state changed signal (MainWindowProtocol)."""

    def on_point_selected(self, index: int) -> None:
        """Handle point selected signal (MainWindowProtocol)."""

    def on_point_moved(self, index: int, x: float, y: float) -> None:
        """Handle point moved signal (MainWindowProtocol)."""

    def on_curve_selection_changed(self, indices: object) -> None:
        """Handle curve selection changed signal (MainWindowProtocol)."""


class MockDataBuilder:
    """Builder for creating test data with various configurations."""

    def __init__(self) -> None:
        self.points: CurveDataList = []
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

    def build(self) -> CurveDataList:
        """Build the final point list."""
        return self.points[:]


class BaseMockCurveView:
    """Basic mock for CurveView with minimal behavior."""

    def __init__(self, **kwargs: Any) -> None:
        from unittest.mock import MagicMock

        # Use MagicMock for most functionality
        self._mock = MagicMock()
        self.curve_data: CurveDataList = kwargs.get("curve_data", [])
        self.selected_points: set[int] = kwargs.get("selected_points", set())


class BaseMockMainWindow:
    """Basic mock for MainWindow with minimal behavior."""

    def __init__(self, **kwargs: Any) -> None:
        from unittest.mock import MagicMock

        # Use MagicMock for most functionality
        self._mock = MagicMock()
        self.curve_data: CurveDataList = kwargs.get("curve_data", [])
        self.selected_indices: list[int] = kwargs.get("selected_indices", [])


class ProtocolCompliantMockCurveView(MockCurveView):
    """Protocol-compliant mock CurveView for service testing."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Additional protocol compliance if needed


class ProtocolCompliantMockMainWindow(MockMainWindow):
    """Protocol-compliant mock MainWindow for service testing."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Additional protocol compliance if needed


class LazyUIMockMainWindow(MockMainWindow):
    """MainWindow mock with lazy UI component creation."""

    def __init__(self, **kwargs: Any) -> None:
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


def make_curve_point(frame: int = 1, x: float = 0.0, y: float = 0.0, status: str = "keyframe") -> CurvePoint:
    """
    Factory for creating CurvePoint objects.

    Args:
        frame: Frame number
        x: X coordinate
        y: Y coordinate
        status: Point status (keyframe/interpolated/normal)

    Returns:
        CurvePoint instance
    """
    from core.models import PointStatus

    # Convert string status to PointStatus enum
    status_map = {
        "keyframe": PointStatus.KEYFRAME,
        "interpolated": PointStatus.INTERPOLATED,
        "normal": PointStatus.NORMAL,
        "tracked": PointStatus.TRACKED,
        "endframe": PointStatus.ENDFRAME,
    }
    point_status = status_map.get(status.lower(), PointStatus.NORMAL)

    return CurvePoint(frame=frame, x=x, y=y, status=point_status)


def make_curve_data(num_points: int = 10) -> list[CurvePoint]:
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


# safe_qt_cleanup is now imported at the top of the file


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
        self.start: float = 0.0

    def __enter__(self):
        import time

        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        import time

        self.elapsed = (time.perf_counter() - self.start) * 1000  # Convert to ms


# ==================== Assertion Helpers ====================


def assert_behavior_changed(
    obj: object,
    attribute: str,
    operation: Callable[..., Any],
    expected_before: object = None,
    expected_after: object = None,
) -> None:
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


def set_test_selection(widget: object, indices: set[int] | list[int]) -> None:
    """Helper to set selection in Phase 6+ compatible way.

    This helper function provides a migration path for tests during Phase 6.
    During Phase 6.1-6.2, it syncs to both CurveDataStore and ApplicationState
    (matching the widget setter behavior). After Phase 6.3, only ApplicationState
    will be used.

    Args:
        widget: Widget (may need CurveDataStore sync until Phase 6.3)
        indices: Point indices to select

    Usage:
        # OLD: widget.selected_indices = {0, 1, 2}
        # NEW: set_test_selection(widget, {0, 1, 2})
    """
    from stores.application_state import get_application_state

    # Convert list to set if needed
    indices_set = set(indices) if isinstance(indices, list) else indices

    # Sync to ApplicationState
    app_state = get_application_state()
    active_curve = app_state.active_curve
    if active_curve:
        app_state.set_selection(active_curve, indices_set)

    # Sync to CurveDataStore (until Phase 6.3 removal)
    # Check if widget has _curve_store attribute (real CurveViewWidget)
    if hasattr(widget, "_curve_store"):
        curve_store = widget._curve_store
        if not indices_set:
            curve_store.clear_selection()
        else:
            curve_store.clear_selection()
            for idx in indices_set:
                curve_store.select(idx, add_to_selection=True)


def create_test_render_state(
    *,
    points: CurveDataList,
    current_frame: int = 1,
    selected_points: set[int] | None = None,
    widget_width: int = 800,
    widget_height: int = 600,
    zoom_factor: float = 1.0,
    pan_offset_x: float = 0.0,
    pan_offset_y: float = 0.0,
    manual_offset_x: float = 0.0,
    manual_offset_y: float = 0.0,
    flip_y_axis: bool = False,
    show_background: bool = False,
    background_image: Any = None,
    image_width: int = 800,
    image_height: int = 600,
    show_grid: bool = False,
    point_radius: int = 5,
    line_width: int = 2,
    **kwargs: Any,
) -> Any:  # RenderState type to avoid import cycle
    """Create RenderState with VisualSettings for tests (Phase 2).

    This helper wraps the RenderState constructor to handle the transition
    from individual visual parameters (show_grid, point_radius, line_width)
    to the consolidated VisualSettings object.

    Args:
        points: Curve data points
        current_frame: Current frame number
        selected_points: Set of selected point indices
        widget_width: Widget width in pixels
        widget_height: Widget height in pixels
        zoom_factor: Zoom factor
        pan_offset_x: Pan offset X
        pan_offset_y: Pan offset Y
        manual_offset_x: Manual offset X
        manual_offset_y: Manual offset Y
        flip_y_axis: Whether to flip Y axis
        show_background: Whether to show background image
        background_image: Background image
        image_width: Image width
        image_height: Image height
        show_grid: Whether to show grid (visual setting)
        point_radius: Point radius (visual setting)
        line_width: Line width (visual setting)
        **kwargs: Additional RenderState arguments

    Returns:
        RenderState instance with visual settings properly configured
    """
    from rendering.render_state import RenderState
    from rendering.visual_settings import VisualSettings

    # Create visual settings from individual parameters
    visual = VisualSettings(
        show_grid=show_grid,
        point_radius=point_radius,
        line_width=line_width,
    )

    return RenderState(
        points=points,
        current_frame=current_frame,
        selected_points=selected_points or set(),
        widget_width=widget_width,
        widget_height=widget_height,
        zoom_factor=zoom_factor,
        pan_offset_x=pan_offset_x,
        pan_offset_y=pan_offset_y,
        manual_offset_x=manual_offset_x,
        manual_offset_y=manual_offset_y,
        flip_y_axis=flip_y_axis,
        show_background=show_background,
        background_image=background_image,
        image_width=image_width,
        image_height=image_height,
        visual=visual,
        **kwargs,
    )


# ==================== Export all helpers ====================

__all__ = [
    "HAS_QT",
    "BaseMockCurveView",
    "BaseMockMainWindow",
    "LazyUIMockMainWindow",
    "MockCurveView",
    "MockDataBuilder",
    "MockMainWindow",
    "PerformanceTimer",
    "Point3",
    "Point4",
    "PointsList",
    "ProtocolCompliantMockCurveView",
    "ProtocolCompliantMockMainWindow",
    "TestImagePool",
    "TestSignal",
    "ThreadSafeTestImage",
    "assert_behavior_changed",
    "assert_qt_container_exists",
    "create_test_render_state",
    "make_curve_data",
    "make_curve_point",
    "mock_dialog_exec",
    "safe_qt_cleanup",
    "set_test_selection",
]

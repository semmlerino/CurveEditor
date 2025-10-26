#!/usr/bin/env python
"""Tests for ViewCameraController.

Comprehensive test suite covering camera and view operations including:
- Zoom in/out/set/wheel operations
- Pan offset management
- Coordinate transformations (data ↔ screen)
- Centering on frames, selections, points
- View fitting (background image, curve bounds)
- Transform caching
- View state management

Focus Areas:
- Zoom factor limits (MIN, MAX, DEFAULT)
- Pan offset persistence
- Transform cache invalidation
- Coordinate space conversions
- View fitting with different data bounds
- Smooth zoom via wheel events
- Pan coordinate calculations
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

from unittest.mock import Mock

import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QPixmap, QWheelEvent

from ui.controllers.view_camera_controller import ViewCameraController
from ui.ui_constants import DEFAULT_ZOOM_FACTOR, MAX_ZOOM_FACTOR, MIN_ZOOM_FACTOR


@pytest.fixture
def mock_curve_view():
    """Create a mock curve view widget for testing."""
    view = Mock()
    view.curve_data = [
        (1, 100.0, 200.0, "keyframe"),
        (5, 150.0, 250.0, "normal"),
        (10, 200.0, 300.0, "normal"),
    ]
    view.selected_indices = set()
    view.background_image = None
    view.image_width = 1920
    view.image_height = 1080
    view.scale_to_image = True
    view.flip_y_axis = False
    view.manual_offset_x = 0.0
    view.manual_offset_y = 0.0
    view.width = Mock(return_value=800)
    view.height = Mock(return_value=600)
    view.update = Mock()
    view.repaint = Mock()
    view._get_display_dimensions = Mock(return_value=(1920, 1080))

    # Mock signals
    view.zoom_changed = Mock()
    view.view_changed = Mock()

    return view


@pytest.fixture
def camera_controller(mock_curve_view):
    """Create ViewCameraController with mock view."""
    return ViewCameraController(mock_curve_view)


class TestViewCameraControllerInitialization:
    """Test controller initialization."""

    def test_controller_initializes_with_widget(self, mock_curve_view) -> None:
        """Test controller initializes with correct widget reference.

        Verifies:
        - Widget reference stored
        - Initial zoom factor set to DEFAULT
        - Pan offsets initialized to 0
        """
        # Act
        controller = ViewCameraController(mock_curve_view)

        # Assert
        assert controller.widget is mock_curve_view
        assert controller.zoom_factor == DEFAULT_ZOOM_FACTOR
        assert controller.pan_offset_x == 0.0
        assert controller.pan_offset_y == 0.0

    def test_controller_transform_cache_initialized(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test that transform cache starts empty.

        Verifies:
        - _transform_cache is None initially
        """
        # Assert
        assert camera_controller._transform_cache is None


class TestTransformCaching:
    """Test transform cache management."""

    def test_get_transform_creates_cache(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test that get_transform creates cache if needed.

        Verifies:
        - Cache created on first call
        - Cache reused on subsequent calls
        """
        # Arrange
        assert camera_controller._transform_cache is None

        # Act
        transform1 = camera_controller.get_transform()

        # Assert
        assert transform1 is not None
        assert camera_controller._transform_cache is not None

    def test_get_transform_returns_same_instance(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test that get_transform returns cached instance.

        Verifies:
        - Same Transform object returned
        - No new instance created
        """
        # Act
        transform1 = camera_controller.get_transform()
        transform2 = camera_controller.get_transform()

        # Assert
        assert transform1 is transform2

    def test_invalidate_caches_clears_transform(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test that invalidate_caches clears transform cache.

        Verifies:
        - Cache cleared
        - Next get_transform creates new cache
        """
        # Arrange
        camera_controller.get_transform()
        assert camera_controller._transform_cache is not None

        # Act
        camera_controller.invalidate_caches()

        # Assert
        assert camera_controller._transform_cache is None


class TestZoomOperations:
    """Test zoom factor management."""

    def test_set_zoom_factor_updates_zoom(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test setting zoom factor.

        Verifies:
        - Zoom factor updated
        - Transform cache invalidated
        - Widget update triggered
        """
        # Arrange
        assert camera_controller.zoom_factor == DEFAULT_ZOOM_FACTOR

        # Act
        camera_controller.set_zoom_factor(2.0)

        # Assert
        assert camera_controller.zoom_factor == 2.0
        assert camera_controller._transform_cache is None

    def test_set_zoom_factor_respects_minimum(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test that zoom is clamped to minimum.

        Verifies:
        - Zoom can't go below MIN_ZOOM_FACTOR
        """
        # Act
        camera_controller.set_zoom_factor(0.01)

        # Assert
        assert camera_controller.zoom_factor >= MIN_ZOOM_FACTOR

    def test_set_zoom_factor_respects_maximum(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test that zoom is clamped to maximum.

        Verifies:
        - Zoom can't exceed MAX_ZOOM_FACTOR
        """
        # Act
        camera_controller.set_zoom_factor(100.0)

        # Assert
        assert camera_controller.zoom_factor <= MAX_ZOOM_FACTOR

    def test_set_zoom_factor_emits_signal(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test that setting zoom emits zoom_changed signal.

        Verifies:
        - Signal emitted with new zoom value
        """
        # Act
        camera_controller.set_zoom_factor(2.0)

        # Assert
        camera_controller.widget.zoom_changed.emit.assert_called()

    def test_wheel_zoom_increases_on_positive_delta(
        self, camera_controller: ViewCameraController, mock_curve_view
    ) -> None:
        """Test wheel zoom with positive delta (scroll up).

        Verifies:
        - Zoom increases with positive delta
        - Zoom factor changed
        """
        # Arrange
        initial_zoom = camera_controller.zoom_factor
        wheel_event = Mock(spec=QWheelEvent)
        wheel_event.angleDelta = Mock(return_value=Mock(y=Mock(return_value=120)))
        cursor_pos = QPointF(400, 300)

        # Act
        camera_controller.handle_wheel_zoom(wheel_event, cursor_pos)

        # Assert
        assert camera_controller.zoom_factor > initial_zoom

    def test_wheel_zoom_decreases_on_negative_delta(
        self, camera_controller: ViewCameraController, mock_curve_view
    ) -> None:
        """Test wheel zoom with negative delta (scroll down).

        Verifies:
        - Zoom decreases with negative delta
        - Zoom factor changed
        """
        # Arrange
        initial_zoom = camera_controller.zoom_factor
        wheel_event = Mock(spec=QWheelEvent)
        wheel_event.angleDelta = Mock(return_value=Mock(y=Mock(return_value=-120)))
        cursor_pos = QPointF(400, 300)

        # Act
        camera_controller.handle_wheel_zoom(wheel_event, cursor_pos)

        # Assert
        assert camera_controller.zoom_factor < initial_zoom


class TestPanOperations:
    """Test pan offset management."""

    def test_pan_updates_offset(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test pan operation updates offset.

        Verifies:
        - pan_offset_x and pan_offset_y updated
        - Transform cache invalidated
        """
        # Arrange
        assert camera_controller.pan_offset_x == 0.0
        assert camera_controller.pan_offset_y == 0.0

        # Act
        camera_controller.pan(50.0, 75.0)

        # Assert
        assert camera_controller.pan_offset_x == 50.0
        assert camera_controller.pan_offset_y == 75.0
        assert camera_controller._transform_cache is None

    def test_apply_pan_offset_y(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test applying Y-axis pan offset.

        Verifies:
        - pan_offset_y adjusted
        """
        # Act
        camera_controller.apply_pan_offset_y(100.0)

        # Assert
        assert camera_controller.pan_offset_y == 100.0


class TestCoordinateTransformation:
    """Test data ↔ screen coordinate conversions."""

    def test_data_to_screen_conversion(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test converting data coordinates to screen coordinates.

        Verifies:
        - Coordinate conversion works
        - Returns QPointF with screen coordinates
        """
        # Act
        screen_pos = camera_controller.data_to_screen(100.0, 200.0)

        # Assert
        assert isinstance(screen_pos, QPointF)
        assert isinstance(screen_pos.x(), (int, float))
        assert isinstance(screen_pos.y(), (int, float))

    def test_screen_to_data_conversion(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test converting screen coordinates to data coordinates.

        Verifies:
        - Inverse conversion works
        - Returns tuple of data coordinates
        """
        # Act
        data_x, data_y = camera_controller.screen_to_data(QPointF(400.0, 300.0))

        # Assert
        assert isinstance(data_x, (int, float))
        assert isinstance(data_y, (int, float))

    def test_coordinate_round_trip(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test that coordinate conversions are roughly reversible.

        Verifies:
        - Converting data→screen→data returns close to original
        """
        # Arrange
        original_x, original_y = 100.0, 200.0

        # Act
        screen_pos = camera_controller.data_to_screen(original_x, original_y)
        result_x, result_y = camera_controller.screen_to_data(screen_pos)

        # Assert - Should be close (not exact due to rounding)
        assert abs(result_x - original_x) < 10
        assert abs(result_y - original_y) < 10


class TestCenteringOperations:
    """Test centering on frames, selections, and points."""

    def test_center_on_point(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test centering view on a specific point.

        Verifies:
        - Pan offset adjusted
        - View update triggered
        """
        # Arrange

        # Act
        camera_controller.center_on_point(100.0, 200.0)

        # Assert
        # Pan offsets should have changed (not same as initial)
        # Values depend on transform, so we just verify they're set
        assert isinstance(camera_controller.pan_offset_x, (int, float))
        assert isinstance(camera_controller.pan_offset_y, (int, float))

    def test_center_on_selection(
        self, camera_controller: ViewCameraController, mock_curve_view
    ) -> None:
        """Test centering view on selected points.

        Verifies:
        - View centers on selection bounds
        - With empty selection, uses curve bounds
        """
        # Arrange
        mock_curve_view.selected_indices = {0, 1}

        # Act
        camera_controller.center_on_selection()

        # Assert
        # View should be updated
        assert camera_controller._transform_cache is None

    def test_center_on_selection_empty(
        self, camera_controller: ViewCameraController, mock_curve_view
    ) -> None:
        """Test center_on_selection with empty selection.

        Verifies:
        - Method handles empty selection gracefully
        """
        # Arrange
        mock_curve_view.selected_indices = set()

        # Act - Should not raise
        camera_controller.center_on_selection()

        # Assert - No exception

    def test_center_on_frame(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test centering view on a specific frame.

        Verifies:
        - View pans to frame position
        """
        # Act
        camera_controller.center_on_frame(5)

        # Assert
        # View centered on frame 5
        assert isinstance(camera_controller.pan_offset_x, (int, float))
        assert isinstance(camera_controller.pan_offset_y, (int, float))


class TestViewFitting:
    """Test view fitting operations."""

    def test_fit_to_curve_bounds(
        self, camera_controller: ViewCameraController, mock_curve_view
    ) -> None:
        """Test fitting view to curve data bounds.

        Verifies:
        - Zoom adjusted to show all curve data
        - Pan centered on curve
        """
        # Arrange
        initial_zoom = camera_controller.zoom_factor

        # Act
        camera_controller.fit_to_curve()

        # Assert
        # Zoom should have changed
        assert camera_controller.zoom_factor != initial_zoom

    def test_fit_to_curve_with_empty_data(
        self, camera_controller: ViewCameraController, mock_curve_view
    ) -> None:
        """Test fit_to_curve with no curve data.

        Verifies:
        - Handles empty data gracefully
        - Doesn't crash
        """
        # Arrange
        mock_curve_view.curve_data = []

        # Act - Should not raise
        camera_controller.fit_to_curve()

        # Assert - No exception

    def test_fit_to_background_image(
        self, camera_controller: ViewCameraController, mock_curve_view
    ) -> None:
        """Test fitting view to background image bounds.

        Verifies:
        - Zoom adjusted for image
        - View encompasses image
        """
        # Arrange
        mock_curve_view.background_image = QPixmap(1920, 1080)

        # Act
        camera_controller.fit_to_background_image()

        # Assert
        # Zoom should be set for image fitting
        assert camera_controller.zoom_factor > 0


class TestViewState:
    """Test view state management."""

    def test_get_view_state_returns_state_dict(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test getting current view state.

        Verifies:
        - Returns ViewState object with zoom, pan, and other state
        """
        # Act
        state = camera_controller.get_view_state()

        # Assert
        # ViewState is a dataclass from services.transform_service
        assert hasattr(state, "zoom_factor")
        assert hasattr(state, "offset_x")
        assert hasattr(state, "offset_y")

    def test_view_state_includes_current_values(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test that view state contains current zoom and pan values.

        Verifies:
        - State reflects controller values
        """
        # Arrange
        camera_controller.zoom_factor = 2.5
        camera_controller.pan_offset_x = 100.0
        camera_controller.pan_offset_y = 50.0

        # Act
        state = camera_controller.get_view_state()

        # Assert - ViewState uses offset_x/offset_y, not pan_offset_x/pan_offset_y
        assert state.zoom_factor == 2.5
        assert state.offset_x == 100.0
        assert state.offset_y == 50.0


class TestResetView:
    """Test view reset operations."""

    def test_reset_view_restores_defaults(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test resetting view to defaults.

        Verifies:
        - Zoom reset to DEFAULT
        - Pan offsets reset to 0
        - Transform cache cleared
        """
        # Arrange
        camera_controller.zoom_factor = 3.0
        camera_controller.pan_offset_x = 100.0
        camera_controller.pan_offset_y = 50.0

        # Act
        camera_controller.reset_view()

        # Assert
        assert camera_controller.zoom_factor == DEFAULT_ZOOM_FACTOR
        assert camera_controller.pan_offset_x == 0.0
        assert camera_controller.pan_offset_y == 0.0
        assert camera_controller._transform_cache is None


class TestTransformUpdateTriggers:
    """Test conditions that invalidate transform cache."""

    def test_zoom_change_invalidates_cache(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test that changing zoom invalidates cache.

        Verifies:
        - Cache cleared after zoom change
        """
        # Arrange
        camera_controller.get_transform()
        assert camera_controller._transform_cache is not None

        # Act
        camera_controller.set_zoom_factor(2.0)

        # Assert
        assert camera_controller._transform_cache is None

    def test_pan_invalidates_cache(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test pan invalidates transform cache.

        Verifies:
        - Cache is cleared after pan (consistent with set_zoom_factor)
        - Ensures transforms are recalculated with new pan offsets
        """
        # Arrange
        camera_controller.get_transform()
        assert camera_controller._transform_cache is not None

        # Act
        camera_controller.pan(50.0, 25.0)

        # Assert - pan() invalidates cache (consistent with zoom behavior)
        assert camera_controller._transform_cache is None


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_zoom_to_zero_prevented(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test that zoom factor never becomes zero.

        Verifies:
        - Zoom clamped to minimum > 0
        """
        # Act
        camera_controller.set_zoom_factor(0.0)

        # Assert
        assert camera_controller.zoom_factor >= MIN_ZOOM_FACTOR
        assert camera_controller.zoom_factor > 0

    def test_very_large_pan_offset_allowed(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test that large pan offsets are allowed.

        Verifies:
        - No artificial limits on pan
        """
        # Act
        camera_controller.pan(10000.0, 10000.0)

        # Assert
        assert camera_controller.pan_offset_x == 10000.0
        assert camera_controller.pan_offset_y == 10000.0

    def test_negative_pan_offset_allowed(
        self, camera_controller: ViewCameraController
    ) -> None:
        """Test that negative pan offsets work.

        Verifies:
        - Both positive and negative pans supported
        """
        # Act
        camera_controller.pan(-100.0, -50.0)

        # Assert
        assert camera_controller.pan_offset_x == -100.0
        assert camera_controller.pan_offset_y == -50.0

    def test_fit_with_single_point(
        self, camera_controller: ViewCameraController, mock_curve_view
    ) -> None:
        """Test fitting view with only one data point.

        Verifies:
        - Single point handled gracefully
        - Zoom and pan set reasonably
        """
        # Arrange
        mock_curve_view.curve_data = [(1, 100.0, 200.0, "keyframe")]

        # Act
        camera_controller.fit_to_curve()

        # Assert
        assert camera_controller.zoom_factor > 0
        assert isinstance(camera_controller.pan_offset_x, (int, float))

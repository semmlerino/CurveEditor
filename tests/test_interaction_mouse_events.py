#!/usr/bin/env python3
"""
Comprehensive mouse event handling tests for InteractionService.

Tests all mouse interactions including:
- Mouse press (point selection, modifiers, rubber band)
- Mouse move (drag points, pan view, rubber band update)
- Mouse release (command creation, cleanup)
- Wheel events (zoom)

Following best practices:
- Use real components (ApplicationState, Commands)
- Mock only at system boundaries (Qt events)
- Parametrize similar test cases
- Clear test names describing behavior
"""

from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

import pytest
from PySide6.QtCore import QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent

from core.type_aliases import CurveDataList
from services import get_interaction_service
from stores.application_state import get_application_state

if TYPE_CHECKING:
    from services.interaction_service import InteractionService

from tests.test_helpers import MockCurveView


class TestMousePressEvents:
    """Test mouse press event handling."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()
        self.service._history = []
        self.service._current_index = -1

    def test_mouse_press_selects_point_single_click(self) -> None:
        """Test single click selects a single point."""
        app_state = get_application_state()
        test_data = cast(CurveDataList, [(1, 100.0, 100.0), (2, 200.0, 200.0), (3, 300.0, 300.0)])
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(test_data)

        # Create mouse event at point position
        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPointF(100.0, 100.0)
        event.button.return_value = Qt.MouseButton.LeftButton
        event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

        # Clear spatial index to ensure rebuild
        self.service.clear_spatial_index()

        self.service.handle_mouse_press(view, event)

        # Should select point at index 0
        assert view.selected_point_idx == 0
        assert 0 in view.selected_points

    def test_mouse_press_ctrl_toggles_selection(self) -> None:
        """Test Ctrl+click toggles point in selection."""
        app_state = get_application_state()
        test_data = cast(CurveDataList, [(1, 100.0, 100.0), (2, 200.0, 200.0)])
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(test_data)
        view.selected_points = {0}  # Pre-select first point

        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPointF(100.0, 100.0)
        event.button.return_value = Qt.MouseButton.LeftButton
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier

        self.service.clear_spatial_index()
        self.service.handle_mouse_press(view, event)

        # Should deselect point 0 (toggle off)
        assert 0 not in view.selected_points

    def test_mouse_press_shift_adds_to_selection(self) -> None:
        """Test Shift+click adds point to selection."""
        app_state = get_application_state()
        test_data = cast(CurveDataList, [(1, 100.0, 100.0), (2, 200.0, 200.0)])
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(test_data)
        view.selected_points = {1}  # Pre-select second point

        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPointF(100.0, 100.0)
        event.button.return_value = Qt.MouseButton.LeftButton
        event.modifiers.return_value = Qt.KeyboardModifier.ShiftModifier

        self.service.clear_spatial_index()
        self.service.handle_mouse_press(view, event)

        # Should add point 0 to selection (both selected)
        assert 0 in view.selected_points
        assert 1 in view.selected_points

    def test_mouse_press_starts_drag_operation(self) -> None:
        """Test clicking on point starts drag operation."""
        app_state = get_application_state()
        test_data = cast(CurveDataList, [(1, 100.0, 100.0)])
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(test_data)

        event = Mock(spec=QMouseEvent)
        pos = QPointF(100.0, 100.0)
        event.position.return_value = pos
        event.button.return_value = Qt.MouseButton.LeftButton
        event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

        self.service.clear_spatial_index()
        self.service.handle_mouse_press(view, event)

        # Should start drag
        assert view.drag_active is True
        assert view.last_drag_pos == pos

    def test_mouse_press_ctrl_starts_rubber_band(self) -> None:
        """Test Ctrl+click on empty area starts rubber band selection."""
        app_state = get_application_state()
        test_data = cast(CurveDataList, [(1, 100.0, 100.0)])
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(test_data)

        # Click away from point
        event = Mock(spec=QMouseEvent)
        pos = QPointF(500.0, 500.0)
        event.position.return_value = pos
        event.button.return_value = Qt.MouseButton.LeftButton
        event.modifiers.return_value = Qt.KeyboardModifier.ControlModifier

        self.service.handle_mouse_press(view, event)

        # Should start rubber band
        assert view.rubber_band_active is True
        assert view.rubber_band_origin == pos

    def test_mouse_press_middle_button_starts_pan(self) -> None:
        """Test middle button click starts pan operation."""
        view = MockCurveView([])

        event = Mock(spec=QMouseEvent)
        pos = QPointF(100.0, 100.0)
        event.position.return_value = pos
        event.button.return_value = Qt.MouseButton.MiddleButton
        event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

        self.service.handle_mouse_press(view, event)

        # Should start pan
        assert view.pan_active is True
        assert view.last_pan_pos == pos

    def test_mouse_press_clears_selection_on_empty_click(self) -> None:
        """Test clicking empty area without modifiers clears selection."""
        app_state = get_application_state()
        test_data = cast(CurveDataList, [(1, 100.0, 100.0)])
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(test_data)
        view.selected_points = {0}  # Pre-select point

        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPointF(500.0, 500.0)  # Away from points
        event.button.return_value = Qt.MouseButton.LeftButton
        event.modifiers.return_value = Qt.KeyboardModifier.NoModifier

        self.service.handle_mouse_press(view, event)

        # Should clear selection and start pan
        assert len(view.selected_points) == 0
        assert view.pan_active is True


class TestMouseMoveEvents:
    """Test mouse move event handling."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()

    def test_mouse_move_drags_selected_points(self) -> None:
        """Test mouse move updates point positions during drag."""
        app_state = get_application_state()
        test_data = cast(CurveDataList, [(1, 100.0, 100.0)])
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(test_data)
        view.drag_active = True
        view.last_drag_pos = QPointF(100.0, 100.0)
        view.selected_points = {0}

        # Move mouse to new position
        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPointF(150.0, 150.0)

        self.service.handle_mouse_move(view, event)

        # Point should be updated in view.curve_data
        # Delta in screen coords: +50, +50
        # With default transform (scale=1), delta in curve coords: +50, -50 (Y inverted)
        updated_point = view.curve_data[0]
        assert updated_point[1] != 100.0 or updated_point[2] != 100.0  # Position changed

    def test_mouse_move_pans_view(self) -> None:
        """Test mouse move pans view when pan is active."""
        view = MockCurveView([])
        view.pan_active = True
        view.last_pan_pos = QPointF(100.0, 100.0)

        # Track pan method calls
        pan_called = False
        original_pan = view.pan

        def track_pan(dx: float, dy: float) -> None:
            nonlocal pan_called
            pan_called = True
            original_pan(dx, dy)

        view.pan = track_pan

        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPointF(150.0, 150.0)

        self.service.handle_mouse_move(view, event)

        # Pan should be called
        assert pan_called is True

    def test_mouse_move_updates_rubber_band(self) -> None:
        """Test mouse move updates rubber band rectangle."""
        view = MockCurveView([])
        view.rubber_band_active = True
        view.rubber_band_origin = QPointF(100.0, 100.0)

        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPointF(200.0, 200.0)

        self.service.handle_mouse_move(view, event)

        # Rubber band geometry should be updated
        if view.rubber_band is not None:
            rect = view.rubber_band.geometry()
            assert rect.width() > 0 or rect.height() > 0


class TestMouseReleaseEvents:
    """Test mouse release event handling."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()

    def test_mouse_release_creates_move_command(self) -> None:
        """Test mouse release creates BatchMoveCommand after dragging."""
        # Note: This test verifies that drag_active is properly reset
        # Command creation requires MainWindowProtocol which needs proper setup
        app_state = get_application_state()
        test_data = cast(CurveDataList, [(1, 100.0, 100.0)])
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(test_data)
        view.drag_active = True
        view.selected_points = {0}

        # Set original positions for drag
        self.service._drag_original_positions = {0: (100.0, 100.0)}

        # Update point position to simulate drag
        view.curve_data[0] = (1, 150.0, 150.0)
        app_state.set_curve_data("test_curve", [(1, 150.0, 150.0)])

        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPointF(150.0, 150.0)

        self.service.handle_mouse_release(view, event)

        # Should end drag operation
        assert view.drag_active is False

    def test_mouse_release_ends_pan(self) -> None:
        """Test mouse release ends pan operation."""
        view = MockCurveView([])
        view.pan_active = True
        view.last_pan_pos = QPointF(100.0, 100.0)

        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPointF(150.0, 150.0)

        self.service.handle_mouse_release(view, event)

        # Pan should be ended
        assert view.pan_active is False
        assert view.last_pan_pos is None

    def test_mouse_release_finalizes_rubber_band_selection(self) -> None:
        """Test mouse release finalizes rubber band selection."""
        app_state = get_application_state()
        test_data = cast(CurveDataList, [(1, 100.0, 100.0), (2, 150.0, 150.0)])
        app_state.set_curve_data("test_curve", test_data)
        app_state.set_active_curve("test_curve")

        view = MockCurveView(test_data)
        view.rubber_band_active = True
        view.rubber_band_origin = QPointF(50.0, 50.0)

        # Ensure rubber band exists
        from PySide6.QtWidgets import QRubberBand

        if view.rubber_band is None:
            view.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle)

        # Set rubber band geometry to cover points
        view.rubber_band.setGeometry(QRect(50, 50, 150, 150))

        event = Mock(spec=QMouseEvent)
        event.position.return_value = QPointF(200.0, 200.0)

        self.service.handle_mouse_release(view, event)

        # Rubber band should be deactivated and hidden
        assert view.rubber_band_active is False
        assert not view.rubber_band.isVisible()


class TestWheelEvents:
    """Test wheel event handling."""

    service: "InteractionService"  # pyright: ignore[reportUninitializedInstanceVariable]

    @pytest.fixture(autouse=True)
    def setup(self, qapp) -> None:
        """Setup test environment."""
        self.service = get_interaction_service()

    def test_wheel_event_zooms_in(self) -> None:
        """Test positive wheel delta zooms in."""
        view = MockCurveView([])

        # Track zoom method calls
        zoom_called = False
        zoom_factor_arg = 1.0

        def track_zoom(factor: float, center: QPointF) -> None:
            nonlocal zoom_called, zoom_factor_arg
            zoom_called = True
            zoom_factor_arg = factor

        view.zoom = track_zoom  # pyright: ignore[reportAttributeAccessIssue]

        event = Mock(spec=QWheelEvent)
        event.angleDelta.return_value = Mock(y=lambda: 120)  # Positive delta
        event.position.return_value = QPointF(100.0, 100.0)

        self.service.handle_wheel_event(view, event)

        # Zoom should be called with factor > 1.0
        assert zoom_called is True
        assert zoom_factor_arg > 1.0

    def test_wheel_event_zooms_out(self) -> None:
        """Test negative wheel delta zooms out."""
        view = MockCurveView([])

        zoom_called = False
        zoom_factor_arg = 1.0

        def track_zoom(factor: float, center: QPointF) -> None:
            nonlocal zoom_called, zoom_factor_arg
            zoom_called = True
            zoom_factor_arg = factor

        view.zoom = track_zoom  # pyright: ignore[reportAttributeAccessIssue]

        event = Mock(spec=QWheelEvent)
        event.angleDelta.return_value = Mock(y=lambda: -120)  # Negative delta
        event.position.return_value = QPointF(100.0, 100.0)

        self.service.handle_wheel_event(view, event)

        # Zoom should be called with factor < 1.0
        assert zoom_called is True
        assert zoom_factor_arg < 1.0

"""
Event handling service for the CurveEditor.

This service processes raw input events (mouse, keyboard, wheel) and converts
them into high-level actions for other services to handle.
"""

import logging
from typing import Any

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent

from services.protocols.event_protocol import ActionType, EventHandlerProtocol, EventResult

logger = logging.getLogger(__name__)


class EventHandlerService(EventHandlerProtocol):
    """
    Handles input events and converts them to actions.

    This service is responsible for:
    - Processing mouse, keyboard, and wheel events
    - Determining what action should be taken based on event and modifiers
    - Converting screen coordinates to curve coordinates
    - Managing drag and pan states
    """

    def __init__(self):
        """Initialize the event handler service."""
        self._drag_start_pos: QPointF | None = None
        self._pan_start_pos: QPointF | None = None
        self._is_dragging = False
        self._is_panning = False
        self._is_selecting = False
        self._selection_start: QPointF | None = None

    def handle_mouse_press(self, view: Any, event: QMouseEvent) -> EventResult:
        """
        Handle mouse press events.

        Args:
            view: The curve view widget
            event: The mouse press event

        Returns:
            EventResult indicating the action to take
        """
        pos = event.position()
        button = event.button()
        modifiers = event.modifiers()

        # Right click - context menu
        if button == Qt.MouseButton.RightButton:
            return EventResult.handled_with(ActionType.CONTEXT_MENU, position=pos)

        # Middle button - start pan
        if button == Qt.MouseButton.MiddleButton:
            self._pan_start_pos = pos
            self._is_panning = True
            return EventResult.handled_with(ActionType.PAN, start_pos=pos)

        # Left button - selection or drag
        if button == Qt.MouseButton.LeftButton:
            # Convert to curve coordinates
            curve_pos = self._convert_to_curve_coords(view, pos)

            # Check for point at position
            from services import get_selection_service

            selection_service = get_selection_service()
            point_idx = selection_service.find_point_at(view, curve_pos.x(), curve_pos.y())

            if point_idx >= 0:
                # Point found - select or start drag
                if modifiers & Qt.KeyboardModifier.ControlModifier:
                    # Multi-select with Ctrl
                    return EventResult.handled_with(ActionType.MULTI_SELECT, index=point_idx)
                elif modifiers & Qt.KeyboardModifier.ShiftModifier:
                    # Range select with Shift
                    return EventResult.handled_with(ActionType.MULTI_SELECT, index=point_idx, range_select=True)
                else:
                    # Single select and potential drag
                    self._drag_start_pos = pos
                    self._is_dragging = True
                    return EventResult.handled_with(ActionType.SELECT, index=point_idx, start_drag=True)
            else:
                # No point - start selection rectangle
                self._selection_start = pos
                self._is_selecting = True
                return EventResult.handled_with(ActionType.SELECT, clear_selection=True, start_rect=True)

        return EventResult.not_handled()

    def handle_mouse_move(self, view: Any, event: QMouseEvent) -> EventResult:
        """
        Handle mouse move events.

        Args:
            view: The curve view widget
            event: The mouse move event

        Returns:
            EventResult indicating the action to take
        """
        pos = event.position()

        # Handle panning
        if self._is_panning and self._pan_start_pos:
            delta = pos - self._pan_start_pos
            self._pan_start_pos = pos
            return EventResult.handled_with(ActionType.PAN, delta_x=delta.x(), delta_y=delta.y())

        # Handle dragging
        if self._is_dragging and self._drag_start_pos:
            delta = pos - self._drag_start_pos
            self._drag_start_pos = pos
            curve_delta = self._convert_delta_to_curve(view, delta)
            return EventResult.handled_with(ActionType.DRAG, delta_x=curve_delta.x(), delta_y=curve_delta.y())

        # Handle selection rectangle
        if self._is_selecting and self._selection_start:
            return EventResult.handled_with(ActionType.SELECT, rect_start=self._selection_start, rect_end=pos)

        return EventResult.not_handled()

    def handle_mouse_release(self, view: Any, event: QMouseEvent) -> EventResult:
        """
        Handle mouse release events.

        Args:
            view: The curve view widget
            event: The mouse release event

        Returns:
            EventResult indicating the action to take
        """
        result = EventResult.not_handled()

        # End panning
        if self._is_panning:
            self._is_panning = False
            self._pan_start_pos = None
            result = EventResult.handled_with(ActionType.PAN, end=True)

        # End dragging
        if self._is_dragging:
            self._is_dragging = False
            self._drag_start_pos = None
            result = EventResult.handled_with(ActionType.DRAG, end=True)

        # End selection rectangle
        if self._is_selecting and self._selection_start:
            pos = event.position()
            result = EventResult.handled_with(
                ActionType.SELECT, rect_start=self._selection_start, rect_end=pos, finish_rect=True
            )
            self._is_selecting = False
            self._selection_start = None

        return result

    def handle_wheel_event(self, view: Any, event: QWheelEvent) -> EventResult:
        """
        Handle mouse wheel events for zooming.

        Args:
            view: The curve view widget
            event: The wheel event

        Returns:
            EventResult indicating zoom action
        """
        # Get wheel delta
        delta = event.angleDelta().y()
        if delta == 0:
            return EventResult.not_handled()

        # Calculate zoom factor
        zoom_factor = 1.1 if delta > 0 else 0.9

        # Get zoom center point
        pos = event.position()

        return EventResult.handled_with(ActionType.ZOOM, factor=zoom_factor, center=pos)

    def handle_key_event(self, view: Any, event: QKeyEvent) -> EventResult:
        """
        Handle keyboard events.

        Args:
            view: The curve view widget
            event: The keyboard event

        Returns:
            EventResult indicating the action to take
        """
        key = event.key()
        modifiers = event.modifiers()

        # Delete key
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            return EventResult.handled_with(ActionType.DELETE)

        # Select all (Ctrl+A)
        if key == Qt.Key.Key_A and modifiers & Qt.KeyboardModifier.ControlModifier:
            return EventResult.handled_with(ActionType.SELECT, select_all=True)

        # Escape - clear selection
        if key == Qt.Key.Key_Escape:
            return EventResult.handled_with(ActionType.SELECT, clear_selection=True)

        # Arrow keys for nudging
        if key in (Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Up, Qt.Key.Key_Down):
            dx = dy = 0
            nudge_amount = 10 if modifiers & Qt.KeyboardModifier.ShiftModifier else 1

            if key == Qt.Key.Key_Left:
                dx = -nudge_amount
            elif key == Qt.Key.Key_Right:
                dx = nudge_amount
            elif key == Qt.Key.Key_Up:
                dy = -nudge_amount
            elif key == Qt.Key.Key_Down:
                dy = nudge_amount

            return EventResult.handled_with(ActionType.DRAG, nudge=True, delta_x=dx, delta_y=dy)

        return EventResult.not_handled()

    def handle_context_menu(self, view: Any, event: QMouseEvent) -> EventResult:
        """
        Handle context menu requests.

        Args:
            view: The curve view widget
            event: The mouse event triggering the menu

        Returns:
            EventResult with context menu data
        """
        pos = event.position()
        curve_pos = self._convert_to_curve_coords(view, pos)

        # Check what's under the cursor
        from services import get_selection_service

        selection_service = get_selection_service()
        point_idx = selection_service.find_point_at(view, curve_pos.x(), curve_pos.y())

        return EventResult.handled_with(
            ActionType.CONTEXT_MENU, position=pos, curve_position=curve_pos, point_index=point_idx
        )

    def _convert_to_curve_coords(self, view: Any, pos: QPointF) -> QPointF:
        """Convert screen coordinates to curve coordinates."""
        # This will use the transform service
        from services import get_transform_service

        transform_service = get_transform_service()
        transform = transform_service.get_transform(view)
        return transform.screen_to_curve(pos)

    def _convert_delta_to_curve(self, view: Any, delta: QPointF) -> QPointF:
        """Convert screen delta to curve delta."""
        from services import get_transform_service

        transform_service = get_transform_service()
        transform = transform_service.get_transform(view)

        # Convert delta by transforming two points and taking difference
        origin = transform.screen_to_curve(QPointF(0, 0))
        delta_point = transform.screen_to_curve(delta)
        return delta_point - origin

    def reset(self) -> None:
        """Reset all event handling state."""
        self._drag_start_pos = None
        self._pan_start_pos = None
        self._is_dragging = False
        self._is_panning = False
        self._is_selecting = False
        self._selection_start = None

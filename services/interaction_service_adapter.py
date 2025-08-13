"""
Adapter for InteractionService to delegate to new decomposed services.

This module provides the integration layer between the old God object
(InteractionService) and the new focused services during migration.
"""

import logging
import os
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent

from services.protocols.event_protocol import ActionType

logger = logging.getLogger(__name__)


class InteractionServiceAdapter:
    """
    Adapter to integrate new services with existing InteractionService.

    This class provides methods that can be mixed into InteractionService
    to delegate to the new services when the feature flag is enabled.
    """

    @staticmethod
    def handle_mouse_press_delegated(service: Any, view: Any, event: QMouseEvent) -> bool:
        """
        Delegate mouse press handling to EventHandlerService if enabled.

        Args:
            service: The InteractionService instance
            view: The curve view widget
            event: The mouse event

        Returns:
            True if handled by new service, False to use legacy code
        """
        if not os.environ.get("USE_NEW_SERVICES", "false").lower() == "true":
            return False

        try:
            from services import get_event_handler_service, get_selection_service

            event_handler = get_event_handler_service()
            selection_service = get_selection_service()

            # Process event through new service
            result = event_handler.handle_mouse_press(view, event)

            if not result.handled:
                return False

            # Handle the action based on result
            if result.action == ActionType.SELECT:
                if result.data:
                    if 'index' in result.data:
                        # Select a specific point
                        idx = result.data['index']
                        add_to_selection = result.data.get('add_to_selection', False)
                        selection_service.select_point_by_index(view, idx, add_to_selection)

                        # Update main window if available
                        if hasattr(view, 'main_window'):
                            service.on_point_selected(view, view.main_window, idx)

                    elif result.data.get('clear_selection'):
                        # Clear selection
                        selection_service.clear_selection(view)

                        # Update main window
                        if hasattr(view, 'main_window'):
                            service.update_history_buttons(view.main_window)

                    if result.data.get('start_drag'):
                        view.drag_active = True
                        view.last_drag_pos = event.position()

                    if result.data.get('start_rect'):
                        # Initialize rubber band selection
                        from PySide6.QtCore import QRect, QSize
                        from PySide6.QtWidgets import QRubberBand

                        if not hasattr(view, 'rubber_band'):
                            view.rubber_band = QRubberBand(QRubberBand.Shape.Rectangle, None)
                        view.rubber_band_origin = event.position()
                        view.rubber_band_active = True
                        view.rubber_band.setGeometry(QRect(view.rubber_band_origin.toPoint(), QSize()))
                        view.rubber_band.show()

            elif result.action == ActionType.MULTI_SELECT:
                if result.data and 'index' in result.data:
                    idx = result.data['index']
                    if result.data.get('range_select'):
                        # Range selection with Shift
                        # TODO: Implement range selection
                        selection_service.toggle_point_selection(view, idx)
                    else:
                        # Toggle selection with Ctrl
                        selection_service.toggle_point_selection(view, idx)

                    # Update main window
                    if hasattr(view, 'main_window'):
                        service.on_point_selected(view, view.main_window, idx)

            elif result.action == ActionType.PAN:
                if result.data and 'start_pos' in result.data:
                    view.pan_active = True
                    view.last_pan_pos = result.data['start_pos']
                    view.setCursor(Qt.CursorShape.ClosedHandCursor)

            elif result.action == ActionType.CONTEXT_MENU:
                # Let the legacy code handle context menu for now
                return False

            return True

        except Exception as e:
            logger.error(f"Error in delegated mouse press handling: {e}")
            return False

    @staticmethod
    def handle_mouse_move_delegated(service: Any, view: Any, event: QMouseEvent) -> bool:
        """
        Delegate mouse move handling to EventHandlerService if enabled.

        Args:
            service: The InteractionService instance
            view: The curve view widget
            event: The mouse event

        Returns:
            True if handled by new service, False to use legacy code
        """
        if not os.environ.get("USE_NEW_SERVICES", "false").lower() == "true":
            return False

        try:
            from services import get_event_handler_service, get_point_manipulation_service, get_selection_service

            event_handler = get_event_handler_service()
            point_manipulation = get_point_manipulation_service()
            selection_service = get_selection_service()

            # Process event through new service
            result = event_handler.handle_mouse_move(view, event)

            if not result.handled:
                return False

            # Handle the action based on result
            if result.action == ActionType.PAN and result.data:
                # Pan the view
                delta_x = result.data.get('delta_x', 0)
                delta_y = result.data.get('delta_y', 0)

                if hasattr(view, 'pan'):
                    view.pan(delta_x, delta_y)
                    view.update()

            elif result.action == ActionType.DRAG and result.data:
                # Drag selected points
                delta_x = result.data.get('delta_x', 0)
                delta_y = result.data.get('delta_y', 0)

                # Get selected points
                state = selection_service.get_selection_state(view)
                if state.selected_indices:
                    # Move points using manipulation service
                    change = point_manipulation.nudge_points(
                        view,
                        list(state.selected_indices),
                        delta_x,
                        delta_y
                    )

                    if change and hasattr(view, 'main_window'):
                        # Record in history
                        service.add_to_history(view.main_window)

            elif result.action == ActionType.SELECT and result.data:
                # Update rubber band rectangle
                if result.data.get('rect_start') and result.data.get('rect_end'):
                    if hasattr(view, 'rubber_band') and view.rubber_band:
                        from PySide6.QtCore import QRect
                        start = result.data['rect_start']
                        end = result.data['rect_end']
                        rect = QRect(start.toPoint(), end.toPoint()).normalized()
                        view.rubber_band.setGeometry(rect)

            return True

        except Exception as e:
            logger.error(f"Error in delegated mouse move handling: {e}")
            return False

    @staticmethod
    def handle_mouse_release_delegated(service: Any, view: Any, event: QMouseEvent) -> bool:
        """
        Delegate mouse release handling to EventHandlerService if enabled.

        Args:
            service: The InteractionService instance
            view: The curve view widget
            event: The mouse event

        Returns:
            True if handled by new service, False to use legacy code
        """
        if not os.environ.get("USE_NEW_SERVICES", "false").lower() == "true":
            return False

        try:
            from services import get_event_handler_service, get_selection_service

            event_handler = get_event_handler_service()
            selection_service = get_selection_service()

            # Process event through new service
            result = event_handler.handle_mouse_release(view, event)

            if not result.handled:
                return False

            # Handle the action based on result
            if result.action == ActionType.PAN and result.data and result.data.get('end'):
                # End panning
                view.pan_active = False
                view.last_pan_pos = None
                view.unsetCursor()

            elif result.action == ActionType.DRAG and result.data and result.data.get('end'):
                # End dragging
                view.drag_active = False
                view.last_drag_pos = None

            elif result.action == ActionType.SELECT and result.data and result.data.get('finish_rect'):
                # Finish rectangle selection
                if hasattr(view, 'rubber_band') and view.rubber_band:
                    from PySide6.QtCore import QRect
                    start = result.data['rect_start']
                    end = result.data['rect_end']
                    rect = QRect(start.toPoint(), end.toPoint()).normalized()

                    # Select points in rectangle
                    count = selection_service.select_points_in_rect(view, rect)

                    # Hide rubber band
                    view.rubber_band.hide()
                    view.rubber_band_active = False

                    # Update main window
                    if count > 0 and hasattr(view, 'main_window'):
                        service.update_history_buttons(view.main_window)

            return True

        except Exception as e:
            logger.error(f"Error in delegated mouse release handling: {e}")
            return False

    @staticmethod
    def handle_wheel_event_delegated(service: Any, view: Any, event: QWheelEvent) -> bool:
        """
        Delegate wheel event handling to EventHandlerService if enabled.

        Args:
            service: The InteractionService instance
            view: The curve view widget
            event: The wheel event

        Returns:
            True if handled by new service, False to use legacy code
        """
        if not os.environ.get("USE_NEW_SERVICES", "false").lower() == "true":
            return False

        try:
            from services import get_event_handler_service

            event_handler = get_event_handler_service()

            # Process event through new service
            result = event_handler.handle_wheel_event(view, event)

            if not result.handled:
                return False

            # Handle zoom action
            if result.action == ActionType.ZOOM and result.data:
                factor = result.data.get('factor', 1.0)
                center = result.data.get('center')

                if hasattr(view, 'zoom'):
                    view.zoom(factor, center)
                    view.update()

            return True

        except Exception as e:
            logger.error(f"Error in delegated wheel event handling: {e}")
            return False

    @staticmethod
    def handle_key_event_delegated(service: Any, view: Any, event: QKeyEvent) -> bool:
        """
        Delegate key event handling to EventHandlerService if enabled.

        Args:
            service: The InteractionService instance
            view: The curve view widget
            event: The key event

        Returns:
            True if handled by new service, False to use legacy code
        """
        if not os.environ.get("USE_NEW_SERVICES", "false").lower() == "true":
            return False

        try:
            from services import get_event_handler_service, get_point_manipulation_service, get_selection_service

            event_handler = get_event_handler_service()
            selection_service = get_selection_service()
            point_manipulation = get_point_manipulation_service()

            # Process event through new service
            result = event_handler.handle_key_event(view, event)

            if not result.handled:
                return False

            # Handle the action based on result
            if result.action == ActionType.DELETE:
                # Delete selected points
                state = selection_service.get_selection_state(view)
                if state.selected_indices:
                    change = point_manipulation.delete_selected_points(
                        view,
                        list(state.selected_indices)
                    )

                    if change and hasattr(view, 'main_window'):
                        service.add_to_history(view.main_window)

            elif result.action == ActionType.SELECT and result.data:
                if result.data.get('select_all'):
                    # Select all points
                    selection_service.select_all_points(view)
                    if hasattr(view, 'main_window'):
                        service.update_history_buttons(view.main_window)

                elif result.data.get('clear_selection'):
                    # Clear selection
                    selection_service.clear_selection(view)
                    if hasattr(view, 'main_window'):
                        service.update_history_buttons(view.main_window)

            elif result.action == ActionType.DRAG and result.data and result.data.get('nudge'):
                # Nudge selected points
                delta_x = result.data.get('delta_x', 0)
                delta_y = result.data.get('delta_y', 0)

                state = selection_service.get_selection_state(view)
                if state.selected_indices:
                    change = point_manipulation.nudge_points(
                        view,
                        list(state.selected_indices),
                        delta_x,
                        delta_y
                    )

                    if change and hasattr(view, 'main_window'):
                        service.add_to_history(view.main_window)

            return True

        except Exception as e:
            logger.error(f"Error in delegated key event handling: {e}")
            return False

#!/usr/bin/env python
"""
Consolidated InteractionService for CurveEditor.

This service merges functionality from:
- curve_service.py: Point manipulation methods (on_point_moved, on_point_selected)
- input_service.py: Mouse, keyboard, and UI event handling
- history_service.py: Undo/redo functionality

Provides a unified interface for all user interactions with the curve editor.
"""

import logging
from typing import Any, Protocol

from PySide6.QtCore import QPointF, QRect, QSize, Qt
from PySide6.QtGui import QAction, QKeyEvent, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QMenu, QRubberBand

from core.point_types import create_point4, get_point_frame, safe_extract_point

logger = logging.getLogger("interaction_service")


class HistoryContainerProtocol(Protocol):
    """Protocol for objects that can be saved and restored in history."""
    
    curve_data: list
    point_name: str
    point_color: str
    history: list
    history_index: int
    max_history_size: int
    
    def restore_state(self, state: dict) -> None:
        """Restore state from history."""
        ...


class StateSnapshot:
    """Efficient state snapshot using minimal data storage."""
    
    def __init__(self, curve_data, point_name: str, point_color: str):
        """Create a state snapshot."""
        # Performance optimization: Store shallow copy instead of deepcopy
        self._data = {
            "curve_data": list(curve_data),  # Shallow copy - tuples are immutable
            "point_name": point_name,
            "point_color": point_color,
        }
    
    def __getitem__(self, key: str) -> object:
        """Support dict-like access for backward compatibility."""
        return self._data[key]
    
    def __setitem__(self, key: str, value: object) -> None:
        """Support dict-like assignment for backward compatibility."""
        self._data[key] = value
    
    def get(self, key: str, default: object = None) -> object:
        """Support dict.get() method for backward compatibility."""
        return self._data.get(key, default)
    
    def keys(self):
        """Support dict.keys() for backward compatibility."""
        return self._data.keys()
    
    def values(self):
        """Support dict.values() for backward compatibility."""
        return self._data.values()
    
    def items(self):
        """Support dict.items() for backward compatibility."""
        return self._data.items()


class InteractionService:
    """
    Consolidated service for all user interactions.
    
    This service handles:
    - Point manipulation (selection, moving)
    - Mouse and keyboard input
    - History management (undo/redo)
    - UI event handling
    """
    
    def __init__(self):
        """Initialize the InteractionService."""
        pass
    
    # ==================== Point Manipulation (from curve_service) ====================
    
    def on_point_moved(self, main_window: "MainWindowProtocol", idx: int, x: float, y: float) -> None:
        """Handle point moved in the view. Updates curve_data and point info.
        
        Args:
            main_window: The main application window
            idx: Index of the point that was moved
            x: New X coordinate
            y: New Y coordinate
        """
        if not hasattr(main_window, "curve_data") or idx < 0 or idx >= len(main_window.curve_data):
            return
        
        point = main_window.curve_data[idx]
        # Use type-safe extraction and update
        frame, _, _, status = safe_extract_point(point)
        # Always create Point4 for consistency
        main_window.curve_data[idx] = create_point4(frame, x, y, status)
        self.update_point_info(main_window, idx, x, y)
        
        if hasattr(main_window, "add_to_history"):
            main_window.add_to_history()
    
    def on_point_selected(self, curve_view: "CurveViewProtocol", main_window: "MainWindowProtocol", idx: int) -> None:
        """Handle point selected event from the curve view.
        
        Args:
            curve_view: The curve view widget
            main_window: The main application window
            idx: Index of the selected point
        """
        # Update main window selected indices
        sel_idx = getattr(curve_view, "selected_point_idx", idx) if hasattr(curve_view, "selected_point_idx") else idx
        idx = sel_idx if isinstance(sel_idx, int) else -1
        main_window.selected_indices = [idx] if idx >= 0 else []
        
        # Ensure curve view's selection is in sync
        if hasattr(curve_view, "selected_points"):
            curve_view.selected_points = set()
            if idx >= 0:
                curve_view.selected_points.add(idx)
                curve_view.selected_point_idx = idx
        
        # Update point info if valid index
        if idx >= 0 and idx < len(main_window.curve_data):
            point_data = main_window.curve_data[idx]
            frame, x, y, _ = safe_extract_point(point_data)
            self.update_point_info(main_window, idx, x, y)
            # Update timeline if available
            if hasattr(main_window, "timeline_slider"):
                main_window.ui_components.timeline_slider.setValue(frame)
        else:
            if 0 <= idx < len(main_window.curve_data):
                current_point = main_window.curve_data[idx]
                frame, x, y, _ = safe_extract_point(current_point)
                # Update point with new status using type-safe constructor
                main_window.curve_data[idx] = create_point4(frame, x, y, "keyframe")
                
                # Also update the point in curve_view.points if available
                if hasattr(curve_view, "points") and idx < len(getattr(curve_view, "points", [])):
                    points = getattr(curve_view, "points")
                    points[idx] = create_point4(frame, x, y, "keyframe")
                
                # Update point info display
                self.update_point_info(main_window, idx, x, y)
                # Add to history
                if hasattr(main_window, "add_to_history"):
                    main_window.add_to_history()
    
    def update_point_info(self, main_window: "MainWindowProtocol", idx: int, x: float, y: float) -> None:
        """Update the point information panel with selected point data.
        
        Args:
            main_window: The main application window
            idx: Index of the point
            x: X coordinate
            y: Y coordinate
        """
        # Collect types for all selected points on the active frame
        selected_types: set[str] = set()
        frame = None
        
        # Get selected indices if available
        selected_indices: list[int] = []
        if hasattr(main_window, "curve_view") and hasattr(main_window.curve_view, "get_selected_indices"):
            selected_indices = main_window.curve_view.get_selected_indices()
        
        if selected_indices:
            # Use the frame of the first selected point as the active frame
            first_idx: int = selected_indices[0]
            if first_idx >= 0 and first_idx < len(main_window.curve_data):
                frame = get_point_frame(main_window.curve_data[first_idx])
                
                # Collect types for all selected points on this frame
                for idx_ in selected_indices:
                    if idx_ >= 0 and idx_ < len(main_window.curve_data):
                        pt = main_window.curve_data[idx_]
                        pt_frame, _, _, pt_status = safe_extract_point(pt)
                        if pt_frame == frame:
                            selected_types.add(pt_status)
        
        # Fallback if no selection or no types found
        if not selected_types and idx >= 0 and idx < len(main_window.curve_data):
            point_data = main_window.curve_data[idx]
            frame, _, _, status = safe_extract_point(point_data)
            selected_types.add(status)
        
        # Update UI text fields
        fields = {
            "type_edit": ", ".join(sorted(selected_types)) if selected_types else "",
            "frame_edit": str(frame) if frame is not None else "",
            "x_coord_edit": f"{x:.2f}",
            "y_coord_edit": f"{y:.2f}",
        }
        
        for field_name, value in fields.items():
            field = getattr(main_window, field_name, None)
            if field is not None:
                field.setText(value)
        
        # Enable point controls
        if hasattr(main_window, "update_point_button"):
            main_window.ui_components.update_point_button.setEnabled(True)
        if hasattr(main_window, "type_edit"):
            main_window.ui_components.type_edit.setEnabled(True)
    
    # ==================== Mouse Input Handling (from input_service) ====================
    
    def handle_mouse_press(self, view: Any, event: QMouseEvent) -> None:
        """Handle mouse press events for selection, dragging, panning, and rectangle selection.
        
        Args:
            view: The curve view widget
            event: Mouse press event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            if event.modifiers() & Qt.KeyboardModifier.AltModifier:
                # Start rectangle selection
                if not hasattr(view, "rubber_band") or getattr(view, "rubber_band", None) is None:
                    setattr(view, "rubber_band", QRubberBand(QRubberBand.Shape.Rectangle, None))
                if not hasattr(view, "rubber_band_origin"):
                    setattr(view, "rubber_band_origin", QPointF())
                if not hasattr(view, "rubber_band_active"):
                    setattr(view, "rubber_band_active", False)
                
                # Set the origin point for the rubber band
                setattr(view, "rubber_band_origin", event.position())
                rubber_band = getattr(view, "rubber_band")
                if rubber_band:
                    rubber_band.setGeometry(QRect(getattr(view, "rubber_band_origin").toPoint(), QSize()))
                    rubber_band.show()
                setattr(view, "rubber_band_active", True)
                # Prevent single point selection/drag when starting rubber band
                view.drag_active = False
                view.last_drag_pos = None
            else:
                # Original LeftButton logic (single point select/drag)
                idx = self.find_point_at(view, event.pos().x(), event.pos().y())
                if idx is not None and idx >= 0:
                    self.select_point_by_index(view, view.main_window, idx)
                    view.drag_active = True
                    view.last_drag_pos = event.position()
                else:
                    self.clear_selection(view, view.main_window)
                    view.drag_active = False
                    view.last_drag_pos = None
        
        elif event.button() == Qt.MouseButton.MiddleButton:
            # Start panning
            view.pan_active = True
            view.last_pan_pos = event.position()
            view.setCursor(Qt.CursorShape.ClosedHandCursor)
    
    def handle_mouse_move(self, view: Any, event: QMouseEvent) -> None:
        """Handle mouse move events for dragging points, panning, or updating rectangle selection.
        
        Args:
            view: The curve view widget
            event: Mouse move event
        """
        current_pos = event.position()
        
        # Handle rubber band selection
        rubber_band_active = getattr(view, "rubber_band_active", False)
        rubber_band = getattr(view, "rubber_band", None)
        
        if rubber_band_active and rubber_band:
            # Calculate selection rectangle
            rubber_band_origin = getattr(view, "rubber_band_origin")
            selection_rect = QRect(rubber_band_origin.toPoint(), current_pos.toPoint()).normalized()
            # Update rubber band geometry
            rubber_band.setGeometry(selection_rect)
            # Perform selection in real-time
            self.select_points_in_rect(view, view.main_window, selection_rect)
        
        elif view.drag_active and view.last_drag_pos and view.selected_point_idx >= 0:
            # Drag selected point
            delta = current_pos - view.last_drag_pos
            view.last_drag_pos = current_pos
            scale = view.zoom_factor if view.zoom_factor != 0 else 1.0
            dx = delta.x() / scale
            dy = delta.y() / scale
            
            # Get current position and calculate new position with delta
            point_data = view.get_point_data(view.selected_point_idx)
            if point_data:
                _, current_x, current_y, _ = point_data
                new_x = current_x + dx
                new_y = current_y + dy
                # Update point position
                self.update_point_position(view, view.main_window, view.selected_point_idx, new_x, new_y)
        
        elif view.pan_active and view.last_pan_pos:
            # Pan the view
            delta = current_pos - view.last_pan_pos
            view.last_pan_pos = current_pos
            view.offset_x += delta.x()
            view.offset_y += delta.y()
            view.update()
    
    def handle_mouse_release(self, view: Any, event: QMouseEvent) -> None:
        """Handle mouse release events.
        
        Args:
            view: The curve view widget
            event: Mouse release event
        """
        if event.button() == Qt.MouseButton.LeftButton:
            # End dragging
            view.drag_active = False
            view.last_drag_pos = None
            
            # End rubber band selection
            if getattr(view, "rubber_band_active", False):
                setattr(view, "rubber_band_active", False)
                rubber_band = getattr(view, "rubber_band", None)
                if rubber_band:
                    rubber_band.hide()
        
        elif event.button() == Qt.MouseButton.MiddleButton:
            # End panning
            view.pan_active = False
            view.last_pan_pos = None
            view.setCursor(Qt.CursorShape.ArrowCursor)
    
    def handle_wheel_event(self, view: Any, event: QWheelEvent) -> None:
        """Handle mouse wheel events for zooming.
        
        Args:
            view: The curve view widget
            event: Wheel event
        """
        # Get the position before zoom
        pos = event.position()
        
        # Calculate zoom factor
        delta = event.angleDelta().y()
        zoom_speed = 0.001
        factor = 1.0 + (delta * zoom_speed)
        
        # Apply zoom
        old_zoom = view.zoom_factor
        view.zoom_factor = max(0.1, min(10.0, view.zoom_factor * factor))
        
        # Adjust offset to zoom towards mouse position
        if view.zoom_factor != old_zoom:
            # Calculate the offset adjustment to keep the point under the mouse stationary
            zoom_ratio = view.zoom_factor / old_zoom
            view.offset_x = pos.x() - (pos.x() - view.offset_x) * zoom_ratio
            view.offset_y = pos.y() - (pos.y() - view.offset_y) * zoom_ratio
        
        view.update()
    
    def handle_key_press(self, view: Any, event: QKeyEvent) -> None:
        """Handle keyboard events.
        
        Args:
            view: The curve view widget
            event: Key press event
        """
        key = event.key()
        modifiers = event.modifiers()
        
        # Delete selected points
        if key == Qt.Key.Key_Delete:
            self.delete_selected_points(view, view.main_window)
        
        # Select all points
        elif key == Qt.Key.Key_A and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.select_all_points(view, view.main_window)
        
        # Deselect all points
        elif key == Qt.Key.Key_D and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.clear_selection(view, view.main_window)
        
        # Undo
        elif key == Qt.Key.Key_Z and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.undo(view.main_window)
        
        # Redo
        elif key == Qt.Key.Key_Y and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.redo(view.main_window)
        
        # Reset view
        elif key == Qt.Key.Key_R and modifiers == Qt.KeyboardModifier.ControlModifier:
            self.reset_view(view)
    
    # ==================== History Management (from history_service) ====================
    
    def add_to_history(self, main_window: HistoryContainerProtocol) -> None:
        """Add current state to history.
        
        Args:
            main_window: The main application window containing state
        """
        # If we're not at the end of the history, truncate it
        if main_window.history_index < len(main_window.history) - 1:
            main_window.history = main_window.history[: main_window.history_index + 1]
        
        # Performance optimization: Use efficient state snapshot instead of deepcopy
        current_state = StateSnapshot(main_window.curve_data, main_window.point_name, main_window.point_color)
        
        main_window.history.append(current_state)
        main_window.history_index = len(main_window.history) - 1
        
        # Limit history size
        if len(main_window.history) > main_window.max_history_size:
            main_window.history = main_window.history[1:]
            main_window.history_index = len(main_window.history) - 1
        
        # Update UI buttons
        self._update_history_buttons(main_window)
    
    def undo(self, main_window: HistoryContainerProtocol) -> None:
        """Undo the last action.
        
        Args:
            main_window: The main application window
        """
        if main_window.history_index > 0:
            main_window.history_index -= 1
            state = main_window.history[main_window.history_index]
            self._restore_state(main_window, state)
            self._update_history_buttons(main_window)
            
            logger.info(f"Undo performed, history index: {main_window.history_index}")
    
    def redo(self, main_window: HistoryContainerProtocol) -> None:
        """Redo the previously undone action.
        
        Args:
            main_window: The main application window
        """
        if main_window.history_index < len(main_window.history) - 1:
            main_window.history_index += 1
            state = main_window.history[main_window.history_index]
            self._restore_state(main_window, state)
            self._update_history_buttons(main_window)
            
            logger.info(f"Redo performed, history index: {main_window.history_index}")
    
    def clear_history(self, main_window: HistoryContainerProtocol) -> None:
        """Clear all history.
        
        Args:
            main_window: The main application window
        """
        main_window.history = []
        main_window.history_index = -1
        self._update_history_buttons(main_window)
        
        logger.info("History cleared")
    
    def _restore_state(self, main_window: HistoryContainerProtocol, state: StateSnapshot) -> None:
        """Restore application state from a history snapshot.
        
        Args:
            main_window: The main application window
            state: State snapshot to restore
        """
        # Restore curve data
        main_window.curve_data = list(state["curve_data"])
        
        # Restore other properties
        main_window.point_name = state.get("point_name", "")
        main_window.point_color = state.get("point_color", "")
        
        # Trigger UI update if method exists
        if hasattr(main_window, "restore_state"):
            main_window.restore_state(state._data)
        
        # Update curve view if available
        if hasattr(main_window, "curve_view") and main_window.curve_view:
            main_window.curve_view.points = list(main_window.curve_data)
            main_window.curve_view.update()
    
    def _update_history_buttons(self, main_window: Any) -> None:
        """Update the enabled state of undo/redo buttons.
        
        Args:
            main_window: The main application window
        """
        if hasattr(main_window, "undo_button"):
            main_window.undo_button.setEnabled(main_window.history_index > 0)
        
        if hasattr(main_window, "redo_button"):
            main_window.redo_button.setEnabled(main_window.history_index < len(main_window.history) - 1)
    
    # ==================== Helper Methods ====================
    
    def find_point_at(self, view: Any, x: float, y: float, threshold: float = 10.0) -> int:
        """Find a point at the given screen coordinates.
        
        Args:
            view: The curve view widget
            x: Screen X coordinate
            y: Screen Y coordinate
            threshold: Selection threshold in pixels
        
        Returns:
            Index of the point at the position, or -1 if no point found
        """
        if not hasattr(view, "points"):
            return -1
        
        # Convert screen to data coordinates
        # This would normally use the transform service
        # For now, simplified implementation
        for i, point in enumerate(view.points):
            _, px, py, _ = safe_extract_point(point)
            # Transform point to screen coordinates
            screen_x = px * view.zoom_factor + view.offset_x
            screen_y = py * view.zoom_factor + view.offset_y
            
            # Check distance
            dist = ((screen_x - x) ** 2 + (screen_y - y) ** 2) ** 0.5
            if dist <= threshold:
                return i
        
        return -1
    
    def select_point_by_index(self, view: Any, main_window: Any, idx: int) -> bool:
        """Select a point by its index.
        
        Args:
            view: The curve view widget
            main_window: The main application window
            idx: Index of the point to select
            
        Returns:
            bool: True if successful, False if index is invalid
        """
        if idx >= 0 and hasattr(view, "selected_points") and hasattr(view, "points") and idx < len(view.points):
            view.selected_points = {idx}
            view.selected_point_idx = idx
            main_window.selected_indices = [idx]
            view.update()
            return True
        return False
    
    def clear_selection(self, view: Any, main_window: Any) -> None:
        """Clear all selected points.
        
        Args:
            view: The curve view widget
            main_window: The main application window
        """
        if hasattr(view, "selected_points"):
            view.selected_points = set()
            view.selected_point_idx = -1
            main_window.selected_indices = []
            view.update()
    
    def select_all_points(self, view: Any, main_window: Any) -> int:
        """Select all points.
        
        Args:
            view: The curve view widget
            main_window: The main application window
            
        Returns:
            int: Number of points selected
        """
        if hasattr(view, "points") and hasattr(view, "selected_points"):
            count = len(view.points)
            view.selected_points = set(range(count))
            main_window.selected_indices = list(range(count))
            if count > 0:
                view.selected_point_idx = 0  # Set to first point when selecting all
            view.update()
            return count
        return 0
    
    def select_points_in_rect(self, view: Any, main_window: Any, rect: QRect) -> int:
        """Select all points within a rectangle.
        
        Args:
            view: The curve view widget
            main_window: The main application window
            rect: Selection rectangle in screen coordinates
            
        Returns:
            int: Number of points selected
        """
        if not hasattr(view, "points"):
            return 0
        
        selected = set()
        for i, point in enumerate(view.points):
            _, px, py, _ = safe_extract_point(point)
            # Transform point to screen coordinates
            screen_x = px * view.zoom_factor + view.offset_x
            screen_y = py * view.zoom_factor + view.offset_y
            
            # Check if point is in rectangle
            if rect.contains(int(screen_x), int(screen_y)):
                selected.add(i)
        
        if hasattr(view, "selected_points"):
            view.selected_points = selected
            main_window.selected_indices = list(selected)
            view.update()
            return len(selected)
        return 0
    
    def delete_selected_points(self, view: Any, main_window: Any) -> None:
        """Delete all selected points.
        
        Args:
            view: The curve view widget
            main_window: The main application window
        """
        if not hasattr(view, "selected_points") or not view.selected_points:
            return
        
        # Delete points in reverse order to maintain indices
        for idx in sorted(view.selected_points, reverse=True):
            if idx < len(main_window.curve_data):
                del main_window.curve_data[idx]
                if hasattr(view, "points") and idx < len(view.points):
                    del view.points[idx]
        
        # Clear selection
        self.clear_selection(view, main_window)
        
        # Add to history
        if hasattr(main_window, "add_to_history"):
            main_window.add_to_history()
    
    def update_point_position(self, view: Any, main_window: Any, idx: int, x: float, y: float) -> bool:
        """Update the position of a point.
        
        Args:
            view: The curve view widget
            main_window: The main application window
            idx: Index of the point to update
            x: New X coordinate
            y: New Y coordinate
            
        Returns:
            bool: True if update was successful, False if index was invalid
        """
        if idx >= 0 and idx < len(main_window.curve_data):
            point = main_window.curve_data[idx]
            frame, _, _, status = safe_extract_point(point)
            main_window.curve_data[idx] = create_point4(frame, x, y, status)
            
            if hasattr(view, "points") and idx < len(view.points):
                view.points[idx] = create_point4(frame, x, y, status)
            
            view.update()
            return True
        return False
    
    def reset_view(self, view: Any) -> None:
        """Reset the view to default zoom and position.
        
        Args:
            view: The curve view widget
        """
        view.zoom_factor = 1.0
        view.offset_x = 0.0
        view.offset_y = 0.0
        view.update()


# Module-level singleton instance
_instance = InteractionService()

def get_interaction_service() -> InteractionService:
    """Get the singleton instance of InteractionService."""
    return _instance
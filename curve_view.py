#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
from PySide6.QtWidgets import QWidget
from typing import Any, Optional
from PySide6.QtCore import Qt, Signal
from services.centering_zoom_service import CenteringZoomService as ZoomOperations
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath, QPaintEvent
from PySide6.QtCore import QPointF
from services.input_service import InputService
from keyboard_shortcuts import ShortcutManager
from services.image_service import ImageService


class CurveView(QWidget):
    """Widget for displaying and editing the 2D tracking curve."""

    # --- Added for type safety and linting ---
    show_grid: bool = False
    show_velocity_vectors: bool = False
    show_all_frame_numbers: bool = False
    show_crosshair: bool = False
    grid_color: QColor | None = None
    grid_line_width: int = 1
    # Removed class-level offset_x and offset_y to avoid shadowing instance variables

    x_offset: int = 0
    y_offset: int = 0
    timeline_slider: Optional[Any] = None  # TODO: Use correct type if known, e.g. Optional[QSlider]
    frame_marker_label: Optional[Any] = None  # TODO: Use correct type if known, e.g. Optional[QLabel]
    curve_data: list[tuple[int, float, float]] = []
    # -----------------------------------------

    point_moved = Signal(int, float, float)  # Signal emitted when a point is moved
    point_selected = Signal(int)  # Signal emitted when a point is selected
    image_changed = Signal(int)  # Signal emitted when image changes via keyboard

    def __init__(self, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        # Set focus policy using correct enum for PySide6
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # type: ignore[attr-defined]
        # If points can be 3-tuple or 4-tuple, use list[Any] for compatibility with all assignments:
        self.points: list[Any] = []  # TODO: Refine type if only one tuple shape is valid
        self.selected_point_idx: int = -1
        self.selected_points: set[int] = set()
        self.drag_active: bool = False
        self.zoom_factor: float = 1.0
        self.offset_x: int = 0
        self.offset_y: int = 0
        self.image_width: int = 1920  # Default, will be updated when data is loaded
        self.image_height: int = 1080  # Default, will be updated when data is loaded
        self.setMouseTracking(True)
        self.point_radius: int = 5

        self.last_drag_pos: Optional[QPointF] = None
        self.pan_active: bool = False
        self.last_pan_pos: Optional[QPointF] = None
        # Image sequence support
        self.background_image: Optional[Any] = None  # TODO: Use correct type if known, e.g. Optional[QImage]
        self.show_background: bool = True
        self.background_opacity: float = 0.7  # 0.0 to 1.0

        # Register shortcuts via ShortcutManager
        self._register_shortcuts()

    def _register_shortcuts(self) -> None:
        # Register CurveView-specific shortcuts
        from typing import Any, cast
        ShortcutManager.connect_shortcut(cast(Any, self), cast(Any, "reset_view"), cast(Any, self.reset_view_slot))
        ShortcutManager.connect_shortcut(cast(Any, self), cast(Any, "toggle_y_flip"), cast(Any, self.toggle_y_flip))
        ShortcutManager.connect_shortcut(cast(Any, self), cast(Any, "toggle_scale_to_image"), cast(Any, self.toggle_scale_to_image))
        ShortcutManager.connect_shortcut(cast(Any, self), cast(Any, "toggle_debug_mode"), cast(Any, self.toggle_debug_mode))

    def reset_view_slot(self) -> None:
        self.resetView()
        self.x_offset = 0
        self.y_offset = 0
        self.update()

    def toggle_y_flip(self) -> None:
        self.flip_y_axis = not getattr(self, "flip_y_axis", False)
        self.update()

    def toggle_scale_to_image(self) -> None:
        self.scale_to_image = not getattr(self, "scale_to_image", False)
        self.update()

    def toggle_debug_mode(self) -> None:
        self.debug_mode = not getattr(self, "debug_mode", False)
        self.update()

        # Debug options
        self.debug_mode = True  # Enable debug visuals
        self.flip_y_axis = True  # Toggle Y-axis flip
        self.scale_to_image = True  # Automatically scale track data to match image dimensions
        self.x_offset = 0  # Manual X offset for fine-tuning alignment
        self.y_offset = 0  # Manual Y offset for fine-tuning alignment

    def setPoints(self, points: list[tuple[int, float, float]], image_width: int, image_height: int, preserve_view: bool = False) -> None:
        print(f"[DEBUG CurveView.setPoints] Start - preserve_view={preserve_view}")
        print(f"[DEBUG CurveView.setPoints] State BEFORE: Zoom={self.zoom_factor}, OffX={self.offset_x}, OffY={self.offset_y}, ManX={self.x_offset}, ManY={self.y_offset}")
        """Set the points to display and optionally preserve the current view state."""
        self.points = points
        # Update dimensions only if they are validly provided (greater than 0)
        if image_width > 0:
            self.image_width = image_width
        if image_height > 0:
            self.image_height = image_height
            sys.stdout.flush() # Correct indentation

        if not preserve_view:
            self.resetView() # Reset pan/zoom only if not preserving
            sys.stdout.flush() # Correct indentation

        self.update() # Trigger repaint with new data and current/reset view state

        sys.stdout.flush()
        print(f"[DEBUG CurveView.setPoints] State AFTER: Zoom={self.zoom_factor}, OffX={self.offset_x}, OffY={self.offset_y}, ManX={self.x_offset}, ManY={self.y_offset}")
    def set_image_sequence(self, path: str, filenames: list[str]) -> None:
        """Set the image sequence to display as background."""
        sys.stdout.flush()
        ImageService.set_image_sequence(  # type: ignore[attr-defined]
self, path, filenames)
        self.update()

    def set_current_image_by_frame(self, frame: int) -> None:
        """Set the current background image based on frame number."""
        ImageService.set_current_image_by_frame(  # type: ignore[attr-defined]
self, frame)

    def set_current_image_by_index(self, idx: int) -> None:
        """Set current image by index and update the view."""
        ImageService.set_current_image_by_index(  # type: ignore[attr-defined]
self, idx)
        self.update()

    def toggle_background_visible(self, visible: bool) -> None:
        """Toggle visibility of background image."""
        self.show_background = visible
        self.update()

    def set_background_opacity(self, opacity: float) -> None:
        self.background_opacity = min(max(opacity, 0.0), 1.0)
        self.update()

    def load_current_image(self) -> None:
        """Load the current image in the sequence."""
        print(f"[DEBUG CurveView.resetView] Start - State BEFORE: Zoom={self.zoom_factor}, OffX={self.offset_x}, OffY={self.offset_y}, ManX={self.x_offset}, ManY={self.y_offset}")
        print(f"[DEBUG CurveView.resetView] Start - State BEFORE: Zoom={self.zoom_factor}, OffX={self.offset_x}, OffY={self.offset_y}, ManX={self.x_offset}, ManY={self.y_offset}")
        ImageService.load_current_image(  # type: ignore[attr-defined]
self)
        print(f"[DEBUG CurveView.paintEvent] Start - State: Zoom={self.zoom_factor}, OffX={self.offset_x}, OffY={self.offset_y}, ManX={self.x_offset}, ManY={self.y_offset}")

    def resetView(self) -> None:
        print(f"[DEBUG CurveView.resetView] End - State AFTER: Zoom={self.zoom_factor}, OffX={self.offset_x}, OffY={self.offset_y}, ManX={self.x_offset}, ManY={self.y_offset}")
        """Reset view to show all points."""
        # Use the CenteringZoomService instead of the deprecated operations module
        from services.centering_zoom_service import CenteringZoomService as ZoomOperations
        print(f"[DEBUG CurveView.resetView] End - State AFTER: Zoom={self.zoom_factor}, OffX={self.offset_x}, OffY={self.offset_y}, ManX={self.x_offset}, ManY={self.y_offset}")
        ZoomOperations.reset_view(self)

        print(f"[DEBUG CurveView.paintEvent] Start - State: Zoom={self.zoom_factor}, OffX={self.offset_x}, OffY={self.offset_y}, ManX={self.x_offset}, ManY={self.y_offset}")
    def paintEvent(self, event: QPaintEvent) -> None:
        print(f"[DEBUG CurveView.paintEvent] Start - State: Zoom={self.zoom_factor}, OffX={self.offset_x}, OffY={self.offset_y}, ManX={self.x_offset}, ManY={self.y_offset}")
        print(f"[DEBUG CurveView.paintEvent] Start - State: Zoom={self.zoom_factor}, OffX={self.offset_x}, OffY={self.offset_y}, ManX={self.x_offset}, ManY={self.y_offset}")
        sys.stdout.flush()
        """Draw the curve and points."""
        if not self.points and not self.background_image:
            return

        painter = QPainter(self)  # type: ignore[arg-type]
        painter.setRenderHint(QPainter.Antialiasing)  # type: ignore[attr-defined]

        # Fill background
        painter.fillRect(self.rect(), QColor(40, 40, 40))

        # Get widget dimensions
        widget_width = self.width()
        widget_height = self.height()

        # Use the background image dimensions if available, otherwise use track dimensions
        display_width = self.image_width
        display_height = self.image_height

        if self.background_image:
            display_width = self.background_image.width()
            display_height = self.background_image.height()

        # Calculate the scale factor to fit in the widget
        scale_x = widget_width / display_width
        scale_y = widget_height / display_height

        # Use uniform scaling to maintain aspect ratio
        scale = min(scale_x, scale_y) * self.zoom_factor

        # Calculate centering offsets
        offset_x, offset_y = ZoomOperations.calculate_centering_offsets(widget_width, widget_height, display_width * scale, display_height * scale, self.offset_x, self.offset_y)
        # offset_y is set below
        # offset_y is now set by calculate_centering_offsets above

        # Transform data points to widget coordinates, respecting scale, centering, pan, and manual offsets
        def transform_point(x: float, y: float) -> tuple[float, float]:
            # 1. Flip Y if needed
            ty = y
            if getattr(self, "flip_y_axis", False):
                img_h = getattr(self, "image_height", self.height())
                ty = img_h - y

            # 2. Scale by overall scale
            sx = x * scale
            sy = ty * scale

            # 3. Center content in widget
            cx = sx + offset_x
            cy = sy + offset_y

            # 4. Apply pan offsets
            px = getattr(self, "offset_x", 0)
            py = getattr(self, "offset_y", 0)

            # 5. Apply manual alignment offsets
            fx = cx + px + getattr(self, "x_offset", 0)
            fy = cy + py + getattr(self, "y_offset", 0)

            return fx, fy

        # Draw background image if available
        if self.show_background and self.background_image:
            # Calculate scaled dimensions
            scaled_width = display_width * scale
            scaled_height = display_height * scale

            # Position image
            img_x = offset_x
            img_y = offset_y

            # Draw the image
            painter.setOpacity(self.background_opacity)
            painter.drawPixmap(int(img_x), int(img_y), int(scaled_width), int(scaled_height), self.background_image)
            painter.setOpacity(1.0)

            # Debugging visuals
            if self.debug_mode:
                # Show alignment info
                painter.setPen(QPen(QColor(255, 100, 100), 1))
                painter.drawText(10, 100, f"Manual Alignment: X-offset: {self.x_offset}, Y-offset: {self.y_offset}")
                painter.drawText(10, 120, f"Adjust with arrow keys + Shift/Ctrl")

        # Draw the main curve if available
        if self.points:
            # Set pen for the curve
            curve_pen = QPen(QColor(0, 160, 230), 2)
            painter.setPen(curve_pen)

            # Create path for the curve
            path = QPainterPath()
            first_point = True

            for frame, x, y in self.points:
                tx, ty = transform_point(x, y)

                if first_point:
                    path.moveTo(tx, ty)
                    first_point = False
                else:
                    path.lineTo(tx, ty)

            # Draw the curve
            painter.drawPath(path)

            # Draw points
            for i, pt in enumerate(self.points):
                # Support both (frame, x, y) and (frame, x, y, status)
                if len(pt) == 4 and pt[3] == 'interpolated':
                    frame, x, y, _ = pt
                    is_interpolated = True
                else:
                    frame, x, y = pt[:3]
                    is_interpolated = False

                tx, ty = transform_point(x, y)

                # Highlight selected points
                if i in self.selected_points:
                    painter.setPen(QPen(QColor(255, 80, 80), 2))
                    painter.setBrush(QColor(255, 80, 80, 150))
                    # primary index gets larger radius
                    point_radius = self.point_radius + 2 if i == self.selected_point_idx else self.point_radius
                elif is_interpolated:
                    # Lighter, more transparent colour for interpolated points
                    painter.setPen(QPen(QColor(180, 220, 255), 1))
                    painter.setBrush(QColor(200, 230, 255, 120))
                    point_radius = self.point_radius
                else:
                    painter.setPen(QPen(QColor(200, 200, 200), 1))
                    painter.setBrush(QColor(220, 220, 220, 200))
                    point_radius = self.point_radius

                painter.drawEllipse(QPointF(tx, ty), point_radius, point_radius)

                # Draw frame number or type/status for selected points
                if i in self.selected_points:
                    painter.setPen(QPen(QColor(200, 200, 100), 1))
                    font = painter.font()
                    font.setPointSize(8)
                    painter.setFont(font)
                    # Show frame and type/status
                    point_type = pt[3] if len(pt) >= 4 else 'normal'
                    painter.drawText(int(tx) + 10, int(ty) - 10, f"{frame}, {point_type}")
                elif i % 10 == 0:
                    painter.setPen(QPen(QColor(200, 200, 100), 1))
                    font = painter.font()
                    font.setPointSize(8)
                    painter.setFont(font)
                    painter.drawText(int(tx) + 10, int(ty) - 10, str(frame))

        # Display info
        info_font = QFont("Monospace", 9)
        painter.setFont(info_font)
        painter.setPen(QPen(QColor(200, 200, 200), 1))

        # Show current view info
        info_text = f"Zoom: {self.zoom_factor:.2f}x | Points: {len(self.points)}"
        if hasattr(self, 'selected_points') and self.selected_points:
            # Gather types of all selected points
            selected_types: set[str] = set()
            for i in self.selected_points:
                if 0 <= i < len(self.points):
                    pt = self.points[i]
                    if len(pt) >= 4:
                        selected_types.add(str(pt[3]))
                    else:
                        selected_types.add('normal')
            types_str = ', '.join(sorted(selected_types))
            info_text += f" | Type(s): {types_str}"
        painter.drawText(10, 20, info_text)

        # Show image info if available
        if self.background_image:
            img_info = f"Image: {ImageService.get_current_image_index(  # type: ignore[attr-defined]
self) + 1}/{ImageService.get_image_count(  # type: ignore[attr-defined]
self)}"
            if ImageService.get_image_filenames(  # type: ignore[attr-defined]
self) and ImageService.get_current_image_index(  # type: ignore[attr-defined]
self) >= 0:
                img_info += f" - {os.path.basename(ImageService.get_image_filenames(  # type: ignore[attr-defined]
self)[ImageService.get_current_image_index(  # type: ignore[attr-defined]
self)])}"
            painter.drawText(10, 40, img_info)

        # Debug info
        if self.debug_mode:
            debug_info = f"Debug Mode: ON | Y-Flip: {'ON' if self.flip_y_axis else 'OFF'} | Scale to Image: {'ON' if self.scale_to_image else 'OFF'}"
            debug_info += f" | Track Dims: {self.image_width}x{self.image_height}"

            if self.background_image:
                debug_info += f" | Image: {self.background_image.width()}x{self.background_image.height()}"

            painter.drawText(10, 60, debug_info)

            # Display keyboard shortcuts
            shortcuts = "Shortcuts: [R] Reset View, [Y] Toggle Y-Flip, [S] Toggle Scale-to-Image"
            shortcuts += " | Arrow keys + Shift: Adjust alignment"
            painter.drawText(10, 80, shortcuts)

        super().paintEvent(event)

    def mousePressEvent(self, event: Any) -> None:
        """Handle mouse press to select or move points."""
        self.setFocus()
        InputService.handle_mouse_press(self, event)

    def mouseMoveEvent(self, event: Any) -> None:
        """Handle mouse movement for dragging points or panning."""
        InputService.handle_mouse_move(self, event)

    def mouseReleaseEvent(self, event: Any) -> None:
        """Handle mouse release."""
        InputService.handle_mouse_release(self, event)

    def wheelEvent(self, event: Any) -> None:
        """Handle mouse wheel for zooming via central service."""
        InputService.handle_wheel_event(self, event)

    def keyPressEvent(self, event: Any) -> None:
        """Handle key events for navigation (arrow keys, etc)."""
        InputService.handle_key_event(self, event)

    # Compatibility methods to ensure consistent interface with EnhancedCurveView

    def set_curve_data(self, curve_data: list[Any]) -> None:
        """Compatibility method for main_window.py curve_data."""
        self.points = curve_data
        self.update()

    def set_selected_indices(self, indices: list[int]) -> None:
        """Set selected point indices."""
        self.selected_points = set(indices)
        if indices:
            self.selected_point_idx = indices[0]
        else:
            self.selected_point_idx = -1
        self.update()

    def get_selected_indices(self) -> list[int]:
        """Return list of selected indices (singleton list or empty)."""
        return list(self.selected_points)

    def toggleGrid(self, enabled: bool) -> None:
        """Stub for grid toggling (not implemented in basic view)."""
        # Basic view doesn't support grid
        pass

    def toggleVelocityVectors(self, enabled: bool) -> None:
        """Stub for velocity vector toggling (not implemented in basic view)."""
        # Basic view doesn't support velocity vectors
        pass

    def toggleAllFrameNumbers(self, enabled: bool) -> None:
        """Stub for frame numbers toggling (not implemented in basic view)."""
        # Basic view doesn't support frame numbers
        pass

    def toggleCrosshair(self, enabled: bool) -> None:
        """Stub for crosshair toggling (not implemented in basic view)."""
        # Basic view doesn't support crosshair
        pass

    def centerOnSelectedPoint(self, point_idx: int) -> None:
        """Stub for centering on point (not implemented in basic view)."""
        # Basic view doesn't support centering on points
        pass

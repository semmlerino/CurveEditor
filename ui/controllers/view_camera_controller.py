"""
ViewCameraController - Manages view transformations and camera operations.

This controller extracts view/camera responsibilities from CurveViewWidget:
- Transform calculations (data ↔ screen coordinate conversion)
- Zoom operations (zoom in/out, set factor, wheel zoom)
- Pan operations (offset management)
- Centering operations (frame, selection, point)
- View fitting (background image, curve bounds)
- Transform cache management

Architecture:
- Composed into CurveViewWidget (not inherited)
- Widget delegates all view/camera operations to this controller
- Controller triggers widget.update() when view state changes
- Maintains backward compatibility via widget properties
"""

from __future__ import annotations

from typing import Protocol

from PySide6.QtCore import QPointF, SignalInstance
from PySide6.QtGui import QPixmap, QWheelEvent

from core.logger_utils import get_logger
from core.point_types import safe_extract_point
from core.type_aliases import CurveDataList
from services import get_data_service, get_transform_service
from services.transform_service import Transform, ViewState
from ui.ui_constants import (
    DEFAULT_ZOOM_FACTOR,
    MAX_ZOOM_FACTOR,
    MIN_ZOOM_FACTOR,
)

logger = get_logger("view_camera_controller")


class CurveViewProtocol(Protocol):
    """Protocol defining the interface needed by ViewCameraController.

    This avoids importing CurveViewWidget and prevents import cycles.
    """

    # Properties
    curve_data: CurveDataList
    selected_indices: set[int]
    background_image: QPixmap | None
    image_width: int
    image_height: int
    scale_to_image: bool
    flip_y_axis: bool
    manual_offset_x: float
    manual_offset_y: float

    # Signals - Qt Signal instances (bound at runtime)
    # SignalInstance represents the bound signal with emit() method
    zoom_changed: SignalInstance  # Signal(float)
    view_changed: SignalInstance  # Signal()

    # Methods
    def width(self) -> int: ...
    def height(self) -> int: ...
    def update(self) -> None: ...
    def repaint(self) -> None: ...
    def _get_display_dimensions(self) -> tuple[int, int]: ...


class ViewCameraController:
    """
    Manages view transformations and camera operations for CurveViewWidget.

    Responsibilities:
    - Coordinate transformations (data ↔ screen)
    - Zoom operations (in/out, set, wheel)
    - Pan offset management
    - Centering on frames/selections/points
    - View fitting to background/curve
    - Transform cache management

    The controller reads state from the widget (dimensions, curve data, selection)
    and modifies view state (zoom, pan) then triggers widget updates.
    """

    def __init__(self, widget: CurveViewProtocol):
        """
        Initialize ViewCameraController.

        Args:
            widget: The CurveViewWidget this controller manages
        """
        self.widget: CurveViewProtocol = widget

        # View transformation state
        self.zoom_factor: float = DEFAULT_ZOOM_FACTOR
        self.pan_offset_x: float = 0.0
        self.pan_offset_y: float = 0.0

        # Transform cache (managed internally)
        self._transform_cache: Transform | None = None

    # Core Transform API

    def get_transform(self) -> Transform:
        """
        Get the current transformation object.

        Returns:
            Transform object for coordinate mapping
        """
        if self._transform_cache is None:
            self._update_transform()
        assert self._transform_cache is not None
        return self._transform_cache

    def _update_transform(self) -> None:
        """Update the cached transformation object using TransformService for LRU caching."""
        # Calculate display dimensions using widget helper method
        # Protocol explicitly declares this method as part of the interface
        display_width, display_height = self.widget._get_display_dimensions()  # pyright: ignore[reportPrivateUsage]

        logger.info(
            f"[TRANSFORM] Display dimensions: {display_width}x{display_height}, zoom_factor: {self.zoom_factor}"
        )

        # Calculate centering offsets
        widget_width = self.widget.width()
        widget_height = self.widget.height()
        logger.info(f"[TRANSFORM] Widget dimensions: {widget_width}x{widget_height}")

        # Base scale to fit content in widget
        scale_x = widget_width / display_width if display_width > 0 else 1.0
        scale_y = widget_height / display_height if display_height > 0 else 1.0
        base_scale = min(scale_x, scale_y) * 0.9  # 90% to leave margin

        # Apply zoom on top of base scale
        total_scale = base_scale * self.zoom_factor

        # Calculate center offsets
        scaled_width = display_width * total_scale
        scaled_height = display_height * total_scale
        _ = (widget_width - scaled_width) / 2  # center_offset_x
        _ = (widget_height - scaled_height) / 2  # center_offset_y

        # Image scale factors for data-to-image mapping
        _ = display_width / self.widget.image_width  # image_scale_x
        _ = display_height / self.widget.image_height  # image_scale_y

        # Create ViewState for caching
        view_state = ViewState(
            display_width=int(display_width),
            display_height=int(display_height),
            widget_width=int(widget_width),
            widget_height=int(widget_height),
            zoom_factor=self.zoom_factor,
            offset_x=self.pan_offset_x,
            offset_y=self.pan_offset_y,
            scale_to_image=self.widget.scale_to_image,
            flip_y_axis=self.widget.flip_y_axis,
            manual_x_offset=self.widget.manual_offset_x,
            manual_y_offset=self.widget.manual_offset_y,
            background_image=self.widget.background_image,
            image_width=self.widget.image_width,
            image_height=self.widget.image_height,
        )

        # Use cached transform service - this enables 99.9% cache hits
        transform_service = get_transform_service()
        self._transform_cache = transform_service.create_transform_from_view_state(view_state)

    def data_to_screen(self, x: float, y: float) -> QPointF:
        """
        Convert data coordinates to screen coordinates.

        Args:
            x: Data X coordinate
            y: Data Y coordinate

        Returns:
            Screen position as QPointF
        """
        transform = self.get_transform()
        screen_x, screen_y = transform.data_to_screen(x, y)
        return QPointF(screen_x, screen_y)

    def screen_to_data(self, pos: QPointF) -> tuple[float, float]:
        """
        Convert screen coordinates to data coordinates.

        Args:
            pos: Screen position

        Returns:
            Data coordinates as (x, y) tuple
        """
        transform = self.get_transform()
        return transform.screen_to_data(pos.x(), pos.y())

    def invalidate_caches(self) -> None:
        """Invalidate transform cache (called when view state changes)."""
        self._transform_cache = None

    # Zoom Operations

    def set_zoom_factor(self, factor: float) -> None:
        """
        Set zoom factor with clamping to valid range.

        Args:
            factor: Desired zoom factor
        """
        old_zoom = self.zoom_factor
        self.zoom_factor = max(MIN_ZOOM_FACTOR, min(MAX_ZOOM_FACTOR, factor))

        if self.zoom_factor != old_zoom:
            self.invalidate_caches()
            self.widget.update()
            self.widget.zoom_changed.emit(self.zoom_factor)
            self.widget.view_changed.emit()

    def handle_wheel_zoom(self, event: QWheelEvent, cursor_pos: QPointF) -> None:
        """
        Handle mouse wheel zoom event, keeping cursor position stationary.

        Args:
            event: Wheel event with angle delta
            cursor_pos: Cursor position in widget coordinates
        """
        # Calculate zoom factor change
        delta = event.angleDelta().y()
        zoom_speed = 1.1
        zoom_factor = zoom_speed if delta > 0 else 1.0 / zoom_speed

        # Get current data position under mouse
        data_x, data_y = self.screen_to_data(cursor_pos)

        # Apply zoom
        old_zoom = self.zoom_factor
        self.zoom_factor = max(MIN_ZOOM_FACTOR, min(MAX_ZOOM_FACTOR, self.zoom_factor * zoom_factor))

        if self.zoom_factor != old_zoom:
            # Adjust pan to keep point under mouse stationary
            self.invalidate_caches()
            new_screen_pos = self.data_to_screen(data_x, data_y)

            offset = cursor_pos - new_screen_pos
            self.pan_offset_x += offset.x()

            # Apply Y pan offset adjustment for zoom centering
            self.apply_pan_offset_y(offset.y())

            # Invalidate caches again after pan adjustment
            self.invalidate_caches()

            self.widget.update()
            self.widget.zoom_changed.emit(self.zoom_factor)
            self.widget.view_changed.emit()

    # Centering Operations

    def center_on_point(self, x: float, y: float) -> None:
        """
        Center the view on a specific data coordinate point.

        Args:
            x: Data x-coordinate to center on
            y: Data y-coordinate to center on
        """
        # Convert data coordinates to screen position
        screen_pos = self.data_to_screen(x, y)
        widget_center = QPointF(self.widget.width() / 2, self.widget.height() / 2)

        # Calculate and apply pan offset
        offset = widget_center - screen_pos
        self.pan_offset_x += offset.x()
        self.apply_pan_offset_y(offset.y())  # Y-flip aware

        # Trigger view updates
        self.invalidate_caches()
        self.widget.update()
        self.widget.repaint()
        self.widget.view_changed.emit()

    def center_on_selection(self) -> None:
        """Center view on selected points."""
        if not self.widget.selected_indices:
            return

        logger.debug(f"[CENTER] Centering on {len(self.widget.selected_indices)} selected points")

        # Calculate center of selected points
        sum_x = sum_y = 0
        count = 0

        for idx in self.widget.selected_indices:
            if 0 <= idx < len(self.widget.curve_data):
                _, x, y, _ = safe_extract_point(self.widget.curve_data[idx])
                sum_x += x
                sum_y += y
                count += 1

        if count > 0:
            center_x = sum_x / count
            center_y = sum_y / count
            logger.debug(f"[CENTER] Data center: ({center_x:.2f}, {center_y:.2f})")

            # Log current pan offset for debugging
            old_pan_x = self.pan_offset_x
            old_pan_y = self.pan_offset_y

            # Use consolidated centering logic
            self.center_on_point(center_x, center_y)

            logger.debug(
                f"[CENTER] Pan offset changed from ({old_pan_x:.2f}, {old_pan_y:.2f}) to ({self.pan_offset_x:.2f}, {self.pan_offset_y:.2f})"
            )

    def center_on_frame(self, frame: int) -> None:
        """
        Center view on a specific frame using gap-aware position logic.

        Args:
            frame: Frame number to center on
        """
        if not self.widget.curve_data:
            logger.warning(f"[CENTER] No curve data available for frame {frame}")
            return

        # Use gap-aware position lookup through data service
        data_service = get_data_service()
        position = data_service.get_position_at_frame(self.widget.curve_data, frame)

        if position:
            x, y = position
            logger.debug(f"[CENTER] Centering on frame {frame} at ({x:.2f}, {y:.2f}) (gap-aware)")

            # Use consolidated centering logic
            self.center_on_point(x, y)

            logger.debug(f"[CENTER] View centered on frame {frame}")
        else:
            logger.warning(f"[CENTER] No position available for frame {frame}")

    # View Fitting Operations

    def fit_to_background_image(self) -> None:
        """Fit the background image fully in view."""
        if not self.widget.background_image:
            return

        # Get actual image dimensions
        img_width = self.widget.background_image.width()
        img_height = self.widget.background_image.height()
        logger.info(f"[FIT_BG] Image dimensions: {img_width}x{img_height}")

        if img_width <= 0 or img_height <= 0:
            return

        # Get widget dimensions
        widget_width = self.widget.width()
        widget_height = self.widget.height()
        logger.info(f"[FIT_BG] Widget dimensions: {widget_width}x{widget_height}")

        if widget_width <= 0 or widget_height <= 0:
            return

        # Calculate the scale needed to fit the image
        # We want to fit the entire image, so use the smaller scale
        # Apply 95% margin for visual breathing room
        margin = 0.95
        scale_x = (widget_width * margin) / img_width
        scale_y = (widget_height * margin) / img_height
        desired_scale = min(scale_x, scale_y)
        logger.info(
            f"[FIT_BG] Calculated desired_scale: {desired_scale} (scale_x={scale_x}, scale_y={scale_y}, margin={margin})"
        )

        # The transform system uses zoom_factor directly as the scale
        # So we can set zoom_factor to our desired_scale directly
        old_zoom = self.zoom_factor
        self.zoom_factor = desired_scale
        logger.info(f"[FIT_BG] Set zoom_factor: {old_zoom} -> {self.zoom_factor}")

        # Reset manual offsets
        old_manual_x, old_manual_y = self.widget.manual_offset_x, self.widget.manual_offset_y
        self.widget.manual_offset_x = 0
        self.widget.manual_offset_y = 0
        logger.info(f"[FIT_BG] Reset manual offsets: ({old_manual_x}, {old_manual_y}) -> (0, 0)")

        # Reset pan offsets - let Transform's automatic centering handle positioning
        old_pan_x, old_pan_y = self.pan_offset_x, self.pan_offset_y
        self.pan_offset_x = 0
        self.pan_offset_y = 0
        logger.info(f"[FIT_BG] Reset pan offsets: ({old_pan_x}, {old_pan_y}) -> (0, 0)")

        # Invalidate caches and update
        self.invalidate_caches()

        # Debug the transform after setting everything up
        transform = self.get_transform()
        params = transform.get_parameters()
        logger.info(f"[FIT_BG] Final transform scale: {params['scale']}")
        logger.info(f"[FIT_BG] Final center offsets: ({params['center_offset_x']}, {params['center_offset_y']})")
        logger.info(f"[FIT_BG] Final pan offsets: ({params['pan_offset_x']}, {params['pan_offset_y']})")

        # Test image positioning using helper method
        top_left_x, top_left_y = self._get_image_top_coordinates(img_height, transform)
        logger.info(f"[FIT_BG] Image top-left will be at: ({top_left_x}, {top_left_y})")

        self.widget.update()

        # Emit signals
        self.widget.view_changed.emit()
        self.widget.zoom_changed.emit(self.zoom_factor)

    def fit_to_curve(self) -> None:
        """Fit view to show all curve points."""
        if not self.widget.curve_data:
            return

        # Get bounds of all points
        min_x = min_y = float("inf")
        max_x = max_y = float("-inf")

        for point in self.widget.curve_data:
            _, x, y, _ = safe_extract_point(point)
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)

        # Calculate required zoom and offset
        data_width = max_x - min_x
        data_height = max_y - min_y

        if data_width > 0 and data_height > 0:
            # Calculate zoom to fit
            margin = 0.1  # 10% margin
            widget_width = self.widget.width() * (1 - 2 * margin)
            widget_height = self.widget.height() * (1 - 2 * margin)

            zoom_x = widget_width / data_width if data_width > 0 else 1.0
            zoom_y = widget_height / data_height if data_height > 0 else 1.0

            self.zoom_factor = min(zoom_x, zoom_y)

            # Center the data
            center_x = (min_x + max_x) / 2
            center_y = (min_y + max_y) / 2

            # Reset offsets
            self.pan_offset_x = 0
            self.pan_offset_y = 0

            self.invalidate_caches()

            # Calculate center position
            screen_center = self.data_to_screen(center_x, center_y)
            widget_center = QPointF(self.widget.width() / 2, self.widget.height() / 2)

            # Adjust pan to center
            offset = widget_center - screen_center
            self.pan_offset_x = offset.x()
            self.pan_offset_y = offset.y()

            self.invalidate_caches()
            self.widget.update()
            self.widget.view_changed.emit()
            self.widget.zoom_changed.emit(self.zoom_factor)

    def reset_view(self) -> None:
        """Reset view to default state."""
        self.zoom_factor = DEFAULT_ZOOM_FACTOR
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.widget.manual_offset_x = 0.0
        self.widget.manual_offset_y = 0.0

        self.invalidate_caches()
        self.widget.update()
        self.widget.view_changed.emit()
        self.widget.zoom_changed.emit(self.zoom_factor)

    # View State

    def get_view_state(self) -> ViewState:
        """
        Get current view state.

        Returns:
            ViewState object with current parameters
        """
        # Calculate display dimensions using widget helper method
        # Protocol explicitly declares this method as part of the interface
        display_width, display_height = self.widget._get_display_dimensions()  # pyright: ignore[reportPrivateUsage]

        return ViewState(
            display_width=display_width,
            display_height=display_height,
            widget_width=self.widget.width(),
            widget_height=self.widget.height(),
            zoom_factor=self.zoom_factor,
            offset_x=self.pan_offset_x,
            offset_y=self.pan_offset_y,
            scale_to_image=self.widget.scale_to_image,
            flip_y_axis=self.widget.flip_y_axis,
            manual_x_offset=self.widget.manual_offset_x,
            manual_y_offset=self.widget.manual_offset_y,
            background_image=self.widget.background_image,
            image_width=self.widget.image_width,
            image_height=self.widget.image_height,
        )

    # Helper Methods

    def apply_pan_offset_y(self, delta_y: float) -> None:
        """
        Apply Y pan offset with conditional inversion for Y-axis flip mode.

        When Y-axis is flipped, invert the pan direction for Y to ensure
        the curve follows the expected mouse drag direction.

        Args:
            delta_y: The Y offset to apply
        """
        if self.widget.flip_y_axis:
            self.pan_offset_y -= delta_y
        else:
            self.pan_offset_y += delta_y

    def pan(self, delta_x: float, delta_y: float) -> None:
        """
        Pan the view by screen pixel deltas.

        Updates pan offsets to move the visible area. Y panning respects
        flip_y_axis mode for natural drag behavior.

        Args:
            delta_x: Horizontal screen pixels to pan (positive = right)
            delta_y: Vertical screen pixels to pan (positive = down)
        """
        self.pan_offset_x += delta_x
        self.apply_pan_offset_y(delta_y)
        self.invalidate_caches()  # Invalidate cache when pan offsets change

    def _get_image_top_coordinates(self, img_height: float, transform: Transform) -> tuple[float, float]:
        """
        Get image top-left coordinates accounting for Y-axis flip mode.

        Args:
            img_height: Height of the image
            transform: Transform object for coordinate conversion

        Returns:
            Tuple of (x, y) screen coordinates for image top-left
        """
        if self.widget.flip_y_axis:
            # With Y-flip, image top is at Y=image_height in data space
            return transform.data_to_screen(0, img_height)
        else:
            # Without Y-flip, image top is at Y=0 in data space
            return transform.data_to_screen(0, 0)

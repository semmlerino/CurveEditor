#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
from PySide6.QtWidgets import QWidget, QRubberBand
from typing import Any, Optional, Tuple
from PySide6.QtCore import Qt, Signal
from services.centering_zoom_service import CenteringZoomService
from PySide6.QtGui import QPainter, QColor, QPen, QFont, QPainterPath, QPaintEvent
from PySide6.QtCore import QPointF
from services.input_service import InputService, CurveViewProtocol  # For type checking only
from services.protocols import ImageSequenceProtocol  # For type checking only
from keyboard_shortcuts import ShortcutManager
from services.image_service import ImageService
from services.logging_service import LoggingService
from typing import List

# Configure logger for this module
logger = LoggingService.get_logger("curve_view")


class CurveView(QWidget):  # Implements protocols through type annotations
    # Type annotations to indicate this class implements the protocols
    # without inheritance, to avoid metaclass conflicts
    _dummy: CurveViewProtocol
    _image_seq_dummy: ImageSequenceProtocol
    """Widget for displaying and editing the 2D tracking curve."""

    # --- Added for type safety and linting ---
    show_grid: bool = False
    show_velocity_vectors: bool = False
    show_all_frame_numbers: bool = False
    show_crosshair: bool = False
    grid_color: QColor | None = None
    grid_line_width: int = 1
    # Removed class-level offset_x and offset_y to avoid shadowing instance variables

    # Using float for protocol compatibility
    x_offset: float = 0.0
    y_offset: float = 0.0
    timeline_slider: Optional[Any] = None  # TODO: Use correct type if known, e.g. Optional[QSlider]
    frame_marker_label: Optional[Any] = None  # TODO: Use correct type if known, e.g. Optional[QLabel]
    # Use the type from protocols.py for better type compatibility
    from services.protocols import PointsList
    curve_data: PointsList = []
    # -----------------------------------------

    point_moved = Signal(int, float, float)  # Signal emitted when a point is moved
    point_selected = Signal(int)  # Signal emitted when a point is selected
    image_changed = Signal(int)  # Signal emitted when image changes via keyboard

    # Protocol required properties
    rubber_band: Optional[QRubberBand] = None
    rubber_band_origin: QPointF = QPointF()
    rubber_band_active: bool = False
    main_window: Any = None  # Reference to the main window, initialized later

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
        # Using float for protocol compatibility
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0
        self.image_width: int = 1920  # Default, will be updated when data is loaded
        self.image_height: int = 1080  # Default, will be updated when data is loaded
        self.setMouseTracking(True)
        self.point_radius: int = 5

        self.last_drag_pos: Optional[QPointF] = None
        self.pan_active: bool = False
        self.last_pan_pos: Optional[QPointF] = None
        # Image sequence support - implementing ImageSequenceProtocol
        self.background_image: Optional[Any] = None  # TODO: Use correct type if known, e.g. Optional[QImage]
        self.show_background: bool = True
        self.background_opacity: float = 0.7  # 0.0 to 1.0
        self.image_filenames: List[str] = []
        self.image_sequence_path: str = ""
        self.current_image_idx: int = 0
        self.scale_to_image: bool = True

        # Debug visualization attributes
        self.debug_mode: bool = True  # Enable debug visuals by default to help diagnose issues
        self.flip_y_axis: bool = True  # Default Y-axis flip setting
        self.debug_img_pos: Tuple[float, float] = (0.0, 0.0)
        self.debug_origin_pos: Tuple[float, float] = (0.0, 0.0)
        self.debug_width_pt: Tuple[float, float] = (0.0, 0.0)

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
        self.x_offset = 0.0
        self.y_offset = 0.0
        self.update()

    def toggle_y_flip(self) -> None:
        self.flip_y_axis = not getattr(self, "flip_y_axis", False)
        self.update()

    def toggle_scale_to_image(self) -> None:
        self.scale_to_image = not getattr(self, "scale_to_image", False)
        self.update()

    def toggle_debug_mode(self) -> None:
        """Toggle debug visualization mode.

        This enables detailed visual feedback about the transform system, including
        origin points, alignment markers, and detailed parameter display.
        """
        current_mode = getattr(self, "debug_mode", False)
        self.debug_mode = not current_mode

        logger.info(f"Debug mode {'enabled' if self.debug_mode else 'disabled'}")
        if self.debug_mode:
            logger.info(f"Debug state: flip_y={getattr(self, 'flip_y_axis', False)}, "
                       f"scale_to_image={getattr(self, 'scale_to_image', True)}, "
                       f"x_offset={getattr(self, 'x_offset', 0)}, y_offset={getattr(self, 'y_offset', 0)}")

        self.update()

    def setPoints(self, points: List[Tuple[int, float, float]], image_width: int = 0, image_height: int = 0, preserve_view: bool = False) -> None:
        """Set the points to display with optional dimension and view preservation parameters.

        This overload accepts the same parameters as setPoints_ext for compatibility,
        but delegates to setPoints_ext to ensure consistent behavior.
        """
        logger.info(f"setPoints called with {len(points)} points (preserve_view={preserve_view})")
        logger.info(f"Current view state: scale_to_image={getattr(self, 'scale_to_image', True)}, zoom={self.zoom_factor}, offset_x={self.offset_x}, offset_y={self.offset_y}")

        # Delegate to the extended version to ensure consistent behavior
        self.setPoints_ext(points, image_width, image_height, preserve_view)

    def setPoints_ext(self, points: list[tuple[int, float, float]], image_width: int, image_height: int, preserve_view: bool = False) -> None:
        """Set the points to display and optionally preserve the current view state."""
        logger.info("Setting points - preserve_view=%s, Points count=%d", preserve_view, len(points))
        logger.info("State BEFORE: Zoom=%.2f, OffsetX=%d, OffsetY=%d, ManualX=%d, ManualY=%d, scale_to_image=%s",
                     self.zoom_factor, self.offset_x, self.offset_y, self.x_offset, self.y_offset,
                     getattr(self, "scale_to_image", True))

        # Store original bounds for logging
        if len(self.points) > 0:
            old_min_x = min(p[1] for p in self.points)
            old_max_x = max(p[1] for p in self.points)
            old_min_y = min(p[2] for p in self.points)
            old_max_y = max(p[2] for p in self.points)
            logger.info(f"BEFORE data bounds: X=[{old_min_x:.2f}, {old_max_x:.2f}], Y=[{old_min_y:.2f}, {old_max_y:.2f}]")

        self.points = points

        # Log new data bounds
        if len(points) > 0:
            new_min_x = min(p[1] for p in points)
            new_max_x = max(p[1] for p in points)
            new_min_y = min(p[2] for p in points)
            new_max_y = max(p[2] for p in points)
            logger.info(f"AFTER data bounds: X=[{new_min_x:.2f}, {new_max_x:.2f}], Y=[{new_min_y:.2f}, {new_max_y:.2f}]")

        # Update dimensions only if they are validly provided (greater than 0)
        old_width = self.image_width
        old_height = self.image_height

        if image_width > 0:
            self.image_width = image_width
        if image_height > 0:
            self.image_height = image_height

        if old_width != self.image_width or old_height != self.image_height:
            logger.info(f"Image dimensions changed: [{old_width}x{old_height}] -> [{self.image_width}x{self.image_height}]")

        if not preserve_view:
            logger.info("Resetting view since preserve_view=False")
            self.resetView()  # Reset pan/zoom only if not preserving
        else:
            logger.info("Preserving view as requested (preserve_view=True)")

        self.update()  # Trigger repaint with new data and current/reset view state

        logger.info("Points set - State AFTER: Zoom=%.2f, OffsetX=%d, OffsetY=%d, ManualX=%d, ManualY=%d, scale_to_image=%s",
                     self.zoom_factor, self.offset_x, self.offset_y, self.x_offset, self.y_offset,
                     getattr(self, "scale_to_image", True))

    def set_image_sequence(self, path: str, filenames: list[str]) -> None:
        # Update our own properties to satisfy ImageSequenceProtocol
        self.image_sequence_path = path
        self.image_filenames = filenames
        self.current_image_idx = 0
        ImageService.set_image_sequence(self, path, filenames)
        self.update()

    def set_current_image_by_frame(self, frame: int) -> None:
        # Delegate to the service but use self as the protocol implementation
        from services.image_service import ImageService as IS
        IS.set_current_image_by_frame(self, frame)

    def set_current_image_by_index(self, idx: int) -> None:
        # Update our own property to satisfy ImageSequenceProtocol
        self.current_image_idx = idx
        ImageService.set_current_image_by_index(self, idx)
        self.update()

    def toggle_background_visible(self, visible: bool) -> None:
        """Toggle visibility of background image."""
        logger.debug(f"Toggling background visibility: {visible}")
        self.show_background = visible
        self.update()

    def toggleBackgroundVisible(self, visible: bool) -> None:
        """Protocol-required alias for toggle_background_visible."""
        self.toggle_background_visible(visible)

    def set_background_opacity(self, opacity: float) -> None:
        """Set the opacity of the background image."""
        logger.debug("Setting background opacity to %.2f", opacity)
        self.background_opacity = min(max(opacity, 0.0), 1.0)
        self.update()

    def load_current_image(self) -> None:
        # Delegate to the service but use self as the protocol implementation
        ImageService.load_current_image(self)

    def update_transform_parameters(self) -> None:
        """Explicitly update the transformation parameters used for rendering.

        This method ensures that all transformation parameters are in sync
        before rendering the curve, which helps prevent unexpected curve shifts
        and eliminates the "floating curve" effect where the curve doesn't align
        with the background image features.
        """
        logger.info("Explicitly updating transform parameters")

        # Store current values for logging
        before_scale_to_image = getattr(self, "scale_to_image", True)
        flip_y_axis = getattr(self, "flip_y_axis", False)

        # Force recalculation of any derived parameters used in paintEvent's transform_point function
        # This ensures consistent rendering coordinates between operations
        display_width = self.image_width
        display_height = self.image_height

        if self.background_image:
            display_width = self.background_image.width()
            display_height = self.background_image.height()

        # Calculate the scale factor to fit in the widget (match the logic in paintEvent exactly)
        widget_width = self.width()
        widget_height = self.height()
        scale_x = widget_width / display_width
        scale_y = widget_height / display_height
        uniform_scale = min(scale_x, scale_y) * self.zoom_factor

        # Calculate image scaling factors for accurate positioning
        # This is critical for curve-to-image alignment
        image_scale_x = 1.0
        image_scale_y = 1.0
        if before_scale_to_image:
            if self.image_width > 0 and display_width > 0:
                image_scale_x = display_width / self.image_width
            if self.image_height > 0 and display_height > 0:
                image_scale_y = display_height / self.image_height

        # Log the parameter values to verify they're consistent
        logger.info(f"Transform parameters updated: scale_to_image={before_scale_to_image}, y_flip={flip_y_axis}, "
                    f"display_dims={display_width}x{display_height}, widget_dims={widget_width}x{widget_height}, "
                    f"track_dims={self.image_width}x{self.image_height}, offsets=(x:{self.offset_x}, y:{self.offset_y}), "
                    f"manual_offsets=(x:{self.x_offset}, y:{self.y_offset}), "
                    f"uniform_scale={uniform_scale:.6f}, image_scale=({image_scale_x:.2f}, {image_scale_y:.2f})")

        # Generate a ViewState and Transform for validation
        from services.view_state import ViewState
        from services.transformation_service import TransformationService

        view_state = ViewState.from_curve_view(self)
        transform = TransformationService.calculate_transform(view_state)

        # Log transform details to help diagnose any alignment issues
        params = transform.get_parameters()
        logger.debug(f"Transform validation: scale={params['scale']:.4f}, "
                    f"center=({params['center_offset'][0]:.1f}, {params['center_offset'][1]:.1f}), "
                    f"pan=({params['pan_offset'][0]:.1f}, {params['pan_offset'][1]:.1f}), "
                    f"manual=({params['manual_offset'][0]:.1f}, {params['manual_offset'][1]:.1f})")

    # Implementation of get_selected_points to satisfy CurveViewProtocol
    def get_selected_points(self) -> List[int]:
        return list(self.selected_points)

    def resetView(self) -> None:
        """Reset view to show all points."""
        logger.debug("Resetting view - State before: Zoom=%.2f, OffsetX=%d, OffsetY=%d, ManualX=%d, ManualY=%d",
                    self.zoom_factor, self.offset_x, self.offset_y, self.x_offset, self.y_offset)

        CenteringZoomService.reset_view(self)

        logger.debug("View reset complete - State after: Zoom=%.2f, OffsetX=%d, OffsetY=%d, ManualX=%d, ManualY=%d",
                     self.zoom_factor, self.offset_x, self.offset_y, self.x_offset, self.y_offset)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the curve and points using stable transformation system."""
        logger.debug("Paint event - View state: Zoom=%.2f, OffsetX=%d, OffsetY=%d, ManualX=%d, ManualY=%d",
                    self.zoom_factor, self.offset_x, self.offset_y, self.x_offset, self.y_offset)
        if not self.points and not self.background_image:
            return

        painter = QPainter(self)  # type: ignore[arg-type]
        painter.setRenderHint(QPainter.Antialiasing)  # type: ignore[attr-defined]

        # Fill background
        painter.fillRect(self.rect(), QColor(40, 40, 40))

        # Use the TransformationService to create a stable transform
        from services.view_state import ViewState
        from services.transformation_service import TransformationService
        from services.transformation_shim import install

        # Ensure the transformation system is installed
        install(self)

        # Get current view state
        view_state = ViewState.from_curve_view(self)

        # Create stable transform for consistent coordinate mapping
        transform = TransformationService.calculate_transform(view_state)

        # Log transform parameters for debugging
        transform_params = transform.get_parameters()
        logger.debug(f"Using stable transform: scale={transform_params['scale']:.4f}, "
                    f"center=({transform_params['center_offset'][0]:.1f}, {transform_params['center_offset'][1]:.1f}), "
                    f"pan=({transform_params['pan_offset'][0]:.1f}, {transform_params['pan_offset'][1]:.1f}), "
                    f"manual=({transform_params['manual_offset'][0]:.1f}, {transform_params['manual_offset'][1]:.1f}), "
                    f"flip_y={transform_params['flip_y']}")

        # Define transform_point function using the stable transform
        def transform_point(x: float, y: float) -> tuple[float, float]:
            return transform.apply(x, y)

        # Draw background image if available
        if self.show_background and self.background_image:
            # Get current transformation parameters
            display_width = self.background_image.width()
            display_height = self.background_image.height()

            # Get the transform parameters for positioning
            params = transform.get_parameters()
            scale = params['scale']
            center_offset_x, center_offset_y = params['center_offset']
            pan_offset_x, pan_offset_y = params['pan_offset']
            # Use params['manual_offset'] directly where needed instead of separate variables
            image_scale_x, image_scale_y = params.get('image_scale', (1.0, 1.0))
            scale_to_image = params.get('scale_to_image', True)

            # Calculate scaled dimensions for the image
            scaled_width = display_width * scale
            scaled_height = display_height * scale

            # Get the image position by directly transforming the origin point (0,0)
            # using the SAME transform method used for curve points
            # This ensures the image and curve use identical transformation logic
            img_x, img_y = transform.apply(0, 0)

            # For debugging, calculate where several key points would appear on screen:
            # 1. Data origin (0,0) - this is now the same as the image position since we're using the same transform
            origin_x, origin_y = img_x, img_y  # img_x, img_y already calculated using transform.apply(0, 0)

            # 2. Data origin (0,0) without image scaling (for comparison only)
            origin_no_scale_x, origin_no_scale_y = transform.apply(0, 0, use_image_scale=False)

            # 3. Data point at image dimensions (width, height)
            width_pt_x, width_pt_y = transform.apply(self.image_width, self.image_height)

            # Log these points for debugging
            logger.debug(f"Image position = Data origin: ({img_x:.1f}, {img_y:.1f}) - using same transform")
            logger.debug(f"Data origin (without scaling): ({origin_no_scale_x:.1f}, {origin_no_scale_y:.1f})")
            logger.debug(f"Data point at image dims: ({width_pt_x:.1f}, {width_pt_y:.1f})")

            # Calculate offset between with/without scaling for reference
            scale_diff_x = img_x - origin_no_scale_x
            scale_diff_y = img_y - origin_no_scale_y
            logger.debug(f"Difference with vs. without scaling: ({scale_diff_x:.1f}, {scale_diff_y:.1f})")
            logger.debug(f"Scale to image setting: {getattr(self, 'scale_to_image', True)}")

            # Store values for debug visualization
            self.debug_img_pos = (img_x, img_y)
            self.debug_origin_pos = (origin_x, origin_y)
            self.debug_origin_no_scale_pos = (origin_no_scale_x, origin_no_scale_y)
            self.debug_width_pt = (width_pt_x, width_pt_y)

            # Draw the image
            painter.setOpacity(self.background_opacity)
            painter.drawPixmap(int(img_x), int(img_y), int(scaled_width), int(scaled_height), self.background_image)
            painter.setOpacity(1.0)

            # Debugging visuals
            if self.debug_mode:
                # Show alignment info with transform details
                painter.setPen(QPen(QColor(255, 100, 100), 1))
                painter.drawText(10, 100, f"Manual Alignment: X-offset: {self.x_offset}, Y-offset: {self.y_offset}")
                painter.drawText(10, 120, f"Transform Scale: {scale:.4f}, Center: ({center_offset_x:.1f}, {center_offset_y:.1f})")
                painter.drawText(10, 140, f"Pan Offset: ({pan_offset_x:.1f}, {pan_offset_y:.1f})")
                painter.drawText(10, 160, f"Final Image Pos: ({img_x:.1f}, {img_y:.1f})")

                # Add more debugging info about image scaling
                if scale_to_image:
                    painter.drawText(10, 180, f"Image Scale: ({image_scale_x:.2f}, {image_scale_y:.2f}), Scale to Image: ON")
                    painter.drawText(10, 195, f"Using identical transform for both curve and image")
                else:
                    painter.drawText(10, 180, f"Image Scale: ({image_scale_x:.2f}, {image_scale_y:.2f}), Scale to Image: OFF")

                painter.drawText(10, 200, f"Adjust with arrow keys + Shift/Ctrl")

                # Add alignment grid crosshair for checking if curve is properly aligned with the background
                # Draw at the center of the image
                center_x = img_x + (scaled_width / 2)
                center_y = img_y + (scaled_height / 2)

                # Draw crosshair lines
                painter.setPen(QPen(QColor(255, 255, 0), 1, Qt.PenStyle.DashLine))
                painter.drawLine(center_x - 50, center_y, center_x + 50, center_y)  # Horizontal line
                painter.drawLine(center_x, center_y - 50, center_x, center_y + 50)  # Vertical line

                # Draw text label
                painter.setPen(QPen(QColor(255, 255, 0), 1))
                painter.drawText(center_x + 10, center_y - 10, "Center")

                # Draw comprehensive alignment debug visualization
                if hasattr(self, 'debug_origin_pos'):
                    origin_x, origin_y = self.debug_origin_pos

                    # Draw a large crosshair at the data origin with scaling
                    painter.setPen(QPen(QColor(0, 255, 0), 2, Qt.PenStyle.DashLine))
                    painter.drawLine(int(origin_x - 30), int(origin_y), int(origin_x + 30), int(origin_y))  # Horizontal
                    painter.drawLine(int(origin_x), int(origin_y - 30), int(origin_x), int(origin_y + 30))  # Vertical

                    # Draw a circle at the origin
                    painter.setPen(QPen(QColor(0, 255, 0), 2))
                    painter.drawEllipse(int(origin_x - 5), int(origin_y - 5), 10, 10)

                    # Label the origin (with scaling)
                    painter.drawText(int(origin_x + 15), int(origin_y - 15), "Data Origin (with scaling)")

                    # Draw the non-scaled origin point (blue)
                    if hasattr(self, 'debug_origin_no_scale_pos'):
                        origin_no_scale_x, origin_no_scale_y = self.debug_origin_no_scale_pos

                        # Draw crosshair for non-scaled origin
                        painter.setPen(QPen(QColor(0, 0, 255), 2, Qt.PenStyle.DashLine))
                        painter.drawLine(int(origin_no_scale_x - 30), int(origin_no_scale_y), int(origin_no_scale_x + 30), int(origin_no_scale_y))
                        painter.drawLine(int(origin_no_scale_x), int(origin_no_scale_y - 30), int(origin_no_scale_x), int(origin_no_scale_y + 30))

                        # Draw square at non-scaled origin
                        painter.setPen(QPen(QColor(0, 0, 255), 2))
                        painter.drawRect(int(origin_no_scale_x - 5), int(origin_no_scale_y - 5), 10, 10)

                        # Label the non-scaled origin
                        painter.drawText(int(origin_no_scale_x + 15), int(origin_no_scale_y - 15), "Data Origin (no scaling)")

                    # Calculate and show offset between image position and data origins
                    if hasattr(self, 'debug_img_pos'):
                        img_x, img_y = self.debug_img_pos
                        dx = origin_x - img_x
                        dy = origin_y - img_y

                        # Show offset information
                        painter.setPen(QPen(QColor(255, 255, 255), 1))
                        painter.drawText(10, 220, f"Origin-Image Offset (scaled): ({dx:.1f}, {dy:.1f})")

                        if hasattr(self, 'debug_origin_no_scale_pos'):
                            # Calculate no-scale offset
                            no_scale_dx = origin_no_scale_x - img_x
                            no_scale_dy = origin_no_scale_y - img_y
                            painter.drawText(10, 240, f"Origin-Image Offset (no scaling): ({no_scale_dx:.1f}, {no_scale_dy:.1f})")

                        painter.drawText(10, 260, f"Y-flip: {getattr(self, 'flip_y_axis', False)}, Scale-to-image: {getattr(self, 'scale_to_image', True)}")

                        # Draw a line from image corner to each origin point
                        painter.setPen(QPen(QColor(255, 0, 0), 1, Qt.PenStyle.DashLine))
                        painter.drawLine(int(img_x), int(img_y), int(origin_x), int(origin_y))

                        if hasattr(self, 'debug_origin_no_scale_pos'):
                            painter.setPen(QPen(QColor(0, 0, 255), 1, Qt.PenStyle.DashLine))
                            painter.drawLine(int(img_x), int(img_y), int(origin_no_scale_x), int(origin_no_scale_y))

                        # Show the image width point if available
                        if hasattr(self, 'debug_width_pt'):
                            width_pt_x, width_pt_y = self.debug_width_pt
                            painter.setPen(QPen(QColor(255, 165, 0), 2))
                            painter.drawEllipse(int(width_pt_x - 5), int(width_pt_y - 5), 10, 10)
                            painter.drawText(int(width_pt_x + 10), int(width_pt_y - 10), f"({self.image_width}, {self.image_height})")


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
        self.setFocus(Qt.FocusReason.MouseFocusReason)
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

    def selectPointByIndex(self, idx: int) -> None:
        """Protocol-required method to select a point by index."""
        self.set_selected_indices([idx])
        self.point_selected.emit(idx)

    def get_selected_indices(self) -> list[int]:
        """Return list of selected indices (singleton list or empty)."""
        return list(self.selected_points)

    def toggleGrid(self, enabled: bool) -> None:
        """Stub for grid toggling (not implemented in basic view)."""
        # Basic view doesn't support grid
        pass

    def toggleVelocityVectors(self, enabled: bool) -> None:
        """Toggle display of velocity vectors."""
        self.show_velocity_vectors = enabled
        self.update()
        
    def setVelocityData(self, velocities: Any) -> None:
        """Set velocity data for visualization.
        
        Args:
            velocities: List of velocity data points
        """
        self.velocity_data = velocities
        self.update()

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

    # Implementation that satisfies both Protocol and QWidget requirements
    # Note: using type: ignore to suppress parameter name mismatch
    def setCursor(self, cursor: Qt.CursorShape) -> None:  # type: ignore[override]
        """Set the cursor to the specified shape."""
        # Call parent implementation without annotating parameter name
        QWidget.setCursor(self, cursor)

    def unsetCursor(self) -> None:
        """Unset the cursor as required by CurveViewProtocol."""
        super().unsetCursor()

    # Additional methods required by CurveViewProtocol
    def findPointAt(self, pos: QPointF) -> int:
        """Find point at the given position."""
        from services.curve_service import CurveService
        result = CurveService.find_point_at(self, pos.x(), pos.y())
        # Ensure we always return an int as required by the protocol
        return result if result is not None else -1

    def get_point_data(self, idx: int) -> Tuple[int, float, float, Optional[str]]:
        """Get point data for the given index."""
        if 0 <= idx < len(self.points):
            point = self.points[idx]
            # Add 'interpolated' tag as fourth element if applicable
            if len(point) > 3 and point[3] == 'interpolated':
                return (point[0], point[1], point[2], 'interpolated')
            return (point[0], point[1], point[2], None)
        return (-1, 0.0, 0.0, None)

    def toggle_point_interpolation(self, idx: int) -> None:
        """Toggle interpolation status of a point."""
        if 0 <= idx < len(self.points):
            point = list(self.points[idx])
            if len(point) > 3 and point[3] == 'interpolated':
                # Remove interpolated tag
                point = point[:3]
            else:
                # Add interpolated tag
                if len(point) <= 3:
                    point.append('interpolated')
                else:
                    point[3] = 'interpolated'
            self.points[idx] = tuple(point)
            self.update()

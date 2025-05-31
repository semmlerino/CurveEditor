#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Curve view widget for displaying and editing 2D tracking curves.

This module provides the CurveView widget which is the central component
for visualizing and editing tracking curves in the 3DE4 Curve Editor.
It handles curve display, point manipulation, image background display,
and user interactions.

The widget implements both CurveViewProtocol and ImageSequenceProtocol
to ensure interface compatibility across the application.

Classes:
    CurveView: Main widget for curve display and editing.

Example:
    from curve_view import CurveView

    # Create curve view widget
    curve_view = CurveView(parent_widget)

    # Set curve data
    curve_view.set_curve_data(tracking_points)

    # Enable visualization options
    curve_view.show_grid = True
    curve_view.show_velocity_vectors = True

Note:
    This widget uses Qt's painting system for rendering and handles
    various input events for interactive editing.

"""
# Standard library imports
import os
from typing import Any, Optional, Tuple, List, Dict, Set, Union, cast

# Third-party imports
from PySide6.QtCore import Qt, Signal, QPointF, QRect, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QPixmap, QPaintEvent, QFont, QMouseEvent, QWheelEvent
from PySide6.QtWidgets import (
    QWidget, QRubberBand, QLabel, QSlider, QApplication, QStyleOption, QStyle
)

# Local imports
from keyboard_shortcuts import ShortcutManager
from services.centering_zoom_service import CenteringZoomService
from services.image_service import ImageService
from services.input_service import InputService
from services.logging_service import LoggingService
from services.protocols import (
    ImageSequenceProtocol,
    PointsList,
    CurveViewProtocol,
    MainWindowProtocol,
    PointTuple,
    PointTupleWithStatus
)

# Configure logger for this module
logger = LoggingService.get_logger("curve_view")


class CurveView(QWidget):  # Implements CurveViewProtocol for type checking
    """Widget for displaying and editing the 2D tracking curve.

    Implements CurveViewProtocol and ImageSequenceProtocol to provide
    a comprehensive interface for curve visualization and editing. Handles
    rendering of tracking points, background images, grid overlays, and
    various visualization options.

    Attributes:
        show_grid: Whether to display grid overlay.
        show_velocity_vectors: Whether to display velocity vectors.
        show_all_frame_numbers: Whether to show frame numbers for all points.
        show_crosshair: Whether to display crosshair at cursor position.
        grid_color: Color used for grid lines.
        grid_line_width: Width of grid lines in pixels.
        background_opacity: Opacity of background image (0.0-1.0).
        point_radius: Radius of point markers in pixels.
        nudge_increment: Current increment for nudging operations.
        current_increment_index: Index in available_increments list.
        available_increments: List of available nudge increment values.
        x_offset: Horizontal offset for curve display.
        y_offset: Vertical offset for curve display.
        zoom_factor: Current zoom level.
        offset_x: Horizontal pan offset.
        offset_y: Vertical pan offset.
        flip_y_axis: Whether to flip Y-axis (image vs math coordinates).
        scale_to_image: Whether to scale curve to image dimensions.
        selected_point_idx: Index of currently selected point.
        points: List of curve points.
        selected_points: Set of selected point indices.
        curve_data: Complete curve data including status.
        background_image: Optional background image pixmap.

    Signals:
        point_selected: Emitted when a point is selected (index).
        point_moved: Emitted when a point is moved (index, x, y).
        image_changed: Emitted when background image changes (index).
        selection_changed: Emitted when selection changes (indices).

    Example:
        curve_view = CurveView()
        curve_view.set_curve_data(tracking_data)
        curve_view.show_grid = True
        curve_view.point_selected.connect(on_point_selected)

    """
    # Protocol required attributes - defined as instance variables in __init__
    show_grid: bool
    show_velocity_vectors: bool
    show_all_frame_numbers: bool
    show_crosshair: bool
    grid_color: QColor
    grid_line_width: int
    background_opacity: float
    point_radius: int
    nudge_increment: float
    current_increment_index: int
    available_increments: List[float]

    # Position and transform
    x_offset: float
    y_offset: float
    zoom_factor: float
    offset_x: float
    offset_y: float
    flip_y_axis: bool
    scale_to_image: bool
    selected_point_idx: int

    # Data and state
    points: PointsList
    selected_points: Set[int]
    curve_data: PointsList
    background_image: Optional[QPixmap]

    # UI elements
    frame_marker_label: Optional[QLabel]
    timeline_slider: Optional[QSlider]
    main_window: Optional[MainWindowProtocol]

    # Selection
    selection_rect: QRect

    # Signals
    point_selected = Signal(int)  # point_index
    point_moved = Signal(int, float, float)  # index, x, y
    image_changed = Signal(int)  # Signal emitted when image changes via keyboard
    selection_changed = Signal(list)  # Signal emitted when selection changes

    # Image sequence properties
    image_sequence_path: str = ""
    image_filenames: List[str] = []
    current_image_idx: int = 0
    image_width: int = 0
    image_height: int = 0
    show_background: bool = True

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """Initialize the CurveView widget.

        Sets up the widget with default values for all visualization options,
        initializes data structures, and configures the widget for user interaction.

        Args:
            parent: Optional parent widget. Defaults to None.

        """
        super().__init__(parent)

        # Initialize protocol required attributes
        self.show_grid = False
        self.show_velocity_vectors = False
        self.show_all_frame_numbers = False
        self.show_crosshair = False
        self.grid_color = QColor(200, 200, 200)
        self.grid_line_width = 1
        self.background_opacity = 1.0
        self.point_radius = 5
        self.nudge_increment = 1.0
        self.current_increment_index = 0
        self.available_increments = [0.1, 0.5, 1.0, 5.0, 10.0]

        # Initialize position and transform
        self.x_offset = 0.0
        self.y_offset = 0.0
        self.zoom_factor = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.flip_y_axis = True
        self.scale_to_image = True
        self.selected_point_idx = -1

        # Initialize data and state
        self.points = []
        self.selected_points = set()
        self.curve_data = []
        self.background_image = None

        # Initialize shortcuts dictionary for keyboard shortcuts
        self.shortcuts = {}

        # Initialize UI elements
        self.frame_marker_label = None
        self.timeline_slider = None
        self.main_window = None

        # Initialize selection
        self.selection_rect = QRect()

        # Set up the widget
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

    # Protocol required properties
    rubber_band: Optional[QRubberBand] = None
    rubber_band_origin: QPointF = QPointF(0, 0)  # Initialize with default value to satisfy protocol
    rubber_band_active: bool = False
    main_window: Any = None  # Reference to the main window, initialized later

    def __init__(self, parent: Optional[Any] = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(800, 600)
        # Set focus policy using correct enum for PySide6
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # type: ignore[attr-defined]
        self.points: PointsList = []  # Main points list, protocol-compliant
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
        self.background_image: Optional[QPixmap] = None
        self.show_background: bool = True
        self.background_opacity: float = 0.7  # 0.0 to 1.0
        self.image_filenames: List[str] = []
        self.image_sequence_path: str = ""
        self.current_image_idx: int = 0
        self.scale_to_image: bool = True

        # Initialize shortcuts dictionary for keyboard shortcuts
        self.shortcuts = {}

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
        """Reset the view to default state.

        Resets zoom to 1.0 and clears all offsets, returning the view
        to its initial state. This is typically called via keyboard shortcut.

        """
        self.resetView()
        self.x_offset = 0.0
        self.y_offset = 0.0
        self.update()

    def toggle_y_flip(self) -> None:
        """Toggle Y-axis flipping between image and mathematical coordinates.

        Switches between image coordinates (Y increases downward) and
        mathematical coordinates (Y increases upward). Updates the view
        immediately after toggling.

        """
        self.flip_y_axis = not getattr(self, "flip_y_axis", False)
        self.update()

    def toggle_scale_to_image(self) -> None:
        """Toggle whether curve points are scaled to image dimensions.

        When enabled, curve coordinates are interpreted relative to the
        image dimensions. When disabled, coordinates are used as-is.
        Updates the view immediately after toggling.

        """
        self.scale_to_image = not getattr(self, "scale_to_image", False)
        self.update()

    def toggle_debug_mode(self) -> None:
        """Toggle debug visualization mode.

        Enables or disables detailed visual feedback about the transform system,
        including origin points, alignment markers, and detailed parameter display.
        Logs the current debug state when toggled.

        Side Effects:
            Updates self.debug_mode flag and triggers view update.
            Logs debug state information when enabled.

        """
        current_mode = getattr(self, "debug_mode", False)
        self.debug_mode = not current_mode

        logger.info(f"Debug mode {'enabled' if self.debug_mode else 'disabled'}")
        if self.debug_mode:
            logger.info(f"Debug state: flip_y={getattr(self, 'flip_y_axis', False)}, "
                       f"scale_to_image={getattr(self, 'scale_to_image', True)}, "
                       f"x_offset={getattr(self, 'x_offset', 0)}, y_offset={getattr(self, 'y_offset', 0)}")

        self.update()

    def setPoints(self, points: PointsList, image_width: int = 0, image_height: int = 0, preserve_view: bool = False) -> None:
        """Set the points to display with optional dimension and view preservation parameters.

        This overload accepts the same parameters as setPoints_ext for compatibility,
        but delegates to setPoints_ext to ensure consistent behavior.
        """
        logger.info(f"setPoints called with {len(points)} points (preserve_view={preserve_view})")
        logger.info(f"Current view state: scale_to_image={getattr(self, 'scale_to_image', True)}, zoom={self.zoom_factor}, offset_x={self.offset_x}, offset_y={self.offset_y}")

        # Delegate to the extended version to ensure consistent behavior
        self.setPoints_ext(points, image_width, image_height, preserve_view)

    def setPoints_ext(self, points: PointsList, image_width: int, image_height: int, preserve_view: bool = False) -> None:
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
        # Update our own properties
        self.image_sequence_path = path
        self.image_filenames = filenames
        # Load the image using ImageService
        # Using type ignore as the CurveView actually implements all required methods from ImageSequenceProtocol
        ImageService.set_image_sequence(self, path, filenames)  # type: ignore[arg-type]  # type: ignore[assignment]
        self.update()

    def set_current_image_by_frame(self, frame: int) -> None:
        # Use the ImageService to set the current image by frame
        # Using type ignore as CurveView implements required methods from CurveViewProtocol
        ImageService.set_current_image_by_frame(self, frame)  # type: ignore[arg-type]  # type: ignore[assignment]

    def set_current_image_by_index(self, idx: int) -> None:
        # Use the ImageService to set the current image by index
        # Using type ignore as CurveView implements required methods from ImageSequenceProtocol
        ImageService.set_current_image_by_index(self, idx)  # type: ignore[arg-type]  # type: ignore[assignment]
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
        # Using type ignore as the CurveView actually implements ImageSequenceProtocol
        ImageService.load_current_image(self)  # type: ignore[arg-type]  # type: ignore[assignment]

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

        # Generate a ViewState and Transform using the unified transformation system for validation
        from services.view_state import ViewState
        from services.unified_transformation_service import UnifiedTransformationService

        view_state = ViewState.from_curve_view(self)
        transform = UnifiedTransformationService.from_view_state(view_state)

        # Log transform details to help diagnose any alignment issues
        params = transform.get_parameters()
        logger.debug(f"Transform validation: scale={params['scale']:.4f}, "
                    f"center=({params['center_offset'][0]:.1f}, {params['center_offset'][1]:.1f}), "
                    f"pan=({params['pan_offset'][0]:.1f}, {params['pan_offset'][1]:.1f}), "
                    f"manual=({params['manual_offset'][0]:.1f}, {params['manual_offset'][1]:.1f})")

    # Implementation of get_selected_points to satisfy CurveViewProtocol
    def get_selected_points(self) -> list[int]:
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

        # Use the UnifiedTransformationService to create a stable transform
        from services.unified_transformation_service import UnifiedTransformationService

        # Create stable transform for consistent coordinate mapping
        transform = UnifiedTransformationService.from_curve_view(self)

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
            origin_no_scale_x, origin_no_scale_y = origin_x, origin_y

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
                    painter.drawText(10, 195, "Using identical transform for both curve and image")
                else:
                    painter.drawText(10, 180, f"Image Scale: ({image_scale_x:.2f}, {image_scale_y:.2f}), Scale to Image: OFF")

                painter.drawText(10, 200, "Adjust with arrow keys + Shift/Ctrl")

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
                            # Add implementation for this condition if needed
                            pass
            else:
                # Display scale info when not scaling to image
                painter.drawText(10, 180, f"Image Scale: ({image_scale_x:.2f}, {image_scale_y:.2f}), Scale to Image: OFF")

        transformed_points: list[tuple[int, int, float, float, tuple[int, float, float] | tuple[int, float, float, bool], bool]] = []
        for i, point in enumerate(self.points):
            frame: int
            x: float
            y: float
            is_interpolated: bool = False
            if len(point) == 3:
                frame, x, y = point
            elif len(point) == 4:
                frame, x, y, is_interpolated = point  # type: ignore
            else:
                continue
            tx: float
            ty: float
            tx, ty = transform_point(x, y)
            # Use type ignore here since we know the runtime type compatibility is maintained
            # but the static type checker can't verify the complex union types
            transformed_points.append((i, frame, tx, ty, point, is_interpolated))  # type: ignore[arg-type]

        if not transformed_points:
            return

        for item in transformed_points:
            i, frame, tx, ty, point, is_interpolated = item
            # i: int; frame: int; tx: float; ty: float; point: tuple[int, float, float] | tuple[int, float, float, bool]; is_interpolated: bool
            if i in self.selected_points:
                color = QColor(255, 255, 0)
                painter.setPen(QPen(color, 6))
                painter.drawPoint(int(tx), int(ty))
                if i == self.selected_point_idx:
                    painter.setPen(QPen(QColor(255, 0, 0), 10))
                    painter.drawPoint(int(tx), int(ty))
            elif is_interpolated:
                color = QColor(150, 150, 255)
                painter.setPen(QPen(color, 6))
                painter.drawPoint(int(tx), int(ty))
            else:
                color = QColor(0, 255, 0)
                painter.setPen(QPen(color, 6))
                painter.drawPoint(int(tx), int(ty))

            # Draw frame number or type/status for selected points
            if i in self.selected_points:
                info_font = QFont()
                info_font.setPointSize(8)
                painter.setFont(info_font)
                painter.setPen(QPen(QColor(200, 200, 100), 1))
                point_type = 'normal'
                if len(point) >= 4:
                    point_type = str(point[3])
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
                        pass  # No type info for this point
            if selected_types:
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

    def set_curve_data(self, curve_data: PointsList) -> None:
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




    def centerOnSelectedPoint(self) -> bool:
        # Protocol expects no argument and returns bool
        # For compatibility, always return False (not centered)
        return False

# ... (rest of the code remains the same)
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

    # Additional protocol-required methods for full compliance
    def setCurrentImageByIndex(self, idx: int) -> None:
        self.set_current_image_by_index(idx)

    def setImageSequence(self, path: str, filenames: list[str]) -> None:
        self.set_image_sequence(path, filenames)

    def setBackgroundOpacity(self, opacity: float) -> None:
        self.set_background_opacity(opacity)

    nudge_increment: float = 1.0
    current_increment_index: int = 0
    available_increments: list[float] = [0.1, 0.5, 1.0, 2.0, 5.0]
    selection_rect: Any = None

    # Additional methods required by CurveViewProtocol
    def findPointAt(self, pos: QPointF) -> int:
        """Find point at the given position."""
        from services.curve_service import CurveService
        result = CurveService.find_point_at(self, pos.x(), pos.y())
        # Ensure we always return an int as required by the protocol
        return result if result is not None else -1

    def get_point_data(self, idx: int) -> Tuple[int, float, float, str | None]:
        """Get point data for the given index."""
        if 0 <= idx < len(self.points):
            point = self.points[idx]
            # Base point data without interpolation flag
            frame, x, y = point[0], point[1], point[2]

            # Check fourth element if it exists, using # type: ignore to bypass the type checking issue
            # since we know the actual runtime types are compatible with our checks
            if len(point) > 3:
                fourth_element = point[3]  # type: ignore[assignment]
                # Check if it's interpolated
                if fourth_element is True or fourth_element == 'interpolated':  # type: ignore[comparison-overlap]
                    return (frame, x, y, 'interpolated')
            return (frame, x, y, None)
        return (-1, 0.0, 0.0, None)

    def toggle_point_interpolation(self, idx: int) -> None:
        """Toggle interpolation status of a point."""
        if 0 <= idx < len(self.points):
            point = list(self.points[idx])
            if len(point) == 4 and isinstance(point[3], bool) and point[3]:
                # If already interpolated, remove the flag
                self.points[idx] = (int(point[0]), float(point[1]), float(point[2]))
            else:
                # Add or set interpolated flag as True (protocol expects bool)
                self.points[idx] = (int(point[0]), float(point[1]), float(point[2]), True)
            self.update()

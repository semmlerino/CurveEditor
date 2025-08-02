#!/usr/bin/env python
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
# Modern Python 3.10+ type annotations (kept for remaining usage)

# Third-party imports
from PySide6.QtCore import QPointF, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QCursor,
    QFontMetrics,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
    QShowEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import QLabel, QRubberBand, QSlider, QWidget

import ui.ui_constants as ui_constants
from components.curve_view_components import CurveImageSequence, CurvePointManager, CurveViewState, CurveVisualization
from core.protocols import MainWindowProtocol, PointsList
from rendering.curve_renderer import CurveRenderer
from services.centering_zoom_service import CenteringZoomService
from services.curve_service import CurveService
from services.image_service import ImageService
from services.input_service import InputService
from services.logging_service import LoggingService
from services.transformation_service import TransformationService
from services.view_state import ViewState

# Local imports
from ui.keyboard_shortcuts import ShortcutManager
from ui.ui_scaling import UIScaling

# Configure logger for this module
logger = LoggingService.get_logger("curve_view")


class CurveView(QWidget):  # Implements CurveViewProtocol and ImageSequenceProtocol via structural typing
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
        available_increments: list of available nudge increment values.
        x_offset: Horizontal offset for curve display.
        y_offset: Vertical offset for curve display.
        zoom_factor: Current zoom level.
        offset_x: Horizontal pan offset.
        offset_y: Vertical pan offset.
        flip_y_axis: Whether to flip Y-axis (image vs math coordinates).
        scale_to_image: Whether to scale curve to image dimensions.
        selected_point_idx: Index of currently selected point.
        points: list of curve points.
        selected_points: set of selected point indices.
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
    available_increments: list[float]

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
    selected_points: set[int]
    curve_data: PointsList
    background_image: QPixmap | None

    # UI elements
    frame_marker_label: QLabel | None
    timeline_slider: QSlider | None
    main_window: MainWindowProtocol | None = None
    velocity_data: list[tuple[float, float]] = []
    last_action_was_fit: bool = False

    # Selection
    selection_rect: QRect

    # Component type annotations
    _visualization: CurveVisualization
    _image_sequence: CurveImageSequence
    _view_state: CurveViewState
    _point_manager: CurvePointManager
    _curve_renderer: "CurveRenderer"  # Forward reference

    # Interaction state annotations
    drag_active: bool
    pan_active: bool
    debug_mode: bool

    # Signals
    point_selected: Signal = Signal(int)  # point_index
    point_moved: Signal = Signal(int, float, float)  # index, x, y
    image_changed: Signal = Signal(int)  # Signal emitted when image changes via keyboard
    selection_changed: Signal = Signal(list)  # Signal emitted when selection changes

    # Image sequence properties
    image_sequence_path: str = ""
    image_filenames: list[str] = []
    current_image_idx: int = 0
    image_width: int = 0
    image_height: int = 0
    show_background: bool = True

    # Protocol required properties
    rubber_band: QRubberBand | None = None
    rubber_band_origin: QPointF = QPointF(0, 0)  # Initialize with default value to satisfy protocol
    rubber_band_active: bool = False

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the CurveView widget.

        Sets up the widget with default values for all visualization options,
        initializes data structures, and configures the widget for user interaction.

        Args:
            parent: Optional parent widget. Defaults to None.

        """
        super().__init__(parent)

        # Widget setup and size policy
        self.setMinimumSize(UIScaling.scale_px(400), UIScaling.scale_px(200))  # Much smaller minimum, let it expand
        from PySide6.QtWidgets import QSizePolicy

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setAcceptDrops(True)

        # Initialize components (Phase 1, 2, 3 & 4 refactoring)
        self._visualization = CurveVisualization()
        self._image_sequence = CurveImageSequence()
        self._view_state = CurveViewState()
        self._point_manager = CurvePointManager()

        # Initialize rendering system
        # Import here to avoid circular imports
        from rendering.curve_renderer import CurveRenderer

        self._curve_renderer = CurveRenderer()

        # Initialize protocol required attributes for visualization (delegate to component)
        self.show_grid = self._visualization.show_grid
        self.show_velocity_vectors = self._visualization.show_velocity_vectors
        self.show_all_frame_numbers = self._visualization.show_all_frame_numbers
        self.show_crosshair = self._visualization.show_crosshair
        import ui.ui_constants as ui_constants

        grid_rgba = ui_constants.CURVE_COLORS["grid_minor"]
        self.grid_color = QColor(*grid_rgba)
        self.grid_line_width = 1
        self.background_opacity = 0.7  # 0.0 to 1.0
        self.point_radius = 5
        self.nudge_increment = 1.0
        self.current_increment_index = 0
        self.available_increments = [0.1, 0.5, 1.0, 5.0, 10.0]

        # Initialize position and transform (Phase 3: delegate to view state component)
        # View state is now managed by CurveViewState component
        # Properties below provide backward compatibility
        self.x_offset = 0.0
        self.y_offset = 0.0
        self.zoom_factor = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.flip_y_axis = True
        self.scale_to_image = False
        self.selected_point_idx = -1

        # Initialize data and state (Phase 4: delegate to point manager)
        # Point data is now managed by CurvePointManager component
        # Properties below provide backward compatibility
        self.points = []
        self.selected_points = set()
        self.curve_data = []
        self.background_image = None
        self.drag_active = False

        # Image sequence support - implementing ImageSequenceProtocol (delegate to component)
        self.show_background = self._image_sequence.show_background
        self.image_filenames = self._image_sequence.image_filenames
        self.image_sequence_path = self._image_sequence.image_sequence_path
        self.current_image_idx = self._image_sequence.current_image_idx
        self.background_opacity = self._image_sequence.background_opacity
        self.image_width = 1920  # Default, will be updated when data is loaded
        self.image_height = 1080  # Default, will be updated when data is loaded

        # Mouse and interaction state
        self.last_drag_pos: QPointF | None = None
        self.pan_active = False
        self.last_pan_pos: QPointF | None = None

        # Initialize UI elements
        self.frame_marker_label = None
        self.timeline_slider = None

        # Initialize selection
        self.selection_rect = QRect()

        # Initialize shortcuts dictionary for keyboard shortcuts
        from PySide6.QtGui import QShortcut

        self.shortcuts: dict[str, QShortcut] = {}

        # Debug visualization attributes
        self.debug_mode = False  # Debug visuals disabled by default for clean UI
        self.debug_img_pos: tuple[float, float] = (0.0, 0.0)
        self.debug_origin_pos: tuple[float, float] = (0.0, 0.0)
        self.debug_width_pt: tuple[float, float] = (0.0, 0.0)

        # Register shortcuts via ShortcutManager
        self._register_shortcuts()

        # Flag to track if we need to fit content on first proper paint
        self._needs_initial_fit: bool = False
        self._has_fitted: bool = False

    def _register_shortcuts(self) -> None:
        # Register CurveView-specific shortcuts
        ShortcutManager.connect_shortcut(self, "reset_view", self.reset_view_slot)
        ShortcutManager.connect_shortcut(self, "toggle_y_flip", self.toggle_y_flip)
        ShortcutManager.connect_shortcut(self, "toggle_scale_to_image", self.toggle_scale_to_image)
        ShortcutManager.connect_shortcut(self, "toggle_debug_mode", self.toggle_debug_mode)

    def emit(self, *args: object, **kwargs: object) -> None:
        """Emit method required by ImageSequenceProtocol.

        This is a compatibility method for the protocol. Qt signals have their own
        emit methods, so this is just a pass-through that does nothing.
        """
        pass

    # Phase 3: View state properties for backward compatibility
    # These properties delegate to the CurveViewState component while maintaining
    # the original interface for services that directly access these attributes

    @property
    def zoom_factor(self) -> float:
        """Get current zoom factor."""
        return self._view_state.zoom_factor

    @zoom_factor.setter
    def zoom_factor(self, value: float) -> None:
        """Set zoom factor."""
        self._view_state.zoom_factor = value

    @property
    def offset_x(self) -> float:
        """Get horizontal pan offset."""
        return self._view_state.offset_x

    @offset_x.setter
    def offset_x(self, value: float) -> None:
        """Set horizontal pan offset."""
        self._view_state.offset_x = value

    @property
    def offset_y(self) -> float:
        """Get vertical pan offset."""
        return self._view_state.offset_y

    @offset_y.setter
    def offset_y(self, value: float) -> None:
        """Set vertical pan offset."""
        self._view_state.offset_y = value

    @property
    def flip_y_axis(self) -> bool:
        """Get Y-axis flip state."""
        return self._view_state.flip_y_axis

    @flip_y_axis.setter
    def flip_y_axis(self, value: bool) -> None:
        """Set Y-axis flip state."""
        self._view_state.flip_y_axis = value

    @property
    def scale_to_image(self) -> bool:
        """Get scale-to-image mode state."""
        return self._view_state.scale_to_image

    @scale_to_image.setter
    def scale_to_image(self, value: bool) -> None:
        """Set scale-to-image mode state."""
        self._view_state.scale_to_image = value

    @property
    def x_offset(self) -> float:
        """Get manual X offset adjustment."""
        return self._view_state.x_offset

    @x_offset.setter
    def x_offset(self, value: float) -> None:
        """Set manual X offset adjustment."""
        self._view_state.x_offset = value

    @property
    def y_offset(self) -> float:
        """Get manual Y offset adjustment."""
        return self._view_state.y_offset

    @y_offset.setter
    def y_offset(self, value: float) -> None:
        """Set manual Y offset adjustment."""
        self._view_state.y_offset = value

    # Phase 4: Point data properties for backward compatibility
    # These properties delegate to the CurvePointManager component while maintaining
    # the original interface for services and tests that directly access these attributes

    @property
    def points(self) -> PointsList:
        """Get curve points list."""
        return self._point_manager.points

    @points.setter
    def points(self, value: PointsList) -> None:
        """Set curve points list."""
        self._point_manager.set_points(value)

    @property
    def selected_points(self) -> set[int]:
        """Get selected point indices."""
        return self._point_manager.selected_points

    @selected_points.setter
    def selected_points(self, value: set[int]) -> None:
        """Set selected point indices."""
        self._point_manager.selected_points = value

    @property
    def selected_point_idx(self) -> int:
        """Get current selected point index."""
        return self._point_manager.selected_point_idx

    @selected_point_idx.setter
    def selected_point_idx(self, value: int) -> None:
        """Set current selected point index."""
        self._point_manager.selected_point_idx = value

    @property
    def curve_data(self) -> PointsList:
        """Get complete curve data."""
        return self._point_manager.curve_data

    @curve_data.setter
    def curve_data(self, value: PointsList) -> None:
        """Set complete curve data."""
        self._point_manager.set_points(value)

    def reset_view_slot(self) -> None:
        """Reset the view to default state.

        Resets zoom to 1.0 and clears all offsets, returning the view
        to its initial state. This is typically called via keyboard shortcut.

        """
        CenteringZoomService.reset_view(self)  # type: ignore[arg-type]
        # Phase 3: View state reset now delegated to component
        self._view_state.x_offset = 0.0
        self._view_state.y_offset = 0.0
        self.update()

    def toggle_y_flip(self) -> None:
        """Toggle Y-axis flipping between image and mathematical coordinates.

        Switches between image coordinates (Y increases downward) and
        mathematical coordinates (Y increases upward). Updates the view
        immediately after toggling.

        """
        # Phase 3: Delegate to view state component
        self._view_state.toggle_y_flip()
        self.update()

    def toggle_scale_to_image(self) -> None:
        """Toggle whether curve points are scaled to image dimensions.

        When enabled, curve coordinates are interpreted relative to the
        image dimensions. When disabled, coordinates are used as-is.
        Updates the view immediately after toggling.

        """
        # Phase 3: Delegate to view state component
        self._view_state.toggle_scale_to_image()
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
            logger.info(
                f"Debug state: flip_y={getattr(self, 'flip_y_axis', False)}, "
                f"scale_to_image={getattr(self, 'scale_to_image', True)}, "
                f"x_offset={getattr(self, 'x_offset', 0)}, y_offset={getattr(self, 'y_offset', 0)}"
            )

        self.update()

    def setPoints(
        self, points: PointsList, image_width: int = 0, image_height: int = 0, preserve_view: bool = False
    ) -> None:
        """Set the points to display with optional dimension and view preservation parameters.

        This overload accepts the same parameters as setPoints_ext for compatibility,
        but delegates to setPoints_ext to ensure consistent behavior.
        """
        logger.info(f"setPoints called with {len(points)} points (preserve_view={preserve_view})")
        logger.info(
            f"Current view state: scale_to_image={getattr(self, 'scale_to_image', True)}, zoom={self.zoom_factor}, offset_x={self.offset_x}, offset_y={self.offset_y}"
        )

        # Delegate to the extended version to ensure consistent behavior
        self.setPoints_ext(points, image_width, image_height, preserve_view)

    def setPoints_ext(
        self, points: PointsList, image_width: int, image_height: int, preserve_view: bool = False
    ) -> None:
        """Set the points to display and optionally preserve the current view state."""
        logger.info("Setting points - preserve_view=%s, Points count=%d", preserve_view, len(points))
        logger.info(
            "State BEFORE: Zoom=%.2f, OffsetX=%d, OffsetY=%d, ManualX=%d, ManualY=%d, scale_to_image=%s",
            self.zoom_factor,
            self.offset_x,
            self.offset_y,
            self.x_offset,
            self.y_offset,
            getattr(self, "scale_to_image", True),
        )

        # Store original bounds for logging
        if len(self.points) > 0:
            old_min_x = min(p[1] for p in self.points)
            old_max_x = max(p[1] for p in self.points)
            old_min_y = min(p[2] for p in self.points)
            old_max_y = max(p[2] for p in self.points)
            logger.info(
                f"BEFORE data bounds: X=[{old_min_x:.2f}, {old_max_x:.2f}], Y=[{old_min_y:.2f}, {old_max_y:.2f}]"
            )

        self.points = points

        # Log new data bounds
        if len(points) > 0:
            new_min_x = min(p[1] for p in points)
            new_max_x = max(p[1] for p in points)
            new_min_y = min(p[2] for p in points)
            new_max_y = max(p[2] for p in points)
            logger.info(
                f"AFTER data bounds: X=[{new_min_x:.2f}, {new_max_x:.2f}], Y=[{new_min_y:.2f}, {new_max_y:.2f}]"
            )

        # Update dimensions only if they are validly provided (greater than 0)
        old_width = self.image_width
        old_height = self.image_height

        if image_width > 0:
            self.image_width = image_width
        if image_height > 0:
            self.image_height = image_height

        if old_width != self.image_width or old_height != self.image_height:
            logger.info(
                f"Image dimensions changed: [{old_width}x{old_height}] -> [{self.image_width}x{self.image_height}]"
            )

        if not preserve_view:
            logger.info("Resetting view since preserve_view=False")
            self.reset_view_slot()  # Reset pan/zoom only if not preserving
        else:
            logger.info("Preserving view as requested (preserve_view=True)")

        self.update()  # Trigger repaint with new data and current/reset view state

        logger.info(
            "Points set - State AFTER: Zoom=%.2f, OffsetX=%d, OffsetY=%d, ManualX=%d, ManualY=%d, scale_to_image=%s",
            self.zoom_factor,
            self.offset_x,
            self.offset_y,
            self.x_offset,
            self.y_offset,
            getattr(self, "scale_to_image", True),
        )

    def set_image_sequence(self, path: str, filenames: list[str]) -> None:
        """Set image sequence (Phase 2: delegate to image sequence component)."""
        self._image_sequence.set_image_sequence(path, filenames)
        # Update protocol attributes to maintain compatibility
        self.image_sequence_path = self._image_sequence.image_sequence_path
        self.image_filenames = self._image_sequence.image_filenames
        self.current_image_idx = self._image_sequence.current_image_idx
        # Load the image using ImageService
        ImageService.set_image_sequence(self, path, filenames)  # type: ignore[arg-type]
        # Fit to window after loading images
        self.fit_to_window()
        self.update()

    def set_current_image_by_frame(self, frame: int) -> None:
        # Use the ImageService to set the current image by frame
        ImageService.set_current_image_by_frame(self, frame)  # type: ignore[arg-type]

    def setCurrentImageByIndex(self, idx: int) -> None:
        """Backward compatibility method for test_integration_workflows.py."""
        self.set_current_image_by_index(idx)

    def setCurrentImageByFrame(self, frame: int) -> None:
        """Protocol-required camelCase alias for set_current_image_by_frame."""
        self.set_current_image_by_frame(frame)

    def setImageSequence(self, path: str, filenames: list[str]) -> None:
        """Protocol-required camelCase alias for set_image_sequence."""
        self.set_image_sequence(path, filenames)

    def toggleBackgroundVisible(self, visible: bool) -> None:
        """Protocol-required camelCase alias for toggle_background_visible."""
        self.toggle_background_visible(visible)

    def setBackgroundOpacity(self, opacity: float) -> None:
        """Protocol-required camelCase alias for set_background_opacity."""
        self.set_background_opacity(opacity)

    def set_current_image_by_index(self, idx: int) -> None:
        """Set current image by index (Phase 2: delegate to image sequence component)."""
        self._image_sequence.set_current_image_by_index(idx)
        # Update protocol attribute to maintain compatibility
        self.current_image_idx = self._image_sequence.current_image_idx
        # Use the ImageService to set the current image by index
        ImageService.set_current_image_by_index(self, idx)  # type: ignore[arg-type]
        self.update()

    def toggle_background_visible(self, visible: bool) -> None:
        """Toggle visibility of background image (Phase 2: delegate to image sequence component)."""
        self._image_sequence.toggle_background_visible(visible)
        # Update protocol attribute to maintain compatibility
        self.show_background = self._image_sequence.show_background
        self.update()

    def set_background_opacity(self, opacity: float) -> None:
        """Set the opacity of the background image (Phase 2: delegate to image sequence component)."""
        self._image_sequence.set_background_opacity(opacity)
        # Update protocol attribute to maintain compatibility
        self.background_opacity = self._image_sequence.background_opacity
        self.update()

    def load_current_image(self) -> None:
        # Using type ignore as the CurveView actually implements ImageSequenceProtocol
        ImageService.load_current_image(self)  # type: ignore[arg-type]

    def update_transform_parameters(self) -> None:
        """Explicitly update the transformation parameters used for rendering.

        Delegates to TransformationService for all transform calculations.
        """
        # Generate ViewState and validate transform using the unified transformation system
        view_state = ViewState.from_curve_view(self)
        transform = TransformationService.from_view_state(view_state)

        # Log transform validation for debugging
        params = transform.get_parameters()
        logger.debug(
            f"Transform updated: scale={params['scale']:.4f}, "
            f"center=({params['center_offset_x']:.1f}, {params['center_offset_y']:.1f}), "
            f"pan=({params['pan_offset_x']:.1f}, {params['pan_offset_y']:.1f})"
        )

    # Implementation of get_selected_points to satisfy CurveViewProtocol
    def get_selected_points(self) -> list[int]:
        return list(self.selected_points)

    def fit_to_window(self) -> None:
        """Fit all content (image and curves) to the window.

        Calculates the appropriate zoom level and offsets to fit
        all visible content within the view with some padding.
        """
        # Only fit if widget has reasonable size
        if self.width() < 300 or self.height() < 300:
            # Widget is too small, defer fitting
            self._needs_initial_fit = True
            return

        from ui.fit_to_window import fit_content_to_window

        fit_content_to_window(self)
        self._has_fitted = True

    def center_view(self) -> None:
        """Center the view on the curve points.

        If points exist, centers on their bounding box.
        Otherwise centers on the image dimensions.
        """
        # Fit content to window instead of just centering
        self.fit_to_window()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the curve and points using the new rendering system."""
        painter = QPainter(self)
        self._curve_renderer.render(painter, event, self)
        # Call parent paintEvent for any additional Qt-specific rendering
        super().paintEvent(event)

    def _draw_empty_state(self, painter: QPainter) -> None:
        """Draw empty state UI with helpful instructions."""
        # Get widget dimensions
        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2

        # Draw subtle background pattern
        pattern_color = UIScaling.get_color("bg_secondary")
        painter.setPen(QPen(QColor(pattern_color), 1, Qt.PenStyle.DotLine))
        grid_spacing = UIScaling.scale_px(50)

        # Draw grid pattern
        for x in range(0, width, grid_spacing):
            painter.drawLine(x, 0, x, height)
        for y in range(0, height, grid_spacing):
            painter.drawLine(0, y, width, y)

        # Draw central icon/symbol
        icon_size = UIScaling.scale_px(80)
        icon_rect = QRect(
            center_x - icon_size // 2, center_y - icon_size - UIScaling.scale_px(40), icon_size, icon_size
        )

        # Draw a simple curve icon
        icon_color = UIScaling.get_color("text_secondary")
        painter.setPen(QPen(QColor(icon_color), UIScaling.scale_px(3)))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        # Draw bezier-like curve symbol
        from PySide6.QtGui import QPainterPath

        path = QPainterPath()
        path.moveTo(icon_rect.left(), icon_rect.bottom())
        path.cubicTo(
            icon_rect.left() + icon_rect.width() * 0.3,
            icon_rect.top(),
            icon_rect.right() - icon_rect.width() * 0.3,
            icon_rect.bottom(),
            icon_rect.right(),
            icon_rect.top(),
        )
        painter.drawPath(path)

        # Draw points on the curve
        painter.setPen(QPen(QColor(ui_constants.CURVE_COLORS["point_normal"]), UIScaling.scale_px(8)))
        painter.drawPoint(icon_rect.left(), icon_rect.bottom())
        painter.drawPoint(icon_rect.center().x(), icon_rect.center().y())
        painter.drawPoint(icon_rect.right(), icon_rect.top())

        # Draw title text
        title_font = UIScaling.get_font("large", "bold")
        painter.setFont(title_font)
        title_color = UIScaling.get_color("text_primary")
        painter.setPen(QPen(QColor(title_color), 1))

        title_text = "No Curve Data Loaded"
        # Use QFontMetrics instead of deprecated painter.fontMetrics()
        font_metrics = QFontMetrics(painter.font())
        title_rect = font_metrics.boundingRect(title_text)
        painter.drawText(center_x - title_rect.width() // 2, center_y, title_text)

        # Draw instruction text
        instruction_font = UIScaling.get_font("normal")
        painter.setFont(instruction_font)
        instruction_color = UIScaling.get_color("text_secondary")
        painter.setPen(QPen(QColor(instruction_color), 1))

        instructions = [
            "Get started by:",
            "",
            "• Click 'Load' button or press Ctrl+O to load track data",
            "• Drag and drop 3DE4 files onto this window",
            "• Use File → Load Track Data from the menu",
            "",
            "Supported formats: 3DE4 tracking data, image sequences",
        ]

        # Create font metrics from painter's font
        font_metrics = QFontMetrics(painter.font())
        line_height = font_metrics.height() + UIScaling.scale_px(5)
        start_y = center_y + UIScaling.scale_px(40)

        for i, line in enumerate(instructions):
            if line:  # Skip empty lines for spacing
                line_rect = font_metrics.boundingRect(line)
                painter.drawText(int(center_x - line_rect.width() // 2), int(start_y + i * line_height), line)

        # Draw keyboard shortcuts hint at bottom
        hint_font = UIScaling.get_font("small")
        painter.setFont(hint_font)
        hint_color = UIScaling.get_color("text_disabled")
        painter.setPen(QPen(QColor(hint_color), 1))

        hint_text = "Press F1 for keyboard shortcuts"
        # Use cached font metrics
        font_metrics = QFontMetrics(painter.font())
        hint_rect = font_metrics.boundingRect(hint_text)
        painter.drawText(int(center_x - hint_rect.width() // 2), int(height - UIScaling.scale_px(20)), hint_text)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press to select or move points."""
        self.setFocus(Qt.FocusReason.MouseFocusReason)
        InputService.handle_mouse_press(self, event)  # type: ignore[arg-type]

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Handle mouse movement for dragging points or panning."""
        InputService.handle_mouse_move(self, event)  # type: ignore[arg-type]

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Handle mouse release."""
        InputService.handle_mouse_release(self, event)  # type: ignore[arg-type]

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Handle mouse wheel for zooming via central service."""
        InputService.handle_wheel_event(self, event)  # type: ignore[arg-type]

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key events for navigation (arrow keys, etc)."""
        InputService.handle_key_event(self, event)  # type: ignore[arg-type]

    def showEvent(self, event: QShowEvent) -> None:
        """Handle widget show event."""
        super().showEvent(event)
        # Set flag to fit content after first proper paint
        if not self._has_fitted and (self.points or self.background_image):
            self._needs_initial_fit = True

    # Compatibility methods to ensure consistent interface with EnhancedCurveView

    def set_curve_data(self, curve_data: PointsList) -> None:
        """Compatibility method for main_window.py curve_data."""
        self.points = curve_data
        self.update()

    def set_selected_indices(self, indices: list[int]) -> None:
        """Set selected point indices (Phase 4: delegate to point manager)."""
        self._point_manager.select_points(set(indices))
        self.update()

    def selectPointByIndex(self, idx: int) -> bool:
        """Protocol-required method to select a point by index (Phase 4: delegate to point manager)."""
        if self._point_manager.select_point(idx):
            self.point_selected.emit(idx)
            self.update()
            return True
        return False

    def get_selected_indices(self) -> list[int]:
        """Return list of selected indices (Phase 4: delegate to point manager)."""
        return list(self._point_manager.selected_points)

    def toggleGrid(self, enabled: bool) -> None:
        """Toggle grid display (Phase 1: delegate to visualization component)."""
        self._visualization.toggle_grid(enabled)
        # Update protocol attribute to maintain compatibility
        self.show_grid = self._visualization.show_grid

    def toggleVelocityVectors(self, enabled: bool) -> None:
        """Toggle display of velocity vectors (Phase 1: delegate to visualization component)."""
        self._visualization.toggle_velocity_vectors(enabled)
        # Update protocol attribute to maintain compatibility
        self.show_velocity_vectors = self._visualization.show_velocity_vectors
        self.update()

    def setVelocityData(self, velocities: list[tuple[float, float]]) -> None:
        """Set velocity data for visualization (Phase 1: delegate to visualization component).

        Args:
            velocities: list of velocity data points
        """
        self._visualization.set_velocity_data(velocities)
        # Maintain compatibility with existing velocity_data attribute if it exists
        self.velocity_data = self._visualization.get_velocity_data()
        self.update()

    def toggleAllFrameNumbers(self, enabled: bool) -> None:
        """Toggle frame numbers display (Phase 1: delegate to visualization component)."""
        self._visualization.toggle_all_frame_numbers(enabled)
        # Update protocol attribute to maintain compatibility
        self.show_all_frame_numbers = self._visualization.show_all_frame_numbers

    def toggleCrosshair(self, enabled: bool) -> None:
        """Toggle crosshair display (Phase 1: delegate to visualization component)."""
        self._visualization.toggle_crosshair(enabled)
        # Update protocol attribute to maintain compatibility
        self.show_crosshair = self._visualization.show_crosshair

    def centerOnSelectedPoint(self) -> bool:
        """Center the view on the currently selected point."""
        if self.selected_point_idx >= 0:
            return TransformationService.center_on_point(self, self.selected_point_idx)  # type: ignore[arg-type]
        return False

    # Implementation that satisfies both Protocol and QWidget requirements
    # Note: using type: ignore to suppress parameter name mismatch
    def setCursor(self, cursor: Qt.CursorShape | QCursor | QPixmap) -> None:  # type: ignore[override]
        """Set the cursor to the specified shape."""
        # Call parent implementation with proper typing
        super().setCursor(cursor)

    def unsetCursor(self) -> None:
        """Unset the cursor as required by CurveViewProtocol."""
        super().unsetCursor()

    def findPointAt(self, pos: QPointF) -> int:
        """Find point at the given position."""
        result = CurveService.find_point_at(self, pos.x(), pos.y())  # type: ignore[arg-type]
        # Ensure we always return an int as required by the protocol
        return result if result is not None else -1

    def get_point_data(self, idx: int) -> tuple[int, float, float, str | None]:
        """Get point data for the given index."""
        result = CurveService.get_point_data(self, idx)  # type: ignore[arg-type]
        # Ensure we return the expected tuple format
        if result is None:
            return (-1, 0.0, 0.0, None)
        return result

    def toggle_point_interpolation(self, idx: int) -> None:
        """Toggle interpolation status of a point (Phase 4: delegate to point manager)."""
        if self._point_manager.toggle_point_interpolation(idx):
            self.update()

    def update_point_position(self, idx: int, x: float, y: float) -> bool:
        """Update the position of a point (Phase 4: delegate to point manager)."""
        if self._point_manager.update_point_position(idx, x, y):
            self.update()
            return True
        return False

from PySide6.QtCore import QPointF, QRect, QSettings, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QContextMenuEvent,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPaintEvent,
    QPen,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QRubberBand,
    QVBoxLayout,
    QWidget,
)

try:
    from PySide6.QtWidgets import QShortcut
except ImportError:
    from PySide6.QtGui import QShortcut

import ui.ui_constants as ui_constants
from core.protocols import CurveViewProtocol, MainWindowProtocol, PointsList
from services.centering_zoom_service import CenteringZoomService as ZoomOperations
from services.curve_service import CurveService as CurveViewOperations
from services.image_service import ImageService
from services.input_service import InputService
from services.logging_service import LoggingService
from services.visualization_service import VisualizationService as VisualizationOperations
from ui.ui_scaling import UIScaling

logger = LoggingService.get_logger("enhanced_curve_view")


class EnhancedCurveView(QWidget):
    # Type annotation to indicate this class implements the protocol without inheritance
    _dummy: CurveViewProtocol
    """Enhanced widget for displaying and editing the 2D tracking curve with
    added visualization options like grid, vectors, and all frame numbers."""

    point_moved: Signal = Signal(int, float, float)  # Signal emitted when a point is moved
    point_selected: Signal = Signal(int)  # Signal emitted when a point is selected
    image_changed: Signal = Signal(int)  # Signal emitted when image changes via keyboard

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize the view."""
        super().__init__(parent)
        self.setMinimumSize(
            UIScaling.scale_px(200), UIScaling.scale_px(200)
        )  # Smaller minimum to allow more flexibility
        # Set size policy to expand and fill available space
        from PySide6.QtWidgets import QSizePolicy

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Set subtle background color to reduce glare
        # Apply theme-aware styling
        UIScaling.apply_theme_stylesheet(self, "curve_view")
        self.points: PointsList = []
        self.selected_point_idx: int = -1
        self.selected_points: set[int] = set()  # Track selected points for multi-select
        self.drag_active: bool = False
        self.pan_active: bool = False
        self.last_pan_pos: QPointF | None = None
        self.zoom_factor: float = 1.0
        self.offset_x: float = 0
        self.offset_y: float = 0
        self.x_offset: float = 0  # Manual offset for view panning
        self.y_offset: float = 0  # Manual offset for view panning
        self.image_width: int = 1920  # Default, will be updated when data is loaded
        self.image_height: int = 1080  # Default, will be updated when data is loaded
        self.setMouseTracking(True)
        self.point_radius: int = 2  # Default point radius (smaller)
        self.setFocusPolicy(Qt.StrongFocus)
        self.display_precision: int = 2  # Default precision for coordinate display

        # Enhanced visual options
        self.show_grid: bool = True
        self.grid_spacing: int = 100
        self.grid_line_width: int = 1
        grid_rgba = ui_constants.CURVE_COLORS["grid_minor"]
        self.grid_color: QColor = QColor(*grid_rgba)
        self.show_velocity_vectors: bool = False
        self.velocity_vector_scale: float = 5.0  # Default scale for velocity vectors
        self.show_all_frame_numbers: bool = False
        self.scale_to_image: bool = True
        self.flip_y_axis: bool = True
        self.show_background: bool = True

        # Point status colors - using standardized curve colors
        normal_color = ui_constants.CURVE_COLORS["point_normal"]
        self.normal_point_color: QColor = QColor(normal_color)
        self.normal_point_border: QColor = QColor(normal_color).darker(150)

        selected_color = ui_constants.CURVE_COLORS["point_selected"]
        self.selected_point_color: QColor = QColor(selected_color)
        self.selected_point_border: QColor = QColor(selected_color).darker(150)

        interpolated_color = ui_constants.CURVE_COLORS["point_interpolated"]
        self.interpolated_point_color: QColor = QColor(interpolated_color)
        self.interpolated_point_border: QColor = QColor(interpolated_color).darker(150)

        # Keyframe status colors: use text color for keyframes
        keyframe_color = UIScaling.get_color("text_primary")
        self.keyframe_point_color: QColor = QColor(keyframe_color)
        self.keyframe_point_border: QColor = QColor(keyframe_color).darker(150)

        # Image background properties
        self.background_opacity: float = 0.7  # Background image opacity (more visible)
        self.image_sequence_path: str = ""  # Path to image sequence directory
        self.image_filenames: list[str] = []  # List of image filenames
        self.current_image_idx: int = -1  # Current image index in sequence
        self.background_image: QPixmap | None = None  # Current background image

        # Selection properties
        self.multi_select_active: bool = False
        self.selection_start: QPointF | None = None
        self.selection_rect: QRect | None = None  # Selection rectangle for multi-select

        # Store reference to main window for direct updates
        self.main_window: MainWindowProtocol | None = parent

        # Ensure widget expands to fill available space
        self.setAutoFillBackground(True)

        # Debug options
        self.debug_mode: bool = False  # Debug visuals disabled by default for clean UI

        # Protocol required properties
        self.rubber_band: QRubberBand | None = None
        self.rubber_band_origin: QPointF = QPointF()
        self.rubber_band_active: bool = False
        self.last_drag_pos: QPointF | None = None

        # Nudging increments
        self.nudge_increment: float = 1.0
        self.available_increments: list[float] = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        self.current_increment_index: int = 2  # Default to 1.0

        # For panning
        self.pan_start_x: float = 0
        self.pan_start_y: float = 0
        self.initial_offset_x: float = 0
        self.initial_offset_y: float = 0

        # Shortcut settings
        self.settings: QSettings = QSettings("Semmlerino", "CurveEditor")
        self.default_shortcuts: dict[str, QKeySequence] = {
            "toggleGrid": QKeySequence("Ctrl+Shift+G"),
            "openShortcutSettings": QKeySequence("Ctrl+Shift+S"),
        }
        self.initShortcuts()

        # Nudge overlay toggle - disabled by default since it's now in status bar
        self.show_nudge_overlay: bool = False
        self.toggle_nudge_shortcut: QShortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        self.toggle_nudge_shortcut.activated.connect(self.toggle_nudge_overlay)

        # Flag to track if we need to fit content on first proper paint
        self._needs_initial_fit: bool = False
        self._has_fitted: bool = False

    def setPoints(
        self,
        points: PointsList,
        image_width: int,
        image_height: int,
        preserve_view: bool = False,
        force_parameters: bool = False,
    ) -> None:
        """Set the points to display and adjust view accordingly.

        Args:
            points: list of points in format [(frame, x, y), ...] or [(frame, x, y, status), ...]
            image_width: Width of the image/workspace
            image_height: Height of the image/workspace
            preserve_view: If True, maintain current view position
            force_parameters: If True, force use of provided view parameters without recalculation
        """
        VisualizationOperations.set_points(self, points, image_width, image_height, preserve_view, force_parameters)

    def setImageSequence(self, path: str, filenames: list[str]) -> None:
        """Set the image sequence to display as background."""
        ImageService.set_image_sequence(self, path, filenames)

    def toggleGrid(self, enabled: bool | None = None) -> None:
        """Toggle grid visibility."""
        VisualizationOperations.toggle_grid(self, enabled)

    def toggleVelocityVectors(self, enabled: bool | None = None) -> None:
        """Toggle velocity vector display."""
        VisualizationOperations.toggle_velocity_vectors(
            self, enabled if enabled is not None else not self.show_velocity_vectors
        )

    def toggleAllFrameNumbers(self, enabled: bool | None = None) -> None:
        """Toggle display of all frame numbers."""
        VisualizationOperations.toggle_all_frame_numbers(
            self, enabled if enabled is not None else not self.show_all_frame_numbers
        )

    def centerOnSelectedPoint(self, point_idx: int = -1, preserve_zoom: bool = True) -> None:
        """Center the view on the specified point index.

        If no index is provided, uses the currently selected point.

        Args:
            point_idx: Index of point to center on. Default -1 uses selected point.
            preserve_zoom: If True, maintain current zoom level. If False, reset view.
        """
        # use auto_center_view to avoid missing args and honor preserve_zoom
        ZoomOperations.auto_center_view(self.main_window, preserve_zoom)

    def setCoordinatePrecision(self, precision: int) -> None:
        """Set decimal precision for coordinate display."""
        self.display_precision = max(1, min(precision, 6))
        self.update()

    def setCurrentImageByFrame(self, frame: int) -> None:
        """Set the current background image based on frame number."""
        ImageService.set_current_image_by_frame(self, frame)

    def setCurrentImageByIndex(self, idx: int) -> None:
        """Set current image by index and update the view."""
        ImageService.set_current_image_by_index(self, idx)

    def toggleBackgroundVisible(self, visible: bool | None = None) -> None:
        """Toggle visibility of background image."""
        VisualizationOperations.toggle_background_visible(
            self, visible if visible is not None else not self.show_background
        )

    def setBackgroundOpacity(self, opacity: float) -> None:
        """Set the opacity of the background image."""
        VisualizationOperations.set_background_opacity(self, opacity)

    def loadCurrentImage(self) -> None:
        """Load the current image in the sequence."""
        ImageService.load_current_image(self)

    def resetView(self) -> None:
        """Reset view to default state (zoom and position)."""
        ZoomOperations.reset_view(self)

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

        from fit_to_window import fit_content_to_window

        fit_content_to_window(self)
        self._has_fitted = True

    def center_view(self) -> None:
        """Center the view on the curve points.

        If points exist, centers on their bounding box.
        Otherwise centers on the image dimensions.
        """
        # Fit content to window instead of just centering
        self.fit_to_window()

    def set_point_radius(self, radius: int | float) -> None:
        """Set the point display radius.

        Args:
            radius: Integer representing the point radius (1-10)
        """
        # Use VisualizationService directly to avoid recursive service call
        VisualizationOperations.set_point_radius(self, int(radius))
        # Update local point_radius property
        self.point_radius = int(radius)

    def get_point_data(self, index: int) -> tuple[int, float, float, bool | str] | None:
        """Get point data as a tuple (frame, x, y, status).

        Args:
            index: Index of the point to get data for

        Returns: tuple of (frame, x, y, status) or None if index is invalid
        """
        # Delegate to service facade if available, else fallback to raw list
        try:
            handler = getattr(CurveViewOperations, "get_point_data", None)
            if callable(handler):
                result = handler(self, index)
                # Ensure we return a properly typed tuple
                if result and len(result) >= 4:
                    return (result[0], result[1], result[2], result[3])
                return None
        except ImportError:
            pass
        # Fallback: normalize a raw point tuple
        from curve_view_plumbing import normalize_point

        pts = getattr(self, "points", None)
        if pts is None or index is None or index < 0 or index >= len(pts):
            return None
        result = normalize_point(pts[index])
        # Ensure proper typing for the return value
        if result and len(result) >= 4:
            return (result[0], result[1], result[2], result[3])
        return None

    def findPointAt(self, pos: QPointF) -> int:
        """Find a point at the given position.

        Args:
            pos: QPoint with screen coordinates

        Returns:
            Index of the found point or -1 if no point was found
        """
        result = CurveViewOperations.find_point_at(self, pos.x(), pos.y())
        return result if result is not None else -1

    def findClosestPointByFrame(self, frame_num: int) -> int:
        """Find the point closest to the given frame number.

        Args:
            frame_num: The frame number to find the closest point to

        Returns:
            Index of the closest point or -1 if no points are available
        """
        result = CurveViewOperations.find_closest_point_by_frame(self, frame_num)
        return result if result is not None else -1

    def toggle_point_interpolation(self, index: int) -> bool:
        """Toggle the interpolation status of a point.

        Args:
            index: Index of the point to toggle

        Returns:
            bool: True if the toggle was successful, False otherwise
        """
        result = CurveViewOperations.toggle_point_interpolation(self, index)
        return bool(result) if result is not None else False

    def finalize_selection(self) -> None:
        """Select all points inside the selection rectangle."""
        CurveViewOperations.finalize_selection(self, self.main_window)

    def paintEvent(self, event: QPaintEvent) -> None:
        """Draw the curve and points with enhanced visualization."""
        # Always paint - don't return early as this prevents proper widget sizing
        # if not self.points and not self.background_image:
        #     return

        # Check if we need to do initial fit after widget is properly sized
        if self._needs_initial_fit and self.width() > 300 and self.height() > 300:
            self._needs_initial_fit = False
            self._has_fitted = True
            # Use a timer to fit after this paint completes
            QTimer.singleShot(10, self.fit_to_window)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Fill background with theme-aware color
        bg_color = UIScaling.get_color("bg_primary")
        painter.fillRect(self.rect(), QColor(bg_color))

        # Draw focus indicator if widget has focus
        if self.hasFocus():
            focus_color = UIScaling.get_color("border_focus")
            painter.setPen(QPen(QColor(focus_color), 2))
            painter.drawRect(self.rect().adjusted(1, 1, -1, -1))

        # Get widget dimensions
        # widget_width = self.width()  # Not used - only height needed for vertical scaling
        widget_height = self.height()

        # Use the background image dimensions if available, otherwise use track dimensions
        display_width = self.image_width
        display_height = self.image_height

        if self.background_image:
            display_width = self.background_image.width()
            display_height = self.background_image.height()

        # Calculate the scale factor to fit in the widget
        # scale_x = widget_width / display_width  # Not used - using scale_y to fill height
        scale_y = widget_height / display_height

        # Scale to fill the widget height completely
        # This ensures the image covers from top to bottom
        # Don't apply zoom_factor to background - it should always fill the view
        scale = scale_y

        # Calculate centering offsets
        # Modified to fill entire widget - no centering, image starts at top-left
        offset_x, offset_y = self.offset_x, self.offset_y

        # Coordinate transformation functions
        def transform_point(x: float, y: float) -> tuple[float, float]:
            """Transform from track coordinates to widget coordinates."""
            # We need to ensure the transformation is consistent with the background image
            # This direct transformation approach ensures the curve and background move together

            if self.scale_to_image:
                # Apply image scaling first if needed
                tx = x * (display_width / self.image_width) if self.image_width > 0 else x
                ty = y * (display_height / self.image_height) if self.image_height > 0 else y

                # Apply Y-flip if needed
                if self.flip_y_axis:
                    ty = display_height - ty

                # Apply scaling, centering, and pan offsets consistently with background image
                tx = tx * scale + offset_x + self.x_offset
                ty = ty * scale + offset_y + self.y_offset

                return tx, ty
            else:
                # Fall back to standard transformation when not scaling to image
                result = CurveViewOperations.transform_point(
                    self,
                    x,
                    y,
                    display_width,
                    display_height,
                    self.offset_x,
                    self.offset_y,
                    scale,
                )

                # Convert result to tuple if needed
                if isinstance(result, tuple):
                    return result
                elif hasattr(result, "x") and hasattr(result, "y"):
                    return (result.x(), result.y())
                else:
                    logger.warning(f"Unexpected transform result type: {type(result)}")
                    return (0, 0)

        def inverse_transform(tx: float, ty: float) -> tuple[float, float]:
            """Transform from widget coordinates to track coordinates."""
            if self.background_image and self.scale_to_image:
                # Convert from widget to image space
                img_x = (tx - offset_x - self.x_offset) / scale

                if self.flip_y_axis:
                    img_y = display_height - ((ty - offset_y - self.y_offset) / scale)
                else:
                    img_y = (ty - offset_y - self.y_offset) / scale

                # Convert from image coordinates to track coordinates
                x = img_x / (display_width / self.image_width) if self.image_width > 0 else img_x
                y = img_y / (display_height / self.image_height) if self.image_height > 0 else img_y
            else:
                # Direct conversion
                x = (tx - offset_x - self.x_offset) / scale

                if self.flip_y_axis:
                    y = self.image_height - ((ty - offset_y - self.y_offset) / scale)
                else:
                    y = (ty - offset_y - self.y_offset) / scale

            return x, y

        # Draw background image if available
        if self.show_background and self.background_image:
            # Calculate scaled dimensions
            scaled_width = display_width * scale
            scaled_height = display_height * scale

            # Position image (apply centering offset and scaling first)
            img_x_scaled = offset_x
            img_y_scaled = offset_y

            # Apply manual pan offset (unscaled widget coordinates)
            img_x = img_x_scaled + self.x_offset
            img_y = img_y_scaled + self.y_offset

            # Draw the image with proper clipping to prevent overflow
            painter.setOpacity(self.background_opacity)

            # Set clipping rect to widget bounds to prevent image overflow
            painter.setClipRect(self.rect())

            if isinstance(self.background_image, QPixmap):
                # If it's already a QPixmap, use it directly with proper aspect ratio
                painter.drawPixmap(int(img_x), int(img_y), int(scaled_width), int(scaled_height), self.background_image)
            else:
                # Convert QImage to QPixmap with proper scaling
                try:
                    # Fill entire area - ignore aspect ratio to cover full widget
                    scaled_image = self.background_image.scaled(
                        int(scaled_width),
                        int(scaled_height),
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    painter.drawImage(int(img_x), int(img_y), scaled_image)
                except (ValueError, TypeError, RuntimeError, OSError) as e:
                    # Fallback if there's an issue with the image scaling
                    logger.warning(f"Failed to scale image: {e}")
                    pass

            painter.setOpacity(1.0)

        # Draw the main curve if available
        if self.points:
            # Set pen for the main curve
            curve_color = ui_constants.CURVE_COLORS["curve_line"]
            curve_pen = QPen(QColor(curve_color), 2)
            painter.setPen(curve_pen)

            # Create path for the curve
            path = QPainterPath()

            if self.points:
                # Start with the first point
                point = self.points[0]
                frame, x, y = point[:3]  # Extract only frame, x, y even if there's a status
                tx, ty = transform_point(x, y)
                path.moveTo(tx, ty)

                # Connect subsequent points
                for i in range(1, len(self.points)):
                    point = self.points[i]
                    frame, x, y = point[:3]  # Extract only frame, x, y even if there's a status
                    tx, ty = transform_point(x, y)
                    path.lineTo(tx, ty)

            # Draw the curve
            painter.drawPath(path)

            # Draw points
            for i in range(len(self.points)):
                point = self.points[i]
                frame, x, y = point[:3]  # Extract only frame, x, y even if there's a status
                tx, ty = transform_point(x, y)

                # Determine if point is selected (either primary selection or in multi-selection)
                is_selected = i in self.selected_points

                # Determine keyframe (first/last always) or interpolated status
                is_keyframe = i == 0 or i == len(self.points) - 1
                is_interpolated = False
                if not is_keyframe and len(point) > 3:
                    if point[3] == "keyframe":
                        is_keyframe = True
                    elif point[3] == "interpolated":
                        is_interpolated = True

                if is_selected:
                    painter.setPen(QPen(self.selected_point_border, 2))
                    painter.setBrush(self.selected_point_color)
                    point_radius = self.point_radius + 2 if i == self.selected_point_idx else self.point_radius
                elif is_keyframe:
                    outline_color = UIScaling.get_color("bg_primary")
                    painter.setPen(QPen(QColor(outline_color).lighter(110), 1))  # subtle outline
                    painter.setBrush(self.keyframe_point_color)
                    point_radius = self.point_radius + 3  # slightly larger for visibility
                elif is_interpolated:
                    painter.setPen(QPen(self.interpolated_point_border, 1))
                    painter.setBrush(self.interpolated_point_color)
                    point_radius = self.point_radius
                else:
                    painter.setPen(QPen(self.normal_point_border, 1))
                    painter.setBrush(self.normal_point_color)
                    point_radius = self.point_radius

                painter.drawEllipse(QPointF(tx, ty), point_radius, point_radius)

                # Draw frame number/type label for each point
                label_color = UIScaling.get_color("text_warning")
                painter.setPen(QPen(QColor(label_color), 1))
                font = UIScaling.get_font("tiny")
                painter.setFont(font)
                if is_selected:
                    point_type = point[3] if len(point) > 3 else "normal"
                    painter.drawText(int(tx) + 10, int(ty) - 10, f"{frame}, {point_type}")
                elif self.show_all_frame_numbers or frame % 10 == 0:
                    painter.drawText(int(tx) + 10, int(ty) - 10, str(frame))

        # Display nudge increment overlay
        if self.show_nudge_overlay:
            indicator_width = 150
            indicator_height = 15
            indicator_x = 10
            indicator_y = 10

            # Use theme-aware colors for overlay
            overlay_bg = UIScaling.get_color("bg_secondary")
            overlay_border = UIScaling.get_color("border_default")
            painter.setBrush(QColor(overlay_bg))
            painter.setPen(QPen(QColor(overlay_border), 1))
            painter.drawRect(indicator_x, indicator_y, indicator_width, indicator_height)

            for i, _increment in enumerate(self.available_increments):
                pos_x = indicator_x + (i / (len(self.available_increments) - 1)) * indicator_width
                tick_color = UIScaling.get_color("text_secondary")
                painter.setPen(QPen(QColor(tick_color), 1))
                painter.drawLine(int(pos_x), indicator_y, int(pos_x), indicator_y + indicator_height)

            current_pos_x = (
                indicator_x + (self.current_increment_index / (len(self.available_increments) - 1)) * indicator_width
            )

            cursor_size = 6
            cursor_color = UIScaling.get_color("text_warning")
            painter.setBrush(QColor(cursor_color))
            painter.setPen(Qt.NoPen)
            cursor_points = [
                QPointF(current_pos_x, indicator_y),
                QPointF(current_pos_x - cursor_size / 2, indicator_y - cursor_size),
                QPointF(current_pos_x + cursor_size / 2, indicator_y - cursor_size),
            ]
            painter.drawPolygon(cursor_points)

            painter.setPen(QPen(QColor(cursor_color), 1))
            painter.drawText(
                indicator_x + indicator_width + 5, indicator_y + indicator_height - 2, f"{self.nudge_increment:.1f}"
            )

            help_color = UIScaling.get_color("text_secondary")
            painter.setPen(QPen(QColor(help_color), 1))
            painter.drawText(indicator_x, indicator_y + indicator_height + 12, "↑/↓ to change increment")

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Delegate mouse press to InputService."""
        self.setFocus()
        InputService.handle_mouse_press(self, event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Delegate mouse move to InputService."""
        InputService.handle_mouse_move(self, event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Delegate mouse release to InputService."""
        InputService.handle_mouse_release(self, event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Delegate wheel event to InputService."""
        InputService.handle_wheel_event(self, event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Delegate key press to InputService."""
        InputService.handle_key_event(self, event)

    def selectAllPoints(self) -> None:
        """Select all points in the curve."""
        CurveViewOperations.select_all_points(self)

    def clearSelection(self) -> None:
        """Clear all point selections."""
        CurveViewOperations.clear_selection(self, self.main_window)

    def selectPointByIndex(self, index: int) -> bool:
        """Select a point by its index."""
        result = CurveViewOperations.select_point_by_index(self, self.main_window, index)
        return bool(result) if result is not None else False

    def set_curve_data(self, curve_data: PointsList) -> None:
        """Compatibility method for curve_data from main_window."""
        # Update internal points and refresh view, preserving zoom/pan
        self.setPoints(curve_data, self.image_width, self.image_height, preserve_view=True)

    def set_selected_indices(self, indices: list[int]) -> None:
        """Set selected point indices."""
        self.selected_points = set(indices)
        if indices:
            self.selected_point_idx = indices[0]
        else:
            self.selected_point_idx = -1
        self.update()

    def get_selected_indices(self) -> list[int]:
        """Return list of selected indices."""
        return list(self.selected_points)

    def change_nudge_increment(self, increase: bool = True) -> bool:
        """Change the nudge increment for point movement."""
        result = CurveViewOperations.change_nudge_increment(self, increase)
        return bool(result) if result is not None else False

    def nudge_selected_points(self, dx: float = 0, dy: float = 0) -> bool:
        """Nudge selected points by the specified delta."""
        result = CurveViewOperations.nudge_selected_points(self, dx, dy)
        return bool(result) if result is not None else False

    def update_point_position(self, index: int, x: float, y: float) -> bool:
        """Update a point's position while preserving its status."""
        result = CurveViewOperations.update_point_position(self, self.main_window, index, x, y)
        return bool(result) if result is not None else False

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Show context menu with point options."""
        InputService.handle_context_menu(self, event)

    def extractFrameNumber(self, img_idx: int) -> int:
        """Extract frame number from the current image index."""
        result = CurveViewOperations.extract_frame_number(self, img_idx)
        return result if result is not None else 0

    def initShortcuts(self) -> None:
        """Initialize configurable keyboard shortcuts."""
        self.shortcuts: dict[str, QShortcut] = {}
        actions = {"toggleGrid": self.toggleGrid, "openShortcutSettings": self.showShortcutSettings}
        for action_key, method in actions.items():
            default_seq = self.default_shortcuts[action_key]
            seq_str = self.settings.value(f"shortcuts/{action_key}", default_seq.toString())
            seq = QKeySequence(seq_str)
            sc = QShortcut(seq, self)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(method)
            self.shortcuts[action_key] = sc

    def reloadShortcuts(self) -> None:
        """Reload shortcuts from settings after edits."""
        for sc in self.shortcuts.values():
            try:
                sc.activated.disconnect()
            except TypeError:
                pass
            sc.deleteLater()
        self.initShortcuts()

    def showShortcutSettings(self) -> None:
        """Open the settings dialog for editing shortcuts."""
        dlg = ShortcutSettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.reloadShortcuts()

    def toggle_nudge_overlay(self, enabled: bool | None = None) -> None:
        """Show or hide the nudge overlay."""
        if enabled is None:
            self.show_nudge_overlay = not self.show_nudge_overlay
        else:
            self.show_nudge_overlay = enabled
        self.update()

    def showEvent(self, event) -> None:
        """Handle widget show event."""
        super().showEvent(event)
        # Set flag to fit content after first proper paint
        if not self._has_fitted and (self.points or self.background_image):
            self._needs_initial_fit = True


class ShortcutSettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Shortcut Settings")
        self.layout = QVBoxLayout(self)
        self.settings = QSettings("Semmlerino", "CurveEditor")
        self.fields = {}
        # Define editable shortcuts
        actions = [("Toggle Grid", "toggleGrid"), ("Open Shortcut Settings", "openShortcutSettings")]
        for label_text, action_key in actions:
            h_layout = QHBoxLayout()
            label = QLabel(label_text)
            edit = QKeySequenceEdit()
            seq_str = self.settings.value(f"shortcuts/{action_key}", "")
            default_seq = QKeySequence("Ctrl+Shift+G") if action_key == "toggleGrid" else QKeySequence("Ctrl+Shift+S")
            seq = QKeySequence(seq_str) if seq_str else default_seq
            edit.setKeySequence(seq)
            h_layout.addWidget(label)
            h_layout.addWidget(edit)
            self.layout.addLayout(h_layout)
            self.fields[action_key] = edit
        # Save/Cancel buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton("Save")
        cancel_btn = QPushButton("Cancel")
        save_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        self.layout.addLayout(btn_layout)

    def accept(self) -> None:
        for action_key, edit in self.fields.items():
            seq = edit.keySequence().toString()
            self.settings.setValue(f"shortcuts/{action_key}", seq)
        super().accept()

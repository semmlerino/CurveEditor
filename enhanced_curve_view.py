# -*- coding: utf-8 -*-
# type: ignore


from PySide6.QtCore import Qt, Signal, QSettings, QPointF
from PySide6.QtGui import (
    QPainter, QPen, QColor, QPainterPath,
    QPixmap, QKeySequence
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QKeySequenceEdit, QPushButton,
    QDialog
)
try:
    from PySide6.QtWidgets import QShortcut
except ImportError:
    from PySide6.QtGui import QShortcut

from services.centering_zoom_service import CenteringZoomService as ZoomOperations
from services.curve_service import CurveService as CurveViewOperations
from services.image_service import ImageService
from services.input_service import InputService, CurveViewProtocol  # Import for type checking
import logging

logger = logging.getLogger(__name__)


class EnhancedCurveView(QWidget):
    # Type annotation to indicate this class implements the protocol without inheritance
    _dummy: CurveViewProtocol
    """Enhanced widget for displaying and editing the 2D tracking curve with
    added visualization options like grid, vectors, and all frame numbers."""

    point_moved = Signal(int, float, float)  # Signal emitted when a point is moved
    point_selected = Signal(int)  # Signal emitted when a point is selected
    image_changed = Signal(int)  # Signal emitted when image changes via keyboard

    def __init__(self, parent=None):
        """Initialize the view."""
        super(EnhancedCurveView, self).__init__(parent)
        self.setMinimumSize(800, 600)
        self.points = []
        self.selected_point_idx = -1
        self.selected_points = set()  # Track selected points for multi-select
        self.drag_active = False
        self.pan_active = False
        self.last_pan_pos = None
        self.zoom_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.x_offset = 0  # Manual offset for view panning
        self.y_offset = 0  # Manual offset for view panning
        self.image_width = 1920  # Default, will be updated when data is loaded
        self.image_height = 1080  # Default, will be updated when data is loaded
        self.setMouseTracking(True)
        self.point_radius = 2  # Default point radius (smaller)
        self.setFocusPolicy(Qt.StrongFocus)
        self.display_precision = 2  # Default precision for coordinate display

        # Enhanced visual options
        self.show_grid = True
        self.grid_spacing = 100
        self.grid_line_width = 1
        self.grid_color = QColor(100, 100, 120, 150)  # Default grid color (semi-transparent gray-blue)
        self.show_velocity_vectors = False
        self.velocity_vector_scale = 5.0  # Default scale for velocity vectors
        self.show_all_frame_numbers = False
        self.scale_to_image = True
        self.flip_y_axis = True
        self.show_background = True

        # Point status colors
        self.normal_point_color = QColor(220, 220, 220, 200)
        self.normal_point_border = QColor(200, 200, 200)
        self.selected_point_color = QColor(255, 80, 80, 150)
        self.selected_point_border = QColor(255, 80, 80)
        self.interpolated_point_color = QColor(100, 180, 255, 150)
        self.interpolated_point_border = QColor(80, 160, 240)
        # Keyframe status colors: darker for key points (improved contrast)
        self.keyframe_point_color = QColor(80, 80, 80, 200)
        self.keyframe_point_border = QColor(50, 50, 50)

        # Image background properties
        self.background_opacity = 0.5  # Background image opacity
        self.image_sequence_path = ""  # Path to image sequence directory
        self.image_filenames = []  # List of image filenames
        self.current_image_idx = -1  # Current image index in sequence
        self.background_image = None  # Current background image

        # Selection properties
        self.multi_select_active = False
        self.selection_start = None
        self.selection_rect = None  # Selection rectangle for multi-select

        # Store reference to main window for direct updates
        self.main_window = parent

        # Debug options
        self.debug_mode = True  # Enable debug visuals

        # Protocol required properties
        self.rubber_band = None
        self.rubber_band_origin = QPointF()
        self.rubber_band_active = False
        self.last_drag_pos = None

        # Nudging increments
        self.nudge_increment = 1.0
        self.available_increments = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        self.current_increment_index = 2  # Default to 1.0

        # For panning
        self.pan_start_x = 0
        self.pan_start_y = 0
        self.initial_offset_x = 0
        self.initial_offset_y = 0

        # Shortcut settings
        self.settings = QSettings("Semmlerino", "CurveEditor")
        self.default_shortcuts = {"toggleGrid": QKeySequence("Ctrl+Shift+G"), "openShortcutSettings": QKeySequence("Ctrl+Shift+S")}
        self.initShortcuts()

        # Nudge overlay toggle
        self.show_nudge_overlay = True
        self.toggle_nudge_shortcut = QShortcut(QKeySequence("Ctrl+N"), self)
        self.toggle_nudge_shortcut.activated.connect(self.toggle_nudge_overlay)

    def setPoints(self, points, image_width, image_height, preserve_view=False, force_parameters=False):
        """Set the points to display and adjust view accordingly.

        Args:
            points: List of points in format [(frame, x, y), ...] or [(frame, x, y, status), ...]
            image_width: Width of the image/workspace
            image_height: Height of the image/workspace
            preserve_view: If True, maintain current view position
            force_parameters: If True, force use of provided view parameters without recalculation
        """
        from services.visualization_service import VisualizationService as VisualizationOperations
        VisualizationOperations.set_points(self, points, image_width, image_height, preserve_view, force_parameters)

    def setImageSequence(self, path, filenames):
        """Set the image sequence to display as background."""
        ImageService.set_image_sequence(self, path, filenames)

    def toggleGrid(self, enabled=None):
        """Toggle grid visibility."""
        from services.visualization_service import VisualizationService as VisualizationOperations
        VisualizationOperations.toggle_grid(self, enabled)

    def toggleVelocityVectors(self, enabled=None):
        """Toggle velocity vector display."""
        from services.visualization_service import VisualizationService as VisualizationOperations
        VisualizationOperations.toggle_velocity_vectors(self, enabled)

    def toggleAllFrameNumbers(self, enabled=None):
        """Toggle display of all frame numbers."""
        from services.visualization_service import VisualizationService as VisualizationOperations
        VisualizationOperations.toggle_all_frame_numbers(self, enabled)


    def centerOnSelectedPoint(self, point_idx=-1, preserve_zoom=True):
        """Center the view on the specified point index.

        If no index is provided, uses the currently selected point.

        Args:
            point_idx: Index of point to center on. Default -1 uses selected point.
            preserve_zoom: If True, maintain current zoom level. If False, reset view.
        """
        # use auto_center_view to avoid missing args and honor preserve_zoom
        ZoomOperations.auto_center_view(self.main_window, preserve_zoom)

    def setCoordinatePrecision(self, precision):
        """Set decimal precision for coordinate display."""
        self.display_precision = max(1, min(precision, 6))
        self.update()

    def setCurrentImageByFrame(self, frame):
        """Set the current background image based on frame number."""
        ImageService.set_current_image_by_frame(self, frame)

    def setCurrentImageByIndex(self, idx):
        """Set current image by index and update the view."""
        ImageService.set_current_image_by_index(self, idx)

    def toggleBackgroundVisible(self, visible=None):
        """Toggle visibility of background image."""
        from services.visualization_service import VisualizationService as VisualizationOperations
        VisualizationOperations.toggle_background_visible(self, visible)

    def setBackgroundOpacity(self, opacity):
        """Set the opacity of the background image."""
        from services.visualization_service import VisualizationService as VisualizationOperations
        VisualizationOperations.set_background_opacity(self, opacity)

    def loadCurrentImage(self):
        """Load the current image in the sequence."""
        ImageService.load_current_image(self)

    def resetView(self):
        """Reset view to default state (zoom and position)."""
        ZoomOperations.reset_view(self)

    def set_point_radius(self, radius):
        """Set the point display radius.

        Args:
            radius: Integer representing the point radius (1-10)
        """
        # Use VisualizationService directly to avoid recursive service call
        from services.visualization_service import VisualizationService as VisualizationOperations
        VisualizationOperations.set_point_radius(self, int(radius))
        # Update local point_radius property
        self.point_radius = int(radius)

    def get_point_data(self, index):
        """Get point data as a tuple (frame, x, y, status).

        Args:
            index: Index of the point to get data for

        Returns:
            Tuple of (frame, x, y, status) or None if index is invalid
        """
        # Delegate to service facade if available, else fallback to raw list
        try:
            handler = getattr(CurveViewOperations, 'get_point_data', None)
            if callable(handler):
                return handler(self, index)
        except ImportError:
            pass
        # Fallback: normalize a raw point tuple
        from curve_view_plumbing import normalize_point
        pts = getattr(self, 'points', None)
        if pts is None or index is None or index < 0 or index >= len(pts):
            return None
        return normalize_point(pts[index])

    def findPointAt(self, pos):
        """Find a point at the given position.

        Args:
            pos: QPoint with screen coordinates

        Returns:
            Index of the found point or -1 if no point was found
        """
        return CurveViewOperations.find_point_at(self, pos.x(), pos.y())

    def findClosestPointByFrame(self, frame_num):
        """Find the point closest to the given frame number.

        Args:
            frame_num: The frame number to find the closest point to

        Returns:
            Index of the closest point or -1 if no points are available
        """
        return CurveViewOperations.find_closest_point_by_frame(self, frame_num)

    def toggle_point_interpolation(self, index):
        """Toggle the interpolation status of a point.

        Args:
            index: Index of the point to toggle

        Returns:
            bool: True if the toggle was successful, False otherwise
        """
        return CurveViewOperations.toggle_point_interpolation(self, index)

    def finalize_selection(self):
        """Select all points inside the selection rectangle."""
        CurveViewOperations.finalize_selection(self, self.main_window)

    def paintEvent(self, event):
        """Draw the curve and points with enhanced visualization."""
        if not self.points and not self.background_image:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

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

        # Coordinate transformation functions
        def transform_point(x, y):
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
                    self, x, y,
                    display_width, display_height,
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

        def inverse_transform(tx, ty):
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

            # Draw the image - use self.background_image directly if it's already a QPixmap
            # to avoid creating a new QPixmap during painting
            painter.setOpacity(self.background_opacity)

            if isinstance(self.background_image, QPixmap):
                # If it's already a QPixmap, use it directly
                painter.drawPixmap(int(img_x), int(img_y), int(scaled_width), int(scaled_height), self.background_image)
            else:
                # Convert QImage to QPixmap only when necessary
                try:
                    painter.drawImage(int(img_x), int(img_y), self.background_image.scaled(int(scaled_width), int(scaled_height), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                except Exception:
                    # Fallback if there's an issue with the image
                    pass

            painter.setOpacity(1.0)

        # Draw the main curve if available
        if self.points:
            # Set pen for the main curve
            curve_pen = QPen(QColor(0, 160, 230), 2)
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
                is_keyframe = (i == 0 or i == len(self.points) - 1)
                is_interpolated = False
                if not is_keyframe and len(point) > 3:
                    if point[3] == 'keyframe':
                        is_keyframe = True
                    elif point[3] == 'interpolated':
                        is_interpolated = True

                if is_selected:
                    painter.setPen(QPen(self.selected_point_border, 2))
                    painter.setBrush(self.selected_point_color)
                    point_radius = self.point_radius + 2 if i == self.selected_point_idx else self.point_radius
                elif is_keyframe:
                    painter.setPen(QPen(QColor(255, 255, 255, 200), 1))  # thin bright outline
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
                painter.setPen(QPen(QColor(200, 200, 100), 1))
                font = painter.font()
                font.setPointSize(8)
                painter.setFont(font)
                if is_selected:
                    point_type = point[3] if len(point) > 3 else 'normal'
                    painter.drawText(int(tx) + 10, int(ty) - 10, f"{frame}, {point_type}")
                elif self.show_all_frame_numbers or frame % 10 == 0:
                    painter.drawText(int(tx) + 10, int(ty) - 10, str(frame))

        # Display nudge increment overlay
        if self.show_nudge_overlay:
            indicator_width = 150
            indicator_height = 15
            indicator_x = 10
            indicator_y = 10

            painter.setBrush(QColor(50, 50, 50, 180))
            painter.setPen(QPen(QColor(100, 100, 100), 1))
            painter.drawRect(indicator_x, indicator_y, indicator_width, indicator_height)

            for i, increment in enumerate(self.available_increments):
                pos_x = indicator_x + (i / (len(self.available_increments) - 1)) * indicator_width
                painter.setPen(QPen(QColor(150, 150, 150), 1))
                painter.drawLine(int(pos_x), indicator_y, int(pos_x), indicator_y + indicator_height)

            current_pos_x = indicator_x + (self.current_increment_index / (len(self.available_increments) - 1)) * indicator_width

            cursor_size = 6
            painter.setBrush(QColor(255, 200, 0))
            painter.setPen(Qt.NoPen)
            cursor_points = [
                QPointF(current_pos_x, indicator_y),
                QPointF(current_pos_x - cursor_size/2, indicator_y - cursor_size),
                QPointF(current_pos_x + cursor_size/2, indicator_y - cursor_size),
            ]
            painter.drawPolygon(cursor_points)

            painter.setPen(QPen(QColor(255, 200, 0), 1))
            painter.drawText(indicator_x + indicator_width + 5, indicator_y + indicator_height - 2, f"{self.nudge_increment:.1f}")

            painter.setPen(QPen(QColor(200, 200, 200), 1))
            painter.drawText(indicator_x, indicator_y + indicator_height + 12, "↑/↓ to change increment")

    def mousePressEvent(self, event):
        """Delegate mouse press to InputService."""
        self.setFocus()
        InputService.handle_mouse_press(self, event)

    def mouseMoveEvent(self, event):
        """Delegate mouse move to InputService."""
        InputService.handle_mouse_move(self, event)

    def mouseReleaseEvent(self, event):
        """Delegate mouse release to InputService."""
        InputService.handle_mouse_release(self, event)

    def wheelEvent(self, event):
        """Delegate wheel event to InputService."""
        InputService.handle_wheel_event(self, event)

    def keyPressEvent(self, event):
        """Delegate key press to InputService."""
        InputService.handle_key_event(self, event)

    def selectAllPoints(self):
        """Select all points in the curve."""
        CurveViewOperations.select_all_points(self)

    def clearSelection(self):
        """Clear all point selections."""
        CurveViewOperations.clear_selection(self, self.main_window)

    def selectPointByIndex(self, index):
        """Select a point by its index."""
        return CurveViewOperations.select_point_by_index(self, index)

    def set_curve_data(self, curve_data):
        """Compatibility method for curve_data from main_window."""
        # Update internal points and refresh view, preserving zoom/pan
        self.setPoints(curve_data, self.image_width, self.image_height, preserve_view=True)

    def set_selected_indices(self, indices):
        """Set selected point indices."""
        self.selected_points = set(indices)
        if indices:
            self.selected_point_idx = indices[0]
        else:
            self.selected_point_idx = -1
        self.update()

    def get_selected_indices(self):
        """Return list of selected indices."""
        return list(self.selected_points)

    def change_nudge_increment(self, increase=True):
        """Change the nudge increment for point movement."""
        return CurveViewOperations.change_nudge_increment(self, increase)

    def nudge_selected_points(self, dx=0, dy=0):
        """Nudge selected points by the specified delta."""
        return CurveViewOperations.nudge_selected_points(self, dx, dy)

    def update_point_position(self, index, x, y):
        """Update a point's position while preserving its status."""
        return CurveViewOperations.update_point_position(self, self.main_window, index, x, y)

    def contextMenuEvent(self, event):
        """Show context menu with point options."""
        InputService.handle_context_menu(self, event)

    def extractFrameNumber(self, img_idx):
        """Extract frame number from the current image index."""
        return CurveViewOperations.extract_frame_number(self, img_idx)

    def initShortcuts(self):
        """Initialize configurable keyboard shortcuts."""
        self.shortcuts = {}
        actions = {"toggleGrid": self.toggleGrid, "openShortcutSettings": self.showShortcutSettings}
        for action_key, method in actions.items():
            default_seq = self.default_shortcuts[action_key]
            seq_str = self.settings.value(f"shortcuts/{action_key}", default_seq.toString())
            seq = QKeySequence(seq_str)
            sc = QShortcut(seq, self)
            sc.setContext(Qt.ApplicationShortcut)
            sc.activated.connect(method)
            self.shortcuts[action_key] = sc

    def reloadShortcuts(self):
        """Reload shortcuts from settings after edits."""
        for sc in self.shortcuts.values():
            try:
                sc.activated.disconnect()
            except TypeError:
                pass
            sc.deleteLater()
        self.initShortcuts()

    def showShortcutSettings(self):
        """Open the settings dialog for editing shortcuts."""
        dlg = ShortcutSettingsDialog(self)
        if dlg.exec() == QDialog.Accepted:
            self.reloadShortcuts()

    def toggle_nudge_overlay(self, enabled=None):
        """Show or hide the nudge overlay."""
        if enabled is None:
            self.show_nudge_overlay = not self.show_nudge_overlay
        else:
            self.show_nudge_overlay = enabled
        self.update()


class ShortcutSettingsDialog(QDialog):
    def __init__(self, parent=None):
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

    def accept(self):
        for action_key, edit in self.fields.items():
            seq = edit.keySequence().toString()
            self.settings.setValue(f"shortcuts/{action_key}", seq)
        super().accept()

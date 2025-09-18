#!/usr/bin/env python
"""
Individual Frame Tab Component for Timeline

Represents a single frame in the timeline with color coding based on point status.
Similar to 3DEqualizer frame tabs with visual indicators for tracking status.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QContextMenuEvent, QEnterEvent, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget


class FrameTab(QWidget):
    """Individual frame tab with color coding and click interaction."""

    # Signals
    frame_clicked = Signal(int)  # Emitted when tab is clicked (frame_number)
    frame_hovered = Signal(int)  # Emitted when tab is hovered (frame_number)

    # Tab appearance constants - modern 3DE style
    TAB_HEIGHT: int = 38  # Taller tabs for better visibility
    BORDER_WIDTH: int = 1
    CORNER_RADIUS: int = 0  # No rounded corners for seamless look
    MIN_WIDTH: int = 2  # Minimum width for very large frame ranges
    MAX_WIDTH: int = 60  # Maximum width for small frame ranges

    # Color scheme for frame status - uses dark theme
    # Initialize colors on first use to avoid import issues
    COLORS: dict[str, QColor] = {}

    @classmethod
    def _init_colors(cls) -> None:
        """Initialize colors from theme if not already done."""
        if not cls.COLORS:
            from ui.ui_constants import COLORS_DARK

            cls.COLORS = {
                "no_points": QColor(COLORS_DARK["bg_secondary"]),  # Secondary background - no tracked points
                "keyframe": QColor(55, 65, 55),  # Very subtle green tint - has keyframe points
                "interpolated": QColor(60, 58, 50),  # Very subtle brown tint - only interpolated points
                "tracked": QColor(50, 55, 65),  # Very subtle blue tint - tracked points
                "endframe": QColor(65, 50, 50),  # Very subtle red tint - segment end
                "startframe": QColor(50, 70, 55),  # Slightly brighter green - segment start
                "inactive": QColor(40, 40, 40),  # Dark gray for inactive segments
                "mixed": QColor(COLORS_DARK["bg_surface"]),  # Surface color for mixed
                "current_frame": QColor(COLORS_DARK["bg_secondary"]),  # Same as no_points, highlight with border
                "current_border": QColor(COLORS_DARK["accent_warning"]),  # Warning color for current frame
                "selected": QColor(COLORS_DARK["bg_selected"]),  # Selected state color
                "border": QColor(COLORS_DARK["border_default"]),  # Default border
                "text": QColor(COLORS_DARK["text_primary"]),  # Primary text
                "text_current": QColor(COLORS_DARK["text_primary"]),  # Primary text for current frame
            }

    # Instance attributes
    frame_number: int
    is_current_frame: bool
    is_hovered: bool
    point_count: int
    keyframe_count: int
    interpolated_count: int
    tracked_count: int
    endframe_count: int
    is_startframe: bool
    is_inactive: bool
    has_selected_points: bool

    def __init__(self, frame_number: int, parent: QWidget | None = None):
        """Initialize frame tab.

        Args:
            frame_number: The frame number this tab represents
            parent: Parent widget
        """
        super().__init__(parent)

        # Initialize colors if needed
        self._init_colors()

        self.frame_number = frame_number
        self.is_current_frame = False
        self.is_hovered = False

        # Point status information
        self.point_count = 0
        self.keyframe_count = 0
        self.interpolated_count = 0
        self.tracked_count = 0
        self.endframe_count = 0
        self.is_startframe = False
        self.is_inactive = False
        self.has_selected_points = False

        # Setup widget
        self._setup_widget()

    def _setup_widget(self):
        """Setup widget properties and policies."""
        # Dynamic width, fixed height
        self.setMinimumHeight(self.TAB_HEIGHT)
        self.setMaximumHeight(self.TAB_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

        # Set tooltip
        self._update_tooltip()

    def set_tab_width(self, width: int):
        """Set the width of the tab dynamically.

        Args:
            width: Width in pixels for this tab
        """
        self.setFixedWidth(max(self.MIN_WIDTH, min(width, self.MAX_WIDTH)))
        self.update()

    def set_point_status(
        self,
        keyframe_count: int = 0,
        interpolated_count: int = 0,
        tracked_count: int = 0,
        endframe_count: int = 0,
        is_startframe: bool = False,
        is_inactive: bool = False,
        has_selected: bool = False,
    ):
        """Update point status information for this frame.

        Args:
            keyframe_count: Number of keyframe points
            interpolated_count: Number of interpolated points
            tracked_count: Number of tracked points
            endframe_count: Number of endframe points
            is_startframe: Whether this frame contains a startframe
            is_inactive: Whether this frame is in an inactive segment
            has_selected: Whether this frame has selected points
        """
        self.keyframe_count = keyframe_count
        self.interpolated_count = interpolated_count
        self.tracked_count = tracked_count
        self.endframe_count = endframe_count
        self.is_startframe = is_startframe
        self.is_inactive = is_inactive
        self.point_count = keyframe_count + interpolated_count + tracked_count + endframe_count
        self.has_selected_points = has_selected

        self._update_tooltip()
        self.update()  # Trigger repaint

    def set_current_frame(self, is_current: bool):
        """Set whether this is the current frame.

        Args:
            is_current: True if this is the current frame
        """
        if self.is_current_frame != is_current:
            self.is_current_frame = is_current
            self.update()  # Trigger repaint

    def _update_tooltip(self):
        """Update tooltip text based on current status."""
        # Always show frame number in tooltip since it's not displayed on tab
        if self.is_inactive:
            tooltip = f"Frame {self.frame_number}: Inactive segment"
        elif self.point_count == 0:
            tooltip = f"Frame {self.frame_number}: No tracked points"
        else:
            parts = []
            if self.is_startframe:
                parts.append("STARTFRAME")
            if self.keyframe_count > 0:
                parts.append(f"{self.keyframe_count} keyframe")
            if self.tracked_count > 0:
                parts.append(f"{self.tracked_count} tracked")
            if self.interpolated_count > 0:
                parts.append(f"{self.interpolated_count} interpolated")
            if self.endframe_count > 0:
                parts.append(f"{self.endframe_count} ENDFRAME")

            status = ", ".join(parts)
            tooltip = f"Frame {self.frame_number}: {status}"

            if self.has_selected_points:
                tooltip += " (selected)"

        self.setToolTip(tooltip)

    def _get_background_color(self) -> QColor:
        """Get background color based on current status."""
        # Priority order: selected > inactive > specific states > mixed
        if self.has_selected_points:
            return self.COLORS["selected"]

        if self.is_inactive:
            return self.COLORS["inactive"]

        # Determine color based on point status
        if self.point_count == 0:
            return self.COLORS["no_points"]

        # Specific state priorities
        if self.endframe_count > 0:
            return self.COLORS["endframe"]
        elif self.is_startframe:
            return self.COLORS["startframe"]
        elif self.tracked_count > 0 and self.keyframe_count == 0 and self.interpolated_count == 0:
            return self.COLORS["tracked"]
        elif self.keyframe_count > 0 and self.interpolated_count == 0 and self.tracked_count == 0:
            return self.COLORS["keyframe"]
        elif self.interpolated_count > 0 and self.keyframe_count == 0 and self.tracked_count == 0:
            return self.COLORS["interpolated"]
        else:
            # Mixed states
            return self.COLORS["mixed"]

    def _get_text_color(self) -> QColor:
        """Get text color - always white in 3DE style."""
        return self.COLORS["text"]  # Always white

    def paintEvent(self, event: QPaintEvent) -> None:
        """Custom paint for frame tab appearance."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        # Draw background with optional gradient for depth
        bg_color = self._get_background_color()
        if self.is_hovered and not self.is_current_frame:
            # Very subtle hover effect
            bg_color = bg_color.lighter(105)

        # Create subtle gradient for depth (3DE style)
        from PySide6.QtGui import QLinearGradient

        gradient = QLinearGradient(0, 0, 0, rect.height())
        gradient.setColorAt(0, bg_color.lighter(110))
        gradient.setColorAt(0.5, bg_color)
        gradient.setColorAt(1, bg_color.darker(110))

        # Use golden border for current frame, subtle border otherwise
        if self.is_current_frame:
            # Draw golden border for current frame
            painter.setPen(QPen(self.COLORS["current_border"], 2))
            painter.setBrush(QBrush(gradient))
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
        else:
            # Draw with subtle border
            painter.setPen(QPen(self.COLORS["border"], self.BORDER_WIDTH))
            painter.setBrush(QBrush(gradient))
            painter.drawRect(rect)

        # No frame numbers on tabs in 3DE style - just colored bars
        # Frame number is shown in tooltip on hover

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for frame selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.frame_clicked.emit(self.frame_number)
        super().mousePressEvent(event)

    def enterEvent(self, event: QEnterEvent) -> None:
        """Handle mouse enter for hover effect."""
        self.is_hovered = True
        self.frame_hovered.emit(self.frame_number)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEnterEvent) -> None:
        """Handle mouse leave."""
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Handle right-click context menu (future feature)."""
        # TODO: Implement context menu with options like:
        # - Jump to frame
        # - Set as keyframe
        # - Interpolate from previous
        # - Copy frame data
        pass

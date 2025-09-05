#!/usr/bin/env python
"""
Individual Frame Tab Component for Timeline

Represents a single frame in the timeline with color coding based on point status.
Similar to 3DEqualizer frame tabs with visual indicators for tracking status.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QMouseEvent, QPainter, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget


class FrameTab(QWidget):
    """Individual frame tab with color coding and click interaction."""

    # Signals
    frame_clicked = Signal(int)  # Emitted when tab is clicked
    frame_hovered = Signal(int)  # Emitted when tab is hovered

    # Tab appearance constants - compact 3DE style
    TAB_WIDTH = 40
    TAB_HEIGHT = 24
    BORDER_WIDTH = 1
    CORNER_RADIUS = 2

    # Color scheme for frame status - professional 3DE style
    COLORS = {
        "no_points": QColor(45, 45, 45),  # Dark gray - no tracked points
        "keyframe": QColor(70, 140, 70),  # Muted green - has keyframe points
        "interpolated": QColor(140, 120, 60),  # Muted yellow/brown - only interpolated points
        "mixed": QColor(70, 100, 140),  # Muted blue - mixed keyframe/interpolated
        "current_frame": QColor(45, 45, 45),  # Same as no_points, highlight with border
        "current_border": QColor(220, 180, 0),  # Golden border for current frame
        "selected": QColor(160, 60, 60),  # Muted red for selected points
        "border": QColor(30, 30, 30),  # Darker border
        "text": QColor(200, 200, 200),  # Softer text for dark backgrounds
        "text_current": QColor(255, 220, 100),  # Golden text for current frame
    }

    def __init__(self, frame_number: int, parent=None):
        """Initialize frame tab.

        Args:
            frame_number: The frame number this tab represents
            parent: Parent widget
        """
        super().__init__(parent)

        self.frame_number = frame_number
        self.is_current_frame = False
        self.is_hovered = False

        # Point status information
        self.point_count = 0
        self.keyframe_count = 0
        self.interpolated_count = 0
        self.has_selected_points = False

        # Setup widget
        self._setup_widget()

    def _setup_widget(self):
        """Setup widget properties and policies."""
        # Fixed size for consistent appearance
        self.setFixedSize(self.TAB_WIDTH, self.TAB_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        # Enable mouse tracking for hover effects
        self.setMouseTracking(True)

        # Set tooltip
        self._update_tooltip()

    def set_point_status(self, keyframe_count: int = 0, interpolated_count: int = 0, has_selected: bool = False):
        """Update point status information for this frame.

        Args:
            keyframe_count: Number of keyframe/manually tracked points
            interpolated_count: Number of interpolated points
            has_selected: Whether this frame has selected points
        """
        self.keyframe_count = keyframe_count
        self.interpolated_count = interpolated_count
        self.point_count = keyframe_count + interpolated_count
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
        if self.point_count == 0:
            tooltip = f"Frame {self.frame_number}: No tracked points"
        else:
            parts = []
            if self.keyframe_count > 0:
                parts.append(f"{self.keyframe_count} keyframe")
            if self.interpolated_count > 0:
                parts.append(f"{self.interpolated_count} interpolated")

            status = ", ".join(parts)
            tooltip = f"Frame {self.frame_number}: {status} points"

            if self.has_selected_points:
                tooltip += " (selected)"

        self.setToolTip(tooltip)

    def _get_background_color(self) -> QColor:
        """Get background color based on current status."""
        # Priority order: selected > point status (current frame uses border highlight)
        if self.has_selected_points:
            return self.COLORS["selected"]

        # Determine color based on point status
        if self.point_count == 0:
            return self.COLORS["no_points"]
        elif self.keyframe_count > 0 and self.interpolated_count > 0:
            return self.COLORS["mixed"]
        elif self.keyframe_count > 0:
            return self.COLORS["keyframe"]
        else:
            return self.COLORS["interpolated"]

    def _get_text_color(self) -> QColor:
        """Get text color based on background."""
        if self.is_current_frame:
            return self.COLORS["text_current"]
        return self.COLORS["text"]

    def paintEvent(self, event):
        """Custom paint for frame tab appearance."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        # Draw background
        bg_color = self._get_background_color()
        if self.is_hovered and not self.is_current_frame:
            # Slightly lighter on hover (except current frame)
            bg_color = bg_color.lighter(115)

        # Use golden border for current frame, normal border otherwise
        border_color = self.COLORS["current_border"] if self.is_current_frame else self.COLORS["border"]
        border_width = 2 if self.is_current_frame else self.BORDER_WIDTH

        painter.setPen(QPen(border_color, border_width))
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(
            rect.adjusted(1, 1, -1, -1) if self.is_current_frame else rect, self.CORNER_RADIUS, self.CORNER_RADIUS
        )

        # Draw frame number
        painter.setPen(QPen(self._get_text_color()))

        # Use smaller font for compact tabs
        font = QFont("Arial", 9)
        font.setBold(self.is_current_frame)
        font.setWeight(QFont.Weight.Bold if self.is_current_frame else QFont.Weight.Normal)
        painter.setFont(font)

        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(self.frame_number))

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for frame selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.frame_clicked.emit(self.frame_number)
        super().mousePressEvent(event)

    def enterEvent(self, event):
        """Handle mouse enter for hover effect."""
        self.is_hovered = True
        self.frame_hovered.emit(self.frame_number)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        """Handle mouse leave."""
        self.is_hovered = False
        self.update()
        super().leaveEvent(event)

    def contextMenuEvent(self, event):
        """Handle right-click context menu (future feature)."""
        # TODO: Implement context menu with options like:
        # - Jump to frame
        # - Set as keyframe
        # - Interpolate from previous
        # - Copy frame data
        pass

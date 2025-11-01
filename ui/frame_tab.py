#!/usr/bin/env python
"""
Individual Frame Tab Component for Timeline

Represents a single frame in the timeline with color coding based on point status.
Similar to 3DEqualizer frame tabs with visual indicators for tracking status.
"""

from typing import ClassVar
from typing_extensions import override
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QContextMenuEvent, QEnterEvent, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget


class StatusColorResolver:
    """Centralized logic for determining frame tab colors based on point status.

    ARCHITECTURAL PRINCIPLE:
    ========================
    Visual appearance reflects both point data status AND segment activity.

    - Point status (NORMAL, KEYFRAME, TRACKED, etc.) determines color
    - Segment activity (active/inactive) affects BOTH line rendering AND gap frame colors
    - Inactive gap segments (frames after ENDFRAME until next KEYFRAME) use dark gray

    Priority Order:
    ===============
    1. Selected (user selection - highest priority)
    2. Endframe (segment boundary marker - red/cyan)
    3. Inactive gap segments (dark gray for frames in gaps)
    4. No points (regular gaps - lighter gray)
    5. Startframe (segment start marker)
    6. Single status (tracked, keyframe, interpolated, normal)
    7. Mixed (multiple statuses present)

    Historical Context:
    ===================
    Inactive gap segments are frames between ENDFRAME and the next KEYFRAME where
    the curve is not active. These frames return held positions (ENDFRAME coords)
    and are rendered with dashed lines. The timeline uses dark gray (30,30,30) to
    visually distinguish gap segments from regular "no data" frames.
    """

    @staticmethod
    def get_background_color(
        colors: dict[str, QColor],
        *,
        point_count: int,
        keyframe_count: int,
        interpolated_count: int,
        tracked_count: int,
        endframe_count: int,
        normal_count: int,
        is_startframe: bool,
        has_selected_points: bool,
        is_inactive: bool = False,
    ) -> QColor:
        """Determine background color based on point status counts.

        Args:
            colors: Dictionary mapping status names to QColor objects
            point_count: Total number of points
            keyframe_count: Number of keyframe points
            interpolated_count: Number of interpolated points
            tracked_count: Number of tracked points
            endframe_count: Number of endframe points
            normal_count: Number of normal points
            is_startframe: Whether this is a startframe
            has_selected_points: Whether frame has selected points
            is_inactive: Whether this frame is in an inactive gap segment

        Returns:
            QColor appropriate for the frame's status
        """
        # Priority 1: Selection overrides everything
        if has_selected_points:
            return colors["selected"]

        # Priority 2: Endframes (segment boundaries)
        if endframe_count > 0:
            return colors["endframe"]

        # Priority 3: Inactive segments (frames after ENDFRAME until next KEYFRAME)
        # This applies to both frames with points and gap frames
        if is_inactive:
            return colors["inactive"]

        # Priority 4: No points (regular gaps between keyframes, or frames without data)
        if point_count == 0:
            return colors["no_points"]

        # Priority 5: Startframe (segment start)
        if is_startframe:
            return colors["startframe"]

        # Priority 6: Single status types (pure states)
        if tracked_count > 0 and keyframe_count == 0 and interpolated_count == 0 and normal_count == 0:
            return colors["tracked"]
        if keyframe_count > 0 and interpolated_count == 0 and tracked_count == 0 and normal_count == 0:
            return colors["keyframe"]
        if interpolated_count > 0 and keyframe_count == 0 and tracked_count == 0 and normal_count == 0:
            return colors["interpolated"]
        if normal_count > 0 and keyframe_count == 0 and interpolated_count == 0 and tracked_count == 0:
            return colors["normal"]

        # Priority 7: Mixed states (multiple statuses)
        return colors["mixed"]


class FrameTab(QWidget):
    """Individual frame tab with color coding and click interaction."""

    # Signals
    frame_clicked: ClassVar[Signal] = Signal(int)  # Emitted when tab is clicked (frame_number)
    frame_hovered: ClassVar[Signal] = Signal(int)  # Emitted when tab is hovered (frame_number)

    # Tab appearance constants - modern 3DE style
    TAB_HEIGHT: int = 38  # Taller tabs for better visibility
    BORDER_WIDTH: int = 1
    CORNER_RADIUS: int = 0  # No rounded corners for seamless look
    MIN_WIDTH: int = 2  # Minimum width for very large frame ranges
    MAX_WIDTH: int = 60  # Maximum width for small frame ranges

    # Color scheme for frame status - uses dark theme
    # Initialize colors on first use to avoid import issues
    _colors_cache: ClassVar[dict[str, QColor]] = {}

    @classmethod
    def _init_colors(cls) -> None:
        """Initialize colors from centralized theme."""
        if not cls._colors_cache:
            from ui.color_manager import COLORS_DARK, STATUS_COLORS_TIMELINE

            cls._colors_cache = {
                "no_points": QColor(*STATUS_COLORS_TIMELINE["no_points"]),
                "normal": QColor(*STATUS_COLORS_TIMELINE["normal"]),
                "keyframe": QColor(*STATUS_COLORS_TIMELINE["keyframe"]),
                "interpolated": QColor(*STATUS_COLORS_TIMELINE["interpolated"]),
                "tracked": QColor(*STATUS_COLORS_TIMELINE["tracked"]),
                "endframe": QColor(*STATUS_COLORS_TIMELINE["endframe"]),
                "startframe": QColor(*STATUS_COLORS_TIMELINE["startframe"]),
                "inactive": QColor(*STATUS_COLORS_TIMELINE["inactive"]),
                "mixed": QColor(*STATUS_COLORS_TIMELINE["mixed"]),
                "current_frame": QColor(COLORS_DARK["bg_secondary"]),  # Same as no_points, highlight with border
                "current_border": QColor(COLORS_DARK["accent_warning"]),  # Warning color for current frame
                "selected": QColor(*STATUS_COLORS_TIMELINE["selected"]),  # Selected state color
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
    normal_count: int
    is_startframe: bool
    is_inactive: bool
    has_selected_points: bool

    def __init__(self, frame_number: int, parent: QWidget | None = None):
        """Initialize frame tab.

        Args:
            frame_number: The frame number this tab represents
            parent: Parent widget
        """
        # Check if parent is still valid before initializing
        # This prevents RuntimeError when parent C++ object is deleted
        if parent is not None:
            try:
                # Try to access a property to check if C++ object is valid
                _ = parent.isVisible()
            except RuntimeError:
                # Parent C++ object is deleted, don't create this widget
                # Set a minimal state to prevent further errors
                self.frame_number = frame_number
                self.is_current_frame = False
                return

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
        self.normal_count = 0
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
        normal_count: int = 0,
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
            normal_count: Number of normal points
            is_startframe: Whether this frame contains a startframe
            is_inactive: Whether this frame is in an inactive segment
            has_selected: Whether this frame has selected points
        """
        self.keyframe_count = keyframe_count
        self.interpolated_count = interpolated_count
        self.tracked_count = tracked_count
        self.endframe_count = endframe_count
        self.normal_count = normal_count
        self.is_startframe = is_startframe
        self.is_inactive = is_inactive
        self.point_count = keyframe_count + interpolated_count + tracked_count + endframe_count + normal_count
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

    def _update_tooltip(self) -> None:
        """Update tooltip text based on current status."""
        # Always show frame number in tooltip since it's not displayed on tab
        if self.point_count == 0:
            tooltip = f"Frame {self.frame_number}: No tracked points"
            if self.is_inactive:
                tooltip += " (inactive segment)"
        else:
            parts: list[str] = []
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
            if self.normal_count > 0:
                parts.append(f"{self.normal_count} normal")

            status = ", ".join(parts)
            # Add "points" at the end for consistency with tests
            tooltip = f"Frame {self.frame_number}: {status} points"

            if self.has_selected_points:
                tooltip += " (selected)"
            if self.is_inactive:
                tooltip += " (inactive segment)"

        self.setToolTip(tooltip)

    def _get_background_color(self) -> QColor:
        """Get background color based on current status.

        Delegates to StatusColorResolver for centralized, consistent color logic.
        See StatusColorResolver class documentation for architectural principles.
        """
        return StatusColorResolver.get_background_color(
            self._colors_cache,
            point_count=self.point_count,
            keyframe_count=self.keyframe_count,
            interpolated_count=self.interpolated_count,
            tracked_count=self.tracked_count,
            endframe_count=self.endframe_count,
            normal_count=self.normal_count,
            is_startframe=self.is_startframe,
            has_selected_points=self.has_selected_points,
            is_inactive=self.is_inactive,
        )

    def _get_text_color(self) -> QColor:
        """Get text color - always white in 3DE style."""
        return self._colors_cache["text"]  # Always white

    @override
    def paintEvent(self, event: QPaintEvent) -> None:
        """Custom paint for frame tab appearance."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()

        # Draw background with optional gradient for depth
        bg_color = self._get_background_color()
        # Hover effect removed - no visual change on hover

        # Create subtle gradient for depth (3DE style)
        from PySide6.QtGui import QLinearGradient

        gradient = QLinearGradient(0, 0, 0, rect.height())
        gradient.setColorAt(0, bg_color.lighter(110))
        gradient.setColorAt(0.5, bg_color)
        gradient.setColorAt(1, bg_color.darker(110))

        # Use golden border for current frame, subtle border otherwise
        if self.is_current_frame:
            # Draw golden border for current frame
            painter.setPen(QPen(self._colors_cache["current_border"], 2))
            painter.setBrush(QBrush(gradient))
            painter.drawRect(rect.adjusted(1, 1, -1, -1))
        else:
            # Draw with subtle border
            painter.setPen(QPen(self._colors_cache["border"], self.BORDER_WIDTH))
            painter.setBrush(QBrush(gradient))
            painter.drawRect(rect)

        # No frame numbers on tabs in 3DE style - just colored bars
        # Frame number is shown in tooltip on hover

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse press for frame selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            self.frame_clicked.emit(self.frame_number)
        super().mousePressEvent(event)

    @override
    def enterEvent(self, event: QEnterEvent) -> None:
        """Handle mouse enter for hover tracking."""
        self.is_hovered = True
        # frame_hovered signal removed - no action needed on hover
        super().enterEvent(event)

    @override
    def leaveEvent(self, event: QEvent) -> None:
        """Handle mouse leave."""
        self.is_hovered = False
        # No visual update needed since hover effect is removed
        super().leaveEvent(event)

    @override
    def contextMenuEvent(self, event: QContextMenuEvent) -> None:
        """Handle right-click context menu (future feature)."""
        # TODO: Implement context menu with options like:
        # - Jump to frame
        # - Set as keyframe
        # - Interpolate from previous
        # - Copy frame data

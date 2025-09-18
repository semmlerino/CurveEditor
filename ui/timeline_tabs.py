#!/usr/bin/env python
"""
Tabbed Timeline Widget for CurveEditor

A frame-based timeline widget similar to 3DEqualizer that displays frame tabs
with color coding to indicate tracking point status at each frame.
Supports horizontal scrolling for many frames with performance optimizations.
"""

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QMouseEvent, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.logger_utils import get_logger
from core.models import FrameNumber

# animation_utils removed - using direct connections instead
from ui.frame_tab import FrameTab

logger = get_logger(__name__)


class TimelineScrollArea(QScrollArea):
    """Custom scroll area optimized for timeline tabs."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Configure scroll area
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        # Smooth scrolling - this method may not exist in all PySide6 versions
        # Commented out due to type checking issues with PySide6 versions
        # try:
        #     self.setHorizontalScrollMode(QScrollArea.ScrollMode.ScrollPerPixel)
        # except AttributeError:
        #     # Fallback for older PySide6 versions
        #     pass

    def wheelEvent(self, arg__1: QWheelEvent) -> None:
        """Handle mouse wheel for horizontal scrolling."""
        # Convert vertical wheel events to horizontal scrolling
        if arg__1.angleDelta().y() != 0:
            # Scroll horizontally instead of vertically
            scroll_bar = self.horizontalScrollBar()
            delta = -arg__1.angleDelta().y()  # Invert for natural scrolling
            scroll_bar.setValue(scroll_bar.value() + delta)
            arg__1.accept()
        else:
            super().wheelEvent(arg__1)


class FrameStatusCache:
    """Cache for frame point status to improve performance."""

    # Attributes - initialized in __init__
    _cache: dict[FrameNumber, tuple[int, int, int, int, int, bool, bool, bool]]
    _dirty_frames: set[FrameNumber]

    def __init__(self) -> None:
        """Initialize empty cache."""
        self._cache = {}
        self._dirty_frames = set()

    def get_status(self, frame: FrameNumber) -> tuple[int, int, int, int, int, bool, bool, bool] | None:
        """Get cached status for frame.

        Args:
            frame: Frame number

        Returns:
            Tuple of (keyframe_count, interpolated_count, tracked_count, endframe_count,
                     normal_count, is_startframe, is_inactive, has_selected) or None if not cached
        """
        return self._cache.get(frame)

    def set_status(
        self,
        frame: FrameNumber,
        keyframe_count: int,
        interpolated_count: int,
        tracked_count: int = 0,
        endframe_count: int = 0,
        normal_count: int = 0,
        is_startframe: bool = False,
        is_inactive: bool = False,
        has_selected: bool = False,
    ) -> None:
        """Cache status for frame.

        Args:
            frame: Frame number
            keyframe_count: Number of keyframe points
            interpolated_count: Number of interpolated points
            tracked_count: Number of tracked points
            endframe_count: Number of endframe points
            normal_count: Number of normal points
            is_startframe: Whether frame has a startframe
            is_inactive: Whether frame is in an inactive segment
            has_selected: Whether frame has selected points
        """
        self._cache[frame] = (
            keyframe_count,
            interpolated_count,
            tracked_count,
            endframe_count,
            normal_count,
            is_startframe,
            is_inactive,
            has_selected,
        )
        self._dirty_frames.discard(frame)

    def invalidate_frame(self, frame: FrameNumber) -> None:
        """Mark frame as needing update."""
        self._dirty_frames.add(frame)

    def invalidate_all(self) -> None:
        """Mark all frames as needing update."""
        self._dirty_frames.update(self._cache.keys())

    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        self._dirty_frames.clear()


class TimelineTabWidget(QWidget):
    """Main timeline widget with frame tabs and navigation."""

    # Signals
    frame_changed: Signal = Signal(int)
    frame_hovered: Signal = Signal(int)

    # Layout constants
    TAB_SPACING: int = 0  # No spacing for seamless look
    NAVIGATION_HEIGHT: int = 20  # Ultra-compact navigation bar
    TOTAL_HEIGHT: int = 60  # Height: 20px nav + 40px scroll area

    # State variables - initialized in __init__
    current_frame: int
    total_frames: int
    min_frame: int
    max_frame: int
    frame_tabs: dict[FrameNumber, "FrameTab"]
    is_scrubbing: bool
    scrub_start_frame: int
    status_cache: FrameStatusCache
    _update_timer: QTimer

    # UI components - initialized in _setup_ui
    main_layout: QVBoxLayout  # pyright: ignore[reportUninitializedInstanceVariable]
    first_btn: QPushButton  # pyright: ignore[reportUninitializedInstanceVariable]
    prev_group_btn: QPushButton  # pyright: ignore[reportUninitializedInstanceVariable]
    next_group_btn: QPushButton  # pyright: ignore[reportUninitializedInstanceVariable]
    last_btn: QPushButton  # pyright: ignore[reportUninitializedInstanceVariable]
    frame_info: QLabel  # pyright: ignore[reportUninitializedInstanceVariable]
    scroll_area: TimelineScrollArea  # pyright: ignore[reportUninitializedInstanceVariable]
    tabs_container: QWidget  # pyright: ignore[reportUninitializedInstanceVariable]
    tabs_layout: QHBoxLayout  # pyright: ignore[reportUninitializedInstanceVariable]

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize timeline widget."""
        super().__init__(parent)

        # Set minimum and fixed height to ensure proper display
        self.setMinimumHeight(self.TOTAL_HEIGHT)
        self.setFixedHeight(self.TOTAL_HEIGHT)
        self.setMaximumHeight(self.TOTAL_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        # Apply minimal styling - inherits from application dark theme
        # Only override specific timeline-specific styles
        self.setStyleSheet("""
            TimelineTabWidget {
                border-top: 1px solid #495057;
                border-bottom: 1px solid #495057;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 10px;
                padding: 0;
                min-width: 16px;
            }
            QLabel {
                font-size: 10px;
                font-family: monospace;
            }
        """)

        # State - start with minimal range, will be updated when data is loaded
        self.current_frame = 1
        self.total_frames = 1
        self.min_frame = 1
        self.max_frame = 1

        # Tab management
        self.frame_tabs = {}

        # Scrubbing state
        self.is_scrubbing = False
        self.scrub_start_frame = 1

        # Performance optimization
        self.status_cache = FrameStatusCache()
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        _ = self._update_timer.timeout.connect(self._perform_deferred_updates)

        # Setup UI
        self._setup_ui()

        # Enable mouse tracking for scrubbing
        self.setMouseTracking(True)

    def _setup_ui(self) -> None:
        """Setup the timeline UI components."""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)  # No spacing between elements

        # Navigation controls
        self._create_navigation_controls()

        # Scrollable timeline
        self._create_timeline_area()

        # Initialize with default range
        self._create_all_tabs()

    def _create_navigation_controls(self) -> None:
        """Create navigation buttons and frame info."""
        nav_widget = QWidget()
        nav_widget.setFixedHeight(self.NAVIGATION_HEIGHT)
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(4, 2, 4, 2)

        # Navigation buttons - ultra-small and minimal
        button_size = 16
        self.first_btn = QPushButton("⏮")
        self.first_btn.setFixedSize(button_size, button_size)
        self.first_btn.setToolTip("Go to first frame")
        self.first_btn.clicked.connect(lambda: self.set_current_frame(self.min_frame))

        self.prev_group_btn = QPushButton("⏪")
        self.prev_group_btn.setFixedSize(button_size, button_size)
        self.prev_group_btn.setToolTip("Jump back 10 frames")
        _ = self.prev_group_btn.clicked.connect(self._jump_back_group)

        self.next_group_btn = QPushButton("⏩")
        self.next_group_btn.setFixedSize(button_size, button_size)
        self.next_group_btn.setToolTip("Jump forward 10 frames")
        _ = self.next_group_btn.clicked.connect(self._jump_forward_group)

        self.last_btn = QPushButton("⏭")
        self.last_btn.setFixedSize(button_size, button_size)
        self.last_btn.setToolTip("Go to last frame")
        self.last_btn.clicked.connect(lambda: self.set_current_frame(self.max_frame))

        # Frame info label - accent color for better visibility
        self.frame_info = QLabel()
        self.frame_info.setStyleSheet(
            "QLabel { color: #ffd43b; font-size: 10px; font-weight: normal; font-family: monospace; }"
        )
        self._update_frame_info()

        # Layout navigation
        nav_layout.addWidget(self.first_btn)
        nav_layout.addWidget(self.prev_group_btn)
        nav_layout.addStretch()
        nav_layout.addWidget(self.frame_info)
        nav_layout.addStretch()
        nav_layout.addWidget(self.next_group_btn)
        nav_layout.addWidget(self.last_btn)

        self.main_layout.addWidget(nav_widget)

    def _create_timeline_area(self) -> None:
        """Create scrollable timeline area."""
        # Create scroll area (but disable scrolling - we show all frames)
        self.scroll_area = TimelineScrollArea(self)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setMinimumHeight(40)  # Minimum for 38px tabs
        self.scroll_area.setFixedHeight(40)  # Fixed height for 38px tabs

        # Create container widget for tabs
        self.tabs_container = QWidget()
        self.tabs_container.setMinimumHeight(38)  # Ensure tabs get their full height
        self.tabs_container.setMaximumHeight(38)  # Prevent compression
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(0, 0, 0, 0)  # No margins for maximum space
        self.tabs_layout.setSpacing(self.TAB_SPACING)  # 0 for seamless
        self.tabs_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.scroll_area.setWidget(self.tabs_container)
        self.main_layout.addWidget(self.scroll_area)

    def set_frame_range(self, min_frame: int, max_frame: int) -> None:
        """Set the frame range for the timeline.

        Args:
            min_frame: Minimum frame number
            max_frame: Maximum frame number
        """
        self.min_frame = min_frame
        self.max_frame = max_frame
        self.total_frames = max_frame - min_frame + 1

        # Update current frame if out of range
        if self.current_frame < min_frame:
            self.current_frame = min_frame
        elif self.current_frame > max_frame:
            self.current_frame = max_frame

        # Clear cache and recreate all tabs
        self.status_cache.clear()
        self._create_all_tabs()
        self._update_frame_info()

    def set_current_frame(self, frame: int) -> None:
        """Set current frame and update display.

        Args:
            frame: Frame number to set as current
        """
        # Clamp to valid range
        frame = max(self.min_frame, min(self.max_frame, frame))

        if frame != self.current_frame:
            # Update old frame tab
            if self.current_frame in self.frame_tabs:
                self.frame_tabs[self.current_frame].set_current_frame(False)

            self.current_frame = frame

            # Update new frame tab
            if frame in self.frame_tabs:
                self.frame_tabs[frame].set_current_frame(True)

            # Update frame info
            self._update_frame_info()

            # Emit signal
            self.frame_changed.emit(frame)

    def update_frame_status(
        self,
        frame: int,
        keyframe_count: int = 0,
        interpolated_count: int = 0,
        tracked_count: int = 0,
        endframe_count: int = 0,
        normal_count: int = 0,
        is_startframe: bool = False,
        is_inactive: bool = False,
        has_selected: bool = False,
    ) -> None:
        """Update comprehensive point status for a specific frame.

        Args:
            frame: Frame number
            keyframe_count: Number of keyframe points
            interpolated_count: Number of interpolated points
            tracked_count: Number of tracked points
            endframe_count: Number of endframe points
            normal_count: Number of normal points
            is_startframe: Whether frame has a startframe
            is_inactive: Whether frame is in an inactive segment
            has_selected: Whether frame has selected points
        """
        # Update cache with all status information
        self.status_cache.set_status(
            frame,
            keyframe_count,
            interpolated_count,
            tracked_count,
            endframe_count,
            normal_count,
            is_startframe,
            is_inactive,
            has_selected,
        )

        # Update tab if visible with all status parameters
        if frame in self.frame_tabs:
            tab = self.frame_tabs[frame]
            tab.set_point_status(
                keyframe_count=keyframe_count,
                interpolated_count=interpolated_count,
                tracked_count=tracked_count,
                endframe_count=endframe_count,
                is_startframe=is_startframe,
                is_inactive=is_inactive,
                has_selected=has_selected,
            )

    def invalidate_frame_status(self, frame: int) -> None:
        """Mark frame status as needing update.

        Args:
            frame: Frame number to invalidate
        """
        self.status_cache.invalidate_frame(frame)

        # Schedule deferred update
        self._schedule_deferred_update()

    def invalidate_all_frames(self) -> None:
        """Mark all frame statuses as needing update."""
        self.status_cache.invalidate_all()
        self._schedule_deferred_update()

    def _calculate_tab_width(self) -> int:
        """Calculate optimal tab width based on available space and frame count."""
        # Use parent width if available, otherwise use a default
        if self.parent():
            available_width = (
                self.parent().width() - 100
            )  # Subtract space for nav buttons and margins  # pyright: ignore[reportAttributeAccessIssue]
        else:
            available_width = 1300  # Default for 1400px window

        # Minimum reasonable width
        if available_width < 200:
            available_width = 1300

        frame_count = self.max_frame - self.min_frame + 1

        if frame_count == 0:
            return 30  # Default width

        # Calculate width per tab
        tab_width = available_width // frame_count

        # Clamp to reasonable limits
        from ui.frame_tab import FrameTab

        return max(FrameTab.MIN_WIDTH, min(tab_width, FrameTab.MAX_WIDTH))

    def _create_all_tabs(self) -> None:
        """Create tabs for all frames with dynamic width."""
        # Clear existing tabs
        for tab in self.frame_tabs.values():
            self.tabs_layout.removeWidget(tab)
            tab.deleteLater()
        self.frame_tabs.clear()

        # Calculate optimal tab width
        tab_width = self._calculate_tab_width()

        # Create tabs for entire frame range
        for frame in range(self.min_frame, self.max_frame + 1):
            tab = FrameTab(frame, self)
            tab.set_tab_width(tab_width)
            _ = tab.frame_clicked.connect(self.set_current_frame)
            _ = tab.frame_hovered.connect(self.frame_hovered.emit)

            # Set current frame status
            if frame == self.current_frame:
                tab.set_current_frame(True)

            # Apply cached status if available with all fields
            cached_status = self.status_cache.get_status(frame)
            if cached_status:
                (
                    keyframe_count,
                    interpolated_count,
                    tracked_count,
                    endframe_count,
                    normal_count,
                    is_startframe,
                    is_inactive,
                    has_selected,
                ) = cached_status
                tab.set_point_status(
                    keyframe_count=keyframe_count,
                    interpolated_count=interpolated_count,
                    tracked_count=tracked_count,
                    endframe_count=endframe_count,
                    is_startframe=is_startframe,
                    is_inactive=is_inactive,
                    has_selected=has_selected,
                )

            self.frame_tabs[frame] = tab
            self.tabs_layout.addWidget(tab)

        # Update container size to fit all tabs
        total_width = tab_width * len(self.frame_tabs) + 4
        self.tabs_container.setMinimumWidth(total_width)

    def _ensure_frame_visible(self, frame: int) -> None:
        """Ensure the specified frame is visible (no-op since all frames are visible)."""
        # All frames are always visible with dynamic width
        pass

    def _update_frame_info(self) -> None:
        """Update frame information label."""
        info_text = f"Frame {self.current_frame:3d} | 1-{self.max_frame:3d}"
        self.frame_info.setText(info_text)

    def _jump_back_group(self) -> None:
        """Jump back by group size."""
        new_frame = max(self.min_frame, self.current_frame - 10)
        self.set_current_frame(new_frame)

    def _jump_forward_group(self) -> None:
        """Jump forward by group size."""
        new_frame = min(self.max_frame, self.current_frame + 10)
        self.set_current_frame(new_frame)

    def _schedule_deferred_update(self) -> None:
        """Schedule a deferred update to avoid excessive redraws."""
        if not self._update_timer.isActive():
            self._update_timer.start(50)  # 50ms delay

    def _perform_deferred_updates(self) -> None:
        """Perform any pending status updates."""
        # This would query the data service for updated point statuses
        # Refresh visible tabs with all status fields
        for frame, tab in self.frame_tabs.items():
            cached_status = self.status_cache.get_status(frame)
            if cached_status:
                (
                    keyframe_count,
                    interpolated_count,
                    tracked_count,
                    endframe_count,
                    normal_count,
                    is_startframe,
                    is_inactive,
                    has_selected,
                ) = cached_status
                tab.set_point_status(
                    keyframe_count=keyframe_count,
                    interpolated_count=interpolated_count,
                    tracked_count=tracked_count,
                    endframe_count=endframe_count,
                    is_startframe=is_startframe,
                    is_inactive=is_inactive,
                    has_selected=has_selected,
                )

    def resizeEvent(self, event: QResizeEvent) -> None:
        """Handle widget resize to recalculate tab widths."""
        super().resizeEvent(event)

        # Recalculate tab width for new size
        if self.frame_tabs:
            tab_width = self._calculate_tab_width()

            # Update width of all existing tabs
            for tab in self.frame_tabs.values():
                tab.set_tab_width(tab_width)

            # Update container size
            total_width = tab_width * len(self.frame_tabs) + 4
            self.tabs_container.setMinimumWidth(total_width)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard navigation."""
        if event.key() == Qt.Key.Key_Left:
            self.set_current_frame(self.current_frame - 1)
            event.accept()
        elif event.key() == Qt.Key.Key_Right:
            self.set_current_frame(self.current_frame + 1)
            event.accept()
        elif event.key() == Qt.Key.Key_Home:
            self.set_current_frame(self.min_frame)
            event.accept()
        elif event.key() == Qt.Key.Key_End:
            self.set_current_frame(self.max_frame)
            event.accept()
        elif event.key() == Qt.Key.Key_PageUp:
            self.set_current_frame(self.current_frame - 10)
            event.accept()
        elif event.key() == Qt.Key.Key_PageDown:
            self.set_current_frame(self.current_frame + 10)
            event.accept()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start scrubbing when mouse is pressed."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Calculate which frame was clicked based on mouse position
            frame = self._get_frame_from_position(event.pos().x())
            if frame is not None:
                self.is_scrubbing = True
                self.scrub_start_frame = frame
                self.set_current_frame(frame)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Update frame while scrubbing."""
        if self.is_scrubbing:
            # Calculate frame from mouse position
            frame = self._get_frame_from_position(event.pos().x())
            if frame is not None and frame != self.current_frame:
                self.set_current_frame(frame)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Stop scrubbing when mouse is released."""
        if event.button() == Qt.MouseButton.LeftButton and self.is_scrubbing:
            self.is_scrubbing = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _get_frame_from_position(self, x: int) -> int | None:
        """Calculate which frame corresponds to the given x position.

        Args:
            x: X coordinate in widget coordinates

        Returns:
            Frame number or None if position is invalid
        """
        # Get the scroll area's viewport position
        if self.scroll_area is not None:
            # Adjust x for scroll position
            scroll_x = self.scroll_area.horizontalScrollBar().value()
            x += scroll_x

        # Check each tab to see if position falls within it
        for frame, tab in self.frame_tabs.items():
            tab_x = tab.x()
            tab_width = tab.width()
            if tab_x <= x < tab_x + tab_width:
                return frame

        # If not on a specific tab, calculate based on tab width
        if self.frame_tabs:
            # Get average tab width
            first_tab = next(iter(self.frame_tabs.values()))
            tab_width = first_tab.width() + self.TAB_SPACING

            # Calculate frame based on position
            frame_index = x // tab_width
            frame = self.min_frame + frame_index

            # Clamp to valid range
            if self.min_frame <= frame <= self.max_frame:
                return frame

        return None

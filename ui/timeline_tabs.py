#!/usr/bin/env python
"""
Tabbed Timeline Widget for CurveEditor

A frame-based timeline widget similar to 3DEqualizer that displays frame tabs
with color coding to indicate tracking point status at each frame.
Supports horizontal scrolling for many frames with performance optimizations.
"""

import logging

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QKeyEvent, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.models import FrameNumber
from ui.frame_tab import FrameTab

logger = logging.getLogger(__name__)


class TimelineScrollArea(QScrollArea):
    """Custom scroll area optimized for timeline tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)

        # Configure scroll area
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        # Smooth scrolling - this method may not exist in all PySide6 versions
        try:
            self.setHorizontalScrollMode(QScrollArea.ScrollMode.ScrollPerPixel)
        except AttributeError:
            # Fallback for older PySide6 versions
            pass

    def wheelEvent(self, event: QWheelEvent):
        """Handle mouse wheel for horizontal scrolling."""
        # Convert vertical wheel events to horizontal scrolling
        if event.angleDelta().y() != 0:
            # Scroll horizontally instead of vertically
            scroll_bar = self.horizontalScrollBar()
            delta = -event.angleDelta().y()  # Invert for natural scrolling
            scroll_bar.setValue(scroll_bar.value() + delta)
            event.accept()
        else:
            super().wheelEvent(event)


class FrameStatusCache:
    """Cache for frame point status to improve performance."""

    def __init__(self):
        """Initialize empty cache."""
        self._cache: dict[FrameNumber, tuple[int, int, bool]] = {}
        self._dirty_frames: set[FrameNumber] = set()

    def get_status(self, frame: FrameNumber) -> tuple[int, int, bool] | None:
        """Get cached status for frame.

        Args:
            frame: Frame number

        Returns:
            Tuple of (keyframe_count, interpolated_count, has_selected) or None if not cached
        """
        return self._cache.get(frame)

    def set_status(self, frame: FrameNumber, keyframe_count: int, interpolated_count: int, has_selected: bool):
        """Cache status for frame.

        Args:
            frame: Frame number
            keyframe_count: Number of keyframe points
            interpolated_count: Number of interpolated points
            has_selected: Whether frame has selected points
        """
        self._cache[frame] = (keyframe_count, interpolated_count, has_selected)
        self._dirty_frames.discard(frame)

    def invalidate_frame(self, frame: FrameNumber):
        """Mark frame as needing update."""
        self._dirty_frames.add(frame)

    def invalidate_all(self):
        """Mark all frames as needing update."""
        self._dirty_frames.update(self._cache.keys())

    def clear(self):
        """Clear entire cache."""
        self._cache.clear()
        self._dirty_frames.clear()


class TimelineTabWidget(QWidget):
    """Main timeline widget with frame tabs and navigation."""

    # Signals
    frame_changed = Signal(int)  # Emitted when user selects a frame
    frame_hovered = Signal(int)  # Emitted when hovering over frame

    # Layout constants
    TAB_SPACING = 1
    NAVIGATION_HEIGHT = 24  # Compact navigation bar
    MIN_VISIBLE_TABS = 15  # More tabs visible at once
    SCROLL_STEP = 5  # Number of tabs to scroll per button click
    TOTAL_HEIGHT = 60  # Compact height matching 3DE

    def __init__(self, parent=None):
        """Initialize timeline widget."""
        super().__init__(parent)

        # Set fixed height to prevent vertical expansion
        self.setFixedHeight(self.TOTAL_HEIGHT)
        self.setMaximumHeight(self.TOTAL_HEIGHT)

        # Apply visual styling - dark professional 3DE style
        self.setStyleSheet("""
            TimelineTabWidget {
                background-color: #1a1a1a;
                border-top: 1px solid #3a3a3a;
                border-bottom: 1px solid #0a0a0a;
            }
            QPushButton {
                background-color: #2a2a2a;
                color: #aaa;
                border: 1px solid #3a3a3a;
                border-radius: 2px;
                font-weight: normal;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3a3a3a;
                color: #ddd;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
            QLabel {
                color: #ccc;
                font-size: 11px;
            }
        """)

        # State
        self.current_frame = 1
        self.total_frames = 100
        self.min_frame = 1
        self.max_frame = 100

        # Tab management
        self.frame_tabs: dict[FrameNumber, FrameTab] = {}
        self.visible_range = (1, 20)  # Currently visible frame range

        # Performance optimization
        self.status_cache = FrameStatusCache()
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.timeout.connect(self._perform_deferred_updates)

        # Setup UI
        self._setup_ui()

    def _setup_ui(self):
        """Setup the timeline UI components."""
        # Main layout
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(2)

        # Navigation controls
        self._create_navigation_controls()

        # Scrollable timeline
        self._create_timeline_area()

        # Initialize with default range
        self._update_visible_tabs()

    def _create_navigation_controls(self):
        """Create navigation buttons and frame info."""
        nav_widget = QWidget()
        nav_widget.setFixedHeight(self.NAVIGATION_HEIGHT)
        nav_layout = QHBoxLayout(nav_widget)
        nav_layout.setContentsMargins(4, 2, 4, 2)

        # Navigation buttons - compact for professional look
        button_size = 20
        self.first_btn = QPushButton("⏮")
        self.first_btn.setFixedSize(button_size, button_size)
        self.first_btn.setToolTip("Go to first frame")
        self.first_btn.clicked.connect(lambda: self.set_current_frame(self.min_frame))

        self.prev_group_btn = QPushButton("⏪")
        self.prev_group_btn.setFixedSize(button_size, button_size)
        self.prev_group_btn.setToolTip("Jump back 10 frames")
        self.prev_group_btn.clicked.connect(self._jump_back_group)

        self.next_group_btn = QPushButton("⏩")
        self.next_group_btn.setFixedSize(button_size, button_size)
        self.next_group_btn.setToolTip("Jump forward 10 frames")
        self.next_group_btn.clicked.connect(self._jump_forward_group)

        self.last_btn = QPushButton("⏭")
        self.last_btn.setFixedSize(button_size, button_size)
        self.last_btn.setToolTip("Go to last frame")
        self.last_btn.clicked.connect(lambda: self.set_current_frame(self.max_frame))

        # Frame info label - professional 3DE style
        self.frame_info = QLabel()
        self.frame_info.setStyleSheet(
            "QLabel { color: #ddc064; font-size: 11px; font-weight: bold; font-family: monospace; }"
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

    def _create_timeline_area(self):
        """Create scrollable timeline area."""
        # Create scroll area
        self.scroll_area = TimelineScrollArea(self)
        # Adjust height to match compact tabs
        self.scroll_area.setFixedHeight(32)  # Enough for 24px tabs + padding

        # Create container widget for tabs
        self.tabs_container = QWidget()
        self.tabs_layout = QHBoxLayout(self.tabs_container)
        self.tabs_layout.setContentsMargins(4, 4, 4, 4)
        self.tabs_layout.setSpacing(self.TAB_SPACING)
        self.tabs_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.scroll_area.setWidget(self.tabs_container)
        self.main_layout.addWidget(self.scroll_area)

    def set_frame_range(self, min_frame: int, max_frame: int):
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

        # Clear cache and update tabs
        self.status_cache.clear()
        self._update_visible_range()
        self._update_visible_tabs()
        self._update_frame_info()

    def set_current_frame(self, frame: int):
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

            # Ensure frame is visible
            self._ensure_frame_visible(frame)
            self._update_frame_info()

            # Emit signal
            self.frame_changed.emit(frame)

    def update_frame_status(
        self, frame: int, keyframe_count: int = 0, interpolated_count: int = 0, has_selected: bool = False
    ):
        """Update point status for a specific frame.

        Args:
            frame: Frame number
            keyframe_count: Number of keyframe points
            interpolated_count: Number of interpolated points
            has_selected: Whether frame has selected points
        """
        # Update cache
        self.status_cache.set_status(frame, keyframe_count, interpolated_count, has_selected)

        # Update tab if visible
        if frame in self.frame_tabs:
            tab = self.frame_tabs[frame]
            tab.set_point_status(keyframe_count, interpolated_count, has_selected)

    def invalidate_frame_status(self, frame: int):
        """Mark frame status as needing update.

        Args:
            frame: Frame number to invalidate
        """
        self.status_cache.invalidate_frame(frame)

        # Schedule deferred update
        self._schedule_deferred_update()

    def invalidate_all_frames(self):
        """Mark all frame statuses as needing update."""
        self.status_cache.invalidate_all()
        self._schedule_deferred_update()

    def _update_visible_range(self):
        """Update which frames should be visible."""
        # Calculate optimal visible range around current frame
        visible_width = self.scroll_area.viewport().width()
        tab_width = FrameTab.TAB_WIDTH + self.TAB_SPACING
        max_visible = max(self.MIN_VISIBLE_TABS, visible_width // tab_width)

        # Center around current frame when possible
        half_range = max_visible // 2
        start = max(self.min_frame, self.current_frame - half_range)
        end = min(self.max_frame, start + max_visible - 1)

        # Adjust start if we're at the end
        if end == self.max_frame:
            start = max(self.min_frame, end - max_visible + 1)

        self.visible_range = (start, end)

    def _update_visible_tabs(self):
        """Update which frame tabs are visible."""
        start_frame, end_frame = self.visible_range

        # Remove tabs outside visible range
        for frame in list(self.frame_tabs.keys()):
            if frame < start_frame or frame > end_frame:
                tab = self.frame_tabs.pop(frame)
                self.tabs_layout.removeWidget(tab)
                tab.deleteLater()

        # Add tabs for visible range
        for frame in range(start_frame, end_frame + 1):
            if frame not in self.frame_tabs:
                tab = FrameTab(frame, self)
                tab.frame_clicked.connect(self.set_current_frame)
                tab.frame_hovered.connect(self.frame_hovered.emit)

                # Set current frame status
                if frame == self.current_frame:
                    tab.set_current_frame(True)

                # Apply cached status if available
                cached_status = self.status_cache.get_status(frame)
                if cached_status:
                    keyframe_count, interpolated_count, has_selected = cached_status
                    tab.set_point_status(keyframe_count, interpolated_count, has_selected)

                self.frame_tabs[frame] = tab
                self.tabs_layout.addWidget(tab)

        # Update container size
        total_width = len(self.frame_tabs) * (FrameTab.TAB_WIDTH + self.TAB_SPACING) + 8
        self.tabs_container.setMinimumWidth(total_width)

    def _ensure_frame_visible(self, frame: int):
        """Ensure the specified frame is visible in the timeline."""
        start_frame, end_frame = self.visible_range

        # Check if frame is outside visible range
        if frame < start_frame or frame > end_frame:
            self._update_visible_range()
            self._update_visible_tabs()

        # Scroll to make frame visible
        if frame in self.frame_tabs:
            tab = self.frame_tabs[frame]
            self.scroll_area.ensureWidgetVisible(tab, 50, 0)  # 50px margin

    def _update_frame_info(self):
        """Update frame information label."""
        visible_start, visible_end = self.visible_range
        info_text = f"Frame {self.current_frame:3d} | {visible_start:3d}-{visible_end:3d} of {self.max_frame:3d}"
        self.frame_info.setText(info_text)

    def _jump_back_group(self):
        """Jump back by group size."""
        new_frame = max(self.min_frame, self.current_frame - 10)
        self.set_current_frame(new_frame)

    def _jump_forward_group(self):
        """Jump forward by group size."""
        new_frame = min(self.max_frame, self.current_frame + 10)
        self.set_current_frame(new_frame)

    def _schedule_deferred_update(self):
        """Schedule a deferred update to avoid excessive redraws."""
        if not self._update_timer.isActive():
            self._update_timer.start(50)  # 50ms delay

    def _perform_deferred_updates(self):
        """Perform any pending status updates."""
        # This would query the data service for updated point statuses
        # For now, just refresh visible tabs
        for frame, tab in self.frame_tabs.items():
            cached_status = self.status_cache.get_status(frame)
            if cached_status:
                keyframe_count, interpolated_count, has_selected = cached_status
                tab.set_point_status(keyframe_count, interpolated_count, has_selected)

    def resizeEvent(self, event: QResizeEvent):
        """Handle widget resize to update visible range."""
        super().resizeEvent(event)
        self._update_visible_range()
        self._update_visible_tabs()

    def keyPressEvent(self, event: QKeyEvent):
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

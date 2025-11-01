#!/usr/bin/env python
"""
Tabbed Timeline Widget for CurveEditor

A frame-based timeline widget similar to 3DEqualizer that displays frame tabs
with color coding to indicate tracking point status at each frame.
Supports horizontal scrolling for many frames with performance optimizations.
"""

import contextlib
from typing import TYPE_CHECKING
from typing_extensions import override
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

from core.frame_utils import clamp_frame, get_frame_range_with_limits
from core.logger_utils import get_logger
from core.models import FrameNumber, FrameStatus
from core.type_aliases import CurveDataList
from stores import get_store_manager
from stores.application_state import ApplicationState, get_application_state
from stores.store_manager import StoreManager

if TYPE_CHECKING:
    from ui.state_manager import StateManager

# animation_utils removed - using direct connections instead
from ui.frame_tab import FrameTab
from ui.qt_utils import safe_slot

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

    @override
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
    _cache: dict[FrameNumber, FrameStatus]
    _dirty_frames: set[FrameNumber]

    def __init__(self) -> None:
        """Initialize empty cache."""
        self._cache = {}
        self._dirty_frames = set()

    def get_status(self, frame: FrameNumber) -> FrameStatus | None:
        """Get cached status for frame.

        Args:
            frame: Frame number

        Returns:
            FrameStatus named tuple or None if not cached
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
        self._cache[frame] = FrameStatus(
            keyframe_count=keyframe_count,
            interpolated_count=interpolated_count,
            tracked_count=tracked_count,
            endframe_count=endframe_count,
            normal_count=normal_count,
            is_startframe=is_startframe,
            is_inactive=is_inactive,
            has_selected=has_selected,
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
    frame_hovered: Signal = Signal(int)

    # Layout constants
    TAB_SPACING: int = 0  # No spacing for seamless look
    NAVIGATION_HEIGHT: int = 20  # Ultra-compact navigation bar
    TOTAL_HEIGHT: int = 60  # Height: 20px nav + 40px scroll area

    # State variables - initialized in __init__
    total_frames: int
    min_frame: int
    max_frame: int
    frame_tabs: dict[FrameNumber, "FrameTab"]
    is_scrubbing: bool
    scrub_start_frame: int
    status_cache: FrameStatusCache
    _update_timer: QTimer
    show_all_curves_mode: bool

    # UI components - initialized in _setup_ui (called from __init__)
    main_layout: QVBoxLayout
    first_btn: QPushButton  # pyright: ignore[reportUninitializedInstanceVariable]
    prev_group_btn: QPushButton  # pyright: ignore[reportUninitializedInstanceVariable]
    next_group_btn: QPushButton  # pyright: ignore[reportUninitializedInstanceVariable]
    last_btn: QPushButton  # pyright: ignore[reportUninitializedInstanceVariable]
    mode_toggle_btn: QPushButton  # pyright: ignore[reportUninitializedInstanceVariable]
    active_point_label: QLabel  # pyright: ignore[reportUninitializedInstanceVariable]
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
        self._state_manager: StateManager | None = None
        self._current_frame: int = 1  # Only for tracking old frame for visual updates
        self.total_frames = 1
        self.min_frame = 1
        self.max_frame = 1

        # Tab management
        self.frame_tabs = {}

        # Scrubbing state
        self.is_scrubbing = False
        self.scrub_start_frame = 1

        # Aggregate mode state
        self.show_all_curves_mode = False

        # Performance optimization
        self.status_cache = FrameStatusCache()
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        _ = self._update_timer.timeout.connect(self._perform_deferred_updates)

        # Setup UI
        self._setup_ui()

        # Enable mouse tracking for scrubbing
        self.setMouseTracking(True)

        # Connect to ApplicationState
        self._store_manager: StoreManager = get_store_manager()
        self._app_state: ApplicationState = get_application_state()
        self._connect_signals()

        # Initialize timeline from current ApplicationState data
        self._on_curves_changed(self._app_state.get_all_curves())

    def __del__(self) -> None:
        """Disconnect signals to prevent memory leaks.

        TimelineTabWidget connects to singleton ApplicationState signals.
        Without cleanup, destroyed widgets would remain in memory as signal
        connection targets, causing memory leaks and potential crashes.
        """
        # Disconnect ApplicationState signals
        try:
            # Defensive check for __del__ edge cases during widget destruction
            if self._app_state is not None:  # pyright: ignore[reportUnnecessaryComparison]
                _ = self._app_state.curves_changed.disconnect(self._on_curves_changed)
                _ = self._app_state.active_curve_changed.disconnect(self._on_active_curve_changed)
                _ = self._app_state.selection_changed.disconnect(self._on_selection_changed)
        except (RuntimeError, AttributeError):
            # Already disconnected or objects destroyed
            pass

        # Disconnect StateManager signals
        try:
            if self._state_manager is not None:
                _ = self._state_manager.frame_changed.disconnect(self._on_frame_changed)
                _ = self._state_manager.active_timeline_point_changed.disconnect(self._on_active_timeline_point_changed)
        except (RuntimeError, AttributeError):
            # Already disconnected or objects destroyed
            pass

    @property
    def current_frame(self) -> int:
        """Get current frame from ApplicationState (single source of truth)."""
        return get_application_state().current_frame

    @current_frame.setter
    def current_frame(self, value: int) -> None:
        """Redirect frame changes through ApplicationState."""
        get_application_state().set_frame(value)
        # Visual update happens via signal callback

    def set_state_manager(self, state_manager: "StateManager") -> None:
        """Connect to StateManager for frame synchronization."""
        # Disconnect from previous StateManager if exists (prevent duplicate connections)
        if self._state_manager is not None:
            try:
                _ = self._state_manager.frame_changed.disconnect(self._on_frame_changed)
                _ = self._state_manager.active_timeline_point_changed.disconnect(self._on_active_timeline_point_changed)
            except (RuntimeError, TypeError):
                pass  # Already disconnected

        self._state_manager = state_manager

        # Connect to frame changes with DirectConnection (default for same-thread)
        # Visual update is lightweight (tab highlight + label text) with no re-entrancy risk
        # DirectConnection prevents queue accumulation during rapid playback
        _ = state_manager.frame_changed.connect(self._on_frame_changed)

        # Connect to active timeline point changes
        _ = state_manager.active_timeline_point_changed.connect(self._on_active_timeline_point_changed)

        # Sync initial state
        actual_frame = get_application_state().current_frame
        if actual_frame != self._current_frame:
            self._on_frame_changed(actual_frame)
        # Sync initial active timeline point
        self._on_active_timeline_point_changed(self._state_manager.active_timeline_point)

    def on_frame_changed(self, frame: int) -> None:
        """
        Public API for frame change notification.

        Args:
            frame: New frame number
        """
        self._on_frame_changed(frame)

    @safe_slot
    def _on_frame_changed(self, frame: int) -> None:
        """React to StateManager frame changes (visual updates only - internal implementation)."""
        # Clamp to valid range
        frame = clamp_frame(frame, self.min_frame, self.max_frame)

        # Update old frame tab visual state
        old_frame = self._current_frame  # Always use internal tracking for old frame
        if old_frame in self.frame_tabs:
            self.frame_tabs[old_frame].set_current_frame(False)

        # Update new frame tab visual state
        if frame in self.frame_tabs:
            self.frame_tabs[frame].set_current_frame(True)

        # Update internal tracking (for visual old frame reference only)
        self._current_frame = frame

        # Update frame info display
        self._update_frame_info()

    @safe_slot
    def _on_active_timeline_point_changed(self, point_name: str | None) -> None:
        """React to StateManager active timeline point changes.

        Args:
            point_name: Name of the active tracking point, or None if no point is active
        """
        if point_name:
            self.active_point_label.setText(f"Timeline: {point_name}")
            # Refresh timeline with the new active timeline point's data
            self._on_curves_changed(self._app_state.get_all_curves())
        else:
            self.active_point_label.setText("No point")

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

    def _connect_signals(self) -> None:
        """Connect to ApplicationState signals for reactive updates."""
        # Connect to ApplicationState signals
        _ = self._app_state.curves_changed.connect(self._on_curves_changed)
        _ = self._app_state.active_curve_changed.connect(self._on_active_curve_changed)
        _ = self._app_state.selection_changed.connect(self._on_selection_changed)

        logger.info("TimelineTabWidget connected to ApplicationState signals")

    @safe_slot
    def _on_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
        """Handle ApplicationState curves_changed signal.

        Supports both single-curve and aggregate display modes.
        """
        logger.info(f"[TIMELINE] _on_curves_changed called with {len(curves)} curves (aggregate={self.show_all_curves_mode})")

        # Invalidate status cache when curve data changes (segmentation may have changed)
        self.status_cache.invalidate_all()
        logger.info(f"[TIMELINE] Invalidated all cache entries (cache size: {len(self.status_cache._cache)})")  # pyright: ignore[reportPrivateUsage]

        # Get active timeline point data (the curve whose timeline should be displayed)
        from services import get_data_service

        data_service = get_data_service()

        # Determine which curves to process based on mode
        if self.show_all_curves_mode:
            # Aggregate mode - use all available curves
            selected_curves = list(curves.keys())
            if not selected_curves:
                # No curves to aggregate - use default range
                total_frames = get_application_state().get_total_frames()
                if total_frames > 1:
                    self.set_frame_range(1, total_frames)
                else:
                    self.set_frame_range(1, 1)
                return

            # Get aggregated status across all curves
            frame_status = data_service.aggregate_frame_statuses_for_curves(selected_curves)

            # Calculate frame range from all curves
            min_frame = 1
            max_frame = 1
            for curve_data in curves.values():
                if curve_data:
                    frame_range = get_frame_range_with_limits(curve_data, max_range=200)
                    if frame_range:
                        curve_min, curve_max = frame_range
                        min_frame = min(min_frame, curve_min) if min_frame > 1 else curve_min
                        max_frame = max(max_frame, curve_max)

            # Also consider image sequence length
            image_sequence_frames = get_application_state().get_total_frames()
            max_frame = max(max_frame, image_sequence_frames)

            # Update frame range
            self.set_frame_range(min_frame, max_frame)

        else:
            # Single-curve mode - use active timeline point
            # Use active_timeline_point from StateManager, fallback to active_curve if not set
            active_timeline_point = None
            if self._state_manager:
                active_timeline_point = self._state_manager.active_timeline_point

            # Fallback to active_curve if active_timeline_point not set (e.g., in tests)
            if not active_timeline_point:
                active_timeline_point = self._app_state.active_curve

            if not active_timeline_point or active_timeline_point not in curves:
                # Check if image sequence is loaded even without tracking data
                total_frames = get_application_state().get_total_frames()
                if total_frames > 1:
                    logger.debug(f"_on_curves_changed: No tracking data, using image sequence range 1-{total_frames}")
                    self.set_frame_range(1, total_frames)
                else:
                    logger.debug("_on_curves_changed: No data, setting frame range to 1-1")
                    self.set_frame_range(1, 1)
                return

            curve_data = curves[active_timeline_point]
            logger.debug(f"_on_curves_changed: got {len(curve_data) if curve_data else 0} points from ApplicationState")

            if not curve_data:
                total_frames = get_application_state().get_total_frames()
                if total_frames > 1:
                    self.set_frame_range(1, total_frames)
                else:
                    self.set_frame_range(1, 1)
                return

            # Calculate frame range from data (with performance limits)
            frame_range = get_frame_range_with_limits(curve_data, max_range=200)
            if not frame_range:
                return

            min_frame, max_frame = frame_range

            # Also consider image sequence length from ApplicationState
            image_sequence_frames = get_application_state().get_total_frames()
            max_frame = max(max_frame, image_sequence_frames)

            # Check if we actually limited the range
            original_max = max([int(point[0]) for point in curve_data if len(point) >= 3])
            if max_frame < original_max:
                logger.warning(
                    f"Timeline limited to 200 frames for performance (actual range: {min_frame}-{original_max})"
                )

            # Update frame range
            self.set_frame_range(min_frame, max_frame)

            # Update status for all frames
            frame_status = data_service.get_frame_range_point_status(curve_data)

        # Update frame status for all frames (common path for both modes)
        inactive_count = 0
        for frame, status in frame_status.items():
            if status.is_inactive:
                inactive_count += 1
            self.update_frame_status(
                frame,
                keyframe_count=status.keyframe_count,
                interpolated_count=status.interpolated_count,
                tracked_count=status.tracked_count,
                endframe_count=status.endframe_count,
                normal_count=status.normal_count,
                is_startframe=status.is_startframe,
                is_inactive=status.is_inactive,
                has_selected=status.has_selected,
            )

        logger.info(f"[TIMELINE] Updated {len(frame_status)} frames ({inactive_count} inactive)")
        logger.debug(f"Timeline updated from ApplicationState: {len(frame_status)} frames")

    @safe_slot
    def _on_active_curve_changed(self, _curve_name: str) -> None:
        """Handle ApplicationState active_curve_changed signal."""
        # Refresh timeline with new active curve data
        self._on_curves_changed(self._app_state.get_all_curves())

    @safe_slot
    def _on_selection_changed(self, selection: set[int], curve_name: str | None = None) -> None:
        """Handle selection changes.

        Phase 4: Removed __default__ - curve_name is now optional.

        Args:
            selection: Selected indices
            curve_name: Curve with selection change (None uses active timeline point)
        """
        # Use StateManager's active_timeline_point, fallback to active_curve if not set
        if not curve_name:
            if self._state_manager:
                curve_name = self._state_manager.active_timeline_point
            # Fallback to active_curve if active_timeline_point not set (e.g., in tests)
            if not curve_name:
                curve_name = self._app_state.active_curve

        if not curve_name:
            return

        curve_data = self._app_state.get_curve_data(curve_name)
        if not curve_data:
            return

        # Find frames that contain selected points
        selected_frames: set[int] = set()
        for index in selection:
            if 0 <= index < len(curve_data):
                point = curve_data[index]
                if len(point) >= 3:
                    frame = int(point[0])
                    selected_frames.add(frame)

        # Update has_selected status for all frames
        from services import get_data_service

        data_service = get_data_service()
        frame_status = data_service.get_frame_range_point_status(curve_data)

        for frame in range(self.min_frame, self.max_frame + 1):
            # Check if this frame has selected points
            has_selected = frame in selected_frames

            # Get existing status from cache or calculate defaults
            status = self.status_cache.get_status(frame)
            if status:
                # Use cached status
                keyframe_count = status.keyframe_count
                interpolated_count = status.interpolated_count
                tracked_count = status.tracked_count
                endframe_count = status.endframe_count
                normal_count = status.normal_count
                is_startframe = status.is_startframe
                is_inactive = status.is_inactive
            else:
                # Get status from data service if not cached
                if frame in frame_status:
                    status = frame_status[frame]
                    keyframe_count = status.keyframe_count
                    interpolated_count = status.interpolated_count
                    tracked_count = status.tracked_count
                    endframe_count = status.endframe_count
                    normal_count = status.normal_count
                    is_startframe = status.is_startframe
                    is_inactive = status.is_inactive
                else:
                    # Default values for frames with no points
                    keyframe_count = interpolated_count = tracked_count = 0
                    endframe_count = normal_count = 0
                    is_startframe = is_inactive = False

            # Update frame status with new has_selected value
            self.update_frame_status(
                frame,
                keyframe_count=keyframe_count,
                interpolated_count=interpolated_count,
                tracked_count=tracked_count,
                endframe_count=endframe_count,
                normal_count=normal_count,
                is_startframe=is_startframe,
                is_inactive=is_inactive,
                has_selected=has_selected,
            )

    @safe_slot
    def toggle_aggregate_mode(self, checked: bool) -> None:
        """Toggle between single-curve and aggregate display modes.

        Args:
            checked: True if aggregate mode is enabled, False for single-curve mode
        """
        self.show_all_curves_mode = checked

        # Update button text to reflect current mode
        if self.show_all_curves_mode:
            self.mode_toggle_btn.setText("All Curves")
            # Get all curves for aggregate display
            all_curves = self._app_state.get_all_curves()
            curve_count = len(all_curves)
            self.active_point_label.setText(f"All Curves ({curve_count})")
        else:
            self.mode_toggle_btn.setText("Aggregate Mode")
            # Restore single-curve display label
            active_timeline_point = None
            if self._state_manager:
                active_timeline_point = self._state_manager.active_timeline_point
            if not active_timeline_point:
                active_timeline_point = self._app_state.active_curve
            if active_timeline_point:
                self.active_point_label.setText(f"Timeline: {active_timeline_point}")
            else:
                self.active_point_label.setText("No point")

        # Refresh timeline display with new mode
        self._on_curves_changed(self._app_state.get_all_curves())

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
        _ = self.first_btn.clicked.connect(lambda: self.set_current_frame(self.min_frame))

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
        _ = self.last_btn.clicked.connect(lambda: self.set_current_frame(self.max_frame))

        # Aggregate mode toggle button
        self.mode_toggle_btn = QPushButton("Aggregate Mode")
        self.mode_toggle_btn.setCheckable(True)
        self.mode_toggle_btn.setFixedHeight(button_size)
        self.mode_toggle_btn.setFixedWidth(120)  # Prevent width shift between "Aggregate Mode" and "All Curves"
        self.mode_toggle_btn.setToolTip("Show combined status from all curves")
        _ = self.mode_toggle_btn.toggled.connect(self.toggle_aggregate_mode)

        # Active point label - shows which tracking point's timeline is displayed
        self.active_point_label = QLabel("No point")
        self.active_point_label.setStyleSheet(
            "QLabel { color: #74c0fc; font-size: 10px; font-weight: bold; font-family: monospace; }"
        )
        self.active_point_label.setToolTip("Currently displayed tracking point")

        # Frame info label - accent color for better visibility
        self.frame_info = QLabel()
        self.frame_info.setStyleSheet(
            "QLabel { color: #ffd43b; font-size: 10px; font-weight: normal; font-family: monospace; }"
        )
        self._update_frame_info()

        # Layout navigation
        nav_layout.addWidget(self.first_btn)
        nav_layout.addWidget(self.prev_group_btn)
        nav_layout.addWidget(self.mode_toggle_btn)
        nav_layout.addWidget(self.active_point_label)
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
        # Only recreate tabs if the range actually changes
        range_changed = self.min_frame != min_frame or self.max_frame != max_frame
        logger.debug(
            f"set_frame_range: old={self.min_frame}-{self.max_frame}, new={min_frame}-{max_frame}, changed={range_changed}"
        )

        self.min_frame = min_frame
        self.max_frame = max_frame
        self.total_frames = max_frame - min_frame + 1

        # Sync internal tracking with ApplicationState (in case they got out of sync)
        # This can happen during initialization
        actual_frame = get_application_state().current_frame
        if self._current_frame != actual_frame:
            # Update internal tracking to match reality
            self._current_frame = actual_frame

        # Update current frame if out of range
        if self.current_frame < min_frame:
            # Update internal tracking FIRST
            self._current_frame = min_frame
            # Update visual state FIRST
            self._on_frame_changed(min_frame)
            # Then delegate
            self.current_frame = min_frame
        elif self.current_frame > max_frame:
            # Update internal tracking FIRST
            self._current_frame = max_frame
            # Update visual state FIRST
            self._on_frame_changed(max_frame)
            # Then delegate
            self.current_frame = max_frame

        # Only recreate tabs if range changed (but don't clear cache)
        if range_changed:
            # Don't clear the cache - preserve existing status data
            # self.status_cache.clear()  # Commented out to preserve status
            self._create_all_tabs()

        self._update_frame_info()

    def set_current_frame(self, frame: int) -> None:
        """Set current frame and update display.

        Args:
            frame: Frame number to set as current

        Implementation Note:
            Updates visual state IMMEDIATELY before delegating to StateManager.
            This prevents race conditions where ApplicationState updates synchronously
            but timeline_tabs visual state waits for queued coordinator callback.
        """
        # Clamp to valid range
        frame = clamp_frame(frame, self.min_frame, self.max_frame)

        # Use internal tracking for old frame (not property, which reads from StateManager)
        old_frame = self._current_frame

        if frame != old_frame:
            # Update visual state IMMEDIATELY (before ApplicationState changes)
            # This ensures timeline_tabs is always in sync with curve_view
            self._on_frame_changed(frame)

            # Then delegate to StateManager (triggers ApplicationState update)
            # Coordinator will run later via queued callback (but timeline already updated)
            self.current_frame = frame

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
        # Debug
        # print(f"update_frame_status: frame {frame}, keyframe={keyframe_count}, frame in tabs={frame in self.frame_tabs}")

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
                normal_count=normal_count,
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
        try:
            parent = self.parent()
            available_width = parent.width() - 100 if parent and isinstance(parent, QWidget) else 1300  # Default for 1400px window
        except RuntimeError:
            # Parent already deleted during teardown
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
        # Check if widget is being deleted
        try:
            _ = self.isVisible()
        except RuntimeError:
            # Widget is being deleted, abort tab creation
            return

        # Layout exists (non-None QHBoxLayout)

        # Clear existing tabs
        for tab in self.frame_tabs.values():
            with contextlib.suppress(RuntimeError):
                self.tabs_layout.removeWidget(tab)
            with contextlib.suppress(RuntimeError):
                tab.deleteLater()
        self.frame_tabs.clear()

        # Calculate optimal tab width
        tab_width = self._calculate_tab_width()

        # Create tabs for entire frame range
        for frame in range(self.min_frame, self.max_frame + 1):
            try:
                tab = FrameTab(frame, self)
            except RuntimeError:
                # Parent widget deleted during tab creation, abort
                return

            # Check if tab was actually created (FrameTab.__init__ can return early)
            # Type-safe check without hasattr
            set_tab_width_method = getattr(tab, "set_tab_width", None)
            if not callable(set_tab_width_method):
                continue

            tab.set_tab_width(tab_width)
            _ = tab.frame_clicked.connect(self.set_current_frame)
            # frame_hovered connection removed - no hover actions needed

            # Set current frame status
            if frame == self.current_frame:
                tab.set_current_frame(True)

            # Apply cached status if available with all fields
            status = self.status_cache.get_status(frame)
            if status:
                tab.set_point_status(
                    keyframe_count=status.keyframe_count,
                    interpolated_count=status.interpolated_count,
                    tracked_count=status.tracked_count,
                    endframe_count=status.endframe_count,
                    normal_count=status.normal_count,
                    is_startframe=status.is_startframe,
                    is_inactive=status.is_inactive,
                    has_selected=status.has_selected,
                )

            self.frame_tabs[frame] = tab
            # Add to layout (tabs_layout is non-None QHBoxLayout)
            try:
                self.tabs_layout.addWidget(tab)
            except RuntimeError:
                # Layout or widget being destroyed during teardown
                return

        # Update container size to fit all tabs
        total_width = tab_width * len(self.frame_tabs) + 4
        self.tabs_container.setMinimumWidth(total_width)

    def _ensure_frame_visible(self, _frame: int) -> None:
        """Ensure the specified frame is visible (no-op since all frames are visible)."""
        # All frames are always visible with dynamic width

    def _update_frame_info(self) -> None:
        """Update frame information label."""
        # frame_info is non-None QLabel
        try:
            info_text = f"Frame {self.current_frame:3d} | 1-{self.max_frame:3d}"
            self.frame_info.setText(info_text)
        except RuntimeError:
            # frame_info QLabel has been deleted
            pass

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
        # Recalculate status for dirty frames
        from services import get_data_service

        data_service = get_data_service()

        # Get active curve data from ApplicationState - use active_curve_data property
        if (cd := self._app_state.active_curve_data) is None:
            return
        _curve_name, curve_data = cd

        # Clear status for frames that no longer have points
        for frame in range(self.min_frame, self.max_frame + 1):
            self.status_cache.set_status(
                frame,
                keyframe_count=0,
                interpolated_count=0,
                tracked_count=0,
                endframe_count=0,
                normal_count=0,
                is_startframe=False,
                is_inactive=False,
                has_selected=False,
            )

        if curve_data:
            # Get frame status for all points
            frame_status = data_service.get_frame_range_point_status(curve_data)

            # Update cache for all frames with data
            for frame, status in frame_status.items():
                self.status_cache.set_status(
                    frame,
                    keyframe_count=status.keyframe_count,
                    interpolated_count=status.interpolated_count,
                    tracked_count=status.tracked_count,
                    endframe_count=status.endframe_count,
                    normal_count=status.normal_count,
                    is_startframe=status.is_startframe,
                    is_inactive=status.is_inactive,
                    has_selected=status.has_selected,
                )

        # Now refresh visible tabs with updated status
        for frame, tab in self.frame_tabs.items():
            status = self.status_cache.get_status(frame)
            if status:
                tab.set_point_status(
                    keyframe_count=status.keyframe_count,
                    interpolated_count=status.interpolated_count,
                    tracked_count=status.tracked_count,
                    endframe_count=status.endframe_count,
                    normal_count=status.normal_count,
                    is_startframe=status.is_startframe,
                    is_inactive=status.is_inactive,
                    has_selected=status.has_selected,
                )

    @override
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

    @override
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard navigation."""
        state = get_application_state()
        if event.key() == Qt.Key.Key_Left:
            # Delegate to ApplicationState (single source of truth)
            state.set_frame(max(self.min_frame, state.current_frame - 1))
            event.accept()
        elif event.key() == Qt.Key.Key_Right:
            # Delegate to ApplicationState (single source of truth)
            state.set_frame(min(self.max_frame, state.current_frame + 1))
            event.accept()
        elif event.key() == Qt.Key.Key_Home:
            # Delegate to ApplicationState (single source of truth)
            state.set_frame(self.min_frame)
            event.accept()
        elif event.key() == Qt.Key.Key_End:
            # Delegate to ApplicationState (single source of truth)
            state.set_frame(self.max_frame)
            event.accept()
        else:
            # Properly propagate unhandled events up the widget hierarchy
            super().keyPressEvent(event)

    @override
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start scrubbing when mouse is pressed."""
        if event.button() == Qt.MouseButton.LeftButton:
            # Calculate which frame was clicked based on mouse position
            frame = self._get_frame_from_position(event.pos().x())
            if frame is not None:
                self.is_scrubbing = True
                self.scrub_start_frame = frame
                # Delegate to ApplicationState (single source of truth)
                get_application_state().set_frame(frame)
                event.accept()
                return
        super().mousePressEvent(event)

    @override
    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Update frame while scrubbing."""
        if self.is_scrubbing:
            # Calculate frame from mouse position
            frame = self._get_frame_from_position(event.pos().x())
            if frame is not None and frame != self.current_frame:
                # Delegate to ApplicationState (single source of truth)
                get_application_state().set_frame(frame)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    @override
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
        # Get the scroll area's viewport position (scroll_area is non-None TimelineScrollArea)
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

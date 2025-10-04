#!/usr/bin/env python
"""
Image Sequence Browser Dialog for CurveEditor.

Provides a visual browser for selecting image sequences with thumbnail previews,
similar to 3DEqualizer or Nuke's sequence view.
"""

import os
import warnings
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QDir, QPoint, QSize, Qt, Signal
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileSystemModel,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSplitter,
    QToolButton,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from core.favorites_manager import FavoritesManager
from core.logger_utils import get_logger
from core.metadata_extractor import ImageMetadataExtractor
from core.workers import DirectoryScanWorker, ThumbnailCache
from ui.ui_constants import (
    FONT_SIZE_LARGE,
    FONT_SIZE_NORMAL,
    FONT_SIZE_SMALL,
    SPACING_SM,
    SPACING_XS,
)
from ui.widgets.card import Card

if TYPE_CHECKING:
    from PySide6.QtCore import QModelIndex

logger = get_logger("image_sequence_browser")


class BreadcrumbBar(QWidget):
    """
    Breadcrumb navigation bar showing clickable path segments.

    Features:
    - Clickable path segments (e.g., Home > Projects > Sequences)
    - Visual chevron separators
    - Tooltip showing full path on hover
    """

    path_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        """Initialize breadcrumb bar."""
        super().__init__(parent)
        self.current_path = ""

        # Create horizontal layout
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        self._layout.addStretch()  # Push breadcrumbs to the left

        self.setStyleSheet(
            f"""
            QToolButton {{
                background: transparent;
                border: none;
                padding: {SPACING_SM}px {SPACING_SM}px;
                font-size: {FONT_SIZE_NORMAL}pt;
            }}
            QToolButton:hover {{
                background: rgba(255, 255, 255, 0.1);
                border-radius: 3px;
            }}
            QLabel {{
                color: #888;
                padding: 0 {SPACING_XS}px;
            }}
        """
        )

    def set_path(self, path: str) -> None:
        """
        Set the current path and update breadcrumb display.

        Args:
            path: Directory path to display
        """
        self.current_path = path

        # Clear existing breadcrumbs
        while self._layout.count() > 1:  # Keep the stretch
            item = self._layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        if not path:
            return

        # Split path into segments
        path_obj = Path(path)
        segments = []

        # Build segment list from root to current
        for parent in reversed(list(path_obj.parents)):
            segments.append((str(parent), parent.name or str(parent)))

        # Add current directory
        segments.append((path, path_obj.name or str(path_obj)))

        # Create breadcrumb buttons
        for i, (segment_path, segment_name) in enumerate(segments):
            # Add chevron separator (except before first segment)
            if i > 0:
                chevron = QLabel(">")
                chevron.setStyleSheet(f"color: #888; padding: 0 {SPACING_XS}px;")
                self._layout.insertWidget(self._layout.count() - 1, chevron)

            # Create button for this segment
            button = QToolButton()
            button.setText(segment_name)
            button.setToolTip(segment_path)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

            # Set accessible properties for screen readers
            button.setAccessibleName(f"Navigate to {segment_name}")
            button.setAccessibleDescription(f"Navigate to directory: {segment_path}")

            # Use functools.partial to capture segment_path
            from functools import partial

            button.clicked.connect(partial(self._on_segment_clicked, segment_path))

            # Bold the current (last) segment
            if i == len(segments) - 1:
                button.setStyleSheet("QToolButton { font-weight: bold; }")

            self._layout.insertWidget(self._layout.count() - 1, button)

    def _on_segment_clicked(self, path: str, checked: bool = False) -> None:
        """
        Handle segment click.

        Args:
            path: Path that was clicked
            checked: Button checked state (unused)
        """
        self.path_changed.emit(path)


class NavigationHistory:
    """
    Browser-style navigation history for back/forward navigation.

    Maintains a stack of visited directories with current position tracking.
    """

    def __init__(self, max_history: int = 50):
        """
        Initialize navigation history.

        Args:
            max_history: Maximum number of history entries to keep
        """
        self.history: list[str] = []
        self.current_index = -1
        self.max_history = max_history

    def add(self, path: str) -> None:
        """
        Add a path to history.

        Args:
            path: Directory path to add
        """
        # Don't add if it's the same as current
        if self.current_index >= 0 and self.current_index < len(self.history):
            if self.history[self.current_index] == path:
                return

        # Truncate forward history when navigating to new location
        self.history = self.history[: self.current_index + 1]

        # Add new path
        self.history.append(path)
        self.current_index = len(self.history) - 1

        # Limit history size
        if len(self.history) > self.max_history:
            self.history.pop(0)
            self.current_index -= 1

    def can_go_back(self) -> bool:
        """Check if we can navigate back."""
        return self.current_index > 0

    def can_go_forward(self) -> bool:
        """Check if we can navigate forward."""
        return self.current_index < len(self.history) - 1

    def go_back(self) -> str | None:
        """
        Navigate back in history.

        Returns:
            Previous path or None if can't go back
        """
        if self.can_go_back():
            self.current_index -= 1
            return self.history[self.current_index]
        return None

    def go_forward(self) -> str | None:
        """
        Navigate forward in history.

        Returns:
            Next path or None if can't go forward
        """
        if self.can_go_forward():
            self.current_index += 1
            return self.history[self.current_index]
        return None

    def get_current(self) -> str | None:
        """Get current path in history."""
        if 0 <= self.current_index < len(self.history):
            return self.history[self.current_index]
        return None


@dataclass
class ImageSequence:
    """
    Represents a detected image sequence with metadata.

    Attributes:
        base_name: Prefix before frame numbers (e.g., "render_")
        padding: Number of digits in frame padding (e.g., 4 for "0001")
        extension: File extension including dot (e.g., ".exr")
        frames: List of actual frame numbers found
        file_list: List of actual filenames in sequence
        directory: Directory containing the sequence
        resolution: Image resolution tuple (width, height) or None
        bit_depth: Bit depth (8, 16, 32) or None
        color_space: Color space identifier or None
        total_size_bytes: Total size of all files in bytes
    """

    base_name: str
    padding: int
    extension: str
    frames: list[int]
    file_list: list[str]
    directory: str
    resolution: tuple[int, int] | None = None
    bit_depth: int | None = None
    color_space: str | None = None
    total_size_bytes: int = 0

    @property
    def frame_range_str(self) -> str:
        """Generate frame range display string (e.g., '[1-100]' or '[1-3,5,7-10]')."""
        if not self.frames:
            return "[]"

        # Sort frames
        sorted_frames = sorted(self.frames)
        ranges: list[str] = []
        start = sorted_frames[0]
        end = start

        for frame in sorted_frames[1:]:
            if frame == end + 1:
                # Consecutive frame, extend range
                end = frame
            else:
                # Gap found, save current range
                if start == end:
                    ranges.append(str(start))
                else:
                    ranges.append(f"{start}-{end}")
                start = frame
                end = frame

        # Add final range
        if start == end:
            ranges.append(str(start))
        else:
            ranges.append(f"{start}-{end}")

        return f"[{','.join(ranges)}]"

    @property
    def has_gaps(self) -> bool:
        """Check if sequence has missing frames."""
        if not self.frames or len(self.frames) < 2:
            return False

        sorted_frames = sorted(self.frames)
        expected_count = sorted_frames[-1] - sorted_frames[0] + 1
        return len(self.frames) < expected_count

    @property
    def missing_frames(self) -> list[int]:
        """Get list of missing frame numbers."""
        if not self.frames:
            return []

        sorted_frames = sorted(self.frames)
        all_frames = set(range(sorted_frames[0], sorted_frames[-1] + 1))
        return sorted(all_frames - set(self.frames))

    @property
    def resolution_str(self) -> str:
        """Get resolution as string (e.g., '1920x1080')."""
        if self.resolution:
            return f"{self.resolution[0]}x{self.resolution[1]}"
        return "Unknown"

    @property
    def total_size_mb(self) -> float:
        """Get total size in megabytes."""
        return self.total_size_bytes / (1024 * 1024)

    @property
    def display_name(self) -> str:
        """Generate display name for sequence (e.g., 'render_####.exr [1-100] (100 frames)')."""
        padding_str = "#" * self.padding
        frame_count = len(self.frames)
        plural = "s" if frame_count != 1 else ""

        # Add metadata if available
        metadata_parts = []
        if self.resolution:
            # Common resolution labels
            labels = {
                (1920, 1080): "HD",
                (2048, 1556): "2K",
                (3840, 2160): "4K",
                (4096, 2160): "4K DCI",
            }
            res_str = labels.get(self.resolution, self.resolution_str)
            metadata_parts.append(res_str)

        if self.bit_depth:
            metadata_parts.append(f"{self.bit_depth}bit")

        metadata_str = f" ({', '.join(metadata_parts)})" if metadata_parts else ""

        return f"{self.base_name}{padding_str}{self.extension} {self.frame_range_str} ({frame_count} frame{plural}){metadata_str}"


class ImageSequenceBrowserDialog(QDialog):
    """
    Custom dialog for browsing and selecting image sequences.

    Features:
    - Directory tree browser on the left
    - Thumbnail grid preview on the right
    - Sequence information display (frame count, resolution)
    - Visual feedback for directories containing image sequences
    """

    # Supported image formats (must match data_service.py and file_operations.py)
    IMAGE_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif", ".exr"}

    # Thumbnail display settings
    THUMBNAIL_SIZE: int = 150
    THUMBNAILS_PER_ROW: int = 4
    MAX_THUMBNAILS: int = 12  # Show first 12 frames

    # Type annotations for attributes (helps type checker detect initialization issues)
    tree_view: QTreeView
    file_model: QFileSystemModel
    drive_selector: QComboBox | None
    address_bar: QComboBox
    breadcrumb_bar: BreadcrumbBar
    back_button: QToolButton
    forward_button: QToolButton
    favorites_list: QListWidget
    sequence_list: QListWidget
    sort_combo: QComboBox
    sort_order_button: QToolButton

    def __init__(self, parent: QWidget | None = None, start_directory: str | None = None):
        """
        Initialize the image sequence browser dialog.

        Args:
            parent: Parent widget
            start_directory: Initial directory to display (defaults to smart selection)
        """
        super().__init__(parent)
        self.selected_directory: str | None = None
        self.selected_sequence: ImageSequence | None = None
        self.favorites_manager: FavoritesManager = FavoritesManager()

        # Initialize workers and cache
        self.thumbnail_cache = ThumbnailCache()
        self.scan_worker: DirectoryScanWorker | None = None
        self.metadata_extractor = ImageMetadataExtractor()

        # Navigation history
        self.nav_history = NavigationHistory()
        self._navigating_from_history = False  # Flag to prevent adding to history during history navigation

        # Sorting state
        self.current_sort = "name"  # name, frame_count, size, date
        self.sort_ascending = True

        # Determine best starting directory
        self.start_directory = self._determine_start_directory(parent, start_directory)

        self._setup_ui()
        self._connect_signals()
        self._setup_shortcuts()
        self._restore_state()

        # Populate recent directories dropdown
        self._populate_recent_directories()

        # Populate favorites list
        self._populate_favorites()

        # Set initial directory
        if self.start_directory and Path(self.start_directory).exists():
            index = self.file_model.index(self.start_directory)
            self.tree_view.setCurrentIndex(index)
            self.tree_view.expand(index)
            self._on_directory_selected(index)
            self._update_address_bar(index)
            self.breadcrumb_bar.set_path(self.start_directory)

            # Add initial directory to navigation history
            self.nav_history.add(self.start_directory)
            self._update_history_buttons()

        # Set initial focus to tree view for immediate keyboard navigation
        self.tree_view.setFocus()

    def _determine_start_directory(self, parent: QWidget | None, start_directory: str | None) -> str:
        """
        Determine the best starting directory for the browser.

        Priority order:
        1. User-provided start_directory
        2. Last used directory from state_manager
        3. Documents folder
        4. Home directory

        Args:
            parent: Parent widget (may have state_manager)
            start_directory: User-provided starting directory

        Returns:
            Path string for starting directory
        """
        # Priority 1: User-provided directory
        if start_directory and Path(start_directory).exists():
            return start_directory

        # Priority 2: Last used directory from state manager
        if hasattr(parent, "state_manager"):
            state_manager = getattr(parent, "state_manager", None)
            if state_manager and hasattr(state_manager, "recent_directories"):
                recent_dirs = state_manager.recent_directories
                if recent_dirs and len(recent_dirs) > 0:
                    last_dir = recent_dirs[0]
                    if Path(last_dir).exists():
                        logger.debug(f"Using last directory from state: {last_dir}")
                        return last_dir

        # Priority 3: Documents folder
        documents_dir = Path.home() / "Documents"
        if documents_dir.exists():
            logger.debug(f"Using Documents folder: {documents_dir}")
            return str(documents_dir)

        # Priority 4: Home directory (fallback)
        home_dir = str(Path.home())
        logger.debug(f"Using home directory: {home_dir}")
        return home_dir

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Load Image Sequence")
        self.resize(1200, 600)

        # Main layout
        main_layout = QVBoxLayout(self)

        # Top navigation bar - spans full width
        top_nav_bar = QHBoxLayout()
        top_nav_bar.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)

        # Back button
        self.back_button = QToolButton()
        self.back_button.setText("←")
        self.back_button.setToolTip("Go back (Alt+Left)")
        self.back_button.setFixedSize(32, 32)
        self.back_button.setEnabled(False)
        self.back_button.setAccessibleName("Go back")
        self.back_button.setAccessibleDescription("Navigate back to previous directory in history")
        top_nav_bar.addWidget(self.back_button)

        # Forward button
        self.forward_button = QToolButton()
        self.forward_button.setText("→")
        self.forward_button.setToolTip("Go forward (Alt+Right)")
        self.forward_button.setFixedSize(32, 32)
        self.forward_button.setEnabled(False)
        self.forward_button.setAccessibleName("Go forward")
        self.forward_button.setAccessibleDescription("Navigate forward to next directory in history")
        top_nav_bar.addWidget(self.forward_button)

        # Up button (go to parent directory)
        self.up_button = QToolButton()
        self.up_button.setText("↑")
        self.up_button.setToolTip("Go to parent directory (Alt+Up)")
        self.up_button.setFixedSize(32, 32)
        self.up_button.setAccessibleName("Go up")
        self.up_button.setAccessibleDescription("Navigate to parent directory")
        top_nav_bar.addWidget(self.up_button)

        # Home button
        self.home_button = QToolButton()
        self.home_button.setText("🏠")
        home_path = str(Path.home())
        self.home_button.setToolTip(f"Go to home directory ({home_path})")
        self.home_button.setFixedSize(32, 32)
        self.home_button.setAccessibleName("Go to home")
        self.home_button.setAccessibleDescription("Navigate to your home directory")
        top_nav_bar.addWidget(self.home_button)

        # Windows drive selector (only on Windows)
        if sys.platform == "win32":
            self.drive_selector = QComboBox()
            self.drive_selector.setToolTip("Select drive")
            self.drive_selector.setMinimumWidth(60)
            self.drive_selector.setMaximumWidth(80)
            self.drive_selector.setAccessibleName("Drive selector")
            self.drive_selector.setAccessibleDescription("Select drive to browse")
            top_nav_bar.addWidget(self.drive_selector)
            # Note: _populate_drives() will be called after tree_view is created
        else:
            self.drive_selector = None

        # Quick Access dropdown
        self.quick_access_button = QToolButton()
        self.quick_access_button.setText("⚡")
        self.quick_access_button.setToolTip("Quick access to common locations")
        self.quick_access_button.setFixedSize(32, 32)
        self.quick_access_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.quick_access_button.setAccessibleName("Quick access")
        self.quick_access_button.setAccessibleDescription(
            "Quick access menu to common locations like Desktop, Documents, Downloads"
        )
        top_nav_bar.addWidget(self.quick_access_button)

        # Breadcrumb bar (clickable path segments)
        self.breadcrumb_bar = BreadcrumbBar()
        self.breadcrumb_bar.setMinimumHeight(32)
        top_nav_bar.addWidget(self.breadcrumb_bar, stretch=1)

        # Address bar (path input) - editable combo box with recent directories
        self.address_bar = QComboBox()
        self.address_bar.setEditable(True)
        self.address_bar.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.address_bar.setMinimumHeight(32)
        self.address_bar.setVisible(False)  # Hidden by default, shown when Ctrl+L is pressed
        if self.address_bar.lineEdit():
            self.address_bar.lineEdit().setPlaceholderText("Enter directory path...")
        self.address_bar.setToolTip("Type or paste a directory path, or select from recent (Ctrl+L to focus)")
        self.address_bar.setAccessibleName("Address bar")
        self.address_bar.setAccessibleDescription(
            "Type or paste directory path to navigate, or select from recent directories"
        )
        top_nav_bar.addWidget(self.address_bar, stretch=1)

        # Go button for address bar
        self.go_button = QToolButton()
        self.go_button.setText("Go")
        self.go_button.setToolTip("Navigate to entered path")
        self.go_button.setFixedSize(50, 32)
        self.go_button.setAccessibleName("Go to path")
        self.go_button.setAccessibleDescription("Navigate to the path entered in address bar")
        top_nav_bar.addWidget(self.go_button)

        # Add to Favorites button
        self.favorite_button = QToolButton()
        self.favorite_button.setText("★")
        self.favorite_button.setToolTip("Add current directory to favorites")
        self.favorite_button.setFixedSize(32, 32)
        self.favorite_button.setEnabled(False)
        self.favorite_button.setAccessibleName("Add to favorites")
        self.favorite_button.setAccessibleDescription("Add current directory to favorites list (Ctrl+D)")
        top_nav_bar.addWidget(self.favorite_button)

        main_layout.addLayout(top_nav_bar)

        # Create splitter for three-panel layout
        self.splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Favorites + Directory tree
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Favorites section (collapsible card)
        favorites_card = Card("Favorites", collapsible=True, collapsed=False)

        self.favorites_list = QListWidget()
        self.favorites_list.setMaximumHeight(150)
        self.favorites_list.setAlternatingRowColors(True)
        self.favorites_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.favorites_list.setAccessibleName("Favorite directories")
        self.favorites_list.setAccessibleDescription(
            "List of your favorite directories for quick access. Double-click to navigate."
        )
        favorites_card.add_widget(self.favorites_list)

        left_layout.addWidget(favorites_card)

        # Directory tree label
        tree_label = QLabel("&All Directories:")
        tree_label.setStyleSheet(f"font-weight: bold; font-size: {FONT_SIZE_LARGE}pt; padding: {SPACING_SM}px;")
        left_layout.addWidget(tree_label)

        # Directory tree
        self.tree_view = QTreeView()
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath("")
        self.file_model.setFilter(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot)
        self.tree_view.setModel(self.file_model)
        self.tree_view.setRootIndex(self.file_model.index(""))
        self.tree_view.setAccessibleName("Directory tree")
        self.tree_view.setAccessibleDescription(
            "Navigate through directories to find image sequences. Use arrow keys to expand and collapse folders."
        )

        # Hide unnecessary columns (size, type, date modified)
        for i in range(1, 4):
            self.tree_view.hideColumn(i)

        # Set label buddy for keyboard shortcut (Alt+A)
        tree_label.setBuddy(self.tree_view)

        left_layout.addWidget(self.tree_view)

        # Now that tree_view exists, we can populate drives (Windows only)
        self._populate_drives()

        self.splitter.addWidget(left_panel)

        # Middle panel: Sequence list with search
        sequence_list_widget = QWidget()
        sequence_list_layout = QVBoxLayout(sequence_list_widget)
        sequence_list_layout.setContentsMargins(0, 0, 0, 0)

        # Search/filter bar
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)

        sequence_label = QLabel("&Sequences:")
        sequence_label.setStyleSheet(f"font-weight: bold; font-size: {FONT_SIZE_LARGE}pt;")
        search_layout.addWidget(sequence_label)

        self.sequence_filter = QLineEdit()
        self.sequence_filter.setPlaceholderText("Filter sequences... (Ctrl+F)")
        self.sequence_filter.setClearButtonEnabled(True)
        self.sequence_filter.textChanged.connect(self._filter_sequences)
        self.sequence_filter.setAccessibleName("Sequence filter")
        self.sequence_filter.setAccessibleDescription("Type to filter sequences by name or path")
        search_layout.addWidget(self.sequence_filter, stretch=1)

        # Set label buddy for keyboard shortcut (Alt+S)
        sequence_label.setBuddy(self.sequence_filter)

        # Sort dropdown
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Name", "Frame Count", "File Size", "Date Modified"])
        self.sort_combo.setToolTip("Sort sequences by...")
        self.sort_combo.setMaximumWidth(150)
        self.sort_combo.currentTextChanged.connect(self._on_sort_changed)
        self.sort_combo.setAccessibleName("Sort by")
        self.sort_combo.setAccessibleDescription("Choose how to sort the image sequences")
        search_layout.addWidget(self.sort_combo)

        # Sort order button (ascending/descending)
        self.sort_order_button = QToolButton()
        self.sort_order_button.setText("↑")  # Initially ascending (matches self.sort_ascending = True)
        self.sort_order_button.setToolTip("Sort order: Ascending (click to toggle)")
        self.sort_order_button.setFixedSize(32, 32)
        self.sort_order_button.clicked.connect(self._toggle_sort_order)
        self.sort_order_button.setAccessibleName("Sort order")
        self.sort_order_button.setAccessibleDescription("Toggle between ascending and descending sort order")
        search_layout.addWidget(self.sort_order_button)

        sequence_list_layout.addWidget(search_container)

        self.sequence_list = QListWidget()
        self.sequence_list.setAlternatingRowColors(True)
        self.sequence_list.setAccessibleName("Image sequences")
        self.sequence_list.setAccessibleDescription(
            "List of image sequences found in the selected directory. Select a sequence to preview, double-click or press Enter to load."
        )
        sequence_list_layout.addWidget(self.sequence_list)

        self.splitter.addWidget(sequence_list_widget)

        # Right panel: Preview area
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        # Info label
        self.info_label = QLabel("Select a sequence to preview thumbnails")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet(f"font-size: {FONT_SIZE_NORMAL}pt; padding: {SPACING_SM}px;")
        self.info_label.setAccessibleName("Status message")
        self.info_label.setAccessibleDescription("Shows current operation status and helpful information")
        preview_layout.addWidget(self.info_label)

        # Progress bar (initially hidden)
        progress_container = QWidget()
        progress_layout = QHBoxLayout(progress_container)
        progress_layout.setContentsMargins(SPACING_SM, 0, SPACING_SM, 0)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setAccessibleName("Scan progress")
        self.progress_bar.setAccessibleDescription("Shows progress of directory scanning operation")
        progress_layout.addWidget(self.progress_bar)

        self.cancel_scan_button = QPushButton("Cancel")
        self.cancel_scan_button.setVisible(False)
        self.cancel_scan_button.setMaximumWidth(80)
        self.cancel_scan_button.setAccessibleName("Cancel scan")
        self.cancel_scan_button.setAccessibleDescription("Stop the current directory scanning operation")
        progress_layout.addWidget(self.cancel_scan_button)

        preview_layout.addWidget(progress_container)

        # Scroll area for thumbnails
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumWidth(THUMBNAIL_SIZE * 2 + 50)

        # Container widget for thumbnail grid
        self.thumbnail_container = QWidget()
        self.thumbnail_layout = QGridLayout(self.thumbnail_container)
        self.thumbnail_layout.setSpacing(SPACING_SM)
        self.scroll_area.setWidget(self.thumbnail_container)

        preview_layout.addWidget(self.scroll_area)

        # Metadata panel (shows technical details of selected sequence)
        self.metadata_panel = Card("Sequence Metadata", collapsible=False)

        # Create metadata labels with enhanced typography
        self.metadata_labels = {
            "resolution": QLabel("Resolution: -"),
            "bit_depth": QLabel("Bit Depth: -"),
            "color_space": QLabel("Color Space: -"),
            "frame_count": QLabel("Frame Count: -"),
            "total_size": QLabel("Total Size: -"),
            "gaps": QLabel("Missing Frames: None"),
        }

        for label in self.metadata_labels.values():
            label.setStyleSheet(f"font-size: {FONT_SIZE_NORMAL}pt; padding: {SPACING_XS}px;")
            self.metadata_panel.add_widget(label)

        self.metadata_panel.setMaximumHeight(200)
        self.metadata_panel.setVisible(False)  # Hidden until sequence selected
        preview_layout.addWidget(self.metadata_panel)

        self.splitter.addWidget(preview_widget)

        # Set splitter proportions (25% tree, 30% sequence list, 45% preview)
        self.splitter.setSizes([250, 350, 600])

        main_layout.addWidget(self.splitter)

        # Button box
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.load_button = QPushButton("Load Sequence")
        self.load_button.setEnabled(False)
        self.load_button.setDefault(True)
        self.load_button.setAccessibleName("Load sequence")
        self.load_button.setAccessibleDescription("Load the selected image sequence")
        button_layout.addWidget(self.load_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.setAccessibleName("Cancel")
        cancel_button.setAccessibleDescription("Close dialog without loading a sequence")
        button_layout.addWidget(cancel_button)

        main_layout.addLayout(button_layout)

        # Connect button signals
        self.load_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

        # Configure logical tab order for keyboard navigation
        self.setTabOrder(self.back_button, self.forward_button)
        self.setTabOrder(self.forward_button, self.up_button)
        self.setTabOrder(self.up_button, self.home_button)

        if self.drive_selector is not None:
            # Windows: include drive selector in tab order
            self.setTabOrder(self.home_button, self.drive_selector)
            self.setTabOrder(self.drive_selector, self.quick_access_button)
        else:
            # Non-Windows: skip drive selector
            self.setTabOrder(self.home_button, self.quick_access_button)

        self.setTabOrder(self.quick_access_button, self.address_bar)
        self.setTabOrder(self.address_bar, self.go_button)
        self.setTabOrder(self.go_button, self.favorite_button)
        self.setTabOrder(self.favorite_button, self.favorites_list)
        self.setTabOrder(self.favorites_list, self.tree_view)
        self.setTabOrder(self.tree_view, self.sequence_filter)
        self.setTabOrder(self.sequence_filter, self.sort_combo)
        self.setTabOrder(self.sort_combo, self.sort_order_button)
        self.setTabOrder(self.sort_order_button, self.sequence_list)
        self.setTabOrder(self.sequence_list, self.load_button)
        self.setTabOrder(self.load_button, cancel_button)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.tree_view.clicked.connect(self._on_directory_selected)
        self.tree_view.clicked.connect(self._update_address_bar)
        self.sequence_list.currentItemChanged.connect(self._on_sequence_selected)
        self.sequence_list.itemDoubleClicked.connect(self._on_sequence_double_clicked)

        # Navigation signals
        self.back_button.clicked.connect(self._go_back)
        self.forward_button.clicked.connect(self._go_forward)
        self.up_button.clicked.connect(self._on_up_clicked)
        self.home_button.clicked.connect(self._on_home_clicked)
        self.go_button.clicked.connect(self._on_go_clicked)
        self.breadcrumb_bar.path_changed.connect(self._navigate_to_path)

        # Address bar signals
        if self.address_bar.lineEdit():
            self.address_bar.lineEdit().returnPressed.connect(self._on_go_clicked)
        self.address_bar.activated.connect(self._on_address_bar_activated)

        # Favorites signals
        self.favorite_button.clicked.connect(self._on_add_to_favorites)
        self.favorites_list.itemDoubleClicked.connect(self._on_favorite_double_clicked)
        self.favorites_list.customContextMenuRequested.connect(self._show_favorites_context_menu)

        # Drive selector signal (Windows only)
        if self.drive_selector is not None:
            self.drive_selector.currentTextChanged.connect(self._on_drive_selected)

        # Quick access menu setup
        self._setup_quick_access_menu()

        # Tree view context menu
        self.tree_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree_view.customContextMenuRequested.connect(self._show_tree_context_menu)

    def _setup_shortcuts(self) -> None:
        """Setup keyboard shortcuts for enhanced navigation."""
        # Navigation shortcuts
        # Alt+Up - Navigate to parent directory
        parent_shortcut = QShortcut(QKeySequence("Alt+Up"), self)
        parent_shortcut.activated.connect(self._on_up_clicked)

        # Alt+Left/Right - Back/Forward in navigation history
        back_shortcut = QShortcut(QKeySequence("Alt+Left"), self)
        back_shortcut.activated.connect(self._go_back)
        forward_shortcut = QShortcut(QKeySequence("Alt+Right"), self)
        forward_shortcut.activated.connect(self._go_forward)

        # Ctrl+L - Focus address bar (like web browsers)
        focus_address_bar = QShortcut(QKeySequence("Ctrl+L"), self)
        focus_address_bar.activated.connect(self._focus_address_bar)

        # Ctrl+F - Focus sequence filter for search
        focus_search = QShortcut(QKeySequence("Ctrl+F"), self)
        focus_search.activated.connect(self._focus_sequence_filter)

        # F5 - Refresh current directory
        refresh_shortcut = QShortcut(QKeySequence("F5"), self)
        refresh_shortcut.activated.connect(self._refresh_current_directory)

        # Ctrl+D - Add to favorites
        favorite_shortcut = QShortcut(QKeySequence("Ctrl+D"), self)
        favorite_shortcut.activated.connect(self._on_add_to_favorites)

        # Ctrl+1/2/3 - Focus panels
        focus_tree = QShortcut(QKeySequence("Ctrl+1"), self)
        focus_tree.activated.connect(lambda: self.tree_view.setFocus())

        focus_sequences = QShortcut(QKeySequence("Ctrl+2"), self)
        focus_sequences.activated.connect(lambda: self.sequence_list.setFocus())

        # Ctrl+Shift+A - Clear selection (Escape is reserved for closing dialog)
        clear_selection_shortcut = QShortcut(QKeySequence("Ctrl+Shift+A"), self)
        clear_selection_shortcut.activated.connect(self._clear_selection)

        # Install event filter on sequence list for Enter key handling
        self.sequence_list.installEventFilter(self)

    def eventFilter(self, obj: object, event: object) -> bool:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Handle events for keyboard navigation."""
        from PySide6.QtCore import QEvent, QObject
        from PySide6.QtGui import QKeyEvent

        # Handle Enter key on sequence list
        if obj == self.sequence_list and isinstance(event, QKeyEvent):
            if event.type() == QEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    # Enter key on sequence list = load sequence
                    current_item = self.sequence_list.currentItem()
                    if current_item and self.load_button.isEnabled():
                        self.accept()
                        return True

        # Type-safe call to parent - cast required for protocol compatibility
        if isinstance(obj, QObject) and isinstance(event, QEvent):
            return super().eventFilter(obj, event)  # type: ignore[misc]
        return False

    def keyPressEvent(self, event: object) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Handle keyboard shortcuts for the dialog."""
        from PySide6.QtGui import QKeyEvent

        if isinstance(event, QKeyEvent):
            # Escape key - cancel dialog
            if event.key() == Qt.Key.Key_Escape:
                self.reject()
                return

            # Type-safe call to parent
            super().keyPressEvent(event)  # type: ignore[arg-type]

    def _focus_address_bar(self) -> None:
        """Focus the address bar and select all text for easy replacement."""
        # Toggle between breadcrumb bar and address bar
        self.breadcrumb_bar.setVisible(False)
        self.address_bar.setVisible(True)
        self.address_bar.setFocus()
        if self.address_bar.lineEdit():
            # Set current path in address bar
            current_path = self.breadcrumb_bar.current_path
            if current_path:
                self.address_bar.lineEdit().setText(current_path)
            self.address_bar.lineEdit().selectAll()

    def _focus_sequence_list(self) -> None:
        """Focus the sequence list for keyboard navigation and type-ahead search."""
        self.sequence_list.setFocus()
        # If there are items and none selected, select first
        if self.sequence_list.count() > 0 and not self.sequence_list.currentItem():
            self.sequence_list.setCurrentRow(0)

    def _focus_sequence_filter(self) -> None:
        """Focus the sequence filter for search."""
        self.sequence_filter.setFocus()
        self.sequence_filter.selectAll()

    def _filter_sequences(self, text: str) -> None:
        """
        Filter sequences based on search text.

        Args:
            text: Filter text (case-insensitive)
        """
        filter_text = text.lower()

        for i in range(self.sequence_list.count()):
            item = self.sequence_list.item(i)
            if item:
                # Search in item text
                item_text = item.text().lower()
                match = filter_text in item_text

                # Also search in sequence metadata if available
                if not match:
                    sequence = item.data(Qt.ItemDataRole.UserRole)
                    if isinstance(sequence, ImageSequence):
                        # Search in directory path
                        if filter_text in sequence.directory.lower():
                            match = True
                        # Search in base name
                        elif filter_text in sequence.base_name.lower():
                            match = True

                item.setHidden(not match)

        # Update info label
        visible_count = sum(1 for i in range(self.sequence_list.count()) if not self.sequence_list.item(i).isHidden())
        total_count = self.sequence_list.count()

        if filter_text:
            self.info_label.setText(f"Showing {visible_count} of {total_count} sequences")
        else:
            self.info_label.setText(f"Found {total_count} sequences")

    def _refresh_current_directory(self) -> None:
        """Refresh the current directory by rescanning it."""
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            self._on_directory_selected(current_index)
            logger.debug("Refreshed current directory")

    def _clear_selection(self) -> None:
        """Clear current selection in sequence list."""
        self.sequence_list.clearSelection()
        self.sequence_list.setCurrentRow(-1)  # Clear current row instead of setCurrentItem(None)
        self._clear_preview()
        self.metadata_panel.setVisible(False)
        self.load_button.setEnabled(False)

    def _populate_recent_directories(self) -> None:
        """Populate address bar dropdown with recent directories from state manager."""
        # Get recent directories from parent's state manager if available
        parent_window = self.parent()
        if hasattr(parent_window, "state_manager"):
            state_manager = getattr(parent_window, "state_manager", None)
            if state_manager and hasattr(state_manager, "recent_directories"):
                recents = state_manager.recent_directories
                self.address_bar.clear()
                for path in recents:
                    if Path(path).exists():
                        self.address_bar.addItem(path)

    def _on_address_bar_activated(self, index: int) -> None:
        """Handle selection from recent directories dropdown.

        Args:
            index: Index of selected item in dropdown
        """
        if index >= 0:
            path = self.address_bar.itemText(index)
            if path:
                self._navigate_to_path(path)

    def _on_directory_selected(self, index: "QModelIndex") -> None:
        """
        Handle directory selection - populates sequence list asynchronously.

        Args:
            index: Model index of selected directory
        """
        directory_path = self.file_model.filePath(index)
        logger.debug(f"Directory selected: {directory_path}")

        # Clear previous state
        self.sequence_list.clear()
        self._clear_preview()
        self.selected_sequence = None
        self.load_button.setEnabled(False)

        # Cancel any existing scan
        if self.scan_worker is not None and self.scan_worker.isRunning():
            self.scan_worker.cancel()
            self.scan_worker.wait()

        # Start async directory scan
        self._start_directory_scan(directory_path)

    def _start_directory_scan(self, directory_path: str) -> None:
        """
        Start asynchronous directory scanning.

        Args:
            directory_path: Directory to scan
        """
        # Show progress UI
        self.progress_bar.setVisible(True)
        self.cancel_scan_button.setVisible(True)
        self.progress_bar.setValue(0)
        self.info_label.setText(f"Scanning directory...\n{directory_path}")

        # Create and start worker
        self.scan_worker = DirectoryScanWorker(directory_path)
        self.scan_worker.progress.connect(self._on_scan_progress)
        self.scan_worker.sequences_found.connect(self._on_sequences_found)
        self.scan_worker.error_occurred.connect(self._on_scan_error)
        self.scan_worker.finished.connect(self._on_scan_finished)

        # Connect cancel button
        self.cancel_scan_button.clicked.connect(self._on_cancel_scan)

        self.scan_worker.start()
        logger.debug(f"Started async scan of {directory_path}")

    def _on_scan_progress(self, current: int, total: int, message: str) -> None:
        """Handle scan progress updates."""
        self.progress_bar.setValue(current)
        self.info_label.setText(f"{message}\n{current}% complete")

    def _on_sequences_found(self, sequence_dicts: list[dict[str, Any]]) -> None:
        """
        Handle sequence detection completion.

        Args:
            sequence_dicts: List of sequence dictionaries from worker
        """
        # Convert dictionaries to ImageSequence objects
        sequences: list[ImageSequence] = []
        for seq_dict in sequence_dicts:
            # Create sequence object
            sequence = ImageSequence(
                base_name=seq_dict["base_name"],
                padding=seq_dict["padding"],
                extension=seq_dict["extension"],
                frames=seq_dict["frames"],
                file_list=seq_dict["file_list"],
                directory=seq_dict["directory"],
            )

            # Extract metadata from first frame
            if sequence.file_list:
                first_frame_path = os.path.join(sequence.directory, sequence.file_list[0])
                metadata = self.metadata_extractor.extract(first_frame_path)
                if metadata:
                    sequence.resolution = (metadata.width, metadata.height)
                    sequence.bit_depth = metadata.bit_depth
                    sequence.color_space = metadata.color_space

            # Calculate total size
            total_size = 0
            for filename in sequence.file_list:
                file_path = os.path.join(sequence.directory, filename)
                try:
                    total_size += os.path.getsize(file_path)
                except OSError:
                    pass
            sequence.total_size_bytes = total_size

            sequences.append(sequence)

        # Populate sequence list
        for sequence in sequences:
            item_text = sequence.display_name
            list_item = QListWidgetItem(item_text)

            # Add warning icon if sequence has gaps
            if sequence.has_gaps:
                list_item.setText(f"⚠️ {item_text}")
                list_item.setToolTip(
                    f"WARNING: Missing {len(sequence.missing_frames)} frames: {sequence.missing_frames[:10]}"
                )
                list_item.setForeground(Qt.GlobalColor.darkYellow)

            self.sequence_list.addItem(list_item)
            # Store sequence object as item data
            list_item.setData(Qt.ItemDataRole.UserRole, sequence)

        # Update info label
        seq_count = len(sequences)
        plural = "s" if seq_count != 1 else ""
        self.info_label.setText(f"Found {seq_count} sequence{plural}")

    def _on_scan_error(self, error_message: str) -> None:
        """Handle scan errors."""
        self.info_label.setText(f"Error scanning directory:\n{error_message}")
        logger.error(f"Scan error: {error_message}")

    def _on_scan_finished(self) -> None:
        """Handle scan completion."""
        # Hide progress UI
        self.progress_bar.setVisible(False)
        self.cancel_scan_button.setVisible(False)

        # Disconnect cancel button (suppress warning if not connected)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=RuntimeWarning, message="Failed to disconnect.*")
            self.cancel_scan_button.clicked.disconnect(self._on_cancel_scan)


    def _on_cancel_scan(self) -> None:
        """Handle scan cancellation request."""
        if self.scan_worker is not None:
            self.scan_worker.cancel()
            self.info_label.setText("Scan cancelled")
            logger.debug("Scan cancelled by user")

        # Update favorite button state
        self._update_favorite_button_state()

    def _on_sequence_selected(self) -> None:
        """Handle sequence selection from list - shows thumbnail preview and metadata."""
        current_item = self.sequence_list.currentItem()
        if not current_item:
            self._clear_preview()
            self.load_button.setEnabled(False)
            self.selected_sequence = None
            self.metadata_panel.setVisible(False)
            return

        # Retrieve stored ImageSequence object
        sequence = current_item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(sequence, ImageSequence):
            logger.warning("Invalid sequence data in list item")
            return

        self.selected_sequence = sequence
        self.selected_directory = sequence.directory

        # Display thumbnails for this sequence
        self._display_sequence_thumbnails(sequence)

        # Update metadata panel
        self._update_metadata_panel(sequence)

        # Enable load button
        self.load_button.setEnabled(True)

        logger.debug(f"Sequence selected: {sequence.display_name}")

    def _on_sequence_double_clicked(self) -> None:
        """Handle sequence double-click - immediately load the sequence."""
        current_item = self.sequence_list.currentItem()
        if not current_item:
            return

        sequence = current_item.data(Qt.ItemDataRole.UserRole)
        if isinstance(sequence, ImageSequence):
            self.selected_sequence = sequence
            self.selected_directory = sequence.directory
            self.accept()

    def _on_up_clicked(self) -> None:
        """Navigate to parent directory."""
        current_index = self.tree_view.currentIndex()
        if not current_index.isValid():
            return

        parent_index = current_index.parent()
        if parent_index.isValid():
            self.tree_view.setCurrentIndex(parent_index)
            self.tree_view.expand(parent_index)
            self._on_directory_selected(parent_index)
            self._update_address_bar(parent_index)

    def _on_home_clicked(self) -> None:
        """Navigate to home directory."""
        home_path = str(Path.home())
        self._navigate_to_path(home_path)

    def _on_go_clicked(self) -> None:
        """Navigate to path entered in address bar."""
        path = self.address_bar.currentText().strip()
        if path:
            self._navigate_to_path(path)
        # Switch back to breadcrumb bar
        self.address_bar.setVisible(False)
        self.breadcrumb_bar.setVisible(True)

    def _go_back(self) -> None:
        """Navigate back in history."""
        if self.nav_history.can_go_back():
            prev_path = self.nav_history.go_back()
            if prev_path and Path(prev_path).exists():
                self._navigating_from_history = True
                self._navigate_to_path(prev_path)
                self._navigating_from_history = False
                self._update_history_buttons()

    def _go_forward(self) -> None:
        """Navigate forward in history."""
        if self.nav_history.can_go_forward():
            next_path = self.nav_history.go_forward()
            if next_path and Path(next_path).exists():
                self._navigating_from_history = True
                self._navigate_to_path(next_path)
                self._navigating_from_history = False
                self._update_history_buttons()

    def _update_history_buttons(self) -> None:
        """Update back/forward button states based on history."""
        self.back_button.setEnabled(self.nav_history.can_go_back())
        self.forward_button.setEnabled(self.nav_history.can_go_forward())

    def _navigate_to_path(self, path: str) -> None:
        """
        Navigate tree view to specified path.

        Args:
            path: Directory path to navigate to
        """
        # Expand tilde to home directory
        path = os.path.expanduser(path)

        # Normalize path (handles forward/backward slashes, relative paths)
        try:
            normalized_path = str(Path(path).resolve())
        except (OSError, ValueError) as e:
            logger.warning(f"Invalid path format: {path} - {e}")
            self.info_label.setText(f"Invalid path format: {path}")
            return

        # Check if path exists and provide specific error messages
        path_obj = Path(normalized_path)
        if not path_obj.exists():
            logger.warning(f"Path does not exist: {normalized_path}")
            self.info_label.setText(f"Path does not exist: {normalized_path}")
            return

        if not path_obj.is_dir():
            logger.warning(f"Path is a file, not a directory: {normalized_path}")
            self.info_label.setText(f"Path is a file, not a directory: {normalized_path}")
            return

        # Check for permission issues
        try:
            # Try to list directory to verify access
            list(path_obj.iterdir())
        except PermissionError:
            logger.warning(f"Permission denied accessing: {normalized_path}")
            self.info_label.setText(f"Permission denied accessing: {normalized_path}")
            return
        except OSError as e:
            logger.warning(f"Error accessing path: {normalized_path} - {e}")
            self.info_label.setText(f"Error accessing path: {normalized_path}")
            return

        # Get model index for path
        index = self.file_model.index(normalized_path)
        if not index.isValid():
            logger.warning(f"Failed to get model index for path: {normalized_path}")
            return

        # Navigate to path
        self.tree_view.setCurrentIndex(index)
        self.tree_view.expand(index)
        self.tree_view.scrollTo(index)
        self._on_directory_selected(index)
        self._update_address_bar(index)

        # Update breadcrumb bar
        self.breadcrumb_bar.set_path(normalized_path)

        # Add to navigation history (unless we're navigating from history)
        if not self._navigating_from_history:
            self.nav_history.add(normalized_path)
            self._update_history_buttons()

        # Update drive selector on Windows
        if self.drive_selector is not None and sys.platform == "win32":
            if len(normalized_path) >= 2 and normalized_path[1] == ":":
                current_drive = normalized_path[0].upper() + ":"
                drive_index = self.drive_selector.findText(current_drive)
                if drive_index >= 0:
                    self.drive_selector.blockSignals(True)
                    self.drive_selector.setCurrentIndex(drive_index)
                    self.drive_selector.blockSignals(False)

        # Add to recent directories
        parent_window = self.parent()
        if hasattr(parent_window, "state_manager"):
            state_manager = getattr(parent_window, "state_manager", None)
            if state_manager and hasattr(state_manager, "add_recent_directory"):
                state_manager.add_recent_directory(normalized_path)
                self._populate_recent_directories()  # Refresh dropdown

        logger.debug(f"Navigated to: {normalized_path}")

    def _update_address_bar(self, index: "QModelIndex | None" = None) -> None:
        """
        Update address bar with current directory path.

        Args:
            index: Model index of directory (uses current if None)
        """
        if index is None:
            index = self.tree_view.currentIndex()

        if not index.isValid():
            return

        path = self.file_model.filePath(index)
        if self.address_bar.lineEdit():
            # Show abbreviated path if it's too long
            display_path = self._abbreviate_path(path, max_length=80)
            self.address_bar.lineEdit().setText(display_path)

            # Set tooltip to show full path
            self.address_bar.setToolTip(
                f"Current directory: {path}\n\nType or paste a directory path, or select from recent (Ctrl+L to focus)"
            )

        # Update button states based on current location
        self._update_button_states(index)

    def _update_button_states(self, index: "QModelIndex | None" = None) -> None:
        """
        Update navigation button states based on current directory.

        Args:
            index: Model index of current directory (uses current if None)
        """
        if index is None:
            index = self.tree_view.currentIndex()

        if not index.isValid():
            self.up_button.setEnabled(False)
            self.up_button.setToolTip("Go to parent directory (at root)")
            return

        # Check if we have a valid parent (not at root)
        parent_index = index.parent()
        has_parent = parent_index.isValid()

        self.up_button.setEnabled(has_parent)
        if has_parent:
            parent_path = self.file_model.filePath(parent_index)
            self.up_button.setToolTip(f"Go to parent directory: {parent_path}")
        else:
            self.up_button.setToolTip("Go to parent directory (at root)")

    def _scan_directory_for_images(self, directory: str) -> list[str]:
        """
        Scan directory for image files.

        Args:
            directory: Directory path to scan

        Returns:
            Sorted list of image filenames
        """
        image_files = []

        try:
            if not os.path.isdir(directory):
                return []

            # Count files and provide progress feedback
            file_count = 0
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    file_count += 1
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in self.IMAGE_EXTENSIONS:
                        image_files.append(filename)

                    # Update progress every 100 files
                    if file_count % 100 == 0:
                        self.info_label.setText(f"Scanning directory... ({len(image_files)} images found)")
                        QApplication.processEvents()

            image_files.sort()

        except (OSError, PermissionError) as e:
            logger.warning(f"Failed to scan directory {directory}: {e}")
            self.info_label.setText(f"Error scanning directory: {e}")

        return image_files

    def _detect_sequences(self, directory: str, image_files: list[str]) -> list[ImageSequence]:
        """
        Detect image sequences from a list of filenames.

        Groups files by pattern (base_name + padding + extension) and creates
        ImageSequence objects for each detected sequence.

        Args:
            directory: Directory containing the files
            image_files: List of image filenames to analyze

        Returns:
            List of detected ImageSequence objects, sorted by base_name
        """
        # Pattern to match: prefix + frame_number (3+ digits) + extension
        # Example: "render_0001.exr" → groups: ("render_", "0001", ".exr")
        pattern = re.compile(r"^(.*)(\d{3,})(\.\w+)$")

        # Dictionary to group files: (base_name, padding, extension) → list of (frame, filename)
        sequence_groups: dict[tuple[str, int, str], list[tuple[int, str]]] = {}

        # Also track non-sequence files (single images without frame numbers)
        non_sequence_files: list[str] = []

        for filename in image_files:
            match = pattern.match(filename)
            if match:
                base_name = match.group(1)
                frame_str = match.group(2)
                extension = match.group(3)
                padding = len(frame_str)
                frame_num = int(frame_str)

                key = (base_name, padding, extension)
                if key not in sequence_groups:
                    sequence_groups[key] = []
                sequence_groups[key].append((frame_num, filename))
            else:
                # File doesn't match sequence pattern (e.g., "image.png" without frame number)
                non_sequence_files.append(filename)

        # Create ImageSequence objects
        sequences: list[ImageSequence] = []

        for (base_name, padding, extension), files in sequence_groups.items():
            # Sort by frame number
            files.sort(key=lambda x: x[0])

            frames = [frame for frame, _ in files]
            file_list = [filename for _, filename in files]

            sequence = ImageSequence(
                base_name=base_name,
                padding=padding,
                extension=extension,
                frames=frames,
                file_list=file_list,
                directory=directory,
            )
            sequences.append(sequence)

        # Handle non-sequence files as individual "sequences" with padding=0
        for filename in non_sequence_files:
            ext = os.path.splitext(filename)[1]
            base = os.path.splitext(filename)[0]
            sequence = ImageSequence(
                base_name=base,
                padding=0,  # Indicates non-sequence
                extension=ext,
                frames=[0],  # Single frame
                file_list=[filename],
                directory=directory,
            )
            sequences.append(sequence)

        # Sort sequences by base_name for consistent display
        sequences.sort(key=lambda s: (s.base_name, s.extension))

        logger.debug(f"Detected {len(sequences)} sequence(s) in {directory}")
        return sequences

    def _display_sequence_thumbnails(self, sequence: ImageSequence) -> None:
        """
        Display thumbnail previews for a specific image sequence.

        Args:
            sequence: ImageSequence object to display
        """
        # Clear existing thumbnails
        self._clear_preview()

        # Update info label
        frame_count = len(sequence.frames)
        self.info_label.setText(f"{sequence.display_name}\n" f"Directory: {sequence.directory}")

        # Load and display thumbnails (limit to MAX_THUMBNAILS)
        thumbnails_to_show = min(frame_count, self.MAX_THUMBNAILS)

        # Calculate stride for even distribution
        stride = max(1, frame_count // thumbnails_to_show)

        for i in range(thumbnails_to_show):
            file_index = i * stride
            if file_index >= len(sequence.file_list):
                break

            filename = sequence.file_list[file_index]
            image_path = os.path.join(sequence.directory, filename)
            frame_number = sequence.frames[file_index] if file_index < len(sequence.frames) else 0
            thumbnail_label = self._create_thumbnail(image_path, frame_number)

            if thumbnail_label:
                row = i // self.THUMBNAILS_PER_ROW
                col = i % self.THUMBNAILS_PER_ROW
                self.thumbnail_layout.addWidget(thumbnail_label, row, col)

    def _create_thumbnail(self, image_path: str, frame_number: int) -> QWidget | None:
        """
        Create a thumbnail widget for an image with caching.

        Args:
            image_path: Path to the image file
            frame_number: Frame number to display

        Returns:
            QLabel widget with thumbnail or None if failed
        """
        try:
            # Check cache first
            cached_pixmap = self.thumbnail_cache.get(image_path, self.THUMBNAIL_SIZE)
            if cached_pixmap is not None:
                logger.debug(f"Cache hit for thumbnail: {image_path}")
                scaled_pixmap = cached_pixmap
            else:
                # Cache miss - load and generate thumbnail
                logger.debug(f"Cache miss for thumbnail: {image_path}")

                # Check if this is an EXR file (requires special loader)
                image_path_obj = Path(image_path)
                if image_path_obj.suffix.lower() == ".exr":
                    from io_utils.exr_loader import load_exr_as_qpixmap

                    pixmap = load_exr_as_qpixmap(image_path)
                else:
                    pixmap = QPixmap(image_path)

                if pixmap is None or pixmap.isNull():
                    logger.warning(f"Failed to load image: {image_path}")
                    return None

                # Scale to thumbnail size while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    QSize(self.THUMBNAIL_SIZE, self.THUMBNAIL_SIZE),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )

                # Store in cache for next time
                self.thumbnail_cache.store(image_path, self.THUMBNAIL_SIZE, scaled_pixmap)

            # Create label with thumbnail
            thumbnail_label = QLabel()
            thumbnail_label.setPixmap(scaled_pixmap)
            thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumbnail_label.setFrameStyle(QLabel.Shape.Box)
            thumbnail_label.setStyleSheet(f"QLabel {{ background-color: #2b2b2b; padding: {SPACING_SM}px; }}")

            # Add frame number below thumbnail
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(SPACING_XS)
            layout.addWidget(thumbnail_label)

            frame_label = QLabel(f"Frame {frame_number}")
            frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            frame_label.setStyleSheet(f"font-size: {FONT_SIZE_SMALL}pt; color: #aaa;")
            layout.addWidget(frame_label)

            return container

        except Exception as e:
            logger.error(f"Failed to create thumbnail for {image_path}: {e}")
            return None

    def _clear_preview(self) -> None:
        """Clear all thumbnail previews."""
        # Remove all widgets from thumbnail layout
        while self.thumbnail_layout.count():
            item = self.thumbnail_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

    def _update_metadata_panel(self, sequence: ImageSequence) -> None:
        """
        Update metadata panel with sequence information.

        Args:
            sequence: ImageSequence to display metadata for
        """
        # Resolution
        if sequence.resolution:
            # Get resolution with label if available
            labels = {
                (1920, 1080): "HD",
                (2048, 1556): "2K Academy",
                (2048, 1080): "2K DCI",
                (3840, 2160): "4K UHD",
                (4096, 2160): "4K DCI",
                (7680, 4320): "8K UHD",
            }
            label = labels.get(sequence.resolution, "")
            res_str = f"{sequence.resolution[0]}x{sequence.resolution[1]}"
            if label:
                res_str += f" ({label})"
            self.metadata_labels["resolution"].setText(f"Resolution: {res_str}")
        else:
            self.metadata_labels["resolution"].setText("Resolution: Unknown")

        # Bit depth
        if sequence.bit_depth:
            self.metadata_labels["bit_depth"].setText(f"Bit Depth: {sequence.bit_depth}-bit")
        else:
            self.metadata_labels["bit_depth"].setText("Bit Depth: Unknown")

        # Color space
        if sequence.color_space:
            self.metadata_labels["color_space"].setText(f"Color Space: {sequence.color_space}")
        else:
            self.metadata_labels["color_space"].setText("Color Space: Unknown")

        # Frame count
        frame_count = len(sequence.frames)
        plural = "s" if frame_count != 1 else ""
        self.metadata_labels["frame_count"].setText(f"Frame Count: {frame_count} frame{plural}")

        # Total size
        if sequence.total_size_bytes > 0:
            size_mb = sequence.total_size_bytes / (1024 * 1024)
            if size_mb >= 1024:
                size_gb = size_mb / 1024
                size_str = f"{size_gb:.2f} GB"
            else:
                size_str = f"{size_mb:.1f} MB"
            self.metadata_labels["total_size"].setText(f"Total Size: {size_str}")
        else:
            self.metadata_labels["total_size"].setText("Total Size: Unknown")

        # Missing frames / gaps
        if sequence.has_gaps:
            missing_count = len(sequence.missing_frames)
            missing_preview = sequence.missing_frames[:10]
            if len(sequence.missing_frames) > 10:
                missing_str = f"{missing_preview}... ({missing_count} total)"
            else:
                missing_str = str(sequence.missing_frames)
            self.metadata_labels["gaps"].setText(f"Missing Frames: {missing_str}")
            self.metadata_labels["gaps"].setStyleSheet(
                f"font-size: {FONT_SIZE_NORMAL}pt; padding: {SPACING_XS}px; color: #ff9900;"
            )
        else:
            self.metadata_labels["gaps"].setText("Missing Frames: None (Complete)")
            self.metadata_labels["gaps"].setStyleSheet(
                f"font-size: {FONT_SIZE_NORMAL}pt; padding: {SPACING_XS}px; color: #00cc00;"
            )

        # Show metadata panel
        self.metadata_panel.setVisible(True)

    def get_selected_directory(self) -> str | None:
        """
        Get the selected directory path.

        Returns:
            Selected directory path or None if cancelled
        """
        return self.selected_directory

    def _populate_favorites(self) -> None:
        """Populate favorites list from manager."""
        self.favorites_list.clear()
        for favorite in self.favorites_manager.get_all():
            item = QListWidgetItem(f"★ {favorite.name}")
            item.setData(Qt.ItemDataRole.UserRole, favorite.path)
            item.setToolTip(favorite.path)
            self.favorites_list.addItem(item)

    def _on_add_to_favorites(self) -> None:
        """Add current directory to favorites."""
        from PySide6.QtWidgets import QInputDialog

        current_index = self.tree_view.currentIndex()
        if not current_index.isValid():
            return

        current_path = self.file_model.filePath(current_index)

        # Check if already favorited
        if self.favorites_manager.is_favorite(current_path):
            self.info_label.setText("Directory already in favorites!")
            return

        # Prompt for name
        name, ok = QInputDialog.getText(
            self, "Add to Favorites", "Enter name for this favorite:", text=Path(current_path).name
        )

        if ok and name:
            if self.favorites_manager.add(name, current_path):
                self._populate_favorites()
                self._update_favorite_button_state()
                self.info_label.setText(f"Added '{name}' to favorites")

    def _on_favorite_double_clicked(self, item: QListWidgetItem) -> None:
        """Navigate to favorite on double-click.

        Args:
            item: List widget item that was double-clicked
        """
        path = item.data(Qt.ItemDataRole.UserRole)
        if path and Path(path).exists():
            self._navigate_to_path(path)
        else:
            self.info_label.setText(f"Favorite path no longer exists: {path}")

    def _show_favorites_context_menu(self, pos: QPoint) -> None:
        """Show context menu for favorites list.

        Args:
            pos: Position where context menu was requested
        """
        from PySide6.QtWidgets import QInputDialog, QMenu

        item = self.favorites_list.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)

        # Actions
        rename_action = menu.addAction("Rename")
        remove_action = menu.addAction("Remove")
        menu.addSeparator()
        move_up_action = menu.addAction("Move Up")
        move_down_action = menu.addAction("Move Down")

        action = menu.exec(self.favorites_list.mapToGlobal(pos))
        path = item.data(Qt.ItemDataRole.UserRole)

        if action == rename_action:
            name, ok = QInputDialog.getText(self, "Rename Favorite", "Enter new name:", text=item.text().lstrip("★ "))
            if ok and name:
                self.favorites_manager.rename(path, name)
                self._populate_favorites()

        elif action == remove_action:
            # Confirm before removing
            from PySide6.QtWidgets import QMessageBox

            reply = QMessageBox.question(
                self,
                "Remove Favorite",
                f"Remove '{item.text().lstrip('★ ')}' from favorites?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,  # Default to No for safety
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.favorites_manager.remove(path)
                self._populate_favorites()
                self._update_favorite_button_state()

        elif action == move_up_action:
            self.favorites_manager.move_up(path)
            self._populate_favorites()

        elif action == move_down_action:
            self.favorites_manager.move_down(path)
            self._populate_favorites()

    def _update_favorite_button_state(self) -> None:
        """Update favorite button based on current directory."""
        current_index = self.tree_view.currentIndex()
        if not current_index.isValid():
            self.favorite_button.setEnabled(False)
            return

        current_path = self.file_model.filePath(current_index)
        is_favorited = self.favorites_manager.is_favorite(current_path)

        self.favorite_button.setEnabled(True)
        if is_favorited:
            self.favorite_button.setToolTip(f"Already in favorites: {current_path}")
            self.favorite_button.setStyleSheet("QToolButton { color: gold; }")
        else:
            self.favorite_button.setToolTip("Add current directory to favorites (Ctrl+D)")
            self.favorite_button.setStyleSheet("")

    def _populate_drives(self) -> None:
        """Populate drive selector with available drives (Windows only)."""
        if sys.platform != "win32" or self.drive_selector is None:
            return

        # Defensive guard: tree_view must be initialized before calling this method
        if not hasattr(self, "tree_view"):
            return

        # Get available drives by checking A-Z
        available_drives = []
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive_path = Path(f"{letter}:/")
            if drive_path.exists():
                available_drives.append(f"{letter}:")

        # Add drives to combo box
        self.drive_selector.clear()
        for drive in available_drives:
            self.drive_selector.addItem(drive)

        # Set current drive based on current directory
        current_index = self.tree_view.currentIndex()
        if current_index.isValid():
            current_path = self.file_model.filePath(current_index)
            if len(current_path) >= 2 and current_path[1] == ":":
                current_drive = current_path[0].upper() + ":"
                index = self.drive_selector.findText(current_drive)
                if index >= 0:
                    # Block signals temporarily to avoid triggering navigation
                    self.drive_selector.blockSignals(True)
                    self.drive_selector.setCurrentIndex(index)
                    self.drive_selector.blockSignals(False)

    def _on_drive_selected(self, drive: str) -> None:
        """Handle drive selection from combo box.

        Args:
            drive: Selected drive letter (e.g., "C:")
        """
        if not drive:
            return

        # Navigate to drive root
        drive_path = f"{drive}/"
        self._navigate_to_path(drive_path)

    def _setup_quick_access_menu(self) -> None:
        """Setup quick access menu with common locations."""
        from PySide6.QtWidgets import QMenu

        menu = QMenu(self)

        # Get quick access locations
        locations = self._get_quick_access_locations()

        # Add menu items
        for name, path in locations.items():
            if path.exists():
                action = menu.addAction(name)
                # Use functools.partial to avoid lambda default parameter issue
                from functools import partial

                action.triggered.connect(partial(self._on_quick_access_clicked, str(path)))

        self.quick_access_button.setMenu(menu)

    def _get_quick_access_locations(self) -> dict[str, Path]:
        """Get dictionary of quick access locations.

        Returns:
            Dictionary mapping display name to Path
        """
        home = Path.home()
        locations = {
            "Desktop": home / "Desktop",
            "Documents": home / "Documents",
            "Downloads": home / "Downloads",
            "Pictures": home / "Pictures",
        }

        # Add platform-specific locations
        if sys.platform == "win32":
            # Windows-specific locations
            if (home / "Videos").exists():
                locations["Videos"] = home / "Videos"
        elif sys.platform == "darwin":
            # macOS-specific locations
            if (home / "Movies").exists():
                locations["Movies"] = home / "Movies"

        return locations

    def _on_quick_access_clicked(self, path: str, checked: bool = False) -> None:
        """Handle quick access location click.

        Args:
            path: Path to navigate to
            checked: Signal parameter (unused)
        """
        self._navigate_to_path(path)

    def _abbreviate_path(self, path: str, max_length: int = 60) -> str:
        """Abbreviate long paths for display.

        Args:
            path: Full path to abbreviate
            max_length: Maximum display length

        Returns:
            Abbreviated path string
        """
        if len(path) <= max_length:
            return path

        # For Windows paths, show drive + ... + last 2 components
        path_obj = Path(path)
        parts = path_obj.parts

        if sys.platform == "win32" and len(parts) > 3:
            # Windows: "C:\...\parent\current"
            drive = parts[0]
            parent = parts[-2] if len(parts) > 1 else ""
            current = parts[-1]
            abbreviated = f"{drive}\\...\\{parent}\\{current}"
        elif len(parts) > 3:
            # Unix: ".../parent/current"
            parent = parts[-2] if len(parts) > 1 else ""
            current = parts[-1]
            abbreviated = f".../{parent}/{current}"
        else:
            # Path is short but still exceeds max_length, truncate middle
            half = (max_length - 3) // 2
            abbreviated = path[:half] + "..." + path[-half:]

        return abbreviated

    def _show_tree_context_menu(self, pos: QPoint) -> None:
        """Show context menu for directory tree.

        Args:
            pos: Position where context menu was requested
        """
        from PySide6.QtWidgets import QMenu

        index = self.tree_view.indexAt(pos)
        if not index.isValid():
            return

        path = self.file_model.filePath(index)
        menu = QMenu(self)

        # Copy Path action
        copy_action = menu.addAction("Copy Path")
        copy_action.triggered.connect(lambda: self._copy_path_to_clipboard(path))

        # Open in File Manager action
        menu.addSeparator()
        if sys.platform == "win32":
            open_action = menu.addAction("Open in File Explorer")
        elif sys.platform == "darwin":
            open_action = menu.addAction("Open in Finder")
        else:
            open_action = menu.addAction("Open in File Manager")
        open_action.triggered.connect(lambda: self._open_in_file_manager(path))

        # Show menu
        menu.exec(self.tree_view.mapToGlobal(pos))

    def _copy_path_to_clipboard(self, path: str) -> None:
        """Copy path to system clipboard.

        Args:
            path: Path to copy
        """
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(path)
            self.info_label.setText(f"Copied to clipboard: {path}")

    def _open_in_file_manager(self, path: str) -> None:
        """Open path in system file manager.

        Args:
            path: Directory path to open
        """
        import subprocess

        try:
            if sys.platform == "win32":
                # Windows: use explorer
                os.startfile(path)  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                # macOS: use open
                subprocess.run(["open", path], check=True)
            else:
                # Linux: use xdg-open
                subprocess.run(["xdg-open", path], check=True)

            logger.debug(f"Opened {path} in file manager")
        except Exception as e:
            logger.error(f"Failed to open {path} in file manager: {e}")
            self.info_label.setText(f"Failed to open in file manager: {e}")

    def _on_sort_changed(self, sort_text: str) -> None:
        """
        Handle sort criterion change.

        Args:
            sort_text: Display text for sort criterion
        """
        # Map display text to internal sort key
        sort_map = {
            "Name": "name",
            "Frame Count": "frame_count",
            "File Size": "size",
            "Date Modified": "date",
        }
        self.current_sort = sort_map.get(sort_text, "name")
        self._apply_sort()

    def _toggle_sort_order(self) -> None:
        """Toggle between ascending and descending sort order."""
        self.sort_ascending = not self.sort_ascending
        self.sort_order_button.setText("↑" if self.sort_ascending else "↓")
        self.sort_order_button.setToolTip(f"Sort order: {'Ascending' if self.sort_ascending else 'Descending'}")
        self._apply_sort()

    def _apply_sort(self) -> None:
        """Apply current sort settings to sequence list."""
        # Collect all sequences (not items, since we'll recreate them)
        sequences: list[ImageSequence] = []
        for i in range(self.sequence_list.count()):
            item = self.sequence_list.item(i)
            if item:
                seq = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(seq, ImageSequence):
                    sequences.append(seq)

        # Sort by current criterion
        if self.current_sort == "name":
            sequences.sort(key=lambda x: x.base_name.lower(), reverse=not self.sort_ascending)
        elif self.current_sort == "frame_count":
            sequences.sort(key=lambda x: len(x.frames), reverse=not self.sort_ascending)
        elif self.current_sort == "size":
            sequences.sort(key=lambda x: x.total_size_bytes, reverse=not self.sort_ascending)
        elif self.current_sort == "date":
            # Sort by modification time of first file in sequence
            def get_mtime(seq: ImageSequence) -> float:
                if seq.file_list:
                    first_file = os.path.join(seq.directory, seq.file_list[0])
                    try:
                        return os.path.getmtime(first_file)
                    except OSError:
                        return 0.0
                return 0.0

            sequences.sort(key=lambda x: get_mtime(x), reverse=not self.sort_ascending)

        # Rebuild list in sorted order (recreate items to avoid C++ deletion issues)
        self.sequence_list.clear()
        for seq in sequences:
            from PySide6.QtWidgets import QListWidgetItem

            item = QListWidgetItem(seq.display_name)
            item.setData(Qt.ItemDataRole.UserRole, seq)
            # Preserve warning icon if sequence has gaps
            if seq.has_gaps:
                item.setText(f"⚠️ {seq.display_name}")
                item.setToolTip(f"WARNING: Missing {len(seq.missing_frames)} frames")
                item.setForeground(Qt.GlobalColor.darkYellow)
            self.sequence_list.addItem(item)

    def _restore_state(self) -> None:
        """Restore dialog state from parent's state manager."""
        parent_window = self.parent()
        if not hasattr(parent_window, "state_manager"):
            return

        state_manager = getattr(parent_window, "state_manager", None)
        if not state_manager:
            return

        # Restore dialog geometry
        if hasattr(state_manager, "get_value"):
            saved_geometry = state_manager.get_value("image_browser_geometry")
            if saved_geometry:
                try:
                    from PySide6.QtCore import QByteArray

                    if isinstance(saved_geometry, bytes | QByteArray):
                        self.restoreGeometry(saved_geometry)
                except Exception as e:
                    logger.warning(f"Failed to restore dialog geometry: {e}")

            # Restore splitter state
            saved_splitter = state_manager.get_value("image_browser_splitter")
            if saved_splitter and hasattr(self, "splitter"):
                try:
                    from PySide6.QtCore import QByteArray

                    if isinstance(saved_splitter, bytes | QByteArray):
                        self.splitter.restoreState(saved_splitter)
                except Exception as e:
                    logger.warning(f"Failed to restore splitter state: {e}")

            # Restore sort preferences
            saved_sort = state_manager.get_value("image_browser_sort")
            if saved_sort:
                self.current_sort = saved_sort
                sort_map_reverse = {
                    "name": "Name",
                    "frame_count": "Frame Count",
                    "size": "File Size",
                    "date": "Date Modified",
                }
                display_text = sort_map_reverse.get(saved_sort, "Name")
                index = self.sort_combo.findText(display_text)
                if index >= 0:
                    self.sort_combo.setCurrentIndex(index)

            saved_sort_order = state_manager.get_value("image_browser_sort_ascending")
            if saved_sort_order is not None:
                self.sort_ascending = saved_sort_order
                self.sort_order_button.setText("↑" if self.sort_ascending else "↓")

    def _save_state(self) -> None:
        """Save dialog state to parent's state manager."""
        parent_window = self.parent()
        if not hasattr(parent_window, "state_manager"):
            return

        state_manager = getattr(parent_window, "state_manager", None)
        if not state_manager:
            return

        # Save dialog geometry
        if hasattr(state_manager, "set_value"):
            try:
                state_manager.set_value("image_browser_geometry", self.saveGeometry())
            except Exception as e:
                logger.warning(f"Failed to save dialog geometry: {e}")

            # Save splitter state
            if hasattr(self, "splitter"):
                try:
                    state_manager.set_value("image_browser_splitter", self.splitter.saveState())
                except Exception as e:
                    logger.warning(f"Failed to save splitter state: {e}")

            # Save sort preferences
            state_manager.set_value("image_browser_sort", self.current_sort)
            state_manager.set_value("image_browser_sort_ascending", self.sort_ascending)

    def accept(self) -> None:
        """Override to save state before closing."""
        self._save_state()
        super().accept()

    def reject(self) -> None:
        """Override to save state before closing."""
        self._save_state()
        super().reject()


# Module-level constant for thumbnail size (referenced in line 144)
THUMBNAIL_SIZE = ImageSequenceBrowserDialog.THUMBNAIL_SIZE

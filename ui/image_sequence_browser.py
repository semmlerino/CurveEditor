#!/usr/bin/env python
"""
Image Sequence Browser Dialog for CurveEditor.

Provides a visual browser for selecting image sequences with thumbnail previews,
similar to 3DEqualizer or Nuke's sequence view.
"""

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QDir, QPoint, QSize, Qt
from PySide6.QtGui import QKeySequence, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileSystemModel,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
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

if TYPE_CHECKING:
    from PySide6.QtCore import QModelIndex

logger = get_logger("image_sequence_browser")


@dataclass
class ImageSequence:
    """
    Represents a detected image sequence.

    Attributes:
        base_name: Prefix before frame numbers (e.g., "render_")
        padding: Number of digits in frame padding (e.g., 4 for "0001")
        extension: File extension including dot (e.g., ".exr")
        frames: List of actual frame numbers found
        file_list: List of actual filenames in sequence
        directory: Directory containing the sequence
    """

    base_name: str
    padding: int
    extension: str
    frames: list[int]
    file_list: list[str]
    directory: str

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
    def display_name(self) -> str:
        """Generate display name for sequence (e.g., 'render_####.exr [1-100] (100 frames)')."""
        padding_str = "#" * self.padding
        frame_count = len(self.frames)
        plural = "s" if frame_count != 1 else ""
        return f"{self.base_name}{padding_str}{self.extension} {self.frame_range_str} ({frame_count} frame{plural})"


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

        # Determine best starting directory
        self.start_directory = self._determine_start_directory(parent, start_directory)

        self._setup_ui()
        self._connect_signals()
        self._setup_shortcuts()

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
        top_nav_bar.setContentsMargins(5, 5, 5, 5)

        # Up button (go to parent directory)
        self.up_button = QToolButton()
        self.up_button.setText("↑")
        self.up_button.setToolTip("Go to parent directory")
        self.up_button.setFixedSize(32, 32)
        top_nav_bar.addWidget(self.up_button)

        # Home button
        self.home_button = QToolButton()
        self.home_button.setText("🏠")
        self.home_button.setToolTip("Go to home directory")
        self.home_button.setFixedSize(32, 32)
        top_nav_bar.addWidget(self.home_button)

        # Windows drive selector (only on Windows)
        if sys.platform == "win32":
            self.drive_selector = QComboBox()
            self.drive_selector.setToolTip("Select drive")
            self.drive_selector.setMinimumWidth(60)
            self.drive_selector.setMaximumWidth(80)
            top_nav_bar.addWidget(self.drive_selector)
            self._populate_drives()
        else:
            self.drive_selector = None

        # Quick Access dropdown
        self.quick_access_button = QToolButton()
        self.quick_access_button.setText("⚡")
        self.quick_access_button.setToolTip("Quick access to common locations")
        self.quick_access_button.setFixedSize(32, 32)
        self.quick_access_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        top_nav_bar.addWidget(self.quick_access_button)

        # Address bar (path input) - editable combo box with recent directories
        self.address_bar = QComboBox()
        self.address_bar.setEditable(True)
        self.address_bar.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.address_bar.setMinimumHeight(32)
        if self.address_bar.lineEdit():
            self.address_bar.lineEdit().setPlaceholderText("Enter directory path...")
        self.address_bar.setToolTip("Type or paste a directory path, or select from recent (Ctrl+L to focus)")
        top_nav_bar.addWidget(self.address_bar)

        # Go button for address bar
        self.go_button = QToolButton()
        self.go_button.setText("Go")
        self.go_button.setToolTip("Navigate to entered path")
        self.go_button.setFixedSize(50, 32)
        top_nav_bar.addWidget(self.go_button)

        # Add to Favorites button
        self.favorite_button = QToolButton()
        self.favorite_button.setText("★")
        self.favorite_button.setToolTip("Add current directory to favorites")
        self.favorite_button.setFixedSize(32, 32)
        self.favorite_button.setEnabled(False)
        top_nav_bar.addWidget(self.favorite_button)

        main_layout.addLayout(top_nav_bar)

        # Create splitter for three-panel layout
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Favorites + Directory tree
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Favorites section (collapsible)
        favorites_group = QGroupBox("Favorites")
        favorites_group.setCheckable(True)
        favorites_group.setChecked(True)  # Expanded by default
        favorites_layout = QVBoxLayout()
        favorites_layout.setContentsMargins(5, 5, 5, 5)

        self.favorites_list = QListWidget()
        self.favorites_list.setMaximumHeight(150)
        self.favorites_list.setAlternatingRowColors(True)
        self.favorites_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        favorites_layout.addWidget(self.favorites_list)

        favorites_group.setLayout(favorites_layout)
        left_layout.addWidget(favorites_group)

        # Directory tree label
        tree_label = QLabel("All Directories:")
        tree_label.setStyleSheet("font-weight: bold; padding: 5px;")
        left_layout.addWidget(tree_label)

        # Directory tree
        self.tree_view = QTreeView()
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath("")
        self.file_model.setFilter(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot)
        self.tree_view.setModel(self.file_model)
        self.tree_view.setRootIndex(self.file_model.index(""))

        # Hide unnecessary columns (size, type, date modified)
        for i in range(1, 4):
            self.tree_view.hideColumn(i)

        left_layout.addWidget(self.tree_view)

        splitter.addWidget(left_panel)

        # Middle panel: Sequence list
        sequence_list_widget = QWidget()
        sequence_list_layout = QVBoxLayout(sequence_list_widget)
        sequence_list_layout.setContentsMargins(0, 0, 0, 0)

        sequence_label = QLabel("Image Sequences:")
        sequence_label.setStyleSheet("font-weight: bold; padding: 5px;")
        sequence_list_layout.addWidget(sequence_label)

        self.sequence_list = QListWidget()
        self.sequence_list.setAlternatingRowColors(True)
        sequence_list_layout.addWidget(self.sequence_list)

        splitter.addWidget(sequence_list_widget)

        # Right panel: Preview area
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)

        # Info label
        self.info_label = QLabel("Select a sequence to preview thumbnails")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.info_label.setStyleSheet("font-size: 11pt; padding: 10px;")
        preview_layout.addWidget(self.info_label)

        # Scroll area for thumbnails
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setMinimumWidth(THUMBNAIL_SIZE * 2 + 50)

        # Container widget for thumbnail grid
        self.thumbnail_container = QWidget()
        self.thumbnail_layout = QGridLayout(self.thumbnail_container)
        self.thumbnail_layout.setSpacing(10)
        self.scroll_area.setWidget(self.thumbnail_container)

        preview_layout.addWidget(self.scroll_area)
        splitter.addWidget(preview_widget)

        # Set splitter proportions (25% tree, 30% sequence list, 45% preview)
        splitter.setSizes([250, 350, 600])

        main_layout.addWidget(splitter)

        # Button box
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.load_button = QPushButton("Load Sequence")
        self.load_button.setEnabled(False)
        self.load_button.setDefault(True)
        button_layout.addWidget(self.load_button)

        cancel_button = QPushButton("Cancel")
        button_layout.addWidget(cancel_button)

        main_layout.addLayout(button_layout)

        # Connect button signals
        self.load_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.tree_view.clicked.connect(self._on_directory_selected)
        self.tree_view.clicked.connect(self._update_address_bar)
        self.sequence_list.currentItemChanged.connect(self._on_sequence_selected)
        self.sequence_list.itemDoubleClicked.connect(self._on_sequence_double_clicked)

        # Navigation signals
        self.up_button.clicked.connect(self._on_up_clicked)
        self.home_button.clicked.connect(self._on_home_clicked)
        self.go_button.clicked.connect(self._on_go_clicked)

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
        # Ctrl+L - Focus address bar (like web browsers)
        focus_address_bar = QShortcut(QKeySequence("Ctrl+L"), self)
        focus_address_bar.activated.connect(self._focus_address_bar)

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
        self.address_bar.setFocus()
        if self.address_bar.lineEdit():
            self.address_bar.lineEdit().selectAll()

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
        Handle directory selection - populates sequence list.

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

        # Show wait cursor and feedback during scanning
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        self.info_label.setText(f"Scanning directory...\n{directory_path}")
        QApplication.processEvents()  # Update UI to show feedback

        try:
            # Scan for image files
            image_files = self._scan_directory_for_images(directory_path)

            if not image_files:
                self.info_label.setText(f"No image files found in:\n{directory_path}")
                return

            # Detect sequences
            sequences = self._detect_sequences(directory_path, image_files)

            if not sequences:
                self.info_label.setText(f"No image sequences detected in:\n{directory_path}")
                return
        finally:
            # Always restore cursor, even if an error occurs
            QApplication.restoreOverrideCursor()

        # Populate sequence list
        for sequence in sequences:
            item_text = sequence.display_name
            self.sequence_list.addItem(item_text)
            # Store sequence object as item data for later retrieval
            self.sequence_list.item(self.sequence_list.count() - 1).setData(Qt.ItemDataRole.UserRole, sequence)

        # Update info label
        seq_count = len(sequences)
        plural = "s" if seq_count != 1 else ""
        self.info_label.setText(f"Found {seq_count} sequence{plural} in:\n{directory_path}")

        logger.debug(f"Populated sequence list with {seq_count} sequence(s)")

        # Auto-select first sequence for better workflow
        if self.sequence_list.count() > 0:
            self.sequence_list.setCurrentRow(0)
            # _on_sequence_selected will be triggered automatically by currentItemChanged signal

        # Update favorite button state
        self._update_favorite_button_state()

    def _on_sequence_selected(self) -> None:
        """Handle sequence selection from list - shows thumbnail preview."""
        current_item = self.sequence_list.currentItem()
        if not current_item:
            self._clear_preview()
            self.load_button.setEnabled(False)
            self.selected_sequence = None
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
        Create a thumbnail widget for an image.

        Args:
            image_path: Path to the image file
            frame_number: Frame number to display

        Returns:
            QLabel widget with thumbnail or None if failed
        """
        try:
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

            # Create label with thumbnail
            thumbnail_label = QLabel()
            thumbnail_label.setPixmap(scaled_pixmap)
            thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumbnail_label.setFrameStyle(QLabel.Shape.Box)
            thumbnail_label.setStyleSheet("QLabel { background-color: #2b2b2b; padding: 5px; }")

            # Add frame number below thumbnail
            container = QWidget()
            layout = QVBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            layout.addWidget(thumbnail_label)

            frame_label = QLabel(f"Frame {frame_number}")
            frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            frame_label.setStyleSheet("font-size: 9pt; color: #aaa;")
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
            self.favorite_button.setToolTip("Add current directory to favorites")
            self.favorite_button.setStyleSheet("")

    def _populate_drives(self) -> None:
        """Populate drive selector with available drives (Windows only)."""
        if sys.platform != "win32" or self.drive_selector is None:
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


# Module-level constant for thumbnail size (referenced in line 144)
THUMBNAIL_SIZE = ImageSequenceBrowserDialog.THUMBNAIL_SIZE

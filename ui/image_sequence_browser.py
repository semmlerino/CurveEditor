#!/usr/bin/env python
"""
Image Sequence Browser Dialog for CurveEditor.

Provides a visual browser for selecting image sequences with thumbnail previews,
similar to 3DEqualizer or Nuke's sequence view.
"""

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QDir, QSize, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileSystemModel,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

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
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".gif", ".exr"}

    # Thumbnail display settings
    THUMBNAIL_SIZE = 150
    THUMBNAILS_PER_ROW = 4
    MAX_THUMBNAILS = 12  # Show first 12 frames

    def __init__(self, parent: QWidget | None = None, start_directory: str | None = None):
        """
        Initialize the image sequence browser dialog.

        Args:
            parent: Parent widget
            start_directory: Initial directory to display (defaults to home)
        """
        super().__init__(parent)
        self.selected_directory: str | None = None
        self.selected_sequence: ImageSequence | None = None
        self.start_directory = start_directory or str(Path.home())

        self._setup_ui()
        self._connect_signals()

        # Set initial directory
        if self.start_directory and Path(self.start_directory).exists():
            index = self.file_model.index(self.start_directory)
            self.tree_view.setCurrentIndex(index)
            self.tree_view.expand(index)
            self._on_directory_selected(index)

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.setWindowTitle("Load Image Sequence")
        self.resize(1200, 600)

        # Main layout
        main_layout = QVBoxLayout(self)

        # Create splitter for three-panel layout
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Directory tree
        self.tree_view = QTreeView()
        self.file_model = QFileSystemModel()
        self.file_model.setRootPath("")
        self.file_model.setFilter(QDir.Filter.Dirs | QDir.Filter.NoDotAndDotDot)
        self.tree_view.setModel(self.file_model)
        self.tree_view.setRootIndex(self.file_model.index(""))

        # Hide unnecessary columns (size, type, date modified)
        for i in range(1, 4):
            self.tree_view.hideColumn(i)

        splitter.addWidget(self.tree_view)

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
        self.sequence_list.currentItemChanged.connect(self._on_sequence_selected)
        self.sequence_list.itemDoubleClicked.connect(self._on_sequence_double_clicked)

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

            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in self.IMAGE_EXTENSIONS:
                        image_files.append(filename)

            image_files.sort()

        except (OSError, PermissionError) as e:
            logger.warning(f"Failed to scan directory {directory}: {e}")

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

    def _create_thumbnail(self, image_path: str, frame_number: int) -> QLabel | None:
        """
        Create a thumbnail widget for an image.

        Args:
            image_path: Path to the image file
            frame_number: Frame number to display

        Returns:
            QLabel widget with thumbnail or None if failed
        """
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
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


# Module-level constant for thumbnail size (referenced in line 144)
THUMBNAIL_SIZE = ImageSequenceBrowserDialog.THUMBNAIL_SIZE

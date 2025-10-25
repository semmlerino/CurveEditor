#!/usr/bin/env python
"""
Simplified Sequence List Widget for CurveEditor.

Provides a clean, compact display of image sequences with essential metadata
and visual indicators for sequence health.
"""

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from core.logger_utils import get_logger
from ui.ui_constants import FONT_SIZE_NORMAL, FONT_SIZE_SMALL, SPACING_SM, SPACING_XS

if TYPE_CHECKING:
    from ui.image_sequence_browser import ImageSequence

logger = get_logger("sequence_list_widget")


class SequenceItemWidget(QWidget):
    """
    Custom widget for displaying sequence information in list items.

    Shows sequence name, frame count, resolution, and health indicators
    in a compact, readable format.
    """

    def __init__(self, sequence: "ImageSequence", parent: QWidget | None = None):
        """
        Initialize sequence item widget.

        Args:
            sequence: ImageSequence data to display
            parent: Parent widget
        """
        super().__init__(parent)
        self.sequence = sequence
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_XS, SPACING_SM, SPACING_XS)
        layout.setSpacing(SPACING_SM)

        # Left side: Main info
        main_layout = QVBoxLayout()
        main_layout.setSpacing(2)

        # Sequence name (primary)
        name_label = QLabel(self._get_display_name())
        name_font = QFont()
        name_font.setPointSize(FONT_SIZE_NORMAL)
        name_font.setBold(True)
        name_label.setFont(name_font)
        name_label.setWordWrap(False)
        main_layout.addWidget(name_label)

        # Details (secondary)
        details_label = QLabel(self._get_details_text())
        details_font = QFont()
        details_font.setPointSize(FONT_SIZE_SMALL)
        details_label.setFont(details_font)
        details_label.setStyleSheet("color: #888;")
        main_layout.addWidget(details_label)

        layout.addLayout(main_layout, stretch=1)

        # Right side: Status indicators
        status_layout = QVBoxLayout()
        status_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)

        # Health indicator
        health_label = QLabel(self._get_health_indicator())
        health_font = QFont()
        health_font.setPointSize(FONT_SIZE_SMALL)
        health_label.setFont(health_font)
        health_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        status_layout.addWidget(health_label)

        # Resolution badge (if available)
        if self.sequence.resolution:
            resolution_label = QLabel(self._get_resolution_badge())
            resolution_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            resolution_label.setStyleSheet(
                f"""
                QLabel {{
                    background-color: #4a90e2;
                    color: white;
                    padding: 2px 6px;
                    border-radius: 3px;
                    font-size: {FONT_SIZE_SMALL - 1}pt;
                    font-weight: bold;
                }}
                """
            )
            status_layout.addWidget(resolution_label)

        layout.addLayout(status_layout)

        # Set size policy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setFixedHeight(50)

    def _get_display_name(self) -> str:
        """Get formatted display name for the sequence."""
        # Create a clean display name
        padding_str = "#" * self.sequence.padding
        return f"{self.sequence.base_name}{padding_str}{self.sequence.extension}"

    def _get_details_text(self) -> str:
        """Get details text showing frame range and count."""
        frame_count = len(self.sequence.frames)
        frame_range = self.sequence.frame_range_str

        # Add file size if available
        size_text = ""
        if self.sequence.total_size_bytes > 0:
            if self.sequence.total_size_mb < 1024:
                size_text = f" • {self.sequence.total_size_mb:.1f} MB"
            else:
                size_gb = self.sequence.total_size_mb / 1024
                size_text = f" • {size_gb:.1f} GB"

        plural = "s" if frame_count != 1 else ""
        return f"{frame_range} • {frame_count} frame{plural}{size_text}"

    def _get_health_indicator(self) -> str:
        """Get health indicator text and styling."""
        if self.sequence.has_gaps:
            missing_count = len(self.sequence.missing_frames)
            return f"⚠️ {missing_count} missing"
        else:
            return "✅ Complete"

    def _get_resolution_badge(self) -> str:
        """Get resolution badge text."""
        if not self.sequence.resolution:
            return ""

        # Common resolution labels
        width, height = self.sequence.resolution
        labels = {
            (1920, 1080): "HD",
            (2048, 1556): "2K",
            (3840, 2160): "4K",
            (4096, 2160): "4K DCI",
            (7680, 4320): "8K",
        }

        return labels.get((width, height), f"{width}×{height}")


class SequenceListWidget(QListWidget):
    """
    Simplified list widget for displaying image sequences.

    Features:
    - Compact sequence display with essential metadata
    - Visual health indicators for missing frames
    - Smart sorting with user-friendly options
    - Keyboard navigation support
    """

    # Signals
    sequence_selected = Signal(object)  # Emits ImageSequence when selected
    sequence_activated = Signal(object)  # Emits ImageSequence when double-clicked/Enter

    def __init__(self, parent: QWidget | None = None):
        """
        Initialize the sequence list widget.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self._sequences: list[ImageSequence] = []
        self._sort_key: str = "name"
        self._sort_ascending: bool = True

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Configure list widget
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        # Set accessible properties
        self.setAccessibleName("Image sequences")
        self.setAccessibleDescription(

            "List of image sequences found in the selected directory. "
            "Select a sequence to preview, double-click or press Enter to load."

        )

        # Enable keyboard navigation
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        self.currentItemChanged.connect(self._on_current_item_changed)
        self.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.itemActivated.connect(self._on_item_activated)

    def set_sequences(self, sequences: list["ImageSequence"]) -> None:
        """
        Set the list of sequences to display.

        Args:
            sequences: List of ImageSequence objects
        """
        self._sequences = sequences.copy()
        self._refresh_display()

    def add_sequence(self, sequence: "ImageSequence") -> None:
        """
        Add a single sequence to the list.

        Args:
            sequence: ImageSequence to add
        """
        self._sequences.append(sequence)
        self._refresh_display()

    def clear_sequences(self) -> None:
        """Clear all sequences from the list."""
        self._sequences.clear()
        self.clear()

    def set_sort_order(self, sort_key: str, ascending: bool = True) -> None:
        """
        Set the sort order for sequences.

        Args:
            sort_key: Sort key ("name", "frame_count", "size", "date")
            ascending: Whether to sort in ascending order
        """
        self._sort_key = sort_key
        self._sort_ascending = ascending
        self._refresh_display()

    def get_selected_sequence(self) -> "ImageSequence | None":
        """
        Get the currently selected sequence.

        Returns:
            Selected ImageSequence or None if no selection
        """
        current_item = self.currentItem()
        if current_item:
            # Get sequence from item data
            sequence_index = current_item.data(Qt.ItemDataRole.UserRole)
            if sequence_index is not None and 0 <= sequence_index < len(self._sequences):
                return self._sequences[sequence_index]
        return None

    def select_sequence_by_name(self, sequence_name: str) -> bool:
        """
        Select a sequence by its display name.

        Args:
            sequence_name: Name of sequence to select

        Returns:
            True if sequence was found and selected
        """
        for i in range(self.count()):
            item = self.item(i)
            if item:
                sequence_index = item.data(Qt.ItemDataRole.UserRole)
                if sequence_index is not None and 0 <= sequence_index < len(self._sequences):
                    sequence = self._sequences[sequence_index]
                    if sequence.display_name == sequence_name:
                        self.setCurrentItem(item)
                        return True
        return False

    def _refresh_display(self) -> None:
        """Refresh the display with current sequences and sort order."""
        # Clear current items
        self.clear()

        if not self._sequences:
            return

        # Sort sequences
        sorted_sequences = self._sort_sequences(self._sequences)

        # Create list items
        for i, sequence in enumerate(sorted_sequences):
            # Create custom widget
            item_widget = SequenceItemWidget(sequence)

            # Create list item
            item = QListWidgetItem()
            item.setSizeHint(item_widget.sizeHint())
            item.setData(Qt.ItemDataRole.UserRole, i)  # Store original index

            # Add to list
            self.addItem(item)
            self.setItemWidget(item, item_widget)

        # Update sequences list to match sorted order
        self._sequences = sorted_sequences

        logger.debug(f"Refreshed display with {len(self._sequences)} sequences, sorted by {self._sort_key}")

    def _sort_sequences(self, sequences: list["ImageSequence"]) -> list["ImageSequence"]:
        """
        Sort sequences according to current sort settings.

        Args:
            sequences: List of sequences to sort

        Returns:
            Sorted list of sequences
        """
        if not sequences:
            return sequences

        # Define sort key functions
        sort_functions = {
            "name": lambda seq: seq.base_name.lower(),
            "frame_count": lambda seq: len(seq.frames),
            "size": lambda seq: seq.total_size_bytes,
            "date": lambda seq: max(
                (Path(seq.directory) / filename).stat().st_mtime
                for filename in seq.file_list[:5]  # Check first 5 files for performance
                if (Path(seq.directory) / filename).exists()
            ) if seq.file_list else 0,
        }

        sort_func = sort_functions.get(self._sort_key, sort_functions["name"])

        try:
            return sorted(sequences, key=sort_func, reverse=not self._sort_ascending)
        except Exception as e:
            logger.warning(f"Failed to sort sequences by {self._sort_key}: {e}")
            return sequences

    def _on_current_item_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        """Handle current item change."""
        if current:
            sequence_index = current.data(Qt.ItemDataRole.UserRole)
            if sequence_index is not None and 0 <= sequence_index < len(self._sequences):
                sequence = self._sequences[sequence_index]
                self.sequence_selected.emit(sequence)
                logger.debug(f"Selected sequence: {sequence.display_name}")

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle item double-click."""
        sequence_index = item.data(Qt.ItemDataRole.UserRole)
        if sequence_index is not None and 0 <= sequence_index < len(self._sequences):
            sequence = self._sequences[sequence_index]
            self.sequence_activated.emit(sequence)
            logger.debug(f"Activated sequence: {sequence.display_name}")

    def _on_item_activated(self, item: QListWidgetItem) -> None:
        """Handle item activation (Enter key)."""
        sequence_index = item.data(Qt.ItemDataRole.UserRole)
        if sequence_index is not None and 0 <= sequence_index < len(self._sequences):
            sequence = self._sequences[sequence_index]
            self.sequence_activated.emit(sequence)
            logger.debug(f"Activated sequence via keyboard: {sequence.display_name}")

    def filter_sequences(self, filter_text: str) -> None:
        """
        Filter sequences by text.

        Args:
            filter_text: Text to filter by (case-insensitive)
        """
        if not filter_text:
            # Show all sequences
            for i in range(self.count()):
                item = self.item(i)
                if item:
                    item.setHidden(False)
            return

        filter_lower = filter_text.lower()

        # Hide/show items based on filter
        for i in range(self.count()):
            item = self.item(i)
            if item:
                sequence_index = item.data(Qt.ItemDataRole.UserRole)
                if sequence_index is not None and 0 <= sequence_index < len(self._sequences):
                    sequence = self._sequences[sequence_index]

                    # Check if filter matches sequence name or path
                    matches = (
                        filter_lower in sequence.base_name.lower() or
                        filter_lower in sequence.extension.lower() or
                        filter_lower in sequence.directory.lower()
                    )

                    item.setHidden(not matches)

        logger.debug(f"Applied filter: '{filter_text}'")

    def get_visible_sequence_count(self) -> int:
        """
        Get the number of visible (non-filtered) sequences.

        Returns:
            Count of visible sequences
        """
        count = 0
        for i in range(self.count()):
            item = self.item(i)
            if item and not item.isHidden():
                count += 1
        return count

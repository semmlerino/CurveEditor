#!/usr/bin/env python
"""
Simple Sequence Browser Widget for CurveEditor.

Provides a streamlined interface for loading image sequences with minimal UI complexity.
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.logger_utils import get_logger
from ui.ui_constants import FONT_SIZE_LARGE, FONT_SIZE_NORMAL, SPACING_SM
from ui.widgets.sequence_list_widget import SequenceListWidget
from ui.widgets.sequence_preview_widget import SequencePreviewWidget
from ui.widgets.smart_location_selector import SmartLocationSelector

if TYPE_CHECKING:
    from ui.image_sequence_browser import ImageSequence
    from ui.state_manager import StateManager

logger = get_logger("simple_sequence_browser")


class SimpleSequenceBrowser(QWidget):
    """
    Simple mode interface for image sequence browsing.

    Features:
    - Smart location selector with recent directories
    - Compact sequence list with essential metadata
    - Thumbnail preview with progress indication
    - Minimal UI complexity for common workflows
    """

    # Signals
    sequence_selected = Signal(object)  # Emits ImageSequence when selected
    sequence_activated = Signal(object)  # Emits ImageSequence when activated (load)
    location_changed = Signal(str)      # Emits when directory location changes

    def __init__(self, parent: QWidget | None = None, state_manager: "StateManager | None" = None):
        """
        Initialize simple sequence browser.

        Args:
            parent: Parent widget
            state_manager: State manager for preferences and recent directories
        """
        super().__init__(parent)
        self.state_manager = state_manager
        # Note: _current_sequences is now a property (see line 270)

        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(SPACING_SM, SPACING_SM, SPACING_SM, SPACING_SM)
        layout.setSpacing(SPACING_SM)

        # Header with location selector
        header_layout = QVBoxLayout()

        # Title
        title_label = QLabel("Load Image Sequence")
        title_label.setStyleSheet(f"font-size: {FONT_SIZE_LARGE}pt; font-weight: bold; margin-bottom: {SPACING_SM}px;")
        header_layout.addWidget(title_label)

        # Location selector row
        location_layout = QHBoxLayout()
        location_layout.setSpacing(SPACING_SM)

        location_label = QLabel("Location:")
        location_label.setStyleSheet(f"font-size: {FONT_SIZE_NORMAL}pt;")
        location_layout.addWidget(location_label)

        self.location_selector = SmartLocationSelector(self, self.state_manager)
        location_layout.addWidget(self.location_selector, stretch=1)

        # Advanced mode button
        self.advanced_button = QPushButton("Advanced >>")
        self.advanced_button.setToolTip("Switch to advanced mode with full directory tree")
        self.advanced_button.setMaximumWidth(100)
        location_layout.addWidget(self.advanced_button)

        header_layout.addLayout(location_layout)
        layout.addLayout(header_layout)

        # Main content area (horizontal split)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(SPACING_SM)

        # Left side: Sequence list
        sequence_layout = QVBoxLayout()

        sequence_label = QLabel("Image Sequences:")
        sequence_label.setStyleSheet(f"font-size: {FONT_SIZE_NORMAL}pt; font-weight: bold;")
        sequence_layout.addWidget(sequence_label)

        self.sequence_list = SequenceListWidget()
        self.sequence_list.setMinimumWidth(350)
        sequence_layout.addWidget(self.sequence_list)

        content_layout.addLayout(sequence_layout, stretch=1)

        # Right side: Preview
        preview_layout = QVBoxLayout()

        preview_label = QLabel("Preview:")
        preview_label.setStyleSheet(f"font-size: {FONT_SIZE_NORMAL}pt; font-weight: bold;")
        preview_layout.addWidget(preview_label)

        self.preview_widget = SequencePreviewWidget()
        self.preview_widget.setMinimumWidth(400)
        preview_layout.addWidget(self.preview_widget)

        content_layout.addLayout(preview_layout, stretch=1)

        layout.addLayout(content_layout, stretch=1)

        # Status label with contextual help
        self.status_label = QLabel("Select a directory to browse image sequences")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"font-size: {FONT_SIZE_NORMAL}pt; color: #666; padding: {SPACING_SM}px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        # Help text (initially hidden)
        self.help_label = QLabel()
        self.help_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.help_label.setStyleSheet(f"font-size: {FONT_SIZE_NORMAL - 1}pt; color: #888; padding: {SPACING_SM}px;")
        self.help_label.setWordWrap(True)
        self.help_label.setVisible(False)
        layout.addWidget(self.help_label)

    def _connect_signals(self) -> None:
        """Connect internal signals."""
        # Location selector
        self.location_selector.location_selected.connect(self._on_location_selected)
        self.location_selector.location_changed.connect(self._on_location_changed)

        # Sequence list
        self.sequence_list.sequence_selected.connect(self._on_sequence_selected)
        self.sequence_list.sequence_activated.connect(self._on_sequence_activated)

        # Advanced button (will be connected by parent dialog)
        # self.advanced_button.clicked.connect(...)

    def _on_location_selected(self, path: str) -> None:
        """
        Handle location selection.

        Args:
            path: Selected directory path
        """
        self.location_changed.emit(path)
        self.status_label.setText(f"Scanning directory: {path}")
        logger.debug(f"Location selected: {path}")

    def _on_location_changed(self, path: str) -> None:
        """
        Handle location change (typing).

        Args:
            path: Current path text
        """
        # Provide real-time feedback but don't trigger scanning yet
        if path:
            self.status_label.setText(f"Type path or select from recent: {path}")
        else:
            self.status_label.setText("Select a directory to browse image sequences")

    def _on_sequence_selected(self, sequence: "ImageSequence") -> None:
        """
        Handle sequence selection.

        Args:
            sequence: Selected ImageSequence
        """
        # Update preview
        self.preview_widget.set_sequence(sequence)

        # Update status
        frame_count = len(sequence.frames)
        plural = "s" if frame_count != 1 else ""
        self.status_label.setText(f"Selected: {sequence.display_name} ({frame_count} frame{plural})")

        # Emit signal
        self.sequence_selected.emit(sequence)

        logger.debug(f"Sequence selected: {sequence.display_name}")

    def _on_sequence_activated(self, sequence: "ImageSequence") -> None:
        """
        Handle sequence activation (double-click or Enter).

        Args:
            sequence: Activated ImageSequence
        """
        self.sequence_activated.emit(sequence)
        logger.debug(f"Sequence activated: {sequence.display_name}")

    def set_sequences(self, sequences: list["ImageSequence"]) -> None:
        """
        Set the list of sequences to display.

        Args:
            sequences: List of ImageSequence objects
        """
        self._current_sequences = sequences
        self.sequence_list.set_sequences(sequences)

        # Update status and help
        count = len(sequences)
        if count == 0:
            self.status_label.setText("No image sequences found in this directory")
            self._show_help_for_empty_directory()
        else:
            plural = "s" if count != 1 else ""
            self.status_label.setText(f"Found {count} image sequence{plural}")
            self._hide_help()

        # Clear preview
        self.preview_widget.set_sequence(None)

        logger.debug(f"Set {count} sequences in simple browser")

    def clear_sequences(self) -> None:
        """Clear all sequences."""
        self._current_sequences.clear()
        self.sequence_list.clear_sequences()
        self.preview_widget.set_sequence(None)
        self.status_label.setText("Select a directory to browse image sequences")

    def get_selected_sequence(self) -> "ImageSequence | None":
        """
        Get the currently selected sequence.

        Returns:
            Selected ImageSequence or None
        """
        return self.sequence_list.get_selected_sequence()

    def set_current_location(self, path: str) -> None:
        """
        Set the current location.

        Args:
            path: Directory path to set
        """
        self.location_selector.set_location(path)

    def get_current_location(self) -> str:
        """
        Get the current location.

        Returns:
            Current directory path
        """
        return self.location_selector.get_location()

    @property
    def _current_sequences(self) -> list["ImageSequence"]:
        """Get current sequences (delegates to sequence_list for sorted order)."""
        return self.sequence_list._sequences

    @_current_sequences.setter
    def _current_sequences(self, sequences: list["ImageSequence"]) -> None:
        """Set current sequences (delegates to sequence_list)."""
        # This setter is called by set_sequences() and clear()
        # The actual storage is in sequence_list._sequences
        pass  # No-op, actual update happens via sequence_list.set_sequences()

    def set_sort_order(self, sort_key: str, ascending: bool = True) -> None:
        """
        Set the sort order for sequences.

        Args:
            sort_key: Sort key ("name", "frame_count", "size", "date")
            ascending: Whether to sort in ascending order
        """
        self.sequence_list.set_sort_order(sort_key, ascending)

    def filter_sequences(self, filter_text: str) -> None:
        """
        Filter sequences by text.

        Args:
            filter_text: Text to filter by
        """
        self.sequence_list.filter_sequences(filter_text)

        # Update status
        visible_count = self.sequence_list.get_visible_sequence_count()
        total_count = len(self._current_sequences)

        if filter_text:
            self.status_label.setText(f"Showing {visible_count} of {total_count} sequences")
        else:
            plural = "s" if total_count != 1 else ""
            self.status_label.setText(f"Found {total_count} image sequence{plural}")

    def set_loading_state(self, is_loading: bool, message: str = "") -> None:
        """
        Set loading state.

        Args:
            is_loading: Whether currently loading
            message: Loading message to display
        """
        if is_loading:
            self.status_label.setText(message or "Loading...")
            self.sequence_list.setEnabled(False)
        else:
            self.sequence_list.setEnabled(True)
            if not message:
                count = len(self._current_sequences)
                if count == 0:
                    self.status_label.setText("No image sequences found in this directory")
                else:
                    plural = "s" if count != 1 else ""
                    self.status_label.setText(f"Found {count} image sequence{plural}")
            else:
                self.status_label.setText(message)

    def refresh_recent_locations(self) -> None:
        """Refresh the recent locations in the location selector."""
        self.location_selector.refresh_locations()

    def set_project_context(self, project_name: str | None) -> None:
        """
        Set project context for location selector.

        Args:
            project_name: Name of current project
        """
        self.location_selector.set_project_context(project_name)

    def _show_help_for_empty_directory(self) -> None:
        """Show contextual help when no sequences are found."""
        help_text = (
            "💡 Tips for finding image sequences:\n\n"
            "• Look for numbered image files (e.g., render_001.jpg, comp.0001.exr)\n"
            "• Supported formats: JPG, PNG, EXR, DPX, TIFF, CIN, HDR\n"
            "• Files should follow patterns like 'name_###.ext' or 'name.####.ext'\n"
            "• Try browsing to a different directory or use the Advanced mode for more options"
        )
        self.help_label.setText(help_text)
        self.help_label.setVisible(True)

    def _hide_help(self) -> None:
        """Hide contextual help."""
        self.help_label.setVisible(False)

    def show_error_help(self, error_message: str, suggestions: list[str] | None = None) -> None:
        """
        Show contextual help for errors.

        Args:
            error_message: Error message to display
            suggestions: Optional list of suggestions
        """
        help_text = f"❌ {error_message}\n\n"

        if suggestions:
            help_text += "💡 Suggestions:\n"
            for suggestion in suggestions[:3]:  # Limit to 3 suggestions
                help_text += f"• {suggestion}\n"
        else:
            help_text += (
                "💡 Try:\n"
                "• Check the path is correct\n"
                "• Select a different directory\n"
                "• Use the Browse button for manual selection"
            )

        self.help_label.setText(help_text)
        self.help_label.setVisible(True)

    def show_loading_help(self) -> None:
        """Show help during loading operations."""
        help_text = (
            "🔍 Scanning directory for image sequences...\n\n"
            "This may take a moment for directories with many files.\n"
            "You can cancel the operation if it takes too long."
        )
        self.help_label.setText(help_text)
        self.help_label.setVisible(True)

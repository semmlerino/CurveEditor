#!/usr/bin/env python
"""
Modern card container widget for Phase 3: Visual Modernization.

Replaces QGroupBox with a modern card design featuring:
- Rounded corners
- Subtle shadows
- Clean visual hierarchy
- Optional collapsibility
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget

from ui.ui_constants import FONT_SIZE_HEADING, FONT_SIZE_NORMAL, SPACING_MD, SPACING_SM


class Card(QWidget):
    """
    Modern card container with shadow and rounded corners.

    Replaces QGroupBox with a cleaner, more modern appearance suitable for
    professional VFX tools like Nuke, Houdini, and 3DEqualizer.

    Features:
    - Rounded corners (8px border radius)
    - Subtle border and shadow
    - Bold title with optional collapse button
    - Consistent spacing using 8px grid system
    - Hover effects for interactivity
    """

    # Signal emitted when card is collapsed/expanded
    collapsed_changed = Signal(bool)  # True = collapsed, False = expanded

    def __init__(
        self,
        title: str = "",
        collapsible: bool = True,
        collapsed: bool = False,
        parent: QWidget | None = None,
    ):
        """
        Initialize card widget.

        Args:
            title: Card title text
            collapsible: Whether card can be collapsed
            collapsed: Initial collapsed state
            parent: Parent widget
        """
        super().__init__(parent)
        self._collapsible = collapsible
        self._collapsed = collapsed

        # Main layout
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(SPACING_MD, SPACING_MD, SPACING_MD, SPACING_MD)
        self._main_layout.setSpacing(SPACING_SM)

        # Header with title and optional collapse button
        if title:
            self._header = QWidget()
            header_layout = QHBoxLayout(self._header)
            header_layout.setContentsMargins(0, 0, 0, SPACING_SM)
            header_layout.setSpacing(SPACING_SM)

            # Title label
            self._title_label = QLabel(title)
            self._title_label.setStyleSheet(f"font-weight: bold; font-size: {FONT_SIZE_HEADING}pt;")
            header_layout.addWidget(self._title_label)

            # Collapse button (if collapsible)
            if collapsible:
                self._collapse_button = QToolButton()
                self._collapse_button.setText("▼" if not collapsed else "▶")
                self._collapse_button.setFixedSize(20, 20)
                _ = self._collapse_button.clicked.connect(self._toggle_collapsed)
                self._collapse_button.setStyleSheet(
                    """
                    QToolButton {
                        background: transparent;
                        border: none;
                        font-size: 10pt;
                    }
                    QToolButton:hover {
                        background: rgba(255, 255, 255, 0.1);
                        border-radius: 3px;
                    }
                """
                )
                header_layout.addWidget(self._collapse_button)

            self._main_layout.addWidget(self._header)

        # Content container (holds user-added widgets)
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(SPACING_SM)
        self._main_layout.addWidget(self._content)

        # Set initial visibility based on collapsed state
        self._content.setVisible(not collapsed)

        # Apply card styling
        self.setStyleSheet(
            f"""
            Card {{
                background-color: #2b2b2b;
                border-radius: 8px;
                border: 1px solid #3a3a3a;
                font-size: {FONT_SIZE_NORMAL}pt;
            }}
            Card:hover {{
                border-color: #4a4a4a;
            }}
        """
        )

    def add_widget(self, widget: QWidget) -> None:
        """
        Add a widget to the card's content area.

        Args:
            widget: Widget to add
        """
        self._content_layout.addWidget(widget)

    def _toggle_collapsed(self) -> None:
        """Toggle collapsed state."""
        self._collapsed = not self._collapsed
        self._content.setVisible(not self._collapsed)

        # Update button icon
        if self._collapse_button is not None:
            self._collapse_button.setText("▼" if not self._collapsed else "▶")

        self.collapsed_changed.emit(self._collapsed)

    def is_collapsed(self) -> bool:
        """Return whether card is collapsed."""
        return self._collapsed

    def set_collapsed(self, collapsed: bool) -> None:
        """
        Set collapsed state.

        Args:
            collapsed: True to collapse, False to expand
        """
        if self._collapsed != collapsed:
            self._toggle_collapsed()

    def content_layout(self) -> QVBoxLayout:
        """
        Get the content layout for adding widgets.

        Returns:
            Content layout
        """
        layout = self._content.layout()
        if not isinstance(layout, QVBoxLayout):
            raise TypeError("Content layout is not a QVBoxLayout")
        return layout

#!/usr/bin/env python
"""
Widget Factory for creating UI components with fallback support.

This module provides factory methods for creating UI widgets that gracefully
handle missing dependencies by falling back to standard Qt widgets.
"""

from PySide6.QtWidgets import QGroupBox, QVBoxLayout, QWidget


class WidgetGroupFactory:
    """Factory for creating widget groups with automatic fallback."""

    @staticmethod
    def create_group(title: str) -> tuple[QWidget, QVBoxLayout]:
        """
        Create a group widget with ModernCard if available, QGroupBox as fallback.

        Args:
            title: The title for the group

        Returns:
            Tuple of (group widget, layout)
        """
        try:
            from ui.modern_widgets import ModernCard

            group = ModernCard(title)
            layout = group.content_layout
        except ImportError:
            group = QGroupBox(title)
            layout = QVBoxLayout()
            # Only set layout if group doesn't have content_layout attribute
            # (ModernCard has content_layout pre-configured)
            if not hasattr(group, "content_layout"):
                group.setLayout(layout)

        return group, layout

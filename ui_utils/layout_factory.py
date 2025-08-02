#!/usr/bin/env python

"""
Layout Factory - Consolidates all layout creation and configuration patterns.

This module eliminates the duplicated layout creation logic found across
all component files, providing a centralized factory for creating consistently
configured layouts. It addresses 15+ instances of duplicate layout code.
"""

from typing import Literal, Optional, Tuple, List
from PySide6.QtWidgets import (
    QWidget, QLayout, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton
)
from PySide6.QtCore import Qt

from ui.ui_scaling import UIScaling


class LayoutFactory:
    """Centralized factory for creating consistently configured layouts.
    
    This class consolidates the layout creation patterns that were
    duplicated across all component files, providing a single source of
    truth for layout configuration and styling.
    """
    
    @staticmethod
    def create_basic_layout(
        parent: Optional[QWidget] = None,
        layout_type: Literal["vertical", "horizontal", "grid"] = "vertical",
        spacing: str = "s",
        margins: Optional[str] = None,
        zero_margins: bool = False
    ) -> QLayout:
        """Create a basic layout with standard configuration.
        
        Replaces 15+ instances of basic layout creation across components.
        
        Args:
            parent: Parent widget for the layout
            layout_type: Type of layout to create
            spacing: Spacing size key (xs, s, m, l)
            margins: Margin size key, None for default margins
            zero_margins: If True, sets margins to 0 (overrides margins param)
            
        Returns:
            Configured QLayout instance
        """
        # Create layout based on type
        if layout_type == "vertical":
            layout = QVBoxLayout(parent) if parent else QVBoxLayout()
        elif layout_type == "horizontal":
            layout = QHBoxLayout(parent) if parent else QHBoxLayout()
        else:  # grid
            layout = QGridLayout(parent) if parent else QGridLayout()
            
        # Set spacing
        layout.setSpacing(UIScaling.get_spacing(spacing))
        
        # Set margins
        if zero_margins:
            layout.setContentsMargins(0, 0, 0, 0)
        elif margins is not None:
            margin = UIScaling.get_spacing(margins)
            layout.setContentsMargins(margin, margin, margin, margin)
            
        return layout
    
    @staticmethod
    def create_button_group_layout(
        buttons: List[QPushButton],
        spacing: str = "s",
        add_stretch: bool = True,
        alignment: Optional[Qt.AlignmentFlag] = None
    ) -> Tuple[QWidget, QHBoxLayout]:
        """Create a horizontal button group with consistent spacing.
        
        Replaces 6+ instances of button group layouts.
        
        Args:
            buttons: List of buttons to add to the group
            spacing: Spacing size key
            add_stretch: Whether to add stretch at the end
            alignment: Optional alignment for the layout
            
        Returns:
            Tuple of (container widget, layout)
        """
        container = QWidget()
        layout = LayoutFactory.create_basic_layout(
            container, "horizontal", spacing, zero_margins=True
        )
        
        # Add buttons
        for button in buttons:
            layout.addWidget(button)
            
        # Add stretch if requested
        if add_stretch:
            layout.addStretch()
            
        # Set alignment if specified
        if alignment:
            layout.setAlignment(alignment)
            
        return container, layout
    
    @staticmethod
    def create_grid_with_labels(
        label_widget_pairs: List[Tuple[str, QWidget]],
        parent: Optional[QWidget] = None,
        spacing: str = "s",
        margins: Optional[str] = "s",
        label_alignment: Qt.AlignmentFlag = Qt.AlignRight | Qt.AlignVCenter
    ) -> QGridLayout:
        """Create a grid layout with label-widget pairs.
        
        Replaces 4+ instances of grid layouts with label-widget patterns.
        
        Args:
            label_widget_pairs: List of (label_text, widget) tuples
            parent: Parent widget
            spacing: Spacing size key
            margins: Margin size key
            label_alignment: Alignment for labels
            
        Returns:
            Configured QGridLayout with widgets added
        """
        layout = LayoutFactory.create_basic_layout(
            parent, "grid", spacing, margins
        )
        
        # Add label-widget pairs
        for row, (label_text, widget) in enumerate(label_widget_pairs):
            label = QLabel(label_text)
            label.setAlignment(label_alignment)
            layout.addWidget(label, row, 0)
            layout.addWidget(widget, row, 1)
            
        return layout
    
    @staticmethod
    def create_container_layout(
        parent: QWidget,
        layout_type: Literal["vertical", "horizontal"] = "vertical",
        spacing: str = "s",
        standard_margins: bool = True
    ) -> QLayout:
        """Create a container layout with standard margins and spacing.
        
        Replaces 8+ instances of container layout patterns.
        
        Args:
            parent: Parent widget (required for containers)
            layout_type: Type of layout
            spacing: Spacing size key
            standard_margins: Whether to use standard margins
            
        Returns:
            Configured layout
        """
        margins = "s" if standard_margins else None
        zero_margins = not standard_margins
        
        return LayoutFactory.create_basic_layout(
            parent, layout_type, spacing, margins, zero_margins
        )
    
    @staticmethod
    def add_widgets_to_layout(
        layout: QLayout,
        widgets: List[QWidget],
        stretch_after: Optional[int] = None,
        stretch_before: Optional[int] = None
    ) -> None:
        """Add multiple widgets to a layout with optional stretches.
        
        Args:
            layout: Target layout
            widgets: Widgets to add
            stretch_after: Add stretch after widget at this index
            stretch_before: Add stretch before widget at this index
        """
        for i, widget in enumerate(widgets):
            if stretch_before is not None and i == stretch_before:
                layout.addStretch()
            layout.addWidget(widget)
            if stretch_after is not None and i == stretch_after:
                layout.addStretch()
    
    @staticmethod
    def create_two_column_grid(
        widgets: List[QWidget],
        parent: Optional[QWidget] = None,
        spacing: str = "s",
        margins: Optional[str] = "s"
    ) -> QGridLayout:
        """Create a 2-column grid layout from a list of widgets.
        
        Args:
            widgets: Widgets to arrange in 2 columns
            parent: Parent widget
            spacing: Spacing size key
            margins: Margin size key
            
        Returns:
            Configured QGridLayout
        """
        layout = LayoutFactory.create_basic_layout(
            parent, "grid", spacing, margins
        )
        
        # Add widgets in 2-column arrangement
        for i, widget in enumerate(widgets):
            row = i // 2
            col = i % 2
            layout.addWidget(widget, row, col)
            
        return layout
    
    @staticmethod
    def apply_standard_spacing(
        layout: QLayout,
        spacing: str = "s",
        margins: Optional[str] = None,
        zero_margins: bool = False
    ) -> None:
        """Apply standard spacing and margins to an existing layout.
        
        Args:
            layout: Layout to configure
            spacing: Spacing size key
            margins: Margin size key
            zero_margins: If True, sets margins to 0
        """
        layout.setSpacing(UIScaling.get_spacing(spacing))
        
        if zero_margins:
            layout.setContentsMargins(0, 0, 0, 0)
        elif margins is not None:
            margin = UIScaling.get_spacing(margins)
            layout.setContentsMargins(margin, margin, margin, margin)
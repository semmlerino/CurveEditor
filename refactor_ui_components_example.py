#!/usr/bin/env python

"""
Example refactoring of ui_components.py to use LayoutFactory.

This file demonstrates how to refactor the duplicate layout patterns
found in ui_components.py to use the new LayoutFactory utility.
"""

from PySide6.QtWidgets import QGroupBox, QLineEdit, QPushButton, QWidget

from ui_utils import LayoutFactory

# Example 1: Zero-margin layout
# BEFORE (Lines 100-103 from ui_components.py):
# main_layout = QVBoxLayout(main_widget)
# main_layout.setContentsMargins(0, 0, 0, 0)
# main_layout.setSpacing(0)

# AFTER:
# Assuming main_widget is a QWidget instance
main_widget = QWidget()  # Example widget
main_layout = LayoutFactory.create_basic_layout(main_widget, "vertical", spacing="none", zero_margins=True)

# Example 2: Layout with spacing
# BEFORE (Lines 150-152):
# bottom_layout = QVBoxLayout(bottom_container)
# bottom_layout.setContentsMargins(0, 0, 0, 0)
# bottom_layout.setSpacing(UIScaling.get_spacing("xs"))

# AFTER:
bottom_container = QWidget()  # Example widget
bottom_layout = LayoutFactory.create_basic_layout(bottom_container, "vertical", spacing="xs", zero_margins=True)

# Example 3: Container with standard margins
# BEFORE (Lines 457-459 for container with standard margins):
# container_layout = QVBoxLayout(container)
# margin = UIScaling.get_spacing("s")
# container_layout.setContentsMargins(margin, margin, margin, margin)
# container_layout.setSpacing(UIScaling.get_spacing("s"))

# AFTER:
container = QWidget()  # Example widget
container_layout = LayoutFactory.create_container_layout(container, "vertical", spacing="s", standard_margins=True)

# Example 4: Button group
# BEFORE (Button group pattern from toolbar_components.py):
# button_layout = QHBoxLayout()
# button_layout.setSpacing(UIScaling.get_spacing("s"))
# button_layout.addWidget(button1)
# button_layout.addWidget(button2)
# button_layout.addStretch()

# AFTER:
button1 = QPushButton("Button 1")  # Example buttons
button2 = QPushButton("Button 2")
button_container, button_layout = LayoutFactory.create_button_group_layout(
    [button1, button2], spacing="s", add_stretch=True
)

# Example 5: Grid with label-widget pairs
# BEFORE (Grid with labels pattern):
# grid_layout = QGridLayout(group)
# grid_layout.addWidget(QLabel("Label1:"), 0, 0)
# grid_layout.addWidget(widget1, 0, 1)
# grid_layout.addWidget(QLabel("Label2:"), 1, 0)
# grid_layout.addWidget(widget2, 1, 1)

# AFTER:
group = QGroupBox("Settings")  # Example group box
widget1 = QLineEdit()  # Example widgets
widget2 = QLineEdit()
grid_layout = LayoutFactory.create_grid_with_labels(
    [("Label1:", widget1), ("Label2:", widget2)], parent=group, spacing="s", margins="s"
)

# Summary of refactoring patterns:
# 1. Replace manual QVBoxLayout/QHBoxLayout creation + setContentsMargins(0,0,0,0)
#    with LayoutFactory.create_basic_layout(..., zero_margins=True)
#
# 2. Replace container layout patterns with standard margins
#    with LayoutFactory.create_container_layout()
#
# 3. Replace button group patterns
#    with LayoutFactory.create_button_group_layout()
#
# 4. Replace grid layouts with label-widget pairs
#    with LayoutFactory.create_grid_with_labels()
#
# 5. For existing layouts needing standardization:
#    LayoutFactory.apply_standard_spacing(layout, spacing="s", zero_margins=True)

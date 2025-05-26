#!/usr/bin/env python
# -*- coding: utf-8 -*-

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QFont, QShortcut  # QShortcut is in QtGui, not QtWidgets
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QTreeWidget, QTreeWidgetItem, QPushButton,
                             QHeaderView)

class ShortcutManager:
    """Manages keyboard shortcuts for the application."""

    # Define all shortcuts here for easy reference and modification
    SHORTCUTS = {
        # File operations
        "open_file": {"key": "Ctrl+O", "description": "Open track file"},
        "save_file": {"key": "Ctrl+S", "description": "Save track file"},
        "export_csv": {"key": "Ctrl+E", "description": "Export to CSV"},

        # Edit operations
        "undo": {"key": "Ctrl+Z", "description": "Undo last action"},
        "redo": {"key": "Ctrl+Y", "description": "Redo last action"},
        "select_all": {"key": "Ctrl+A", "description": "Select all points"},
        "deselect_all": {"key": "Ctrl+Shift+A", "description": "Deselect all points"},
        "delete_selected": {"key": "Delete", "description": "Delete selected points"},

        # View operations
        "reset_view": {"key": "R", "description": "Reset view"},
        "toggle_grid": {"key": "G", "description": "Toggle grid"},
        "toggle_velocity": {"key": "V", "description": "Toggle velocity vectors"},
        "toggle_frame_numbers": {"key": "F", "description": "Toggle all frame numbers"},
        "toggle_crosshair": {"key": "X", "description": "Toggle crosshair"},
        "center_on_point": {"key": "C", "description": "Center on selected point"},
        "toggle_background": {"key": "B", "description": "Toggle background image"},
        "toggle_fullscreen": {"key": "F11", "description": "Toggle fullscreen mode"},
        "zoom_in": {"key": "+", "description": "Zoom in"},
        "zoom_out": {"key": "-", "description": "Zoom out"},

        # Frame Navigation
        "next_frame": {"key": "Right", "description": "Go to next frame"},
        "prev_frame": {"key": "Left", "description": "Go to previous frame"},
        "first_frame": {"key": "Home", "description": "Go to first frame"},
        "last_frame": {"key": "End", "description": "Go to last frame"},
        "frame_forward_10": {"key": "Shift+.", "description": "Forward 10 frames"},
        "frame_back_10": {"key": "Shift+,", "description": "Back 10 frames"},

        # Nudging
        "nudge_up": {"key": "Num+2", "description": "Nudge selected point(s) up"},
        "nudge_down": {"key": "Num+8", "description": "Nudge selected point(s) down"},
        "nudge_left": {"key": "Num+4", "description": "Nudge selected point(s) left"},
        "nudge_right": {"key": "Num+6", "description": "Nudge selected point(s) right"},

        # Curve View specific
        "toggle_y_flip": {"key": "Y", "description": "Toggle Y-flip"},
        "toggle_scale_to_image": {"key": "S", "description": "Toggle scale-to-image"},
        "toggle_debug_mode": {"key": "D", "description": "Toggle debug mode"},
        "clear_selection": {"key": "Escape", "description": "Clear current selection"},
        "play_pause": {"key": "Space", "description": "Play/pause timeline"},

        # Tools
        "smooth_selected": {"key": "Ctrl+Shift+S", "description": "Smooth selected points"},
        "filter_selected": {"key": "Ctrl+Shift+F", "description": "Filter selected points"},
        "detect_problems": {"key": "Ctrl+D", "description": "Detect tracking problems"}
    }

    @staticmethod
    def setup_shortcuts(window):
        """Set up all keyboard shortcuts for the main window.

        Args:
            window: The main window object to add shortcuts to
        """
        # Clear any existing shortcuts first
        window.shortcuts = {}

        # Create and connect each shortcut
        for shortcut_id, data in ShortcutManager.SHORTCUTS.items():
            key = data["key"]

            # Skip shortcuts without a key sequence
            if not key:
                continue

            # Create the shortcut
            shortcut = QShortcut(QKeySequence(key), window)
            # Ensure the shortcut works regardless of focused widget
            shortcut.setContext(Qt.ApplicationShortcut)
            window.shortcuts[shortcut_id] = shortcut

    @staticmethod
    def connect_shortcut(window, shortcut_id, slot_function):
        """Connect a shortcut to a slot function.

        Args:
            window: The main window containing shortcuts
            shortcut_id: ID of the shortcut to connect
            slot_function: Function to call when shortcut is triggered
        """
        if shortcut_id in window.shortcuts:
            window.shortcuts[shortcut_id].activated.connect(slot_function)

    @staticmethod
    def get_shortcut_key(shortcut_id):
        """Get the key sequence for a shortcut ID.

        Args:
            shortcut_id: ID of the shortcut

        Returns:
            Key sequence string or None if not found
        """
        if shortcut_id in ShortcutManager.SHORTCUTS:
            return ShortcutManager.SHORTCUTS[shortcut_id]["key"]
        return None

    @staticmethod
    def get_shortcut_description(shortcut_id):
        """Get the description for a shortcut ID.

        Args:
            shortcut_id: ID of the shortcut

        Returns:
            Description string or None if not found
        """
        if shortcut_id in ShortcutManager.SHORTCUTS:
            return ShortcutManager.SHORTCUTS[shortcut_id]["description"]
        return None


class ShortcutsDialog(QDialog):
    """Dialog for displaying keyboard shortcuts."""

    def __init__(self, parent=None):
        super(ShortcutsDialog, self).__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.resize(500, 500)

        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI."""
        layout = QVBoxLayout(self)

        # Add title label
        title_label = QLabel("Keyboard Shortcuts")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Create table for shortcuts
        self.shortcuts_table = QTableWidget()
        self.shortcuts_table.setColumnCount(2)
        self.shortcuts_table.setHorizontalHeaderLabels(["Shortcut", "Description"])
        self.shortcuts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.shortcuts_table.setAlternatingRowColors(True)

        # Fill table with shortcuts
        self.populate_shortcuts_table()

        layout.addWidget(self.shortcuts_table)

        # Add close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def populate_shortcuts_table(self):
        """Populate the shortcuts table with all defined shortcuts."""
        # Group shortcuts by category
        categories = {
            "File": ["open_file", "save_file", "export_csv"],
            "Edit": ["undo", "redo", "select_all", "deselect_all", "delete_selected", "clear_selection"],
            "View": ["reset_view", "toggle_grid", "toggle_velocity", "toggle_frame_numbers",
                     "toggle_crosshair", "center_on_point", "toggle_background", "toggle_fullscreen", "zoom_in", "zoom_out",
                     "toggle_y_flip", "toggle_scale_to_image", "toggle_debug_mode"], # Added Curve View specific toggles here
            "Frame Navigation": ["prev_frame", "next_frame", "first_frame", "last_frame",
                               "frame_back_10", "frame_forward_10", "play_pause"],
            "Nudging": ["nudge_up", "nudge_down", "nudge_left", "nudge_right"],
            "Tools": ["smooth_selected", "filter_selected", "detect_problems"]
        }

        # Count total rows needed
        total_rows = sum(len(ids) + 1 for ids in categories.values())  # +1 for each category header
        self.shortcuts_table.setRowCount(total_rows)

        # Populate table
        row = 0
        for category, shortcut_ids in categories.items():
            # Add category header
            category_item = QTableWidgetItem(category)
            category_item.setBackground(Qt.lightGray)
            category_item.setFont(QFont("Sans Serif", -1, QFont.Bold))
            self.shortcuts_table.setItem(row, 0, category_item)
            self.shortcuts_table.setItem(row, 1, QTableWidgetItem(""))
            self.shortcuts_table.setSpan(row, 0, 1, 2)
            row += 1

            # Add shortcuts in this category
            for shortcut_id in shortcut_ids:
                if shortcut_id in ShortcutManager.SHORTCUTS:
                    shortcut = ShortcutManager.SHORTCUTS[shortcut_id]
                    self.shortcuts_table.setItem(row, 0, QTableWidgetItem(shortcut["key"]))
                    self.shortcuts_table.setItem(row, 1, QTableWidgetItem(shortcut["description"]))
                    row += 1

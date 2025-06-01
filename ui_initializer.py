#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
UI Initialization for Curve Editor Main Window.

This module handles the initialization of UI components for the MainWindow,
helping to reduce the size of the MainWindow class.
"""

from typing import TYPE_CHECKING
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QPushButton, QStatusBar, QSlider, QLineEdit,
    QSpinBox
)
from PySide6.QtGui import QAction

from services.logging_service import LoggingService

if TYPE_CHECKING:
    from main_window import MainWindow

logger = LoggingService.get_logger("ui_initializer")


class UIInitializer:
    """Handles initialization of UI components for MainWindow."""

    @staticmethod
    def initialize_ui_elements(window: 'MainWindow'):
        """Initialize all UI elements for the main window.

        Args:
            window: The MainWindow instance
        """
        logger.info("Initializing UI elements")

        # Initialize basic UI elements
        window.image_label = QLabel()
        window.status_bar = QStatusBar()
        window.save_button = QPushButton()
        window.add_point_button = QPushButton()
        window.smooth_button = QPushButton()
        window.fill_gaps_button = QPushButton()
        window.filter_button = QPushButton()
        window.detect_problems_button = QPushButton()
        window.extrapolate_button = QPushButton()
        window.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        window.frame_edit = QLineEdit()
        window.go_button = QPushButton()
        window.info_label = QLabel()
        window.prev_image_button = QPushButton()
        window.next_image_button = QPushButton()
        window.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        window.undo_button = QPushButton()
        window.redo_button = QPushButton()
        window.toggle_bg_button = QPushButton()

        # Initialize dynamic UI components
        window.update_point_button = None
        window.type_edit = None

        # Initialize point size spin (referenced in signal connections)
        window.point_size_spin = QSpinBox()
        window.x_edit = QLineEdit()
        window.y_edit = QLineEdit()

    @staticmethod
    def initialize_undo_redo_actions(window: 'MainWindow'):
        """Initialize undo/redo actions.

        Args:
            window: The MainWindow instance
        """
        # Create undo/redo buttons if they don't exist yet
        # These are needed to satisfy the HistoryContainerProtocol
        if not hasattr(window, 'undo_button'):
            window.undo_button = window.findChild(QAction, "actionUndo")
            if not window.undo_button:
                window.undo_button = QAction("Undo", window)
                logger.debug("Created placeholder undo action")

        if not hasattr(window, 'redo_button'):
            window.redo_button = window.findChild(QAction, "actionRedo")
            if not window.redo_button:
                window.redo_button = QAction("Redo", window)
                logger.debug("Created placeholder redo action")

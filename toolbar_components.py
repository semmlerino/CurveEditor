#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Toolbar components for the Curve Editor.

This module contains all toolbar-related UI components including file operations,
view controls, curve operations, and history/analysis buttons.
"""

from typing import Any, Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QToolBar
)

from services.dialog_service import DialogService as DialogOperations
from services.history_service import HistoryService as HistoryOperations
from services.visualization_service import VisualizationService


class ToolbarComponents:
    """Static utility class for toolbar UI components."""

    @staticmethod
    def create_toolbar(main_window: Any) -> QWidget:
        """Create a more organized toolbar with action buttons grouped by function."""

        toolbar = QToolBar()
        toolbar.setObjectName("MainToolbar")

        # Create groups of related buttons
        # File operations group
        file_group = QWidget()
        file_layout = QVBoxLayout(file_group)
        file_layout.setContentsMargins(5, 2, 5, 2)
        file_layout.setSpacing(2)

        file_label = QLabel("File")
        file_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        file_font = QFont("Arial")  # type: ignore[arg-type]
        file_font.setPointSize(8)
        file_font.setWeight(QFont.Weight.Bold)
        file_label.setFont(file_font)
        file_layout.addWidget(file_label)  # type: ignore[arg-type]

        # Create grouped buttons
        file_buttons = QHBoxLayout()
        main_window.load_button = QPushButton("Load")
        main_window.load_button.setToolTip("Load Track Data")
        main_window.load_button.clicked.connect(lambda: DialogOperations.show_load_dialog(main_window))

        main_window.export_button = QPushButton("Export")
        main_window.export_button.setToolTip("Export Track Data")
        main_window.export_button.clicked.connect(lambda: DialogOperations.show_export_dialog(main_window))
        main_window.export_button.setEnabled(False)  # Initially disabled

        file_buttons.addWidget(main_window.load_button)
        file_buttons.addWidget(main_window.export_button)
        file_layout.addLayout(file_buttons)

        # View controls group
        view_group = QWidget()
        view_layout = QVBoxLayout(view_group)
        view_layout.setContentsMargins(5, 2, 5, 2)
        view_layout.setSpacing(2)

        view_label = QLabel("View")
        view_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        view_font = QFont("Arial")  # type: ignore[arg-type]
        view_font.setPointSize(8)
        view_font.setWeight(QFont.Weight.Bold)
        view_label.setFont(view_font)
        view_layout.addWidget(view_label)  # type: ignore[arg-type]

        view_buttons = QGridLayout()

        main_window.center_button = QPushButton("Center")
        main_window.center_button.setToolTip("Center View on Track Data")
        main_window.center_button.clicked.connect(lambda: VisualizationService.center_view(main_window))
        main_window.center_button.setEnabled(False)

        main_window.reset_zoom_button = QPushButton("Reset")
        main_window.reset_zoom_button.setToolTip("Reset View Zoom")
        main_window.reset_zoom_button.clicked.connect(lambda: VisualizationService.reset_zoom(main_window))
        main_window.reset_zoom_button.setEnabled(False)

        main_window.toggle_grid_view_button = QPushButton("Grid")
        main_window.toggle_grid_view_button.setCheckable(True)
        main_window.toggle_grid_view_button.setToolTip("Toggle Grid (G)")
        main_window.toggle_grid_view_button.clicked.connect(lambda: VisualizationService.toggle_grid(main_window))
        main_window.toggle_grid_view_button.setEnabled(False)

        main_window.toggle_background_button = QPushButton("BG")
        main_window.toggle_background_button.setCheckable(True)
        main_window.toggle_background_button.setToolTip("Toggle Background Image")
        main_window.toggle_background_button.setEnabled(False)  # Enable when image service ready

        view_buttons.addWidget(main_window.center_button, 0, 0)
        view_buttons.addWidget(main_window.reset_zoom_button, 0, 1)
        view_buttons.addWidget(main_window.toggle_grid_view_button, 1, 0)
        view_buttons.addWidget(main_window.toggle_background_button, 1, 1)

        view_layout.addLayout(view_buttons)

        # Curve operations group
        curve_group = QWidget()
        curve_layout = QVBoxLayout(curve_group)
        curve_layout.setContentsMargins(5, 2, 5, 2)
        curve_layout.setSpacing(2)

        curve_label = QLabel("Curve Operations")
        curve_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        curve_font = QFont("Arial")  # type: ignore[arg-type]
        curve_font.setPointSize(8)
        curve_font.setWeight(QFont.Weight.Bold)
        curve_label.setFont(curve_font)
        curve_layout.addWidget(curve_label)  # type: ignore[arg-type]

        curve_buttons = QGridLayout()

        main_window.smooth_button = QPushButton("Smooth")
        main_window.smooth_button.setToolTip("Smooth Selected Curve")
        main_window.smooth_button.clicked.connect(lambda: DialogOperations.show_smooth_dialog(main_window))
        main_window.smooth_button.setEnabled(False)

        main_window.fill_gaps_button = QPushButton("Fill Gaps")
        main_window.fill_gaps_button.setToolTip("Fill Gaps in Curve")
        main_window.fill_gaps_button.clicked.connect(lambda: DialogOperations.show_fill_gaps_dialog(main_window))
        main_window.fill_gaps_button.setEnabled(False)

        main_window.filter_button = QPushButton("Filter")
        main_window.filter_button.setToolTip("Apply Filter to Curve")
        main_window.filter_button.clicked.connect(lambda: DialogOperations.show_filter_dialog(main_window))
        main_window.filter_button.setEnabled(False)

        main_window.extrapolate_button = QPushButton("Extrapolate")
        main_window.extrapolate_button.setToolTip("Extrapolate Curve")
        main_window.extrapolate_button.clicked.connect(lambda: DialogOperations.show_extrapolate_dialog(main_window))
        main_window.extrapolate_button.setEnabled(False)

        curve_buttons.addWidget(main_window.smooth_button, 0, 0)
        curve_buttons.addWidget(main_window.fill_gaps_button, 0, 1)
        curve_buttons.addWidget(main_window.filter_button, 1, 0)
        curve_buttons.addWidget(main_window.extrapolate_button, 1, 1)

        curve_layout.addLayout(curve_buttons)

        # History and Analysis group
        history_group = QWidget()
        history_layout = QVBoxLayout(history_group)
        history_layout.setContentsMargins(5, 2, 5, 2)
        history_layout.setSpacing(2)

        history_label = QLabel("History & Analysis")
        history_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        history_font = QFont("Arial")  # type: ignore[arg-type]
        history_font.setPointSize(8)
        history_font.setWeight(QFont.Weight.Bold)
        history_label.setFont(history_font)
        history_layout.addWidget(history_label)  # type: ignore[arg-type]

        history_buttons = QHBoxLayout()

        main_window.undo_button = QPushButton("Undo")
        main_window.undo_button.setToolTip("Undo Last Action")
        main_window.undo_button.clicked.connect(lambda: HistoryOperations.undo_action(main_window))
        main_window.undo_button.setEnabled(False)

        main_window.redo_button = QPushButton("Redo")
        main_window.redo_button.setToolTip("Redo Last Action")
        main_window.redo_button.clicked.connect(lambda: HistoryOperations.redo_action(main_window))
        main_window.redo_button.setEnabled(False)

        main_window.detect_problems_button = QPushButton("Detect")
        main_window.detect_problems_button.setToolTip("Problem detection temporarily disabled during refactoring.")
        main_window.detect_problems_button.setEnabled(False)

        history_buttons.addWidget(main_window.undo_button)
        history_buttons.addWidget(main_window.redo_button)
        history_buttons.addWidget(main_window.detect_problems_button)
        history_layout.addLayout(history_buttons)

        # Create the main toolbar layout
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(5, 0, 5, 0)
        toolbar_layout.setSpacing(10)

        # Add all groups to toolbar with separators
        toolbar_layout.addWidget(file_group)
        toolbar_layout.addWidget(ToolbarComponents._create_vertical_line())
        toolbar_layout.addWidget(view_group)
        toolbar_layout.addWidget(ToolbarComponents._create_vertical_line())
        toolbar_layout.addWidget(curve_group)
        toolbar_layout.addWidget(ToolbarComponents._create_vertical_line())
        toolbar_layout.addWidget(history_group)
        toolbar_layout.addStretch()

        # Add info label
        main_window.info_label = QLabel("No data loaded")
        toolbar_layout.addWidget(main_window.info_label)

        # Create a container widget for the toolbar
        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar_layout)

        return toolbar_widget

    @staticmethod
    def _create_vertical_line() -> QFrame:
        """Create a vertical separator line."""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    @staticmethod
    def set_file_operations_enabled(main_window: Any, enabled: bool) -> None:
        """Enable or disable file operation buttons."""
        if hasattr(main_window, 'export_button'):
            main_window.export_button.setEnabled(enabled)

    @staticmethod
    def set_view_operations_enabled(main_window: Any, enabled: bool) -> None:
        """Enable or disable view operation buttons."""
        buttons = ['center_button', 'reset_zoom_button', 'toggle_grid_view_button']
        for button_name in buttons:
            if hasattr(main_window, button_name):
                getattr(main_window, button_name).setEnabled(enabled)

    @staticmethod
    def set_curve_operations_enabled(main_window: Any, enabled: bool) -> None:
        """Enable or disable curve operation buttons."""
        buttons = ['smooth_button', 'fill_gaps_button', 'filter_button', 'extrapolate_button']
        for button_name in buttons:
            if hasattr(main_window, button_name):
                getattr(main_window, button_name).setEnabled(enabled)

    @staticmethod
    def set_history_operations_enabled(main_window: Any, undo_enabled: bool, redo_enabled: bool) -> None:
        """Set the enabled state of history operation buttons."""
        if hasattr(main_window, 'undo_button'):
            main_window.undo_button.setEnabled(undo_enabled)
        if hasattr(main_window, 'redo_button'):
            main_window.redo_button.setEnabled(redo_enabled)

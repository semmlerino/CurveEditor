#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Point editing components for the Curve Editor.

This module contains UI components related to point editing, including
point information display and coordinate editing controls.
"""

from typing import Any

from PySide6.QtWidgets import (
    QGridLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget
)


class PointEditComponents:
    """Static utility class for point editing UI components."""

    @staticmethod
    def create_point_info_panel(main_window: Any) -> QWidget:
        """
        Create the point information and editing panel.

        This panel displays:
        - Current frame information
        - Point type information
        - Update point button

        Args:
            main_window: The main application window instance

        Returns:
            QWidget: The point info panel widget
        """
        # Left side: Point Info and Editing
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)

        # Point Info Group
        point_info_group = QGroupBox("Point Info")
        point_info_layout = QGridLayout(point_info_group)

        main_window.frame_info_label = QLabel("Frame: N/A")
        main_window.type_label = QLabel("Type:")
        main_window.type_edit = QLineEdit()
        main_window.type_edit.setReadOnly(True)
        main_window.update_point_button = QPushButton("Update Point")

        point_info_layout.addWidget(main_window.frame_info_label, 0, 0, 1, 2)
        point_info_layout.addWidget(main_window.type_label, 1, 0)
        point_info_layout.addWidget(main_window.type_edit, 1, 1)
        point_info_layout.addWidget(main_window.update_point_button, 2, 0, 1, 2)

        left_layout.addWidget(point_info_group)
        left_layout.addStretch()  # Push controls to the top

        return left_panel

    @staticmethod
    def update_point_info_display(main_window: Any, frame: int, point_type: str) -> None:
        """
        Update the point information display.

        Args:
            main_window: The main application window instance
            frame: Current frame number
            point_type: Type of the point
        """
        if hasattr(main_window, 'frame_info_label'):
            main_window.frame_info_label.setText(f"Frame: {frame}")

        if hasattr(main_window, 'type_edit'):
            main_window.type_edit.setText(point_type)

    @staticmethod
    def set_point_editing_enabled(main_window: Any, enabled: bool) -> None:
        """
        Enable or disable point editing controls.

        Args:
            main_window: The main application window instance
            enabled: Whether to enable or disable the controls
        """
        if hasattr(main_window, 'update_point_button'):
            main_window.update_point_button.setEnabled(enabled)

    @staticmethod
    def clear_point_info(main_window: Any) -> None:
        """
        Clear the point information display.

        Args:
            main_window: The main application window instance
        """
        if hasattr(main_window, 'frame_info_label'):
            main_window.frame_info_label.setText("Frame: N/A")

        if hasattr(main_window, 'type_edit'):
            main_window.type_edit.clear()

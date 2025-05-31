#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Edit Signal Connector for 3DE4 Curve Editor.

This module handles signal connections for editing operations including:
- Point editing controls
- Curve view signals
- Batch edit operations (when enabled)
"""

# Standard library imports
import logging
from typing import Any, Callable, TYPE_CHECKING

# Local imports
from services.curve_service import CurveService as CurveViewOperations

if TYPE_CHECKING:
    from main_window import MainWindow

# Configure logger
logger = logging.getLogger(__name__)


class EditSignalConnector:
    """Handles signal connections for editing operations."""

    @staticmethod
    def connect_signals(main_window: 'MainWindow', connect_signal_func: Callable[..., Any]) -> None:
        """Connect all edit-related signals.

        Args:
            main_window: The main application window
            connect_signal_func: Function to connect signals with tracking
        """
        EditSignalConnector._connect_curve_view_signals(main_window, connect_signal_func)
        EditSignalConnector._connect_point_editing_signals(main_window, connect_signal_func)
        EditSignalConnector._connect_batch_edit_signals(main_window, connect_signal_func)

    @staticmethod
    def _connect_curve_view_signals(main_window: 'MainWindow', connect_signal: Callable[[object, object, Callable[..., object], str], None]) -> None:
        """Connect signals from the curve view widget.

        Args:
            main_window: The main application window
            connect_signal: Function to connect signals
        """
        if not hasattr(main_window, 'curve_view'):
            logger.warning("No curve_view found, skipping curve view signals")
            return

        cv = main_window.curve_view

        # Define all curve view signals to connect
        def on_point_selected(idx: int) -> None:
            CurveViewOperations.on_point_selected(cv, main_window, idx)

        def on_point_moved(idx: int, x: float, y: float) -> None:
            CurveViewOperations.on_point_moved(cv, main_window, idx, x, y)

        connections: list[tuple[object, Callable[..., object], str]] = [
            (getattr(cv, 'point_selected', None), on_point_selected, "curve_view.point_selected"),
            (getattr(cv, 'point_moved', None), on_point_moved, "curve_view.point_moved"),
        ]

        # Connect each signal
        for signal, slot, name in connections:
            connect_signal(main_window, signal, slot, name)

    @staticmethod
    def _connect_point_editing_signals(main_window: 'MainWindow', connect_signal: Callable[[object, object, Callable[..., object], str], None]) -> None:
        """Connect signals for point editing controls.

        Args:
            main_window: The main application window
            connect_signal: Function to connect signals
        """
        # Point info update button
        if hasattr(main_window, 'update_point_button'):
            connect_signal(
                main_window,
                main_window.update_point_button.clicked,
                lambda: CurveViewOperations.update_point_from_edit(main_window),
                "update_point_button.clicked"
            )

        # Enhanced point size control
        if hasattr(main_window, 'point_size_spin'):
            connect_signal(
                main_window,
                main_window.point_size_spin.valueChanged,
                lambda value: CurveViewOperations.set_point_size(main_window.curve_view, main_window, float(value)),  # type: ignore[arg-type]
                "point_size_spin.valueChanged"
            )

        # Point coordinate entry fields
        if hasattr(main_window, 'x_edit') and hasattr(main_window, 'y_edit'):
            connect_signal(
                main_window,
                main_window.x_edit.returnPressed,
                lambda: CurveViewOperations.update_point_from_edit(main_window),
                "x_edit.returnPressed"
            )

            connect_signal(
                main_window,
                main_window.y_edit.returnPressed,
                lambda: CurveViewOperations.update_point_from_edit(main_window),
                "y_edit.returnPressed"
            )

    @staticmethod
    def _connect_batch_edit_signals(main_window: 'MainWindow', connect_signal: Callable[[object, object, Callable[..., object], str], None]) -> None:
        """Connect signals for batch editing operations.

        Args:
            main_window: The main application window
            connect_signal: Function to connect signals
        """
        # Batch edit buttons are typically connected in batch_edit.py
        # But we'll add some common ones here if they exist

        # NOTE: Batch edit UI initialization is commented out in main_window.py __init__
        # Commenting out these connections until batch_edit_ui is re-enabled.
        # if hasattr(main_window, 'scale_button'):
        #     connect_signal(
        #         main_window,
        #         main_window.scale_button.clicked,
        #         lambda: main_window.batch_edit_ui.batch_scale() if hasattr(main_window, 'batch_edit_ui') else None,
        #         "scale_button.clicked"
        #     )

        # if hasattr(main_window, 'offset_button'):
        #     connect_signal(
        #         main_window,
        #         main_window.offset_button.clicked,
        #         lambda: main_window.batch_edit_ui.batch_offset() if hasattr(main_window, 'batch_edit_ui') else None,
        #         "offset_button.clicked"
        #     )

        # if hasattr(main_window, 'rotate_button'):
        #     connect_signal(
        #         main_window,
        #         main_window.rotate_button.clicked,
        #         lambda: main_window.batch_edit_ui.batch_rotate() if hasattr(main_window, 'batch_edit_ui') else None,
        #         "rotate_button.clicked"
        #     )

        # if hasattr(main_window, 'smooth_batch_button'):
        #     connect_signal(
        #         main_window,
        #         main_window.smooth_batch_button.clicked,
        #         lambda: main_window.batch_edit_ui.batch_smooth() if hasattr(main_window, 'batch_edit_ui') else None,
        #         "smooth_batch_button.clicked"
        #     )

        # if hasattr(main_window, 'select_all_button'):
        #     connect_signal(
        #         main_window,
        #         main_window.select_all_button.clicked,
        #         lambda: CurveViewOperations.select_all_points(main_window.curve_view, main_window),
        #         "select_all_button.clicked"
        #     )
        pass  # Currently all batch edit signals are commented out

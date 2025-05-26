#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
View signal connector for CurveEditor.

This module handles all signal connections related to the curve view widget
including point selection, movement, and view manipulation.
"""

from typing import Any, Callable

from services.curve_service import CurveService as CurveViewOperations


class ViewSignalConnector:
    """Handles signal connections for curve view operations."""

    @staticmethod
    def connect_signals(main_window: Any, registry: Any) -> None:
        """Connect all curve view related signals.

        Args:
            main_window: The main application window
            registry: The signal registry for tracking connections
        """
        ViewSignalConnector._connect_curve_view_signals(main_window, registry)
        ViewSignalConnector._connect_point_editing_signals(main_window, registry)

    @staticmethod
    def _connect_curve_view_signals(main_window: Any, registry: Any) -> None:
        """Connect signals from the curve view widget.

        Args:
            main_window: The main application window
            registry: The signal registry for tracking connections
        """
        if not hasattr(main_window, 'curve_view'):
            print("  [WARN] No curve_view found, skipping curve view signals")
            return

        cv = main_window.curve_view

        # Define all curve view signals to connect
        connections: list[tuple[Any, Callable[[int], None] | Callable[[int, float, float], None], str]] = [
            (getattr(cv, 'point_selected', None),
             lambda idx: CurveViewOperations.on_point_selected(cv, main_window, int(idx)),
             "curve_view.point_selected"),

            (getattr(cv, 'point_moved', None),
             lambda idx, x, y: CurveViewOperations.on_point_moved(main_window, int(idx), float(x), float(y)),
             "curve_view.point_moved"),
        ]

        # Connect each signal
        for signal, slot, name in connections:
            registry._connect_signal(main_window, signal, slot, name)

    @staticmethod
    def _connect_point_editing_signals(main_window: Any, registry: Any) -> None:
        """Connect signals for point editing controls.

        Args:
            main_window: The main application window
            registry: The signal registry for tracking connections
        """
        # Point info update button
        if hasattr(main_window, 'update_point_button'):
            registry._connect_signal(
                main_window,
                main_window.update_point_button.clicked,
                lambda: CurveViewOperations.update_point_from_edit(main_window),
                "update_point_button.clicked"
            )

        # Enhanced point size control
        if hasattr(main_window, 'point_size_spin'):
            registry._connect_signal(
                main_window,
                main_window.point_size_spin.valueChanged,
                lambda value: CurveViewOperations.set_point_size(main_window.curve_view, main_window, float(value)),
                "point_size_spin.valueChanged"
            )

        # Point coordinate entry fields
        if hasattr(main_window, 'x_edit') and hasattr(main_window, 'y_edit'):
            registry._connect_signal(
                main_window,
                main_window.x_edit.returnPressed,
                lambda: CurveViewOperations.update_point_from_edit(main_window),
                "x_edit.returnPressed"
            )

            registry._connect_signal(
                main_window,
                main_window.y_edit.returnPressed,
                lambda: CurveViewOperations.update_point_from_edit(main_window),
                "y_edit.returnPressed"
            )

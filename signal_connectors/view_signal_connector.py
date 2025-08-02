#!/usr/bin/env python

"""
View signal connector for CurveEditor.

This module handles all signal connections related to the curve view widget
including point selection, movement, and view manipulation.
"""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from main_window import MainWindow
    from signal_registry import RegistryConnector

from services.curve_service import CurveService as CurveViewOperations
from services.logging_service import LoggingService

# Configure logger
logger = LoggingService.get_logger("view_signal_connector")


class ViewSignalConnector:
    """Handles signal connections for curve view operations."""

    @staticmethod
    def connect_signals(main_window: "MainWindow", registry: "RegistryConnector") -> None:
        """Connect all curve view related signals.

        Args:
            main_window: The main application window
            registry: The signal registry for tracking connections
        """
        ViewSignalConnector._connect_curve_view_signals(main_window, registry)
        ViewSignalConnector._connect_point_editing_signals(main_window, registry)

    @staticmethod
    def _connect_curve_view_signals(main_window: "MainWindow", registry: "RegistryConnector") -> None:
        """Connect signals from the curve view widget.

        Args:
            main_window: The main application window
            registry: The signal registry for tracking connections
        """
        if not hasattr(main_window, "curve_view"):
            logger.warning("No curve_view found, skipping curve view signals")
            return

        cv = main_window.curve_view

        # Define all curve view signals to connect
        def on_point_selected(idx: int) -> None:
            CurveViewOperations.on_point_selected(cv, main_window, idx)

        def on_point_moved(idx: int, x: float, y: float) -> None:
            CurveViewOperations.on_point_moved(main_window, idx, x, y)

        connections: list[tuple[Any, Callable[..., Any], str]] = [
            (getattr(cv, "point_selected", None), on_point_selected, "curve_view.point_selected"),
            (getattr(cv, "point_moved", None), on_point_moved, "curve_view.point_moved"),
        ]

        # Connect each signal
        for signal, slot, name in connections:
            registry._connect_signal(main_window, signal, slot, name)

    @staticmethod
    def _connect_point_editing_signals(main_window: "MainWindow", registry: "RegistryConnector") -> None:
        """Connect signals for point editing controls.

        Args:
            main_window: The main application window
            registry: The signal registry for tracking connections
        """
        # Point info update button
        if hasattr(main_window, "update_point_button"):
            registry._connect_signal(
                main_window,
                main_window.update_point_button.clicked,
                lambda: CurveViewOperations.update_point_from_edit(main_window),
                "update_point_button.clicked",
            )

        # Enhanced point size control
        if hasattr(main_window, "point_size_spin"):

            def on_point_size_changed(value: float) -> None:
                CurveViewOperations.set_point_size(main_window.curve_view, main_window, float(value))

            registry._connect_signal(
                main_window,
                main_window.point_size_spin.valueChanged,  # type: ignore[attr-defined]
                on_point_size_changed,
                "point_size_spin.valueChanged",
            )

        # Point coordinate entry fields
        if hasattr(main_window, "x_edit") and hasattr(main_window, "y_edit"):
            registry._connect_signal(
                main_window,
                main_window.x_edit.returnPressed,
                lambda: CurveViewOperations.update_point_from_edit(main_window),
                "x_edit.returnPressed",
            )  # type: ignore[attr-defined]

            registry._connect_signal(
                main_window,
                main_window.y_edit.returnPressed,
                lambda: CurveViewOperations.update_point_from_edit(main_window),
                "y_edit.returnPressed",
            )  # type: ignore[attr-defined]

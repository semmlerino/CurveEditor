#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Signal Registry for 3DE4 Curve Editor.

This module provides a centralized registry for managing signal connections
throughout the application. It delegates to modular signal connector classes
for better organization and maintainability.

Key improvements in this refactored version:
1. Delegates signal connections to specialized connector modules
2. Maintains centralized connection tracking
3. Provides consistent error handling across all connections
4. Simplified and more maintainable code structure
"""

# Standard library imports
import traceback
from typing import TYPE_CHECKING, Any, Callable

# Local imports
from signal_connectors import (
    EditSignalConnector,
    FileSignalConnector,
    ShortcutSignalConnector,
    UISignalConnector,
    ViewSignalConnector,
    VisualizationSignalConnector
)

if TYPE_CHECKING:
    from main_window import MainWindow


class SignalRegistry:
    """Centralized registry for managing signal connections.

    This class serves as the main entry point for connecting all signals
    in the application. It delegates to specialized connector modules for
    different functional areas.
    """

    @classmethod
    def connect_all_signals(cls, main_window: Any) -> None:
        """Connect all signals throughout the application.

        Args:
            main_window: The main application window instance

        This method serves as the single entry point for connecting all signals
        in the application. It tracks which signals have been connected to prevent
        duplicate connections and provides detailed error reporting.
        """
        # Initialize connection tracking for debugging
        if not hasattr(main_window, 'connected_signals'):
            main_window.connected_signals = set()  # type: ignore[attr-defined]

        # Print a header to make the connection process visible in logs
        print("\n" + "="*80)
        print("CONNECTING ALL APPLICATION SIGNALS")
        print("="*80)

        # Define all signal connection groups to process
        signal_groups = [
            # File operations
            ("File Operations", lambda mw: FileSignalConnector.connect_signals(mw, cls._connect_signal)),

            # Edit operations (curve view, point editing, batch edit)
            ("Edit Operations", lambda mw: EditSignalConnector.connect_signals(mw, cls._connect_signal)),

            # View operations (enhanced view and visualization)
            ("View Operations", lambda mw: ViewSignalConnector.connect_signals(mw, cls._connect_signal)),
            ("Visualization", lambda mw: VisualizationSignalConnector.connect_signals(mw, cls._connect_signal)),

            # UI operations (timeline, dialogs, history, image, analysis)
            ("UI Operations", lambda mw: UISignalConnector.connect_signals(mw, cls._connect_signal)),

            # Keyboard shortcuts (handled last after all UI elements are connected)
            ("Keyboard Shortcuts", lambda mw: ShortcutSignalConnector.connect_shortcuts(mw)),
        ]

        # Connect each group with proper error handling
        for group_name, connection_func in signal_groups:
            try:
                print(f"\nConnecting {group_name} signals...")
                connection_func(main_window)
                print(f"[OK] Successfully connected {group_name} signals")
            except Exception as e:
                print(f"[ERROR] Error connecting {group_name} signals: {str(e)}")
                traceback.print_exc()

        print("\n" + "="*80)
        print(f"Signal connection complete. {len(main_window.connected_signals if isinstance(main_window.connected_signals, set) else set())} total connections.")  # type: ignore[attr-defined]
        print("="*80 + "\n")

    @staticmethod
    def _connect_signal(
        main_window: Any,
        signal: Any,
        slot: Callable[..., Any],
        signal_name: str | None = None
    ) -> bool:
        """Connect a signal to a slot with tracking and error handling.

        Args:
            main_window: The main application window
            signal: The signal to connect
            slot: The slot function to connect to
            signal_name: Optional name for the signal for tracking

        Returns:
            bool: True if connection was successful, False otherwise
        """
        if signal is None:
            print(f"  [ERROR] Signal '{signal_name}' is None, cannot connect")
            return False

        if not hasattr(signal, 'connect'):
            print(f"  [ERROR] Object '{signal_name}' is not a signal (no connect method)")
            return False

        # Create a unique identifier for this connection
        connection_id = f"{signal_name or id(signal)}-{id(slot)}"

        # Check if this connection already exists
        if connection_id in main_window.connected_signals:
            print(f"  [WARN] Signal '{signal_name}' already connected to this slot, skipping")
            return True

        try:
            # Make the connection
            signal.connect(slot)

            # Add to tracking set
            main_window.connected_signals.add(connection_id)

            # Log success
            print(f"  [OK] Connected: {signal_name or 'signal'}")
            return True
        except Exception as e:
            print(f"  [ERROR] Error connecting {signal_name or 'signal'}: {str(e)}")
            return False

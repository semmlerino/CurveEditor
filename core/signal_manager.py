#!/usr/bin/env python
"""
Signal Manager for Qt memory leak prevention.

This module provides a context manager and utilities for properly managing
Qt signal connections to prevent memory leaks. It ensures all signals are
disconnected when widgets are destroyed.

Key features:
1. Automatic signal disconnection on widget destruction
2. Connection tracking for debugging
3. Context manager for scoped connections
4. Weak reference support to prevent circular references
"""

import logging
import weakref
from collections.abc import Callable
from contextlib import contextmanager
from typing import cast, final

from PySide6.QtCore import QObject, Signal, SignalInstance

logger = logging.getLogger("signal_manager")


@final
class SignalConnection:
    """Represents a single signal connection that can be cleanly disconnected."""

    def __init__(
        self,
        signal: Signal | SignalInstance,
        slot: Callable[..., None],
        signal_name: str | None = None,
    ):
        """Initialize a signal connection.

        Args:
            signal: The Qt signal
            slot: The slot function to connect to
            signal_name: Optional name for debugging
        """
        self.signal = signal
        self.slot = slot
        self.signal_name = signal_name or f"signal_{id(signal)}"
        self.connected = False

    def connect(self) -> bool:
        """Connect the signal to the slot.

        Returns:
            bool: True if successful, False otherwise
        """
        if self.connected:
            logger.debug(f"Signal {self.signal_name} already connected")
            return True

        try:
            # Cast to SignalInstance to access connect method
            signal_instance = cast(SignalInstance, self.signal)
            _ = signal_instance.connect(self.slot)
            self.connected = True
            logger.debug(f"Connected signal: {self.signal_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect {self.signal_name}: {e}")
            return False

    def disconnect(self) -> bool:
        """Disconnect the signal from the slot.

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.connected:
            return True

        try:
            # Cast to SignalInstance to access disconnect method
            signal_instance = cast(SignalInstance, self.signal)
            _ = signal_instance.disconnect(self.slot)
            self.connected = False
            logger.debug(f"Disconnected signal: {self.signal_name}")
            return True
        except Exception as e:
            logger.warning(f"Failed to disconnect {self.signal_name}: {e}")
            return False


class SignalManager:
    """Manages signal connections for a widget to prevent memory leaks.

    This class tracks all signal connections for a widget and ensures they
    are properly disconnected when the widget is destroyed.
    """

    def __init__(self, owner: QObject | None = None):
        """Initialize the signal manager.

        Args:
            owner: The widget that owns these connections (optional)
        """
        self.connections: list[SignalConnection] = []
        self.owner_ref: weakref.ReferenceType[QObject] | None = None

        if owner:
            # Use weak reference to avoid circular references
            self.owner_ref = weakref.ref(owner, self._owner_destroyed)

            # Try to hook into the owner's destruction
            if hasattr(owner, "destroyed"):
                _ = owner.destroyed.connect(self.disconnect_all)

    def _owner_destroyed(self, _: weakref.ReferenceType[QObject]) -> None:
        """Called when the owner widget is destroyed."""
        logger.debug(f"Owner destroyed, disconnecting {len(self.connections)} signals")
        self.disconnect_all()

    def connect(
        self,
        signal: Signal | SignalInstance,
        slot: Callable[..., None],
        signal_name: str | None = None,
    ) -> SignalConnection:
        """Connect a signal and track the connection.

        Args:
            signal: The Qt signal
            slot: The slot function to connect to
            signal_name: Optional name for debugging

        Returns:
            SignalConnection: The connection object
        """
        connection = SignalConnection(signal, slot, signal_name)
        if connection.connect():
            self.connections.append(connection)
        return connection

    def disconnect(self, connection: SignalConnection) -> bool:
        """Disconnect a specific signal connection.

        Args:
            connection: The connection to disconnect

        Returns:
            bool: True if successful, False otherwise
        """
        if connection in self.connections:
            if connection.disconnect():
                self.connections.remove(connection)
                return True
        return False

    def disconnect_all(self) -> None:
        """Disconnect all tracked signal connections."""
        disconnected = 0
        failed = 0

        # Copy list to avoid modification during iteration
        connections_copy = list(self.connections)

        for connection in connections_copy:
            if connection.disconnect():
                disconnected += 1
            else:
                failed += 1

        self.connections.clear()

        if disconnected > 0 or failed > 0:
            logger.info(f"Disconnected {disconnected} signals" + (f", {failed} failed" if failed > 0 else ""))

    def __del__(self) -> None:
        """Ensure all signals are disconnected when manager is destroyed."""
        if self.connections:
            logger.debug(f"SignalManager destructor: disconnecting {len(self.connections)} signals")
            self.disconnect_all()

    @contextmanager
    def temporary_connection(
        self,
        signal: Signal | SignalInstance,
        slot: Callable[..., None],
        signal_name: str | None = None,
    ):
        """Context manager for temporary signal connections.

        Usage:
            with signal_manager.temporary_connection(button.clicked, handler):
                # Signal is connected here
                do_something()
            # Signal is automatically disconnected here

        Args:
            signal: The Qt signal
            slot: The slot function to connect to
            signal_name: Optional name for debugging

        Yields:
            SignalConnection: The active connection
        """
        connection = self.connect(signal, slot, signal_name)
        try:
            yield connection
        finally:
            _ = self.disconnect(connection)


class ManagedWidget:
    """Mixin class that adds automatic signal management to Qt widgets.

    Usage:
        class MyWidget(QWidget, ManagedWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                ManagedWidget.__init__(self)

                # Use self.signal_manager for all connections
                self.signal_manager.connect(
                    button.clicked,
                    self.on_button_clicked,
                    "button_click"
                )
    """

    signal_manager: SignalManager

    def __init__(self):
        """Initialize the managed widget mixin."""
        self.signal_manager = SignalManager(self if isinstance(self, QObject) else None)

    def __del__(self) -> None:
        """Ensure signals are disconnected on destruction."""
        if hasattr(self, "signal_manager"):
            self.signal_manager.disconnect_all()

#!/usr/bin/env python
"""
Signal type definitions for Qt signals in protocols.

This module provides proper type annotations for Qt signals to replace
the use of Any in protocol definitions, improving type safety and
IDE support.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, TypeVar

# Use object instead of Any for better type safety
SignalSlot = Callable[..., object]
VoidSlot = Callable[[], object]

T = TypeVar("T")
P = TypeVar("P")


class SignalInstance(Protocol):
    """Protocol for Qt signal instances.

    This protocol represents the instance of a signal that can be connected
    to slots and emitted. It provides type safety for signal operations.
    """

    def connect(self, slot: SignalSlot) -> None:
        """Connect the signal to a slot."""
        ...

    def disconnect(self, slot: SignalSlot | None = None) -> None:
        """Disconnect the signal from a slot."""
        ...

    def emit(self, *args: object) -> None:
        """Emit the signal with arguments."""
        ...


class TypedSignal[P](Protocol):
    """Generic protocol for typed Qt signals.

    This protocol provides type-safe signal operations with specific parameter types.
    """

    def connect(self, slot: Callable[[P], object]) -> None:
        """Connect the signal to a slot with typed parameters."""
        ...

    def disconnect(self, slot: Callable[[P], object] | None = None) -> None:
        """Disconnect the signal from a slot."""
        ...

    def emit(self, arg: P) -> None:
        """Emit the signal with typed argument."""
        ...


# Type aliases for specific signal types with proper parameter types
ImageChangedSignal = TypedSignal[int]  # Signal[int] - emits image index
PointSelectedSignal = TypedSignal[int]  # Signal[int] - emits point index
SelectionChangedSignal = TypedSignal[list[int]]  # Signal[list[int]] - emits selected indices


# For multi-parameter signals, we need a more complex protocol
class PointMovedSignalProtocol(Protocol):
    """Protocol for point moved signal that emits frame, x, y coordinates."""

    def connect(self, slot: Callable[[int, float, float], object]) -> None:
        """Connect to a slot that accepts frame, x, y parameters."""
        ...

    def disconnect(self, slot: Callable[[int, float, float], object] | None = None) -> None:
        """Disconnect from a slot."""
        ...

    def emit(self, frame: int, x: float, y: float) -> None:
        """Emit the signal with frame, x, y coordinates."""
        ...


PointMovedSignal = PointMovedSignalProtocol  # Signal[int, float, float] - emits frame, x, y


# Additional signal types for common use cases
class VoidSignalProtocol(Protocol):
    """Protocol for signals that emit no parameters."""

    def connect(self, slot: VoidSlot) -> None:
        """Connect to a parameterless slot."""
        ...

    def disconnect(self, slot: VoidSlot | None = None) -> None:
        """Disconnect from a slot."""
        ...

    def emit(self) -> None:
        """Emit the signal with no parameters."""
        ...


VoidSignal = VoidSignalProtocol


class BaseSignalConnector:
    """Base class for signal connection operations.

    This class wraps the signal connection functionality to provide a consistent
    interface for signal connector modules. It acts as a bridge between the
    SignalRegistry and the specialized signal connector classes.

    The class takes a connection function at initialization and provides the
    _connect_signal method that is expected by all signal connector classes.
    """

    def __init__(self, connect_func: Callable[..., bool]) -> None:
        """Initialize the signal connector with a connection function.

        Args:
            connect_func: The function to use for connecting signals.
                         Should match the signature of SignalRegistry._connect_signal
        """
        self._connect_signal: Callable[..., bool] = connect_func


class SignalConnectorProtocol(Protocol):
    """Protocol defining the interface for signal connector objects.

    This protocol defines what methods signal connector classes expect
    from their registry parameter. It ensures type safety and provides
    clear documentation of the required interface.
    """

    def _connect_signal(
        self,
        main_window: object,  # MainWindow
        signal: object,  # Qt Signal
        slot: Callable[..., None],
        signal_name: str | None = None,
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
        ...


# For runtime usage (when not type checking)
if not TYPE_CHECKING:
    # At runtime, signals are created by Qt, so we just use the base protocol
    # The typed protocols provide compile-time type safety
    ImageChangedSignal = SignalInstance
    PointSelectedSignal = SignalInstance
    PointMovedSignal = SignalInstance
    SelectionChangedSignal = SignalInstance
    VoidSignal = SignalInstance

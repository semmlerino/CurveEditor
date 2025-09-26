#!/usr/bin/env python
"""
Signal type definitions for Qt signals in protocols.

This module provides proper type annotations for Qt signals to replace
the use of Any in protocol definitions, improving type safety and
IDE support.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Generic, Protocol, TypeVar

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


class TypedSignal(Protocol, Generic[P]):
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


# For runtime usage (when not type checking)
if not TYPE_CHECKING:
    # At runtime, signals are created by Qt, so we just use the base protocol
    # The typed protocols provide compile-time type safety
    ImageChangedSignal = SignalInstance
    PointSelectedSignal = SignalInstance
    PointMovedSignal = SignalInstance
    SelectionChangedSignal = SignalInstance
    VoidSignal = SignalInstance

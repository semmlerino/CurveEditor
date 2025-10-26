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

from protocols.data import PointMovedSignalProtocol, VoidSignalProtocol

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


# Use imported protocols from protocols.data
PointMovedSignal = PointMovedSignalProtocol  # Signal[int, float, float] - emits frame, x, y
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

"""
Event handling protocol definitions for the CurveEditor.

This module defines the protocol interfaces for event handling services,
ensuring clean boundaries and dependency inversion.
"""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Protocol

from PySide6.QtGui import QKeyEvent, QMouseEvent, QWheelEvent


class ActionType(Enum):
    """Types of actions that can result from events."""
    SELECT = auto()
    MULTI_SELECT = auto()
    DRAG = auto()
    PAN = auto()
    ZOOM = auto()
    CONTEXT_MENU = auto()
    DELETE = auto()
    NONE = auto()


@dataclass
class EventResult:
    """Result of event processing."""
    handled: bool
    action: ActionType
    data: dict[str, Any] | None = None

    @classmethod
    def not_handled(cls) -> "EventResult":
        """Create a result for unhandled events."""
        return cls(handled=False, action=ActionType.NONE)

    @classmethod
    def handled_with(cls, action: ActionType, **data: Any) -> "EventResult":
        """Create a result for handled events with data."""
        return cls(handled=True, action=action, data=data)


class EventHandlerProtocol(Protocol):
    """Protocol for event handling services."""

    def handle_mouse_press(self, view: Any, event: QMouseEvent) -> EventResult:
        """Handle mouse press events."""
        ...

    def handle_mouse_move(self, view: Any, event: QMouseEvent) -> EventResult:
        """Handle mouse move events."""
        ...

    def handle_mouse_release(self, view: Any, event: QMouseEvent) -> EventResult:
        """Handle mouse release events."""
        ...

    def handle_wheel_event(self, view: Any, event: QWheelEvent) -> EventResult:
        """Handle mouse wheel events."""
        ...

    def handle_key_event(self, view: Any, event: QKeyEvent) -> EventResult:
        """Handle keyboard events."""
        ...

    def handle_context_menu(self, view: Any, event: QMouseEvent) -> EventResult:
        """Handle context menu requests."""
        ...

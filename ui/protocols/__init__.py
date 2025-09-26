"""Protocol definitions for UI components."""

from .controller_protocols import (
    ActionHandlerProtocol,
    BackgroundImageProtocol,
    MultiPointTrackingProtocol,
    PointEditorProtocol,
    SignalConnectionProtocol,
    TimelineControllerProtocol,
    UIInitializationProtocol,
    ViewOptionsProtocol,
)

__all__ = [
    "ActionHandlerProtocol",
    "ViewOptionsProtocol",
    "TimelineControllerProtocol",
    "BackgroundImageProtocol",
    "MultiPointTrackingProtocol",
    "PointEditorProtocol",
    "SignalConnectionProtocol",
    "UIInitializationProtocol",
]

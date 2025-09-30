"""Protocol definitions for UI components."""

from .controller_protocols import (
    ActionHandlerProtocol,
    BackgroundImageProtocol,
    MultiPointTrackingProtocol,
    PointEditorProtocol,
    SignalConnectionProtocol,
    TimelineControllerProtocol,
    UIInitializationProtocol,
    ViewManagementProtocol,
    ViewOptionsProtocol,
)

__all__ = [
    "ActionHandlerProtocol",
    "ViewOptionsProtocol",
    "ViewManagementProtocol",
    "TimelineControllerProtocol",
    "BackgroundImageProtocol",
    "MultiPointTrackingProtocol",
    "PointEditorProtocol",
    "SignalConnectionProtocol",
    "UIInitializationProtocol",
]

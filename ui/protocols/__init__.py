"""Protocol definitions for UI components."""

from .controller_protocols import (
    ActionHandlerProtocol,
    BackgroundImageProtocol,
    FrameNavigationProtocol,
    MultiPointTrackingProtocol,
    PlaybackControllerProtocol,
    PointEditorProtocol,
    SignalConnectionProtocol,
    TimelineControllerProtocol,
    UIInitializationProtocol,
    ViewOptionsProtocol,
)

__all__ = [
    "PlaybackControllerProtocol",
    "FrameNavigationProtocol",
    "ActionHandlerProtocol",
    "ViewOptionsProtocol",
    "TimelineControllerProtocol",
    "BackgroundImageProtocol",
    "MultiPointTrackingProtocol",
    "PointEditorProtocol",
    "SignalConnectionProtocol",
    "UIInitializationProtocol",
]

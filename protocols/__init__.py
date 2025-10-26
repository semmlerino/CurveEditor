"""
Centralized protocol definitions for CurveEditor.

This package consolidates all Protocol definitions that were previously
scattered across 31 files into three organized modules:

- ui: UI component protocols (MainWindowProtocol, CurveViewProtocol, etc.)
- services: Service layer protocols (TransformServiceProtocol, DataServiceProtocol, etc.)
- data: Data model protocols (PointProtocol, CurveDataProtocol, etc.)

This consolidation reduces duplication and improves maintainability.
"""

from protocols.data import (
    BatchEditableProtocol,
    CurveDataList,
    CurveDataProtocol,
    HistoryCommandProtocol,
    HistoryContainerProtocol,
    HistoryState,
    ImageProtocol,
    Point4,
    PointMovedSignalProtocol,
    PointProtocol,
    QtPointF,
    VoidSignalProtocol,
)
from protocols.services import (
    DataServiceProtocol,
    FileLoadWorkerProtocol,
    InteractionServiceProtocol,
    LoggingServiceProtocol,
    ServiceProtocol,
    ServicesProtocol,
    SessionManagerProtocol,
    SignalProtocol,
    StatusServiceProtocol,
    TransformServiceProtocol,
    UIServiceProtocol,
)
from protocols.ui import (
    CommandManagerProtocol,
    CurveViewProtocol,
    CurveWidgetProtocol,
    EventProtocol,
    FrameNavigationProtocol,
    MainWindowProtocol,
    ShortcutManagerProtocol,
    StateManagerProtocol,
    WidgetProtocol,
)

__all__ = [
    "BatchEditableProtocol",
    "CommandManagerProtocol",
    "CurveDataList",
    "CurveDataProtocol",
    "CurveViewProtocol",
    "CurveWidgetProtocol",
    "DataServiceProtocol",
    "EventProtocol",
    "FileLoadWorkerProtocol",
    "FrameNavigationProtocol",
    "HistoryCommandProtocol",
    "HistoryContainerProtocol",
    "HistoryState",
    "ImageProtocol",
    "InteractionServiceProtocol",
    "LoggingServiceProtocol",
    "MainWindowProtocol",
    "Point4",
    "PointMovedSignalProtocol",
    "PointProtocol",
    "QtPointF",
    "ServiceProtocol",
    "ServicesProtocol",
    "SessionManagerProtocol",
    "ShortcutManagerProtocol",
    "SignalProtocol",
    "StateManagerProtocol",
    "StatusServiceProtocol",
    "TransformServiceProtocol",
    "UIServiceProtocol",
    "VoidSignalProtocol",
    "WidgetProtocol",
]

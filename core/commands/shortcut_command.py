#!/usr/bin/env python
"""
Shortcut Command base class for keyboard shortcuts.

This module provides the foundation for keyboard shortcut commands that can be
executed globally regardless of widget focus.
"""
# pyright: reportImportCycles=false

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QWidget

if TYPE_CHECKING:
    from ui.curve_view_widget import CurveViewWidget
    from ui.main_window import MainWindow

from core.logger_utils import get_logger

logger = get_logger("shortcut_commands")


@dataclass
class ShortcutContext:
    """Context information for shortcut execution.

    Provides all necessary information about the application state
    when a shortcut is triggered, allowing commands to make intelligent
    decisions about execution.
    """

    main_window: MainWindow
    """Reference to the main application window."""

    focused_widget: QWidget | None
    """The widget that currently has keyboard focus."""

    key_event: QKeyEvent
    """The keyboard event that triggered this shortcut."""

    selected_curve_points: set[int]
    """Indices of currently selected curve points."""

    selected_tracking_points: list[str]
    """Names of currently selected tracking points."""

    current_frame: int | None
    """The current frame number, if available."""

    @property
    def has_curve_selection(self) -> bool:
        """Check if any curve points are selected."""
        return bool(self.selected_curve_points)

    @property
    def has_tracking_selection(self) -> bool:
        """Check if any tracking points are selected."""
        return bool(self.selected_tracking_points)

    @property
    def widget_type(self) -> str:
        """Get the type name of the focused widget."""
        if self.focused_widget:
            return type(self.focused_widget).__name__
        return "None"


class ShortcutCommand(ABC):
    """Abstract base class for keyboard shortcut commands.

    Each shortcut command encapsulates the logic for a specific keyboard
    shortcut, including context checking and execution.
    """

    def __init__(self, key_sequence: str, description: str) -> None:
        """Initialize the shortcut command.

        Args:
            key_sequence: The key sequence that triggers this command (e.g., "E", "Shift+1")
            description: Human-readable description of what this shortcut does
        """
        self.key_sequence: str = key_sequence
        self._description: str = description

    def _get_curve_widget(self, context: ShortcutContext) -> CurveViewWidget | None:
        """Get curve widget with validation.

        Args:
            context: Shortcut context containing main window

        Returns:
            CurveViewWidget if available, None otherwise

        Logs warning if widget not available.
        """
        widget = context.main_window.curve_widget
        if not widget:
            logger.warning(f"{self.__class__.__name__}: No curve widget available")
        return widget

    @abstractmethod
    def can_execute(self, context: ShortcutContext) -> bool:
        """Check if this command can execute in the current context.

        Args:
            context: The current application context

        Returns:
            True if the command can execute, False otherwise
        """
        pass

    @abstractmethod
    def execute(self, context: ShortcutContext) -> bool:
        """Execute the shortcut action.

        Args:
            context: The current application context

        Returns:
            True if the command was executed successfully, False otherwise
        """
        pass

    @property
    def description(self) -> str:
        """Get the human-readable description of this shortcut."""
        return self._description

    def log_execution(self, context: ShortcutContext, success: bool) -> None:
        """Log the execution of this command.

        Args:
            context: The context in which the command was executed
            success: Whether the execution was successful
        """
        status = "succeeded" if success else "failed"
        logger.info(
            f"Shortcut [{self.key_sequence}] {status}: {self.description} "
            f"(widget: {context.widget_type}, "
            f"curve_selection: {len(context.selected_curve_points)}, "
            f"tracking_selection: {len(context.selected_tracking_points)})"
        )

#!/usr/bin/env python
"""
Commands package for undo/redo functionality.

This package provides a command pattern implementation for all undoable
operations in the CurveEditor application.
"""

# Import cycles are resolved through lazy imports in consuming modules
from core.commands.base_command import Command, CompositeCommand, NullCommand  # pyright: ignore[reportImportCycles]
from core.commands.command_manager import CommandManager
from core.commands.curve_commands import (
    AddPointCommand,
    BatchMoveCommand,
    DeletePointsCommand,
    MovePointCommand,
    SetCurveDataCommand,
    SetPointStatusCommand,
    SmoothCommand,
)

__all__ = [
    # Base classes
    "Command",
    "CompositeCommand",
    "NullCommand",
    # Manager
    "CommandManager",
    # Curve commands
    "SetCurveDataCommand",
    "SmoothCommand",
    "MovePointCommand",
    "BatchMoveCommand",
    "DeletePointsCommand",
    "SetPointStatusCommand",
    "AddPointCommand",
]

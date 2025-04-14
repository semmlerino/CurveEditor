[2025-04-12 00:00:58] - Centralized all CurveView hotkey logic through ShortcutManager. CurveView now registers its shortcuts via ShortcutManager, and direct key handling for R, Y, S, D has been removed from keyPressEvent.
# Active Context

This file tracks the project's current status, including recent changes, current goals, and open questions.
2025-04-11 14:33:44 - Log of updates made.

*

## Current Focus

* Refactoring and modularization of the codebase for maintainability and clarity.
* Integration of enhanced visualization and editing tools for 2D tracking curves.
* Improving user workflow with session persistence and configuration management.

## Recent Changes

* Migrated from PyQt5 to PySide6 for better compatibility and access to new Qt features.
* Refactored main window and curve view logic to delegate functionality to utility classes.
* Enhanced the curve view with grid, velocity vectors, and frame number visualization.
* Centralized signal-slot architecture for UI event handling.
* Improved batch editing, smoothing, filtering, and gap filling tools.
* [2025-04-11 15:55:55] - Rectangle selection now uses Alt+Drag instead of Shift+Drag for multi-point selection.
* [2025-04-14 14:41:00] - Reassigned hotkeys: Frame navigation (Left/Right), Nudging (Numpad 4/6/8/2).

## Open Questions/Issues

* Are there additional file formats or tracking data types to support?
* What further enhancements are needed for track quality analysis?
* Are there any performance bottlenecks with large image sequences or track files?
* What are the next priorities for UI/UX improvements?
2025-04-11 14:44:49 - UMB: Comprehensive Memory Bank update performed, synchronizing documentation and architectural context.
# System Patterns *Optional*

This file documents recurring patterns and standards used in the project.
It is optional, but recommended to be updated as the project evolves.
2025-04-11 14:40:20 - Log of updates made.

*

## Coding Patterns

* Utility-class-based architecture for modularity and maintainability.
* Centralized signal-slot system for event handling.
* Defensive programming in UI component setup and signal connections.
* Use of static methods for operations that do not require instance state.

## Architectural Patterns

* Separation of concerns between UI, data, and operations.
* Facade pattern in EnhancedCurveView to delegate to utility classes.
* Dynamic import pattern for on-demand loading of utility classes.
* Centralized configuration and session persistence using JSON.

## Testing Patterns

* Manual and automated testing of curve editing, visualization, and file operations.
* Use of dialog-based parameter collection for user-driven testing.
* History stack for undo/redo as a means of state validation.
2025-04-11 14:44:49 - UMB: Memory Bank synchronized. Noted explicit use of PySide6 and explicit Qt module imports as a coding/architectural pattern.
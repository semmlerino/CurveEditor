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
* [2025-04-23 11:02:28] - **Import Standardization Pattern**: All imports of curve operations should use `from services.curve_service import CurveService as CurveViewOperations`. This maintains backward compatibility with code that expects `CurveViewOperations` while using the new service-based architecture.
* History stack for undo/redo as a means of state validation.
* [2025-04-23 14:35:00] - **Unit Testing Pattern**: Introduced `pytest` for unit testing. Initial tests created for `CurveService.transform_point` in `tests/test_curve_service.py`.
* [2025-04-23 14:58:37] - **Test Coverage Requirement**: Every fix or new feature addition must be accompanied by corresponding unit tests, unless adequate tests already exist.
2025-04-11 14:44:49 - UMB: Memory Bank synchronized. Noted explicit use of PySide6 and explicit Qt module imports as a coding/architectural pattern.
# Decision Log

This file records architectural and implementation decisions using a list format.
2025-04-11 14:40:20 - Log of updates made.

*

## Decision

* Transitioned from PyQt5 to PySide6 for improved compatibility with Python 3.12 and access to new Qt features.
* Refactored the codebase to use modular utility classes for maintainability and separation of concerns.
* Centralized signal-slot architecture for UI event handling.
* Enhanced curve view with advanced visualization options (grid, velocity vectors, frame numbers).
* Implemented batch editing, smoothing, filtering, and gap filling tools.

## Rationale 

* PySide6 offers better long-term support and access to modern Qt features.
* Modular utility classes reduce code duplication and improve maintainability.
* Centralized event handling simplifies debugging and future enhancements.
* Advanced visualization and editing tools improve user workflow and tracking accuracy.

## Implementation Details

* Updated all UI components and event connections to use PySide6.
* Delegated functionality from main window and curve view to specialized utility classes.
* Integrated enhanced curve view features and batch editing tools.
* Updated configuration and session persistence to use JSON.
* Improved documentation and code comments for maintainability.
[2025-04-11 14:54:32] - Added left/right arrow key navigation for previous/next frame in EnhancedCurveView. Rationale: Improves usability and efficiency for users navigating frame sequences. Impact: Users can now quickly move between frames using keyboard shortcuts, streamlining the workflow.
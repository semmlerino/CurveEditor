[2025-04-11 15:48:18] - Removed 'Delete' shortcut entirely from 'Delete Selected' QAction in menu_bar.py. Rationale: Changing shortcut context did not resolve the ambiguity warning. Removing the shortcut from the menu action prevents conflict with keyPressEvent handlers that also use Qt.Key_Delete. Impact: The 'Ambiguous shortcut overload: Del' warning should be resolved. Delete functionality remains via key press in relevant views and via menu click.
[2025-04-11 15:55:55] - Changed rectangle selection modifier from Shift to Alt. Rationale: Aligns with user request and avoids conflict with other multi-select behaviors. Impact: Users now use Alt+Drag to select multiple points with a rectangle.


[2025-04-11 15:45:25] - Changed shortcut context for 'Delete Selected' QAction in menu_bar.py to Qt.ApplicationShortcut. Rationale: Attempt to resolve 'Ambiguous shortcut overload: Del' warning by differentiating its context from potential conflicts (e.g., keyPressEvent handlers). Impact: Should eliminate the Qt warning related to the 'Del' shortcut.


[2025-04-11 15:41:53] - Resolved circular import between main_window.py and menu_bar.py. Removed direct import of MainWindow in menu_bar.py and used `typing.TYPE_CHECKING` block for type hint resolution. Rationale: Fixes runtime ImportError while satisfying static type checkers. Impact: Application should now start without the circular import error.


[2025-04-11 15:19:18] - Unified left/right arrow navigation: CurveViewOperations no longer intercepts left/right arrow key events, allowing MainWindow to handle global navigation without Shift. This resolves the longstanding modifier-key navigation issue.

[2025-04-11 15:19:18] - Unified left/right arrow navigation: CurveViewOperations no longer intercepts left/right arrow key events, allowing MainWindow to handle global navigation without Shift. This resolves the longstanding modifier-key navigation issue.
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
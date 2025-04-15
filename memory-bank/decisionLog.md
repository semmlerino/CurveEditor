[2025-04-15 16:29:30] - Added 'Auto-Center on Frame Change' feature.
    Decision: Implement a toggle in the View menu to enable/disable automatic centering of the view on the selected point when the frame changes.
    Rationale: Improve user workflow by keeping the focus point centered during frame-by-frame navigation.
    Implementation Details: Added boolean setting 'view/autoCenterOnFrameChange' to QSettings (settings_operations.py). Added checkable QAction to View menu (menu_bar.py) connected to handler in MainWindow (main_window.py). Added logic to frame change methods (next_frame, prev_frame, go_to_frame, etc. in ui_components.py) to check the setting and call ZoomOperations.center_on_selected_point if enabled.


[2025-04-14 15:08:22] - Removed special multi-point selection handling in ZoomOperations.zoom_view to ensure consistent incremental mouse wheel zoom behavior regardless of selection count. Rationale: Fixes bug reported by user where multi-point zoom was overly aggressive; aligns behavior with user expectation of consistent zoom step.

[2025-04-14 14:41:00] - Reassigned hotkeys: Frame navigation to Left/Right arrows, Point nudging to Numpad 4/6/8/2. Removed previous frame nav keys (,/.) and arrow keys for nudge. Rationale: User request for more intuitive frame navigation, retaining nudge functionality on Numpad.
[2025-04-12 00:00:39] - Centralized all CurveView hotkey logic (R, Y, S, D) through ShortcutManager for maintainability and user-friendliness. Direct key handling for these actions was removed from keyPressEvent. Only navigation keys remain handled directly.
[2025-04-11 23:17:20] - Decided to consolidate all user-facing view-centering and zooming logic (including all offset calculations and UI triggers) into a single unified file (zoom_operations.py), updating all buttons, wrappers, and removing duplication across the codebase. Grid-specific and geometric centering (e.g., batch editing) will remain in their respective modules.
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
[2025-04-12 00:23:17] - Consolidated all centering and zooming logic to ZoomOperations in centering_zoom_operations.py. Removed redundant wrappers and updated all UI, widget, and signal/shortcut wiring to use the canonical implementation. This reduces duplication and centralizes view logic.
[2025-04-11 14:54:32] - Added left/right arrow key navigation for previous/next frame in EnhancedCurveView. Rationale: Improves usability and efficiency for users navigating frame sequences. Impact: Users can now quickly move between frames using keyboard shortcuts, streamlining the workflow.
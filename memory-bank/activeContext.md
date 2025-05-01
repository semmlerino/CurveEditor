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
* [2025-04-23 14:08:00] - Fixed bug where background image did not pan with the curve in EnhancedCurveView.
* [2025-04-23 14:09:06] - Fixed TypeError in CurveService.on_point_selected by correcting signal connection in signal_registry.py.

* [2025-04-23 14:18:05] - Fixed ImportError in track_quality.py by capitalizing Dict and Tuple in typing import.
* [2025-04-23 14:26:20] - Fixed TypeError (metaclass conflict) in main_window.py by removing MainWindowProtocol inheritance. Application now runs successfully.

* [2025-04-23 14:28:56] - Fixed bug where curve did not pan correctly with manual offsets when `scale_to_image` was disabled or no background image was present. Modified `CurveService.transform_point`.
* [2025-04-23 14:30:26] - Initialized unit testing framework (pytest) and added initial tests for `CurveService.transform_point`.

* [2025-04-23 14:38:00] - Investigated 'C' hotkey issue. Found that the toggle functionality for auto-centering was already correctly implemented in `signal_registry.py` for the 'center_on_point' shortcut. Removed redundant `toggle_auto_center` method previously added to `main_window.py`.
* [2025-04-23 14:57:00] - Fixed pytest fixture errors in `tests/test_main_window.py` by refactoring `main_window_fixture` to use `with patch(...)` context manager for `ZoomOperations` mock. Tests now pass.
* [2025-04-23 15:23:35] - Fixed TypeError in `services/input_service.py` by removing extra argument from `add_to_history` call.
* [2025-04-23 15:30:00] - Implemented real-time rectangle selection: Moved selection logic from `handle_mouse_release` to `handle_mouse_move` in `services/input_service.py` for dynamic updates during drag.
* [2025-04-23 15:38:14] - Added unit tests (`tests/test_input_service.py`) covering real-time rectangle selection in `handle_mouse_move` and finalization in `handle_mouse_release`.

* [2025-04-23 16:17:00] - Fixed smoothing displacement: Added "Selected Points" option to SmoothingDialog and updated dialog_operations.py to use selected indices from CurveView.




## Open Questions/Issues
* [2025-04-23 14:38:00] - Added unit tests for `main_window.set_centering_enabled` in `tests/test_main_window.py` to verify state changes and menu action updates.


* [2025-04-23 11:02:05] - Refactoring imports to standardize on `from services.curve_service import CurveService as CurveViewOperations`. Updated `main_window.py`, `enhanced_curve_view.py`, `curve_view_plumbing.py`, `batch_edit.py`, and `services/input_service.py`. Confirmed that `signal_registry.py`, `ui_components.py`, and `menu_bar.py` already had the correct imports.
* Are there additional file formats or tracking data types to support?
* What further enhancements are needed for track quality analysis?
* Are there any performance bottlenecks with large image sequences or track files?
* What are the next priorities for UI/UX improvements?
* [2025-04-23 14:09:06] - Pylance detected numerous potential type/attribute errors in signal_registry.py after applying the fix for CurveService.on_point_selected. These need investigation.
2025-04-11 14:44:49 - UMB: Comprehensive Memory Bank update performed, synchronizing documentation and architectural context.
* [2025-04-23 14:18:05] - Pylance is reporting numerous errors related to unresolved PySide6 imports and unknown types/attributes across multiple files after fixing the track_quality.py import. This suggests a potential environment or Pylance configuration issue.

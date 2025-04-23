[2025-04-23 14:58:43] - Updated systemPatterns.md with new unit testing requirement: All fixes/features must have corresponding unit tests.
# Progress

This file tracks the project's progress using a task list format.
2025-04-11 14:40:20 - Log of updates made.

*

## Completed Tasks

* Migrated from PyQt5 to PySide6 for improved compatibility and features.
* Refactored codebase to use modular utility classes for maintainability.
* Implemented enhanced curve view with advanced visualization options.
* Centralized signal-slot architecture for UI event handling.
* Added batch editing, smoothing, filtering, and gap filling tools.
2025-04-11 14:44:49 - UMB: Memory Bank update completed, documentation and codebase context synchronized.
* [2025-04-14 14:41:00] - Completed hotkey reassignment: Frame nav (Arrows), Nudge (Numpad).
* [2025-04-14 15:08:39] - Fixed multi-point mouse wheel zoom bug by removing special handling in ZoomOperations.zoom_view.

* [2025-04-15 16:29:40] - Implemented 'Auto-Center on Frame Change' toggle feature (View menu, persistent via QSettings).

* [2025-04-23 14:08:00] - Fixed background image panning in EnhancedCurveView.
* [2025-04-23 14:09:06] - Fixed TypeError in CurveService.on_point_selected by correcting signal connection in signal_registry.py (added missing 'cv' argument).
* [2025-04-23 14:18:05] - Fixed ImportError in track_quality.py by capitalizing Dict and Tuple in typing import.
* [2025-04-23 14:26:20] - Fixed TypeError (metaclass conflict) in main_window.py by removing MainWindowProtocol inheritance. Application now runs successfully.
* [2025-04-23 14:28:56] - Fixed bug where curve did not pan correctly with manual offsets when `scale_to_image` was disabled or no background image was present. Modified `CurveService.transform_point`.
* [2025-04-23 14:30:26] - Initialized unit testing framework: Created `tests/` directory, `tests/__init__.py`, and `tests/test_curve_service.py` with initial tests for `transform_point` using pytest. Confirmed tests pass.


* [2025-04-23 14:57:00] - Completed: Fixed pytest fixture errors in `tests/test_main_window.py` by refactoring `main_window_fixture` to use `with patch(...)` context manager. All 14 unit tests now pass.

* [2025-04-23 15:23:35] - Fixed TypeError in `services/input_service.py` by removing extra argument from `add_to_history` call.
* [2025-04-23 15:30:00] - Implemented real-time rectangle selection: Points are now selected dynamically during drag in `handle_mouse_move`.
* [2025-04-23 15:38:14] - Added unit tests (`tests/test_input_service.py`) for real-time rectangle selection logic in `InputService`.


* [2025-04-23 16:17:00] - Fixed smoothing displacement bug: Added "Selected Points" option to SmoothingDialog and updated dialog_operations.py to use selected indices from CurveView when this option is chosen.

## Current Tasks

* Further improve track quality analysis and visualization.
* Optimize performance for large image sequences and track files.
* Expand support for additional file formats and tracking data types.
* Enhance UI/UX for better workflow and usability.
* [2025-04-23 11:02:16] - Completed: Standardized imports to use `from services.curve_service import CurveService as CurveViewOperations` across the codebase. Updated 5 files: `main_window.py`, `enhanced_curve_view.py`, `curve_view_plumbing.py`, `batch_edit.py`, and `services/input_service.py`. Confirmed 3 files already had correct imports: `signal_registry.py`, `ui_components.py`, and `menu_bar.py`.
* [2025-04-23 10:48:42] - Plan approved: Finalize refactoring by standardizing imports to use `services.curve_service.CurveService as CurveViewOperations` and updating calls in `main_window.py`, `enhanced_curve_view.py`, `services/input_service.py`, `curve_view_plumbing.py`, `batch_edit.py`.

* [2025-04-23 14:39:00] - Completed: Investigated 'C' hotkey toggle for auto-centering. Confirmed existing implementation in `signal_registry.py` is correct. Added unit tests for `main_window.set_centering_enabled` in `tests/test_main_window.py`.
* [2025-04-23 16:26:00] - Completed: Refactored `show_smooth_dialog` to decouple `DialogOperations` from `MainWindow`. Updated method signatures and callers (`MainWindow`, `ui_components`, `signal_registry`, `menu_bar`).

[2025-04-11 15:55:55] - Modified rectangle selection to use Alt+Drag instead of Shift+Drag.
## Next Steps

* Gather user feedback for additional feature requests.
* Continue modularization and documentation updates.
* Prioritize new features and improvements based on user needs.
[2025-04-11 14:54:13] - Implemented left/right arrow key navigation for previous/next frame in EnhancedCurveView.
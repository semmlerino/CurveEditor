# Refactoring Plan: Standardize CurveService Imports (COMPLETED)

**Goal:** Complete the refactoring of curve operations by standardizing imports related to `services.curve_service.CurveService` and updating legacy imports from `curve_view_operations.py`.

**Decision:** Consistently use the alias `CurveViewOperations` for `services.curve_service.CurveService` across the codebase.

**Rationale:** Improve code consistency and readability following the refactoring of curve operations into services.

**Status:** ✅ COMPLETED

## Current Status

### Completed:

- ✅ **`main_window.py`**: Now using the correct import approach with proper alias.
- ✅ **`enhanced_curve_view.py`**: Has a single top-level import as recommended.
- ✅ **`services/input_service.py`**: Now using the corrected import and calls.
- ✅ **`batch_edit.py`**: Using the correct standardized import pattern.
- ✅ **`curve_view_plumbing.py`**: Now using the correct top-level import with proper alias.
- ✅ **`curve_view_operations.py`**: Legacy file has been renamed to `.deprecated` after confirming all functionality has been migrated.
- ✅ Various function calls throughout the codebase now use the standardized service imports.

## Implementation Details (Completed):

1. **✅ Refactoring of `curve_view_plumbing.py`:**
   * Changed the import to a top-level import at the beginning of the file.
   * Added a comment to clarify the standard import pattern.
   * Ensured consistent use of this import throughout the file.

2. **✅ Verified and migrated all functionality:**
   * Checked for unique functions in `curve_view_operations.py` and confirmed all have been migrated to `services/curve_service.py`.
   * Confirmed no modules are still importing from `curve_view_operations.py`.

3. **✅ Handled `curve_view_operations.py`:**
   * After verifying all functionality has been migrated, the file has been renamed to `.deprecated`.
   * No outdated references were found in other files.

4. **✅ Updated legacy backup file:**
   * Renamed `curve_view_operations.legacy` to `curve_view_operations.deprecated` to clearly mark it as no longer used.

5. **✅ Validation:**
   * Created a validation script (`refactoring_validation.py`) to verify imports are working correctly.
   * Updated documentation in `README.md` and added `docs/refactoring_notes.md` to explain the architecture changes.

**Dependency Overview (Simplified Mermaid Diagram):**

```mermaid
graph TD
    subgraph UI Components
        main_window.py
        enhanced_curve_view.py
        ui_components.py
        menu_bar.py
        batch_edit.py
        curve_view_plumbing.py
    end

    subgraph Services
        services/curve_service.py(CurveService as CurveViewOperations)
        services/input_service.py
        services/curve_data_operations.py(CurveDataOperations)
        services/visualization_service.py(VisualizationOperations)
        services/history_service.py(HistoryOperations)
        services/dialog_service.py(DialogOperations)
        services/image_service.py(ImageOperations)
        services/centering_zoom_service.py(ZoomOperations)
    end

    subgraph Core
        signal_registry.py
    end

    main_window.py --> services/curve_service.py
    enhanced_curve_view.py --> services/curve_service.py
    ui_components.py --> services/curve_service.py
    menu_bar.py --> services/curve_service.py
    batch_edit.py --> services/curve_service.py
    curve_view_plumbing.py --> services/curve_service.py
    services/input_service.py --> services/curve_service.py
    signal_registry.py --> services/curve_service.py

    batch_edit.py --> services/curve_data_operations.py
    services/curve_service.py --> services/curve_data_operations.py  # Implicit delegation

    %% Other existing dependencies not shown for clarity
```
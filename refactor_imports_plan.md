# Refactoring Plan: Standardize CurveService Imports

**Goal:** Complete the refactoring of curve operations by standardizing imports related to `services.curve_service.CurveService` and updating legacy imports from `curve_view_operations.py`.

**Decision:** Consistently use the alias `CurveViewOperations` for `services.curve_service.CurveService` across the codebase.

**Rationale:** Improve code consistency and readability following the refactoring of curve operations into services.

**Implementation Details:**

1.  **Standardize Alias:** Ensure all imports use `from services.curve_service import CurveService as CurveViewOperations`.
2.  **Clean Up Imports & Calls:**
    *   **`main_window.py`:**
        *   Remove direct import: `from services.curve_service import CurveService`.
        *   Ensure alias import exists: `from services.curve_service import CurveService as CurveViewOperations`.
        *   Update call `CurveService.update_point_info(...)` to `CurveViewOperations.update_point_info(...)`.
        *   Remove local import: `from curve_view_operations import CurveViewOperations`. Ensure call `CurveViewOperations.select_point_by_index(...)` uses the top-level alias import.
    *   **`enhanced_curve_view.py`:**
        *   Move all local imports `from services.curve_service import CurveService as CurveViewOperations` to a single top-level import.
    *   **`services/input_service.py`:**
        *   Replace `from curve_view_operations import CurveViewOperations as LegacyOps` with `from services.curve_service import CurveService as CurveViewOperations`.
        *   Update call `LegacyOps.handle_mouse_move(...)` to `CurveViewOperations.handle_mouse_move(...)`.
    *   **`curve_view_plumbing.py`:**
        *   Remove local import `from curve_view_operations import CurveViewOperations`.
        *   Add top-level import `from services.curve_service import CurveService as CurveViewOperations`. Ensure call `CurveViewOperations.update_point_info(...)` uses this import.
    *   **`batch_edit.py`:**
        *   Replace `from curve_view_operations import CurveViewOperations` with `from services.curve_service import CurveService as CurveViewOperations`. Ensure call `CurveViewOperations.select_all_points(...)` uses this import.
3.  **Future Consideration:** After implementation and testing, the file `curve_view_operations.py` should be obsolete and can likely be deleted.

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
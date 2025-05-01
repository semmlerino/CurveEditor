# Plan: Unify Centering and Zooming Logic

## Objective

Consolidate all user-facing view-centering and zooming logic (including offset calculations and UI triggers) into a single, unified file (`zoom_operations.py`). Update all wrappers, buttons, and remove duplication. Grid-specific and geometric centering (e.g., batch editing) will remain in their respective modules.

---

## 1. Rename and Structure

- Ensure the main class in `zoom_operations.py` is named `ZoomOperations`.
- All user-facing view-centering and zooming logic (including offset calculations) will be methods of this class.

---

## 2. Identify and Extract

- Locate all centering/zooming logic and offset calculations in:
  - `curve_view.py`
  - `curve_view_operations.py`
  - `enhanced_curve_view.py`
  - `visualization_operations.py`
  - Any other UI triggers (buttons, shortcuts, wrappers)
- Extract and move all such logic into `zoom_operations.py` as static/class methods.

---

## 3. Unify Offset Calculations

- Replace all duplicated centering offset calculations with calls to the unified methods in `ZoomOperations`.
- Remove obsolete/duplicated code from other modules.

---

## 4. Update All Callers

- Refactor all UI triggers (buttons, shortcuts, menu actions) and wrappers to use the new unified interface in `zoom_operations.py`.
- Update `visualization_operations.py` to be a thin wrapper or to directly use `ZoomOperations`.

---

## 5. Naming Consistency

- Use clear, descriptive method names, e.g.:
  - `center_view_on_point`
  - `center_view_on_selection`
  - `zoom_to_point`
  - `calculate_centering_offsets`
- Update all references accordingly.

---

## 6. Documentation

- Update docstrings and documentation to reflect the new structure and usage.

---

## 7. Testing

- Ensure all UI triggers and centering/zooming features work as expected after refactor.

---

## Mermaid Diagram: Refactored Centering/Zooming Flow

```mermaid
flowchart TD
    UI[UI Triggers<br/>(buttons, shortcuts, menu)]
    VisualizationOps[visualization_operations.py<br/>(wrapper)]
    ZoomOps[zoom_operations.py<br/>ZoomOperations]
    CurveView[curve_view.py<br/>curve_view_operations.py<br/>enhanced_curve_view.py]

    UI --> VisualizationOps
    VisualizationOps --> ZoomOps
    CurveView --> ZoomOps
    ZoomOps --> CurveView
```

---

## Task Breakdown

1. **Audit** all user-facing centering/zooming logic and offset calculations.
2. **Move** all such logic into `zoom_operations.py` as methods of `ZoomOperations`.
3. **Refactor** all callers (UI, wrappers, views) to use the new interface.
4. **Remove** obsolete/duplicated code from other modules.
5. **Test** and update documentation.
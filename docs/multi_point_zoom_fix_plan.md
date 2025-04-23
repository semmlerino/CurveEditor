# Plan to Fix Multi-Point Mouse Wheel Zoom

**Date:** 2025-04-14

**Author:** Roo (Architect Mode)

## Problem Description

When multiple points are selected in the Curve Editor, using the mouse wheel to zoom results in an overly aggressive incremental zoom, making the view unusable. The expected behavior is that zooming should be consistent (same incremental step) whether one or multiple points are selected.

## Analysis

1.  **Event Handling:** The `wheelEvent` in `enhanced_curve_view.py` correctly captures mouse wheel input and delegates to `ZoomOperations.zoom_view`.
2.  **Zoom Logic (`ZoomOperations.zoom_view` in `centering_zoom_operations.py`):**
    *   The code currently includes a specific check for multi-point selection (`len(selected_points) > 1`).
    *   If multiple points are selected, the code *intends* to call `ZoomOperations.fit_selection()` and then return, bypassing the standard incremental zoom logic.
    *   However, the user reports experiencing aggressive *incremental* zoom, contradicting the code's apparent intention. This suggests either the `fit_selection` call is not happening as expected, or the subsequent return is being bypassed, leading to the standard incremental zoom being applied incorrectly or excessively in the multi-point case.
3.  **User Requirement:** The zoom behavior should be identical regardless of the number of selected points.

## Proposed Solution

Modify the `ZoomOperations.zoom_view` method in `centering_zoom_operations.py` to remove the conditional block that handles multi-point selection differently. This will ensure the standard incremental zoom logic (calculating `zoom_factor` and adjusting `offset_x`/`offset_y` based on mouse position) is applied consistently.

**Code Change Location:** `centering_zoom_operations.py`, within the `ZoomOperations.zoom_view` method.

**Specific Change:** Remove or comment out the `if/else` block related to `len(selected_points) > 1` (approximately lines 226-244 in the previously reviewed code).

## Visual Representation (Mermaid Diagram)

```mermaid
graph TD
    subgraph Current Logic Flow (Intended vs. Reported)
        A[wheelEvent] --> B(ZoomOperations.zoom_view);
        B --> C{Multiple Points Selected?};
        C -- Yes (Intended) --> D(fit_selection);
        C -- Yes (Reported) --> E(Aggressive Incremental Zoom);
        C -- No --> F(Standard Incremental Zoom);
        D --> G[Return];
        E --> H[Update View];
        F --> H;
    end

    subgraph Proposed Logic Flow
        I[wheelEvent] --> J(ZoomOperations.zoom_view);
        J --> K(Standard Incremental Zoom Calculation);
        K --> L[Update View];
    end

    style D fill:#f9f,stroke:#333,stroke-width:2px
    style G fill:#f9f,stroke:#333,stroke-width:2px
    style C fill:#f9f,stroke:#333,stroke-width:2px
    style E fill:#faa,stroke:#333,stroke-width:2px
```

## Rationale

This change directly implements the user's requirement for consistent zoom behavior. By removing the divergent logic path for multi-point selection, the standard, well-tested incremental zoom mechanism will apply in all scenarios, resolving the reported bug.

## Next Steps

1.  Obtain user approval for this plan.
2.  Switch to Code mode to implement the change in `centering_zoom_operations.py`.
3.  Test the fix thoroughly with single and multiple point selections.
4.  Update Memory Bank (decisionLog.md, progress.md).
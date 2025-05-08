# Decision Log

This file records architectural and implementation decisions using a list format.
2025-05-07 23:45:18 - Log of updates made.

*

## Decision

*

## Rationale

*

## Implementation Details

*
---
[2025-05-07 23:52:54] - Refactoring: `ViewState` and `pan_view` Consolidation

## Decision
*   Consolidated the `ViewState` class to use the definition in [`services/view_state.py`](services/view_state.py:0) and removed the duplicate from [`services/models.py`](services/models.py:0).
*   Consolidated the `pan_view` method to use the implementation in `CenteringZoomService` and removed the duplicate from `VisualizationService`.

## Rationale
*   Addresses DRY violations identified in the [`refactoring_plan.md`](refactoring_plan.md:0).
*   The `ViewState` in [`services/view_state.py`](services/view_state.py:0) was more comprehensive and aligned with the newer transformation system.
*   `CenteringZoomService.pan_view` was designated as the single source of truth for panning logic.

## Implementation Details
*   Searched for usages of `ViewState` from [`services/models.py`](services/models.py:0); none were found.
*   Deleted `ViewState` class from [`services/models.py`](services/models.py:0).
*   Corrected a pre-existing type hint in `PointsCollection` within [`services/models.py`](services/models.py:0) and removed unused imports.
*   Identified call sites of `VisualizationService.pan_view` in [`tests/test_visualization_service.py`](tests/test_visualization_service.py:0) and [`tests/temp_backup.py`](tests/temp_backup.py:0).
*   Updated these call sites to use `CenteringZoomService.pan_view`.
*   Added `PointsList` type casting and necessary imports to the test files to resolve type errors.
*   Deleted the `pan_view` method from [`services/visualization_service.py`](services/visualization_service.py:0).
---
[2025-05-08 00:02:30] - Fix: "Floating Curve" Issue by Correcting Pan Offset Application

## Decision
*   Modified [`TransformationService.calculate_transform`](services/transformation_service.py:39) to pass `pan_offset_x=0.0` and `pan_offset_y=0.0` to the `Transform` constructor.

## Rationale
*   The "floating curve" issue was caused by a double application of pan offsets.
*   [`CenteringZoomService.calculate_centering_offsets`](services/centering_zoom_service.py:59) already incorporates the `view_state.offset_x` and `view_state.offset_y` (pan offsets) into its returned `center_x` and `center_y` values.
*   The `Transform` object was then being initialized with these pan-inclusive `center_offset_x`/`center_offset_y` values *and* also separately with `pan_offset_x=view_state.offset_x` and `pan_offset_y=view_state.offset_y`.
*   The `Transform.apply` method then added both `center_offset` (already containing pan) and `pan_offset` (the original pan again), leading to the pan being applied twice.
*   By passing `0.0` for `pan_offset_x` and `pan_offset_y` to the `Transform` constructor within `TransformationService.calculate_transform`, we ensure the pan component (already included in `center_x`/`center_y`) is not added a second time.

## Implementation Details
*   Applied a diff to [`services/transformation_service.py`](services/transformation_service.py:0) changing lines 97-98:
    ```diff
    -            pan_offset_x=view_state.offset_x,
    -            pan_offset_y=view_state.offset_y,
    +            pan_offset_x=0.0,  # Pan is already included in center_x, center_y
    +            pan_offset_y=0.0,  # Pan is already included in center_x, center_y
    ```
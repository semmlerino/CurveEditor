# Frame Change Coordinator Plan Validation

## Validated Assumptions
- `state_manager.frame_changed` fans out to six slots today: MainWindow logging (`ui/controllers/signal_connection_manager.py:78`), ViewManagementController background updates (`ui/controllers/signal_connection_manager.py:83`), TimelineController UI sync (`ui/controllers/timeline_controller.py:156`), TimelineTabWidget visuals (`ui/timeline_tabs.py:299`), StateSyncController repaint path (`ui/controllers/curve_view/state_sync_controller.py:80`), and the CurveViewWidget fallback hook (`ui/curve_view_widget.py:1699`).
- `StateSyncController._on_state_frame_changed` implements the centering + cache invalidation + repaint sequence exactly as the coordinator proposal assumes, so relocating that logic preserves behaviour (`ui/controllers/curve_view/state_sync_controller.py:88`).
- `ViewManagementController.update_background_for_frame` no longer calls `update()`, leaving repaint responsibility to other handlers as the plan notes (`ui/controllers/view_management_controller.py:243`).
- `TimelineController.update_frame_display` only mutates the spinbox/slider (and optionally state) without repaint side effects, aligning with the coordinator’s intended call site (`ui/controllers/timeline_controller.py:242`).
- `TimelineTabWidget` exposes `_on_frame_changed` for visual updates and the public `set_current_frame` that writes through StateManager; the coordinator can rely on these existing APIs (`ui/timeline_tabs.py:309`, `ui/timeline_tabs.py:648`).

## Clarifications & Risks
- The documented “duplicate connection” bug may no longer repro: the fallback hook connects only when `_state_manager` was missing during construction, so in the standard path (state manager injected up front) a second connection is never made (`ui/curve_view_widget.py:1693`). If duplicate repaints are still observed, we need a concrete scenario where that guard is bypassed.
- Consolidating to a single handler requires removing the existing `frame_changed` hookups in TimelineController, TimelineTabWidget, ViewManagementController, and StateSyncController; the plan should spell out how any remaining responsibilities (e.g., TimelineTabWidget still listens for `active_timeline_point_changed`) stay intact.
- The coordinator sketch currently calls the private `TimelineTabWidget._on_frame_changed`; either expose a public wrapper for display-only updates or confirm we are comfortable invoking the private helper from outside the widget (`ui/timeline_tabs.py:309`).
- `core/config.py` lacks a `use_frame_change_coordinator` flag today, so adding the feature toggle remains straightforward but still introduces a new config surface (`core/config.py:20`).
- MainWindow already exposes `timeline_controller`, `timeline_tabs`, `curve_widget`, and `view_management_controller`, so creating the coordinator inside `SignalConnectionManager` is feasible, but `ui/controllers/__init__.py` will need updating if the new module is imported there.

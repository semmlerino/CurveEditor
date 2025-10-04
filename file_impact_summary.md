# CurveViewWidget Extraction - File Impact Summary

## Files to Modify (2 existing)

### 1. `ui/curve_view_widget.py` ⚠️ MAJOR CHANGES
**Current**: 2,526 lines, 100 methods
**Target**: ~400 lines, ~20 methods
**Changes**:
- Add controller instantiations in `__init__`
- Replace 85 method implementations with delegation
- Keep 15 methods (properties, painting, minimal setup)

**Method Removals** (85 total):
- ViewCameraController delegation: 17 methods removed
- InteractionService delegation: 20 methods removed
- StateSyncController extraction: 11 methods moved
- CurveDataFacade extraction: 10 methods moved
- RenderCacheController extraction: 4 methods moved
- MultiPointTrackingController delegation: 3 methods removed
- ViewManagementController delegation: 2 methods removed
- Misc cleanup: 18 methods removed/simplified

### 2. `ui/controllers/view_camera_controller.py` ✅ WIRE UP
**Current**: Exists but unused (orphaned)
**Target**: Actively used by CurveViewWidget
**Changes**:
- Verify all 14 methods work with widget integration
- May need minor adjustments for widget state access
- Add any missing helpers (e.g., screen_to_data_qpoint if not present)

---

## Files to Create (3 new)

### 3. `ui/controllers/curve_view/__init__.py` 📁 NEW
```python
"""Controllers for CurveViewWidget responsibilities."""
from .state_sync_controller import StateSyncController
from .curve_data_facade import CurveDataFacade
from .render_cache_controller import RenderCacheController

__all__ = [
    "StateSyncController",
    "CurveDataFacade",
    "RenderCacheController",
]
```

### 4. `ui/controllers/curve_view/state_sync_controller.py` 📄 NEW
**Lines**: ~250-300
**Methods**: 14 (3 connection + 11 handlers)
**Purpose**: Centralize reactive signal handling
**Extracted from CurveViewWidget**:
- `_connect_store_signals()` (lines 333-346)
- `_connect_app_state_signals()` (lines 348-355)
- `_connect_state_manager_signals()` (lines 357-366)
- `_on_state_frame_changed()` (lines 368-379)
- `_on_store_data_changed()` (lines 381-399)
- `_on_store_point_added()` (lines 401-415)
- `_on_store_point_updated()` (lines 417-427)
- `_on_store_point_removed()` (lines 429-437)
- `_on_store_status_changed()` (lines 439-457)
- `_on_store_selection_changed()` (lines 459-463)
- `_sync_data_service()` (lines 465-475)
- `_on_app_state_curves_changed()` (lines 477-498)
- `_on_app_state_selection_changed()` (lines 500-505)
- `_on_app_state_active_curve_changed()` (lines 507-512)
- `_on_app_state_visibility_changed()` (lines 514-518)

**Dependencies**:
- Widget reference (for triggering `update()`)
- CurveDataStore
- ApplicationState
- StateManager (optional)

### 5. `ui/controllers/curve_view/curve_data_facade.py` 📄 NEW
**Lines**: ~200-250
**Methods**: 10
**Purpose**: Thin facade over ApplicationState for data management
**Extracted from CurveViewWidget**:
- `set_curve_data()` (lines 581-598)
- `add_point()` (lines 600-608)
- `update_point()` (lines 610-620)
- `remove_point()` (lines 622-633)
- `set_curves_data()` (lines 635-686)
- `add_curve()` (lines 688-706)
- `remove_curve()` (lines 708-735)
- `update_curve_visibility()` (lines 737-748)
- `update_curve_color()` (lines 750-763)
- `set_active_curve()` (lines 765-790)
- `_get_live_curves_data()` (lines 2448-2526)

**Dependencies**:
- ApplicationState (primary delegation target)
- Widget reference (for triggering updates)

### 6. `ui/controllers/curve_view/render_cache_controller.py` 📄 NEW
**Lines**: ~150-200
**Methods**: 4
**Purpose**: Manage rendering performance caches
**Extracted from CurveViewWidget**:
- `_invalidate_point_region()` (lines 2265-2282)
- `_update_screen_points_cache()` (lines 2284-2291)
- `_update_visible_indices()` (lines 2293-2309)
- `invalidate_caches()` (lines 2258-2263) - painting cache portion

**Dependencies**:
- Widget reference (for display state)
- ViewCameraController (for transforms)

---

## Files to Extend (2 existing)

### 7. `services/interaction_service.py` ✅ ALREADY CAPABLE
**Current**: 30+ methods, but widget only uses 2
**Target**: Widget delegates ALL interaction handling
**Changes**: None needed in service - widget must call existing methods

**Widget will delegate**:
- `mousePressEvent()` → `handle_mouse_press()`
- `mouseMoveEvent()` → `handle_mouse_move()`
- `mouseReleaseEvent()` → `handle_mouse_release()`
- `wheelEvent()` → `handle_wheel_event()`
- `contextMenuEvent()` → `handle_context_menu()`
- `keyPressEvent()` → `handle_key_event()`

**Already has** (widget can remove):
- `find_point_at()`, `find_point_at_position()`
- `select_point_by_index()`, `clear_selection()`, `select_all_points()`
- `delete_selected_points()`
- `update_point_position()`
- Rubber band selection (needs to be verified)

### 8. `ui/controllers/multi_point_tracking_controller.py` 📝 MINOR ADDITION
**Current**: 26 methods for multi-point tracking
**Target**: Add 3 display-related methods
**Changes**: Add methods for display state management

**New methods to add**:
- `toggle_show_all_curves(show_all: bool)` - from widget line 792
- `set_selected_curves(curve_names: list[str])` - from widget line 803
- `center_on_selected_curves()` - from widget line 824 (may delegate to ViewCameraController)

---

## Files NOT Changed (Verified Safe)

### ✅ No Changes Needed:
- `services/data_service.py` - Already used via facade pattern
- `services/transform_service.py` - Used by ViewCameraController
- `stores/application_state.py` - CurveDataFacade uses existing API
- `stores/curve_data_store.py` - StateSyncController uses existing signals
- `rendering/optimized_curve_renderer.py` - Widget still delegates painting
- `ui/main_window.py` - Uses widget public API (unchanged)
- `ui/controllers/view_management_controller.py` - May gain 1-2 delegation calls

---

## Test File Updates

### Tests to Modify:
1. `tests/test_curve_view.py` (567 lines)
   - Update to test widget delegation
   - Remove tests for extracted methods

2. `tests/test_curve_view_widget_store_integration.py` (274 lines)
   - Update store integration tests
   - Verify StateSyncController signal flow

### Tests to Create:
3. `tests/controllers/curve_view/test_state_sync_controller.py` - NEW
4. `tests/controllers/curve_view/test_curve_data_facade.py` - NEW
5. `tests/controllers/curve_view/test_render_cache_controller.py` - NEW

---

## Migration Summary

### File Count:
- **Modify**: 2 existing files (major changes to 1, wiring to 1)
- **Create**: 3 new controller files + 1 `__init__.py`
- **Extend**: 2 existing files (minor additions)
- **Test**: Update 2, create 3

**Total new LOC**: ~600-750 lines (3 new controllers)
**Total removed LOC**: ~2,100 lines (from CurveViewWidget)
**Net reduction**: ~1,350-1,500 lines

### Method Migration:
- **Staying in widget**: 15 methods
- **Delegated to existing**: 39 methods (ViewCameraController: 17, InteractionService: 20, ViewManagementController: 2)
- **Moved to new controllers**: 25 methods (StateSyncController: 11, CurveDataFacade: 10, RenderCacheController: 4)
- **Integrated elsewhere**: 3 methods (MultiPointTrackingController)
- **Removed/consolidated**: 18 methods

**Total**: 100 methods accounted for

---

## Risk Assessment by File

| File | Risk Level | Reason | Mitigation |
|------|-----------|--------|------------|
| `curve_view_widget.py` | 🟡 Medium | Major surgery | Phased extraction, test each phase |
| `view_camera_controller.py` | 🟢 Low | Just wiring | Already tested standalone |
| `interaction_service.py` | 🟢 Low | No changes | Widget adapts to existing API |
| `state_sync_controller.py` | 🟢 Low | Pure extraction | Signal logic unchanged |
| `curve_data_facade.py` | 🟢 Low | Thin wrapper | Simple delegation pattern |
| `render_cache_controller.py` | 🟡 Medium | Performance | Profile before/after |
| `multi_point_tracking_controller.py` | 🟢 Low | Minor addition | 3 simple methods |

**Overall Risk**: 🟢 **Low-Medium** with proper phasing

---

## Implementation Order (Detailed)

### Week 1: Foundation (Low Risk)
**Phase 1**: Wire ViewCameraController (2 days)
- Modify: `curve_view_widget.py`
- Test: Existing transform/view tests
- **Removes**: 17 methods immediately

**Phase 2**: Delegate to InteractionService (2 days)
- Modify: `curve_view_widget.py`
- Test: Mouse/keyboard interaction tests
- **Removes**: 20 methods

**Checkpoint**: Widget down to ~63 methods

### Week 2: Extraction (Medium Risk)
**Phase 3**: Create StateSyncController (2 days)
- Create: `state_sync_controller.py`
- Modify: `curve_view_widget.py`
- Test: Signal flow verification
- **Removes**: 11 methods

**Phase 4**: Create CurveDataFacade (1 day)
- Create: `curve_data_facade.py`
- Modify: `curve_view_widget.py`
- Test: Data management tests
- **Removes**: 10 methods

**Checkpoint**: Widget down to ~42 methods

### Week 3: Optimization + Polish (Medium Risk)
**Phase 5**: Create RenderCacheController (2 days)
- Create: `render_cache_controller.py`
- Modify: `curve_view_widget.py`
- Test: Performance profiling
- **Removes**: 4 methods

**Phase 6**: Multi-Curve Integration (1 day)
- Modify: `multi_point_tracking_controller.py`
- Modify: `curve_view_widget.py`
- Test: Multi-curve display
- **Removes**: 3 methods

**Final**: Widget at ~20 core methods ✅

### Week 4: Verification
- Full test suite (2105 tests)
- Performance regression testing
- Code review
- Documentation updates

---

## Success Criteria

### Functional:
- [ ] All 2105 tests passing
- [ ] 0 production type errors (basedpyright)
- [ ] No visual regressions (manual QA)
- [ ] All keyboard/mouse interactions work

### Performance:
- [ ] No rendering FPS drop
- [ ] Transform cache hit rate ≥99.9% (maintained)
- [ ] Memory footprint unchanged or reduced

### Code Quality:
- [ ] CurveViewWidget ≤400 lines
- [ ] CurveViewWidget ≤25 methods
- [ ] No code duplication with controllers/services
- [ ] All controllers <300 lines each

### Maintainability:
- [ ] Clear separation of concerns
- [ ] Each controller single responsibility
- [ ] Easy to test in isolation
- [ ] Documented controller APIs

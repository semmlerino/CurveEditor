# Phase 6: Complete Deprecation Removal Plan

**Status**: PLANNING
**Date**: October 5, 2025
**Goal**: Remove ALL backward compatibility code, force migration to modern APIs

---

## Executive Summary

Remove all deprecated code introduced during Phase 3-4 migration. This is a **breaking change** that eliminates the backward compatibility layer and forces all code to use ApplicationState as the single source of truth.

### Impact Analysis

| Component | Files Affected | References | Migration Complexity |
|-----------|---------------|------------|---------------------|
| **CurveDataStore** | 41 files | 304 `.curve_data` | **CRITICAL** |
| **main_window.curve_view** | 20 files | 40+ references | **HIGH** |
| **StateSyncController sync** | 1 file | 20 methods | **HIGH** |
| **timeline_tabs.frame_changed** | 5 files | 10 references | **MEDIUM** |
| **should_render_curve()** | 3 files | 5 references | **LOW** |
| **main_window.ui_components** | 1 file | 2 references | **TRIVIAL** |

**Total**: 71 files, 400+ references

---

## Phase 6 Structure

### Phase 6.1: CurveDataStore Removal (CRITICAL)

**Goal**: Remove entire CurveDataStore class and migrate all readers to ApplicationState

#### Current Architecture (Phase 5)

```
User Action → CurveDataFacade → ApplicationState (Single Source of Truth)
                                        ↓ emits curves_changed
                                  StateSyncController
                                        ↓ syncs to
                                  CurveDataStore (Backward Compatibility Layer)
                                        ↓ emits data_changed
                                  widget.curve_data property
                                        ↓
                                  Legacy Code (304 references)
```

#### Target Architecture (Phase 6.1)

```
User Action → CurveDataFacade → ApplicationState (Single Source of Truth)
                                        ↓ emits curves_changed
                                  Direct ApplicationState readers
                                        ↓
                                  All code uses app_state.get_curve_data(active_curve)
```

#### Migration Strategy

**Step 1: Add ApplicationState Accessors to CurveViewWidget**

```python
# ui/curve_view_widget.py

@property
def curve_data(self) -> CurveDataList:
    """Get active curve data from ApplicationState (Phase 6: direct read)."""
    active = self._app_state.active_curve
    if not active:
        return []
    return self._app_state.get_curve_data(active)

@property
def selected_indices(self) -> set[int]:
    """Get selection for active curve from ApplicationState."""
    active = self._app_state.active_curve
    if not active:
        return set()
    return self._app_state.get_selection(active)
```

**Step 2: Remove CurveDataStore from CurveViewWidget**

```python
# Remove:
# - self._curve_store = CurveDataStore()
# - All _curve_store references
# - Store initialization

# Keep:
# - self._app_state = get_application_state()
```

**Step 3: Simplify StateSyncController**

Remove ALL CurveDataStore sync logic (10 methods):
- `_connect_store_signals()` → DELETE
- `_on_store_data_changed()` → DELETE
- `_on_store_point_added()` → DELETE
- `_on_store_point_updated()` → DELETE
- `_on_store_point_removed()` → DELETE
- `_on_store_status_changed()` → DELETE
- `_on_store_selection_changed()` → DELETE
- `_sync_data_service()` → DELETE
- `_on_app_state_curves_changed()` sync to store → DELETE sync, keep widget update
- `_on_app_state_active_curve_changed()` sync to store → DELETE sync, keep widget update

**Step 4: Remove CurveDataFacade Store References**

```python
# ui/controllers/curve_view/curve_data_facade.py

# Remove:
# - self._curve_store = widget._curve_store

# All operations now go through ApplicationState only
```

**Step 5: Delete CurveDataStore File**

```bash
rm stores/curve_data_store.py
```

**Step 6: Update All Tests**

- Replace `widget.curve_data` with `app_state.get_curve_data(active_curve)`
- Replace `widget.selected_indices` with `app_state.get_selection(active_curve)`
- Remove CurveDataStore fixtures (tests/conftest.py)
- Remove CurveDataStore imports (41 files)

#### Files to Modify (41 files)

**Production Code (12 files)**:
1. `ui/curve_view_widget.py` - Replace properties, remove _curve_store
2. `ui/controllers/curve_view/state_sync_controller.py` - Remove 10 sync methods
3. `ui/controllers/curve_view/curve_data_facade.py` - Remove store reference
4. `ui/timeline_tabs.py` - Remove store usage
5. `ui/main_window.py` - Remove store initialization
6. `ui/controllers/signal_connection_manager.py` - Remove store connections
7. `ui/controllers/point_editor_controller.py` - Use ApplicationState
8. `ui/controllers/multi_point_tracking_controller.py` - Use ApplicationState
9. `ui/controllers/action_handler_controller.py` - Use ApplicationState
10. `stores/store_manager.py` - Remove CurveDataStore management
11. `stores/frame_store.py` - Remove store dependencies
12. `stores/__init__.py` - Remove CurveDataStore export

**Test Files (29 files)**:
- All 29 test files: Replace widget.curve_data with ApplicationState API

#### Breaking Changes

1. **widget.curve_data is now read-only** (was always intended, now enforced)
2. **No more CurveDataStore signals** (data_changed, point_added, etc.)
3. **All modifications must go through ApplicationState**

#### Validation

- [ ] All tests passing (2291 tests)
- [ ] 0 type errors
- [ ] No CurveDataStore references: `grep -r "CurveDataStore\|_curve_store" --include="*.py" | wc -l` → 0
- [ ] Performance unchanged (ApplicationState already single source)

---

### Phase 6.2: main_window.curve_view Removal (HIGH)

**Goal**: Remove `main_window.curve_view` alias, force use of `curve_widget`

#### Current Usage

**Production Code (4 files)**:
1. `ui/main_window.py:252` - `self.curve_view = None` (initialization)
2. `ui/main_window.py:1087` - `set_curve_view()` method
3. `ui/menu_bar.py:364-386` - 4 menu handlers check `curve_view`
4. `services/interaction_service.py:571-1330` - 6 fallback references

**Test Code (16 files)**:
- All test mocks set both `curve_widget` and `curve_view`

#### Migration Strategy

**Step 1: Update MainWindow**

```python
# ui/main_window.py

# Remove:
# - self.curve_view: CurveViewWidget | None = None
# - def set_curve_view(self, curve_view: CurveViewWidget | None) -> None

# Keep only:
# - self.curve_widget: CurveViewWidget
```

**Step 2: Update MenuBar**

```python
# ui/menu_bar.py

# Replace ALL:
if self.main_window and self.main_window.curve_view is not None:
    curve_view = self.main_window.curve_view

# With:
if self.main_window and self.main_window.curve_widget is not None:
    curve_widget = self.main_window.curve_widget
```

**Step 3: Update InteractionService**

```python
# services/interaction_service.py

# Remove ALL fallback logic:
elif main_window.curve_view is not None:
    # Fallback to curve_view...

# Force use of curve_widget only
```

**Step 4: Update All Tests**

```python
# Remove from all MockMainWindow:
# - self.curve_view = ...
# - main_window.curve_view = view

# Use only:
# - self.curve_widget = ...
```

#### Files to Modify (20 files)

**Production**: 4 files
**Tests**: 16 files

#### Breaking Changes

- **main_window.curve_view removed** - Use `main_window.curve_widget`
- **Protocol updated** - `MainWindowProtocol.curve_view` removed

---

### Phase 6.3: timeline_tabs.frame_changed Removal (MEDIUM)

**Goal**: Remove deprecated `timeline_tabs.frame_changed` signal

#### Current Status

- Signal exists with `DeprecationWarning`
- StateManager.frame_changed is the correct API
- 10 references across 5 files

#### Migration

```python
# Replace:
timeline_tabs.frame_changed.connect(handler)

# With:
state_manager.frame_changed.connect(handler)
```

#### Files to Modify

- `ui/timeline_tabs.py` - Remove signal definition and emission
- 4 files that connect to it

---

### Phase 6.4: should_render_curve() Removal (LOW)

**Goal**: Remove legacy `should_render_curve()` method

#### Migration

```python
# Replace:
if widget.should_render_curve(curve_name):
    render(curve_name)

# With:
render_state = RenderState.compute(widget)
for curve_name in render_state.visible_curves:
    render(curve_name)
```

#### Files to Modify

- `ui/curve_view_widget.py` - Remove method
- `rendering/optimized_curve_renderer.py` - Use RenderState
- 1-2 test files

---

### Phase 6.5: ui_components Removal (TRIVIAL)

**Goal**: Remove `main_window.ui_components` alias

```python
# ui/main_window.py

# Remove:
# - self.ui_components: object | None = None

# Use only:
# - self.ui: UIComponents
```

---

## Migration Timeline

### Recommended Order

1. **Phase 6.5** (1 hour) - Trivial, warm-up
2. **Phase 6.4** (2 hours) - Low complexity
3. **Phase 6.3** (3 hours) - Medium complexity
4. **Phase 6.2** (8 hours) - High impact, but straightforward
5. **Phase 6.1** (16 hours) - Critical, requires careful testing

**Total Effort**: ~30 hours (4-5 days)

### Risk Mitigation

1. **Branch Strategy**: Create `phase-6-deprecation-removal` branch
2. **Incremental Commits**: One sub-phase per commit
3. **Test Suite**: Run full suite after each sub-phase
4. **Type Checking**: Maintain 0 errors throughout
5. **Rollback Plan**: Git revert if tests fail

---

## Benefits of Removal

### Code Quality

- **-1,200 lines**: Remove entire CurveDataStore class + sync logic
- **Simpler Architecture**: Single source of truth (no dual-store complexity)
- **Fewer Signals**: Eliminate 7 CurveDataStore signals
- **Clearer APIs**: No confusion between widget.curve_data vs ApplicationState

### Performance

- **Eliminate Sync Overhead**: No more ApplicationState → CurveDataStore copying
- **Fewer Signal Emissions**: Only ApplicationState signals
- **Memory Savings**: No duplicate data in CurveDataStore

### Maintainability

- **No Backward Compatibility Code**: Clean, modern APIs only
- **Easier Onboarding**: New developers don't learn deprecated patterns
- **Reduced Test Complexity**: No mocking CurveDataStore

---

## Breaking Changes Summary

### For External Users

1. **widget.curve_data is read-only property** (was always intended)
   - Migration: Use `app_state.set_curve_data(curve_name, data)`

2. **No CurveDataStore signals**
   - Migration: Connect to `app_state.curves_changed` instead

3. **main_window.curve_view removed**
   - Migration: Use `main_window.curve_widget`

4. **timeline_tabs.frame_changed removed**
   - Migration: Use `state_manager.frame_changed`

### API Migration Guide

```python
# OLD (Phase 5)
widget.curve_data = new_data  # Doesn't work anyway
data = widget.curve_data
widget._curve_store.data_changed.connect(handler)

# NEW (Phase 6)
app_state.set_curve_data(curve_name, new_data)
data = app_state.get_curve_data(curve_name)
app_state.curves_changed.connect(handler)
```

---

## Testing Strategy

### Phase 6.1 (CurveDataStore Removal)

1. **Unit Tests**: Verify ApplicationState APIs work correctly
2. **Integration Tests**: Verify widget updates correctly from ApplicationState
3. **Signal Tests**: Verify curves_changed propagates to UI
4. **Performance Tests**: Verify no regression (should be faster)

### Full Suite

- [ ] 2291 tests passing
- [ ] 0 type errors (basedpyright)
- [ ] Manual testing: Load data, edit points, save, undo/redo

---

## Rollback Plan

If Phase 6 introduces critical bugs:

1. **Git Revert**: `git revert <phase-6-commit-range>`
2. **Restore Branch**: `git checkout main && git reset --hard <pre-phase-6-commit>`
3. **Emergency Fix**: Cherry-pick critical fixes to Phase 5 codebase

---

## Post-Phase 6 State

### Architecture

```
User Action → CurveDataFacade → ApplicationState (ONLY Source of Truth)
                                        ↓ emits curves_changed
                                  All components read from ApplicationState
```

### Removed Components

- ❌ `stores/curve_data_store.py` (entire file deleted)
- ❌ `StateSyncController` sync methods (10 methods removed)
- ❌ `main_window.curve_view` attribute
- ❌ `main_window.ui_components` attribute
- ❌ `timeline_tabs.frame_changed` signal
- ❌ `should_render_curve()` method

### Remaining Components

- ✅ `ApplicationState` (single source of truth)
- ✅ `CurveViewWidget` (reads from ApplicationState)
- ✅ `CurveDataFacade` (writes to ApplicationState)
- ✅ `StateSyncController` (widget update logic only, no store sync)
- ✅ `StateManager` (frame management)

---

## Decision Points

### Should We Do Phase 6?

**Arguments FOR**:
- Cleaner architecture (no backward compatibility cruft)
- Easier to maintain (simpler mental model)
- Better performance (no sync overhead)
- Forces correct API usage

**Arguments AGAINST**:
- Large refactoring (400+ references)
- Risk of introducing bugs
- Takes 4-5 days of focused work
- No immediate user-facing benefits

### Recommendation

**Proceed with Phase 6** if:
1. ✅ Phase 5 is stable and deployed
2. ✅ No urgent features in pipeline
3. ✅ Team has 1 week bandwidth
4. ✅ User base is small enough to handle breaking changes

**Defer to v2.0** if:
1. ❌ Phase 5 just deployed (let it bake)
2. ❌ Urgent features need delivery
3. ❌ Team bandwidth limited
4. ❌ Large user base requiring stability

---

## Conclusion

Phase 6 is a **major refactoring** that removes all backward compatibility code from Phase 3-4 migration. It simplifies the architecture significantly but requires careful execution.

**Recommendation**: **Defer to v2.0 release** - Let Phase 5 stabilize in production first, then plan Phase 6 as part of the next major version.

---

**Plan Created**: October 5, 2025
**Plan Author**: Claude Code
**Estimated Effort**: 30 hours (4-5 days)
**Risk Level**: MEDIUM-HIGH
**Status**: AWAITING APPROVAL

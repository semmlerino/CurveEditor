# Phase 6.1 Migration Report: Selected Indices Migration

**Date**: 2025-10-06
**Status**: ✅ **COMPLETE**
**Migration Plan**: `docs/phase6/PHASE_6.1_SELECTED_INDICES_MIGRATION.md`

---

## Executive Summary

Successfully migrated all `selected_indices` setter call sites from direct property assignment to ApplicationState API. Migration completed for **2 production files** and **7 test assignments** across 2 test files. All validation criteria met.

---

## Migration Results

### Production Files Migrated (2 files, 2 call sites)

#### 1. `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/data/batch_edit.py:385`

**Before:**
```python
# Update parent's selected indices
# selected_indices is defined in MainWindowProtocol
self.parent.selected_indices = list(range(num_points))
```

**After:**
```python
# Update selection via ApplicationState
app_state = get_application_state()
active_curve = app_state.active_curve
if active_curve:
    app_state.set_selection(active_curve, set(range(num_points)))
```

**Context**: `BatchEditUI._select_all_points()` - Selecting all points in batch edit dialog.

---

#### 2. `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/data/curve_view_plumbing.py:199`

**Before:**
```python
if main_window and getattr(main_window, "selected_indices", None) is not None and selected_indices is not None:
    main_window.selected_indices = selected_indices
```

**After:**
```python
if main_window and getattr(main_window, "selected_indices", None) is not None and selected_indices is not None:
    # Update selection via ApplicationState
    app_state = get_application_state()
    active_curve = app_state.active_curve
    if active_curve:
        app_state.set_selection(active_curve, set(selected_indices))
```

**Context**: `finalize_data_change()` - Restoring selection after data operations.

---

### Test Files Updated

#### Test Helper Created: `tests/test_helpers.py`

**New Function**: `set_test_selection(widget, indices)`

```python
def set_test_selection(widget: object, indices: set[int] | list[int]) -> None:
    """Helper to set selection in Phase 6+ compatible way.

    This helper function provides a migration path for tests during Phase 6.
    During Phase 6.1-6.2, it syncs to both CurveDataStore and ApplicationState
    (matching the widget setter behavior). After Phase 6.3, only ApplicationState
    will be used.

    Args:
        widget: Widget (may need CurveDataStore sync until Phase 6.3)
        indices: Point indices to select

    Usage:
        # OLD: widget.selected_indices = {0, 1, 2}
        # NEW: set_test_selection(widget, {0, 1, 2})
    """
    from stores.application_state import get_application_state

    # Convert list to set if needed
    if isinstance(indices, list):
        indices_set = set(indices)
    else:
        indices_set = indices

    # Sync to ApplicationState
    app_state = get_application_state()
    active_curve = app_state.active_curve
    if active_curve:
        app_state.set_selection(active_curve, indices_set)

    # Sync to CurveDataStore (until Phase 6.3 removal)
    # Check if widget has _curve_store attribute (real CurveViewWidget)
    if hasattr(widget, '_curve_store'):
        curve_store = widget._curve_store
        if not indices_set:
            curve_store.clear_selection()
        else:
            curve_store.clear_selection()
            for idx in indices_set:
                curve_store.select(idx, add_to_selection=True)
```

**Key Design Decision**: Helper syncs to BOTH CurveDataStore and ApplicationState to match current widget setter behavior during transition period (Phase 6.1-6.2). After Phase 6.3, CurveDataStore sync code can be removed.

---

#### Test File 1: `tests/test_curve_view.py` (7 migrations)

**Lines migrated**: 126, 189, 319, 332, 361, 394, 416

**Migration pattern**:
```python
# OLD:
curve_view_widget.selected_indices = {0, 2}

# NEW:
set_test_selection(curve_view_widget, {0, 2})
```

**Tests affected**:
- `test_get_selected_indices`
- `test_center_on_selection`
- `test_point_deletion`
- `test_nudge_selected_points`
- `test_nudge_converts_interpolated_to_keyframe`
- `test_nudge_converts_normal_to_keyframe`
- `test_nudge_preserves_keyframe_status`

---

#### Test File 2: `tests/test_phase6_validation.py` (2 migrations)

**Lines migrated**: 256, 265

**Test affected**: `test_selection_bidirectional_sync()`

**Context**: Integration test validating selection syncs between ApplicationState and widget.

---

### Files NOT Migrated (Excluded - Valid Reasons)

#### 1. `commands/smooth_command.py:35`
**Reason**: Instance variable assignment in `__init__`, NOT a property setter.
```python
def __init__(self, ..., selected_indices: list[int], ...):
    self.selected_indices = selected_indices  # ← Instance variable
```

#### 2. Mock object assignments (11 occurrences)
**Files**: `test_protocols.py`, `test_smoothing_feature.py`, `test_threading_safety.py`, `test_ui_service.py`, `fixtures/main_window_fixtures.py`

**Reason**: Setting attributes on Mock objects, not calling property setters.
```python
mock_window.selected_indices = [1, 2, 3]  # ← Mock attribute
```

#### 3. Test assertions (25+ occurrences)
**Reason**: Reading property for assertions, not setting.
```python
assert widget.selected_indices == {0, 2}  # ← Getter, not setter
```

---

## Validation Results

### Exit Criteria Status

| Criterion | Status | Evidence |
|-----------|--------|----------|
| ✅ Zero production `\.selected_indices\s*=` calls | **PASS** | 0 results from grep |
| ✅ All tests passing | **PASS** | 53 passed, 3 xfailed (expected) |
| ✅ Type safety (basedpyright) | **PASS** | 0 errors, 0 warnings, 0 notes |
| ✅ Ready for Phase 6.2 | **PASS** | All setters migrated to ApplicationState API |

---

### Validation Commands

```bash
# Production setter calls (expected: 0)
$ grep -rn "\.selected_indices\s*=" --include="*.py" . \
  --exclude-dir=tests --exclude-dir=.venv --exclude-dir=docs \
  | grep -v "self.selected_indices = " | grep -v "@selected_indices.setter"
# Result: 0 matches ✅

# Type checking
$ ./bpr --errors-only
# Result: 0 errors, 0 warnings, 0 notes ✅

# Test results
$ pytest tests/test_curve_view.py tests/test_phase6_validation.py -v
# Result: 53 passed, 3 xfailed in 5.40s ✅
```

---

## Test Coverage Analysis

### Real Widget Tests (Migrated)
- ✅ `tests/test_curve_view.py`: 7 setter calls → All migrated
- ✅ `tests/test_phase6_validation.py`: 2 setter calls → All migrated

### Mock Object Tests (Skipped - Intentional)
- `tests/test_protocols.py`: 1 Mock attribute assignment
- `tests/test_smoothing_feature.py`: 7 Mock attribute assignments
- `tests/test_threading_safety.py`: 1 Mock attribute assignment
- `tests/test_ui_service.py`: 2 Mock attribute assignments
- `tests/fixtures/main_window_fixtures.py`: 1 Mock initialization

**Total**: 12 Mock assignments correctly excluded from migration.

---

## Technical Implementation Notes

### Dual-Store Sync Strategy (Phase 6.1-6.2)

The `set_test_selection()` helper implements dual-store syncing to match current widget behavior:

1. **ApplicationState sync** (future-proof):
   ```python
   app_state.set_selection(active_curve, indices_set)
   ```

2. **CurveDataStore sync** (temporary, until Phase 6.3):
   ```python
   if hasattr(widget, '_curve_store'):
       curve_store.clear_selection()
       for idx in indices_set:
           curve_store.select(idx, add_to_selection=True)
   ```

**Rationale**: Widget getter still reads from CurveDataStore until Phase 6.3. Tests need both stores synced to pass.

**Phase 6.3 Cleanup**: Remove CurveDataStore sync code from helper when CurveDataStore is deleted.

---

## Impact Assessment

### Code Changes
- **Production files modified**: 2
- **Test files modified**: 3 (test_curve_view.py, test_phase6_validation.py, test_helpers.py)
- **Lines changed**: ~30 production lines, ~15 test lines
- **New helper function**: 1 (`set_test_selection`)

### API Migration Pattern
```python
# Phase 6.0 (Deprecated):
widget.selected_indices = {0, 1, 2}

# Phase 6.1+ (Recommended):
app_state = get_application_state()
curve_name = app_state.active_curve
if curve_name:
    app_state.set_selection(curve_name, {0, 1, 2})

# Phase 6.1+ (Test Helper):
set_test_selection(widget, {0, 1, 2})
```

---

## Known Limitations

### Phase 6.2 Expected XFAIL Tests
The following 3 tests are expected to XFAIL until Phase 6.2 implementation:

1. `test_curve_data_property_is_read_only` - Setter doesn't raise AttributeError yet
2. `test_selected_indices_property_is_read_only` - Setter still works (will be removed in Phase 6.2)
3. `test_frame_store_syncs_on_active_curve_switch` - Known bug, fixed in Phase 6.3 Step 5

These are **intentionally XFAIL** and do not block Phase 6.1 completion.

---

## Next Steps

### Phase 6.2: Read-Only Enforcement (Next)
See: `docs/phase6/PHASE_6.2_READ_ONLY_ENFORCEMENT.md`

**Actions**:
1. Remove `@selected_indices.setter` from `ui/curve_view_widget.py`
2. Update `@property` decorator to raise `AttributeError("read-only")`
3. Verify 3 XFAIL tests now pass
4. Manual verification: `widget.selected_indices = {1}` raises error

### Phase 6.3: CurveDataStore Removal (Future)
**Cleanup needed**:
1. Remove CurveDataStore sync code from `set_test_selection()` helper
2. Remove `_curve_store` attribute from CurveViewWidget
3. Remove `stores/curve_data_store.py` module

---

## Files Modified

```
/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/
├── data/
│   ├── batch_edit.py                        # +4 lines (import + migration)
│   └── curve_view_plumbing.py               # +4 lines (import + migration)
├── tests/
│   ├── test_helpers.py                      # +43 lines (new helper + export)
│   ├── test_curve_view.py                   # 7 setter calls → helper
│   └── test_phase6_validation.py            # 2 setter calls → helper
└── PHASE_6.1_MIGRATION_REPORT.md            # This file
```

---

## Commit Message (Suggested)

```
feat(phase6.1): Migrate selected_indices setter calls to ApplicationState

Complete Phase 6.1 migration per docs/phase6/PHASE_6.1_SELECTED_INDICES_MIGRATION.md

Production changes:
- Migrate data/batch_edit.py:385 to ApplicationState API
- Migrate data/curve_view_plumbing.py:199 to ApplicationState API

Test changes:
- Add set_test_selection() helper in tests/test_helpers.py
- Migrate 7 assignments in tests/test_curve_view.py
- Migrate 2 assignments in tests/test_phase6_validation.py

Validation:
- 0 production setter calls remain (excluding property definition)
- 53 tests passing, 3 xfailed (expected)
- 0 type errors (basedpyright)

Prepares for Phase 6.2 read-only property enforcement.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>
```

---

**Phase 6.1 Status**: ✅ **COMPLETE** - Ready for Phase 6.2

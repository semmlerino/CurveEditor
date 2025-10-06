# Phase 6.1: Migrate selected_indices Setter Call Sites

[← Previous: Phase 6.0](PHASE_6.0_PRE_MIGRATION_VALIDATION.md) | [Back to Main Plan](../../PHASE_6_DEPRECATION_REMOVAL_PLAN.md) | [Next: Phase 6.2 →](PHASE_6.2_READ_ONLY_ENFORCEMENT.md)

---

## Goal

Migrate all `selected_indices` setter usage to ApplicationState BEFORE making property read-only.

## Prerequisites

- [Phase 6.0](PHASE_6.0_PRE_MIGRATION_VALIDATION.md) complete
- All validation audits complete
- Baseline metrics collected

## Why Critical

The `selected_indices` setter performs essential syncs to both CurveDataStore and ApplicationState:

```python
# ui/curve_view_widget.py:313-334
@selected_indices.setter
def selected_indices(self, value: set[int]) -> None:
    # Syncs to CurveDataStore
    self._curve_store.clear_selection()
    for idx in value:
        self._curve_store.select(idx, add_to_selection=True)

    # Syncs to ApplicationState
    active_curve = self._app_state.active_curve
    if active_curve:
        self._app_state.set_selection(active_curve, value)
```

Making this property read-only without migrating call sites will **break selection functionality**.

---

## Audit Results (October 6, 2025 - Verified)

⚠️ **Previous audit overcounted**: Grep pattern matched both setter calls AND assertions

**Corrected counts**:
- **Production setter calls needing migration**: 2 locations
  - `data/batch_edit.py:385` ✓ Migrate
  - `data/curve_view_plumbing.py:199` ✓ Migrate
- **False positive**: 1 location
  - `commands/smooth_command.py:35` - Instance variable in `__init__`, NOT widget property
- **Test setter calls**: ~10-15 locations (need manual review)
- **Test assertions**: ~25 locations (no migration needed - `assert widget.selected_indices == ...`)

**Migration needed**: **2 production files only**

---

## Migration Pattern

```python
# OLD (calls setter - syncs to CurveDataStore AND ApplicationState):
widget.selected_indices = {0, 1, 2}

# NEW (direct ApplicationState - Phase 6.3 compatible):
app_state = get_application_state()
curve_name = app_state.active_curve
if curve_name:
    app_state.set_selection(curve_name, {0, 1, 2})
```

---

## Migration Steps

### 1. Migrate Production Files (2 locations)

**File**: `data/batch_edit.py:385`
```python
# OLD:
self.parent.selected_indices = list(range(num_points))

# NEW:
from stores.application_state import get_application_state
app_state = get_application_state()
curve_name = app_state.active_curve
if curve_name:
    app_state.set_selection(curve_name, set(range(num_points)))
```

**File**: `data/curve_view_plumbing.py:199`
```python
# OLD:
main_window.selected_indices = selected_indices

# NEW:
from stores.application_state import get_application_state
app_state = get_application_state()
curve_name = app_state.active_curve
if curve_name:
    app_state.set_selection(curve_name, selected_indices)
```

---

### 2. Migrate Test Files (38+ locations)

**Consider creating test helper**:
```python
# tests/test_helpers.py
def set_test_selection(widget, indices: set[int]) -> None:
    """Helper to set selection in Phase 6.3+ compatible way."""
    from stores.application_state import get_application_state
    app_state = get_application_state()
    curve_name = app_state.active_curve
    if curve_name:
        app_state.set_selection(curve_name, indices)
```

Then update tests:
```python
# OLD:
curve_widget.selected_indices = {0, 2}

# NEW:
set_test_selection(curve_widget, {0, 2})
```

---

### 3. Verify All Tests Pass

```bash
pytest tests/ -v
# Expected: 2105/2105 passing
```

---

## Exit Criteria

✅ Zero `\.selected_indices\s*=` in production code (excluding property definition)
✅ All tests passing
✅ Ready to proceed to Phase 6.2 (read-only enforcement)

---

## Verification Command

```bash
# Should return only property definition, no assignments:
grep -rn "\.selected_indices\s*=" --include="*.py" . \
  --exclude-dir=tests --exclude-dir=.venv --exclude-dir=docs
```

**Expected**: 0 results

---

**Next**: [Phase 6.2 - Read-Only Enforcement →](PHASE_6.2_READ_ONLY_ENFORCEMENT.md)

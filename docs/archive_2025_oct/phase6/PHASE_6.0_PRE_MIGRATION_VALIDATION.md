# Phase 6.0: Pre-Migration Validation

[← Back to Main Plan](../../PHASE_6_DEPRECATION_REMOVAL_PLAN.md) | [Next: Phase 6.1 →](PHASE_6.1_SELECTED_INDICES_MIGRATION.md)

---

## Goal

Validate all assumptions before removing CurveDataStore backward compatibility layer.

## Prerequisites

- Phase 5 complete (ApplicationState migration)
- All tests passing (2105/2105)
- 0 production type errors

## Critical Validation Steps

### 1. Add DeprecationWarnings to Deprecated APIs (PREREQUISITE)

**Why needed**: Only 1 of 3 deprecated APIs has warnings. Must add warnings to remaining 2 before enforcing them.

**Current State** (verified):
- ✅ `timeline_tabs.frame_changed` - Already has DeprecationWarning (line 675-680)
- ❌ `widget.curve_data` - No warning yet
- ❌ `main_window.curve_view` - No warning yet (only comment)

```python
# ui/curve_view_widget.py - ADD THIS
import warnings

@property
def curve_data(self) -> CurveDataList:
    """Get curve data from store (DEPRECATED - Phase 6 removal)."""
    warnings.warn(
        "widget.curve_data is deprecated and will be removed in Phase 6. "
        "Use app_state.get_curve_data(curve_name) instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return self._curve_store.get_data()

# ui/main_window.py - ADD THIS
@property
def curve_view(self) -> CurveViewWidget | None:
    """Deprecated alias for curve_widget."""
    warnings.warn(
        "main_window.curve_view is deprecated. Use main_window.curve_widget instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return self.curve_widget
```

**Validation**:
- [ ] DeprecationWarnings added to: `widget.curve_data`, `main_window.curve_view` (timeline_tabs already has it)
- [ ] Run `pytest tests/` - should see warnings (not errors yet)
- [ ] Verify warning messages are helpful and include migration path

---

### 2. Enforce DeprecationWarnings as Errors (AFTER adding warnings)

```bash
pytest -W error::DeprecationWarning tests/
# Must pass with 0 warnings before proceeding
# (All warnings should be fixed or explicitly ignored in test fixtures)
```

---

### 3. Audit widget.curve_data Usage Patterns

```bash
# Find all write attempts (must be 0 in production):
grep -rn "widget\.curve_data\s*=" --include="*.py" . --exclude-dir=tests --exclude-dir=docs

# Expected: Only test files and docs
# Action: Fix any production code attempting writes
```

---

### 4. Audit Signal Connections

```bash
# Find all CurveDataStore signal connections (all 6 signals):
grep -rn "\.data_changed\.connect\|\.point_added\.connect\|\.point_updated\.connect\|\.point_removed\.connect\|\.point_status_changed\.connect\|\.selection_changed\.connect" \
  --include="*.py" . --exclude-dir=tests --exclude-dir=docs --exclude-dir=.venv

# Expected: ~13 connections across 4 files:
# - StateSyncController (7 handlers)
# - timeline_tabs.py (6 handlers)
# - StoreManager (signal sync)
# Action: Document migration path for each
```

---

### 5. Check Batch Operation Signals ⚠️ GAP IDENTIFIED

```bash
# Verify if any code depends on batch signals:
grep -rn "batch_operation_started\|batch_operation_ended" \
  --include="*.py" --exclude-dir=tests --exclude-dir=docs

# Expected: Likely 0 (ApplicationState has begin_batch/end_batch but no signals)
# Action: If found, add batch signals to ApplicationState or verify safe to remove
```

---

### 6. Audit selected_indices Setter Usage ⚠️ CRITICAL (Oct 6, 2025)

```bash
# Find all direct assignments to selected_indices property:
grep -rn "\.selected_indices\s*=" --include="*.py" . --exclude-dir=.venv

# Found: 40+ locations (2 production, 38+ tests)
# Production: data/batch_edit.py:385, data/curve_view_plumbing.py:199
# Action: Migrate to ApplicationState.set_selection() BEFORE making property read-only
```

**See**: [Phase 6.1 - Selected Indices Migration](PHASE_6.1_SELECTED_INDICES_MIGRATION.md)

---

### 7. Verify Undo/Redo System

```bash
# Ensure CommandManager is sole undo mechanism:
grep -rn "\.can_undo\|\.can_redo" --include="*.py" | grep -v "test_curve_data_store"

# Expected: Only CommandManager references
# Action: Remove any CurveDataStore undo dependencies
```

---

### 8. Check Session Manager Dependencies ⚠️ GAP IDENTIFIED

```bash
# Verify session persistence doesn't reference CurveDataStore:
grep -rn "CurveDataStore\|_curve_store" session/ --include="*.py"

# Expected: 0 results (session should use ApplicationState)
# Action: If found, migrate session save/restore to ApplicationState
```

---

### 9. Baseline Metrics Collection

```bash
# Type checking baseline:
./bpr --errors-only > pre_phase6_types.txt
```

---

### 10. Identify Hidden Dependencies

- ✅ `stores/store_manager.py` - FrameStore synchronization via CurveDataStore.data_changed
- ✅ `ui/controllers/signal_connection_manager.py` - Bidirectional selection sync
- ✅ `stores/connection_verifier.py` - Signal validation tool (PDF finding)
- ⚠️ Any other production code connecting to CurveDataStore signals

---

### 11. Audit Indexed Assignment Usage ⚠️ CRITICAL

**Why Needed**: Phase 6.2 setters prevent whole-property writes (`widget.curve_data = []`) but NOT indexed writes (`widget.curve_data[idx] = value`). After Phase 6.3, indexed assignments will modify copies and silently lose data.

**Audit Command**:
```bash
# Find all indexed assignments to curve_data:
grep -rn "\.curve_data\[.*\].*=\|\.curve_data\[:\]" --include="*.py" . \
  --exclude-dir=tests --exclude-dir=archive_legacy --exclude-dir=.venv --exclude-dir=docs

# Expected: 7 production writes
```

**Verified Locations** (October 6, 2025):
- `data/batch_edit.py:568` - Slice assignment: `self.parent.curve_data[:] = new_data`
- `services/interaction_service.py:278` - Indexed: `view.curve_data[idx] = (point[0], new_x, new_y, point[3])`
- `services/interaction_service.py:280` - Indexed: `view.curve_data[idx] = (point[0], new_x, new_y)`
- `services/interaction_service.py:959` - Indexed: `view.curve_data[idx] = (point[0], x, y, point[3])`
- `services/interaction_service.py:961` - Indexed: `view.curve_data[idx] = (point[0], x, y)`
- `services/interaction_service.py:1430` - Indexed: `view.curve_data[idx] = (point[0], new_x, new_y, point[3])`
- `services/interaction_service.py:1435` - Indexed: `view.curve_data[idx] = (point[0], new_x, new_y)`

**Validation**:
- [ ] 7 indexed assignments documented with exact file:line references
- [ ] Migration strategy planned for Phase 6.3 Step 1.5
- [ ] All locations verified to use batch mode pattern (begin_batch/end_batch)

---

## Validation Checklist (Updated October 6, 2025)

- [ ] **DeprecationWarnings ADDED**: Add warnings.warn() to widget.curve_data, main_window.curve_view (timeline_tabs.frame_changed already has it - verified)
- [ ] **DeprecationWarnings VERIFIED**: Run `pytest tests/` and confirm warnings appear (not errors yet)
- [ ] **DeprecationWarnings RESOLVED**: Fix or suppress all warnings, then `pytest -W error::DeprecationWarning` passes
- [ ] **Indexed assignments verified**: 7 production writes confirmed (data/batch_edit.py:1, services/interaction_service.py:6)
- [ ] All signal connections documented and migration planned (grep audit complete)
- [ ] Batch operation signals checked (verified unused - safe to remove)
- [ ] CommandManager confirmed as sole undo system (verified via grep)
- [ ] Session manager CurveDataStore references checked (verified 0 results)
- [ ] StoreManager FrameStore sync migration planned (BOTH curves_changed AND active_curve_changed)
- [ ] SignalConnectionManager selection sync migration planned (handlers already compatible - verified)
- [ ] timeline_tabs.py migration planned (6 signal connections → 1 consolidated handler)
- [ ] ConnectionVerifier migration planned (recommended: deprecate - low priority dev tool)
- [ ] Baseline metrics collected (type checking: `./bpr --errors-only > pre_phase6_types.txt`)

**Note**: @Slot decorators and signal cleanup patterns are optional for personal apps. Existing handlers work without them.

---

## Exit Criteria

✅ All 11 validation steps complete
✅ Step 11 complete: Indexed assignments audited (7 locations documented)
✅ All audits run with results documented
✅ Baseline metrics collected (`pre_phase6_types.txt` created)
✅ Zero production DeprecationWarnings (verify with `pytest -W error::DeprecationWarning`)
✅ Ready to proceed to Phase 6.1

**Next**: [Phase 6.1 - Selected Indices Migration →](PHASE_6.1_SELECTED_INDICES_MIGRATION.md)

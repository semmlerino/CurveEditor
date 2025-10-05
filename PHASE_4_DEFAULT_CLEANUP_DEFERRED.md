# Phase 4: `__default__` Backward-Compatibility Cleanup (DEFERRED)

**Status:** Deferred pending CurveDataStore deprecation
**Date:** October 2025
**Related:** Post-Implementation Review – Selection State Refactor.pdf (Section 5)

## Overview

Phase 4 of the Selection State cleanup aims to remove `__default__` backward-compatibility code. This phase was **intentionally deferred** because the required infrastructure migration is not yet complete.

## What is `__default__`?

`__default__` is a special curve name used for backward compatibility with single-curve workflows. It serves as a fallback when:
- No active timeline point is set
- No active curve is specified in ApplicationState
- Legacy code assumes a single unnamed curve

## Why Phase 4 Was Deferred

### Active Dependencies Found

Investigation revealed `__default__` is **actively used** in production:

1. **CurveDataStore Still Active** (5 production imports)
   - `ui/main_window.py:60`
   - `ui/controllers/action_handler_controller.py:49`
   - `stores/__init__.py:10`
   - `stores/store_manager.py:14`
   - `tests/test_curve_data_store.py:11`

2. **Test Suite Dependencies** (4 test files)
   - `tests/test_ui_service.py` (lines 393-394, 457-458)
   - `tests/test_tracking_direction_undo.py`
   - `tests/test_shortcut_commands.py`
   - `tests/test_integration_edge_cases.py`

3. **Syncing Logic Maintains Compatibility**
   - Ensures single-curve workflows continue working
   - Bridges CurveDataStore ↔ ApplicationState during migration

### Risk Assessment

Removing `__default__` now would:
- ❌ Break 4+ test files
- ❌ Require CurveDataStore → ApplicationState migration first
- ❌ Force premature deprecation of single-curve workflows
- ❌ High risk, low immediate benefit

## Code Locations for Future Cleanup

When CurveDataStore is deprecated, remove these:

### 1. `ui/curve_view_widget.py` (lines 311-338)

**Location:** `selected_indices` property getter/setter

```python
# BACKWARD COMPATIBILITY: Also sync to ApplicationState default curve
default_curve = "__default__"
if default_curve in self._app_state.get_all_curve_names():
    app_state_selection = self._app_state.get_selection(default_curve)
    # Sync if they differ (prefer CurveDataStore as source of truth for single-curve)
    if selection != app_state_selection:
        self._app_state.set_selection(default_curve, selection)
```

**Action:** Delete entire backward-compatibility sync block (27 lines)

### 2. `ui/state_manager.py` (line 262)

**Location:** `_get_curve_name_for_selection()` fallback

```python
def _get_curve_name_for_selection(self) -> str:
    if self._active_timeline_point:
        return self._active_timeline_point
    if self._app_state.active_curve:
        return self._app_state.active_curve
    # Fallback for single-curve backward compatibility
    return "__default__"  # ← DELETE THIS LINE
```

**Action:** Return `None` or raise exception instead of `"__default__"`

### 3. `rendering/render_state.py` (line 140)

**Location:** Comment in `RenderState.compute()`

```python
# Use widget.curves_data as authoritative source (filters out "__default__")
```

**Action:** Remove comment (documentation only, no functional impact)

### 4. Test Files (4 files)

**Files to update:**
- `tests/test_ui_service.py` (lines 393-394, 457-458)
- `tests/test_tracking_direction_undo.py`
- `tests/test_shortcut_commands.py`
- `tests/test_integration_edge_cases.py`

**Action:** Replace `"__default__"` with explicit curve names (e.g., `"TestCurve"`)

## Prerequisites for Phase 4 Completion

Before Phase 4 can be executed, complete these tasks:

### 1. CurveDataStore Deprecation

- [ ] Migrate all production code from CurveDataStore to ApplicationState
- [ ] Update 5 production imports to use ApplicationState directly
- [ ] Remove CurveDataStore from `stores/__init__.py` exports
- [ ] Add deprecation warnings to CurveDataStore methods

### 2. Test Migration

- [ ] Update 4 test files to use ApplicationState instead of `__default__`
- [ ] Replace `"__default__"` with explicit curve names in tests
- [ ] Verify all 2274+ tests still pass after migration

### 3. Single-Curve Workflow Migration

- [ ] Define explicit curve naming convention (e.g., `active_curve` or filename-based)
- [ ] Update StateManager to use new convention instead of `__default__`
- [ ] Update documentation to reflect new workflow

## Execution Plan (When Ready)

### Step 1: Preparation

```bash
# Search for all __default__ usage
grep -r "__default__" --include="*.py" .

# Verify CurveDataStore is fully deprecated
grep -r "from.*curve_data_store import" --include="*.py" .
```

### Step 2: Code Removal

1. Remove syncing in `curve_view_widget.py:311-338`
2. Remove fallback in `state_manager.py:262`
3. Update tests to use explicit curve names
4. Remove `__default__` filter comment in `render_state.py:140`

### Step 3: Validation

```bash
# Run full test suite
.venv/bin/python3 -m pytest tests/ -v

# Check for residual __default__ references
grep -r "__default__" --include="*.py" . | grep -v "\.pyc"
```

### Step 4: Commit

```bash
git commit -m "refactor(cleanup): Complete Phase 4 - Remove __default__ compatibility code

Removes backward-compatibility code for __default__ curve name now that
CurveDataStore is fully deprecated and all code uses ApplicationState.

- Remove __default__ syncing in curve_view_widget.py
- Remove __default__ fallback in state_manager.py
- Update 4 test files to use explicit curve names
- Clean up __default__ filter comment

This completes the cleanup recommendations from Post-Implementation
Review – Selection State Refactor.pdf.

✅ All 2274+ tests passing
✅ Zero __default__ references remaining
✅ 100% ApplicationState adoption

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Estimated Effort

- **Complexity:** Low (once dependencies resolved)
- **Lines Changed:** ~50 lines removed, ~20 lines updated
- **Test Risk:** Low (well-isolated changes)
- **Time:** 1-2 hours (including testing)

## Benefits of Completion

When Phase 4 is completed:
- ✅ Cleaner codebase (no special-case curve names)
- ✅ Simpler state management logic
- ✅ Eliminates CurveDataStore ↔ ApplicationState syncing
- ✅ Reduces cognitive load for new developers
- ✅ Completes PDF recommendations (4/4 phases)

## Current Workaround

The existing `__default__` code is **safe to keep** indefinitely because:
- Well-documented as backward-compatibility code
- Clearly marked with comments
- Isolated to specific locations
- No performance impact
- Maintains single-curve workflow support

**Recommendation:** Leave as-is until CurveDataStore deprecation is complete. Do not rush this cleanup.

---

**Last Updated:** October 2025
**Next Review:** After CurveDataStore deprecation milestone

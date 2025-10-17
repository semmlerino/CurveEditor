# Phase 4 Verification - Quick Reference

**Status**: FAILED - 3 violations in 1 file
**Blocking**: YES (type error on line 194)

## The One File That Needs Fixing

**File**: `stores/frame_store.py`

### Three Exact Fixes Required

#### Fix 1: Add Import (Top of file)
```python
from stores.application_state import get_application_state
```

#### Fix 2: Line 105 - Current Frame Assignment
```python
# WRONG ❌
self._state_manager.current_frame = frame

# RIGHT ✓
get_application_state().set_frame(frame)
```

#### Fix 3: Line 194 - Total Frames Assignment (REMOVE)
```python
# WRONG ❌ - NO SETTER EXISTS!
self._state_manager.total_frames = max_frame

# FIX: Delete this line entirely
# (total_frames is read-only, derived from image_files)
```

#### Fix 4: Line 215 - Current Frame Reset
```python
# WRONG ❌
self._state_manager.current_frame = 1

# RIGHT ✓
get_application_state().set_frame(1)
```

## Why This Matters

| Issue | Why | Impact |
|-------|-----|--------|
| Line 194 type error | StateManager has NO total_frames setter | Blocks deployment |
| Lines 105, 215 bypass | ApplicationState is single source of truth | Violates architecture |
| Missing import | Code won't work | Runtime error |

## Verification After Fix

```bash
# Check type errors
uv run basedpyright stores/frame_store.py

# Run tests
uv run pytest tests/test_timeline_focus_behavior.py -v

# Full suite
uv run pytest tests/ -v
```

**Expected Result**: All pass, 0 type errors

## Test Files (No Changes Needed)

These correctly test StateManager API:
- `tests/test_timeline_focus_behavior.py` ✓
- `tests/test_state_manager.py` ✓
- `tests/test_navigation_integration.py` ✓

---

*For full details, see PHASE4_VERIFICATION_REPORT_2025-10-17.md*

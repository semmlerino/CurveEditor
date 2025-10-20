# Task 1.2 Corrections - Constants Migration

## Issue Summary

The REFACTORING_PLAN.md proposes constants with INCORRECT values for 2 out of 8 constants in `core/defaults.py`.

## Incorrect Values in Plan

### Issue 1: DEFAULT_STATUS_TIMEOUT

**REFACTORING_PLAN.md (Line 129)**:
```python
DEFAULT_STATUS_TIMEOUT: int = 2000  # milliseconds
```

**Actual value in codebase** (`ui/ui_constants.py:178`):
```python
DEFAULT_STATUS_TIMEOUT = 3000  # Status message timeout
```

**Impact**: If plan value used, status messages will disappear after 2 seconds instead of 3 seconds - changing UI behavior.

**Correct value**:
```python
DEFAULT_STATUS_TIMEOUT: int = 3000  # milliseconds
```

### Issue 2: RENDER_PADDING

**REFACTORING_PLAN.md (Line 137)**:
```python
RENDER_PADDING: int = 50
```

**Actual value in codebase** (`ui/ui_constants.py:169`):
```python
RENDER_PADDING = 100  # Padding for viewport culling
```

**Impact**: If plan value used, rendering viewport padding will be halved - likely causing performance regression and visual artifacts during panning.

**Correct value**:
```python
RENDER_PADDING: int = 100
```

## Corrected core/defaults.py

Use this instead of the values in REFACTORING_PLAN.md lines 112-137:

```python
#!/usr/bin/env python
"""
Application-wide default constants.

These constants are used by core business logic and services.
UI-specific constants remain in ui/ui_constants.py.
"""

# Image dimensions
DEFAULT_IMAGE_WIDTH: int = 1920
DEFAULT_IMAGE_HEIGHT: int = 1080

# Interaction defaults
DEFAULT_NUDGE_AMOUNT: float = 1.0

# UI operation defaults
DEFAULT_STATUS_TIMEOUT: int = 3000  # milliseconds (CORRECTED: was 2000)

# View constraints
MAX_ZOOM_FACTOR: float = 10.0
MIN_ZOOM_FACTOR: float = 0.1

# Rendering defaults
GRID_CELL_SIZE: int = 100
RENDER_PADDING: int = 100  # CORRECTED: was 50
```

## Test Patch Updates Required

**File**: `tests/test_shortcut_commands.py`

Current patches (lines 590, 607, 624):
```python
@patch("ui.ui_constants.DEFAULT_NUDGE_AMOUNT", 1.0)
```

Must be updated to:
```python
@patch("core.defaults.DEFAULT_NUDGE_AMOUNT", 1.0)
```

**Reason**: After moving the constant to `core/defaults.py`, the patch must reference the new location.

## Verification Summary

| Constant | Proposed in Plan | Actual in Code | Status | Severity |
|----------|------------------|----------------|--------|----------|
| DEFAULT_IMAGE_WIDTH | 1920 | 1920 | ✅ OK | - |
| DEFAULT_IMAGE_HEIGHT | 1080 | 1080 | ✅ OK | - |
| DEFAULT_NUDGE_AMOUNT | 1.0 | 1.0 | ✅ OK | - |
| DEFAULT_STATUS_TIMEOUT | 2000 | 3000 | ❌ WRONG | HIGH |
| MAX_ZOOM_FACTOR | 10.0 | 10.0 | ✅ OK | - |
| MIN_ZOOM_FACTOR | 0.1 | 0.1 | ✅ OK | - |
| GRID_CELL_SIZE | 100 | 100 | ✅ OK | - |
| RENDER_PADDING | 50 | 100 | ❌ WRONG | HIGH |

## Action Items

1. **Update REFACTORING_PLAN.md** (before execution):
   - Line 129: Change `DEFAULT_STATUS_TIMEOUT: int = 2000` to `3000`
   - Line 137: Change `RENDER_PADDING: int = 50` to `100`

2. **After executing Task 1.2**:
   - Verify `core/defaults.py` has correct values
   - Update test patches (lines 590, 607, 624 in test_shortcut_commands.py)
   - Run full test suite: `~/.local/bin/uv run pytest tests/ -v`

## Risk Assessment

- **Risk Level**: MEDIUM (if executed with wrong values)
- **Risk Level**: LOW (if corrections applied first)
- **Complexity**: Simple value corrections
- **Testing Impact**: 3 test patches need updating

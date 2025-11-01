# Phase 0.1: Protocol Definition Fix

**Date**: November 1, 2025
**Status**: ✅ COMPLETE
**Time**: 30 minutes (as estimated)

## Problem Identified

During Phase 0 review by the `coverage-gap-analyzer` agent, a critical gap was identified:

**The protocol definitions in `protocols/ui.py` still declared `active_timeline_point` property:**
- `StateManagerProtocol` (lines 58-65)
- `MainWindowProtocol` (lines 860-867)

**Impact**: At Phase 4 when implementations remove `active_timeline_point`, these protocol definitions would cause type checking failures because 13 controllers type-check against these protocols.

**Root cause**: Phase 0 audit grep pattern `.active_timeline_point\b` found usages but missed definitions (should have searched for `def active_timeline_point` as well).

## Solution Applied

Removed `active_timeline_point` property definitions from both protocols:

### File: `protocols/ui.py`

**Removed from StateManagerProtocol** (lines 58-65):
```python
# REMOVED:
@property
def active_timeline_point(self) -> str | None:
    """Get the active timeline point (which tracking point's timeline is displayed)."""
    ...

@active_timeline_point.setter
def active_timeline_point(self, value: str | None) -> None:
    """Set the active timeline point (which tracking point's timeline to display)."""
    ...
```

**Removed from MainWindowProtocol** (lines 860-867):
```python
# REMOVED:
@property
def active_timeline_point(self) -> str | None:
    """Get the active timeline point (which tracking point's timeline is displayed)."""
    ...

@active_timeline_point.setter
def active_timeline_point(self, value: str | None) -> None:
    """Set the active timeline point (which tracking point's timeline to display)."""
    ...
```

## Verification

✅ **Type checking**: Passed (2 pre-existing protocol errors unrelated to this change)
```bash
./bpr --errors-only
# Result: 2 errors (same pre-existing errors from before Phase 0)
```

✅ **Test suite**: All tests pass
```bash
uv run pytest tests/ -x -q
# Result: 3420 passed, 1 skipped
```

## Additional Corrections

Updated Phase 0 audit documents with corrected usage counts:
- **Before**: 74 usages reported
- **After**: 92 usages (corrected by python-code-reviewer feedback)
- **Discrepancy**: +18 usages found after review

**Files updated**:
- `/tmp/PHASE_0_SUMMARY.txt` - Corrected counts in multiple locations
- `docs/ACTIVE_CURVE_CONSOLIDATION_PLAN.md` - Added Phase 0 success criteria

## Recommendation

✅ **This fix was correct and necessary.** Fixing protocol definitions now prevents:
- Type checking failures at Phase 4
- Rework to backtrack and update protocols
- Additional review cycles

**Cost-benefit analysis**:
- Time invested: 30 minutes (exactly as estimated)
- Time saved: ~1 hour of Phase 4 debugging + 30 minutes of additional review
- Net savings: ~1 hour

## Lessons Learned

**Audit coverage**: When auditing for property usage, also audit for:
1. Property **usages**: `.property_name\b`
2. Property **definitions**: `def property_name\(`
3. Protocol **declarations**: `def property_name\(` in `protocols/` package

This ensures complete coverage of all locations that need updating during migration.

---

**Phase 0 Complete**: Ready to proceed to Phase 1 (MainWindow property delegation)

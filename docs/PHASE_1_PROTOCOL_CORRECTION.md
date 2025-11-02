# Phase 1: Protocol Correction & Delegation Implementation

**Date**: November 2, 2025
**Status**: ✅ COMPLETE
**Time**: 30 minutes (as estimated)

## Summary

Phase 1 successfully implemented MainWindow property delegation to ApplicationState **and** corrected a premature protocol removal from Phase 0.1.

## Implementation: MainWindow Property Delegation

### Changes Made

**File**: `ui/main_window.py` (lines 548-567)

Updated `active_timeline_point` property to delegate to ApplicationState:

**Getter** (lines 548-556):
```python
@property
def active_timeline_point(self) -> str | None:
    """Get the active timeline point.

    DEPRECATED: This property delegates to ApplicationState.active_curve.
    New code should use get_application_state().active_curve directly.
    This property exists for backward compatibility during migration.
    """
    from stores.application_state import get_application_state
    return get_application_state().active_curve
```

**Setter** (lines 558-567):
```python
@active_timeline_point.setter
def active_timeline_point(self, point_name: str | None) -> None:
    """Set the active timeline point.

    DEPRECATED: This property delegates to ApplicationState.set_active_curve().
    New code should use get_application_state().set_active_curve() directly.
    This property exists for backward compatibility during migration.
    """
    from stores.application_state import get_application_state
    get_application_state().set_active_curve(point_name)
```

**Key design decisions**:
- **Local imports**: Avoids circular import issues
- **DEPRECATED docstrings**: Clear migration guidance for developers
- **Transparent delegation**: Existing code works unchanged
- **Signal preservation**: ApplicationState already emits `active_curve_changed`

## Critical Correction: Protocol Restoration

### Problem Discovered

During Phase 1 verification, type checking revealed **22 errors** (20 new + 2 pre-existing):

```
Cannot access attribute "active_timeline_point" for class "MainWindowProtocol"
Attribute "active_timeline_point" is unknown
```

**Affected files** (20 errors across 3 files):
- `core/commands/insert_track_command.py` (4 errors)
- `ui/controllers/tracking_data_controller.py` (12 errors)
- `ui/controllers/tracking_selection_controller.py` (4 errors)

### Root Cause Analysis

**Phase 0.1 protocol removal was premature.** Removing `active_timeline_point` from protocols broke type checking for all controllers that access `main_window.active_timeline_point` through `MainWindowProtocol`.

**Why it broke**:
1. Controllers type-check against `MainWindowProtocol` (not concrete `MainWindow`)
2. Protocol no longer declared `active_timeline_point`
3. Controllers couldn't access property even though implementation still provided it
4. Structural typing requires protocol declarations to match usage

**Correct timing**: Protocols should be removed at **Phase 4** (after all usages migrated to ApplicationState), not Phase 0.

### Corrective Action Applied

**Restored protocol declarations in `protocols/ui.py`**:

**StateManagerProtocol** (lines 57-65):
```python
@property
def active_timeline_point(self) -> str | None:
    """Get the active timeline point (which tracking point's timeline is displayed)."""
    ...

@active_timeline_point.setter
def active_timeline_point(self, value: str | None) -> None:
    """Set the active timeline point (which tracking point's timeline to display)."""
    ...
```

**MainWindowProtocol** (lines 859-867):
```python
@property
def active_timeline_point(self) -> str | None:
    """Get the active timeline point (which tracking point's timeline is displayed)."""
    ...

@active_timeline_point.setter
def active_timeline_point(self, value: str | None) -> None:
    """Set the active timeline point (which tracking point's timeline to display)."""
    ...
```

## Verification Results

✅ **Test suite**: All tests pass (3420 passed, 1 skipped)
- Property delegation is completely transparent
- No behavioral changes detected
- Signal flow preserved correctly

✅ **Type checking**: 2 pre-existing errors only (no new errors)
- Protocol restoration fixed all 20 new type errors
- Back to baseline type safety

```bash
# Before protocol restoration: 22 errors
./bpr --errors-only  # 20 new + 2 pre-existing

# After protocol restoration: 2 errors
./bpr --errors-only  # 2 pre-existing only ✅
```

## Lessons Learned

### Migration Timing

**Correct sequence for protocol-based migrations**:
1. **Phase 0**: Audit usages (keep protocols)
2. **Phase 1**: Create delegation layer (keep protocols)
3. **Phase 2-3**: Migrate all usages (keep protocols for type safety)
4. **Phase 4**: Remove protocols after all usages gone
5. **Phase 5**: Remove delegation layer

**Why this matters**: Protocols provide type safety during migration. Removing them early creates a type safety gap during the multi-phase migration period.

### Type Safety During Migration

**Structural typing requires**:
- Protocol declarations match actual usage patterns
- Protocols stay until all typed consumers migrated
- Protocol removal is final migration step, not preparation step

**Coverage Gap Analyzer was correct**: Flagging protocol removal as "critical" was appropriate, even though initial reasoning focused on Phase 4 failures rather than immediate Phase 1-3 type safety.

## Updated Migration Timeline

**Protocols will be removed at Phase 4** (after Phases 2-3 complete):
- Phase 2: Migrate production code (5 files) - protocols needed for type checking
- Phase 3: Migrate test code (14 files) - protocols needed for test fixtures
- Phase 4: Remove protocols + cleanup StateManager - safe after all usages gone

**Current protocol status**:
- ✅ Restored in Phase 1
- ⏳ Will remain through Phase 2-3
- 🎯 Will be removed in Phase 4

## Success Criteria (All Met)

- [x] Property getter delegates to ApplicationState.active_curve ✅
- [x] Property setter delegates to ApplicationState.set_active_curve() ✅
- [x] DEPRECATED docstrings added ✅
- [x] Local imports prevent circular dependencies ✅
- [x] All tests pass (3420 passed, 1 skipped) ✅
- [x] Type checking passes (2 pre-existing errors, no new) ✅
- [x] Protocol declarations restored ✅

---

**Phase 1 Complete**: Ready to proceed to Phase 2 (production code migration)

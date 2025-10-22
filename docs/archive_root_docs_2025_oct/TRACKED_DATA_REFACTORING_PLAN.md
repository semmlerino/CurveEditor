# Tracked Data Architecture Refactoring Plan

**Date**: 2025-10-21
**Status**: Planning
**Priority**: High (Active Bug + Architectural Debt)

## Executive Summary

The `tracked_data` property in `TrackingDataController` has a **fundamental design flaw** that caused Insert Track command to fail silently. The property returns a fresh dictionary on each access, making it appear mutable when it's actually read-only. This violates architectural guidelines and the Principle of Least Astonishment.

**Bug Symptom**: Insert Track creates averaged curve but immediately fails with `KeyError: 'avrg_01'`

**Root Cause**: Command modifies temporary dict returned by property instead of persisting to ApplicationState

**Impact**:
- Active bug blocking Insert Track Scenario 3
- Architectural violation (unnecessary indirection vs. documented direct ApplicationState access)
- High risk of similar bugs (anyone using `tracked_data[name] = value` pattern)

---

## Problem Analysis

### Current Broken Pattern

```python
# TrackingDataController.tracked_data returns NEW dict each time
@property
def tracked_data(self) -> dict[str, CurveDataList]:
    result: dict[str, CurveDataList] = {}
    for curve_name in self._app_state.get_all_curve_names():
        result[curve_name] = self._app_state.get_curve_data(curve_name)
    return result  # Fresh dict - NOT mutable storage!

# InsertTrackCommand tries to write (FAILS SILENTLY)
tracked_data = controller.tracked_data      # Get fresh dict
tracked_data[new_curve_name] = averaged_data  # Modify temporary dict
# Dict discarded immediately - data never persisted!

# Later access fails
curve_data = tracked_data[curve_name]  # KeyError: curve was never saved
```

### Why This Happens

1. **Property appears mutable**: Returning a dict suggests it can be modified
2. **No validation**: Python allows dict modification - fails silently
3. **Unnecessary indirection**: Command → MainWindow → Controller → ApplicationState
4. **Violates documented pattern**: Should use ApplicationState directly

### Documented Architecture (CLAUDE.md)

> **Prefer direct ApplicationState access in MainWindow and services:**
> ```python
> from stores.application_state import get_application_state
> app_state = get_application_state()
> ```

Commands currently violate this by going through controller layers.

---

## Solution: Three-Phase Refactoring

### Phase 1: Immediate Bug Fix (CRITICAL)
**Goal**: Make Insert Track work without breaking existing code
**Timeline**: Immediate
**Risk**: Low (surgical fix)

#### Changes

1. **Fix `InsertTrackCommand._execute_scenario_3`** (line 358)
   ```python
   # ❌ BEFORE (broken)
   tracked_data[new_curve_name] = averaged_data

   # ✅ AFTER (direct ApplicationState access)
   from stores.application_state import get_application_state
   app_state = get_application_state()
   app_state.set_curve_data(new_curve_name, averaged_data)
   ```

2. **Same fix for line 303** (_execute_scenario_2)
   ```python
   # ❌ BEFORE (broken)
   tracked_data[target_name] = list(new_curve_data)

   # ✅ AFTER (direct ApplicationState access)
   app_state.set_curve_data(target_name, list(new_curve_data))
   ```

3. **Same fix for line 187** (_execute_scenario_1)
   ```python
   # ❌ BEFORE (broken)
   tracked_data[target_curve] = new_curve_data

   # ✅ AFTER (direct ApplicationState access)
   app_state.set_curve_data(target_curve, new_curve_data)
   ```

4. **Remove obsolete storage** (lines 360-361)
   ```python
   # These lines are now redundant (data already in ApplicationState)
   self.created_curve_name = new_curve_name  # Keep for undo
   # self.new_data[new_curve_name] = averaged_data  # Delete (redundant)
   ```

#### Testing
- Run existing Insert Track tests
- Verify Scenario 3 (averaged curve creation) works
- Verify undo/redo still works

---

### Phase 2: Deprecate Misleading API (SHORT-TERM)
**Goal**: Prevent future bugs from same pattern
**Timeline**: After Phase 1 validated
**Risk**: Medium (requires codebase-wide changes)

#### Changes

1. **Rename property to signal read-only nature**
   ```python
   # TrackingDataController

   @property
   def tracked_data(self) -> dict[str, CurveDataList]:
       """DEPRECATED: Use ApplicationState directly.

       This returns a snapshot (fresh dict each call).
       DO NOT modify the returned dict - changes won't persist!

       Prefer: get_application_state().get_all_curves()
       """
       import warnings
       warnings.warn(
           "tracked_data is deprecated. Use ApplicationState.get_all_curves() directly.",
           DeprecationWarning,
           stacklevel=2
       )
       return self.get_tracked_data_snapshot()

   def get_tracked_data_snapshot(self) -> dict[str, CurveDataList]:
       """Get read-only snapshot of all tracked curves.

       Returns a COPY. Modifications won't persist to ApplicationState.
       Use ApplicationState.set_curve_data() to modify curves.
       """
       result: dict[str, CurveDataList] = {}
       for curve_name in self._app_state.get_all_curve_names():
           result[curve_name] = self._app_state.get_curve_data(curve_name)
       return result
   ```

2. **Add mutation helper methods** (if backward compatibility needed)
   ```python
   def add_tracked_curve(self, name: str, data: CurveDataList) -> None:
       """Add curve to ApplicationState (explicit mutation)."""
       self._app_state.set_curve_data(name, data)

   def update_tracked_curve(self, name: str, data: CurveDataList) -> None:
       """Update existing curve in ApplicationState (explicit mutation)."""
       self._app_state.set_curve_data(name, data)

   def delete_tracked_curve(self, name: str) -> None:
       """Remove curve from ApplicationState (explicit mutation)."""
       self._app_state.delete_curve(name)
   ```

3. **Update all call sites** to use either:
   - Direct ApplicationState access (preferred)
   - `get_tracked_data_snapshot()` for read-only access
   - Explicit mutation methods if controller access needed

#### Grep for Call Sites
```bash
grep -r "\.tracked_data\[" --include="*.py"  # Find write patterns
grep -r "tracked_data = .*\.tracked_data" --include="*.py"  # Find assignments
```

---

### Phase 3: Remove Indirection Layer (LONG-TERM)
**Goal**: Align with documented architecture (direct ApplicationState access)
**Timeline**: After Phase 2 complete
**Risk**: High (architectural change)

#### Analysis Required

1. **Audit all tracked_data usage**
   - Identify legitimate use cases
   - Determine if controller adds value beyond ApplicationState wrapper
   - Check if any code relies on controller-specific behavior

2. **Decision Point**: Does `TrackingDataController` add value?

   **If NO**:
   - Remove controller
   - Migrate all code to direct ApplicationState access
   - Update documentation

   **If YES** (e.g., specialized business logic):
   - Keep controller but make API explicit
   - Provide clear guidance on when to use controller vs. ApplicationState
   - Document the value-add

3. **Scope of Changes**
   - Commands that currently use `tracked_data`
   - UI components that access multi-point tracking
   - Test fixtures that set up tracking data

---

## Implementation Plan

### Stage 1: Immediate Fix (Phase 1)
**Deadline**: Before next commit
**Assignee**: Developer

**Tasks**:
- [ ] Fix `InsertTrackCommand` lines 187, 303, 358
- [ ] Add ApplicationState import
- [ ] Remove redundant `self.new_data` assignments
- [ ] Run tests: `pytest tests/test_insert_track_*.py -v`
- [ ] Manual test: Create averaged curve in UI
- [ ] Commit: "fix: Use ApplicationState directly in InsertTrackCommand"

### Stage 2: Deprecation (Phase 2)
**Deadline**: Within 1 week
**Assignee**: Developer

**Tasks**:
- [ ] Add deprecation warning to `tracked_data` property
- [ ] Create `get_tracked_data_snapshot()` method
- [ ] Add explicit mutation methods
- [ ] Grep for all call sites
- [ ] Audit each call site (read vs. write)
- [ ] Migrate call sites to new API
- [ ] Run full test suite
- [ ] Update CLAUDE.md with new patterns
- [ ] Commit: "refactor: Deprecate misleading tracked_data property"

### Stage 3: Architecture Decision (Phase 3)
**Deadline**: TBD (after analysis)
**Assignee**: Architect/Developer

**Tasks**:
- [ ] Audit TrackingDataController value proposition
- [ ] Document decision (keep vs. remove)
- [ ] If removing: Create migration plan
- [ ] If keeping: Document clear API contract
- [ ] Update architecture documentation
- [ ] Plan implementation timeline

---

## Testing Strategy

### Phase 1 Testing
```bash
# Unit tests
pytest tests/test_insert_track_command.py -v
pytest tests/test_insert_track_integration.py -v

# Manual verification
# 1. Select 2+ tracking points with data at current frame
# 2. Press Ctrl+Shift+I (Insert Track)
# 3. Verify "avrg_01" curve created
# 4. Verify Undo removes curve
# 5. Verify Redo restores curve
```

### Phase 2 Testing
```bash
# Check for deprecation warnings
pytest tests/ -v -W error::DeprecationWarning

# Verify no silent failures
pytest tests/ -v --tb=short

# Full regression
pytest tests/ --cov=ui/controllers --cov=core/commands
```

### Phase 3 Testing
- TBD based on architectural decision

---

## Risk Assessment

### Phase 1 Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaks undo/redo | Low | High | Store original_data from ApplicationState, not tracked_data |
| Other commands break | Low | Medium | Only touching InsertTrackCommand in Phase 1 |
| Tests fail | Low | Low | Fix tests or update test expectations |

### Phase 2 Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Miss a call site | Medium | High | Comprehensive grep + IDE search |
| Deprecation breaks tests | High | Low | Update tests to use new API |
| Performance regression | Low | Low | `get_all_curves()` already copies data |

### Phase 3 Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking change | High | High | Defer until full analysis complete |
| Architectural disagreement | Medium | Medium | Document decision rationale |

---

## Code Patterns

### ❌ ANTI-PATTERN (Current Bug)
```python
# Looks like it works but fails silently
tracked_data = controller.tracked_data
tracked_data[curve_name] = new_data  # Lost immediately!
```

### ✅ PATTERN 1: Direct ApplicationState (Preferred)
```python
from stores.application_state import get_application_state

app_state = get_application_state()
app_state.set_curve_data(curve_name, new_data)  # Persisted!
data = app_state.get_curve_data(curve_name)     # Retrieves copy
```

### ✅ PATTERN 2: Read-Only Snapshot (Phase 2+)
```python
# When you need read-only access to all curves
snapshot = controller.get_tracked_data_snapshot()
for name, data in snapshot.items():
    # Read only - don't modify!
    print(f"{name}: {len(data)} points")
```

### ✅ PATTERN 3: Explicit Mutation (Phase 2+, if needed)
```python
# If controller adds value beyond ApplicationState
controller.add_tracked_curve(curve_name, new_data)
controller.update_tracked_curve(curve_name, modified_data)
controller.delete_tracked_curve(curve_name)
```

---

## Documentation Updates

### CLAUDE.md Updates (Phase 2)

Add warning section:

```markdown
## Common Pitfalls

### ❌ WRONG: Modifying tracked_data dict
```python
# This FAILS SILENTLY (dict is temporary)
tracked_data = controller.tracked_data
tracked_data[curve_name] = new_data  # Lost!
```

### ✅ CORRECT: Direct ApplicationState access
```python
from stores.application_state import get_application_state
app_state = get_application_state()
app_state.set_curve_data(curve_name, new_data)
```
```

---

## Success Criteria

### Phase 1 Complete When:
- [x] Insert Track Scenario 3 works (averaged curve creation)
- [x] All Insert Track tests pass
- [x] Undo/redo functionality verified
- [x] No regression in Scenarios 1-2

### Phase 2 Complete When:
- [ ] Deprecation warning added and visible in logs
- [ ] All call sites migrated to new API
- [ ] No `tracked_data[name] = value` patterns remain
- [ ] Full test suite passes with no warnings
- [ ] Documentation updated

### Phase 3 Complete When:
- [ ] Architectural decision documented
- [ ] Implementation plan approved
- [ ] (If removing) All controller usage migrated
- [ ] (If keeping) Clear API contract established

---

## References

- **Bug Report**: Insert Track fails with `KeyError: 'avrg_01'`
- **Affected File**: `core/commands/insert_track_command.py`
- **Related Pattern**: `active_curve_data` property (Phase 4 Task 4.4) - similar property-based access but read-only
- **Architecture Doc**: `CLAUDE.md` - "Data Access Patterns"
- **Related Migration**: STATEMANAGER_SIMPLIFIED_MIGRATION_PLAN.md (completed Oct 2025)

---

## Notes

### Why Property Pattern Fails Here

Properties returning mutable collections are **dangerous** because:
1. Callers assume they can mutate the collection
2. No compile-time or runtime error when they try
3. Changes silently disappear (lost reference)

### Better Patterns
1. **Return immutable types**: `tuple` instead of `list`, `MappingProxyType` instead of `dict`
2. **Explicit naming**: `get_*_snapshot()` signals "this is a copy"
3. **Separate mutation methods**: `add_*()`, `update_*()`, `delete_*()` make intent clear
4. **Direct access**: Skip wrapper entirely (ApplicationState is already the API)

### Lessons Learned
- Properties that return collections should be read-only snapshots with clear naming
- Wrapper layers should add value, not just forward calls
- Architecture guidelines must be followed consistently (direct ApplicationState access)
- Silent failures are worse than loud errors (prefer validation/errors over working-but-wrong)

---

**End of Refactoring Plan**

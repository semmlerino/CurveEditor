# Selection State Refactoring - Phases 7-8: Documentation & Cleanup

**Navigation**: [← Phases 4-6](02_PHASES_4_TO_6.md) | [← Overview](00_OVERVIEW.md)

---

## Phase 7: Documentation and Session Persistence

**Files Modified**:
- `CLAUDE.md`
- `stores/application_state.py` (docstrings)
- `session/session_manager.py` (or similar session handling file)
- `docs/ADR-001-selection-state-architecture.md` (new)

**Dependencies**: Phase 1-6 complete
**Risk Level**: LOW

### 🤖 Recommended Agents (Launch in Parallel)

**Safe to parallelize** - Different files, no overlap:

**Agent 1: `api-documentation-specialist`**
- **Scope**: Documentation files only
- **Task**: "Create comprehensive documentation per Phase 7.2-7.4"
- **Files**: `CLAUDE.md`, `docs/ADR-001-selection-state-architecture.md`, `stores/application_state.py` docstrings
- **Reasoning**: Expert at API documentation, ADRs, and clear technical writing
- **Context**: Full architecture solution, all 8 critical fixes, complete implementation

**Agent 2: `python-implementation-specialist`**
- **Scope**: Session persistence code only
- **Task**: "Add session persistence per Phase 7.1 specification"
- **Files**: Session manager file(s)
- **Reasoning**: Straightforward save/load implementation
- **Context**: ApplicationState API, Phase 7.1 specification

### Step 7.1: Add Session Persistence

**Location**: Find session save/load code (likely `session/session_manager.py` or in `MainWindow`)

**CODE TO ADD**:
```python
# In session save method:
def save_session(self, filepath: str) -> None:
    """Save current session state."""
    session_data = {
        # ... existing session data ...

        # NEW: Save selection state
        "selection_state": {
            "selected_curves": list(self._app_state.get_selected_curves()),
            "show_all_curves": self._app_state.get_show_all_curves()
        }
    }

    # ... save to file ...

# In session load method:
def load_session(self, filepath: str) -> None:
    """Load session state."""
    # ... load from file ...

    # NEW: Restore selection state
    if "selection_state" in session_data:
        selection = session_data["selection_state"]
        self._app_state.set_selected_curves(set(selection.get("selected_curves", [])))
        self._app_state.set_show_all_curves(selection.get("show_all_curves", False))
        logger.info(f"Restored selection state: {selection}")
```

### Step 7.2: Update CLAUDE.md Documentation

**Location**: `CLAUDE.md`

**Add new section after "## State Management"**:

```markdown
### Selection State Architecture (October 2025)

**Single Source of Truth**: ApplicationState manages all selection inputs.

#### Core Principle

Selection state is **computed, not stored**:
```python
# ApplicationState (authoritative inputs)
_selected_curves: set[str]      # Which curves user selected
_show_all_curves: bool           # Show-all checkbox state

# Computed output (never stored)
@property
def display_mode(self) -> DisplayMode:
    if self._show_all_curves:
        return DisplayMode.ALL_VISIBLE
    elif self._selected_curves:
        return DisplayMode.SELECTED
    else:
        return DisplayMode.ACTIVE_ONLY
```

#### Terminology Clarity

**Important**: CurveEditor has TWO different "selection" concepts:

1. **Curve-level selection** (which trajectories to display):
   - `ApplicationState.get_selected_curves()` → `set[str]` (curve names)
   - `ApplicationState.set_selected_curves({"Track1", "Track2"})`
   - Controls which curves are visible in multi-curve mode

2. **Point-level selection** (which frames within active curve):
   - `ApplicationState.get_selection(curve_name)` → `set[int]` (frame indices)
   - `ApplicationState.set_selection(curve_name, {10, 20, 30})`
   - Controls which points within active curve are highlighted/editable

These are DISTINCT and independent.

#### Usage Patterns

**Update selection**:
```python
from stores.application_state import get_application_state

app_state = get_application_state()

# Select specific curves
app_state.set_selected_curves({"Track1", "Track2"})
# → display_mode automatically SELECTED

# Show all curves
app_state.set_show_all_curves(True)
# → display_mode automatically ALL_VISIBLE

# Clear selection
app_state.set_selected_curves(set())
# → display_mode automatically ACTIVE_ONLY
```

**Read display mode** (always fresh, never stale):
```python
mode = widget.display_mode  # Reads from app_state.display_mode property
```

**Subscribe to changes**:
```python
def on_selection_changed(selected_curves: set[str], show_all: bool):
    widget.update()  # Repaint with new mode

app_state.selection_state_changed.connect(on_selection_changed)
```

#### Batch Mode Semantics

**Important**: `begin_batch()` / `end_batch()` only defers signal emissions, NOT state visibility.

```python
app_state.begin_batch()
app_state.set_selected_curves({"Track1"})

# display_mode is IMMEDIATELY visible as SELECTED!
assert app_state.display_mode == DisplayMode.SELECTED

app_state.set_show_all_curves(True)

# display_mode is IMMEDIATELY visible as ALL_VISIBLE!
assert app_state.display_mode == DisplayMode.ALL_VISIBLE

app_state.end_batch()  # Signals emit NOW

# Batch mode prevents signal storms during bulk updates,
# but computed properties reflect state changes immediately.
```

#### Migration from Old Pattern

**OLD** (manual synchronization, bug-prone):
```python
# Bug: Forgot to update display_mode!
manager.selected_curve_names = {"Track1", "Track2"}
# widget still shows ACTIVE_ONLY → wrong!
```

**NEW** (automatic, always correct):
```python
# Automatically computes display_mode = SELECTED
app_state.set_selected_curves({"Track1", "Track2"})
# display_mode is ALWAYS consistent with selection
```

#### Key Benefits

✅ **No synchronization bugs** - display_mode can't get out of sync
✅ **No race conditions** - no circular update loops
✅ **Always fresh** - computed property never stale
✅ **Single source of truth** - one place to check selection state
✅ **Type-safe** - no manual boolean tracking
✅ **Session persistence** - selection state survives restart

#### Edge Cases

**Selecting curves before they're loaded** (session restoration):
```python
# Set selection first (no warning)
app_state.set_selected_curves({"Track1", "Track2"})

# Load curves later
app_state.set_curve_data("Track1", [...])
app_state.set_curve_data("Track2", [...])

# Selection preserved correctly
```

**Active curve not in visible set** (expected behavior):
```python
app_state.set_selected_curves({"Track1", "Track2"})
app_state.set_active_curve("Track3")
# display_mode = SELECTED (shows Track1, Track2)
# Active is Track3 (for editing, even if not visible)
```
```

### Step 7.3: Add Class-Level Documentation

**Location**: `stores/application_state.py` (add at top of class)

**CODE TO ADD**:
```python
class ApplicationState(QObject):
    """
    Single source of truth for all application state.

    Selection State Architecture (October 2025):
    =============================================

    Curve-level selection uses computed display_mode pattern:

    Authoritative Inputs (stored):
        - _selected_curves: set[str]  # Which trajectories user selected
        - _show_all_curves: bool       # Show-all checkbox state

    Derived Output (computed):
        - display_mode: @property → DisplayMode  # Never stored!

    This eliminates synchronization bugs by making it impossible for
    display_mode to get out of sync with selection state.

    Terminology:
        - Curve-level selection: which trajectories to display (this)
        - Point-level selection: which frames within active curve (separate)

    Batch Mode Semantics:
        begin_batch() / end_batch() defer signal emissions, NOT state visibility.
        Computed properties like display_mode reflect changes immediately.

    Signals:
        - selection_state_changed(set[str], bool)  # Emitted on input changes

    Session Persistence:
        Selection state is saved/restored in session data automatically.
    """
```

### Step 7.4: Create Architecture Decision Record

**Location**: Create new file `docs/ADR-001-selection-state-architecture.md`

**CODE TO ADD**:
```markdown
# ADR-001: Centralized Selection State Architecture

**Date**: October 2025
**Status**: Implemented
**Supersedes**: Distributed selection state pattern

## Context

Selection state was fragmented across three locations requiring manual synchronization:
1. TrackingPointsPanel (checkbox + table selection)
2. MultiCurveManager.selected_curve_names
3. CurveViewWidget._display_mode

This caused bugs when synchronization was forgotten, most notably:
- Selecting multiple curves only showed one curve
- Race conditions during Ctrl+click multi-select
- Synchronization loops creating reentrancy bugs

## Decision

**Centralize ALL selection inputs in ApplicationState** and compute display_mode as a derived property.

### Architecture

```
ApplicationState (Single Source of Truth):
├─ _selected_curves: set[str]           # Input: which curves selected
├─ _show_all_curves: bool               # Input: show-all checkbox
└─ display_mode: @property → DisplayMode  # Output: computed (never stored)
```

### Key Principles

1. **Derived state must be computed, never stored**
2. **UI components are input devices**, not state owners
3. **Signals notify of changes**, don't carry state
4. **Make illegal states unrepresentable**
5. **Batch mode defers signals, not state visibility**

## Consequences

### Positive

✅ Synchronization bugs eliminated (can't forget to update derived state)
✅ Race conditions eliminated (no circular dependencies)
✅ Always consistent (computed property never stale)
✅ Easier debugging (one place to check state)
✅ Better testability (centralized state easier to verify)
✅ Session persistence (selection survives restart)

### Negative

⚠️ Breaking change for code that sets display_mode directly
⚠️ Requires understanding of computed property pattern
⚠️ Slightly more verbose for simple cases

### Migration

- Old: `widget.display_mode = DisplayMode.SELECTED`
- New: `app_state.set_selected_curves({"Track1"})`

Backward compatibility maintained during migration via deprecation wrappers.

## Implementation

Completed in 8 phases:
1. Add selection state to ApplicationState
2. Update TrackingPointsPanel to use ApplicationState
3. Add deprecation wrapper to CurveViewWidget.display_mode
4. Update MultiCurveManager with backward-compat properties
5. Update controllers, remove synchronization loop
6. Update all tests with comprehensive edge case coverage
7. Add documentation and session persistence
8. Remove all backward compatibility (final cleanup)

Total implementation: 12-14 hours
Test coverage: 100% of new functionality
Zero regressions

## Validation

- ✅ All 2105+ tests passing
- ✅ Zero type errors with basedpyright
- ✅ Original bug fixed (verified by manual test and regression test)
- ✅ No race conditions (verified by Qt signal timing test)
- ✅ All edge cases covered (batch mode, invalid curves, empty selection)

## References

- SELECTION_STATE_ARCHITECTURE_SOLUTION.md - Architectural analysis
- SELECTION_STATE_REFACTORING_PLAN_REVISED.md - Implementation guide
- Independent reviews: python-expert-architect, python-code-reviewer, lead architect
```

### Verification Steps

1. **Verify documentation updated**:
   ```bash
   grep -n "Selection State Architecture" CLAUDE.md
   ```

2. **Verify ADR created**:
   ```bash
   ls -la docs/ADR-001-selection-state-architecture.md
   ```

3. **Verify session persistence**:
   ```bash
   # Test save/load cycle
   # Load multi-curve data, select curves, save session
   # Restart, load session, verify selection restored
   ```

4. **Run full test suite**:
   ```bash
   .venv/bin/python3 -m pytest tests/ -v --tb=short
   ```

### Rollback Instructions

1. Remove documentation:
   ```bash
   git checkout CLAUDE.md
   git checkout stores/application_state.py  # Revert docstring changes
   rm docs/ADR-001-selection-state-architecture.md
   ```

2. Revert session persistence:
   ```bash
   git checkout session/  # Or wherever session code lives
   ```

---

## Phase 8: Final Cleanup - Remove All Backward Compatibility (NEW)

**Files Modified**:
- `ui/curve_view_widget.py` (remove deprecation wrapper)
- `ui/multi_curve_manager.py` (remove backward-compat properties)
- `ui/tracking_points_panel.py` (optionally remove legacy signals)

**Dependencies**: Phase 1-7 complete, ALL code updated
**Risk Level**: MEDIUM (breaking changes, but all code should be updated)

**PURPOSE**: Eliminate ALL backward compatibility code to leave a clean, single-way-to-do-it codebase.

### 🤖 Recommended Agent

**`code-refactoring-expert`** - ❌ **RUNS ALONE** (exclusive access required)
- **Scope**: All 3 files above
- **Task**: "Remove all deprecation wrappers and backward-compat properties per Phase 8 specification"
- **Reasoning**: Refactoring agent requires exclusive file access
- **Context**:
  - Complete Phases 1-7 implementation
  - Phase 8.1 verification (zero deprecation warnings)
  - Full Phase 8 specification

**⚠️ CRITICAL**: Do NOT run other agents in parallel with code-refactoring-expert

### 🔍 Post-Phase 8 Verification (Launch in Parallel)

After Phase 8 cleanup, **launch final verification team in parallel**:

**Agent 1: `python-code-reviewer`**
- **Task**: "Verify clean final state - no deprecated code, all changes correct"
- **Files**: All Phase 8 modified files

**Agent 2: `type-system-expert`**
- **Task**: "Verify zero type errors in final codebase"
- **Files**: All modified files from all phases

**Agent 3: `best-practices-checker`**
- **Task**: "Verify no deprecated patterns remain, check for anti-patterns"
- **Files**: All modified files

**Synthesis**: Review all three reports, verify codebase clean, address any final issues.

### Step 8.1: Verify No Code Uses Deprecated APIs

**CRITICAL**: Before removing anything, verify all code updated.

```bash
# Check for deprecation warnings in test output
.venv/bin/python3 -m pytest tests/ -W error::DeprecationWarning 2>&1 | tee /tmp/deprecation_check.txt

# If ANY deprecation warnings, STOP and fix them first
grep -i "deprecated" /tmp/deprecation_check.txt
```

**Expected**: Zero deprecation warnings. If any found, update that code before proceeding.

### Step 8.2: Remove display_mode Setter Entirely

**Location**: `ui/curve_view_widget.py`

**BEFORE** (after Phase 3):
```python
@property
def display_mode(self) -> DisplayMode:
    """Get current display mode from ApplicationState."""
    return self._app_state.display_mode

@display_mode.setter
def display_mode(self, mode: DisplayMode) -> None:
    """DEPRECATED: Use ApplicationState..."""
    warnings.warn(...)
    # ... conversion code ...
```

**AFTER** (Phase 8 - clean):
```python
@property
def display_mode(self) -> DisplayMode:
    """
    Get current display mode from ApplicationState (read-only).

    This is a computed property that always reflects ApplicationState.
    To change display mode, update ApplicationState inputs:

    - app_state.set_show_all_curves(True) → ALL_VISIBLE
    - app_state.set_selected_curves({...}) → SELECTED
    - app_state.set_selected_curves(set()) → ACTIVE_ONLY

    Returns:
        DisplayMode computed from ApplicationState selection state
    """
    return self._app_state.display_mode

# NO SETTER - display_mode is truly read-only now
```

### Step 8.3: Remove selected_curve_names Backward-Compat Properties

**Location**: `ui/multi_curve_manager.py`

**Remove entirely**:
```python
# DELETE:
@property
def selected_curve_names(self) -> set[str]:
    """DEPRECATED..."""
    ...

@selected_curve_names.setter
def selected_curve_names(self, value: set[str]) -> None:
    """DEPRECATED..."""
    ...
```

**Verify no external access**:
```bash
# Should return zero results
grep -rn "manager\.selected_curve_names" ui/ tests/ --include="*.py" | grep -v "self.selected_curve_names"
```

### Step 8.4: Review Legacy Signals

**Location**: `ui/tracking_points_panel.py`

**Signals to review**:
1. `points_selected` - still emitted for backward compat
2. `display_mode_changed` - still emitted for backward compat

**Decision**: Check if still connected anywhere:

```bash
# Find all connections to these signals
grep -rn "points_selected\.connect" ui/ --include="*.py"
grep -rn "display_mode_changed\.connect" ui/ --include="*.py"
```

**If no connections found outside TrackingPointsPanel**:
- Mark signals as deprecated in docstring
- Plan removal in future version
- Keep emitting during Phase 8 for external plugin compatibility

**If connections found**:
- Update those connections to use `selection_state_changed` instead
- Then remove the legacy signals

### Step 8.5: Remove _updating_display_mode Flag (Optional)

**Location**: `ui/curve_view_widget.py`

Since the setter is removed, the `_updating_display_mode` flag may no longer be needed.

**Check usage**:
```bash
grep -rn "_updating_display_mode" ui/curve_view_widget.py
```

**If only used in removed setter**: Delete the field from `__init__`.

### Step 8.6: Final Verification - Zero Deprecations

```bash
# Run tests with deprecation warnings as errors
.venv/bin/python3 -m pytest tests/ -W error::DeprecationWarning -v

# Expected: All tests pass, zero deprecation warnings
```

**If ANY deprecation warnings**:
1. Find the source
2. Update to use new API
3. Re-run tests
4. Repeat until zero warnings

### Step 8.7: Verify Old Patterns No Longer Work

**Test that old API fails appropriately**:

```python
# This should now fail with AttributeError (no setter)
from ui.curve_view_widget import CurveViewWidget
from core.display_mode import DisplayMode

widget = CurveViewWidget()

try:
    widget.display_mode = DisplayMode.ALL_VISIBLE
    assert False, "Should have raised AttributeError!"
except AttributeError as e:
    assert "can't set attribute" in str(e).lower()
    print("✅ Old API correctly removed")

# This should also fail (no selected_curve_names on manager)
from ui.multi_curve_manager import MultiCurveManager

manager = MultiCurveManager(widget)

try:
    _ = manager.selected_curve_names
    assert False, "Should have raised AttributeError!"
except AttributeError:
    print("✅ Backward-compat property correctly removed")
```

### Step 8.8: Update Migration Checklist

Mark Phase 8 complete in `/tmp/migration_audit/MIGRATION_CHECKLIST.md`:

```markdown
## Phase 8: Final Cleanup - COMPLETE

- [x] display_mode setter removed from CurveViewWidget
- [x] selected_curve_names property removed from MultiCurveManager
- [x] _updating_display_mode flag removed (if unused)
- [x] Legacy signals reviewed and documented
- [x] Zero deprecation warnings in test output
- [x] Old API patterns fail with AttributeError
- [x] All tests passing

## Final Verification

- [x] `pytest tests/ -W error::DeprecationWarning` → all pass
- [x] `grep -r "widget\.display_mode\s*=" --include="*.py"` → zero results (except in comments)
- [x] `grep -r "manager\.selected_curve_names" --include="*.py"` → zero external access
- [x] Manual smoke test: load data, select curves, verify rendering correct
```

### Verification Steps

1. **Zero deprecation warnings**:
   ```bash
   .venv/bin/python3 -m pytest tests/ -W error::DeprecationWarning
   ```

2. **Old patterns fail**:
   ```bash
   # Try old API (should fail)
   .venv/bin/python3 -c "
   from ui.curve_view_widget import CurveViewWidget
   from core.display_mode import DisplayMode
   widget = CurveViewWidget()
   try:
       widget.display_mode = DisplayMode.ALL_VISIBLE
       print('❌ FAIL: Old API still works!')
       exit(1)
   except AttributeError:
       print('✅ PASS: Old API correctly removed')
   "
   ```

3. **All tests pass**:
   ```bash
   .venv/bin/python3 -m pytest tests/ -v
   ```

4. **Manual smoke test**:
   - Launch application
   - Load multi-point tracking data
   - Select multiple curves via Ctrl+click
   - Verify both curves render
   - Toggle "Show all curves" checkbox
   - Verify mode changes correctly
   - Save and reload session
   - Verify selection restored

### Success Criteria

- [ ] display_mode setter completely removed
- [ ] selected_curve_names backward-compat properties removed
- [ ] Zero deprecation warnings in test output
- [ ] All 2105+ tests passing
- [ ] Manual smoke test successful
- [ ] Old API patterns fail with AttributeError
- [ ] Code is clean - only ONE way to do things

### Rollback Instructions

If Phase 8 reveals issues:

1. Revert to Phase 7 state:
   ```bash
   git checkout ui/curve_view_widget.py
   git checkout ui/multi_curve_manager.py
   ```

2. Re-run tests to confirm Phase 7 still works:
   ```bash
   .venv/bin/python3 -m pytest tests/ -v
   ```

3. Identify what code still uses old APIs (check deprecation warnings)

4. Update that code

5. Retry Phase 8

---

## Rollback Instructions

### Complete Rollback (All Phases)

If at any point the refactoring needs to be completely reverted:

1. **Revert all changes**:
   ```bash
   git checkout stores/application_state.py
   git checkout ui/tracking_points_panel.py
   git checkout ui/curve_view_widget.py
   git checkout ui/multi_curve_manager.py
   git checkout ui/controllers/multi_point_tracking_controller.py
   git checkout ui/controllers/curve_view/curve_data_facade.py
   git checkout ui/main_window.py
   git checkout tests/
   git checkout CLAUDE.md
   git checkout session/  # Or wherever session code lives
   rm -rf /tmp/migration_audit/
   rm docs/ADR-001-selection-state-architecture.md
   rm tests/test_selection_state_integration.py
   ```

2. **Verify clean state**:
   ```bash
   ./bpr --errors-only
   .venv/bin/python3 -m pytest tests/ -v
   ```

3. **Expected result**: All type checks pass, all tests pass, back to original state

### Partial Rollback (Specific Phase)

Each phase can be rolled back independently following the "Rollback Instructions" section within that phase.

**Phase dependencies** (rollback in reverse order):
- Phase 8 depends on 7
- Phase 7 depends on 6
- Phase 6 depends on 5
- Phase 5 depends on 4
- Phase 4 depends on 3
- Phase 3 depends on 2.5
- Phase 2.5 depends on 2
- Phase 2 depends on 1

To rollback to Phase N: rollback all phases > N in reverse order.

---

## Success Criteria

### Phase Completion Checklist

- [ ] **Phase 1**: ApplicationState has selection state, display_mode property works, validation warns
- [ ] **Phase 2**: TrackingPointsPanel updates ApplicationState on user input, Qt signal timing fixed
- [ ] **Phase 2.5**: Comprehensive audit complete, all affected locations documented
- [ ] **Phase 3**: CurveViewWidget.display_mode has deprecation wrapper, widget fields sync
- [ ] **Phase 4**: MultiCurveManager uses ApplicationState, backward-compat properties added
- [ ] **Phase 5**: Controllers use ApplicationState, synchronization loop removed, edge cases handled
- [ ] **Phase 6**: All tests updated and passing, edge case tests added
- [ ] **Phase 7**: Documentation complete, session persistence working
- [ ] **Phase 8**: All backward compatibility removed, zero deprecations, clean codebase

### Final Verification

**Run these commands to verify complete success**:

1. **Type checking** (0 errors):
   ```bash
   ./bpr --errors-only
   ```

2. **All tests pass** (2105+ tests):
   ```bash
   .venv/bin/python3 -m pytest tests/ -v
   ```

3. **Zero deprecation warnings** (after Phase 8):
   ```bash
   .venv/bin/python3 -m pytest tests/ -W error::DeprecationWarning
   ```

4. **Manual test - The original bug is fixed**:
   ```bash
   .venv/bin/python3 -c "
   from PySide6.QtWidgets import QApplication
   import sys
   from ui.main_window import MainWindow
   from stores.application_state import get_application_state, reset_application_state
   from core.models import CurvePoint

   app = QApplication(sys.argv)
   reset_application_state()
   window = MainWindow()
   app_state = get_application_state()

   # Simulate the exact bug scenario
   window.tracking_panel.set_tracked_data({
       'Track1': [CurvePoint(1, 10, 20)],
       'Track2': [CurvePoint(1, 30, 40)]
   })

   # User selects TWO curves
   window.tracking_panel.set_selected_points(['Track1', 'Track2'])

   # Verify BOTH curves will render
   from rendering.render_state import RenderState
   state = RenderState.compute(window.curve_widget)

   assert 'Track1' in state.visible_curves, 'Track1 not visible!'
   assert 'Track2' in state.visible_curves, 'Track2 not visible!'
   assert len(state.visible_curves) == 2, f'Expected 2 curves, got {len(state.visible_curves)}'

   print('✅ BUG FIXED: Selecting two curves now shows BOTH curves!')
   print(f'   display_mode: {app_state.display_mode}')
   print(f'   selected_curves: {app_state.get_selected_curves()}')
   print(f'   visible_curves: {state.visible_curves}')
   "
   ```

5. **Old API patterns fail** (after Phase 8):
   ```bash
   .venv/bin/python3 -c "
   from ui.curve_view_widget import CurveViewWidget
   from core.display_mode import DisplayMode
   widget = CurveViewWidget()
   try:
       widget.display_mode = DisplayMode.ALL_VISIBLE
       print('❌ FAIL: Old API still works')
       exit(1)
   except AttributeError:
       print('✅ PASS: Old API correctly removed')
   "
   ```

---

## Summary

This revised refactoring plan provides step-by-step instructions to implement the centralized selection state architecture that eliminates synchronization bugs.

### Key Changes from Original Plan

1. ✅ **Phase 2.5 added** - Comprehensive audit before breaking changes
2. ✅ **Phase 3 revised** - Deprecation wrapper instead of immediate removal
3. ✅ **Phase 4 enhanced** - Backward-compatibility properties for smooth migration
4. ✅ **Phase 5 improved** - Removes redundant updates, handles edge cases
5. ✅ **Phase 6 expanded** - Complete edge case test coverage
6. ✅ **Phase 7 enhanced** - Session persistence and batch mode docs
7. ✅ **Phase 8 added** - Final cleanup removes all backward compatibility

### Critical Fixes Incorporated

1. **Phase ordering bug** - Deprecation period prevents broken intermediate states
2. **Widget field sync** - Updates selected_curve_names and selected_curves_ordered
3. **Comprehensive audit** - Phase 2.5 finds all affected code before changes
4. **Validation** - Permissive validation allows init before load
5. **Redundant updates** - Controller doesn't re-update ApplicationState
6. **Backward compatibility** - Properties and wrappers for gradual migration
7. **Edge case handling** - All scenarios covered and tested
8. **Session persistence** - Selection state survives restart

### Benefits

- ✅ Fixes multi-curve selection bug
- ✅ Eliminates race conditions
- ✅ Prevents future synchronization bugs
- ✅ Cleaner, more maintainable architecture
- ✅ Smooth migration path with backward compatibility
- ✅ Complete test coverage of edge cases
- ✅ Clean final state with no backward-compat cruft

---

**Ready to implement!** Follow each phase sequentially, verifying at each step.

---

**Done!** Return to [Overview](00_OVERVIEW.md) or review any phase as needed.

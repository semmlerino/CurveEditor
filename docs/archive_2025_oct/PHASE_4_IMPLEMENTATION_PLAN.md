# Phase 4: `__default__` Cleanup - Detailed Implementation Plan

**Date**: 2025-10-05
**Status**: Phase 1 Complete - BLOCKED on ApplicationState API gaps
**Updated**: 2025-10-05 (Added Phase 0 - ApplicationState Enhancement)
**Related**: PHASE_4_DEFAULT_CLEANUP_DEFERRED.md, Post-Implementation Review – Selection State Refactor.pdf, PHASE_4_FINDINGS_SYNTHESIS.md

---

## Executive Summary

Phase 4 aims to remove `__default__` backward-compatibility code by first deprecating CurveDataStore in favor of ApplicationState as the single source of truth.

**CRITICAL UPDATE**: Phase 1 analysis revealed that **ApplicationState lacks essential point manipulation methods** required for migration. A new **Phase 0** has been added to enhance ApplicationState API before proceeding with deprecation.

**Revised Timeline**: 5-8 days (vs original 3-4 days)
**Revised Phases**: 6 phases (was 5) - Phase 0 added as prerequisite

This plan uses specialized agents for parallel analysis, sequential refactoring, and comprehensive validation.

---

## Current State Assessment (October 2025)

### CurveDataStore Dependencies

**Production Imports** (3 files):
- `ui/main_window.py:58` - Direct import + `_curve_store` attribute
- `ui/controllers/action_handler_controller.py:48` - Import for data retrieval
- `tests/test_curve_data_store.py:10` - Test file

**Active Usage** (51 `get_curve_store()` calls):
- `ui/controllers/curve_view/curve_data_facade.py` - Data manipulation methods
- `ui/controllers/curve_view/state_sync_controller.py` - Signal subscriptions + syncing
- `ui/controllers/multi_point_tracking_controller.py` - Selection operations
- `ui/main_window.py` - Multiple references throughout

**Signal Connections**:
- `data_changed`, `point_added`, `point_updated`, `point_removed`
- `point_status_changed`, `selection_changed`
- All connected in `state_sync_controller.py`

### `__default__` Dependencies

**Production Files** (6 locations):

1. **ui/state_manager.py:262**
   - Fallback in `_get_curve_name_for_selection()`
   - Returns `"__default__"` when no active curve

2. **ui/curve_view_widget.py:311-338**
   - Backward compatibility syncing in `selected_indices` property
   - 27 lines of sync logic

3. **ui/curve_view_widget.py:359-367**
   - Filters `__default__` from `curves_data` property
   - 3 filter locations

4. **ui/controllers/multi_point_tracking_controller.py:82-88, 100-102, 1090**
   - Filters `__default__` from tracked curves
   - 3 filter locations

5. **ui/controllers/curve_view/curve_data_facade.py:65-76**
   - Documents `__default__` usage
   - Uses for single-curve operations

6. **ui/controllers/curve_view/state_sync_controller.py:217-231**
   - Critical syncing of ApplicationState `__default__` back to CurveDataStore
   - Maintains backward compatibility

7. **rendering/render_state.py:140**
   - Comment only (documentation)

**Test Files** (4 files):
- `tests/test_ui_service.py` - Lines 393-394, 457-458
- `tests/test_shortcut_commands.py` - Lines 172-173, 197-198, 579-580
- `tests/test_tracking_direction_undo.py` - Unknown locations
- `tests/test_integration_edge_cases.py` - 9 locations (lines 179, 211, 247, 283, 320, 380, 425, 496, 557)

---

## Agent Orchestration Strategy

### Phase 0: ApplicationState API Enhancement (PREREQUISITE - NEW)

**Status**: ✅ COMPLETE (Phase 1 analysis identified this requirement)
**Duration**: 1-2 days
**Risk**: LOW (additive changes only)
**Agent**: python-implementation-specialist

**Rationale**: Phase 1 analysis by python-code-reviewer revealed that ApplicationState lacks essential point manipulation methods actively used in production. Migration cannot proceed without these APIs.

**Missing P0 Methods (CRITICAL - Blocks migration)**:
- `add_point(curve_name, point)` → Used in CurveDataFacade, 4 test files
- `remove_point(curve_name, index)` → Used in CurveDataFacade, 2 test files
- `set_point_status(curve_name, index, status)` → Used in SetPointStatusCommand (undo/redo), CurveViewWidget, 4 test files

**Missing P1 Methods (HIGH VALUE - Heavy usage)**:
- `select_all(curve_name=None)` → MenuBar, ActionHandler, ShortcutCommands, 7+ test files
- `select_range(curve_name, start, end)` → CurveViewWidget rubber-band selection

**Implementation Details**: See PHASE_4_FINDINGS_SYNTHESIS.md Section 6.1 and 6.2

---

**Agent Prompt**:
```
Add P0 and P1 methods to ApplicationState for CurveDataStore deprecation.

CONTEXT:
Phase 1 analysis revealed ApplicationState lacks point manipulation methods
required for CurveDataStore migration. These methods are actively used in
production and must be added before migration can proceed.

FILE TO MODIFY:
- stores/application_state.py

REQUIRED P0 METHODS (Critical - Blocks Migration):

1. add_point(curve_name: str, point: CurvePoint) -> int
   - Append point to curve
   - Return index of added point
   - Emit curves_changed signal
   - Handle empty curve case

2. remove_point(curve_name: str, index: int) -> bool
   - Remove point at index
   - Update selection indices (shift down after removed index)
   - Emit curves_changed signal
   - Return True if removed, False if invalid

3. set_point_status(curve_name: str, index: int, status: str | PointStatus) -> bool
   - Change point status (NORMAL, KEYFRAME, ENDFRAME, etc.)
   - Handle both string and PointStatus enum
   - Emit curves_changed signal
   - Return True if changed, False if invalid

REQUIRED P1 METHODS (High Value - Improves Ergonomics):

4. select_all(curve_name: str | None = None) -> None
   - Select all points in curve
   - Default to active_curve if curve_name is None
   - Use existing set_selection() method

5. select_range(curve_name: str, start: int, end: int) -> None
   - Select range of points (inclusive)
   - Clamp to valid indices
   - Use existing set_selection() method

IMPLEMENTATION REQUIREMENTS:
- Maintain thread safety (use _assert_main_thread())
- Follow existing ApplicationState patterns
- Emit appropriate signals (curves_changed for data, selection_changed for selection)
- Handle edge cases (empty curves, invalid indices)
- Update selection indices correctly in remove_point()
- Type hints for all parameters and return values
- Comprehensive docstrings

TESTING REQUIREMENTS:
- Create tests/test_application_state_enhancements.py
- Test all P0 and P1 methods
- Edge cases: empty curves, invalid indices, None curve_name
- Signal emission verification
- Selection index shifting in remove_point()
- Type compatibility (PointStatus enum vs string)

EXIT CRITERIA:
- All 5 methods implemented with docstrings
- All methods have comprehensive tests
- All existing 2274+ tests still passing
- 0 basedpyright errors (run ./bpr)
- Code review ready

DELIVERABLE: Enhanced ApplicationState with 5 new methods + comprehensive tests
```

**Expected Output**:
- Enhanced `stores/application_state.py` with 5 new methods
- New test file `tests/test_application_state_enhancements.py`
- All existing tests still passing (2274+)
- 0 type errors

---

### Phase 1: Dependency Analysis (PARALLEL - Read-only) ✅ COMPLETE

**Agent 1: deep-debugger**

**Prompt**:
```
Analyze CurveDataStore dependencies and migration risks to ApplicationState.

SCOPE:
- Map all 51 get_curve_store() calls across codebase
- Trace signal chains: data_changed, point_added, point_updated, point_removed, point_status_changed, selection_changed
- Identify circular dependencies between CurveDataStore ↔ ApplicationState
- Find risky patterns (e.g., nested signal emissions, race conditions)

FILES TO ANALYZE:
- stores/curve_data_store.py (implementation)
- ui/controllers/curve_view/curve_data_facade.py (heavy user)
- ui/controllers/curve_view/state_sync_controller.py (signal orchestration)
- ui/controllers/multi_point_tracking_controller.py (selection logic)
- ui/main_window.py (central orchestrator)

DELIVERABLE:
- Complete dependency map (call graph)
- Signal chain diagram (which signals trigger which updates)
- Risk assessment (high/medium/low for each migration point)
- Recommended migration order (least risky → most risky)
```

**Expected Output**:
- Dependency graph showing all CurveDataStore references
- Signal flow diagram
- Risk matrix for migration points
- Ordered migration sequence

---

**Agent 2: python-code-reviewer**

**Prompt**:
```
Review ApplicationState API completeness for CurveDataStore deprecation.

COMPARE:
- stores/curve_data_store.py (legacy API)
- stores/application_state.py (target API)

ANALYSIS:
1. Feature parity check - does ApplicationState support all CurveDataStore operations?
2. Signal compatibility - are signal names/signatures compatible?
3. Missing features - what needs to be added to ApplicationState?
4. Breaking changes - what behavior differs between the two?
5. Performance implications - any performance regressions expected?

SPECIFIC METHODS TO VERIFY:
- get_data() → get_curve_data(curve_name)
- set_data() → set_curve_data(curve_name, data)
- add_point(), update_point(), remove_point() → check equivalents
- select(), deselect(), clear_selection() → selection API
- All signals: data_changed, point_added, etc.

DELIVERABLE:
- Feature gap analysis
- API migration table (old method → new method)
- Recommended ApplicationState enhancements (if any)
- Breaking change warnings
```

**Expected Output**:
- API compatibility matrix
- Feature gap list
- Migration mapping table
- Risk warnings for breaking changes

---

**Execution**: Launch both agents in single message (parallel)

**Synthesis**: Combine outputs to create comprehensive risk assessment before proceeding

---

### Phase 2: Migration Design (SEQUENTIAL)

**Agent: python-expert-architect**

**Prompt**:
```
Design CurveDataStore → ApplicationState migration strategy.

CONTEXT:
[Paste synthesized findings from Phase 1 agents]

REQUIREMENTS:
1. Zero-downtime migration (all tests must pass at every step)
2. Preserve all signal subscriptions and reactivity
3. Maintain backward compatibility during migration
4. Remove __default__ special case as final step

DESIGN DELIVERABLES:

1. **Migration Sequence**:
   - Which files to migrate in which order?
   - Dependencies between migration steps
   - Rollback points if issues found

2. **Signal Migration Strategy**:
   - How to transition signal subscriptions?
   - Avoid signal storms during transition
   - Batch operations where appropriate

3. **__default__ Removal Approach**:
   - When to remove (after which migration step?)
   - How to handle single-curve workflows?
   - New curve naming convention (if needed)

4. **Testing Strategy**:
   - Unit tests per migration step
   - Integration tests for signal chains
   - Full regression suite timing

5. **Rollback Plan**:
   - How to revert if critical issues found?
   - Git branch strategy
   - Commit granularity

DESIGN CONSTRAINTS:
- Must maintain 100% test pass rate (2274+ tests)
- No performance regressions
- Type safety preserved (0 basedpyright errors)
- Thread safety maintained

DELIVERABLE: Detailed migration architecture document
```

**Expected Output**:
- Step-by-step migration sequence
- Signal transition strategy
- Testing checkpoints
- Rollback procedures
- Code examples for complex transitions

---

### Phase 3: CurveDataStore Deprecation (SEQUENTIAL)

#### Step 3.1: Core Refactoring

**Agent: code-refactoring-expert**

**Prompt**:
```
Refactor CurveDataStore usage to ApplicationState following architecture design.

CONTEXT:
[Paste architecture design from Phase 2]

REFACTORING TASKS:

1. **ui/controllers/curve_view/curve_data_facade.py**
   - Replace: self._curve_store.set_data(data)
   - With: self._app_state.set_curve_data(curve_name, data)
   - Update: add_point(), update_point(), remove_point() methods
   - Maintain: Same external API (facade pattern)

2. **ui/controllers/curve_view/state_sync_controller.py**
   - Replace: self._curve_store.data_changed.connect(...)
   - With: self._app_state.curves_changed.connect(...)
   - Update all 6 signal subscriptions
   - Remove: __default__ syncing logic (lines 217-231)

3. **ui/controllers/multi_point_tracking_controller.py**
   - Replace: self.main_window.curve_widget._curve_store.select(i)
   - With: Direct ApplicationState selection API
   - Remove: __default__ filtering (lines 82-88, 100-102, 1090)

4. **ui/controllers/action_handler_controller.py**
   - Replace: self._curve_store.get_data()
   - With: ApplicationState data retrieval
   - Remove: _curve_store attribute and import

5. **ui/main_window.py**
   - Remove: self._curve_store attribute (line 217)
   - Remove: get_curve_store() method (lines 559-562)
   - Update: All _curve_store references to ApplicationState
   - Remove: CurveDataStore import (line 58)

REFACTORING PRINCIPLES:
- Preserve exact external behavior
- Maintain all signal emissions
- Keep type safety (update type hints)
- Use batch operations where multiple changes occur
- Add comments explaining ApplicationState usage

DELIVERABLE: Refactored files with preserved functionality
```

**Expected Output**:
- 5 refactored files
- ApplicationState-based implementations
- Preserved external APIs
- Updated type hints

---

#### Step 3.2: `__default__` Removal

**Agent: python-implementation-specialist**

**Prompt**:
```
Remove __default__ backward-compatibility code after CurveDataStore deprecation.

CONTEXT:
CurveDataStore has been fully deprecated. All code now uses ApplicationState.

REMOVAL TASKS:

1. **ui/state_manager.py:262**
   ```python
   # BEFORE:
   def _get_curve_name_for_selection(self) -> str:
       if self._active_timeline_point:
           return self._active_timeline_point
       if self._app_state.active_curve:
           return self._app_state.active_curve
       return "__default__"  # ← DELETE

   # AFTER:
   def _get_curve_name_for_selection(self) -> str | None:
       if self._active_timeline_point:
           return self._active_timeline_point
       if self._app_state.active_curve:
           return self._app_state.active_curve
       return None  # Or raise exception
   ```

2. **ui/curve_view_widget.py:311-338**
   - Delete entire __default__ syncing block in selected_indices setter
   - 27 lines removed

3. **ui/curve_view_widget.py:359-367**
   - Remove __default__ filtering from curves_data property
   - Simplify to just return ApplicationState data

4. **rendering/render_state.py:140**
   - Remove comment about __default__ filtering
   - Documentation cleanup only

5. **Test Files** (4 files):
   - tests/test_ui_service.py (lines 393-394, 457-458)
   - tests/test_shortcut_commands.py (lines 172-173, 197-198, 579-580)
   - tests/test_tracking_direction_undo.py
   - tests/test_integration_edge_cases.py (9 locations)

   Replace "__default__" with explicit curve names like "TestCurve"

VERIFICATION:
After removal, search for residual __default__ references:
grep -r "__default__" --include="*.py" . | grep -v ".pyc"

Should return ZERO production code matches (only in this documentation)

DELIVERABLE: Clean codebase with zero __default__ references
```

**Expected Output**:
- Updated state_manager.py with None fallback
- Cleaned curve_view_widget.py (27 lines removed)
- Updated 4 test files
- Verification of zero __default__ references

---

### Phase 4: Cleanup & Validation (PARALLEL)

**Agent 1: test-development-master**

**Prompt**:
```
Update test suite after CurveDataStore deprecation and __default__ removal.

TASKS:

1. **Migrate test_curve_data_store.py**:
   - Option A: Delete file entirely (CurveDataStore deprecated)
   - Option B: Convert to test ApplicationState features
   - Recommended: Option A (clean break)

2. **Update 4 __default__ test files**:
   - tests/test_ui_service.py
   - tests/test_shortcut_commands.py
   - tests/test_tracking_direction_undo.py
   - tests/test_integration_edge_cases.py

   Replace "__default__" with explicit curve names:
   - Use "TestCurve" or "pp56_TM_138G" (realistic names)
   - Update assertions to reference new names
   - Ensure tests still validate same behavior

3. **Run full test suite**:
   uv run pytest tests/ -v

   Target: 2274+ tests passing (100% pass rate)

4. **Coverage verification**:
   - Ensure ApplicationState coverage maintained
   - Verify no regression in test coverage percentage
   - Add tests for edge cases if gaps found

DELIVERABLE:
- Updated/removed test files
- Test suite execution report
- Coverage report
- List of any failing tests with root cause analysis
```

**Expected Output**:
- Test migration complete
- Full test suite passing
- Coverage report
- Failure analysis (if any)

---

**Agent 2: type-system-expert**

**Prompt**:
```
Fix type errors after CurveDataStore removal and __default__ cleanup.

SCOPE:
Run basedpyright and fix all new type errors introduced by refactoring.

EXPECTED ISSUES:

1. **Return type changes**:
   - _get_curve_name_for_selection() now returns str | None
   - Update all callers to handle None case

2. **Missing CurveDataStore types**:
   - Remove CurveDataStore type annotations
   - Replace with ApplicationState types

3. **Protocol compliance**:
   - Verify all protocols still satisfied
   - Update protocol definitions if needed

4. **Optional curve names**:
   - Handle None curve names gracefully
   - Add proper type guards

EXECUTION:
./bpr --errors-only

Target: 0 production errors (maintain current state)

DELIVERABLE:
- All type errors fixed
- Type annotations updated
- Protocol compliance verified
- basedpyright report showing 0 errors
```

**Expected Output**:
- Type-safe codebase
- Updated type hints
- 0 basedpyright errors
- Protocol compliance verified

---

**Agent 3: python-code-reviewer**

**Prompt**:
```
Final review of Phase 4 cleanup - verify complete removal of legacy code.

VERIFICATION CHECKLIST:

1. **CurveDataStore References**:
   - ✓ Zero imports in production code
   - ✓ Zero get_curve_store() calls
   - ✓ Zero _curve_store attributes
   - ✓ stores/__init__.py updated (removed from exports)

2. **__default__ References**:
   - ✓ Zero production code references
   - ✓ Zero test references
   - ✓ Only documentation mentions remain

3. **ApplicationState Adoption**:
   - ✓ All curve operations use ApplicationState
   - ✓ All signal subscriptions migrated
   - ✓ Batch operations used appropriately

4. **Code Quality**:
   - ✓ No dead code left behind
   - ✓ No orphaned comments
   - ✓ No TODO markers related to migration
   - ✓ Documentation updated

5. **Architecture Cleanliness**:
   - ✓ Single source of truth (ApplicationState)
   - ✓ No dual storage patterns
   - ✓ Clean signal chains
   - ✓ No circular dependencies

SEARCHES TO RUN:
- grep -r "CurveDataStore" --include="*.py" . | grep -v test | grep -v ".pyc"
- grep -r "__default__" --include="*.py" . | grep -v ".md" | grep -v ".pyc"
- grep -r "get_curve_store" --include="*.py" .
- grep -r "_curve_store\." --include="*.py" .

DELIVERABLE:
- Final review report
- List of any remaining issues
- Architectural assessment
- Recommendation for merge
```

**Expected Output**:
- Comprehensive review report
- Verification of clean codebase
- Architectural approval
- Merge recommendation

---

**Execution**: Launch all 3 agents in single message (parallel)

---

### Phase 5: Final Integration (SEQUENTIAL)

**Manual Tasks** (Orchestrator synthesizes agent outputs):

1. **Remove CurveDataStore from exports**:
   ```python
   # stores/__init__.py
   # Remove "CurveDataStore" from __all__
   # Remove import statement
   ```

2. **Add deprecation notice**:
   ```python
   # stores/curve_data_store.py - top of file
   """
   DEPRECATED: This module is deprecated as of October 2025.
   Use stores.application_state.ApplicationState instead.

   This file is maintained for backward compatibility only and will be
   removed in a future release.
   """
   import warnings
   warnings.warn(
       "CurveDataStore is deprecated. Use ApplicationState instead.",
       DeprecationWarning,
       stacklevel=2
   )
   ```

3. **Update documentation**:
   - CLAUDE.md: Update "Legacy Stores" section
   - PHASE_4_DEFAULT_CLEANUP_DEFERRED.md: Mark as COMPLETE
   - Add PHASE_4_COMPLETION_REPORT.md

4. **Run final validation**:
   ```bash
   # Full test suite
   uv run pytest tests/ -v

   # Type check
   ./bpr

   # Linting
   uv run ruff check .

   # Search for residual references
   grep -r "CurveDataStore" --include="*.py" . | grep -v test | grep -v ".pyc" | grep -v "DEPRECATED"
   grep -r "__default__" --include="*.py" . | grep -v ".md" | grep -v ".pyc"
   ```

5. **Create commit**:
   ```bash
   git add .
   git commit -m "$(cat <<'EOF'
   refactor(cleanup): Complete Phase 4 - Remove __default__ and deprecate CurveDataStore

   Completes Phase 4 of the Selection State Refactor cleanup by deprecating
   CurveDataStore in favor of ApplicationState as the single source of truth
   and removing all __default__ backward-compatibility code.

   Changes:
   - Refactored 5 controllers to use ApplicationState directly
   - Removed __default__ fallback from state_manager.py
   - Removed __default__ syncing from curve_view_widget.py (27 lines)
   - Removed __default__ filtering from 3 controllers
   - Updated 4 test files to use explicit curve names
   - Deprecated CurveDataStore with warning
   - Removed CurveDataStore from stores/__init__.py exports

   Migration Details:
   - curve_data_facade.py: ApplicationState data operations
   - state_sync_controller.py: ApplicationState signal subscriptions
   - multi_point_tracking_controller.py: Direct ApplicationState selection
   - action_handler_controller.py: ApplicationState data retrieval
   - main_window.py: Removed _curve_store attribute

   Testing:
   ✅ All 2274+ tests passing
   ✅ 0 basedpyright errors (production)
   ✅ Zero CurveDataStore references in production code
   ✅ Zero __default__ references remaining
   ✅ 100% ApplicationState adoption

   This completes the cleanup recommendations from Post-Implementation
   Review – Selection State Refactor.pdf (Section 5, Phase 4).

   🤖 Generated with Claude Code
   Co-Authored-By: Claude <noreply@anthropic.com>
   EOF
   )"
   ```

---

## Risk Assessment

### High Risk
- **Signal chain disruption**: Migrating 6 signal subscriptions could break reactivity
  - *Mitigation*: Test after each signal migration, verify UI updates work

- **Selection state corruption**: Changing selection API could lose selections
  - *Mitigation*: Use batch operations, verify selection preserved in tests

### Medium Risk
- **None return from _get_curve_name_for_selection()**: Callers may not handle None
  - *Mitigation*: Type system will catch, add proper None checks

- **Test failures**: 4 test files using __default__ may have hard-coded assumptions
  - *Mitigation*: Update tests incrementally, run after each change

### Low Risk
- **Performance regression**: ApplicationState should be faster (already optimized)
  - *Mitigation*: Monitor test execution time

- **Documentation gaps**: Some docs may reference CurveDataStore
  - *Mitigation*: Search for all documentation references

---

## Success Criteria

✅ **Zero CurveDataStore references** in production code
✅ **Zero __default__ references** in production code
✅ **100% test pass rate** (2274+ tests)
✅ **0 basedpyright errors** (production code)
✅ **All signals working** (UI reactivity preserved)
✅ **Performance maintained** (no regressions)
✅ **Clean architecture** (single source of truth)
✅ **Documentation updated** (CLAUDE.md, completion report)

---

## Rollback Plan

If critical issues found at any stage:

1. **Immediate**: Revert last commit
   ```bash
   git reset --hard HEAD~1
   ```

2. **Run tests** to verify rollback successful:
   ```bash
   uv run pytest tests/ -v
   ```

3. **Analyze failure**:
   - Review agent outputs for missed dependencies
   - Check signal chains for broken connections
   - Verify ApplicationState API completeness

4. **Re-plan**:
   - Launch deep-debugger on specific failure
   - Update migration design
   - Retry with additional safeguards

---

## Timeline Estimate

- **Phase 1** (Parallel analysis): 30-45 minutes
- **Phase 2** (Design): 45-60 minutes
- **Phase 3** (Refactoring): 60-90 minutes
- **Phase 4** (Validation): 30-45 minutes (parallel)
- **Phase 5** (Integration): 15-30 minutes

**Total**: 3-4 hours with agent assistance

---

## Post-Completion Tasks

1. **Update PHASE_4_DEFAULT_CLEANUP_DEFERRED.md**:
   - Change status to COMPLETED
   - Add completion date
   - Link to completion report

2. **Create PHASE_4_COMPLETION_REPORT.md**:
   - Document actual vs. planned effort
   - List all changed files
   - Performance metrics (if any)
   - Lessons learned

3. **Update CLAUDE.md**:
   - Remove CurveDataStore from "Legacy Stores"
   - Update ApplicationState as sole store
   - Update import examples

4. **Close related issues** (if any GitHub issues exist)

---

## Agent Communication Template

When launching agents, use this format for consistency:

```markdown
**Agent**: [agent-name]
**Task**: [one-line description]
**Context**: [paste relevant prior findings]
**Scope**: [specific files/functions]
**Deliverable**: [expected output format]
```

This ensures all agents receive structured, actionable prompts.

---

**Last Updated**: 2025-10-05
**Status**: Ready for execution
**Next Step**: Launch Phase 1 parallel agents

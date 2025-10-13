# Phase 6: Complete Deprecation Removal Plan

**Status**: PLANNING
**Goal**: Remove ALL backward compatibility code, force migration to modern APIs

---

## Executive Summary

Remove all deprecated code introduced during Phase 3-4 migration. This is a **breaking change** that eliminates the backward compatibility layer and forces all code to use ApplicationState as the single source of truth.

### Impact Analysis

| Component | Files Affected | References | Migration Complexity |
|-----------|---------------|------------|---------------------|
| **CurveDataStore** | **15 prod + 36 tests** (including timeline_tabs.py) | 53 prod `.curve_data` refs | **CRITICAL** |
| **Indexed Assignments** | 2 prod files | 7 writes (.curve_data[idx] = ...) | **HIGH** |
| **selected_indices** | **2 prod files** | **2 setter calls** (not 40+) | **MEDIUM** |
| **StoreManager** | 1 file | ApplicationState integration needed | **HIGH** |
| **SignalConnectionManager** | 1 file | Selection sync | **HIGH** |
| **main_window.curve_view** | **5 prod files** | **15+ references** | **MEDIUM-HIGH** |
| **timeline_tabs.frame_changed** | ~3 files | ~3 references (mostly cleanup) | **LOW** |
| **should_render_curve()** | 2 files | 3 functional refs | **LOW** |
| **ui_components** | 1 file | 1 import | **TRIVIAL** |

**Total**: **25 unique prod files + 36 tests** (32+ file modifications across phases due to overlap), ~80 production references to migrate

*Note: Some files are modified in multiple phases (e.g., ui/curve_view_widget.py appears in phases 6.0, 6.1, 6.2, and 6.3; ui/main_window.py in 6.0, 6.3, 6.4; ui/timeline_tabs.py in 6.0, 6.3, 6.5), resulting in 32+ total file modifications despite only 25 unique files affected.*

---

## Phase 6 Structure

### Overview

Phase 6 is divided into 8 sequential sub-phases, executed in dependency order:

| Phase | Description | Complexity | Document |
|-------|-------------|------------|----------|
| **6.0** | Pre-Migration Validation | **CRITICAL** | [Details →](docs/phase6/PHASE_6.0_PRE_MIGRATION_VALIDATION.md) |
| **6.1** | Selected Indices Migration | **HIGH** | [Details →](docs/phase6/PHASE_6.1_SELECTED_INDICES_MIGRATION.md) |
| **6.2** | Read-Only Enforcement | **HIGH** | [Details →](docs/phase6/PHASE_6.2_READ_ONLY_ENFORCEMENT.md) |
| **6.3** | CurveDataStore Removal | **CRITICAL** | [Details →](docs/phase6/PHASE_6.3_CURVEDATASTORE_REMOVAL.md) |
| **6.4** | curve_view Removal | **MEDIUM** | [Details →](docs/phase6/PHASE_6.4_CURVE_VIEW_REMOVAL.md) |
| **6.5** | Timeline Signal Removal | **MEDIUM** | [Details →](docs/phase6/PHASE_6.5_TIMELINE_SIGNAL_REMOVAL.md) |
| **6.6** | should_render Removal | **LOW** | [Details →](docs/phase6/PHASE_6.6_SHOULD_RENDER_REMOVAL.md) |
| **6.7** | ui_components Removal | **TRIVIAL** | [Details →](docs/phase6/PHASE_6.7_UI_COMPONENTS_REMOVAL.md) |

### Quick Reference

**Phase 6.0 - Pre-Migration Validation**: Add DeprecationWarnings, run audits, collect baseline metrics
**Phase 6.1 - Selected Indices Migration**: Migrate 2 `selected_indices` setter call sites (production only)
**Phase 6.2 - Read-Only Enforcement**: Add property setters, create validation test suite
**Phase 6.3 - CurveDataStore Removal**: Remove entire CurveDataStore class (7 indexed assignments + 44 files)
**Phase 6.4 - curve_view Removal**: Remove `main_window.curve_view` alias (20 files)
**Phase 6.5 - Timeline Signal Removal**: Remove `timeline_tabs.frame_changed` (5 files)
**Phase 6.6 - should_render Removal**: Remove `should_render_curve()` (3 files)
**Phase 6.7 - ui_components Removal**: Remove `ui_components` alias (trivial)

---

## Execution Strategy

### Recommended Order

**Rationale**: Do highest-risk changes first when rollback is cleanest. If Phase 6.3 succeeds, remaining phases are mechanical.

1. ✅ **Phase 6.0** - Pre-migration validation (audits, baseline collection)
2. ✅ **Phase 6.1** - Selected indices migration (2 production call sites)
3. ✅ **Phase 6.2** - Read-only enforcement (property setters + validation tests)
4. ⚠️ **Phase 6.3** - **CRITICAL**: CurveDataStore removal (15 prod files + timeline_tabs.py)
5. ⬜ **Phase 6.4** - curve_view removal (5 prod files including batch_edit.py)
6. ⬜ **Phase 6.5** - Timeline signal removal (mostly cleanup)
7. ⬜ **Phase 6.6** - should_render removal
8. ⬜ **Phase 6.7** - ui_components removal

**Note**: Phases must run sequentially due to file overlaps (timeline_tabs.py, interaction_service.py, batch_edit.py modified in multiple phases). Parallel execution is not possible.

---

### Agent-Based Execution Strategy

**Philosophy**: Leverage specialized agents for implementation and review while maintaining pragmatic personal-app approach.

#### Implementation Agents (per Phase)

| Phase | Implementation Agent | Rationale |
|-------|---------------------|-----------|
| **6.0** | `general-purpose` | Audits, baseline collection - general tasks |
| **6.1** | `python-implementation-specialist` | Simple migration (2 call sites) |
| **6.2** | `python-implementation-specialist` + `test-development-master` | Property setters + test suite creation |
| **6.3** | `python-expert-architect` | **CRITICAL** - Complex refactor (15 files, 7 indexed writes) |
| **6.4** | `python-implementation-specialist` | Mechanical alias removal (20 files) |
| **6.5** | `python-implementation-specialist` | Simple signal removal (5 files) |
| **6.6** | `python-implementation-specialist` | Method removal (3 files) |
| **6.7** | `python-implementation-specialist` | Trivial import cleanup |

#### Review Agents (when to run)

**After Implementation (Quick Sanity Checks)**:
- Run `python-code-reviewer` after **each phase** to catch obvious issues before proceeding
- Prompt: "Review changes for Phase X.Y implementation - focus on correctness, type safety, and missed migrations"

**After Critical Phases (Comprehensive Reviews)**:
- **After Phase 6.2**: `python-code-reviewer` + `type-system-expert`
  - Verify property setters work correctly
  - Validate test suite completeness
  - Check type annotations

- **After Phase 6.3**: `python-code-reviewer` + `type-system-expert` + `test-development-master`
  - **Most important review** - CurveDataStore removal is highest risk
  - Verify all indexed assignments migrated
  - Check ApplicationState integration
  - Validate test coverage for new patterns

**Final Review (After Phase 6.7)**:
- `python-code-reviewer` + `best-practices-checker`
- Comprehensive review of entire Phase 6 migration
- Verify no deprecated code remains
- Check for cleanup opportunities

#### Review Prompts

**Quick Sanity Check** (after each phase):
```
Review Phase X.Y implementation focusing on:
1. Are all file modifications from the phase document completed?
2. Any obvious bugs or type errors?
3. Any missed migration sites?
Keep review pragmatic - this is a personal app, not enterprise-grade.
```

**Critical Phase Review** (after 6.2, 6.3):
```
Comprehensive review of Phase X.Y implementation:
1. Verify all migration patterns applied correctly
2. Check type safety and error handling
3. Validate test coverage for new patterns
4. Identify potential runtime issues
5. Verify exit criteria met
Context: Personal app - avoid over-engineering, focus on correctness.
```

**Final Review** (after 6.7):
```
Final Phase 6 migration review:
1. No deprecated code remains (grep verification)
2. All tests passing (2105/2105)
3. Type checking clean (0 errors)
4. Code quality improvements achieved
5. Any technical debt introduced?
Context: Personal app with 3DEqualizer integration.
```

#### Agent Execution Workflow

```bash
# Example: Phase 6.3 (Critical)
# 1. Implementation
[Launch python-expert-architect agent]
Prompt: "Implement Phase 6.3 CurveDataStore removal following docs/phase6/PHASE_6.3_CURVEDATASTORE_REMOVAL.md.
Execute all steps in order, verify with validation commands."

# 2. Quick Review
[Launch python-code-reviewer agent]
Prompt: "Review Phase 6.3 implementation - focus on correctness and missed migrations."

# 3. Comprehensive Review (critical phase)
[Launch python-code-reviewer + type-system-expert agents in parallel]
Prompt: "Comprehensive review of Phase 6.3 - verify ApplicationState integration,
indexed assignment migration, and test coverage."

# 4. Fix issues if found
[Re-launch python-expert-architect with specific fixes]

# 5. Validate
pytest tests/ -v
./bpr --errors-only

# 6. Commit
git commit -m "Phase 6.3: CurveDataStore removed"
```

#### Pragmatic Filtering

When reviewing agent suggestions:
- ✅ **Accept**: Correctness fixes, type safety, missed migrations
- ⚠️ **Consider**: Performance optimizations, test improvements
- ❌ **Reject**: Over-engineering (runtime debug modes, exhaustive pre-planning, enterprise patterns)

---

### Risk Mitigation

1. **Branch Strategy**:
   ```bash
   git checkout -b phase-6-backup         # Create backup before starting
   git checkout -b phase-6-dev            # Development branch
   # After each sub-phase, commit with clear message
   # If failure: git checkout phase-6-backup
   ```

2. **Incremental Commits with Reset Points**:
   ```bash
   git commit -m "Phase 6.0: Pre-migration validation complete"  # Hash: abc123
   git commit -m "Phase 6.1: Selected indices migrated"          # Hash: def456
   git commit -m "Phase 6.2: Read-only enforcement complete"     # Hash: ghi789
   git commit -m "Phase 6.3: CurveDataStore removed"             # Hash: jkl012
   # If Phase 6.4 fails: git reset --hard jkl012
   ```

3. **Test Suite**: Run validation checklist after each sub-phase

4. **Type Checking**: Maintain 0 errors throughout, compare pre/post baselines

5. **Rollback Options**:
   - **Option A**: Backup branch `git checkout phase-6-backup`
   - **Option B**: Single atomic commit `git revert <commit>`
   - **Option C**: Stacked commits with reset `git reset --hard <hash>`

---

## Breaking Changes Summary

1. **widget.curve_data is read-only property**
   - Migration: Use `app_state.set_curve_data(curve_name, data)`

2. **widget.selected_indices is read-only property**
   - Migration: Use `app_state.set_selection(curve_name, indices)`

3. **Indexed assignments no longer work** (modify copy, not source)
   - Migration: Update via ApplicationState or use batch operations

4. **No CurveDataStore signals**
   - Migration: Connect to `app_state.curves_changed` instead

5. **main_window.curve_view removed**
   - Migration: Use `main_window.curve_widget`

6. **timeline_tabs.frame_changed removed**
   - Migration: Use `state_manager.frame_changed`

---

## API Migration Guide

```python
# ❌ OLD (Phase 5) - Property assignment
widget.curve_data = new_data  # Doesn't work anyway
data = widget.curve_data  # Returns from CurveDataStore
widget._curve_store.data_changed.connect(handler)
widget.selected_indices = {0, 1, 2}  # Syncs to both stores

# ✅ NEW (Phase 6) - ApplicationState only
app_state.set_curve_data(curve_name, new_data)
data = app_state.get_curve_data(curve_name)
app_state.curves_changed.connect(handler)
app_state.set_selection(curve_name, {0, 1, 2})

# ❌ OLD (Phase 5) - Indexed assignment
widget.curve_data[idx] = (frame, x, y)  # Modifies CurveDataStore

# ❌ BROKEN (Phase 6.3+) - Indexed assignment modifies COPY
widget.curve_data[idx] = (frame, x, y)  # Modifies copy, NOT ApplicationState!

# ✅ NEW (Phase 6.3+) - Correct migration
data = list(app_state.get_curve_data(curve_name))
data[idx] = (frame, x, y)
app_state.set_curve_data(curve_name, data)

# For batch updates (drag operations):
app_state.begin_batch()
try:
    data = list(app_state.get_curve_data(curve_name))
    for idx in selected_indices:
        data[idx] = (frame, x, y)
    app_state.set_curve_data(curve_name, data)
finally:
    app_state.end_batch()  # Emits single signal
```

---

## Testing Strategy

### Phase 6.0 - Validation Baseline
- Run all audits (signal connections, indexed writes, etc.)
- Collect type checking baseline: `./bpr --errors-only > pre_phase6_types.txt`
- Verify DeprecationWarnings work

### Phase 6.2 - Validation Test Suite
- **14 tests already implemented** in `tests/test_phase6_validation.py`:
  - **6 required tests**: Read-only properties (2 with xfail), thread safety, multi-curve edge cases, FrameStore sync (1 with xfail)
  - **4 optional integration tests**: Batch signal deduplication, selection sync, undo/redo, session persistence
  - **4 agent-recommended tests**: Coverage gaps identified in code review
- Tests with `xfail` markers will automatically pass when Phase 6.2 implementation is complete

### Full Suite Validation
After each phase:
```bash
pytest tests/ -v
# Expected: 2105/2105 passing

./bpr --errors-only
# Expected: 0 errors (same as baseline)
```

---

## Rollback Plan

### Option A: Backup Branch (Recommended)
```bash
git checkout phase-6-backup
git branch -D phase-6-dev
# Manual verification, then:
git push origin phase-6-backup
```

### Option B: Single Atomic Commit
```bash
git revert <phase-6-commit-hash>
git push
```

### Option C: Stacked Commits Reset
```bash
git reset --hard <last-good-commit-hash>
git push --force-with-lease
```

### Emergency Fix Protocol
1. Immediate rollback via chosen option
2. Capture error logs and failing test output
3. Create issue with reproduction steps
4. Fix in isolated branch
5. Re-attempt with corrected approach

---

## Post-Phase 6 State

### Architecture
- **ApplicationState**: Single source of truth (no sync layer)
- **Direct Reads**: All code uses `app_state.get_curve_data(active_curve)`
- **Qt Signals**: `curves_changed`, `selection_changed`, `active_curve_changed`, etc.

### Removed Components
- ❌ **CurveDataStore** (~300 lines) - Entire backward compatibility layer
- ❌ **StateSyncController sync logic** (~150 lines) - 7 signal handlers
- ❌ **main_window.curve_view** - Alias for curve_widget
- ❌ **timeline_tabs.frame_changed** - Deprecated signal
- ❌ **should_render_curve()** - Legacy method
- ❌ **ui_components** - Deprecated alias

**Total Removed**: ~600 lines of backward compatibility code

### Remaining Components
- ✅ **ApplicationState** - Single source of truth
- ✅ **StateSyncController** - ApplicationState signal handling only
- ✅ **CurveViewWidget** - Direct ApplicationState readers
- ✅ **CommandManager** - Undo/redo system
- ✅ **RenderState** - Immutable render state snapshots

---

## Benefits of Removal

### Code Quality
- **-600 lines**: Remove backward compatibility layer
- **Simpler Architecture**: Single source of truth (no dual-store complexity)
- **Fewer Signals**: Eliminate 7 CurveDataStore signals
- **Clearer APIs**: No confusion between widget.curve_data vs ApplicationState

### Maintainability
- **No Backward Compatibility Code**: Clean, modern APIs only
- **Reduced Test Complexity**: No mocking CurveDataStore
- **Easier Debugging**: Single data flow path

---

## Decision Points

### Should We Do Phase 6?

**YES, if**:
- ✅ ApplicationState migration is complete and stable
- ✅ Team is ready to commit to modern APIs
- ✅ Validation test suite passes

**WAIT, if**:
- ⚠️ Any Phase 5 regressions remain unfixed
- ⚠️ Team lacks bandwidth for testing
- ⚠️ External dependencies still use deprecated APIs

---

## Historical Context

For detailed amendment history (October 5-6, 2025), see:
- [Amendment History](docs/phase6/AMENDMENTS_HISTORY.md) - Agent reviews, PDF assessment, audit verification

---

## Success Probability

- **Initial Planning**: 75%
- **After Agent Reviews (Oct 6)**: 90%
- **After Pragmatic Assessment (Oct 6)**: **80-85%** (realistic for personal app)
- **With Agent-Based Execution (Oct 6 - Final)**: **85-90%** (agent implementation + review)
- **Confidence**: HIGH

**Pragmatic Assessment (Personal App Context)**:
- ✅ **4 critical blockers fixed**: Step ordering, protocol ordering, DataService sync, grep patterns
- ✅ **2105 existing tests** provide comprehensive coverage (4 drag tests validate migration)
- ✅ **Simpler solutions work**: No need for visual cache pattern or enterprise features
- ✅ **Agent-based execution**: Specialized agents for implementation + multi-agent reviews
- ⚠️ **Remaining risks**: Step execution discipline, test fixture brittleness (mitigated by reviews)

**Key Success Factors**:
- Fixed step ordering (Phase 6.3: Step 2→3→4, Phase 6.4: Code→Tests→Protocols)
- Existing test suite catches regressions immediately
- DataService sync added to prevent stale exports
- Grep patterns now comprehensive (all 6 signals)
- **Agent workflow**: Implementation → Quick review → Comprehensive review (critical phases) → Validate → Commit

**Why Higher Than Agent Estimates**:
- Agents optimized for enterprise-grade software (over-engineering)
- Personal app tolerates simpler migrations
- Test coverage stronger than agents assessed
- Critical fixes applied reduce risk from 40% → 85%+
- Agent-based execution provides additional safety net with multi-phase reviews

---

## Quick Start

1. **Read Phase 6.0**: [Pre-Migration Validation →](docs/phase6/PHASE_6.0_PRE_MIGRATION_VALIDATION.md)
2. **Verify prerequisites**: Phase 5 complete, all tests passing
3. **Create backup branch**: `git checkout -b phase-6-backup`
4. **Execute phases in order**: 6.0 → 6.1 → 6.2 → 6.3 → 6.4 → 6.5 → 6.6 → 6.7
   - Use recommended **implementation agents** for each phase (see Agent-Based Execution Strategy)
   - Run **review agents** after implementation (quick sanity + comprehensive for critical phases)
5. **Validate after each phase**: Tests + type checking
6. **Commit with clear messages**: Enable surgical rollback

---

## Conclusion

Phase 6 represents the final cleanup of the ApplicationState migration, removing all backward compatibility code and establishing ApplicationState as the sole data authority. With comprehensive validation, incremental execution, agent-based implementation and review, and multiple rollback options, this migration can be executed with high confidence.

**Estimated Timeline**: 4-6 days (realistic for 25 prod files + validation + agent reviews)
**Recommended Approach**:
- Execute phases 6.0-6.3 first (high-risk) with comprehensive agent reviews
- Use specialized implementation agents per phase
- Run quick reviews after each phase, comprehensive reviews after critical phases
- Then phases 6.4-6.7 (mechanical)
**Success Probability**: 80-85% (realistic for major breaking change with agent assistance)
**Success Metrics**: All tests passing, 0 type errors, -600 lines of complexity removed, no deprecated code remaining

---

*Last Updated: October 2025*
*Phase Status: PLANNING - Ready for execution pending stakeholder approval*

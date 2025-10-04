# Phase 8: InteractionService Multi-Curve Refactor - Final Implementation Plan

**Date:** October 2025
**Status:** Planning Complete - Ready for Implementation
**Decision:** ✅ **GO - Proceed with Implementation**

---

## Executive Summary

### Project Overview

**Objective:** Refactor InteractionService to natively support multi-curve interactions, eliminating 25 duplicated methods between InteractionService and CurveViewWidget.

**Scope:** Phase 8 of 8 in the CurveViewWidget god object elimination project.

**Current State:**
- 25 methods duplicated between InteractionService (single-curve) and CurveViewWidget (multi-curve)
- 3 critical bugs (Y-flip inversion, thread safety violation, protocol duplication)
- 80% test coverage achieved (56 tests passing)
- 0 production type errors

**Proposed Solution:**
- Make InteractionService multi-curve native (match ApplicationState design)
- Introduce 3 new dataclasses (PointSearchResult, CurveSelection, SearchMode)
- Add optional `curve_name` parameter to 11 methods (backward compatible)
- Consolidate 2 duplicate protocol definitions into 1
- Fix 3 critical bugs

### Key Metrics

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| **Code Lines** | 1,662 | 1,387 | **-275 (-16.5%)** |
| **Duplicate Methods** | 25 | 0 | **-25 (-100%)** |
| **Protocol Definitions** | 2 | 1 | **-1 (-50%)** |
| **Critical Bugs** | 3 | 0 | **-3 (FIXED)** |
| **Type Errors** | 0 | 0 | **0 (maintained)** |
| **Test Coverage** | 80% | ≥80% | **Maintained** |

### Timeline

**Total Duration:** 2-3 weeks (revised from 1-2 weeks after Phase 6 validation)
**Implementation Effort:** 15-24 hours (includes 50% buffer for high-risk increments)
**Increments:** 10 (detailed in Implementation Plan)
**Critical Fixes Required:** 2-3 hours (before implementation begins)

### Recommendation

✅ **GO - Proceed with Implementation**

**Rationale:**
- Phase 4 prototype PASSED with 0 new type errors
- Architecture validated as implementable
- ROI positive (benefits significantly outweigh costs)
- 80% test coverage provides comprehensive safety net
- Incremental plan with clear rollback strategy
- Fixes 3 critical bugs affecting user experience

---

## Planning Phase Synopsis

### Phase 1: Duplication Assessment ✅

**Agent:** python-code-reviewer + type-system-expert (parallel)

**Findings:**
- **25 duplicated methods** across 6 categories:
  - Selection: 6 methods (find_point_at, select_point_by_index, clear_selection, select_all_points, select_points_in_rect, toggle_selection)
  - Manipulation: 5 methods (update_point_position, delete_selected_points, nudge_selected_points, batch_move_points, smooth_points)
  - Mouse Events: 5 methods (handle_mouse_press, handle_mouse_move, handle_mouse_release, handle_wheel_event, handle_double_click)
  - State Callbacks: 3 methods (on_data_changed, on_selection_changed, on_frame_changed)
  - History: 5 methods (add_to_history, undo_action, redo_action, save_state, restore_state)
  - View: 1 method (apply_pan_offset_y)

- **16 single-curve assumptions** in InteractionService (all calling `get_curve_data()` without curve name)

- **5 multi-curve features** only in widget:
  - Multi-curve point finding
  - Cross-curve selection with Ctrl+Click
  - Multi-curve rendering state
  - Multi-curve centering
  - Live data merging from multiple sources

- **3 critical bugs identified:**
  - **HIGH:** Y-flip direction inversion (hardcoded `-delta_y` breaks flip_y_axis=False)
  - **HIGH:** Thread safety violation (no main thread assertions)
  - **HIGH:** Protocol split (2 duplicate CurveViewProtocol definitions, 90% overlap)

- **Type safety issues:**
  - 10 unnecessary type ignores
  - Protocol mismatches between duplicates
  - Missing multi-curve type support

**Impact:** Duplication confirmed - exceeds initial estimate of 24 methods

---

### Phase 2: Test Safety Net ✅

**Agent:** test-development-master

**Findings:**
- **Before:** 45% coverage (582 statements, 321 missed)
- **After:** 80% coverage (582 statements, 115 uncovered)
- **Tests Added:** 29 new tests
- **Total Tests:** 56 InteractionService tests passing
- **Execution Time:** ~4 seconds

**Coverage Areas:**
- ✅ Mouse event handlers (press, move, release, wheel)
- ✅ Selection operations (single/multi-select, rectangular selection)
- ✅ Point manipulation (move, nudge, delete)
- ✅ History operations (add, undo, redo)
- ✅ State management callbacks

**Result:** ✅ 80% threshold met - safe to proceed with refactoring

---

### Phase 3A: Architecture Design ✅

**Agent:** python-expert-architect

**Design Decisions:**

1. **PointSearchResult** dataclass (replaces `int` return type):
   - Structured result with `index`, `curve_name`, `distance`
   - Comparison operators for backward compatibility (`>=`, `==`, `__bool__`)
   - `.found` property clearer than `idx != -1`
   - Type-safe and extensible

2. **SearchMode** type alias:
   - `Literal["active", "all_visible"]` for explicit search behavior
   - More extensible than boolean flag
   - Future-proof for additional modes

3. **CurveSelection** dataclass:
   - Mirrors ApplicationState's `dict[str, set[int]]` structure
   - Immutable for thread safety
   - `.active_selection` property for backward compatibility
   - Type-safe multi-curve selection state

4. **Optional Parameters Pattern:**
   - `curve_name: str | None = None` (defaults to active curve)
   - Backward compatible (existing calls unchanged)
   - Explicit multi-curve support when needed

5. **Protocol Consolidation:**
   - Single CurveViewProtocol in `protocols/ui.py` (authoritative)
   - `services/service_protocols.py` re-exports (no duplication)
   - Added `flip_y_axis: bool` property (critical for Y-flip fix)

6. **Thread Safety:**
   - `_assert_main_thread()` method matching ApplicationState pattern
   - Main-thread-only contract (no mutex complexity)
   - Early error detection vs silent corruption

**5 Design Gaps Addressed:**
- ✅ Comparison operators added to PointSearchResult
- ✅ CurveSelection fully specified with methods
- ✅ Spatial index mutation approach documented
- ✅ Prototype scope expanded (3 → 8-10 methods for 40% coverage)
- ✅ Test estimate updated (54% → 70-80% realistic)

**Documentation:** Complete architecture in `INTERACTIONSERVICE_MULTI_CURVE_ARCHITECTURE.md` (2,118 lines)

**User Approval:** ✅ Approved

---

### Phase 3B: Migration Strategy ✅

**Deliverable:** 10 incremental migration steps with granular checkpoints

**Principles:**
- ✅ Tests pass at every step
- ✅ Type errors = 0 at every step
- ✅ Each increment independently testable
- ✅ Simple rollback (git checkout specific files)
- ✅ Visible progress (checklist format)

**10 Increments Defined:**

| Inc | Description | Duration | Risk | Files Changed |
|-----|-------------|----------|------|---------------|
| 1 | Add Core Types | 30-45 min | LOW | core/models.py, core/type_aliases.py |
| 2 | Consolidate Protocol | 45-60 min | LOW | protocols/ui.py, service_protocols.py |
| 3 | Thread Safety | 30 min | LOW | services/interaction_service.py |
| 4 | find_point_at() | 90-120 min | MEDIUM | services/interaction_service.py, tests/ |
| 5 | Selection Methods | 60-90 min | MEDIUM | services/interaction_service.py, tests/ |
| 6 | Manipulation Methods | 60-90 min | MEDIUM | services/interaction_service.py, tests/ |
| 7 | Mouse Handlers + Y-flip | 90-120 min | HIGH | services/interaction_service.py, tests/ |
| 8 | Widget Delegation | 2-3 hours | **VERY HIGH** | ui/curve_view_widget.py, tests/ |
| 9 | State Callbacks | 45-60 min | LOW | services/interaction_service.py, tests/ |
| 10 | Cleanup & Docs | 90-120 min | LOW | All, CLAUDE.md |

**Timeline:** 1-2 weeks (10 increments × 30 min to 3 hours each)

**Detailed Plan:** See `INTERACTIONSERVICE_MULTI_CURVE_ARCHITECTURE.md` lines 900-1710

---

### Phase 4: Prototyping ✅

**Agent:** python-implementation-specialist

**Scope:** Prototype 8-10 methods (40% coverage) across all 6 categories

**Items Implemented:**

1. **Core Types:**
   - ✅ PointSearchResult dataclass (core/models.py, +50 lines)
   - ✅ CurveSelection dataclass (core/models.py, +52 lines)
   - ✅ SearchMode type alias (core/type_aliases.py, +10 lines)

2. **Methods Prototyped:**
   - ✅ _assert_main_thread() - Thread safety infrastructure
   - ✅ find_point_at() - Core search with PointSearchResult return, SearchMode parameter
   - ✅ select_point_by_index() - Optional curve_name parameter
   - ✅ update_point_position() - Optional curve_name parameter
   - ✅ handle_mouse_move() - Y-flip bug fix implemented
   - ✅ on_data_changed() - State callback with curve_name
   - ✅ apply_pan_offset_y() - Y-flip awareness

3. **Protocol Enhancement:**
   - ✅ flip_y_axis property added to CurveViewProtocol

**Validation Results:**
- ✅ **0 new type errors** introduced
- ✅ All prototypes compile cleanly (basedpyright passes)
- ✅ Backward compatibility confirmed (comparison operators work)
- ✅ Y-flip bug fix implemented correctly (`y_multiplier = -1.0 if flip_y_axis else 1.0`)
- ✅ Thread safety pattern matches ApplicationState

**Minor Finding:**
- Spatial index mutation hack in `find_point_at()` "all_visible" mode
- Workaround: Temporarily mutates `view.curve_data` for SpatialIndex compatibility
- Recommendation: Update SpatialIndex API to accept `curve_data` parameter (cleaner)
- **Not a blocker** - works correctly, just not ideal style

**Decision Gate Result:** ✅ **PASS**
- All 6 success criteria met
- No architecture blockers discovered
- Ready to proceed to full implementation

**Files Modified:**
- core/models.py: +102 lines
- core/type_aliases.py: +10 lines
- services/interaction_service.py: +145 lines (prototype methods)
- services/service_protocols.py: +1 line

---

## ROI Analysis

### Benefits (What We Gain)

#### 1. Code Reduction
- **275 lines removed** (16.5% reduction in combined InteractionService + CurveViewWidget)
- Less code to maintain
- Fewer potential bugs
- Faster developer onboarding

**Value:** Ongoing maintenance cost reduction

#### 2. Eliminate Duplication (25 Methods)
- **Single source of truth** for all interaction logic
- Bug fixes require 1 update (not 2)
- Consistent behavior guaranteed across single/multi-curve modes
- Reduced test maintenance burden

**Value:** 50% reduction in interaction method maintenance

#### 3. Fix 3 Critical Bugs

**Bug #1: Y-Flip Direction Inversion (HIGH)**
- **Impact:** Users dragging points see incorrect direction when `flip_y_axis=False`
- **Fix:** Conditional Y-multiplier based on view setting
- **Value:** Correct user experience for tracking data workflows

**Bug #2: Thread Safety Violation (HIGH)**
- **Impact:** Potential race conditions if accessed from background threads
- **Fix:** `_assert_main_thread()` assertions throughout
- **Value:** Early error detection, prevents silent data corruption

**Bug #3: Protocol Duplication (HIGH)**
- **Impact:** 117 lines duplicated, protocols diverging over time
- **Fix:** Single authoritative protocol, re-export pattern
- **Value:** Type safety, easier maintenance, clear contracts

#### 4. Multi-Curve Native Architecture
- **Future-proof:** Matches ApplicationState's `dict[str, CurveDataList]` design
- **Scalable:** Handles N curves without modification
- **Enables Advanced Features:**
  - Insert Track (3DEqualizer-style gap filling)
  - Cross-curve operations
  - Multi-curve selection/manipulation
  - Per-curve visibility controls

**Value:** Foundation for future enhancements

#### 5. Improved Maintainability
- **Clear responsibility boundaries:** InteractionService = authoritative
- **Type-safe interfaces:** 0 type errors maintained
- **Comprehensive tests:** 80% coverage, 56+ passing tests
- **Protocol-based design:** Loose coupling, easier testing

**Value:** Faster feature development, easier debugging

---

### Costs (What We Invest)

#### 1. Implementation Time
**Total: 15-24 hours over 2-3 weeks** (revised from 10-16 hours after Phase 6 validation)

**Breakdown:**
- **Critical Fixes:** 2-3 hours (CurveSelection, SpatialIndex, Commands - BEFORE implementation)
- Increments 1-3: 2-3 hours (infrastructure - low risk)
- Increments 4-7: 8-12 hours (core methods - medium/high risk, 50% buffer added)
- Increment 8: 4-6 hours (widget delegation - **highest risk**, split into sub-increments)
- Increments 9-10: 2-3 hours (cleanup, docs - low risk)

#### 2. Test Updates
**40-45 tests affected (70-80% of suite)**

**Categories:**
- **No changes:** 11-16 tests (use defaults, no API changes)
- **Minor updates:** 25-30 tests (add `.index` property access, update comparisons)
- **Y-coordinate fixes:** 10 tests (update expectations for corrected Y-flip behavior)
- **New tests:** 5-8 tests (multi-curve feature validation)

**Effort:** Included in increment timelines above

#### 3. Risk Exposure

**Increment 8 (Widget Delegation) - VERY HIGH RISK**
- Removes ~450 lines of CurveViewWidget logic
- Replaces with service delegation
- Affects 20 tests
- Requires extensive manual testing

**Mitigation:**
- Incremental approach (test after each method)
- Backup old methods as deprecated
- Clear rollback plan (git checkout)
- Manual testing checklist (single-curve, multi-curve, all mouse interactions)

#### 4. Opportunity Cost
**1-2 weeks not spent on:**
- New features
- Other refactorings
- Bug fixes

**Justification:** This refactor is foundational for future enhancements (Insert Track, advanced multi-curve features)

---

### Break-Even Analysis

**One-Time Costs:**
- Implementation: 10-16 hours
- Test updates: Included in implementation

**Ongoing Savings:**
- **30% faster bug fixes** (update 1 place instead of 2)
- **Easier feature additions** (single-curve + multi-curve supported automatically)
- **Reduced cognitive load** (no duplication to track)

**Break-Even Point:**
- After ~2-3 bug fixes in interaction methods
- Or after 1 new interaction feature
- Expected: **Within 1-2 months**

**Long-Term ROI:** POSITIVE
- Cumulative savings increase over time
- Foundation for advanced features that would be difficult without this refactor

---

### ROI Summary

| Factor | Assessment |
|--------|------------|
| **Code Quality** | ✅ Significant improvement (-275 lines, -25 duplicates) |
| **Bug Fixes** | ✅ 3 critical bugs fixed |
| **Maintainability** | ✅ Major improvement (single source of truth) |
| **Future-Proofing** | ✅ Multi-curve native enables advanced features |
| **Time Investment** | ⚠️ Moderate (1-2 weeks) |
| **Risk** | ⚠️ Manageable (incremental, rollback plan) |
| **Break-Even** | ✅ Fast (1-2 months) |

**Overall ROI:** ✅ **POSITIVE - Benefits significantly outweigh costs**

---

## Implementation Plan

### Overview

**10 Incremental Steps** over **1-2 weeks** (10-16 hours total)

**Strategy:**
- Start with non-breaking infrastructure (Increments 1-3)
- Gradually extend methods with backward-compatible parameters (Increments 4-7)
- High-risk widget delegation in controlled increment (Increment 8)
- Cleanup and validation (Increments 9-10)

**Validation at Every Step:**
```bash
# After EACH increment:
./bpr --errors-only          # 0 type errors
uv run pytest tests/ -x -q   # All tests pass
git commit                    # Atomic checkpoint
```

---

### Week 1: Foundation & Core Methods

#### Increment 1: Add Core Types (30-45 min) - LOW RISK ✅ COMPLETE
**Files:** core/models.py, core/type_aliases.py, core/spatial_index.py
**Changes:** +120 lines (types), Critical Fix #2 applied
**Commit:** Included in Increment 2 commit

- ✅ Add PointSearchResult dataclass
- ✅ Add CurveSelection dataclass (WITH deep copy fix)
- ✅ Add SearchMode type alias
- ✅ **BONUS:** Applied Critical Fix #2 (SpatialIndex API updated to accept curve_data parameter)

**Success:** ✅ Types compile, importable, 0 behavior changes, 56/56 tests passing

---

#### Increment 2: Consolidate Protocol (45-60 min) - LOW RISK ✅ COMPLETE
**Files:** services/service_protocols.py
**Changes:** -120 lines (removed duplicate)
**Commit:** refactor(phase8-inc2): Consolidate CurveViewProtocol

- ✅ No enhancements needed (protocols/ui.py already complete)
- ✅ Update service_protocols.py to re-export from protocols.ui
- ✅ Remove duplicate 120-line protocol definition
- ✅ Backward compatibility maintained (7 files importing still work)

**Success:** ✅ 0 type errors, single protocol definition, re-export works, 56/56 tests passing

---

#### Increment 3: Thread Safety (30 min) - LOW RISK ✅ COMPLETE
**Files:** services/interaction_service.py
**Changes:** Already done from Phase 4 prototyping
**Status:** Pre-existing implementation verified

- ✅ `_assert_main_thread()` method exists (lines 96-116)
- ✅ Matches ApplicationState pattern exactly
- ✅ Already has 6 call sites (more than planned)

**Success:** ✅ Method exists, callable, passes on main thread, verified operational

---

#### Increment 4: find_point_at() (90-120 min) - MEDIUM RISK ✅ COMPLETE
**Files:** services/interaction_service.py
**Changes:** Already done from Phase 4 prototyping
**Status:** Pre-existing implementation verified

- ✅ Return type: `int` → `PointSearchResult`
- ✅ Parameter: `mode: SearchMode = "active"`
- ✅ Thread assertion added
- ✅ "active" mode implemented (single-curve, backward compatible)
- ✅ "all_visible" mode implemented (multi-curve search)
- ✅ Backward compatibility via comparison operators

**Success:** ✅ 0 type errors, backward compatibility works, multi-curve search works, 56/56 tests passing

---

#### Increment 5: Selection Methods (60-90 min) - MEDIUM RISK ✅ COMPLETE
**Files:** services/interaction_service.py
**Changes:** +92 lines (implementations), -18 lines (refactored)
**Commit:** feat(phase8-inc5): Add curve_name parameter to selection methods (79f0b48)

Updated 3 methods with `curve_name: str | None = None` parameter:
- ✅ clear_selection()
- ✅ select_all_points()
- ✅ select_points_in_rect()
- ✅ select_point_by_index() - already done from Phase 4

Added thread assertions to all.

**Success:** ✅ All methods support curve_name, default to active curve, 56/56 tests passing

---

### Week 2: Advanced Methods & Cleanup

#### Increment 6: Manipulation Methods (60-90 min) - MEDIUM RISK ✅ COMPLETE
**Files:** services/interaction_service.py
**Changes:** +42 lines (implementations), -13 lines (refactored)
**Commit:** feat(phase8-inc6): Add curve_name parameter to manipulation methods (cf4bdf2)

Updated 2 methods with `curve_name: str | None = None` parameter:
- ✅ delete_selected_points()
- ✅ nudge_selected_points()
- ✅ update_point_position() - already done from Phase 4

**Success:** ✅ Commands track curve context, undo/redo work, 56/56 tests passing

---

#### Increment 7: Mouse Handlers + Y-flip Fix (90-120 min) - HIGH RISK
**Files:** services/interaction_service.py, tests/test_interaction_service.py
**Changes:** ~120 lines (5 handlers updated, bug fix), 8-10 test updates

Update 5 mouse event handlers:
- _handle_mouse_press_consolidated() - auto-detect multi-curve, auto-switch curves
- _handle_mouse_move_consolidated() - **Y-FLIP BUG FIX** (`y_multiplier = -1.0 if flip_y_axis else 1.0`)
- _handle_mouse_release_consolidated()
- handle_wheel_event()
- handle_double_click()

Update tests with corrected Y-coordinate expectations.

**Success:** Auto-detects multi-curve, Y-flip bug fixed, manual testing confirms

---

#### Increment 8: Widget Delegation (2-3 hours) - VERY HIGH RISK ⚠️
**Files:** ui/curve_view_widget.py, tests/test_curve_view.py, tests/test_ui_components_integration.py
**Changes:** -450 lines (removal), +50 lines (delegation), 20 test updates

**BACKUP FIRST:** `cp ui/curve_view_widget.py ui/curve_view_widget.py.backup`

- Replace mousePressEvent() logic (~90 lines) with service delegation
- Replace mouseMoveEvent() logic with service delegation
- Replace mouseReleaseEvent() logic with service delegation
- Replace wheelEvent() logic with service delegation
- Remove `_find_point_at_multi_curve()` (44 lines)
- Remove duplicate selection/manipulation logic (~300 lines)
- Update 20 tests to use service methods

**Manual Testing Required:**
- Single-curve: click, drag, zoom, pan, select
- Multi-curve: click, drag, cross-curve selection, curve switching
- Keyboard: Ctrl+click, Alt+drag, all shortcuts

**Rollback:** `cp ui/curve_view_widget.py.backup ui/curve_view_widget.py`

**Success:** All mouse interactions work, multi-curve features preserved, tests pass

---

#### Increment 9: State Callbacks (45-60 min) - LOW RISK
**Files:** services/interaction_service.py, tests/test_interaction_history.py
**Changes:** ~40 lines (3 methods updated), 2-3 test updates

Update 3 callbacks with `curve_name: str | None = None` parameter:
- on_data_changed()
- on_selection_changed()
- on_frame_changed()

Verify history methods already multi-curve via ApplicationState (no changes).

**Success:** Callbacks support curve_name, history works, tests pass

---

#### Increment 10: Cleanup & Docs (90-120 min) - LOW RISK
**Files:** services/interaction_service.py, ui/curve_view_widget.py, CLAUDE.md, docs/
**Changes:** -50 lines (dead code), +100 lines (docs)

- Remove deprecated code paths
- Update docstrings with multi-curve examples
- Update CLAUDE.md with new patterns
- Create migration guide
- Performance validation (cache hit rate, rendering speed, point queries)
- Final test suite run (all 2105+ tests)

**Success:** Code clean, documentation complete, all metrics met

---

### Validation Strategy

**After Each Increment:**
```bash
./bpr --errors-only                    # 0 errors
uv run pytest tests/ -x -q             # All pass
git add . && git commit -m "..."       # Checkpoint
```

**After Increments 4, 7, 8 (Critical):**
```bash
uv run pytest tests/ -xvs              # Full suite with verbose output
# Manual testing with real tracking data
```

**After Increment 10 (Final):**
```bash
./bpr                                  # Full type check
uv run pytest tests/ --cov=services.interaction_service --cov=ui.curve_view_widget
uv run pytest tests/test_cache_performance.py  # Performance validation
# Full manual QA pass
```

---

## Risk Assessment

### High-Risk Areas

#### 1. Increment 8: Widget Delegation (VERY HIGH RISK) ⚠️

**Risks:**
- 450 lines removed from CurveViewWidget
- 20 tests affected
- Complex mouse interaction logic
- Multi-curve selection edge cases

**Mitigation:**
- **Backup:** Copy file before starting
- **Incremental:** Replace one event handler at a time, test after each
- **Manual Testing:** Comprehensive checklist (see Increment 8)
- **Rollback Plan:** `cp .backup` or `git checkout`
- **Deprecation Option:** Keep old methods with warnings for one release cycle

**Contingency:** If issues found, revert and create parallel implementation (new methods alongside old, gradual migration)

---

#### 2. Y-Flip Bug Fix (MEDIUM RISK)

**Risks:**
- Changes drag direction for `flip_y_axis=False` workflows
- 10 tests need coordinate expectation updates
- User perception: "It worked before" (but it was wrong)

**Mitigation:**
- **Clear Documentation:** Explain this is a BUG FIX
- **Test Coverage:** Update 10 tests with correct expectations
- **Manual Testing:** Validate both `flip_y_axis=True` and `False` modes
- **User Communication:** Mention in release notes

---

#### 3. PointSearchResult Return Type Change (MEDIUM RISK)

**Risks:**
- All code using `find_point_at()` affected
- Comparison patterns need updates (`idx >= 0` → `result.index >= 0` or `result >= 0`)

**Mitigation:**
- **Backward Compatibility:** Comparison operators make most patterns work unchanged
- **Property Access:** `.index` provides int when needed
- **Test Coverage:** Validate all call sites updated
- **Type Safety:** basedpyright catches incompatibilities

---

### Low-Risk Areas

- Increments 1-3: Infrastructure (additive only, no behavior changes)
- Increment 9: State callbacks (optional parameters with defaults)
- Increment 10: Cleanup and docs (no logic changes)

---

### Rollback Strategy

**Per-Increment Rollback:**
```bash
# If Increment N fails:
git log --oneline -10              # Find last good commit
git checkout <commit> -- <files>   # Restore specific files
# OR
git reset --hard <commit>          # Reset entire repo
```

**Backup Strategy (Increment 8):**
```bash
# Before starting:
cp ui/curve_view_widget.py ui/curve_view_widget.py.backup

# If issues:
cp ui/curve_view_widget.py.backup ui/curve_view_widget.py
git checkout tests/test_curve_view.py
```

**Full Rollback (Nuclear Option):**
```bash
# If entire Phase 8 needs abort:
git checkout main              # Return to pre-Phase 8 state
git branch -D phase8/*         # Delete all phase branches
```

---

### Testing Strategy

#### Unit Testing
- **After each increment:** Run affected test files
- **Test count:** 56 existing + 5-8 new = ~64 total
- **Coverage target:** ≥80% maintained

#### Integration Testing
- **After Increments 4, 7, 8:** Full test suite (2105+ tests)
- **Focus areas:** Multi-curve operations, mouse events, commands

#### Manual Testing
- **After Increment 7:** Y-flip behavior validation
- **After Increment 8:** Comprehensive mouse interaction testing
  - Single-curve mode
  - Multi-curve mode
  - All keyboard modifiers (Ctrl, Alt, Shift)
  - All shortcuts (C, F, E, D, Delete, Numpad, etc.)

#### Performance Testing
- **After Increment 10:** Validate metrics maintained
  - Cache hit rate: 99.9%
  - Rendering speed: 47x baseline
  - Point query speed: 64.7x linear

#### Regression Testing
- **Throughout:** Ensure existing features preserved
  - Insert Track (3DEqualizer-style gap filling)
  - Cross-curve selection
  - Hover highlighting
  - Undo/redo
  - Playback

---

## Success Criteria

### Code Quality Metrics

| Metric | Target | Validation |
|--------|--------|------------|
| Lines Removed | 275 | `git diff --stat` |
| Duplicate Methods | 0 (was 25) | Manual inspection |
| Protocol Definitions | 1 (was 2) | Grep for CurveViewProtocol |
| Type Errors | 0 | `./bpr --errors-only` |

### Performance Metrics (Must Maintain)

| Metric | Target | Validation |
|--------|--------|------------|
| Cache Hit Rate | 99.9% | TransformService cache stats |
| Rendering Speed | 47x baseline | OptimizedCurveRenderer benchmarks |
| Point Query Speed | 64.7x linear | SpatialIndex query benchmarks |

### Test Coverage

| Category | Target | Validation |
|----------|--------|------------|
| Total Tests | All 2105+ passing | `uv run pytest tests/ -x` |
| InteractionService | ≥80% coverage | `pytest --cov=services.interaction_service` |
| CurveViewWidget | ≥80% coverage | `pytest --cov=ui.curve_view_widget` |
| Tests Updated | 40-45 (70-80% of suite) | Git diff count |

### Bug Fixes Validated

| Bug | Validation Method |
|-----|------------------|
| Y-flip inversion | Manual test with flip_y_axis=True/False, verify drag direction |
| Thread safety | Assertions in place, test from worker thread (expect error) |
| Protocol split | Single definition in protocols/ui.py, re-export verified |

### Functionality Preserved

- ✅ Multi-curve support works
- ✅ Insert Track (3DEqualizer-style) functional
- ✅ Cross-curve selection with Ctrl+Click
- ✅ Hover highlighting
- ✅ All keyboard shortcuts
- ✅ Undo/redo
- ✅ Playback

---

## Final Recommendation

### Decision: ✅ **GO - Proceed with Implementation**

### Rationale

1. **Architecture Validated**
   - Phase 4 prototype PASSED with 0 new type errors
   - All 10 items implemented successfully
   - No blockers discovered
   - Minor spatial index finding has workaround

2. **Comprehensive Safety Net**
   - 80% test coverage (56 tests passing)
   - Incremental plan with validation at every step
   - Clear rollback strategy per increment
   - Backup plan for high-risk Increment 8

3. **Positive ROI**
   - Benefits: 275 lines removed, 25 duplicates eliminated, 3 bugs fixed, future-proof architecture
   - Costs: 10-16 hours implementation
   - Break-even: 1-2 months
   - Long-term: Significant ongoing savings

4. **Bug Fixes Critical**
   - Y-flip inversion affects user experience (incorrect drag direction)
   - Thread safety violation risks data corruption
   - Protocol duplication hinders maintenance

5. **Foundation for Future**
   - Multi-curve native enables advanced features (Insert Track, cross-curve ops)
   - Matches ApplicationState design (consistency)
   - Scales to N curves without modification

### Conditions for Success

1. **Follow incremental plan strictly** (10 steps, no shortcuts)
2. **Run validation after EACH increment** (tests + types)
3. **Manual testing after Increments 7, 8** (mouse events, widget delegation)
4. **Performance validation at end** (cache, rendering, queries)
5. **If Increment 8 fails:** Revert, use parallel implementation strategy

### Alternative Scenarios

**DEFER if:**
- User has time constraints (< 2 weeks available)
- Production issues take priority
- Major feature deadline conflicts

**CANCEL if:**
- Fundamental architecture flaw found (none discovered)
- Prototype failed (it passed ✅)
- Alternative simpler solution exists (none identified)

**Since none of the DEFER/CANCEL conditions apply:**

## ✅ **PROCEED TO PHASE 6 (Final Validation)**

---

## Next Steps

### Phase 6: Final Validation (Parallel Agents)

Launch in parallel:
1. **python-code-reviewer:** Review final implementation plan, architecture design
2. **type-system-expert:** Verify type safety of proposed changes
3. **performance-profiler:** Assess performance impact predictions

Expected duration: 30-60 minutes

### After Phase 6: User Approval Checkpoint

User reviews:
- This implementation plan
- Agent validation findings
- ROI analysis
- Risk assessment

User decides: **PROCEED / DEFER / CANCEL**

If PROCEED → Begin Increment 1 implementation

---

**Document Version:** 1.0
**Last Updated:** October 2025
**Status:** ✅ Ready for Phase 6 Validation

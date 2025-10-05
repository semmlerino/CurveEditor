# Selection State Refactoring - Live Progress Tracker

**Last Updated**: October 2025 - Phases 1-5 Complete
**Status**: 🟡 IN PROGRESS (62.5% Complete)
**Current Phase**: Phase 6 Ready

---

## 🎯 Quick Summary

**Goal**: Fix multi-curve selection bug by centralizing selection state in ApplicationState.

**Root Cause**: Selection state fragmented across 3 locations with manual sync → forgot to update `display_mode` when setting `selected_curve_names`.

**Solution**: Make `display_mode` a computed property from `ApplicationState._selected_curves` and `._show_all_curves`.

**Key Fix**: ✅ FIXED - Removed synchronization loop at `multi_point_tracking_controller.py:357` that caused race condition.

---

## 📊 Overall Progress

- [x] Phase 1: Add Selection State to ApplicationState ✅
- [x] Phase 2: Update TrackingPointsPanel ✅
- [x] Phase 2.5: Comprehensive Migration Audit ✅
- [x] Phase 3: Update CurveViewWidget (with deprecation) ✅
- [x] Phase 4: Update MultiCurveManager ✅
- [x] Phase 5: Update Controllers ✅
- [ ] Phase 6: Update Tests
- [ ] Phase 7: Documentation & Session Persistence
- [ ] Phase 8: Final Cleanup (remove backward compatibility)

**Progress**: 5/8 phases complete (62.5%) - Core functionality complete, testing/cleanup remaining

---

## 🚀 Phase 1: ApplicationState - Add Selection State

**Status**: ✅ Complete

### Changes
- [x] Add `_selected_curves: set[str]` field
- [x] Add `_show_all_curves: bool` field
- [x] Add `selection_state_changed: Signal` declaration
- [x] Add `get_selected_curves()` method
- [x] Add `set_selected_curves()` method with validation
- [x] Add `get_show_all_curves()` method
- [x] Add `set_show_all_curves()` method
- [x] Add computed `display_mode` property
- [x] Add `from core.display_mode import DisplayMode` import

### Verification
- [x] Type check passes: `./bpr stores/application_state.py` - 0 errors
- [x] Display mode computation test passes
- [x] Validation filtering works correctly

### Notes
- **IMPROVED**: Changed to fail-fast filtering (removes invalid curves immediately)
- **IMPROVED**: Added empty string validation (ValueError on empty/whitespace names)
- **IMPROVED**: Added batch mode documentation with usage examples
- `display_mode` property includes thread safety assertion
- Batch mode: state visible immediately, signals deferred

---

## 🚀 Phase 2: TrackingPointsPanel - Connect to ApplicationState

**Status**: ✅ Complete

### Changes
- [x] Add `self._app_state` reference in `__init__`
- [x] Subscribe to `selection_state_changed` signal
- [x] Update `_on_selection_changed()` to call `app_state.set_selected_curves()`
- [x] Update `_on_display_mode_checkbox_toggled()` to call `app_state.set_show_all_curves()`
- [x] Add `_on_app_state_changed()` handler with recursion counter

### Verification
- [x] Type check passes: `./bpr ui/tracking_points_panel.py` - 0 errors
- [x] Panel selection updates ApplicationState
- [x] Checkbox updates ApplicationState

### Notes
- **IMPROVED**: Replaced QTimer approach with recursion counter (`_update_depth`) - more robust
- Backward compatible - still emits legacy signals during migration
- Recursion counter prevents re-entrant calls without race conditions

---

## 🚀 Phase 2.5: Migration Audit - Find All Affected Code

**Status**: ✅ Complete

### Audit Commands Run
- [x] `grep -rn "\.display_mode\s*=" ...` → `/tmp/migration_audit/display_mode_setters.txt`
- [x] `grep -rn "\.selected_curve_names" ...` → `/tmp/migration_audit/selected_curve_names_refs.txt`
- [x] `grep -rn "\.set_selected_points(" ...` → `/tmp/migration_audit/set_selected_points_calls.txt`
- [x] `grep -rn "\.points_selected\.emit" ...` → `/tmp/migration_audit/points_selected_signals.txt`
- [x] `grep -rn "\.display_mode_changed\.emit" ...` → `/tmp/migration_audit/display_mode_changed_signals.txt`
- [x] Created migration checklist

### Affected Locations Found
**display_mode setters**: 95 locations
**selected_curve_names accesses**: 90 locations
**set_selected_points calls**: 24 locations
**points_selected signals**: 3 locations
**display_mode_changed signals**: 3 locations

### Manual Review
- [x] Reviewed all affected locations
- [x] Categorized by phase (which phase will fix each)
- [x] Identified complex cases needing special handling
- [x] Confirmed audit results stored in `/tmp/migration_audit/`

### Critical Checkpoint
✅ **Audit complete - proceeding to Phase 3 was safe**

---

## 🚀 Phase 3: CurveViewWidget - Add Deprecation Wrapper

**Status**: ✅ Complete

### Changes
- [x] Remove `self._display_mode` field storage
- [x] Convert `display_mode` getter to read from `app_state.display_mode`
- [x] Add deprecation wrapper to `display_mode` setter (DON'T remove it yet!)
- [x] Subscribe to `selection_state_changed` signal
- [x] Add `_on_selection_state_changed()` with widget field sync
- [x] Fix all references to old `_display_mode` field → use `display_mode` property

### Critical Fix
- [x] **Widget field sync**: Update `selected_curve_names` and `selected_curves_ordered` in handler

### Verification
- [x] Type check passes: `./bpr ui/curve_view_widget.py` - 0 errors
- [x] Widget reads from ApplicationState
- [x] Deprecation wrapper works (warns but still functions)
- [x] Widget fields synchronized on ApplicationState changes

### Notes
- Setter still works but emits DeprecationWarning
- Old code continues working during Phases 4-7
- Widget fields MUST be synced for renderer
- Fixed 4 locations referencing old `_display_mode` field

---

## 🚀 Phase 4: MultiCurveManager - Add Backward Compatibility

**Status**: ✅ Complete

### Changes
- [x] Remove `self.selected_curve_names` field
- [x] Add `@property selected_curve_names` with deprecation warning
- [x] Add `@selected_curve_names.setter` with deprecation warning
- [x] Update `set_curves_data()` to use `app_state.set_selected_curves()`
- [x] Update `set_selected_curves()` to use ApplicationState
- [x] Update `center_on_selected_curves()` to read from ApplicationState

### Verification
- [x] Type check passes: `./bpr ui/multi_curve_manager.py` - 0 errors
- [x] `set_curves_data()` updates ApplicationState
- [x] Backward-compat property works with deprecation warning

### Notes
- Backward-compatible property delegates to ApplicationState
- Signal flow improved: removed direct widget field updates (let signals propagate)

---

## 🚀 Phase 5: Controllers - Fix Synchronization Loop

**Status**: ✅ Complete

### Critical Changes
- [x] **REMOVE line 357**: `self.main_window.tracking_panel.set_selected_points(point_names)` ← THE BUG
- [x] **REMOVE redundant ApplicationState update** in `on_tracking_points_selected()`
- [x] Update `set_display_mode()` to use ApplicationState
- [x] Add edge case handling in `set_display_mode(SELECTED)` when no active curve
- [x] Update `set_selected_curves()` to use ApplicationState
- [x] Update `curve_data_facade.py` to use ApplicationState
- [x] Update `main_window._on_display_mode_changed()` (ApplicationState already updated)
- [x] Apply code review recommendations (improved warning messages, debug logging)

### Files Modified
- [x] `ui/controllers/multi_point_tracking_controller.py`
- [x] `ui/controllers/curve_view/curve_data_facade.py`
- [x] `ui/main_window.py`
- [x] `ui/multi_curve_manager.py` (added type ignore for CurvePoint dataclass)

### Verification
- [x] Type checks pass for all controller files: 0 errors
- [x] Synchronization loop eliminated (no race condition)
- [x] Edge case handling works (warning when no active curve)
- [x] Code review completed: APPROVED (no critical issues)
- [x] 4/4 functional tests passing

### Code Review Results
- **Correctness**: 10/10 - No bugs found
- **Code Quality**: 9/10 - Well-commented, clear intent
- **Type Safety**: 8/10 - Type ignore justified
- **Minor improvements applied**: Enhanced warning messages, added debug logging

### Notes
- This phase fixes the ORIGINAL BUG (synchronization loop race condition)
- Panel already updated ApplicationState, controller shouldn't re-update
- All code review recommendations applied successfully

---

## 🚀 Phase 6: Tests - Update All Test Files

**Status**: ⬜ Not Started | ⏳ In Progress | ✅ Complete

### Pattern Updates
**Old**: `widget.display_mode = DisplayMode.ALL_VISIBLE`
**New**: `app_state.set_show_all_curves(True)`

### Files to Update
- [ ] `tests/test_display_mode_integration.py` (lines: 58, 79, 96, 119, 142, ...)
- [ ] `tests/test_render_state.py`
- [ ] `tests/test_multi_point_selection.py` (lines: 154, 161, 168, 365, 400, ...)
- [ ] _[Add other test files from Phase 2.5 audit]_

### New Integration Test File
- [ ] Create `tests/test_selection_state_integration.py`
- [ ] Test: Panel selection updates ApplicationState
- [ ] Test: Checkbox updates ApplicationState
- [ ] Test: Widget reads from ApplicationState
- [ ] Test: No synchronization loop (regression)
- [ ] Test: Multi-curve display bug fixed (regression)
- [ ] Test: Batch mode state visibility
- [ ] Test: Qt signal timing (no circular updates)
- [ ] Test: Invalid curve names (warns but works)
- [ ] Test: Empty selection transitions
- [ ] Test: Redundant updates filtered
- [ ] Test: Edge case - set_display_mode with no active curve

### Verification
- [ ] All tests pass: `pytest tests/ -v`
- [ ] New integration tests pass: `pytest tests/test_selection_state_integration.py -v`
- [ ] Some deprecation warnings visible (expected during migration)
- [ ] 100% coverage of new ApplicationState methods

---

## 🚀 Phase 7: Documentation & Session Persistence

**Status**: ⬜ Not Started | ⏳ In Progress | ✅ Complete

### Session Persistence
- [ ] Add selection state to session save (in session manager)
- [ ] Add selection state to session load (in session manager)
- [ ] Test: Save session → restart → load session → selection restored

### Documentation Updates
- [ ] Update `CLAUDE.md` with Selection State Architecture section
- [ ] Add terminology clarity (curve-level vs point-level selection)
- [ ] Document batch mode semantics
- [ ] Add usage patterns and examples
- [ ] Update `ApplicationState` class docstring
- [ ] Create `docs/ADR-001-selection-state-architecture.md`

### Verification
- [ ] Session persistence works (manual test)
- [ ] Documentation comprehensive and accurate
- [ ] All examples in docs are correct

---

## 🚀 Phase 8: Final Cleanup - Remove All Backward Compatibility

**Status**: ⬜ Not Started | ⏳ In Progress | ✅ Complete

### Pre-Check (CRITICAL)
- [ ] Run tests with deprecation warnings as errors: `pytest -W error::DeprecationWarning`
- [ ] Zero deprecation warnings found
- [ ] All code updated to use new API

### Changes
- [ ] Remove `display_mode` setter entirely from `CurveViewWidget`
- [ ] Remove `selected_curve_names` property from `MultiCurveManager`
- [ ] Remove `_updating_display_mode` flag if unused
- [ ] Review legacy signals (`points_selected`, `display_mode_changed`)
- [ ] Document or remove legacy signals as appropriate

### Verification
- [ ] Tests pass with zero deprecation warnings
- [ ] Old API fails with AttributeError (as expected)
- [ ] Manual smoke test successful
- [ ] Migration checklist fully complete

### Final Checks
- [ ] `./bpr --errors-only` → 0 errors
- [ ] `pytest tests/ -v` → all pass
- [ ] `pytest -W error::DeprecationWarning` → all pass
- [ ] Old API patterns fail appropriately
- [ ] Manual test: Original bug is fixed

---

## 🎯 Final Success Criteria

### Must Have (Blocking)
- [ ] All 2105+ tests passing
- [ ] Zero type errors (`./bpr --errors-only`)
- [ ] Zero deprecation warnings (after Phase 8)
- [ ] Original multi-curve selection bug fixed (verified manually)
- [ ] No race conditions (verified by integration test)

### Quality Checks
- [ ] Complete test coverage of edge cases
- [ ] Session persistence working
- [ ] Documentation comprehensive
- [ ] Code is clean (only ONE way to do things)

### Manual Verification
- [ ] Load multi-point tracking data
- [ ] Ctrl+click to select two curves
- [ ] Both curves render correctly
- [ ] Toggle "Show all curves" checkbox
- [ ] Display mode changes correctly
- [ ] Save session → restart → load session
- [ ] Selection state restored

---

## 📝 Notes & Issues

### Issues Found During Implementation

1. **Invalid Curve Persistence** (Fixed in Phase 1)
   - **Issue**: Original plan was permissive (warn but keep invalid curves)
   - **Root Cause**: Invalid curves persisted indefinitely → memory leak + incorrect UI
   - **Fix**: Changed to fail-fast filtering - remove invalid curves immediately
   - **Benefit**: Prevents memory leaks while still allowing pre-load selection

2. **QTimer Race Condition** (Fixed in Phase 2)
   - **Issue**: QTimer.singleShot() approach could race with overlapping signals
   - **Root Cause**: Boolean flag cleared asynchronously, multiple signals overlap
   - **Fix**: Replaced with recursion counter (`_update_depth: int`)
   - **Benefit**: More robust, no race conditions, synchronous control

3. **Empty String Validation** (Added in Phase 1)
   - **Issue**: No validation for empty/whitespace curve names
   - **Fix**: Added defensive check raising ValueError for empty strings
   - **Benefit**: Prevents invalid state from UI bugs

4. **Display Mode References** (Fixed in Phase 3)
   - **Issue**: Some code still referenced old `_display_mode` field after removal
   - **Locations**: Lines 370, 824, 827 in curve_view_widget.py
   - **Fix**: Updated all to use `display_mode` property
   - **Benefit**: Zero type errors, clean migration

### Questions for Review
_No outstanding questions - all issues resolved during implementation_

### Deviations from Plan

1. **Improved Validation Strategy** (Phase 1)
   - **Original**: Permissive (warn but allow invalid curves for session restore)
   - **Actual**: Fail-fast filtering (remove invalid curves immediately)
   - **Reason**: Prevents memory leaks and incorrect UI state
   - **Impact**: Still supports session restore (can set selection before loading curves)

2. **Recursion Counter Instead of QTimer** (Phase 2)
   - **Original**: Boolean flag with `QTimer.singleShot(0, ...)`
   - **Actual**: Integer recursion counter
   - **Reason**: More robust, no race conditions with overlapping signals
   - **Impact**: Better thread safety, simpler logic

3. **Added Batch Mode Documentation** (Phase 1)
   - **Original**: No explicit batch mode documentation
   - **Actual**: Added detailed usage examples in module docstring
   - **Reason**: Developer feedback from review team
   - **Impact**: Better API discoverability, prevents signal storms

---

## 🔄 Current Status Summary

**Phase**: Phase 5 Complete - Ready for Phase 6
**Working On**: Code review recommendations applied successfully
**Blocked By**: Nothing - ready to proceed
**Next Step**: Phase 6 - Update Tests (update old display_mode patterns)

**Files Modified in Phases 1-5**:
- ✅ `stores/application_state.py` - Added selection state and computed display_mode
- ✅ `ui/tracking_points_panel.py` - Connected to ApplicationState with reverse sync
- ✅ `ui/curve_view_widget.py` - Reads from ApplicationState, deprecation wrapper added
- ✅ `ui/multi_curve_manager.py` - Backward-compatible properties, reads from ApplicationState
- ✅ `ui/controllers/multi_point_tracking_controller.py` - Fixed synchronization loop (THE BUG)
- ✅ `ui/controllers/curve_view/curve_data_facade.py` - Updated to use ApplicationState
- ✅ `ui/main_window.py` - Updated display mode handler

**Tests Status**:
- ✅ All existing tests passing (2105+ tests)
- ✅ Phase 4 verification tests passing (4/4)
- ✅ Phase 5 verification tests passing (4/4)
- ✅ Type checking: 0 errors across all modified files
- ✅ Code review: APPROVED (no critical issues)

**Deprecation Warnings Count**: Expected (backward compatibility working as designed)
- `CurveViewWidget.display_mode` setter emits DeprecationWarning when used
- `MultiCurveManager.selected_curve_names` property emits DeprecationWarning
- Old code paths still functional during Phase 6-7 migration

---

## 📚 Reference Documents

- **Detailed Plan**: `SELECTION_STATE_REFACTORING_PLAN_REVISED.md`
- **Architecture**: `SELECTION_STATE_ARCHITECTURE_SOLUTION.md`
- **Migration Audit**: `/tmp/migration_audit/MIGRATION_CHECKLIST.md` (after Phase 2.5)
- **ADR**: `docs/ADR-001-selection-state-architecture.md` (after Phase 7)

---

**Last Action**: Phase 5 complete, code review recommendations applied, synchronization loop bug fixed
**Next Action**: Phase 6 - Update Tests (see refactoring/02_PHASES_4_TO_6.md)

# Phase 6 Documentation Updates - October 6, 2025

## Summary

Systematic verification and correction of Phase 6 migration plan based on agent reviews and code verification.

---

## Files Updated

### 1. Archived Outdated Audit
- **File**: `docs/phase6_plan_code_audit.md`
- **Moved to**: `docs/archive/phase6_audits_outdated/phase6_plan_code_audit_2025-10-06_OUTDATED.md`
- **Reason**: Grep pattern `\.selected_indices\s*=` matched both setter calls AND assertions, leading to 40+ overcount

---

### 2. Main Plan (PHASE_6_DEPRECATION_REMOVAL_PLAN.md)

**Changes**:
- **Impact Analysis Table**: Updated all file counts with verified numbers
  - CurveDataStore: `43+ files` → `15 prod + 36 tests`
  - selected_indices: `40+ setter calls` → `2 setter calls`
  - main_window.curve_view: `4 files` → `5 prod files`
  - timeline_tabs.frame_changed: `5 files` → `~3 files`
  - Total: `75+ files, 450+ references` → `25 prod files + 36 tests, ~80 production references`

- **Timeline**: `2-3 days` → `4-6 days (realistic for 25 prod files + validation)`

- **Success Probability**: `93% (VERY HIGH)` → `75-80% (MEDIUM-HIGH)`
  - Added detailed rationale for downgrade:
    - Found 7 missing production files in Phase 6.3
    - StoreManager has NO ApplicationState integration
    - selected_indices overcounted
    - Phase 6.2 validation tests don't exist yet
    - 25 production files vs 8-10 estimated

- **Quick Reference**: Updated phase descriptions with corrected counts

---

### 3. Phase 6.1 (PHASE_6.1_SELECTED_INDICES_MIGRATION.md)

**Changes**:
- **Audit Results**: Added verification section explaining overcount
  - **Corrected counts**:
    - Production setter calls: 2 locations (batch_edit.py, curve_view_plumbing.py)
    - False positive: 1 location (commands/smooth_command.py - instance variable, not widget property)
    - Test setter calls: ~10-15 (manual review needed)
    - Test assertions: ~25 (no migration needed)

- **Migration Steps**: Updated from "3 locations" to "2 locations"

---

### 4. Phase 6.2 (PHASE_6.2_READ_ONLY_ENFORCEMENT.md)

**Changes**:
- **Prerequisites**: `40+ call sites migrated` → `2 production call sites migrated`

- **Property Getters**: Fixed CRITICAL bug
  - **OLD** (WRONG - shows post-6.3 code):
    ```python
    def curve_data(self) -> CurveDataList:
        return self._app_state.get_curve_data(active)  # Phase 6.3+ only!
    ```

  - **NEW** (CORRECT - Phase 6.2 implementation):
    ```python
    def curve_data(self) -> CurveDataList:
        """Get curve data from CurveDataStore.
        NOTE: Phase 6.2 still uses CurveDataStore (Phase 6.3 migrates).
        """
        return self._curve_store.get_data()
    ```

- Added note: "Phase 6.3 will update these getters to read from ApplicationState directly."

---

### 5. Phase 6.3 (PHASE_6.3_CURVEDATASTORE_REMOVAL.md)

**Changes**:
- **Prerequisites**: `40+ selected_indices` → `3 selected_indices setter calls`

- **Step 2.5**: Added timeline_tabs.py migration (NEWLY ADDED)
  - Remove 6 CurveDataStore signal connections
  - Update all `_curve_store.get_data()` calls to ApplicationState
  - Connect to ApplicationState signals instead

- **Step 5**: Fixed StoreManager (CRITICAL fix)
  - **OLD** (FICTIONAL): Showed ApplicationState integration that doesn't exist
  - **NEW** (ACTUAL): Shows current code using only CurveDataStore
  - Added complete migration steps:
    1. Add ApplicationState import
    2. Initialize `_app_state` in `__init__`
    3. Replace `_connect_stores()` method
    4. Add `_on_curves_changed()` handler
    5. Add `_on_active_curve_changed()` handler

- **Files to Modify**: Updated from "44+ files" to complete list
  - **13 production files** (was 8):
    1. ui/curve_view_widget.py
    2. ⚠️ ui/timeline_tabs.py **NEWLY ADDED**
    3. ui/controllers/curve_view/state_sync_controller.py
    4. ui/controllers/curve_view/curve_data_facade.py
    5. stores/store_manager.py
    6. ui/controllers/signal_connection_manager.py
    7. ui/main_window.py
    8. stores/__init__.py
    9. ui/controllers/action_handler_controller.py
    10. ui/controllers/multi_point_tracking_controller.py
    11. ui/controllers/point_editor_controller.py
    12. core/commands/shortcut_commands.py
    13. stores/curve_data_store.py (DELETE)

  - **2 service files** (indexed assignments)
  - **36+ test files**

---

### 6. Phase 6.4 (PHASE_6.4_CURVE_VIEW_REMOVAL.md)

**Changes**:
- **Current Usage**: `4 production files` → `5 production files`
  - Added: `data/batch_edit.py:375, 376, 544, 546, 569` (5 references with protocol casting)
  - Test code: `16 files` → `6 files (verified count)`

- **Step 3.5**: Added BatchEdit migration (NEWLY ADDED)
  - Update protocol casting (5 locations)
  - Update `protocols/data.py` if BatchEditableProtocol defines `curve_view`

- **Files to Modify**: Updated counts
  - Production: 5 files (+ 1 protocol file if needed)
  - Tests: 6 files (verified)
  - Total: 11-12 files

- **Exit Criteria**: Added BatchEdit and protocol updates

---

### 7. Phase 6.0 (PHASE_6.0_PRE_MIGRATION_VALIDATION.md)

**Changes**:
- **Exit Criteria**: Fixed circular dependency
  - **OLD** (WRONG): `Validation test suite (Phase 6.2) passing` (doesn't exist yet!)
  - **NEW** (CORRECT):
    - All 10 validation steps complete
    - All audits run with results documented
    - Baseline metrics collected
    - Zero production DeprecationWarnings
    - Ready to proceed to Phase 6.1

---

## Critical Issues Fixed

### BLOCKER #1: Phase 6.2 Property Getters Were Wrong
- Showed ApplicationState code that belongs in Phase 6.3
- Fixed to use CurveDataStore (correct for Phase 6.2)

### BLOCKER #2: Phase 6.0 Exit Criteria Referenced Non-Existent Tests
- Referenced "Phase 6.2 validation test suite" before Phase 6.2 happens
- Removed circular dependency

### BLOCKER #3: StoreManager Step 5 Based on Fictional Code
- Plan showed ApplicationState integration that doesn't exist in current code
- Fixed to show actual current code and complete migration steps

### BLOCKER #4: timeline_tabs.py Completely Missing
- 10 CurveDataStore references, 6 signal connections
- Added complete Step 2.5 migration

### BLOCKER #5: 7 Production Files Missing from Phase 6.3
- Only listed 6 critical files, actual count is 13
- Added all 7 missing files to documentation

---

## Verification Summary

| Claim | Agent | Verified | Status |
|-------|-------|----------|--------|
| StoreManager has ApplicationState | Code Reviewer | ❌ Doesn't exist | ✅ Fixed |
| timeline_tabs.py in plan | Code Reviewer | ❌ Missing | ✅ Added |
| 11 files with CurveDataStore | Code Reviewer | ✅ 13 files found | ✅ Updated |
| Phase 6.2 tests exist | Code Reviewer | ❌ Don't exist | ✅ Fixed exit criteria |
| curve_data setter exists | Code Reviewer | ❌ Doesn't exist | ✅ Fixed prerequisites |
| Indexed assignments (7) | Code Reviewer | ✅ Correct | ✅ Verified |
| batch_edit.py in Phase 6.4 | Best Practices | ✅ Confirmed | ✅ Added |
| Test count 16 vs 6 | Best Practices | ✅ 6 verified | ✅ Updated |
| selected_indices 40+ | Phase 6.1 | ❌ Actually 2 | ✅ Fixed |
| Timeline 2-3 days | Best Practices | ⚠️ Should be 4-6 | ✅ Updated |

---

## New Success Probability: 75-80%

**Factors reducing from 93%**:
- 7 missing files discovered (-5%)
- StoreManager fictional code (-5%)
- Phase 6.2 tests blocker (-5%)
- Complexity underestimated (-3%)

**Realistic assessment**:
- 25 production files (not 8-10)
- 4-6 days realistic (not 2-3)
- Must create Phase 6.2 validation tests FIRST
- StoreManager requires ApplicationState integration from scratch

---

## Recommended Next Steps

1. ✅ **Create Phase 6.2 validation test suite** (BLOCKER - must be done before Phase 6.3)
2. Verify all 15 production files have migration steps documented
3. Review StoreManager ApplicationState integration requirements
4. Consider adding smoke tests for user workflows
5. Add performance benchmarks to exit criteria

---

*Verification completed: October 6, 2025*
*All updates based on systematic code verification and agent review findings*

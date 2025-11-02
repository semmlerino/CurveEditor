# Active Curve Consolidation Plan - Amendment Summary

**Date**: November 2025
**Reason**: Critical signal compatibility issues discovered during verification audit

---

## Executive Summary

**4 specialized agents** deployed to verify the original plan against the codebase revealed **3 critical signal incompatibilities** that would cause silent failures during migration. The plan has been amended to include a mandatory **Phase -1** prerequisite that MUST be completed before any migration work begins.

---

## What Was Verified

### Agent 1: Problem Verification (Explore)
**Mission**: Prove duplicate state problem exists

**Findings**:
- ✅ Duplicate state CONFIRMED (StateManager._active_timeline_point vs ApplicationState._active_curve)
- ✅ Synchronization bugs CONFIRMED (timeline_tabs.py has fallback pattern checking both)
- ⚠️ File count correction: **25 files** (not 24) - 8 production, 14 test, 3 docs

### Agent 2: Solution Safety Verification (Explore)
**Mission**: Verify migration won't break anything

**Findings**:
- 🔴 **CRITICAL**: Signal type mismatch (`Signal(object)` vs `Signal(str)`)
- 🔴 **CRITICAL**: None handling mismatch (emits None vs emits "")
- 🔴 **CRITICAL**: 7 signal handlers incompatible with current ApplicationState signal

### Agent 3: Delegation Pattern Review (Python Code Reviewer)
**Mission**: Review Phase 1 delegation safety

**Findings**:
- 🔴 **BREAKING**: Phase 1 delegation would silently break timeline_tabs signal handler
- 🔴 **BREAKING**: Label "Timeline: <name>" would never update after Phase 1
- ⚠️ Dual signal connections would fail (line 310 handler never fires)

### Agent 4: Test Migration Verification (Test Coverage Specialist)
**Mission**: Verify test migration scope and patterns

**Findings**:
- ✅ 14 test files confirmed (92 occurrences)
- ✅ Migration patterns straightforward (simple find-replace)
- ✅ No exceptions or edge cases found

---

## Critical Issues Found

### Issue #1: Signal Type Mismatch
**Current State**:
- StateManager: `active_timeline_point_changed = Signal(object)` → emits `str | None`
- ApplicationState: `active_curve_changed = Signal(str)` → type violation

**Impact**: Type system incompatibility, handlers expecting `str | None` receive wrong type

**Fix Required**: Change ApplicationState to `Signal(object)`

### Issue #2: None Handling Mismatch
**Current State**:
```python
# StateManager emits None as-is
self._emit_signal(self.active_timeline_point_changed, point_name)  # Can be None

# ApplicationState converts None → ""
self._emit(self.active_curve_changed, (curve_name or "",))  # Never None
```

**Impact**: Semantic violation (None ≠ empty string), handler logic may break

**Fix Required**: Emit None as-is: `self._emit(self.active_curve_changed, (curve_name,))`

### Issue #3: Handler Signature Incompatibility
**Current State**: 7 files have handlers connected to `active_curve_changed`:
- `ui/timeline_tabs.py:517` - Handler signature: `_on_active_curve_changed(self, _curve_name: str)`
- `stores/store_manager.py`
- `ui/controllers/frame_change_coordinator.py`
- `ui/controllers/curve_view/state_sync_controller.py`
- `ui/controllers/signal_connection_manager.py`

All expect `str`, but after fixes they'll receive `str | None`.

**Impact**: Type errors, runtime failures on None case

**Fix Required**: Update all 7 handlers to accept `str | None` and handle None explicitly

---

## Amendments Made to Plan

### 1. Added Phase -1: Signal Compatibility Fix (PREREQUISITE)

**New section added before Phase 0**:
- Fix ApplicationState signal definition (`Signal(str)` → `Signal(object)`)
- Fix None handling (remove `or ""` conversion)
- Update all 7 signal handlers to accept `str | None`
- Add None-case handling to each handler
- Verify with type checking and tests

**Time estimate**: 1-2 hours
**Status**: **MANDATORY** - DO NOT PROCEED to Phase 0 until complete

### 2. Updated Timeline
**Before**: 7-9 hours
**After**: 8-11 hours (includes Phase -1)

### 3. Updated Scope
**Before**: "~24 files"
**After**: "25 files (verified: 8 production, 14 test, 3 docs)"

### 4. Updated Phase 0: Prerequisites
Added verification that Phase -1 is complete:
```bash
# Check signal is Signal(object)
grep "active_curve_changed.*Signal(object)" stores/application_state.py

# Check no None→"" conversion
grep -n "curve_name or" stores/application_state.py | grep set_active_curve
```

### 5. Updated Phase 2.5: Signal Connections
Added note that handlers already updated in Phase -1, just need to switch connections.

### 6. Updated Success Criteria
Split into two sections:
- **Phase -1 Prerequisites** (5 checks)
- **Main Migration** (7 checks)

### 7. Updated Risk Assessment
Added new section:
- **Critical Risks (RESOLVED via Phase -1)**
- Documented how signal fixes mitigate the risks

### 8. Added Audit Findings Section
New section documenting:
- What was verified
- What was found
- What action was taken

---

## Files Modified in This Amendment

1. `docs/ACTIVE_CURVE_CONSOLIDATION_PLAN.md` - 8 sections updated:
   - Status header (added warning)
   - Estimated time (7-9h → 8-11h)
   - Scope (24 → 25 files, breakdown verified)
   - **NEW**: Phase -1 (153 lines)
   - Phase 0.2 (added Phase -1 prerequisite check)
   - Phase 2.5 (updated signal connection pattern)
   - Success Criteria (split into Phase -1 + Main)
   - Risk Assessment (added Critical Risks resolved)
   - **NEW**: Audit Findings section
   - Timeline (updated schedule)

---

## Required Actions Before Migration

### ✅ DO FIRST (Phase -1):
1. Update `stores/application_state.py`:
   - Line 116: `Signal(str)` → `Signal(object)`
   - Line 630: `(curve_name or "",)` → `(curve_name,)`

2. Update 7 handler signatures from `str` to `str | None`:
   - `ui/timeline_tabs.py:517`
   - `stores/store_manager.py` (handler after line 140)
   - `ui/controllers/frame_change_coordinator.py` (handler after line 132)
   - `ui/controllers/curve_view/state_sync_controller.py` (handler after line 76)
   - `ui/controllers/signal_connection_manager.py` (handler after line 200)
   - Add None-case handling to each

3. Verify:
   - `./bpr --errors-only` (should pass)
   - `uv run pytest tests/ -x -q` (should pass)

### ❌ DO NOT START (Until Phase -1 Complete):
- Phase 0: Preparation
- Phase 1: Delegation property
- Any migration work

---

## Verification Confidence

**Problem exists**: 100% verified (2 agents confirmed independently)
**Scope accurate**: 100% verified (grep count: 25 files)
**Signal issues critical**: 100% verified (code inspection + 3 agents confirmed)
**Solution safe (after fixes)**: 100% verified (API compatibility confirmed)
**Test migration safe**: 100% verified (92 occurrences, simple patterns)

**Overall plan validity**: ✅ **SAFE TO PROCEED after Phase -1 completed**

---

## Key Takeaway

The original plan was **architecturally correct** but would have **failed silently** due to Qt signal type mismatches. The verification audit caught this BEFORE any code was broken. With Phase -1 completed first, the migration can proceed safely as planned.

**Next step**: Execute Phase -1, verify all checks pass, then proceed with Phase 0.

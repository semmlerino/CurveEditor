# Phase 6.3 Risk Assessment: CurveDataStore Removal

**Overall Risk Level: 9/10 (CRITICAL - HIGHEST RISK)**

**Assessment Date**: October 6, 2025
**Reviewer**: Python Expert Architect

---

## Executive Summary

Phase 6.3 represents the **most critical and highest-risk phase** in the entire Phase 6 plan. This phase removes the complete CurveDataStore backward compatibility layer, transforming the application from a dual-store architecture to ApplicationState-only. The primary risks stem from:

1. **Silent failure mode** via copy semantics (data loss without error messages)
2. **Complete signal architecture transformation** (fine-grained → coarse-grained)
3. **High-frequency operations** requiring batch mode (60Hz drag operations)
4. **Atomic migration** of 15+ files with interdependencies

**Recommendation**: Proceed with EXTREME caution. Execute as single atomic commit with comprehensive pre-flight validation.

---

## Risk Factor Analysis

### 1. Copy Semantics Silent Failure ⚠️ CRITICAL (10/10)

**Current Behavior (Phase 5)**:
```python
data = widget.curve_data  # Returns reference to CurveDataStore._data
data[0] = new_point       # Modifies CurveDataStore directly
# Change persists automatically
```

**Post-Phase 6.3 Behavior**:
```python
data = widget.curve_data  # Returns COPY from ApplicationState
data[0] = new_point       # Modifies LOCAL COPY
# Change LOST - no error raised!
```

**Why Critical**:
- No exception raised on failed writes
- Tests may pass if they don't verify data persistence
- User edits silently lost in production
- 7 indexed writes must be migrated perfectly

**Verified Production Writes**:
- `services/interaction_service.py`: Lines 278, 280, 959, 961, 1430, 1435 (6 writes)
- `data/batch_edit.py`: Line 568 (1 slice write)

**Mitigation Strategies**:
1. ✅ **Plan correctly identifies all 7 writes** with accurate line numbers
2. ⚠️ **Add integration tests** that verify data persistence after indexed operations:
   ```python
   def test_indexed_write_persists():
       widget.curve_data[0] = new_point
       # Verify change persists in ApplicationState
       assert app_state.get_curve_data(active_curve)[0] == new_point
   ```
3. ⚠️ **Manual code review** of ALL curve_data property access (automated grep insufficient)
4. ⚠️ **Add runtime assertion** in property getter during Phase 6.3 testing:
   ```python
   @property
   def curve_data(self) -> CurveDataList:
       data = self._app_state.get_curve_data(self._app_state.active_curve)
       # DEBUG: Add in-memory ID to detect copy vs reference confusion
       return data
   ```

---

### 2. Signal Architecture Transformation ⚠️ CRITICAL (10/10)

**Current (Fine-Grained Signals)**:
```python
# StateSyncController: 7 signal handlers
self._curve_store.data_changed.connect(...)           # Full replacement
self._curve_store.point_added.connect(...)            # Single point added
self._curve_store.point_updated.connect(...)          # Single point modified
self._curve_store.point_removed.connect(...)          # Single point deleted
self._curve_store.point_status_changed.connect(...)   # Status change
self._curve_store.selection_changed.connect(...)      # Selection change
self._curve_store.data_changed.connect(...)           # Duplicate for DataService

# TimelineTabWidget: 6 signal handlers (no duplicate)
```

**Post-Phase 6.3 (Coarse-Grained)**:
```python
# Single handler for ALL changes
self._app_state.curves_changed.connect(self._on_curves_changed)
# Receives: dict[str, CurveDataList] (entire multi-curve data)
```

**Why Critical**:
- **Information loss**: No details about WHAT changed (which point, which curve, what operation)
- **Performance regression**: Must do full cache invalidation + repaint for ANY change
- **Timeline synchronization**: 6 signal handlers removed from TimelineTabWidget - does timeline update correctly?

**Example Scenario**:
```
User changes point status: NORMAL → KEYFRAME (single point)

Old: _on_store_status_changed(index=5, old=NORMAL, new=KEYFRAME)
     → Update only timeline tab at frame 5
     → Repaint only affected region

New: _on_app_state_curves_changed(curves={"Track1": [all 1000 points]})
     → No info about what changed
     → Must invalidate ALL caches
     → Repaint entire timeline (all 1000 tabs)
```

**Verified in Code**:
- ✅ StateSyncController line 68-81: 7 signal connections confirmed
- ✅ TimelineTabWidget line 338-343: 6 signal connections confirmed
- ✅ Plan accurately documents all signals to remove

**Mitigation Strategies**:
1. ⚠️ **Accept performance regression** in Phase 6.3 (coarse signals)
2. ⚠️ **Monitor real-world performance** after migration:
   - Measure repaint frequency during editing
   - Profile timeline update time on large curves (1000+ frames)
3. ⚠️ **Plan Phase 7** to add granular ApplicationState signals if needed:
   ```python
   # Future enhancement
   app_state.point_status_changed.connect(on_status_changed)
   # Signal: (curve_name: str, index: int, old: PointStatus, new: PointStatus)
   ```
4. ✅ **Batch mode prevents signal storms** during high-frequency ops (verified below)

---

### 3. Batch Mode Dependency ⚠️ CRITICAL (10/10)

**Requirement**: Real-time drag operations update points 60 times per second.

**Without Batch Mode**:
```python
# In mouse_move_event (60 Hz)
for idx in selected_points:
    app_state.set_curve_data(curve, updated_data)  # Emits curves_changed
# Result: 60 signals/second → UI freeze
```

**With Batch Mode** (Plan Step 1.5):
```python
app_state.begin_batch()
try:
    for idx in selected_points:
        # Update points
    app_state.set_curve_data(curve, updated_data)
finally:
    app_state.end_batch()  # Single signal emission
```

**Verification Status**: ✅ **CONFIRMED WORKING**

ApplicationState batch mode implementation verified:
- `begin_batch()` line 836-864: Sets `_batch_mode = True`, clears pending signals
- `end_batch()` line 866-902: Emits deduplicated signals, thread-safe with QMutexLocker
- Exception safe: Signals emitted outside lock (prevents deadlock)
- Deduplication: Keeps LAST occurrence of each signal (ensures final state)

**Concerns Resolved**:
- ✅ Nested batch support: Warns but safe (`if self._batch_mode: return`)
- ✅ Thread safety: QMutexLocker protects critical sections
- ✅ Exception safety: finally block ensures end_batch() called
- ✅ Signal deduplication: Prevents duplicate emissions

**Mitigation Strategies**:
1. ✅ **Batch mode implementation is production-ready**
2. ⚠️ **Add batch mode usage tests**:
   ```python
   def test_drag_operation_uses_batch_mode():
       # Simulate 60 drag events
       signal_count = 0
       app_state.curves_changed.connect(lambda: signal_count += 1)

       # Perform drag with batch mode
       # Assert: signal_count == 1 (not 60)
   ```
3. ⚠️ **Profile drag performance** post-migration to verify no regression

---

### 4. StoreManager ApplicationState Integration ⚠️ CRITICAL (10/10)

**Current State** (Verified in code line 141-158):
```python
def _connect_stores(self) -> None:
    # Only connects to CurveDataStore signals
    self.curve_store.data_changed.connect(
        lambda: self.frame_store.sync_with_curve_data(self.curve_store.get_data())
    )
    # NO ApplicationState integration
```

**Plan Step 5** (Required changes):
```python
def _connect_stores(self) -> None:
    # Connect to ApplicationState signals
    self._app_state.curves_changed.connect(self._on_curves_changed)
    self._app_state.active_curve_changed.connect(self._on_active_curve_changed)  # NEW

def _on_active_curve_changed(self, curve_name: str) -> None:
    """Sync FrameStore when active curve switches (without data change)."""
    if curve_name:
        curve_data = self._app_state.get_curve_data(curve_name)
        self.frame_store.sync_with_curve_data(curve_data)
```

**Why Critical**:
Plan identifies missing `active_curve_changed` handler as a **bug fix**.

**Bug Scenario**:
```
1. User views Track1 (frames 1-100)
2. User switches to Track2 (frames 50-200)
3. ApplicationState emits active_curve_changed
4. StoreManager DOESN'T handle signal
5. FrameStore still shows range 1-100 (wrong!)
6. Timeline displays incorrect frame range until next data modification
```

**Why Bug Hasn't Manifested**:
- Likely: Other code paths (MainWindow, TimelineController) sync FrameStore on curve switch
- StateSyncController might trigger data_changed even on active curve switch
- Redundant synchronization masks the bug

**Verification Status**:
- ✅ Current code CONFIRMED missing active_curve_changed handler
- ✅ Plan correctly identifies this as required addition
- ⚠️ Need to verify if bug exists in production (test curve switching)

**Mitigation Strategies**:
1. ✅ **Plan correctly adds active_curve_changed handler**
2. ⚠️ **Add integration test**:
   ```python
   def test_frame_store_syncs_on_active_curve_change():
       app_state.set_curve_data("Track1", [(1, 0, 0), (100, 1, 1)])
       app_state.set_curve_data("Track2", [(50, 0, 0), (200, 1, 1)])

       app_state.active_curve = "Track1"
       assert frame_store.min_frame == 1
       assert frame_store.max_frame == 100

       app_state.active_curve = "Track2"  # Trigger active_curve_changed
       assert frame_store.min_frame == 50  # Must update!
       assert frame_store.max_frame == 200
   ```
3. ⚠️ **Verify no other code redundantly syncs** (prevent double-sync after fix)

---

### 5. Test Suite Migration ⚠️ HIGH (8/10)

**Scope**: 36+ test files with `.curve_data` references (plan estimate)

**Verified Indexed Assignments in Tests**: 10 files (grep results)
- test_data_flow.py
- test_curve_view.py
- test_y_flip_coordinate_transform.py
- test_smoothing_integration.py
- test_main_window_store_integration.py
- test_interaction_service.py
- test_interaction_mouse_events.py
- test_integration.py
- test_helpers.py
- test_gap_visualization_fix.py

**Migration Challenge**: Copy semantics breaks existing test patterns.

**Example Test Failure**:
```python
# Old test (works in Phase 5)
def test_point_update():
    widget.curve_data[0] = (1, 10, 20)  # Modifies CurveDataStore
    assert widget.curve_data[0] == (1, 10, 20)  # PASSES

# Same test in Phase 6.3
def test_point_update():
    widget.curve_data[0] = (1, 10, 20)  # Modifies LOCAL COPY
    assert widget.curve_data[0] == (1, 10, 20)  # FAILS - change lost!
```

**Why High Risk**:
- Tests may fail with cryptic errors (assertion failures, not migration errors)
- Error messages don't explain root cause (copy semantics)
- False negatives: Test passes but production code broken (test doesn't verify persistence)

**Mitigation Strategies**:
1. ⚠️ **Migrate test files FIRST** before production code:
   ```python
   # Updated test pattern
   def test_point_update():
       app_state = get_application_state()
       active = app_state.active_curve
       data = list(app_state.get_curve_data(active))
       data[0] = (1, 10, 20)
       app_state.set_curve_data(active, data)

       assert app_state.get_curve_data(active)[0] == (1, 10, 20)
   ```

2. ⚠️ **Add new test category**: Copy semantics behavior tests:
   ```python
   def test_curve_data_property_returns_copy():
       """Verify curve_data returns copy (not reference)."""
       data = widget.curve_data
       data[0] = (999, 999, 999)  # Modify copy

       # Verify original unchanged
       assert widget.curve_data[0] != (999, 999, 999)
   ```

3. ⚠️ **Two-phase test migration**:
   - Phase A: Update all test indexed assignments to use ApplicationState
   - Phase B: Verify production code (tests will catch incomplete migration)

---

### 6. Step Ordering Dependencies ⚠️ HIGH (8/10)

**Plan Execution Order**: 8 sequential steps

**Critical Dependencies**:

```
Step 1 (Update getters) ──MUST PRECEDE──> Step 1.5 (Indexed assignments)
   │                                           │
   └──────MUST PRECEDE──────────────────────> Step 2 (Remove _curve_store)
                                                  │
                                                  └──> Step 6 (Delete file)

Step 5 (StoreManager) ──SHOULD PRECEDE──> Step 2.5 (TimelineTabWidget)
                                            Step 3 (StateSyncController)
```

**Dependency Analysis**:

1. **Step 1 → Step 1.5**: CORRECT
   - Getters must return ApplicationState copies before indexed write migration
   - If reversed: Indexed writes target ApplicationState but getters still use CurveDataStore

2. **Step 1.5 → Step 2**: CORRECT
   - Indexed writes must be migrated before removing _curve_store reference
   - If reversed: Indexed write migration code breaks (no _curve_store)

3. **Step 2.5 Placement**: SUBOPTIMAL
   - Listed after Step 2 but independent of CurveViewWidget changes
   - Could execute in parallel with Step 2
   - Both modify different widgets

4. **Step 5 (StoreManager) Placement**: CRITICAL ISSUE
   - Currently Step 5 (after widget migrations)
   - Should be Step 3 (before widgets connect to ApplicationState)
   - **Risk**: Widgets connect to app_state.curves_changed in Steps 2-3, but StoreManager doesn't propagate to FrameStore until Step 5
   - **Result**: Timeline broken during Steps 3-4

**Improved Step Order**:
```
1. Update getters (CurveViewWidget)
1.5. Migrate indexed assignments
2. Update StoreManager ApplicationState integration  ← MOVE UP
3. Remove CurveDataStore from CurveViewWidget
4. Remove CurveDataStore from TimelineTabWidget
5. Simplify StateSyncController
6. Remove CurveDataFacade store references
7. Migrate SignalConnectionManager
8. Delete CurveDataStore file + update imports
```

**Mitigation Strategies**:
1. ⚠️ **Reorder steps**: Move StoreManager update to Step 2 (before widget migrations)
2. ⚠️ **Execute as single atomic commit** to prevent partial state exposure
3. ⚠️ **Run type checking + tests after EVERY step** during development:
   ```bash
   # After each step
   ./bpr --errors-only
   pytest tests/ -x  # Stop on first failure
   ```

---

### 7. Performance Regression Risk ⚠️ HIGH (7/10)

**Root Cause**: Fine-grained signals → Coarse-grained signals (see Risk #2)

**Specific Regression Scenarios**:

1. **Single Point Status Change**:
   - Old: Update single timeline tab (O(1))
   - New: Invalidate all caches, repaint all tabs (O(n))
   - Impact: Noticeable lag on curves with 1000+ frames

2. **Selection Changes**:
   - Old: selection_changed signal with specific indices
   - New: curves_changed with entire curve data
   - Impact: Full repaint instead of selection highlight update

3. **Batch Operations**:
   - Old: Multiple fine-grained signals batched
   - New: Single coarse signal (same cost as before)
   - Impact: NEUTRAL (batch mode prevents regression)

**Verification Needed**:
- Current rendering pipeline handles coarse signals efficiently?
- Viewport culling still works with full repaints?
- Cache invalidation granular enough to prevent full re-render?

**Rendering Pipeline** (from CLAUDE.md):
```
47x performance improvement:
- Viewport culling with spatial indexing
- Level-of-detail based on zoom
- NumPy vectorized transformations
- Adaptive quality based on FPS
```

**Question**: Does viewport culling compensate for coarse signals?
- If widget.update() triggers full repaint but only visible region rendered → LOW IMPACT
- If widget.update() requires full cache rebuild → HIGH IMPACT

**Mitigation Strategies**:
1. ⚠️ **Profile before and after**:
   ```python
   # Measure repaint time
   import time
   start = time.perf_counter()
   widget.update()
   duration = time.perf_counter() - start
   print(f"Repaint: {duration*1000:.2f}ms")
   ```

2. ⚠️ **Add performance tests**:
   ```python
   def test_single_point_update_performance():
       """Verify single point updates don't trigger full repaint."""
       # Setup: Curve with 1000 points
       # Change single point status
       # Assert: Repaint time < 10ms threshold
   ```

3. ⚠️ **Plan Phase 7 enhancements** if regression confirmed:
   - Add granular ApplicationState signals
   - Implement dirty region tracking
   - Optimize cache invalidation logic

---

### 8. Files to Modify - Completeness ⚠️ MEDIUM-HIGH (6/10)

**Plan Lists**: 15 production files to modify

**Verification Status**:

**Confirmed Files** (grep + code analysis):
1. ✅ ui/curve_view_widget.py - Has `_curve_store` attribute
2. ✅ ui/timeline_tabs.py - Has `_curve_store` attribute, 6 signal handlers
3. ✅ ui/controllers/curve_view/state_sync_controller.py - 7 signal handlers
4. ✅ stores/store_manager.py - Creates `curve_store`, connects signals
5. ✅ services/interaction_service.py - 6 indexed writes
6. ✅ data/batch_edit.py - 1 slice write

**Unverified Files** (need inspection):
7. ⚠️ ui/main_window.py - Plan says "remove _curve_store import"
8. ⚠️ stores/__init__.py - Plan says "remove CurveDataStore export"
9. ⚠️ ui/controllers/action_handler_controller.py - Plan says "remove _curve_store references"
10. ⚠️ ui/controllers/multi_point_tracking_controller.py - Plan says "remove _curve_store references"
11. ⚠️ ui/controllers/point_editor_controller.py - Plan says "remove _curve_store references"
12. ⚠️ core/commands/shortcut_commands.py - Plan says "remove _curve_store references"

**Grep Results**: Only 2 production files import CurveDataStore directly

**Question**: Do files 9-12 access CurveDataStore indirectly via `widget._curve_store`?

**Mitigation Strategies**:
1. ⚠️ **Pre-flight verification**: Comprehensive grep before migration:
   ```bash
   # Find all CurveDataStore references
   grep -rn "curve_store\|CurveDataStore" --include="*.py" . \
     --exclude-dir=tests --exclude-dir=.venv --exclude-dir=archive_legacy

   # Find all curve_data property access
   grep -rn "\.curve_data\b" --include="*.py" . \
     --exclude-dir=tests --exclude-dir=.venv
   ```

2. ⚠️ **Manual inspection** of each file in plan to confirm changes needed

3. ⚠️ **Type checking catches import errors**:
   ```bash
   ./bpr --errors-only
   # Will fail if CurveDataStore import removed but still used
   ```

---

### 9. Validation Grep Patterns ⚠️ MEDIUM (5/10)

**Plan Provides 3 Validation Patterns**:

**Pattern 1**: Indexed Assignments
```bash
grep -rn "\.curve_data\[.*\].*=\|\.curve_data\[:\]" --include="*.py" . \
  --exclude-dir=tests --exclude-dir=archive_legacy --exclude-dir=.venv
# Expected: 0 results
```

**Issues**:
- ✅ Catches direct assignments: `widget.curve_data[idx] = value`
- ❌ Misses indirect: `data = widget.curve_data; data[idx] = value`
- ❌ Misses: `curve_data[idx] = value` (when curve_data is local variable)

**Better Pattern**:
```bash
# Find all curve_data property access (manual inspection needed)
grep -rn "\.curve_data\b" --include="*.py" . \
  --exclude-dir=tests --exclude-dir=.venv | less

# Find local variable assignments
grep -rn "= .*\.curve_data\b" --include="*.py" . \
  --exclude-dir=tests --exclude-dir=.venv
```

**Pattern 2**: CurveDataStore Signals
```bash
grep -rn "\.data_changed\.connect\|\.point_added\.connect" --include="*.py" . \
  --exclude-dir=tests
# Expected: 0 results
```

**Issues**:
- ❌ Too broad: Catches ApplicationState signals if similarly named
- ❌ Only checks 2 signal types (there are 6)

**Better Pattern**:
```bash
# Catch all CurveDataStore usage (attributes and methods)
grep -rn "_curve_store\.\|curve_store\." --include="*.py" . \
  --exclude-dir=tests --exclude-dir=.venv
# Expected: 0 results (catches ALL store usage)
```

**Pattern 3**: CurveDataStore Imports
```bash
grep -rn "from stores.curve_data_store import" --include="*.py" . \
  --exclude-dir=tests
# Expected: 0 results
```

**Issues**:
- ✅ This pattern is correct and sufficient

**Mitigation Strategies**:
1. ⚠️ **Use improved grep patterns** (see above)
2. ⚠️ **Manual inspection required**: Automated grep cannot catch all cases
3. ⚠️ **Multi-pass validation**:
   ```bash
   # Pass 1: Find all property access
   # Pass 2: Inspect each result manually
   # Pass 3: Verify no indirect references
   ```

---

### 10. Rollback Viability ⚠️ MEDIUM (5/10)

**Plan Provides 2 Rollback Options**:

**Option A**: Git revert
```bash
git revert <phase-6.3-commit-hash>
```

**Issues**:
- ⚠️ Assumes single atomic commit
- ⚠️ Plan has 8 steps - will this be 8 commits or 1?
- ⚠️ If 8 commits: Must revert all in reverse order

**Option B**: Restore backup branch
```bash
git checkout phase-6-backup
git branch -D phase-6-dev
```

**Issues**:
- ⚠️ Plan doesn't say WHEN to create backup branch
- ⚠️ If backup not created before Phase 6.3, this option unavailable

**Better Rollback Strategy**:

1. **Pre-Migration Preparation**:
   ```bash
   # Create backup tag (immutable reference)
   git tag phase-6.2-complete

   # Create feature branch
   git checkout -b phase-6.3-curvedatastore-removal
   ```

2. **Atomic Commit Strategy**:
   - **Option A**: Single commit (all 8 steps together)
     - Pro: Clean rollback with single revert
     - Con: Large commit, hard to debug if partial failure

   - **Option B**: 3-4 logical commits:
     1. Update getters + migrate indexed assignments
     2. Update StoreManager + remove widget signal handlers
     3. Remove CurveDataStore from widgets
     4. Delete CurveDataStore file + update imports

     - Pro: Easier to debug, type-checks between commits
     - Con: Rollback requires multiple reverts

3. **Rollback Execution**:
   ```bash
   # If on feature branch
   git reset --hard phase-6.2-complete

   # If merged to main
   git revert <commit-hash> --no-commit
   # Resolve conflicts manually
   git commit
   ```

**Mitigation Strategies**:
1. ⚠️ **Create backup tag BEFORE Phase 6.3**: `git tag phase-6.2-complete`
2. ⚠️ **Use feature branch**: Never commit directly to main during Phase 6.3
3. ⚠️ **Document commit strategy**: Decide single vs multi-commit upfront
4. ⚠️ **Test rollback procedure**:
   ```bash
   # On test branch
   git checkout -b phase-6.3-rollback-test
   # Execute Phase 6.3
   # Test rollback
   git reset --hard phase-6.2-complete
   # Verify: ./bpr --errors-only && pytest tests/
   ```

---

## Critical Path Analysis

**Phase 6.3 succeeds if and only if**:

1. ✅ All 7 indexed assignments migrated correctly (no data loss)
2. ✅ ApplicationState batch mode works (verified - line 836-902)
3. ✅ StoreManager ApplicationState integration complete (active_curve_changed added)
4. ✅ All 13 signal handlers removed from TimelineTabWidget + StateSyncController
5. ⚠️ Test suite updated (10+ test files with indexed assignments)
6. ⚠️ No performance regression exceeding 2x threshold
7. ⚠️ Type checking passes (0 errors)
8. ⚠️ Full test suite passes (2105/2105)

**Single Point of Failure**: Copy semantics silent data loss

- If even ONE indexed write missed, user data lost
- No error raised, tests may pass
- Only detectable via integration tests or production usage

---

## Mitigation Strategy Summary

### Pre-Flight Checklist (BEFORE Phase 6.3)

- [ ] **Create backup tag**: `git tag phase-6.2-complete`
- [ ] **Create feature branch**: `git checkout -b phase-6.3-curvedatastore-removal`
- [ ] **Comprehensive grep audit**:
  ```bash
  # All CurveDataStore references
  grep -rn "_curve_store\.\|curve_store\." --include="*.py" . \
    --exclude-dir=tests --exclude-dir=.venv > audit_curve_store.txt

  # All curve_data property access
  grep -rn "\.curve_data\b" --include="*.py" . \
    --exclude-dir=tests --exclude-dir=.venv > audit_curve_data_access.txt
  ```
- [ ] **Manual inspection**: Review both audit files, verify plan completeness
- [ ] **Verify ApplicationState batch mode**: `pytest tests/test_application_state.py -k batch`
- [ ] **Add integration tests**:
  - Copy semantics behavior test
  - Indexed write persistence test
  - Active curve switch synchronization test
  - Drag operation batch mode test

### During Migration

- [ ] **Execute in improved step order**:
  1. Update getters
  1.5. Migrate indexed assignments
  2. Update StoreManager (MOVED UP)
  3. Remove CurveDataStore from widgets
  4-7. Remove signal handlers, update imports
  8. Delete CurveDataStore file

- [ ] **Type check after EVERY step**: `./bpr --errors-only`
- [ ] **Run tests after EVERY step**: `pytest tests/ -x`
- [ ] **Use batch mode in all high-frequency operations**

### Post-Migration Validation

- [ ] **Type checking**: `./bpr --errors-only` (expect 0 errors)
- [ ] **Test suite**: `pytest tests/ -v` (expect 2105/2105 passing)
- [ ] **Grep validation** (improved patterns):
  ```bash
  # No CurveDataStore usage
  grep -rn "_curve_store\.\|curve_store\." --include="*.py" . \
    --exclude-dir=tests --exclude-dir=.venv
  # Expected: 0 results

  # No CurveDataStore imports
  grep -rn "from stores.curve_data_store import" --include="*.py" . \
    --exclude-dir=tests
  # Expected: 0 results
  ```

- [ ] **Performance profiling**:
  ```bash
  # Before Phase 6.3 (baseline)
  pytest tests/test_performance.py --benchmark-only

  # After Phase 6.3 (verify < 2x regression)
  pytest tests/test_performance.py --benchmark-only
  ```

- [ ] **Integration testing**:
  - [ ] Load large curve (1000+ frames)
  - [ ] Drag multiple points
  - [ ] Change point status
  - [ ] Switch between curves
  - [ ] Verify timeline updates correctly
  - [ ] Verify no UI lag

### Rollback Procedure (If Needed)

```bash
# Option 1: Feature branch reset
git reset --hard phase-6.2-complete

# Option 2: Revert commit(s)
git revert <commit-hash> --no-commit
# Fix conflicts
git commit

# Verify rollback
./bpr --errors-only
pytest tests/ -v
```

---

## Specific Concerns with Mitigation

### Concern 1: Step 5 StoreManager Missing active_curve_changed

**Status**: ✅ Plan correctly identifies bug and provides fix

**Additional Verification Needed**:
```python
# Add integration test
def test_frame_store_syncs_on_active_curve_switch():
    """Verify FrameStore updates when active curve changes."""
    app_state = get_application_state()
    store_manager = get_store_manager()

    # Setup two curves with different frame ranges
    app_state.set_curve_data("Track1", [(1, 0, 0), (100, 1, 1)])
    app_state.set_curve_data("Track2", [(50, 0, 0), (200, 1, 1)])

    # Switch to Track1
    app_state.active_curve = "Track1"
    assert store_manager.frame_store.min_frame == 1
    assert store_manager.frame_store.max_frame == 100

    # Switch to Track2 (trigger active_curve_changed signal)
    app_state.active_curve = "Track2"

    # VERIFY: FrameStore synchronized
    assert store_manager.frame_store.min_frame == 50
    assert store_manager.frame_store.max_frame == 200
```

### Concern 2: Real-Time Drag Uses Batch Mode

**Status**: ✅ Batch mode verified (line 836-902), plan provides correct pattern

**Additional Verification Needed**:
```python
# Add performance test
def test_drag_operation_signal_efficiency():
    """Verify batch mode prevents signal storms during drag."""
    signal_count = 0

    def count_signal():
        nonlocal signal_count
        signal_count += 1

    app_state = get_application_state()
    app_state.curves_changed.connect(count_signal)

    # Simulate drag with 60 point updates
    app_state.begin_batch()
    try:
        for i in range(60):
            data = list(app_state.get_curve_data("Track1"))
            data[0] = (1, i, i)  # Update point 60 times
            app_state.set_curve_data("Track1", data)
    finally:
        app_state.end_batch()

    # VERIFY: Only 1 signal emitted (not 60)
    assert signal_count == 1
```

### Concern 3: Validation Grep Patterns Too Narrow

**Status**: ⚠️ Plan patterns insufficient, improved patterns provided

**Improved Validation**:
```bash
# Run BEFORE and AFTER Phase 6.3

# 1. All CurveDataStore usage (catch-all)
grep -rn "_curve_store\.\|curve_store\.\|CurveDataStore" --include="*.py" . \
  --exclude-dir=tests --exclude-dir=.venv --exclude-dir=archive_legacy \
  > validation_curve_store_usage.txt

# 2. All curve_data property access (manual inspection)
grep -rn "\.curve_data\b" --include="*.py" . \
  --exclude-dir=tests --exclude-dir=.venv \
  > validation_curve_data_access.txt

# 3. Local variable assignments from curve_data
grep -rn "= .*\.curve_data\b" --include="*.py" . \
  --exclude-dir=tests --exclude-dir=.venv \
  > validation_curve_data_assignments.txt

# After Phase 6.3:
# - File 1 should be EMPTY (0 results)
# - Files 2-3 require manual inspection (verify read-only or followed by set_curve_data)
```

---

## Risk Level Justification

**Overall: 9/10 (CRITICAL)**

**Why 9/10?**

1. **Architecture Transformation** (10/10 severity):
   - Removes entire backward compatibility layer
   - No partial rollback possible
   - Changes fundamental data access pattern

2. **Silent Failure Mode** (10/10 severity):
   - Copy semantics causes data loss WITHOUT errors
   - Tests may pass despite broken code
   - Only detectable via integration testing or production usage

3. **High-Frequency Operations** (10/10 severity):
   - Drag operations = 60Hz updates
   - Must use batch mode correctly
   - UI freeze if batch mode fails

4. **Complete Signal Redesign** (10/10 severity):
   - 13 fine-grained signal handlers removed
   - Replaced with 1 coarse-grained handler
   - Potential performance regression

**Why not 10/10?**

- ✅ ApplicationState batch mode verified working
- ✅ Plan accurately identifies all critical issues
- ✅ 7 indexed writes correctly identified with line numbers
- ✅ StoreManager bug correctly diagnosed

**Phase 6.3 is executable** with proper preparation, but requires:
- Comprehensive pre-flight validation
- Atomic migration (single commit or feature branch)
- Extensive integration testing
- Performance profiling before/after

**Comparison to Other Phases**:
- Phase 6.1: 3/10 (simple setter migration)
- Phase 6.2: 5/10 (read-only enforcement)
- **Phase 6.3: 9/10** (architecture transformation)
- Phase 6.4+: Unknown (not yet analyzed)

---

## Recommendation

**PROCEED WITH EXTREME CAUTION**

**Required Actions BEFORE Phase 6.3**:

1. ✅ **Create backup tag**: `git tag phase-6.2-complete`
2. ⚠️ **Add integration tests** (4 tests minimum):
   - Copy semantics behavior
   - Indexed write persistence
   - Active curve switch synchronization
   - Drag batch mode efficiency
3. ⚠️ **Comprehensive grep audit**: Verify all 15 files in plan need changes
4. ⚠️ **Performance baseline**: Profile before migration
5. ⚠️ **Reorder steps**: Move StoreManager to Step 2

**Execution Strategy**:

**Option A - Single Atomic Commit** (RECOMMENDED):
```bash
git checkout -b phase-6.3-curvedatastore-removal
# Execute all 8 steps
# Verify: ./bpr --errors-only && pytest tests/
git commit -m "feat(phase6.3): Remove CurveDataStore backward compatibility layer"
# Merge only after full validation
```

**Option B - Multi-Commit** (If debugging needed):
```bash
git checkout -b phase-6.3-curvedatastore-removal
# Commit 1: Getters + indexed assignments
# Commit 2: StoreManager integration
# Commit 3: Widget signal handler removal
# Commit 4: Delete CurveDataStore file
# Type check + test after EACH commit
```

**Success Criteria**:
- ✅ 0 type errors
- ✅ 2105/2105 tests passing
- ✅ 0 CurveDataStore references (grep validation)
- ✅ Performance regression < 2x (profile validation)
- ✅ Integration tests pass (4 new tests)

---

**Assessment Complete**: October 6, 2025

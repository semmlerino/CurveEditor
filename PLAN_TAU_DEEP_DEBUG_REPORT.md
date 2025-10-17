# Plan TAU Deep Debugging Report
**Generated:** 2025-10-15
**Analysis Type:** Critical Path Deep Dive
**Severity:** 🔴 CRITICAL IMPLEMENTATION GAP DETECTED

---

## 🚨 EXECUTIVE SUMMARY

**CRITICAL FINDING: Phase 1 of Plan TAU was documented as complete but NOT actually implemented.**

Three of four Phase 1 tasks claim to be complete with git commits, but code inspection reveals:
- ❌ **Task 1.1 (Property Setter Races):** PARTIALLY implemented (2/3 locations still broken)
- ❌ **Task 1.2 (Qt.QueuedConnection):** NOT implemented (0/50+ connections added)
- ❌ **Task 1.3 (hasattr() Removal):** NOT implemented (46/46 instances remain)
- ⚠️ **Task 1.4 (Coordinator Verification):** Documentation added, but contradicts actual code

**Impact:** Timeline desync bugs that Phase 1 claimed to fix are STILL PRESENT. The application runs entirely synchronously despite documentation claiming asynchronous signal/slot architecture.

**Root Cause:** Documentation and commit messages describe fixes that were never applied to the codebase.

---

## 🔴 CRITICAL BUGS

### BUG #1: Qt.QueuedConnection Completely Missing
**Severity:** 🔴 CRITICAL
**Type:** Race Condition / Synchronous Execution
**Status:** Phase 1 Task 1.2 NOT implemented

**Expected (per Phase 1 docs):**
```python
# ui/controllers/frame_change_coordinator.py:111
_ = self.main_window.state_manager.frame_changed.connect(
    self.on_frame_changed,
    Qt.QueuedConnection  # EXPLICIT: Defer to event loop
)
```

**Reality:**
```python
# ui/controllers/frame_change_coordinator.py:111
_ = self.main_window.state_manager.frame_changed.connect(self.on_frame_changed)
# Uses default Qt.AutoConnection → DirectConnection (synchronous!)
```

**Evidence:**
```bash
$ grep -r "Qt.QueuedConnection" ui/ services/ --include="*.py" | wc -l
3  # All 3 are in COMMENTS, not actual code!
```

**Impact:**
- All signal connections execute synchronously
- State updates trigger immediate nested callbacks
- Reentrancy risks in frame change handling
- Timeline desync bugs still possible despite "fix"

**Files Affected:**
- `ui/controllers/frame_change_coordinator.py:111` - Missing QueuedConnection
- `ui/state_manager.py:72-73` - Missing QueuedConnection on ApplicationState forwards
- `ui/controllers/signal_connection_manager.py:143-232` - All 40+ connections missing QueuedConnection
- `ui/timeline_tabs.py:376-378` - Missing QueuedConnection on ApplicationState signals
- `ui/timeline_tabs.py:315` - Explicitly uses DirectConnection with comment justifying it

**Verification:**
```bash
# Phase 1 claimed: "50+ explicit Qt.QueuedConnection connections"
# Reality: 0 actual uses (only comments)
grep -r "\.connect(" ui/controllers/ | grep -v "Qt.QueuedConnection" | wc -l
# Returns: ~45 connections without explicit type
```

---

### BUG #2: Property Setter Race Conditions NOT Fixed
**Severity:** 🔴 CRITICAL
**Type:** Race Condition
**Status:** Phase 1 Task 1.1 PARTIALLY implemented

**Location 1:** `ui/state_manager.py:454`

**Expected (per Phase 1 docs):**
```python
if self.current_frame > count:
    self._app_state.set_frame(count)  # ✅ FIXED: Direct state update
```

**Reality:**
```python
if self.current_frame > count:
    self.current_frame = count  # ❌ STILL BUGGY: Property setter
```

**Location 2:** `ui/state_manager.py:107`

**Expected:**
```python
if self.current_frame > new_total:
    self._app_state.set_frame(new_total)  # ✅ FIXED: Direct state update
```

**Reality:**
```python
if self.current_frame > new_total:
    self.current_frame = new_total  # ❌ STILL BUGGY: Property setter
```

**Impact:**
- Property setter triggers synchronous signal emission
- Frame changes during image loading can cause timeline desync
- Race window: State=N but UI waiting for queued callback (which never comes because no QueuedConnection!)

**Race Condition Sequence:**
```python
1. StateManager.total_frames = 100
2.   → _app_state.set_image_files([...])  # Updates state synchronously
3.   → if current_frame > 100:
4.       → self.current_frame = 100  # ❌ Property setter
5.           → _app_state.set_frame(100)  # Emits frame_changed
6.               → StateManager.frame_changed.emit(100)  # DirectConnection!
7.                   → FrameChangeCoordinator.on_frame_changed(100)  # Immediate execution
8.                       → Updates UI synchronously
9.                       → If coordinator modifies state → NESTED EXECUTION!
```

**Files Affected:**
- `ui/state_manager.py:454` (total_frames.setter)
- `ui/state_manager.py:107` (set_image_files)

**Note:** `ui/timeline_tabs.py:284-286` has similar pattern but was documented as intentional in set_frame_range.

---

### BUG #3: hasattr() Removal NOT Implemented
**Severity:** 🟡 MEDIUM
**Type:** Type Safety / CLAUDE.md Violation
**Status:** Phase 1 Task 1.3 NOT implemented

**Expected (per Phase 1 docs):**
```python
# Success Metrics:
# - ✅ 0 hasattr() in production code (ui/, services/, core/)
```

**Reality:**
```bash
$ grep -r "hasattr(" ui/ services/ core/ --include="*.py" | wc -l
46  # Exact same count as before Task 1.3!
```

**Impact:**
- CLAUDE.md compliance not achieved
- Type checker loses attribute information
- ~30% of type ignores could be eliminated but aren't

**Files Still Affected (per Phase 1 docs):**
- `ui/image_sequence_browser.py` - 12 instances
- `ui/controllers/timeline_controller.py` - 9 instances (in __del__)
- `ui/controllers/signal_connection_manager.py` - 5 instances
- `services/interaction_service.py` - 4 instances
- `core/commands/shortcut_commands.py` - 3 instances
- 10 more files with 1-2 instances each

**Verification:**
```bash
# Check if any replacements were made
grep -r "is not None" ui/controllers/timeline_controller.py | grep -c "playback_timer\|frame_spinbox"
# Expected: 9 (if Task 1.3 was done)
# Reality: 0
```

---

### BUG #4: FrameChangeCoordinator Uses DirectConnection Despite Documentation
**Severity:** 🔴 CRITICAL
**Type:** Documentation Mismatch / Race Condition
**Status:** Code contradicts Phase 1 fixes and commit messages

**Documentation Claims:**
- Commit message: "Fix timeline-curve desynchronization with Qt.QueuedConnection"
- Phase 1 docs: "Uses Qt.QueuedConnection for deterministic ordering"

**Reality:**
```python
# ui/controllers/frame_change_coordinator.py:111
# Connect with default Qt.AutoConnection (DirectConnection for same thread)
# Immediate execution for responsive playback; timeline_tabs handles desync prevention
_ = self.main_window.state_manager.frame_changed.connect(self.on_frame_changed)
```

**Evidence from Comments:**
```python
# Line 100: "Timeline_tabs uses Qt.QueuedConnection to prevent desync, but coordinator
#            can execute synchronously for better playback performance."
```

**Impact:**
- Frame changes trigger immediate synchronous execution
- No deterministic ordering (depends on connection order)
- Violates documented architecture

---

### BUG #5: StateManager Signal Forwarding Creates Double DirectConnection Chain
**Severity:** 🔴 CRITICAL
**Type:** Nested Execution / Reentrancy Risk
**Status:** Signal forwarding without QueuedConnection

**Location:** `ui/state_manager.py:72-73`

**Code:**
```python
# Forward ApplicationState signals (subscribers use Qt.QueuedConnection)
# StateManager forwards immediately; subscribers defer with QueuedConnection
# to prevent synchronous nested execution
_ = self._app_state.frame_changed.connect(self.frame_changed.emit)
_ = self._app_state.selection_changed.connect(self._on_app_state_selection_changed)
```

**Comment Says:** "subscribers use Qt.QueuedConnection"
**Reality:** No subscribers use Qt.QueuedConnection (see Bug #1)

**Impact:**
Creates deeply nested synchronous execution:
```
ApplicationState.set_frame(42)
  → emit frame_changed (DirectConnection)
    → StateManager.frame_changed.emit() (DirectConnection)
      → FrameChangeCoordinator.on_frame_changed(42) (DirectConnection)
        → _update_timeline_widgets()
          → timeline_tabs._on_frame_changed()
            → Potentially calls set_frame() again → REENTRANCY!
```

**Reentrancy Protection:** ApplicationState has `_emitting_batch` flag, but it only protects batch flush, not normal emissions.

---

### BUG #6: Batch Update Signal Deduplication Is Lossy
**Severity:** 🟡 MEDIUM (but untested - not used in production)
**Type:** Data Loss in Batch Operations
**Status:** Latent bug in unused feature

**Location:** `stores/application_state.py:979-994`

**Code:**
```python
def _flush_pending_signals(self) -> None:
    """Emit all pending signals (deduplicated)."""
    # Deduplicate by signal type - last emission wins
    unique_signals: dict[SignalInstance, tuple[Any, ...]] = {}
    for signal, args in self._pending_signals:
        unique_signals[signal] = args  # ❌ BUG: Key is signal instance, not (signal, curve_name)
```

**Issue:** When multiple curves are updated in a batch, only the LAST update is kept:

```python
with state.batch_updates():
    state.set_selection("Track1", {1, 2, 3})  # Queued: selection_changed(Track1)
    state.set_selection("Track2", {4, 5, 6})  # Overwrites previous!
# After batch: Only Track2's selection is emitted, Track1's update is LOST
```

**Root Cause:** Dictionary key is the signal instance (e.g., `selection_changed` signal object), not a tuple of `(signal, curve_name)`. Both emissions map to the same key.

**Current Impact:** LOW - batch_updates() is defined but not used in production code:
```bash
$ grep -r "with.*batch_updates()" ui/ services/ | wc -l
0  # Only used in tests (21 occurrences)
```

**Future Risk:** HIGH - If batch_updates() is adopted, multi-curve operations will silently lose data.

**Fix Required:**
```python
# Change deduplication key to include curve-specific args
unique_signals: dict[tuple[SignalInstance, ...], tuple[Any, ...]] = {}
for signal, args in self._pending_signals:
    key = (signal, *args)  # Include args in key
    unique_signals[key] = args
```

---

## ⚠️ SIGNAL/THREADING ISSUES

### Issue #1: No Thread Safety Assertions in Services
**Files:** `services/data_service.py`, `services/interaction_service.py`, etc.

**Observation:** ApplicationState has `_assert_main_thread()` checks, but services don't verify thread context.

**Risk:** Services can be called from worker threads without detection.

**Recommendation:** Add thread assertions to service entry points:
```python
def some_service_method(self):
    assert QThread.currentThread() == QApplication.instance().thread()
    # ... rest of method
```

---

### Issue #2: Signal Connection Ordering Undefined
**Impact:** Without Qt.QueuedConnection, execution order depends on connection order (non-deterministic).

**Example:** If timeline_tabs connects before FrameChangeCoordinator, timeline updates before coordinator invalidates caches → stale data visible.

**Current Mitigation:** FrameChangeCoordinator is connected via SignalConnectionManager which runs early.

**Proper Fix:** Use Qt.QueuedConnection for deterministic event-loop-based ordering.

---

### Issue #3: QThread Workers Look Good (Post-Refactor)
**Status:** ✅ VERIFIED

QThread refactoring (commit d2ceeaf) successfully modernized workers:
- `DirectoryScanWorker` uses `requestInterruption()` / `isInterruptionRequested()`
- `ProgressWorker` uses Qt interruption API
- Explicit Qt.QueuedConnection on cross-thread signals (image browser)

**No issues found in worker thread implementations.**

---

## 🔍 EDGE CASES & RESOURCE MANAGEMENT

### Edge Case #1: Widget Destruction During Signal Emission
**Location:** `ui/timeline_tabs.py:254-263` (__del__)

**Code:**
```python
def __del__(self):
    try:
        if self._app_state is not None:
            _ = self._app_state.curves_changed.disconnect(self._on_curves_changed)
    except (RuntimeError, AttributeError):
        pass  # Already disconnected or objects destroyed
```

**Assessment:** ✅ CORRECT - Proper cleanup with defensive error handling.

**Pattern Used Throughout:**
- timeline_tabs, timeline_controller, signal_connection_manager all use similar pattern
- Catches RuntimeError (widget deleted) and AttributeError (attribute missing)

---

### Edge Case #2: Frame Clamping Race
**Location:** `ui/state_manager.py:406-411` (current_frame.setter)

**Comment in Code:**
```python
# Note: Signal emission happens before frame clamping in set_image_files(),
# creating a brief window where current_frame may exceed total_frames.
# Observers should clamp defensively if needed.
```

**Issue:** Documented race condition but no defensive clamping in all observers.

**Impact:** Observers can receive invalid frame numbers (e.g., frame 101 when total_frames=100).

**Recommendation:** Add defensive clamping in FrameChangeCoordinator:
```python
def on_frame_changed(self, frame: int) -> None:
    # Defensive clamp (handles race condition from set_image_files)
    total_frames = self.main_window.state_manager.total_frames
    frame = max(1, min(frame, total_frames))
    # ... rest of method
```

---

### Edge Case #3: Batch Update Nesting
**Location:** `stores/application_state.py:1014-1016` (batch_updates context manager)

**Code:**
```python
# Support nesting with reference counting
self._batch_depth += 1
is_outermost = self._batch_depth == 1
```

**Assessment:** ✅ CORRECT - Properly supports nested batch operations.

**Testing:** Verify with:
```python
with state.batch_updates():
    state.set_frame(10)
    with state.batch_updates():  # Nested
        state.set_selection("Track1", {1, 2})
    # Inner batch doesn't emit
# Outer batch emits both signals
```

---

## 📊 TEST COVERAGE GAPS

### Gap #1: No Tests for Qt.QueuedConnection Behavior
**Impact:** Critical architectural feature untested.

**Missing Tests:**
```python
def test_frame_change_uses_queued_connection(main_window):
    """Verify frame_changed signal uses Qt.QueuedConnection."""
    coordinator = main_window.frame_change_coordinator

    # Emit signal
    main_window.state_manager.frame_changed.emit(42)

    # Should NOT have been called yet (queued)
    assert coordinator.last_frame_update != 42

    # Process event loop
    QEventLoop().processEvents()

    # NOW it should have been called
    assert coordinator.last_frame_update == 42
```

**Current Status:** Phase 1 Task 1.4 mentions creating this test, but test file doesn't exist.

---

### Gap #2: No Tests for Property Setter Race Conditions
**Missing Test:**
```python
def test_total_frames_setter_race_condition():
    """Verify total_frames setter doesn't cause nested execution."""
    state_manager = StateManager()

    # Track callback order
    callbacks = []

    def on_frame_changed(frame):
        callbacks.append(('frame', frame))

    def on_total_changed(total):
        callbacks.append(('total', total))

    state_manager.frame_changed.connect(on_frame_changed)
    state_manager.total_frames_changed.connect(on_total_changed)

    # Set total_frames (triggers frame clamping)
    state_manager.total_frames = 50

    # Verify no nested execution (would show as interleaved callbacks)
    assert callbacks == [('total', 50), ('frame', 50)]  # Sequential, not nested
```

---

### Gap #3: No Tests for Batch Update Multi-Curve Deduplication Bug
**Missing Test:**
```python
def test_batch_updates_multi_curve_signals():
    """Verify batch updates don't lose multi-curve signals."""
    state = get_application_state()

    emitted_selections = []
    def on_selection(indices, curve_name):
        emitted_selections.append((curve_name, indices))

    state.selection_changed.connect(on_selection)

    with state.batch_updates():
        state.set_selection("Track1", {1, 2, 3})
        state.set_selection("Track2", {4, 5, 6})

    # FAILS with current implementation - only Track2 is emitted
    assert len(emitted_selections) == 2
    assert ("Track1", {1, 2, 3}) in emitted_selections
    assert ("Track2", {4, 5, 6}) in emitted_selections
```

---

## 🎯 RECOMMENDATIONS

### Priority 1: CRITICAL (Fix Immediately)

**1. Implement Phase 1 Task 1.2 (Qt.QueuedConnection)**
- **Effort:** 4-6 hours
- **Files:** 7 files, 50+ connections
- **Template:**
```python
from PySide6.QtCore import Qt

_ = signal.connect(
    slot,
    Qt.QueuedConnection  # EXPLICIT: Defer to event loop
)
```

**Locations:**
- `ui/controllers/frame_change_coordinator.py:111`
- `ui/state_manager.py:72-73`
- `ui/controllers/signal_connection_manager.py:143-232`
- `ui/timeline_tabs.py:376-378, 315`
- `ui/controllers/multi_point_tracking_controller.py:62-64`
- `ui/image_sequence_browser.py` (already has some, verify all)

**Verification:**
```bash
grep -r "\.connect(" ui/controllers/ ui/state_manager.py | grep -v "Qt.QueuedConnection" | grep -v "# Widget"
# Should return: 0 cross-component connections without explicit type
```

---

**2. Fix Property Setter Race Conditions (Complete Task 1.1)**
- **Effort:** 30 minutes
- **Files:** `ui/state_manager.py` (2 locations)

**Changes:**
```python
# ui/state_manager.py:454 (total_frames.setter)
if self.current_frame > count:
    self._app_state.set_frame(count)  # Direct update, skip property

# ui/state_manager.py:107 (set_image_files)
if self.current_frame > new_total:
    self._app_state.set_frame(new_total)  # Direct update, skip property
```

**Verification:**
```bash
grep -n "self.current_frame = " ui/state_manager.py
# Should return: Only property setter definition, not usage in setters
```

---

**3. Add Test Coverage for Signal Timing**
- **Effort:** 2-3 hours
- **File:** Create `tests/test_signal_timing.py`
- **Tests:**
  - `test_frame_change_uses_queued_connection`
  - `test_property_setter_no_nested_execution`
  - `test_signal_forwarding_queued`

---

### Priority 2: HIGH (Fix Within Week)

**4. Implement Phase 1 Task 1.3 (hasattr() Removal)**
- **Effort:** 8-12 hours
- **Files:** 15 files, 46 instances
- **Automated Script:** Phase 1 docs provide `tools/fix_hasattr.py`

**Verification:**
```bash
grep -r "hasattr(" ui/ services/ core/ --include="*.py" | wc -l
# Expected: 0
```

---

**5. Fix Batch Update Signal Deduplication**
- **Effort:** 1 hour
- **File:** `stores/application_state.py:982-985`

**Change:**
```python
# Before
unique_signals: dict[SignalInstance, tuple[Any, ...]] = {}
for signal, args in self._pending_signals:
    unique_signals[signal] = args

# After (include args in key)
unique_signals: dict[tuple[Any, ...], tuple[Any, ...]] = {}
for signal, args in self._pending_signals:
    key = (id(signal), *args)  # Use signal ID + args as key
    unique_signals[key] = (signal, args)
```

**Add Test:**
```python
tests/stores/test_application_state_batch_multi_curve.py
```

---

### Priority 3: MEDIUM (Address in Next Sprint)

**6. Add Defensive Frame Clamping in Observers**
- **Effort:** 2 hours
- **Files:** FrameChangeCoordinator, timeline widgets

**7. Document Actual Signal Connection Strategy**
- **Effort:** 1 hour
- **Update:** CLAUDE.md with actual patterns (not aspirational ones)

**8. Add Thread Safety Assertions in Services**
- **Effort:** 3 hours
- **Pattern:**
```python
def _assert_main_thread(self) -> None:
    if QThread.currentThread() != QApplication.instance().thread():
        raise RuntimeError(f"{self.__class__.__name__} must be called from main thread")
```

---

## 📋 ROOT CAUSE ANALYSIS

### Why Did Phase 1 "Complete" Without Implementation?

**Hypothesis 1:** Documentation-Driven Development Gone Wrong
- Plan TAU was written as prescriptive documentation
- Commit messages described intended changes, not actual changes
- No verification that code matched documentation

**Hypothesis 2:** Partial Implementation Mistaken for Complete
- Some changes were made (e.g., QThread refactoring)
- Assumed related changes were also complete
- Verification tests weren't run or were mocked

**Hypothesis 3:** Incomplete Git Staging
- Changes were made locally but not staged/committed
- Work-in-progress left in working directory
- Different changes committed than intended

---

### How to Prevent This

**1. Verification Before "Complete"**
```bash
# For Task 1.2 (Qt.QueuedConnection)
grep -r "Qt.QueuedConnection" ui/ services/ | wc -l
# Must be: >= 50

# For Task 1.3 (hasattr)
grep -r "hasattr(" ui/ services/ core/ --include="*.py" | wc -l
# Must be: 0

# For Task 1.1 (Property setters)
grep -n "self.current_frame = " ui/state_manager.py | wc -l
# Must be: 1 (only the @property setter definition)
```

**2. Automated Verification Script**
Create `plan_tau/verify_phase1.sh`:
```bash
#!/bin/bash
set -e

echo "=== Phase 1 Verification ==="

# Task 1.2: Qt.QueuedConnection count
COUNT=$(grep -r "Qt.QueuedConnection" ui/ services/ --include="*.py" | grep -v "^[[:space:]]*#" | wc -l)
if [ "$COUNT" -ge 50 ]; then
    echo "✅ Task 1.2: $COUNT explicit QueuedConnection uses"
else
    echo "❌ Task 1.2 FAILED: Only $COUNT uses, need 50+"
    exit 1
fi

# Task 1.3: hasattr() count
COUNT=$(grep -r "hasattr(" ui/ services/ core/ --include="*.py" | wc -l)
if [ "$COUNT" -eq 0 ]; then
    echo "✅ Task 1.3: 0 hasattr() in production code"
else
    echo "❌ Task 1.3 FAILED: Found $COUNT hasattr() instances"
    exit 1
fi

# Task 1.1: Property setter race conditions
COUNT=$(grep -n "self.current_frame = " ui/state_manager.py | grep -v "@property" | grep -v "def current_frame" | wc -l)
if [ "$COUNT" -eq 0 ]; then
    echo "✅ Task 1.1: No property setter races"
else
    echo "❌ Task 1.1 FAILED: Found $COUNT property setter uses"
    exit 1
fi

echo "=== All Phase 1 Tasks Verified ==="
```

**3. Require Verification in Commit Message**
```
fix(signals): Add explicit Qt.QueuedConnection to 52 cross-component signals

Verification:
✅ grep -r "Qt.QueuedConnection" ui/ services/ | wc -l → 52
✅ All tests passing: 2345/2345
✅ ./bpr --errors-only → 0 errors
```

---

## 📈 SEVERITY SUMMARY

| Severity | Count | Description |
|----------|-------|-------------|
| 🔴 CRITICAL | 5 | Race conditions, synchronous execution, documentation mismatches |
| 🟡 MEDIUM | 2 | Type safety violations, latent bugs |
| ⚠️ WARNING | 3 | Edge cases, missing defensive code |
| ℹ️ INFO | 3 | Test coverage gaps, documentation needs |

**Total Issues:** 13 (5 critical, 2 medium, 3 warnings, 3 info)

---

## ✅ NEXT STEPS

1. **Immediate:** Run verification script to confirm current state
2. **Day 1:** Implement Priority 1 fixes (Qt.QueuedConnection + property setters)
3. **Day 2:** Add test coverage for signal timing
4. **Week 1:** Complete hasattr() removal (Task 1.3)
5. **Week 2:** Fix batch update deduplication
6. **Sprint Plan:** Address medium priority items

**Estimated Effort to Fix All Critical Issues:** 2-3 days

---

**Report Compiled By:** Deep-Debugger Agent
**Verification Methods:** Code inspection, grep analysis, pattern matching, sequential thinking
**Confidence Level:** HIGH (code-verified, not speculation)

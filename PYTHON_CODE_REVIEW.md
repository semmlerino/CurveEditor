# Code Review: ELIMINATE_COORDINATOR_PLAN.md

**Review Date**: October 19, 2025
**Reviewer**: Python Code Reviewer Agent
**Branch**: `fix/eliminate-frame-coordinator-v2`
**Total Test Count**: ~2439 tests

---

## Executive Summary

**Overall Assessment**: MEDIUM-HIGH RISK with 3 critical bugs, 2 architectural issues, and 1 missing component. The plan's strategy is sound (direct connections > coordinator indirection), but execution details contain logic errors and incomplete signal cleanup.

**Risk Level Breakdown**:
- **3 HIGH RISK** issues (could break functionality)
- **2 MEDIUM RISK** issues (need validation/rework)
- **3 LOW RISK** issues (minor concerns)
- **5 VALIDATED** assumptions (confirmed by code inspection)

**Recommendation**: Fix critical issues before proceeding. Time estimate of 3-5 hours is realistic IF critical bugs are addressed.

---

## HIGH RISK Issues (Must Fix Before Implementation)

### 1. CRITICAL: Missing TimelineTabWidget Signal Disconnection

**Location**: Phase 1.3, Phase 3.2
**Severity**: HIGH - Memory leak risk

**Problem**:
```python
# Plan says (Phase 1.3):
# "TimelineTabWidget: Change connection from StateManager to ApplicationState"
# "Update cleanup in __del__ to disconnect from app_state"
```

**Code Reality** (ui/timeline_tabs.py:361-368):
```python
def _connect_signals(self) -> None:
    """Connect to ApplicationState signals for reactive updates."""
    # Connect to ApplicationState signals
    _ = self._app_state.curves_changed.connect(self._on_curves_changed)
    _ = self._app_state.active_curve_changed.connect(self._on_active_curve_changed)
    _ = self._app_state.selection_changed.connect(self._on_selection_changed)
    # NO frame_changed connection exists!
```

**Finding**: `TimelineTabWidget` does NOT connect to `frame_changed` signal at all. It only connects to:
- `curves_changed`
- `active_curve_changed`
- `selection_changed`

The plan assumes a `state_manager.frame_changed` connection exists to replace, but **there is no such connection**.

**Impact**: Phase 1.3 and Phase 3.2 steps are INVALID. Attempting to change a non-existent connection will waste time.

**Fix**:
1. Verify if TimelineTabWidget actually needs frame change notifications
2. If yes: Add NEW connection (not "change" existing)
3. If no: Remove TimelineTabWidget from Phase 1.3 and Phase 3.2 entirely

**Root Cause**: Plan assumed TimelineTabWidget uses StateManager forwarding, but code shows it bypasses StateManager and connects directly to ApplicationState already.

---

### 2. CRITICAL: Incorrect SignalManager Usage Pattern

**Location**: Phase 1.1 (lines 110-118)
**Severity**: HIGH - Type error, connection will fail

**Problem**:
```python
# Plan proposes:
self.signal_manager.connect(
    self._app_state.frame_changed,
    self._on_frame_changed,
    "app_state_frame_changed"
)
```

**Code Reality** (core/signal_manager.py:124-143):
```python
def connect(
    self,
    signal: Signal | SignalInstance,
    slot: Callable[..., None],
    signal_name: str | None = None,
) -> SignalConnection:  # ← Returns SignalConnection, not bool
    """Connect a signal and track the connection."""
    connection = SignalConnection(signal, slot, signal_name)
    if connection.connect():
        self.connections.append(connection)
    return connection  # ← Return value
```

**Finding**: Plan doesn't capture return value. While not fatal (SignalManager appends internally), best practice is:
```python
_ = self.signal_manager.connect(...)  # Explicitly ignore return
```

**Impact**: MEDIUM - Code will work but violates ruff F841 (unused return value in some contexts).

**Fix**: Use `_ = self.signal_manager.connect(...)` pattern (matches existing CurveViewWidget pattern at line 175).

---

### 3. CRITICAL: Missing ViewManagementController Signal Connection

**Location**: Phase 1.2 (lines 122-132)
**Severity**: HIGH - Incomplete implementation

**Problem**:
```python
# Plan says (Phase 1.2):
# "Connect to ApplicationState (get reference from MainWindow)"
# "Ensure cleanup on controller destruction"
```

**Code Reality**:
- ViewManagementController does NOT have a `signal_manager` attribute
- ViewManagementController is not a QWidget (it's a plain controller class)
- No existing pattern for signal cleanup in this controller

**Finding**: Plan assumes SignalManager pattern applies, but ViewManagementController is not structured for it.

**Current Architecture** (ui/controllers/view_management_controller.py):
```python
class ViewManagementController:
    """Controller for view management operations."""
    def __init__(self, main_window: MainWindow):
        self.main_window = main_window
        # No signal_manager, no QObject inheritance
```

**Impact**: Phase 1.2 connection will fail. No clear cleanup mechanism exists.

**Fix Options**:
1. **Option A** (Recommended): Add signal connection in MainWindow, clean up in MainWindow destructor
   ```python
   # In MainWindow.__init__:
   self._app_state.frame_changed.connect(
       self.view_management_controller._on_frame_changed
   )

   # In MainWindow.__del__ or cleanup:
   self._app_state.frame_changed.disconnect(
       self.view_management_controller._on_frame_changed
   )
   ```

2. **Option B**: Make ViewManagementController inherit QObject, add SignalManager
   - More invasive, requires architectural change
   - Not recommended for this refactor scope

**Recommendation**: Use Option A - MainWindow owns the connection lifecycle.

---

## MEDIUM RISK Issues (Need Validation)

### 4. Atomic Data Capture Pattern May Be Unnecessary

**Location**: Phase 1.1 (lines 96-100)
**Severity**: MEDIUM - Architectural confusion

**Problem**:
```python
# Plan proposes:
def _on_frame_changed(self, frame: int) -> None:
    """Handle frame changes with atomic data capture (defensive pattern)."""
    # Atomic capture - defensive against curve switching during handler
    if (cd := self._app_state.active_curve_data) is None:
        return
    curve_name, curve_data = cd
```

**Question**: Why capture `curve_data` if it's not used in the handler?

**Actual Usage** (proposed):
```python
# Apply centering if enabled
if self.centering_mode:
    self.center_on_frame(frame)  # ← Uses frame parameter only
```

**Code Reality** (ui/controllers/view_camera_controller.py:318-342):
```python
def center_on_frame(self, frame: int) -> None:
    """Center view on a specific frame using gap-aware position logic."""
    if not self.widget.curve_data:  # ← Re-fetches curve_data internally
        logger.warning(f"[CENTER] No curve data available for frame {frame}")
        return

    # Use gap-aware position lookup through data service
    data_service = get_data_service()
    position = data_service.get_position_at_frame(self.widget.curve_data, frame)
```

**Finding**: `center_on_frame()` fetches `curve_data` internally via `self.widget.curve_data`. The "atomic capture" in `_on_frame_changed` is NOT used.

**Impact**: Code works but adds unnecessary complexity. Violates YAGNI principle.

**Analysis**:
- **Atomic capture IS needed** if handler directly uses `curve_data`
- **Atomic capture NOT needed** if handler delegates to methods that re-fetch
- Current proposal: capture but don't use → Dead code

**Recommendation**: Simplify to:
```python
def _on_frame_changed(self, frame: int) -> None:
    """Handle frame changes - apply centering and invalidate caches."""
    if self.centering_mode:
        self.center_on_frame(frame)

    self.invalidate_caches()
    self.update()
```

**Alternative**: If defensive pattern desired for future-proofing, use it:
```python
def _on_frame_changed(self, frame: int) -> None:
    """Handle frame changes with defensive curve data check."""
    if self._app_state.active_curve_data is None:
        return  # No active curve, nothing to center on

    if self.centering_mode:
        self.center_on_frame(frame)

    self.invalidate_caches()
    self.update()
```

---

### 5. Test Coverage Gap: Integration Test Design Incomplete

**Location**: Phase 0.1 (lines 34-56)
**Severity**: MEDIUM - Test may not reproduce actual bug

**Problem**:
```python
# Plan proposes:
def test_rapid_frame_changes_via_signal_chain(qtbot, main_window):
    """Test actual signal chain with rapid scrubbing (reproduces user bug)."""
    app_state = get_application_state()
    curve_widget = main_window.curve_widget

    # Enable centering mode
    curve_widget.centering_mode = True

    # Simulate rapid scrubbing (100 frames in 1 second)
    for frame in range(1, 101):
        app_state.set_frame(frame)
        qtbot.wait(10)  # 10ms per frame
```

**Issues**:

1. **Missing curve data**: Test enables centering but doesn't load curve data
   ```python
   # NEEDED:
   app_state.set_curve_data("Track1", test_data)
   app_state.set_active_curve("Track1")
   ```

2. **No assertion on visual jumps**: Test says "Verify: No visual jumps" but only asserts:
   ```python
   assert curve_widget.last_painted_frame == 100
   ```
   This doesn't detect centering jumps, only final frame rendering.

3. **Timing-dependent**: `qtbot.wait(10)` may not reliably reproduce QueuedConnection queue buildup on all systems.

**Recommendation**: Enhance test to:
```python
def test_rapid_frame_changes_via_signal_chain(qtbot, main_window):
    """Test actual signal chain with rapid scrubbing (reproduces user bug)."""
    app_state = get_application_state()
    curve_widget = main_window.curve_widget

    # Load curve data (CRITICAL: missing in plan)
    test_data = [(i, 100.0 + i, 200.0 + i) for i in range(1, 101)]
    app_state.set_curve_data("Track1", test_data)
    app_state.set_active_curve("Track1")

    # Enable centering mode
    curve_widget.centering_mode = True

    # Track pan offset changes to detect jumps
    pan_offset_history = []

    # Simulate rapid scrubbing (100 frames in 1 second)
    for frame in range(1, 101):
        app_state.set_frame(frame)
        qtbot.wait(10)  # 10ms per frame
        pan_offset_history.append((frame, curve_widget.pan_offset_x, curve_widget.pan_offset_y))

    # Verify: Pan offsets should change smoothly (monotonic for linear motion)
    # If QueuedConnection bug exists, we'd see non-monotonic jumps
    for i in range(1, len(pan_offset_history)):
        prev_frame, prev_x, prev_y = pan_offset_history[i - 1]
        curr_frame, curr_x, curr_y = pan_offset_history[i]

        # For linear motion, offset changes should be consistent
        # Large deviations indicate "jump" from stale frame centering
        # (Exact threshold depends on test data - 50 pixels is example)
        x_delta = abs(curr_x - prev_x)
        y_delta = abs(curr_y - prev_y)
        assert x_delta < 50, f"Frame {curr_frame}: X offset jumped by {x_delta}"
        assert y_delta < 50, f"Frame {curr_frame}: Y offset jumped by {y_delta}"
```

---

## LOW RISK Issues (Minor Concerns)

### 6. Potential Race: Direct Connection Ordering Not Guaranteed

**Location**: Phase 1 architecture
**Severity**: LOW - Unlikely to cause issues but worth noting

**Context**: Plan assumes AutoConnection = DirectConnection = synchronous execution.

**Reality Check**:
```python
# Qt documentation: AutoConnection behavior
AutoConnection:
- If receiver in same thread as emitter → DirectConnection (synchronous)
- If receiver in different thread → QueuedConnection (asynchronous)
```

**Finding**: Plan is correct for single-thread Qt app. All components run in main thread.

**Potential Issue**: If future refactor moves background loading to worker thread, AutoConnection would become QueuedConnection, recreating the original bug.

**Mitigation**: Document thread assumption in code comments:
```python
# Uses AutoConnection (default) which becomes DirectConnection for same-thread
# signals. If components move to worker threads, must explicitly use DirectConnection.
_ = self._app_state.frame_changed.connect(self._on_frame_changed)
```

**Recommendation**: Add comment in Phase 1 implementation. No code change needed now.

---

### 7. Documentation Update Incomplete

**Location**: Phase 4.1 (lines 225-229)
**Severity**: LOW - Documentation drift

**Problem**:
```python
# Plan says:
# "Remove FrameChangeCoordinator from controllers list (line ~419)"
```

**Finding**: CLAUDE.md line 419 doesn't match current file (file is 434 lines). Reference is approximate.

**Actual Location** (CLAUDE.md:415-423):
```markdown
## UI Controllers

Specialized controllers in `ui/controllers/`:
1. **ActionHandlerController**: Menu/toolbar actions
2. **MultiPointTrackingController**: Multi-curve tracking, Insert Track
3. **PointEditorController**: Point editing logic
4. **SignalConnectionManager**: Signal/slot connections
5. **TimelineController**: Frame navigation, playback
6. **UIInitializationController**: UI component setup
7. **ViewCameraController**: Camera movement
8. **ViewManagementController**: View state (zoom, pan, fit)
9. **FrameChangeCoordinator**: Coordinates frame change responses  # ← Line to remove
```

**Impact**: Minor - just need to find the right line. Won't affect functionality.

**Recommendation**: When implementing Phase 4.1, search for "FrameChangeCoordinator" in CLAUDE.md rather than relying on line number.

---

### 8. StateManager Signal Forwarding Removal May Affect Unknown Consumers

**Location**: Phase 3.3 (lines 200-211)
**Severity**: LOW - Unlikely but worth checking

**Problem**: Plan removes `StateManager.frame_changed` signal entirely.

**Verification Needed**:
```bash
# Check for any remaining consumers
grep -r "state_manager.frame_changed" --include="*.py" --exclude-dir=tests
```

**Expected Result**: Only docs and the StateManager definition itself.

**Actual Result** (from earlier grep): 19 files, but most are docs/plans/archives.

**Recommendation**:
1. Run verification grep during Phase 3.1 (audit step)
2. If unexpected consumers found, update them BEFORE removing signal
3. Add deprecation warning if needed:
   ```python
   # In StateManager (temporary during migration):
   @deprecated("Use ApplicationState.frame_changed directly")
   frame_changed = Signal(int)
   ```

---

## VALIDATED Assumptions (Confirmed by Code)

### ✅ 1. Coordinator Uses QueuedConnection

**Plan Claim** (line 111, 318-343): Coordinator uses `Qt.QueuedConnection` causing race conditions.

**Code Confirmation** (ui/controllers/frame_change_coordinator.py:108-112):
```python
_ = self.main_window.state_manager.frame_changed.connect(
    self.on_frame_changed,
    Qt.QueuedConnection,  # ← CONFIRMED
)
```

**Status**: CORRECT ✅

---

### ✅ 2. Tests Bypass Signal Chain

**Plan Claim** (lines 371-383): Tests call `widget.on_frame_changed()` directly, bypassing signal chain.

**Code Confirmation** (tests/test_centering_toggle.py:93):
```python
# Trigger frame change
widget.on_frame_changed(2)  # ← Direct call, bypasses ApplicationState.set_frame()
```

**Status**: CORRECT ✅

This is why all 2400+ tests pass but production has centering jump bug.

---

### ✅ 3. Centering Uses Widget Dimensions, Not Background

**Plan Claim** (lines 353-367): Centering calculations use widget dimensions, not background image dimensions. Coordinator's justification is false.

**Code Confirmation** (ui/controllers/view_camera_controller.py:271):
```python
def center_on_point(self, x: float, y: float) -> None:
    screen_pos = self.data_to_screen(x, y)
    widget_center = QPointF(self.widget.width() / 2, self.widget.height() / 2)
    # ^^^ Uses WIDGET dimensions, NOT background dimensions
```

**Status**: CORRECT ✅

Coordinator's claim (frame_change_coordinator.py:27-30) about background affecting centering is **FALSE**.

---

### ✅ 4. Background Update Doesn't Trigger Repaint

**Plan Claim** (line 186-189): Background loading sets image but doesn't call `update()`.

**Code Confirmation** (ui/controllers/view_management_controller.py:341-343):
```python
if pixmap is not None:
    self.main_window.curve_widget.background_image = pixmap
    # NOTE: Don't call update() here - FrameChangeCoordinator handles the repaint
```

**Status**: CORRECT ✅

ViewManagementController explicitly relies on coordinator for repaint coordination.

---

### ✅ 5. SignalManager Provides Automatic Cleanup

**Plan Claim** (Phase 0.2, lines 59-69): SignalManager handles memory cleanup automatically.

**Code Confirmation** (core/signal_manager.py:113-117):
```python
# Try to hook into the owner's destruction
destroyed_signal = getattr(owner, "destroyed", None)
if destroyed_signal is not None:
    signal_instance = cast(SignalInstance, destroyed_signal)
    _ = signal_instance.connect(self.disconnect_all)
```

**Status**: CORRECT ✅

SignalManager will disconnect all signals when owner widget is destroyed.

---

## Risk Assessment Summary

| Risk Level | Count | Impact |
|------------|-------|--------|
| HIGH       | 3     | Implementation blockers |
| MEDIUM     | 2     | Need design decisions |
| LOW        | 3     | Minor polish needed |
| VALIDATED  | 5     | Plan assumptions correct |

**Overall Risk**: MEDIUM-HIGH

**Recommendation**: Address all HIGH risk issues before starting implementation. Revisit MEDIUM issues during Phase 1.

---

## Critical Fixes Required Before Implementation

### Fix 1: TimelineTabWidget Steps (HIGH PRIORITY)

**Action**: Remove TimelineTabWidget from plan

**Reason**: It already connects directly to ApplicationState, no StateManager forwarding to replace.

**Changes**:
- Phase 1.3: DELETE TimelineTabWidget bullet points
- Phase 3.2: VERIFY TimelineTabWidget not in audit list
- Phase 3.3: TimelineTabWidget already compliant

---

### Fix 2: ViewManagementController Connection Pattern (HIGH PRIORITY)

**Action**: Revise Phase 1.2 to use MainWindow-owned connection

**Revised Phase 1.2**:
```python
### 1.2 ViewManagementController Direct Connection

In MainWindow.__init__ (after controller creation):
```python
# Connect ViewManagementController to frame changes
# MainWindow owns connection lifecycle (controller is not QObject)
self._view_mgmt_frame_conn = self._app_state.frame_changed.connect(
    self.view_management_controller._on_frame_changed
)
```

In MainWindow cleanup (new method or __del__):
```python
def cleanup_signals(self) -> None:
    """Disconnect signals before destruction."""
    if hasattr(self, '_view_mgmt_frame_conn'):
        try:
            self._app_state.frame_changed.disconnect(
                self.view_management_controller._on_frame_changed
            )
        except (RuntimeError, TypeError):
            pass  # Already disconnected
```

In ViewManagementController:
```python
def _on_frame_changed(self, frame: int) -> None:
    """Update background image for frame (if images loaded)."""
    if self.image_filenames:
        self.update_background_for_frame(frame)
        logger.debug(f"[VIEW-MGMT] Background updated for frame {frame}")
```
```

---

### Fix 3: Integration Test Enhancement (MEDIUM PRIORITY)

**Action**: Add missing test data and pan offset assertions

**Revised Phase 0.1 Test**:
```python
def test_rapid_frame_changes_via_signal_chain(qtbot, main_window):
    """Test actual signal chain with rapid scrubbing (reproduces user bug)."""
    app_state = get_application_state()
    curve_widget = main_window.curve_widget

    # CRITICAL: Load curve data (missing in original plan)
    test_data = [(i, 100.0 + i, 200.0 + i) for i in range(1, 101)]
    app_state.set_curve_data("Track1", test_data)
    app_state.set_active_curve("Track1")

    # Enable centering mode
    curve_widget.centering_mode = True

    # Track pan offsets to detect jumps
    pan_history = []

    # Simulate rapid scrubbing (100 frames in 1 second)
    for frame in range(1, 101):
        app_state.set_frame(frame)
        qtbot.wait(10)  # 10ms per frame
        pan_history.append((curve_widget.pan_offset_x, curve_widget.pan_offset_y))

    # Verify smooth pan offset changes (no jumps from stale frames)
    for i in range(1, len(pan_history)):
        prev_x, prev_y = pan_history[i - 1]
        curr_x, curr_y = pan_history[i]

        # Linear motion → consistent offset deltas
        x_delta = abs(curr_x - prev_x)
        y_delta = abs(curr_y - prev_y)

        # If QueuedConnection bug exists, we'd see large non-monotonic jumps
        assert x_delta < 50, f"Frame {i+1}: X offset jumped {x_delta:.2f}px"
        assert y_delta < 50, f"Frame {i+1}: Y offset jumped {y_delta:.2f}px"

    # Verify final frame rendered
    assert curve_widget.last_painted_frame == 100
```

---

## Recommendations for Plan Improvement

### 1. Add Pre-Implementation Validation Phase

**Insert Before Phase 0**:

```markdown
## Phase -1: Pre-Implementation Validation (30 min)

**Objective**: Verify plan assumptions against current codebase

### -1.1 Verify Signal Connection Inventory
- [ ] Run: `grep -rn "state_manager.frame_changed.connect" --include="*.py" | grep -v test | grep -v docs`
- [ ] List actual consumers (expected: only TimelineTabWidget, Coordinator)
- [ ] Update plan if unexpected consumers found

### -1.2 Verify Component Structure
- [ ] Confirm CurveViewWidget has SignalManager
- [ ] Confirm ViewManagementController lacks SignalManager
- [ ] Confirm TimelineTabWidget signal connections
- [ ] Update plan based on findings

### -1.3 Review Memory Leak Test Pattern
- [ ] Read test_widget_lifecycle_no_memory_leaks pattern
- [ ] Ensure SignalManager cleanup verified
- [ ] Add Qt object deletion validation

**Checkpoint -1**:
- ✅ Signal connection inventory matches plan
- ✅ Component structure validated
- ✅ Memory test pattern understood
- ✅ Plan revised if needed

**Git Commit**: None (validation only)
```

---

### 2. Simplify Atomic Capture Pattern

**Revise Phase 1.1** (lines 93-108):

```python
def _on_frame_changed(self, frame: int) -> None:
    """Handle frame changes - apply centering and invalidate caches."""
    # Early exit if no active curve (defensive check)
    if self._app_state.active_curve_data is None:
        return

    # Apply centering if enabled
    # Note: center_on_frame() re-fetches curve_data internally for gap-aware lookup
    if self.centering_mode:
        self.center_on_frame(frame)

    # Invalidate caches and trigger repaint
    self.invalidate_caches()
    self.update()
```

**Rationale**:
- Removes unused `curve_name, curve_data = cd` unpacking
- Keeps defensive `active_curve_data` check for robustness
- Clarifies why re-fetch happens in `center_on_frame()`
- Adheres to YAGNI (don't capture data you don't use)

---

### 3. Add Explicit Qt Connection Type Documentation

**Add to Phase 1** (after step 1.3):

```markdown
### 1.4 Document Connection Type Strategy

Add comments to new connections:

```python
# CurveViewWidget._on_frame_changed connection:
# Uses AutoConnection (default) which becomes DirectConnection for same-thread
# signals, ensuring synchronous execution. If components move to worker threads
# in future refactors, must explicitly use Qt.DirectConnection.

# ViewManagementController._on_frame_changed connection:
# Same-thread signal ensures background loads synchronously before centering,
# though current centering logic doesn't depend on background (uses widget dims).
```

**Rationale**: Future-proof against threading changes.
```

---

### 4. Strengthen Rollback Strategy

**Add to Rollback Strategy section** (after line 282):

```markdown
**Validation before rollback** (prevent unnecessary rollback):
1. Check if failure is environmental (e.g., missing test data)
2. Review test output for actual vs expected behavior
3. Verify type errors with `./bpr` before assuming logic bug
4. Consider if fix is trivial (< 5 min) vs rollback overhead

**Emergency hotfix** (production issue):
1. `git revert <commit-hash>` (preserves history)
2. Create hotfix branch from main
3. Apply minimal fix (e.g., remove QueuedConnection)
4. Deploy hotfix
5. Continue refactor in separate branch
```

---

## Time Estimate Validation

**Plan Estimate**: 3-5 hours

**Revised Estimate** (with fixes): 4-6 hours

**Breakdown**:
- Phase -1 (new): 30 min (validation)
- Phase 0: 1.5-2 hours (integration test + fixes)
- Phase 1: 1.5-2 hours (with ViewManagementController pattern change)
- Phase 2: 30 min (unchanged)
- Phase 3: 1 hour (with pre-audit validation)
- Phase 4: 30 min (unchanged)

**Risk Buffer**: +1 hour for unexpected issues discovered during Phase 0 integration test

**Confidence**: MEDIUM (depends on integration test revealing additional issues)

---

## Final Recommendation

### Proceed with Implementation After Fixes

**Required Actions**:
1. ✅ Apply Fix 1 (TimelineTabWidget steps removal)
2. ✅ Apply Fix 2 (ViewManagementController connection pattern)
3. ✅ Apply Fix 3 (Integration test enhancement)
4. ⚠️ Add Phase -1 (pre-implementation validation)
5. ⚠️ Review MEDIUM risk issues (atomic capture, test design)

**Go/No-Go Criteria**:
- ✅ All HIGH risk fixes applied
- ✅ Phase -1 validation passes
- ✅ Integration test written and FAILS with current code (proves bug exists)
- ✅ Memory leak test pattern understood
- ✅ Git branch created and baseline metrics captured

**Confidence Level**: HIGH (after fixes applied)

**Expected Outcome**:
- Cleaner architecture (no coordinator indirection)
- Eliminated race conditions (synchronous frame handling)
- Simpler signal flow (direct connections)
- ~200 lines of code removed
- All 2400+ tests pass
- Centering works immediately during rapid scrubbing

---

## Appendix: Code Evidence

### A. Current Signal Connections (Baseline)

**FrameChangeCoordinator** (ui/controllers/frame_change_coordinator.py:108-112):
```python
_ = self.main_window.state_manager.frame_changed.connect(
    self.on_frame_changed,
    Qt.QueuedConnection,  # ← Asynchronous, causes queue buildup
)
```

**TimelineTabWidget** (ui/timeline_tabs.py:361-368):
```python
# Connects directly to ApplicationState, NOT StateManager
_ = self._app_state.curves_changed.connect(self._on_curves_changed)
_ = self._app_state.active_curve_changed.connect(self._on_active_curve_changed)
_ = self._app_state.selection_changed.connect(self._on_selection_changed)
# NO frame_changed connection!
```

**CurveViewWidget** (ui/curve_view_widget.py:175):
```python
# Already uses SignalManager for cleanup
_ = self.signal_manager.connect(
    self._app_state.selection_state_changed,
    self._on_selection_state_changed,
    "selection_state_changed",
)
```

**StateManager** (ui/state_manager.py:70):
```python
# Forwards ApplicationState signals (to be removed)
_ = self._app_state.frame_changed.connect(self.frame_changed.emit)
```

---

### B. Coordinator Activation (Baseline)

**SignalConnectionManager** (ui/controllers/signal_connection_manager.py:127):
```python
# Connect frame change coordinator (replaces 6 independent frame_changed connections)
self.main_window.frame_change_coordinator.connect()
logger.info("FrameChangeCoordinator wired")
```

---

### C. Test Pattern (Current - Bypasses Signal Chain)

**test_centering_toggle.py** (line 93):
```python
# Direct call to widget method - BYPASSES signal chain
widget.on_frame_changed(2)

# Should be (to test signal chain):
app_state = get_application_state()
app_state.set_frame(2)  # Triggers frame_changed signal
```

---

**Review Complete** ✅

**Next Steps**:
1. Apply critical fixes to plan
2. Run Phase -1 validation
3. Proceed with Phase 0 implementation
4. Monitor integration test results closely

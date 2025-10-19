# Architectural Fix: Eliminate FrameChangeCoordinator and Signal Forwarding

**Goal**: Remove coordinator pattern, eliminate race conditions, simplify signal flow

**Strategy**: Validation-first approach with clean incremental phases

**Created**: October 19, 2025
**Revised**: October 19, 2025 (after 4-agent review)
**Branch**: `fix/eliminate-frame-coordinator-v2`

---

## Revision Summary

**Changes from original plan**:
- ✅ Added Phase 0: Integration tests FIRST (existing tests bypass signal chain)
- ✅ Removed feature flags (created false safety - test both paths but only one runs)
- ✅ Corrected root cause: Synchronous execution is the fix, not atomic capture
- ✅ Simplified: 5 phases (was 7), 3-5 hours (was 6-8 hours)
- ✅ Code verification: Coordinator's justification is false (background doesn't affect centering)

**Why these changes**:
- **Single-user desktop app**: Git rollback is sufficient safety net
- **Test gap discovered**: All centering tests call `widget.on_frame_changed()` directly, bypassing signal chain
- **Root cause clarified**: Race is from stale frame parameters in QueuedConnection queue, not stale curve_data
- **Coordinator unnecessary**: Claims background affects centering viewport, but code shows centering uses widget dimensions only

---

## Phase 0: Foundation & Validation (1-2 hours)

**Objective**: Add missing test coverage, verify assumptions, establish baseline

### 0.1 Add Integration Test for Signal Chain
- [ ] Create `tests/test_frame_change_integration.py`
- [ ] Add test that triggers frame changes via `ApplicationState.set_frame()` (not direct calls)
  ```python
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

      # Verify: No visual jumps, final frame rendered correctly
      assert curve_widget.last_painted_frame == 100
  ```
- [ ] Test should **FAIL** with current coordinator (proves bug exists)
- [ ] Document failure mode: "Visual jumps during rapid scrubbing" or "Centering lags behind"

### 0.2 Verify Memory Management Strategy
- [ ] Read SignalManager implementation (`ui/signal_manager.py`)
- [ ] Document cleanup pattern for new direct connections
- [ ] Add test: Create/destroy widget 100x, verify no memory leaks
  ```python
  def test_widget_lifecycle_no_memory_leaks(qtbot):
      """Verify direct connections clean up on widget destruction."""
      for _ in range(100):
          widget = CurveViewWidget(...)
          widget.deleteLater()
          qtbot.wait(10)
      # Should not crash, memory should be stable
  ```

### 0.3 Capture Baseline Metrics
- [ ] Run full test suite: `uv run pytest tests/ -v` (baseline: all pass)
- [ ] Run type checking: `./bpr --errors-only` (baseline: 0 errors)
- [ ] Measure frame change latency (if tooling available)
- [ ] Count update() calls per frame change (should be 2-3 with coordinator)
- [ ] Create git branch: `fix/eliminate-frame-coordinator-v2`

**Checkpoint 0**:
- ✅ Integration test written and **FAILS** (proves bug exists)
- ✅ Memory management strategy documented
- ✅ Baseline metrics captured
- ✅ Git branch created

**Git Commit**: "test(integration): Add signal chain test (currently FAILS - reproduces centering bug)"

---

## Phase 1: Direct Connections (1-2 hours)

**Objective**: Make components independently reactive with synchronous signal delivery

### 1.1 CurveViewWidget Direct Connection
- [ ] Add `_on_frame_changed(frame: int)` method to CurveViewWidget:
  ```python
  def _on_frame_changed(self, frame: int) -> None:
      """Handle frame changes with atomic data capture (defensive pattern)."""
      # Atomic capture - defensive against curve switching during handler
      if (cd := self._app_state.active_curve_data) is None:
          return
      curve_name, curve_data = cd

      # Apply centering if enabled
      if self.centering_mode:
          self.center_on_frame(frame)

      # Invalidate caches and trigger repaint
      self.invalidate_caches()
      self.update()
  ```
- [ ] Connect to ApplicationState in `__init__`:
  ```python
  # Use SignalManager for automatic cleanup on widget destruction
  self.signal_manager.connect(
      self._app_state.frame_changed,
      self._on_frame_changed,
      "app_state_frame_changed"
  )
  ```
- [ ] Uses **AutoConnection** (default) = DirectConnection for same-thread = synchronous
- [ ] Add logging: `logger.debug(f"[CURVE-VIEW] Frame changed to {frame}")`

### 1.2 ViewManagementController Direct Connection
- [ ] Add `_on_frame_changed(frame: int)` method:
  ```python
  def _on_frame_changed(self, frame: int) -> None:
      """Update background image for frame (if images loaded)."""
      if self.image_filenames:
          self.update_background_for_frame(frame)
          logger.debug(f"[VIEW-MGMT] Background updated for frame {frame}")
  ```
- [ ] Connect to ApplicationState (get reference from MainWindow)
- [ ] Ensure cleanup on controller destruction

### 1.3 Timeline Direct Connections
- [ ] TimelineTabWidget: Change connection from StateManager to ApplicationState
  ```python
  # BEFORE: state_manager.frame_changed.connect(self._on_frame_changed)
  # AFTER:  app_state.frame_changed.connect(self._on_frame_changed)
  ```
- [ ] Update cleanup in `__del__` to disconnect from app_state
- [ ] TimelineController: No changes needed (doesn't listen to frame changes)

**Checkpoint 1**:
- [ ] Integration test now **PASSES** (bug fixed)
- [ ] All unit tests pass: `uv run pytest tests/ -v`
- [ ] Type checking clean: `./bpr`
- [ ] Memory leak test passes (widget lifecycle)
- [ ] Manual test: Centering works immediately during rapid scrubbing

**Git Commit**: "feat(reactive): Add direct frame change connections to components"

---

## Phase 2: Remove Coordinator (30 min)

**Objective**: Delete redundant coordinator code

### 2.1 Disconnect Coordinator
- [ ] In MainWindow, comment out coordinator connection:
  ```python
  # self.frame_change_coordinator.connect()  # Now redundant
  ```
- [ ] Run full test suite to verify nothing breaks
- [ ] Run app manually, verify centering works

### 2.2 Delete Coordinator Files
- [ ] Delete `ui/controllers/frame_change_coordinator.py`
- [ ] Delete `tests/test_frame_change_coordinator.py`
- [ ] Remove coordinator instance from MainWindow:
  ```python
  # DELETE: self.frame_change_coordinator = FrameChangeCoordinator(self)
  ```
- [ ] Remove coordinator imports

**Checkpoint 2**:
- [ ] Full test suite passes: `uv run pytest tests/ -v`
- [ ] Type checking clean: `./bpr`
- [ ] Grep for "frame_change_coordinator": 0 results
- [ ] Application runs without coordinator

**Git Commit**: "refactor(cleanup): Remove redundant FrameChangeCoordinator"

---

## Phase 3: Remove StateManager Signal Forwarding (1 hour)

**Objective**: Eliminate signal forwarding indirection

### 3.1 Audit Current Connections
- [ ] Grep for `state_manager.frame_changed.connect`
- [ ] List all components still using StateManager forwarding
- [ ] Verify most already updated in Phase 1

### 3.2 Update Remaining Connections (if any)
- [ ] Change `state_manager.frame_changed` → `app_state.frame_changed`
- [ ] Update one component at a time
- [ ] Test after each change

### 3.3 Remove StateManager Forwarding
- [ ] In `StateManager.__init__`, delete forwarding connection:
  ```python
  # DELETE THIS LINE:
  # self._app_state.frame_changed.connect(self.frame_changed.emit)
  ```
- [ ] Delete signal definition from StateManager:
  ```python
  # DELETE THIS LINE:
  # frame_changed = Signal(int)
  ```
- [ ] Update StateManager docstring (no longer forwards signals)

**Checkpoint 3**:
- [ ] Grep `state_manager.frame_changed`: 0 results (except definition removal)
- [ ] Full test suite passes: `uv run pytest tests/ -v`
- [ ] Type checking clean: `./bpr`

**Git Commit**: "refactor(arch): Remove StateManager signal forwarding, direct ApplicationState connections"

---

## Phase 4: Documentation & Final Validation (30 min)

**Objective**: Update docs, comprehensive validation

### 4.1 Update CLAUDE.md
- [ ] Remove FrameChangeCoordinator from controllers list (line ~419)
- [ ] Update StateManager section: "UI preferences and view state only, no signal forwarding"
- [ ] Add architectural principle: "Components connect directly to ApplicationState for data signals"
- [ ] Document pattern: "Use AutoConnection (default) for same-thread signals"

### 4.2 Update This Plan Document
- [ ] Add "COMPLETED" stamp at top
- [ ] Document actual time spent vs estimated
- [ ] Note any deviations from plan

### 4.3 Final Validation
- [ ] Full test suite: `uv run pytest tests/ -v` (all pass)
- [ ] Type checking: `./bpr` (0 errors)
- [ ] Linting: `uv run ruff check . --fix` (0 warnings)
- [ ] Integration test passes (no visual jumps)
- [ ] Performance: Update calls per frame = 1 (was 2-3)

### 4.4 Manual Regression Testing
- [ ] Centering mode + rapid scrubbing (main bug - should be fixed)
- [ ] Background images + scrubbing (secondary bug - should be fixed)
- [ ] Undo/redo with frame changes
- [ ] Multi-curve switching
- [ ] Timeline playback

**Checkpoint 4**:
- ✅ All tests pass
- ✅ No type errors
- ✅ No lint warnings
- ✅ Centering works immediately (no delays)
- ✅ No visual jumps when scrubbing
- ✅ Documentation updated

**Git Commit**: "docs(arch): Document direct reactive pattern, remove coordinator references"

---

## Rollback Strategy

**Surgical rollback** (if checkpoint fails):
1. Identify which phase failed
2. `git log --oneline` to find last passing commit
3. `git reset --hard <last-good-commit>`
4. Debug issue in isolation
5. Retry phase when fixed

**Full rollback** (if major issues discovered):
1. `git checkout main`
2. `git branch fix/coordinator-failed` (preserve work for reference)
3. Review AGENT_FINDINGS_SYNTHESIS.md for alternative approaches
4. Start fresh with refined understanding

**Temporary workaround** (if rollback needed urgently):
- Remove QueuedConnection from coordinator (line 111)
- Keeps coordinator but fixes immediate race condition
- Buys time for proper refactor

---

## Success Criteria

**Technical:**
- ✅ All 124+ tests pass (including new integration test)
- ✅ No type errors (basedpyright)
- ✅ No lint warnings (ruff)
- ✅ Centering works immediately (no delays)
- ✅ Timeline scrubbing is smooth (no lag)
- ✅ Background and curve stay in sync

**Architectural:**
- ✅ No FrameChangeCoordinator (simpler architecture)
- ✅ No StateManager signal forwarding (single source of truth)
- ✅ Components independently reactive (loose coupling)
- ✅ No execution order dependencies (resilient)
- ✅ Race conditions eliminated (reliable)

**Code Quality:**
- ✅ Simpler: ~200 lines of code removed
- ✅ More maintainable: No coordinator to update when adding components
- ✅ SOLID compliant: Each component owns its reactions
- ✅ KISS compliant: Direct connections, no indirection

**Performance:**
- ✅ Update calls per frame change: 1 (was 2-3)
- ✅ Frame change latency: ≤ baseline (no regression)
- ✅ No memory leaks (widget lifecycle test passes)

---

## Root Cause Analysis (Revised)

### The Actual Problem

**Stale frame parameters from QueuedConnection queue buildup**:

```
User rapidly scrubs timeline (frames 5 → 6 → 7):

T0: frame_changed(5) emitted
T1: TimelineTabWidget updates SYNCHRONOUSLY (shows frame 5)
T2: Coordinator.on_frame_changed(5) QUEUED (QueuedConnection)

T3: frame_changed(6) emitted
T4: TimelineTabWidget updates SYNCHRONOUSLY (shows frame 6)
T5: Coordinator.on_frame_changed(6) QUEUED

T6: frame_changed(7) emitted
T7: TimelineTabWidget updates SYNCHRONOUSLY (shows frame 7)
T8: Coordinator.on_frame_changed(7) QUEUED

T9: Event loop processes on_frame_changed(5) ← STALE!
T10: Centers view on frame 5 position (timeline shows 7)
T11: Event loop processes on_frame_changed(6) ← STALE!
T12: Centers view on frame 6 position (timeline shows 7)
T13: Event loop processes on_frame_changed(7) ← Finally current!
T14: Centers view on frame 7 position

Result: User sees THREE centering operations (visual "jumps")
even though timeline only shows frame 7.
```

**Mixed synchronous/asynchronous execution**:
- Timeline uses **DirectConnection** (immediate, synchronous)
- Coordinator uses **QueuedConnection** (deferred, async)
- Creates desynchronization between timeline and view

### Why Coordinator's Justification is False

**Coordinator claims** (frame_change_coordinator.py:27-30):
> "Background loading might happen AFTER centering, causing the centering
> calculation to use old background dimensions."

**Code reality** (view_camera_controller.py:271):
```python
def center_on_point(self, x: float, y: float) -> None:
    screen_pos = self.data_to_screen(x, y)
    widget_center = QPointF(self.widget.width() / 2, self.widget.height() / 2)
    # ^^^ Uses WIDGET dimensions, NOT background dimensions
```

**Verification**: Background images are just painted behind curves. They don't affect coordinate transformations or viewport calculations. Centering uses widget dimensions only.

**Conclusion**: Coordinator solves a non-existent problem. The execution order it enforces is unnecessary.

### Why Tests Don't Catch This

**Test pattern** (test_centering_toggle.py:93):
```python
widget.on_frame_changed(2)  # Direct synchronous call
```

**Production pattern**:
```python
ApplicationState.set_frame(2)
  → StateManager.frame_changed.emit(2)
    → Coordinator.on_frame_changed(2) [QUEUED via QueuedConnection]
```

Tests bypass the signal chain entirely, so they never exercise the QueuedConnection code path. This is why all centering tests pass but production fails.

### The Proper Fix

**Remove QueuedConnection**, use **AutoConnection** (default):
- AutoConnection = DirectConnection for same-thread = synchronous execution
- Latest frame change supersedes previous ones (no queue buildup)
- Immediate centering on current frame only
- Clean, responsive behavior

**Atomic data capture** (defensive pattern, not primary fix):
- Captures `active_curve_data` at signal receipt
- Prevents issues if curve switching happens during handler execution
- Good practice but doesn't fix the stale frame parameter issue
- The frame parameter is stale, not the curve_data

**Direct connections**:
- Each component connects to ApplicationState
- Simpler architecture (no coordinator indirection)
- No execution order dependencies
- SOLID compliant (each component owns its reactions)

---

## Estimated Time & Risk

**Total Time**: 3-5 hours (was 6-8 hours)
- Phase 0: 1-2 hours (validation, new)
- Phase 1: 1-2 hours (direct connections)
- Phase 2: 30 min (remove coordinator)
- Phase 3: 1 hour (remove forwarding)
- Phase 4: 30 min (docs & validation)

**Risk Level**: Low
- Validation-first approach (Phase 0 proves bug exists)
- Comprehensive test suite catches regressions
- Git rollback available at each phase
- Single-user desktop app (not critical production service)

**Complexity**: Medium
- Straightforward refactor (remove indirection)
- Well-understood problem (4-agent review)
- Clear success criteria (integration test passes)

---

## Related Documents

- **AGENT_FINDINGS_SYNTHESIS.md**: 4-agent review, contradiction resolution, detailed analysis
- **BEST_PRACTICES_REVIEW_INDEX.md**: Qt best practices audit findings
- **ELIMINATE_COORDINATOR_ARCHITECTURAL_REVIEW.md**: Architectural analysis

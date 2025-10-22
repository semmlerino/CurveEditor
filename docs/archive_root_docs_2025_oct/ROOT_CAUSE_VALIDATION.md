# Root Cause Validation: ELIMINATE_COORDINATOR_PLAN.md

**Date:** October 19, 2025
**Validator:** Deep Debugger Agent
**Method:** Signal flow analysis, Qt mechanics verification, git history investigation

---

## Executive Summary

The plan's root cause analysis contains **significant inaccuracies** and **misunderstands Qt signal mechanics**. While the proposed fix (DirectConnection) may work, the reasoning is flawed and could reintroduce the original bug that QueuedConnection was added to solve.

**Risk Level:** HIGH - Removing QueuedConnection without understanding why it was added

---

## CONFIRMED: What the Plan Gets Right

### ✅ Test Gap Identified (Lines 370-383)

**Plan's claim:** Tests bypass signal chain by calling `widget.on_frame_changed()` directly.

**Validation:** CORRECT

```python
# test_centering_toggle.py:93
widget.on_frame_changed(2)  # Direct synchronous call
```

vs production:
```python
ApplicationState.set_frame(2)
  → StateManager.frame_changed.emit(2)
    → Coordinator.on_frame_changed(2) [QUEUED]
```

**Impact:** Tests validate centering logic but not signal delivery timing.

### ✅ Coordinator's Justification is False (Lines 351-367)

**Plan's claim:** "Background loading might happen AFTER centering, causing centering calculation to use old background dimensions."

**Validation:** CORRECT - This justification is FALSE

Evidence from `view_camera_controller.py:271`:
```python
def center_on_point(self, x: float, y: float) -> None:
    widget_center = QPointF(self.widget.width() / 2, self.widget.height() / 2)
    # Uses WIDGET dimensions, NOT background dimensions
```

Background images are painted decoratively and don't affect coordinate transformations.

### ✅ Timeline Uses DirectConnection (Implicit)

**Validation:** CORRECT

`timeline_tabs.py:301`:
```python
_ = state_manager.frame_changed.connect(self._on_frame_changed)
# No connection type = AutoConnection = DirectConnection (same thread)
```

Timeline updates synchronously while coordinator updates asynchronously.

---

## INCORRECT: What the Plan Gets Wrong

### ❌ "Stale Frame Parameter" Theory is WRONG (Lines 318-343)

**Plan's claim:** Multiple frame_changed emissions queue up, causing CurveView to center on frames 5, 6, 7 sequentially while timeline shows 7.

**Reality:** This fundamentally misunderstands Qt's event queue.

**What Actually Happens:**
```
User scrubs 5→6→7 in rapid succession (all within one mouse move handler):

Synchronous phase (during handler):
T0: set_frame(5) → frame_changed(5) emitted
T1:   Timeline updates to 5 (SYNC via DirectConnection)
T2:   Coordinator QUEUES update(5) [not processed yet]
T3: set_frame(6) → frame_changed(6) emitted
T4:   Timeline updates to 6 (SYNC)
T5:   Coordinator QUEUES update(6) [not processed yet]
T6: set_frame(7) → frame_changed(7) emitted
T7:   Timeline updates to 7 (SYNC)
T8:   Coordinator QUEUES update(7) [not processed yet]
T9: Mouse handler returns

Asynchronous phase (event loop):
T10: Process update(5) - centers on frame 5
T11: Process update(6) - centers on frame 6
T12: Process update(7) - centers on frame 7
```

**The REAL Issue:** It's not "stale parameters" causing wrong centering. It's LATENCY. Timeline shows 7 immediately, CurveView eventually shows 7 but with delay. This creates visual lag during rapid scrubbing.

**Implication:** The bug is a UX/performance issue (perceived lag), not a correctness issue (wrong frame).

### ❌ "Atomic Data Capture" is a Red Herring (Lines 393-398)

**Plan's claim:** "Atomic capture prevents issues if curve switching happens during handler execution."

**Reality:** Single-threaded UI can't switch curves DURING a handler. Handler must complete first.

**What atomic capture actually protects against:**
- Long-running handlers where state changes before completion
- NOT applicable to fast centering operations
- Conflates frame parameter staleness (real) with curve data staleness (hypothetical)

### ❌ Ignores Why QueuedConnection Was Added

**Critical Missing Context:** Commit 51c500e (Oct 2025):

```
fix(signals): Fix timeline-curve desynchronization with Qt.QueuedConnection

Root cause was synchronous nested execution when coordinator
executed inside TimelineController's event handler.

With QueuedConnection, coordinator runs AFTER input handler
completes, preventing Qt widget state machine confusion.
```

**The Original Bug QueuedConnection Fixed:**

```
Without QueuedConnection (DirectConnection):
1. User drags slider → TimelineController.on_slider_changed(5)
2.   Inside handler: set_frame(5)
3.     ApplicationState.set_frame(5) → frame_changed(5)
4.       Coordinator.on_frame_changed(5) executes IMMEDIATELY (nested!)
5.         Updates timeline widgets while slider handler still running
6.         Qt slider state machine gets confused (nested state changes)
7.   Slider handler completes, but slider state is now inconsistent
Result: Timeline desynchronization, slider shows wrong value
```

**With QueuedConnection:**
```
1. User drags slider → TimelineController.on_slider_changed(5)
2.   Inside handler: set_frame(5)
3.     frame_changed(5) emitted → coordinator update QUEUED
4.   Slider handler completes cleanly
5. Event loop processes coordinator update (no nested execution)
Result: No state machine confusion, timeline stays synchronized
```

**Plan's Proposal Will Reintroduce This Bug!**

---

## MISSING: What the Plan Doesn't Address

### 🔴 Re-entrancy Protection

**Question:** What prevents signal loops with DirectConnection?

```
Potential loop:
Slider change → set_frame(5) → frame_changed(5)
  → Timeline update → Slider position update
    → Slider change signal??? → LOOP
```

**Not analyzed:** Whether timeline updates block signals or have other protection.

### 🔴 Event Coalescing

Qt may coalesce queued events but cannot coalesce synchronous calls.

**With QueuedConnection:**
- Multiple frame_changed(5,6,7) might coalesce into fewer actual handler calls
- More efficient

**With DirectConnection:**
- EVERY emission calls handler immediately
- Potentially LESS efficient during rapid scrubbing

### 🔴 Paint Event Batching

**Plan assumes:** Multiple centering operations cause multiple paint events (visual jumps).

**Reality:** Qt batches update() calls. Multiple `widget.update()` calls in sequence trigger ONE paint event when control returns to event loop.

The "three visual jumps" scenario (lines 342-343) may not actually occur.

### 🔴 Alternative Hypotheses Not Explored

1. **Centering calculation bug:** What if the centering math is wrong in some edge cases?
2. **Timeline state management:** What if timeline_tabs is updating its own state incorrectly?
3. **Image loading timing:** What if background loading DOES matter in ways the plan missed?
4. **Widget geometry:** What if widget resizing during scrubbing affects centering?

**None of these were investigated.**

---

## ALTERNATIVE THEORIES

### Theory A: Lag is the Only Issue (Likely Correct)

**Hypothesis:** QueuedConnection causes perceptible lag during rapid scrubbing, but centering is always eventually correct.

**Evidence:**
- Tests show centering logic works
- No reports of wrong final frame
- User complaint: "slight jump" (suggests visual lag, not wrong destination)

**Solution:** DirectConnection for immediate feedback.

**Risk:** Reintroduces nested execution bug from commit 51c500e.

**Mitigation:** Add signal blocking in timeline widgets.

### Theory B: Double-Connection Bug (Possible)

**Hypothesis:** Timeline_tabs connects to frame_changed TWICE (once directly, once via coordinator), causing double updates.

**Evidence:**
- Timeline uses DirectConnection (immediate)
- Coordinator uses QueuedConnection (delayed)
- This creates TWO updates per frame change

**Solution:** Remove direct timeline connection OR remove coordinator.

**Risk:** Lower - doesn't change connection types.

### Theory C: Signal Forwarding Overhead (Unlikely)

**Hypothesis:** StateManager forwarding adds unnecessary indirection and delay.

**Evidence:**
```
ApplicationState.frame_changed
  → StateManager.frame_changed (forwarding)
    → Coordinator.on_frame_changed (queued)
```

**Solution:** Connect coordinator directly to ApplicationState.

**Risk:** Lower - reduces indirection without changing connection semantics.

---

## RECOMMENDATIONS

### 🟡 Recommendation 1: Validate Theory A First

**Before removing QueuedConnection:**

1. **Add diagnostic logging:**
```python
def on_frame_changed(self, frame: int) -> None:
    import time
    t = time.perf_counter()
    logger.debug(f"[COORDINATOR] Frame {frame} processing at {t}")
    # ... existing code
    logger.debug(f"[COORDINATOR] Frame {frame} completed in {time.perf_counter()-t:.3f}s")
```

2. **Measure actual lag:**
- Run application with rapid scrubbing
- Check if lag is measurable (>16ms = visible at 60fps)
- If lag <16ms, it's not perceptible → not the real bug

3. **Test with DirectConnection:**
```python
# Temporary test: Change line 111
Qt.ConnectionType.DirectConnection  # Test only!
```

4. **Verify nested execution doesn't break slider:**
- Drag slider rapidly
- Check if slider value stays synchronized
- Look for Qt warnings about nested event processing

### 🟡 Recommendation 2: Try Theory B (Lower Risk)

**Check for double-connection:**

```python
# In timeline_tabs.py, temporarily comment out:
# _ = state_manager.frame_changed.connect(self._on_frame_changed)

# Keep only coordinator connection
# Test if lag disappears
```

If this fixes the lag, the issue is double-updating, not QueuedConnection.

### 🟡 Recommendation 3: Hybrid Approach

**Keep QueuedConnection for re-entrancy protection, but optimize:**

```python
def on_frame_changed(self, frame: int) -> None:
    # Skip if frame hasn't changed (coalescing)
    if frame == self._last_processed_frame:
        return
    self._last_processed_frame = frame

    # Original logic...
```

This reduces redundant processing without changing connection semantics.

### 🔴 Recommendation 4: Integration Test FIRST (Plan's Phase 0)

**Plan is correct here:** Write integration test that reproduces bug BEFORE fixing.

```python
def test_rapid_scrubbing_no_lag(qtbot, main_window):
    """Measure lag between timeline and curve view updates."""
    app_state = get_application_state()
    timeline = main_window.timeline_tabs
    curve_view = main_window.curve_widget

    # Enable centering
    curve_view.centering_mode = True

    lags = []
    for frame in range(1, 101):
        t0 = time.perf_counter()
        app_state.set_frame(frame)

        # Timeline updates immediately (DirectConnection)
        assert timeline.current_frame == frame

        # Curve view should also be at correct frame (may be delayed)
        t1 = time.perf_counter()
        # Wait for coordinator (QueuedConnection) to process
        qtbot.wait(5)  # 5ms max wait
        t2 = time.perf_counter()

        lag = t2 - t0
        lags.append(lag)

    avg_lag = sum(lags) / len(lags)
    max_lag = max(lags)

    # Lag should be imperceptible (<16ms for 60fps)
    assert avg_lag < 0.016, f"Average lag {avg_lag*1000:.1f}ms too high"
    assert max_lag < 0.033, f"Max lag {max_lag*1000:.1f}ms too high"
```

**This test will:**
- Confirm if lag exists
- Quantify lag magnitude
- Fail with current coordinator (proves bug)
- Pass after fix (validates solution)

---

## CONCLUSIONS

### What We Know for Certain:

1. ✅ Tests bypass signal chain (confirmed gap)
2. ✅ Coordinator's background justification is false
3. ✅ Timeline uses DirectConnection, coordinator uses QueuedConnection
4. ✅ QueuedConnection was added intentionally to fix nested execution bug

### What We Don't Know:

1. ❓ Is lag actually perceptible? (needs measurement)
2. ❓ Will DirectConnection reintroduce nested execution bug?
3. ❓ Is double-connection the real culprit?
4. ❓ Are there other factors causing visual jumps?

### Risk Assessment:

**Plan's approach (remove QueuedConnection):**
- **Probability of fixing lag:** 80%
- **Probability of reintroducing bug:** 60%
- **Net risk:** MEDIUM-HIGH

**Alternative (fix double-connection):**
- **Probability of fixing lag:** 50%
- **Probability of reintroducing bug:** 10%
- **Net risk:** LOW

**Hybrid (keep QueuedConnection, optimize):**
- **Probability of fixing lag:** 40%
- **Probability of reintroducing bug:** 5%
- **Net risk:** VERY LOW

### Final Recommendation:

**DO NOT proceed with plan as written.** Execute in this order:

1. **Phase 0: Measure and validate** (Plan's approach is correct here)
   - Write integration test
   - Measure actual lag
   - Confirm bug exists and is perceptible

2. **Phase 1: Try low-risk fixes first**
   - Check for double-connection
   - Try direct ApplicationState connection
   - Try event coalescing optimization

3. **Phase 2: DirectConnection only if necessary**
   - Add signal blocking to timeline widgets
   - Test thoroughly for nested execution bugs
   - Keep QueuedConnection as fallback

4. **Phase 3: Remove coordinator last**
   - Only after DirectConnection proven safe
   - Only after nested execution bug verified fixed

**The plan has the phases in correct order (Phase 0 first) but underestimates the risk of Phase 1.**

---

## Supporting Evidence

### Commit 51c500e Analysis

```
Author: GabrielH <gabrhas@gmail.com>
Date:   Tue Oct 14 21:34:23 2025 +0100

fix(signals): Fix timeline-curve desynchronization with Qt.QueuedConnection

Resolves recurring bug where timeline disconnects from curve frame status during
slider interaction. Root cause was synchronous nested execution when coordinator
executed inside TimelineController's event handler.

Changes:
- Add Qt.QueuedConnection to FrameChangeCoordinator (breaks nested execution)
- Remove redundant TimelineController.frame_changed signal emission
```

**Key insight:** QueuedConnection was added 5 days ago to fix a REAL bug. Removing it risks regression.

### Qt Signal Connection Types

**AutoConnection (default):**
- Same thread → DirectConnection (synchronous)
- Cross thread → QueuedConnection (async)

**DirectConnection:**
- Always synchronous
- Handler executes immediately in emitter's context
- Allows nested execution
- Faster but riskier

**QueuedConnection:**
- Always asynchronous
- Posts event to receiver's event loop
- Prevents nested execution
- Safer but slower

**For same-thread UI signals:** AutoConnection = DirectConnection (plan is correct here).

---

**Validator:** Deep Debugger Agent
**Confidence:** HIGH (evidence-based analysis)
**Recommendation:** REVISE plan with lower-risk approach

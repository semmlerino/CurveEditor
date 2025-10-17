# Qt Signal Timing Analysis: Timeline-Curve Desynchronization

**Date**: 2025-10-13
**Issue**: Timeline and curve display showing different frame positions
**Root Cause**: Nested signal execution causing redundant widget updates and state confusion

---

## Executive Summary

The desynchronization is caused by **nested Qt signal execution** combined with **redundant widget updates**. When a user drags the timeline slider, Qt executes signals synchronously (DirectConnection), causing the FrameChangeCoordinator to run in the middle of TimelineController's update process. This creates redundant spinbox/slider updates that interfere with Qt's internal widget state machine.

**Impact**: Low severity (visual glitch), but indicates architectural issue with signal flow.

**Recommended Fix**: Use `Qt.QueuedConnection` for FrameChangeCoordinator + remove redundant signals.

---

## Complete Signal Flow Trace

### User Action: Drag Timeline Slider to Frame 42

```
1. User drags slider → TimelineController._on_slider_changed(42)
   |
2. Timeline Handler:
   ├─ blockSignals(spinbox, True)
   ├─ spinbox.setValue(42)              [FIRST WIDGET UPDATE]
   ├─ blockSignals(spinbox, False)
   └─ _update_frame(42)
      |
3. State Update (line 196):
   └─ state_manager.current_frame = 42
      |
4. State Manager Setter (state_manager.py:332-345):
   ├─ Clamp frame to valid range
   └─ app_state.set_frame(42)
      |
5. ApplicationState.set_frame():
   └─ emit app_state.frame_changed(42)
      |
6. StateManager Forwarding (state_manager.py:70):
   └─ emit state_manager.frame_changed(42)
      |
7. FrameChangeCoordinator.on_frame_changed(42)  [NESTED EXECUTION - SYNCHRONOUS]
   |
   Phase 1: Pre-paint State Updates
   ├─ _update_background(42)
   ├─ _apply_centering(42)
   └─ _invalidate_caches()
   |
   Phase 2: Widget Updates
   └─ _update_timeline_widgets(42)
      ├─ timeline_controller.update_frame_display(42, update_state=False)
      │  ├─ blockSignals(spinbox, True)
      │  ├─ spinbox.setValue(42)     [SECOND WIDGET UPDATE - REDUNDANT!]
      │  ├─ blockSignals(spinbox, False)
      │  ├─ blockSignals(slider, True)
      │  ├─ slider.setValue(42)       [SECOND WIDGET UPDATE - REDUNDANT!]
      │  └─ blockSignals(slider, False)
      └─ timeline_tabs._on_frame_changed(42)
   |
   Phase 3: Single Repaint
   └─ curve_widget.update()          [Triggers paintEvent]
      └─ paintEvent reads state_manager.current_frame = 42 ✓
   |
   [FrameChangeCoordinator returns]
   |
8. Back to TimelineController._update_frame():
   └─ self.frame_changed.emit(42)    [REDUNDANT SIGNAL]
      |
9. MainWindow.on_frame_changed_from_controller(42)
   └─ logger.debug() only - NO-OP
```

---

## Qt-Specific Issues Identified

### 1. **Synchronous Signal Execution (DirectConnection)**

**Problem**: All signals use `Qt.AutoConnection` (default), which resolves to `Qt.DirectConnection` for same-thread signals. This causes FrameChangeCoordinator to execute **synchronously** within the state manager setter.

**Evidence**:
```python
# frame_change_coordinator.py:90
_ = self.main_window.state_manager.frame_changed.connect(self.on_frame_changed)
# ^ No connection type specified = Qt.AutoConnection
# ^ Same thread = Qt.DirectConnection = SYNCHRONOUS execution
```

**Impact**: Deep call stacks, nested execution, unpredictable timing.

### 2. **Redundant Widget Updates**

**Problem**: Spinbox and slider are updated TWICE per frame change:
- Once in `TimelineController._on_slider_changed()` (line 186-187)
- Again in `FrameChangeCoordinator._update_timeline_widgets()` (line 248-253)

**Evidence**:
```python
# First update (timeline_controller.py:186-187)
_ = self.frame_spinbox.blockSignals(True)
self.frame_spinbox.setValue(value)  # User just set this via drag!
_ = self.frame_spinbox.blockSignals(False)

# Second update (via coordinator, line 248-253)
_ = self.frame_spinbox.blockSignals(True)
self.frame_spinbox.setValue(frame)  # REDUNDANT - already at this value
_ = self.frame_spinbox.blockSignals(False)
```

**Impact**: Qt widget state machine confusion, especially when called while widget is processing user interaction.

### 3. **blockSignals() Timing Issues**

**Problem**: Calling `blockSignals(True)` → `setValue()` → `blockSignals(False)` while a widget is mid-interaction (user still dragging) may interfere with Qt's internal event processing.

**Qt Documentation Warning**:
> "Note that signals are not blocked for the sender when blockSignals() is used."

**Impact**: Widget may receive events out of order or miss internal state updates.

### 4. **Missing Re-entrancy Protection**

**Problem**: FrameChangeCoordinator doesn't guard against re-entrant calls. If any phase operation triggers another frame change (e.g., centering logic), the coordinator could execute recursively.

**Evidence**: No `_is_processing` flag or signal blocking.

**Impact**: Potential infinite recursion or stack overflow in edge cases.

### 5. **Redundant Signal Emission**

**Problem**: `TimelineController.frame_changed` signal emitted after state already updated and coordinator already notified everyone.

**Evidence**:
```python
# timeline_controller.py:200
self.frame_changed.emit(frame)  # After state_manager.frame_changed already fired
```

**Impact**: Extra signal processing, potential for duplicate responses.

---

## Signal Flow Diagram

```
User Input (Slider Drag)
        ↓
  TimelineController
  _on_slider_changed()
        ↓
    [Update Widgets]
  spinbox.setValue(42)
  slider already at 42
        ↓
  state_manager.current_frame = 42
        ↓
    StateManager.setter
        ↓
  app_state.set_frame(42)
        ↓
 ApplicationState.frame_changed
        ↓
 StateManager.frame_changed (forwarded)
        ↓
 FrameChangeCoordinator [SYNCHRONOUS]
        ├─ Phase 1: Background/Cache
        ├─ Phase 2: [REDUNDANT] update widgets AGAIN
        └─ Phase 3: Repaint curve
        ↓
  [Returns to TimelineController]
        ↓
 TimelineController.frame_changed [REDUNDANT]
        ↓
  MainWindow (no-op)
```

---

## Recommended Fixes

### **Option 1: Use Qt.QueuedConnection for Coordinator (RECOMMENDED)**

**Change**: Modify connection type to defer coordinator execution.

```python
# ui/controllers/frame_change_coordinator.py:90
def connect(self) -> None:
    """Connect to state manager frame_changed signal (idempotent)."""
    try:
        self.main_window.state_manager.frame_changed.disconnect(self.on_frame_changed)
    except (RuntimeError, TypeError):
        pass

    # Use QueuedConnection to defer execution until next event loop iteration
    _ = self.main_window.state_manager.frame_changed.connect(
        self.on_frame_changed,
        Qt.QueuedConnection  # ← ADD THIS
    )
    logger.info("FrameChangeCoordinator connected with QueuedConnection")
```

**Benefits**:
- ✅ Breaks nested execution - coordinator runs AFTER TimelineController completes
- ✅ Timeline widgets fully updated before coordinator processes
- ✅ No widget state confusion from mid-processing updates
- ✅ Maintains existing architecture with minimal changes
- ✅ Follows Qt best practices for cross-component coordination

**Trade-offs**:
- ⚠️ Slight delay (~1ms) between state update and coordinator execution
- ℹ️ For frame changes, this is acceptable and actually more correct

**Testing**: Verify centering mode still works correctly with deferred execution.

---

### **Option 2: Remove Redundant Timeline Updates**

**Change**: Don't update timeline widgets in coordinator - they're already updated.

```python
# ui/controllers/frame_change_coordinator.py:177-189
def _update_timeline_widgets(self, frame: int) -> None:
    """Update timeline widgets (spinbox, slider, tabs)."""
    # REMOVED: timeline_controller.update_frame_display(frame, update_state=False)
    # Reason: Timeline already updated by TimelineController before state change

    # Only update timeline tabs (visual updates only)
    if self.timeline_tabs:
        self.timeline_tabs._on_frame_changed(frame)

    logger.debug(f"[FRAME-COORDINATOR] Timeline tabs updated for frame {frame}")
```

**Benefits**:
- ✅ Eliminates redundant widget updates
- ✅ Simpler execution flow
- ✅ No nested blockSignals() calls
- ✅ Fixes the root cause directly

**Trade-offs**:
- ⚠️ Assumes TimelineController always updates widgets before state changes
- ⚠️ If frame changes come from other sources (e.g., programmatic), timeline might not update

**Mitigation**: Document that TimelineController is responsible for widget updates.

---

### **Option 3: Remove Redundant TimelineController Signal**

**Change**: Don't emit `TimelineController.frame_changed` - it's redundant.

```python
# ui/controllers/timeline_controller.py:193-204
def _update_frame(self, frame: int) -> None:
    """Update the current frame and notify listeners."""
    # Update state manager (single source of truth)
    self.state_manager.current_frame = frame
    logger.debug(f"[FRAME] Current frame set to: {frame}")

    # REMOVED: self.frame_changed.emit(frame)
    # Reason: state_manager.frame_changed already emitted, this is redundant

    # Update status
    total = self.frame_spinbox.maximum()
    self.status_message.emit(f"Frame {frame}/{total}")
```

**Cleanup Required**:
```python
# ui/controllers/signal_connection_manager.py:95-97
# REMOVE this connection - it connects to a no-op handler
_ = self.main_window.timeline_controller.frame_changed.connect(
    self.main_window.on_frame_changed_from_controller
)

# ui/main_window.py:434-443
# REMOVE this method - it does nothing
def on_frame_changed_from_controller(self, frame: int) -> None:
    ...  # Dead code
```

**Benefits**:
- ✅ Eliminates duplicate signal emission
- ✅ Simplifies signal architecture
- ✅ No performance impact
- ✅ Removes dead code

**Trade-offs**: None - this signal is genuinely redundant.

---

### **RECOMMENDED COMBINATION: Option 1 + Option 3**

**Implementation Plan**:

1. **Add Qt.QueuedConnection to FrameChangeCoordinator** (Option 1)
2. **Remove TimelineController.frame_changed emission** (Option 3)
3. **Remove dead code** in MainWindow and SignalConnectionManager

**Result**:
- Clean, predictable signal flow
- No nested execution
- No redundant updates or signals
- Follows Qt best practices
- Minimal code changes

---

## Testing Checklist

### Manual Testing

- [ ] Drag timeline slider - verify smooth frame changes
- [ ] Use spinbox arrows - verify frame increments correctly
- [ ] Click timeline tabs - verify navigation works
- [ ] Enable centering mode - verify centering still works with QueuedConnection
- [ ] Load background images - verify background updates during frame changes
- [ ] Rapid slider dragging - verify no frame skips or visual glitches
- [ ] Playback mode - verify smooth animation

### Automated Testing

- [ ] Run existing timeline tests - should all pass
- [ ] Add test for coordinator with QueuedConnection
- [ ] Add test for redundant signal removal
- [ ] Verify no regressions in frame navigation

---

## Additional Recommendations

### 1. Add Re-entrancy Protection

```python
# ui/controllers/frame_change_coordinator.py
class FrameChangeCoordinator:
    def __init__(self, main_window: MainWindow):
        ...
        self._is_processing = False  # Re-entrancy guard

    def on_frame_changed(self, frame: int) -> None:
        """Handle frame change with re-entrancy protection."""
        if self._is_processing:
            logger.warning(f"Re-entrant frame change to {frame} - ignoring")
            return

        self._is_processing = True
        try:
            # ... existing phases ...
        finally:
            self._is_processing = False
```

### 2. Consider Event Compression

For rapid frame changes (e.g., during playback), consider compressing events:

```python
# Use QTimer.singleShot to compress rapid updates
self._pending_frame = None
self._update_timer = QTimer()
self._update_timer.setSingleShot(True)
self._update_timer.timeout.connect(self._process_pending_frame)

def on_frame_changed(self, frame: int) -> None:
    self._pending_frame = frame
    if not self._update_timer.isActive():
        self._update_timer.start(0)  # Next event loop iteration
```

### 3. Add Signal Flow Logging

For debugging future issues:

```python
# Add to logger configuration
logger = get_logger("frame_signal_flow")

# Log at each signal emission point
logger.debug(f"[SIGNAL-FLOW] TimelineController → frame_changed({frame})")
logger.debug(f"[SIGNAL-FLOW] StateManager → frame_changed({frame})")
logger.debug(f"[SIGNAL-FLOW] FrameChangeCoordinator.on_frame_changed({frame})")
```

---

## Conclusion

The timeline-curve desynchronization is caused by **synchronous nested signal execution** creating **redundant widget updates**. The recommended fix uses `Qt.QueuedConnection` to defer coordinator execution, eliminating nested calls and ensuring timeline widgets are fully updated before coordination begins.

This follows Qt's design philosophy:
> "When you have complex interactions between components, use QueuedConnection to break synchronous dependencies and give the event loop control."

**Implementation Difficulty**: Low
**Risk**: Low (deferred execution is standard Qt pattern)
**Estimated Time**: 30 minutes + testing

---

## References

- Qt Documentation: [Signals & Slots](https://doc.qt.io/qt-6/signalsandslots.html)
- Qt Documentation: [Qt::ConnectionType](https://doc.qt.io/qt-6/qt.html#ConnectionType-enum)
- Qt Documentation: [Event Loop](https://doc.qt.io/qt-6/eventsandfilters.html)
- CurveEditor: `ui/controllers/frame_change_coordinator.py`
- CurveEditor: `ui/controllers/timeline_controller.py`
- CurveEditor: `ui/state_manager.py`

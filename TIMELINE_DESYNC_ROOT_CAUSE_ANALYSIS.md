# Timeline-Curve Desynchronization Bug - Root Cause Analysis

## Summary

The timeline shows the wrong frame during rapid clicking because `timeline_tabs` updates its visual state through a QUEUED signal callback, but ApplicationState updates synchronously, creating a race window.

## Signal Connection Map

### All frame_changed Connections

1. **ApplicationState → StateManager** (state_manager.py:72-75)
   ```python
   _ = self._app_state.frame_changed.connect(
       self.frame_changed.emit,
       Qt.QueuedConnection  # ✓ Queued
   )
   ```

2. **StateManager → FrameChangeCoordinator** (frame_change_coordinator.py:110-112)
   ```python
   _ = self.main_window.state_manager.frame_changed.connect(
       self.on_frame_changed,
       Qt.QueuedConnection,  # ✓ Queued
   )
   ```

### Direct timeline_tabs Connections

**CRITICAL FINDING:** `timeline_tabs` does NOT connect to `frame_changed` signals!

```python
# ui/timeline_tabs.py:300-304
def set_state_manager(self, state_manager: "StateManager") -> None:
    self._state_manager = state_manager
    _ = state_manager.active_timeline_point_changed.connect(self._on_active_timeline_point_changed)
    # ❌ NO frame_changed connection here!
```

The `frame_changed` connection was intentionally removed (signal_connection_manager.py:183):
```python
# NOTE: timeline_tabs.frame_changed connection REMOVED to prevent circular signal flow
```

## The Bug Sequence

### What Happens When User Clicks Timeline Tab

1. User clicks tab 42
2. `timeline_tabs.set_current_frame(42)` called
3. **Line 661:** `old_frame = self.current_frame`
   - This reads from the **property getter** (line 275-279)
   - Property returns `self._state_manager.current_frame`
   - Returns current ApplicationState value (say, 40)

4. **Line 665:** `self.current_frame = 42`
   - Delegates to `StateManager.current_frame = 42`
   - StateManager calls `ApplicationState.set_frame(42)`
   - ApplicationState **SYNCHRONOUSLY** emits `frame_changed(42)`
   - StateManager **QUEUES** forwarding to its `frame_changed`
   - FrameChangeCoordinator **QUEUES** its callback
   - **Returns immediately**

5. **At this point:**
   - ✓ `ApplicationState.current_frame = 42` (updated synchronously)
   - ✓ `StateManager.current_frame = 42` (updated synchronously)
   - ❌ `timeline_tabs._current_frame = 40` (NOT updated yet!)
   - ⏳ Coordinator callback pending in event queue

6. **Paint events can happen NOW:**
   - `curve_view_widget.paintEvent()` reads `ApplicationState.current_frame = 42`
   - Curve widget draws frame 42
   - **BUT** timeline_tabs visual state shows frame 40 (old tab highlighted)

7. **LATER** (after event queue processes):
   - Coordinator runs
   - Calls `timeline_tabs._on_frame_changed(42)` (line 215)
   - Updates `timeline_tabs._current_frame = 42`
   - Timeline visual state finally correct

## Why the Bug Persists

The race window exists because:

1. **ApplicationState updates synchronously** - new frame value available immediately
2. **Curve widget reads ApplicationState directly** - can paint new frame immediately
3. **timeline_tabs updates via queued callback** - visual state delayed until coordinator runs
4. **Property getter reads ApplicationState** - masks the internal tracking variable mismatch

## The Root Cause

The bug is in `timeline_tabs.set_current_frame()` (line 651-666):

```python
def set_current_frame(self, frame: int) -> None:
    frame = max(self.min_frame, min(self.max_frame, frame))

    old_frame = self.current_frame  # ❌ BUG: Reads from property (StateManager/ApplicationState)

    if frame != old_frame:
        self.current_frame = frame  # Delegates to StateManager
        # ❌ BUG: Visual update happens LATER via coordinator callback
```

The problem:
- `old_frame` reads from ApplicationState (via property getter)
- After setting StateManager, ApplicationState is updated synchronously
- But `timeline_tabs._current_frame` (internal tracking) is NOT updated
- Visual updates wait for coordinator callback (queued)

## Why Qt.QueuedConnection Didn't Fix It

We added `Qt.QueuedConnection` to:
1. StateManager forwarding (state_manager.py:74)
2. FrameChangeCoordinator connection (frame_change_coordinator.py:112)

These connections ARE working as intended - they queue the callbacks. The problem is that `timeline_tabs` needs to update its OWN visual state IMMEDIATELY when `set_current_frame()` is called, not wait for the coordinator.

## The Solution

`timeline_tabs.set_current_frame()` should update its visual state IMMEDIATELY before delegating to StateManager:

```python
def set_current_frame(self, frame: int) -> None:
    frame = max(self.min_frame, min(self.max_frame, frame))

    old_frame = self._current_frame  # ✓ Read internal tracking, not property

    if frame != old_frame:
        # ✓ Update visual state IMMEDIATELY
        self._on_frame_changed(frame)

        # Then delegate to StateManager (triggers ApplicationState update)
        self.current_frame = frame
```

This ensures:
- timeline_tabs visual state updates immediately
- ApplicationState updates immediately
- Curve widget can paint correctly immediately
- Coordinator still runs later (for background loading, centering, etc.)
- No race window where timeline and curve are out of sync

## Verification

The fix eliminates the race window by making timeline_tabs update its own state synchronously, matching ApplicationState's synchronous update pattern. The coordinator's queued callback becomes a no-op for timeline_tabs (since it's already updated), but still handles other tasks like background loading and centering.

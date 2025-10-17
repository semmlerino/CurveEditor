# Timeline-Curve Desynchronization Bug - Fix Summary

## Problem

Timeline showed wrong frame during rapid clicking because visual updates were queued while ApplicationState updated synchronously.

## Root Cause

In `timeline_tabs.set_current_frame()`:

```python
# BEFORE (buggy):
old_frame = self.current_frame  # ❌ Reads from property → StateManager → ApplicationState
if frame != old_frame:
    self.current_frame = frame  # Updates ApplicationState synchronously
    # ❌ Visual update happens LATER via queued coordinator callback
```

**The Race Window:**
1. ApplicationState updates synchronously
2. Curve widget can paint new frame immediately
3. timeline_tabs visual state NOT updated yet (waiting for queued callback)
4. **RESULT: Curve shows frame 42, timeline shows frame 40**

## Solution

Update timeline_tabs visual state IMMEDIATELY before delegating to StateManager:

```python
# AFTER (fixed):
old_frame = self._current_frame  # ✓ Read internal tracking variable directly
if frame != old_frame:
    self._on_frame_changed(frame)  # ✓ Update visual state IMMEDIATELY
    self.current_frame = frame     # Then update ApplicationState
```

## Files Modified

### `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/ui/timeline_tabs.py`

**Lines 651-675:** `set_current_frame()` method

Changes:
1. Read `self._current_frame` instead of `self.current_frame` property
2. Call `self._on_frame_changed(frame)` BEFORE delegating to StateManager
3. Added implementation note explaining the synchronous update requirement

## Why This Works

### Before Fix (Race Condition)
```
User clicks frame 42
├── timeline_tabs.set_current_frame(42)
├── ApplicationState.current_frame = 42 (synchronous)
├── frame_changed signal emitted (synchronous)
├── StateManager.frame_changed forwarding QUEUED
├── FrameChangeCoordinator.on_frame_changed QUEUED
├── set_current_frame() RETURNS
├── ⚠️ Paint event can happen here! ⚠️
│   ├── curve_widget reads ApplicationState = 42 ✓
│   └── timeline_tabs._current_frame = 40 ❌ (out of sync!)
└── LATER: Coordinator runs, timeline_tabs updates to 42
```

### After Fix (No Race)
```
User clicks frame 42
├── timeline_tabs.set_current_frame(42)
├── timeline_tabs._on_frame_changed(42) ✓ IMMEDIATE visual update
├── ApplicationState.current_frame = 42 (synchronous) ✓
├── frame_changed signal emitted (synchronous)
├── StateManager.frame_changed forwarding QUEUED
├── FrameChangeCoordinator.on_frame_changed QUEUED
├── set_current_frame() RETURNS
├── ✓ Paint event can happen here ✓
│   ├── curve_widget reads ApplicationState = 42 ✓
│   └── timeline_tabs._current_frame = 42 ✓ (synchronized!)
└── LATER: Coordinator runs (timeline already up-to-date, no-op)
```

## Testing Verification

To verify fix works:

1. **Load tracking data** with multiple frames
2. **Rapid click different timeline tabs** (click 5+ times quickly)
3. **Expected Result:** Timeline tab highlight always matches curve display frame
4. **Previous Bug:** Timeline would lag behind or show wrong frame

## Why Qt.QueuedConnection Wasn't Enough

The previous attempt added `Qt.QueuedConnection` to:
- StateManager → ApplicationState forwarding
- FrameChangeCoordinator connection

These connections ARE working correctly - they queue the callbacks as intended. The problem was that timeline_tabs relied ONLY on the queued callback for visual updates, creating a window where ApplicationState was updated but timeline_tabs visual state wasn't.

The fix makes timeline_tabs update its OWN state synchronously, matching ApplicationState's synchronous update pattern.

## Architecture Principles

This fix follows Qt threading best practices:

1. **Widget owns its visual state** - timeline_tabs updates its own display immediately
2. **State updates are synchronous** - ApplicationState and timeline_tabs both update immediately
3. **Coordinator handles side effects** - Background loading, centering, etc. can be deferred
4. **No race windows** - All state consistent before any paint events

## Related Files

- `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/TIMELINE_DESYNC_ROOT_CAUSE_ANALYSIS.md` - Detailed signal flow analysis
- `ui/controllers/frame_change_coordinator.py` - Coordinator still uses Qt.QueuedConnection (correct)
- `ui/state_manager.py` - StateManager still uses Qt.QueuedConnection (correct)
- `stores/application_state.py` - ApplicationState updates synchronously (correct)

## Status

✅ **Fixed** - timeline_tabs now updates visual state synchronously, eliminating race window

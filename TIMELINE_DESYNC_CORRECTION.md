# Correction: Timeline Desync Fix

**Original Commit:** `51c500e`
**Original Message:** "fix(signals): Fix timeline-curve desynchronization with Qt.QueuedConnection"
**Date:** 2025-10-13

---

## ⚠️ CORRECTION (2025-10-15)

The commit message and several documentation files incorrectly attributed the timeline desync fix to Qt.QueuedConnection.

**This is INCORRECT.**

---

## What ACTUALLY Fixed the Issue

The timeline desync was fixed by **synchronous visual updates in timeline_tabs.py**, NOT by Qt.QueuedConnection.

**Actual Fix (timeline_tabs.py:665-680):**
```python
def set_current_frame(self, frame: int) -> None:
    """Set current frame with immediate visual update.

    IMPORTANT: Updates visual state BEFORE delegating to StateManager.
    This ensures timeline_tabs internal state stays in sync.
    """
    # Update visual state IMMEDIATELY (synchronous)
    self._on_frame_changed(frame)

    # Then delegate to StateManager
    self.current_frame = frame
```

**Why This Works:**
- Timeline_tabs updates its own visual state synchronously
- THEN delegates to StateManager
- No race condition between ApplicationState update and visual update
- Simple, deterministic, works perfectly

---

## What DIDN'T Fix It

**No Qt.QueuedConnection parameters exist in actual code:**

```bash
$ grep -rn "Qt.QueuedConnection" ui/ services/
ui/state_manager.py:69:        # Forward ApplicationState signals (subscribers use Qt.QueuedConnection)
ui/controllers/frame_change_coordinator.py:100:        # Timeline_tabs uses Qt.QueuedConnection to prevent desync
ui/controllers/frame_change_coordinator.py:245:        # (no manual call needed - they subscribe directly with Qt.QueuedConnection)

# ALL 3 MATCHES ARE COMMENTS, NOT CODE!
```

**Actual Signal Connections:**
```python
# ui/state_manager.py:72 - NO Qt.QueuedConnection
_ = self._app_state.frame_changed.connect(self.frame_changed.emit)

# ui/controllers/frame_change_coordinator.py:111 - NO Qt.QueuedConnection
_ = self.main_window.state_manager.frame_changed.connect(self.on_frame_changed)
```

---

## Why Documentation Was Wrong

1. **Initial Investigation Phase:**
   - Qt.QueuedConnection was explored as potential solution
   - Documentation written during exploration

2. **Actual Implementation:**
   - Simpler solution worked better (synchronous visual updates)
   - Easier to understand and debug
   - More deterministic behavior

3. **Documentation Not Updated:**
   - Comments and docs retained incorrect Qt.QueuedConnection references
   - Commit message written based on initial exploration
   - Actual implementation used different approach

---

## Affected Documentation

**Files with incorrect Qt.QueuedConnection claims:**

1. **Git commit message:** `51c500e` (cannot amend - already pushed)
2. **TIMELINE_DESYNC_ROOT_CAUSE_ANALYSIS.md** - Shows code with Qt.QueuedConnection that doesn't exist
3. **ui/state_manager.py:69** - Comment claims "subscribers use Qt.QueuedConnection" (FALSE)
4. **ui/controllers/frame_change_coordinator.py:100** - Comment claims "Timeline_tabs uses Qt.QueuedConnection" (FALSE)
5. **ui/controllers/frame_change_coordinator.py:245** - Comment claims direct Qt.QueuedConnection subscription (FALSE)

**File with CORRECT description:**
- **TIMELINE_DESYNC_FIX_SUMMARY.md:88-135** - Accurately describes synchronous visual update fix

---

## Corrected Summary

**Timeline desync was fixed by:**
- Ensuring timeline_tabs updates its visual state synchronously
- BEFORE delegating frame changes to StateManager
- Using simple, deterministic synchronous method calls
- NOT using Qt.QueuedConnection signal parameters

**Evidence:**
- See `TIMELINE_DESYNC_FIX_SUMMARY.md:88-135` for accurate description
- See `ui/timeline_tabs.py:665-680` for actual implementation
- Search codebase shows ZERO Qt.QueuedConnection in actual signal connections

---

## Action Items

- [x] Create this correction document
- [ ] Update TIMELINE_DESYNC_ROOT_CAUSE_ANALYSIS.md with correction note
- [ ] Fix comments in ui/state_manager.py:69
- [ ] Fix comments in ui/controllers/frame_change_coordinator.py:100, 245
- [ ] Add note to git history (via git notes or documentation)

---

**Correction Date:** 2025-10-15
**Verified By:** Second-pass code review with four specialized agents
**Evidence:** Direct codebase inspection + grep verification
**Confidence:** 100%

# Frame Change Coordinator Refactor

## Problem Statement

**Bug**: Timeline jumps during centering mode playback with background images (reported in production despite passing tests).

**Root Cause**: Six independent handlers connected to `state_manager.frame_changed` with **non-deterministic execution order**. Even though workarounds have reduced update() calls to 1-2, Qt doesn't guarantee signal handler ordering, causing race conditions where background loading and centering happen in wrong order.

### Current Architecture (Problematic)

```
state_manager.frame_changed signal emits
    ↓
┌───────────────────────────────────────────────┐
│ 6 Independent Handlers (No Coordination)     │
├───────────────────────────────────────────────┤
│ 1. StateSyncController                        │
│    - center_on_frame() if centering_mode      │
│    - invalidate_caches()                      │
│    - update() ← REPAINT (1 of 1-2)            │
│                                               │
│ 2. ViewManagementController                   │
│    - Load background image for frame          │
│    - ✅ Patched: NO update() call             │
│                                               │
│ 3. TimelineController                         │
│    - Update spinbox/slider widgets            │
│    - ✅ NO repaint                            │
│                                               │
│ 4. TimelineTabs                               │
│    - Update tab visual states                 │
│    - ✅ NO repaint                            │
│                                               │
│ 5. MainWindow                                 │
│    - Just logs (noop)                         │
│                                               │
│ 6. CurveViewWidget (fallback)                │
│    - ⚠️ DUPLICATE: Also connects to #1        │
│    - Calls same _on_state_frame_changed       │
│    - update() ← REPAINT (2 of 1-2)            │
└───────────────────────────────────────────────┘
         ↓
    PROBLEM: Non-deterministic execution order
    + potential duplicate update() calls
```

### Actual Race Condition

**Qt doesn't guarantee handler execution order.** Background loading might happen AFTER centering:

```
❌ Scenario: Bad Order (causes jump)
1. StateSyncController runs first
   - Centers on frame N (uses OLD background for viewport calc)
   - Calls update() → paint with old background + new centering
2. ViewManagementController runs second
   - Loads NEW background (no repaint triggered)
3. Next frame: User sees NEW background with OLD centering position
   Result: Visual jump
```

**Issues**:
1. **Non-Deterministic Order**: Qt signal execution order is undefined and platform-dependent
2. **Duplicate Connection**: Fallback in curve_view_widget.py creates potential 2x update() calls
3. **Implicit Dependencies**: Background must load before centering, but not enforced
4. **Fragile Workarounds**: Tribal knowledge ("don't call update() in handler X") documented in comments
5. **Tests Don't Catch It**: Signal ordering may differ between test and production environments
6. **Future Brittleness**: New feature connecting to frame_changed could reintroduce race

## Proposed Solution: FrameChangeCoordinator

### Design Principles

1. **Single Responsibility**: One component owns frame change response
2. **Explicit Ordering**: State updates happen in deterministic order
3. **Single Repaint**: Only one `update()` call after ALL state updates
4. **Testable**: Coordinator can be tested independently
5. **Extensible**: Easy to add new frame change behaviors

### New Architecture

```
state_manager.frame_changed signal emits
    ↓
┌───────────────────────────────────────────────┐
│ FrameChangeCoordinator                        │
│ (Single handler, coordinates all updates)     │
├───────────────────────────────────────────────┤
│ Phase 1: Pre-paint State Updates             │
│ ─────────────────────────────────────────────│
│ 1. Load background image (if needed)         │
│    → view_management.update_background()      │
│                                               │
│ 2. Apply centering (if enabled)               │
│    → curve_widget.center_on_frame()           │
│                                               │
│ 3. Invalidate render caches                   │
│    → curve_widget.invalidate_caches()         │
│                                               │
│ Phase 2: Widget Updates (no repaints)        │
│ ─────────────────────────────────────────────│
│ 4. Update timeline controls                   │
│    → timeline_controller.update_display()     │
│                                               │
│ 5. Update timeline tabs                       │
│    → timeline_tabs.set_current_frame()        │
│                                               │
│ Phase 3: Single Repaint                       │
│ ─────────────────────────────────────────────│
│ 6. Trigger paint with all state applied       │
│    → curve_widget.update()                    │
└───────────────────────────────────────────────┘
         ↓
    RESULT: One paint event with consistent state
```

## Implementation Plan

### Phase 1: Create Coordinator (Backward Compatible)

**File**: `ui/controllers/frame_change_coordinator.py`

```python
"""
FrameChangeCoordinator - Coordinates all frame change responses.

This controller ensures frame changes happen atomically:
1. All state updates complete before any paint events
2. Updates happen in deterministic order
3. Only one repaint after all updates
"""

from __future__ import annotations
from typing import TYPE_CHECKING
from core.logger_utils import get_logger

if TYPE_CHECKING:
    from ui.main_window import MainWindow

logger = get_logger("frame_change_coordinator")


class FrameChangeCoordinator:
    """
    Coordinates all responses to frame changes.

    Ensures atomic updates: all state changes complete before any paint.
    """

    def __init__(self, main_window: MainWindow):
        self.main_window = main_window
        self.curve_widget = main_window.curve_widget
        self.view_management = main_window.view_management_controller
        self.timeline_controller = main_window.timeline_controller
        self.timeline_tabs = main_window.timeline_tabs

    def connect(self) -> None:
        """Connect to state manager frame_changed signal."""
        self.main_window.state_manager.frame_changed.connect(
            self.on_frame_changed
        )
        logger.info("FrameChangeCoordinator connected")

    def disconnect(self) -> None:
        """Disconnect from state manager (cleanup)."""
        try:
            self.main_window.state_manager.frame_changed.disconnect(
                self.on_frame_changed
            )
            logger.info("FrameChangeCoordinator disconnected")
        except (RuntimeError, TypeError):
            # Signal already disconnected or connection never made
            pass

    def on_frame_changed(self, frame: int) -> None:
        """
        Handle frame change with coordinated updates.

        Order is critical:
        1. Background image (affects rendering)
        2. Centering (updates pan_offset)
        3. Cache invalidation (prepares for render)
        4. Widget updates (no repaints)
        5. Single repaint (with all state applied)
        """
        logger.debug(f"[FRAME-COORDINATOR] Frame changed to {frame}")

        # Phase 1: Pre-paint state updates
        self._update_background(frame)
        self._apply_centering(frame)
        self._invalidate_caches()

        # Phase 2: Widget updates (no repaints)
        self._update_timeline_widgets(frame)

        # Phase 3: Single repaint
        self._trigger_repaint()

    def _update_background(self, frame: int) -> None:
        """Update background image for frame (if images loaded)."""
        if self.view_management and self.view_management.image_filenames:
            self.view_management.update_background_for_frame(frame)
            logger.debug(f"[FRAME-COORDINATOR] Background updated for frame {frame}")

    def _apply_centering(self, frame: int) -> None:
        """Apply centering if centering mode is enabled."""
        if self.curve_widget and self.curve_widget.centering_mode:
            self.curve_widget.center_on_frame(frame)
            logger.debug(f"[FRAME-COORDINATOR] Centering applied for frame {frame}")

    def _invalidate_caches(self) -> None:
        """Invalidate render caches to prepare for repaint."""
        if self.curve_widget:
            self.curve_widget.invalidate_caches()
            logger.debug("[FRAME-COORDINATOR] Caches invalidated")

    def _update_timeline_widgets(self, frame: int) -> None:
        """Update timeline widgets (spinbox, slider, tabs)."""
        # Update timeline controller (spinbox/slider)
        if self.timeline_controller:
            self.timeline_controller.update_frame_display(frame, update_state=False)

        # Update timeline tabs
        if self.timeline_tabs:
            self.timeline_tabs.set_current_frame(frame)

        logger.debug(f"[FRAME-COORDINATOR] Timeline widgets updated for frame {frame}")

    def _trigger_repaint(self) -> None:
        """Trigger single repaint with all state applied."""
        if self.curve_widget:
            self.curve_widget.update()
            logger.debug("[FRAME-COORDINATOR] Repaint triggered")
```

### Phase 2: Migrate Connections

**Before** (6 connections):
```python
# ui/controllers/signal_connection_manager.py
state_manager.frame_changed.connect(main_window.on_state_frame_changed)
state_manager.frame_changed.connect(view_management.update_background_for_frame)

# ui/controllers/timeline_controller.py
state_manager.frame_changed.connect(lambda f: self.update_frame_display(f, False))

# ui/timeline_tabs.py
state_manager.frame_changed.connect(self._on_frame_changed)

# ui/controllers/curve_view/state_sync_controller.py
state_manager.frame_changed.connect(self._on_state_frame_changed)

# ui/curve_view_widget.py (fallback)
state_manager.frame_changed.connect(self.state_sync._on_state_frame_changed)
```

**After** (1 connection):
```python
# ui/controllers/signal_connection_manager.py
# Create and connect coordinator
main_window.frame_change_coordinator = FrameChangeCoordinator(main_window)
main_window.frame_change_coordinator.connect()

# All other frame_changed connections REMOVED
```

### Phase 3: Update Controllers (Remove update() calls)

**StateSyncController**: Remove entire `_on_state_frame_changed` method (coordinator handles this)

**ViewManagementController**: Already done - removed `update()` call

**TimelineController**: Keep `update_frame_display()` but ensure it never repaints

**TimelineTabs**: Keep `_on_frame_changed()` logic, expose as public method `set_current_frame()`

**MainWindow**: Remove `on_state_frame_changed()` (just logged anyway)

### Phase 4: Add Tests

**File**: `tests/test_frame_change_coordinator.py`

```python
"""Tests for FrameChangeCoordinator."""

class TestFrameChangeCoordinator:
    """Test frame change coordination."""

    def test_coordinator_initialization(self, qtbot):
        """Test coordinator creates successfully."""

    def test_single_connection_to_frame_changed(self, qtbot):
        """Test only coordinator connects to frame_changed signal."""

    def test_update_order_is_deterministic(self, qtbot):
        """Test updates happen in correct order."""

    def test_single_repaint_per_frame_change(self, qtbot):
        """Test only one update() call per frame change."""

    def test_centering_before_repaint(self, qtbot):
        """Test centering updates pan_offset before repaint."""

    def test_background_before_centering(self, qtbot):
        """Test background loads before centering."""

    def test_works_without_background_images(self, qtbot):
        """Test coordinator works when no background loaded."""

    def test_works_without_centering_mode(self, qtbot):
        """Test coordinator works when centering disabled."""

    def test_no_jumps_during_playback_with_background(self, qtbot):
        """Regression test: no visual jumps with background + centering."""
```

## Migration Strategy

### Phase 0: Pre-work (Critical Fixes) - **2 hours**

**Fix foundational issues before implementing coordinator:**

1. **Fix Timeline Tabs API** (`ui/timeline_tabs.py`)
   - Rename `_on_frame_changed` → `set_current_frame` (make public)
   - Update signal connection at line 299
   - Reflects actual purpose: canonical way to set current frame for tabs

2. **Fix Duplicate Connection Bug** (`ui/curve_view_widget.py`)
   - Remove or properly guard fallback connection at line 1699
   - Current try-except doesn't prevent duplicate connections (Qt allows multiple)
   - **Risk**: `update()` currently called 1-2 times per frame (duplicate connection)
   - Options:
     - A) Remove fallback entirely (ensure proper initialization order)
     - B) Add proper guard: `if not self.state_sync._state_manager:`

3. **Verify Current State**
   - Run all centering tests to establish baseline
   - Run background image tests
   - Document which tests currently pass/fail

**Deliverables:**
- ✅ Public `TimelineTabs.set_current_frame()` method
- ✅ No duplicate frame_changed connections
- ✅ All existing tests pass

---

### Phase 1: Create Coordinator (Backward Compatible) - **3 hours**

**Create coordinator without connecting it yet:**

1. **Implement FrameChangeCoordinator** (`ui/controllers/frame_change_coordinator.py`)
   - Include `connect()` and `disconnect()` methods
   - Add null checks for all controllers
   - Add comprehensive docstrings explaining phase ordering
   - DO NOT connect to signals yet

2. **Add Feature Flag** (`core/config.py`)
   ```python
   @dataclass
   class AppConfig:
       # ... existing flags ...
       use_frame_change_coordinator: bool = False  # Default OFF for safe rollout
   ```

3. **Verify Implementation**
   - Import coordinator (shouldn't break anything)
   - Verify all dependencies exist
   - Check type hints with basedpyright

**Deliverables:**
- ✅ Working coordinator class (not connected)
- ✅ Feature flag in config
- ✅ All existing tests still pass

---

### Phase 2: Add Comprehensive Tests - **3 hours**

**Create test suite before migration:**

**File**: `tests/test_frame_change_coordinator.py`

```python
"""Tests for FrameChangeCoordinator."""

class TestFrameChangeCoordinator:
    def test_coordinator_initialization(self, qtbot):
        """Test coordinator creates with all dependencies."""

    def test_disconnect_cleanup(self, qtbot):
        """Test disconnect() properly cleans up signal."""

    def test_phase_ordering_explicit(self, qtbot, mocker):
        """Test phases execute in exact order (mock to verify)."""

    def test_single_repaint_per_frame(self, qtbot, mocker):
        """Test only ONE update() call per frame change."""

    def test_background_before_centering(self, qtbot):
        """Test background loads BEFORE centering calculation."""

    def test_centering_before_repaint(self, qtbot):
        """Test centering updates pan_offset BEFORE update()."""

    def test_works_without_background(self, qtbot):
        """Test coordinator handles missing background gracefully."""

    def test_works_without_centering_mode(self, qtbot):
        """Test coordinator works when centering disabled."""

    def test_production_conditions_smooth_playback(self, qtbot):
        """Integration test: smooth playback with background + centering."""
```

**Deliverables:**
- ✅ Comprehensive test suite
- ✅ All tests pass with coordinator (flag ON)
- ✅ All tests pass without coordinator (flag OFF)

---

### Phase 3: Connect Coordinator with Feature Flag - **2 hours**

**Enable coordinator while keeping rollback option:**

1. **Update Signal Connection Manager** (`ui/controllers/signal_connection_manager.py`)
   ```python
   from core.config import get_config

   if get_config().use_frame_change_coordinator:
       # New path: Use coordinator
       coordinator = FrameChangeCoordinator(main_window)
       coordinator.connect()
       logger.info("Using FrameChangeCoordinator")
   else:
       # Old path: Use existing connections (all 6)
       _ = state_manager.frame_changed.connect(...)
       # ... (keep existing connections)
   ```

2. **Test Both Code Paths**
   - Run full suite with flag OFF (baseline)
   - Run full suite with flag ON (coordinator active)
   - Compare results (should be identical)

3. **Manual Testing**
   - Test with background images + centering mode
   - Test rapid frame changes
   - Test toggling centering during playback
   - Verify no visual jumps

**Deliverables:**
- ✅ Feature flag controls which path is used
- ✅ Both paths tested and working
- ✅ Manual verification: no visual jumps with flag ON

---

### Phase 4: Remove Old Connections - **1 hour**

**Clean migration after coordinator proven stable:**

1. **Remove All Old Connections**
   - Delete 6 frame_changed connections from signal_connection_manager
   - Remove fallback connection in curve_view_widget.py
   - Remove MainWindow.on_state_frame_changed (just logs)

2. **Simplify Signal Connection Manager**
   - Keep only coordinator connection
   - Remove feature flag conditionals
   - Clean up imports

3. **Verify No Regressions**
   - Run full test suite
   - All 2264+ tests should pass

**Deliverables:**
- ✅ Only ONE connection to frame_changed (coordinator)
- ✅ Simplified signal_connection_manager
- ✅ All tests pass

---

### Phase 5: Cleanup & Documentation - **1 hour**

**Finalize refactor:**

1. **Remove Feature Flag**
   - Delete `use_frame_change_coordinator` from config.py
   - No longer needed (coordinator is permanent)

2. **Update Documentation**
   - Add coordinator to `CLAUDE.md`
   - Update `ARCHITECTURE.md` if needed
   - Document frame change coordination pattern

3. **Remove Deprecated Code**
   - Remove any methods that are no longer called
   - Clean up comments about frame change handling

**Deliverables:**
- ✅ Updated documentation
- ✅ No deprecated code
- ✅ Clean commit history

---

### Total Estimated Time: **12 hours** (1.5 days)

**Phase 0**: 2 hours (critical bug fixes)
**Phase 1**: 3 hours (coordinator implementation)
**Phase 2**: 3 hours (comprehensive tests)
**Phase 3**: 2 hours (feature flag migration)
**Phase 4**: 1 hour (cleanup old connections)
**Phase 5**: 1 hour (documentation)

## Benefits

### Immediate
- ✅ Fixes centering jump bug permanently
- ✅ Single repaint per frame (better performance)
- ✅ Deterministic update order (no race conditions)

### Long-term
- ✅ Easy to add new frame change behaviors
- ✅ Clear ownership (one place to look)
- ✅ Testable (can mock individual update phases)
- ✅ Self-documenting (code shows explicit order)

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Duplicate connection causes 2x updates** | High | Medium | Fix in Phase 0 before coordinator |
| **Signal ordering varies by platform/timing** | Medium | High | Coordinator makes order explicit and deterministic |
| **Breaking existing functionality** | Low | High | Feature flag + comprehensive tests + both paths tested |
| **User discovers new edge case in production** | Medium | Medium | Feature flag allows instant rollback without code changes |
| **Creating a "god object"** | Low | Medium | Coordinator delegates to existing controllers (pure coordination) |
| **Tight coupling to MainWindow** | Low | Low | Already coupled via existing controllers |
| **Hard to extend in future** | Low | Low | Phase pattern allows easy insertion of new steps |

### Why Feature Flag is Critical

**Don't skip the feature flag** (despite what some might suggest):

✅ **Confidence Building**: Run with flag ON for days/weeks to gain confidence
✅ **Easy Rollback**: Flip flag OFF if weird edge case appears (no code changes)
✅ **A/B Testing**: Can compare behavior between old and new paths
✅ **Personal Project**: No pressure to ship - can take time to thoroughly validate
✅ **Low Cost**: Only 2-3 extra commits (worth the safety)

The feature flag is **not complexity** - it's **risk management** for careful technical debt elimination.

## Success Criteria

**Phase 0 (Pre-work):**
- [ ] Timeline tabs has public `set_current_frame()` method
- [ ] No duplicate frame_changed connections
- [ ] All existing tests pass (baseline established)

**Phase 1-2 (Implementation + Tests):**
- [ ] Coordinator class created with `connect()` and `disconnect()` methods
- [ ] Feature flag added to config
- [ ] All tests pass with coordinator (flag ON)
- [ ] All tests pass without coordinator (flag OFF)
- [ ] Code coverage ≥ 95% for coordinator

**Phase 3 (Migration):**
- [ ] Both code paths tested and working identically
- [ ] Manual testing: smooth playback with background + centering (flag ON)
- [ ] No visual jumps in production scenarios

**Phase 4-5 (Cleanup):**
- [ ] Only 1 connection to `state_manager.frame_changed` (coordinator)
- [ ] All 2264+ tests pass
- [ ] Documentation updated (CLAUDE.md, ARCHITECTURE.md)
- [ ] No deprecated code remaining

## Future Enhancements

Once coordinator is in place, we can easily add:
- Frame change debouncing (rapid playback optimization)
- Frame change transactions (begin/end batching)
- Frame change hooks (plugins can register behaviors)
- Performance metrics (time each phase)
- Conditional updates (skip work if nothing changed)

---

## Critical Findings from Code Review

### Agent Review Summary (2 specialized agents deployed)

**✅ Verified:**
- All files, methods, and attributes exist as described
- Coordinator design is architecturally sound
- Phase ordering is correct (background → centering → cache → widgets → repaint)

**⚠️ Critical Issues Found:**

1. **Duplicate Connection Bug** (High Priority)
   - `curve_view_widget.py:1699` creates duplicate connection to `state_sync._on_state_frame_changed`
   - Qt allows multiple connections to same slot - try-except won't prevent it
   - Results in 1-2 `update()` calls per frame change (not 1 as previously thought)
   - **Must fix in Phase 0**

2. **Non-Deterministic Signal Order** (Root Cause)
   - Qt doesn't guarantee signal handler execution order
   - Can vary by platform, timing, and Qt version
   - Even with patches, background might load AFTER centering
   - **Why tests pass but production fails**: timing-dependent race condition
   - **Coordinator fixes this**: Explicit order enforced in code

3. **Timeline Tabs API Mismatch**
   - Coordinator calls `timeline_tabs.set_current_frame()` but method doesn't exist
   - Actual method: `_on_frame_changed()` (private)
   - **Fix**: Rename to public (reflects actual purpose)

### User Experience vs Tests

**User reports**: "it still jumps" in production
**Tests report**: All centering tests pass

**Resolution**: Trust the user feedback. Tests don't catch timing-dependent race conditions because:
- Signal order may differ between test and production environments
- Test fixtures may have different initialization timing
- Background loading in tests may be synchronous vs async in production

**The coordinator solves this by making order explicit and deterministic.**

---

## Decision: Proceed with Refactor

**Recommendation**: **YES** - Proceed with full refactor using revised plan above.

**Justification:**
- Bug exists in production (user confirmation) despite passing tests
- Duplicate connection bug is real and fixable
- Non-deterministic signal order is the root cause
- Coordinator moves from "fragile workaround" to "robust architecture"
- Feature flag provides safe migration path for personal project
- 12 hours investment eliminates technical debt permanently

**This is not just a bug fix - it's architectural cleanup that prevents future regressions.**

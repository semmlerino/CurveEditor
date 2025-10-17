# PLAN TAU Phase 4: StateManager Setter Migration Strategy

**Date:** 2025-10-17
**Context:** Phase 3 completed migration of StateManager data **getters** to ApplicationState. Phase 4 must migrate **setters** and **signal connections**.

---

## Executive Summary

Phase 4 deferred work consists of:
1. **2 production total_frames setter calls** (timeline_tabs.py, timeline_controller.py)
2. **~82 test current_frame setter calls** across 13 test files
3. **5 StateManager signal connections** in signal_connection_manager.py

**Recommended Approach:** Remove total_frames setter entirely, replace test current_frame setters with direct ApplicationState calls, and migrate data-related signal connections to ApplicationState.

---

## 1. total_frames Setter Migration

### Current Implementation

**StateManager.total_frames setter** (lines 371-407):
```python
@total_frames.setter
def total_frames(self, count: int) -> None:
    """Set total frames by creating synthetic image_files list (DEPRECATED)."""
    count = max(1, count)
    current_total = self._app_state.get_total_frames()

    if current_total != count:
        # Create synthetic image_files list to achieve desired total_frames
        synthetic_files = [f"<synthetic_frame_{i+1}>" for i in range(count)]
        self._app_state.set_image_files(synthetic_files)

        # Emit signal for backward compatibility
        self.total_frames_changed.emit(count)
```

### Production Callsites (2 files)

1. **ui/timeline_tabs.py:620**
   ```python
   def set_frame_range(self, min_frame: int, max_frame: int) -> None:
       self.min_frame = min_frame
       self.max_frame = max_frame
       self.total_frames = max_frame - min_frame + 1

       if self._state_manager is not None:
           self._state_manager.total_frames = max_frame  # ❌ Creates synthetic files
   ```

2. **ui/controllers/timeline_controller.py:499**
   ```python
   def set_frame_range(self, min_frame: int, max_frame: int) -> None:
       self.frame_spinbox.setMaximum(max_frame)
       self.frame_slider.setMaximum(max_frame)

       self.state_manager.total_frames = max_frame  # ❌ Creates synthetic files
   ```

### Test Callsites (~40 occurrences)

Multiple test files use `state_manager.total_frames = N` for fixture setup:
- test_timeline_tabs.py
- test_timeline_scrubbing.py
- test_timeline_integration.py
- test_timeline_functionality.py
- test_timeline_focus_behavior.py
- test_frame_change_coordinator.py
- test_frame_highlight.py
- test_state_manager.py (dedicated tests for the setter behavior)
- Plus ~6 more files

### Architectural Problem

**Root Cause:** The setter creates **synthetic data** (fake image filenames) to drive UI state. This is backward - frame range should be **derived from actual data** (curve data or real image sequence), not synthetically created by UI.

**Invariant Violation:** ApplicationState maintains `total_frames = len(image_files)`. The setter exploits this by creating fake files to achieve a desired total_frames value.

### Recommended Strategy: **REMOVE ENTIRELY**

**Production Code:**
```python
# ❌ BEFORE (Phase 3)
if self._state_manager is not None:
    self._state_manager.total_frames = max_frame

# ✅ AFTER (Phase 4) - REMOVE THE CALL
# Frame range is derived from actual data via signals:
# - ApplicationState.curves_changed → timeline updates from curve data
# - ApplicationState.image_sequence_changed → timeline updates from image files
```

**Test Code:**
```python
# ❌ BEFORE (Phase 3)
state_manager.total_frames = 100

# ✅ AFTER (Phase 4) - Set real image files
from stores.application_state import get_application_state
state = get_application_state()
state.set_image_files([f"frame{i:04d}.png" for i in range(1, 101)])
# total_frames now automatically = 100 (derived from image_files length)
```

**Rationale:**
1. **Single Source of Truth:** Frame count derived from actual data, not UI-driven synthetic data
2. **Cleaner Architecture:** UI reacts to data changes via signals, doesn't create fake data
3. **Eliminates Deprecated Pattern:** Removes the synthetic image_files workaround
4. **Better Testing:** Tests use real data patterns instead of shortcuts

### Migration Steps

**Step 1:** Update test fixtures (low risk, high impact)
```python
# In conftest.py or test setup
def setup_frame_range(state: ApplicationState, num_frames: int) -> None:
    """Helper to set up frame range for tests."""
    files = [f"frame{i:04d}.png" for i in range(1, num_frames + 1)]
    state.set_image_files(files)
```

**Step 2:** Remove production callsites (2 files)
- timeline_tabs.py:620 - Delete the setter call
- timeline_controller.py:499 - Delete the setter call

**Step 3:** Verify frame range updates via signals
- Timeline should update via `ApplicationState.curves_changed` signal
- Timeline should update via `ApplicationState.image_sequence_changed` signal
- Test that frame range changes propagate correctly

**Step 4:** Remove the setter from StateManager
- Delete `total_frames.setter` method (lines 371-407)
- Keep `total_frames` property getter (delegates to ApplicationState)

**Step 5:** Remove `total_frames_changed` signal (see Signal Migration section)

---

## 2. current_frame Setter Migration

### Current Implementation

**StateManager.current_frame setter** (lines 344-358):
```python
@current_frame.setter
def current_frame(self, frame: int) -> None:
    """Set the current frame number (with clamping to valid range)."""
    total = self._app_state.get_total_frames()
    frame = max(1, min(frame, total))

    # Delegate to ApplicationState for storage
    self._app_state.set_frame(frame)
```

**ApplicationState.current_frame** is a **read-only property** - must use `set_frame()` method:
```python
@property
def current_frame(self) -> int:
    """Get the current frame number."""
    return self._current_frame

# No setter! Must use:
def set_frame(self, frame: int) -> None:
    """Set the current frame and emit signal."""
    # ... implementation
```

### Test Callsites (~82 occurrences, 13 files)

Pattern analysis:
- `state_manager.current_frame = 5` - Direct assignment (39 occurrences)
- `window.state_manager.current_frame = 10` - Via MainWindow (43 occurrences)

**Affected test files:**
1. test_event_filter_navigation.py (7 occurrences)
2. test_keyframe_navigation.py (12 occurrences)
3. test_state_manager.py (28 occurrences)
4. test_tracking_point_status_commands.py (4 occurrences)
5. test_frame_change_coordinator.py (5 occurrences)
6. test_frame_highlight.py (7 occurrences)
7. test_global_shortcuts.py (2 occurrences)
8. test_multi_point_selection.py (2 occurrences)
9. test_unified_curve_rendering.py (3 occurrences)
10. test_keyboard_shortcuts_enhanced.py (2 occurrences)
11. test_data_service_synchronization.py (1 occurrence)
12. test_timeline_focus_behavior.py (1 occurrence)
13. stores/test_application_state_phase0a.py (8 occurrences)

### Recommended Strategy: **DIRECT DELEGATION**

**Simple Find-Replace Pattern:**
```python
# ❌ BEFORE (Phase 3)
state_manager.current_frame = 5
window.state_manager.current_frame = 10

# ✅ AFTER (Phase 4)
from stores.application_state import get_application_state
get_application_state().set_frame(5)
get_application_state().set_frame(10)
```

**Rationale:**
1. **Direct to Source:** No intermediate StateManager layer
2. **Explicit Intent:** Method call is clearer than property assignment
3. **Type Safe:** ApplicationState.set_frame() is the official API
4. **Consistent:** Matches other ApplicationState usage patterns

### Migration Steps

**Step 1:** Add import if not present
```python
from stores.application_state import get_application_state
```

**Step 2:** Find-replace in each test file
```bash
# Pattern 1: state_manager.current_frame =
# Replace with: get_application_state().set_frame(

# Pattern 2: window.state_manager.current_frame =
# Replace with: get_application_state().set_frame(
```

**Step 3:** Optional cleanup - create test helper
```python
# In conftest.py
def set_test_frame(frame: int) -> None:
    """Set current frame for tests."""
    get_application_state().set_frame(frame)
```

**Step 4:** Consider removing StateManager.current_frame setter
- After test migration, evaluate if setter is still needed
- Likely can be removed (property getter stays for backward compat)

---

## 3. Signal Connection Migration

### Current Signal Connections (signal_connection_manager.py:163-171)

```python
def _connect_signals(self) -> None:
    """Connect signals from state manager and shortcuts."""
    # 1. File/modification state (StateManager-owned)
    _ = self.main_window.state_manager.file_changed.connect(self.main_window.on_file_changed)
    _ = self.main_window.state_manager.modified_changed.connect(self.main_window.on_modified_changed)

    # 2. Selection state (forwarded from ApplicationState)
    _ = self.main_window.state_manager.selection_changed.connect(self.main_window.on_selection_changed)

    # 3. View state (StateManager-owned)
    _ = self.main_window.state_manager.view_state_changed.connect(self.main_window.on_view_state_changed)

    # 4. Frame range updates (DEPRECATED - uses synthetic data pattern)
    _ = self.main_window.state_manager.total_frames_changed.connect(
        lambda total: self.main_window.timeline_controller.set_frame_range(1, total)
    )
```

### StateManager Signal Forwarding (state_manager.py:72-73)

```python
def __init__(self, parent: QObject | None = None):
    # ...
    # Forward ApplicationState signals
    _ = self._app_state.frame_changed.connect(self.frame_changed.emit)  # Direct forward
    _ = self._app_state.selection_changed.connect(self._on_app_state_selection_changed)  # Adapter
```

**Adapter Function:**
```python
def _on_app_state_selection_changed(self, indices: set[int], curve_name: str) -> None:
    """Adapter to forward ApplicationState selection_changed signal.

    ApplicationState emits (indices, curve_name), StateManager emits just indices.
    """
    expected_curve = self._get_curve_name_for_selection()
    if curve_name == expected_curve:
        self.selection_changed.emit(indices)  # Emit without curve_name
```

### Signal Architecture Analysis

**StateManager Signals:**
- `file_changed` - File metadata (StateManager-owned, NO ApplicationState equivalent)
- `modified_changed` - Modification flag (StateManager-owned, NO ApplicationState equivalent)
- `selection_changed` - **Forwards** ApplicationState.selection_changed (strips curve_name)
- `view_state_changed` - View state (StateManager-owned, NO ApplicationState equivalent)
- `total_frames_changed` - DEPRECATED (should use ApplicationState.image_sequence_changed)
- `frame_changed` - **Forwards** ApplicationState.frame_changed (direct passthrough)

**ApplicationState Signals:**
- `state_changed` - Generic state change
- `curves_changed` - Curve data changed
- `selection_changed` - Selection changed **(includes curve_name parameter)**
- `active_curve_changed` - Active curve changed
- `frame_changed` - Frame changed
- `curve_visibility_changed` - Curve visibility changed
- `selection_state_changed` - Selection state changed
- `image_sequence_changed` - Image sequence changed

### Recommended Strategy: **SELECTIVE MIGRATION**

**Signals to KEEP in StateManager** (UI-owned state):
1. ✅ `file_changed` - File metadata is StateManager's domain
2. ✅ `modified_changed` - Modification flag is StateManager's domain
3. ✅ `view_state_changed` - View state (zoom, pan) is StateManager's domain

**Signals to MIGRATE to ApplicationState** (data-owned state):
1. ⚠️ `selection_changed` - Connect directly to ApplicationState (handler signature changes)
2. ❌ `total_frames_changed` - REMOVE, replace with `image_sequence_changed`

### Migration: selection_changed

**Handler Signature Change:**
```python
# ❌ BEFORE (Phase 3) - StateManager strips curve_name
def on_selection_changed(self, indices: set[int]) -> None:
    # Only gets indices, not which curve
    pass

# ✅ AFTER (Phase 4) - ApplicationState includes curve_name
def on_selection_changed(self, indices: set[int], curve_name: str) -> None:
    # Now knows which curve the selection belongs to
    pass
```

**Connection Change:**
```python
# ❌ BEFORE (Phase 3)
_ = self.main_window.state_manager.selection_changed.connect(
    self.main_window.on_selection_changed
)

# ✅ AFTER (Phase 4)
from stores.application_state import get_application_state
_ = get_application_state().selection_changed.connect(
    self.main_window.on_selection_changed
)
```

**Handler Update:**
```python
# MainWindow.on_selection_changed must accept curve_name parameter
def on_selection_changed(self, indices: set[int], curve_name: str) -> None:
    """Handle selection changes from ApplicationState.

    Args:
        indices: Selected point indices
        curve_name: Name of curve with selection change
    """
    # Update UI based on selection
    # Can now filter by curve_name if needed
    pass
```

### Migration: total_frames_changed → image_sequence_changed

**Current Pattern (DEPRECATED):**
```python
# Uses total_frames_changed to update timeline frame range
_ = self.main_window.state_manager.total_frames_changed.connect(
    lambda total: self.main_window.timeline_controller.set_frame_range(1, total)
)
```

**Problems:**
1. Relies on deprecated total_frames setter creating synthetic image_files
2. Lambda loses type information
3. Hardcoded min_frame=1 assumption
4. Doesn't react to actual data changes (curves or real images)

**Recommended Replacement:**
```python
# ✅ AFTER (Phase 4) - React to real data changes
from stores.application_state import get_application_state

# Connect to image sequence changes
_ = get_application_state().image_sequence_changed.connect(
    self._on_image_sequence_changed
)

# Connect to curve data changes (may affect frame range)
_ = get_application_state().curves_changed.connect(
    self._on_curves_changed
)

def _on_image_sequence_changed(self, files: list[str]) -> None:
    """Update timeline frame range when image sequence changes."""
    total = len(files) if files else 1
    self.main_window.timeline_controller.set_frame_range(1, max(1, total))

def _on_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
    """Update timeline frame range when curve data changes."""
    # Calculate frame range from active curve data
    active_curve = get_application_state().active_curve
    if active_curve and active_curve in curves:
        curve_data = curves[active_curve]
        if curve_data:
            frames = [int(point[0]) for point in curve_data]
            min_frame = min(frames)
            max_frame = max(frames)
            self.main_window.timeline_controller.set_frame_range(min_frame, max_frame)
```

**Rationale:**
1. **Data-Driven:** Timeline updates from real data changes, not synthetic setters
2. **Type-Safe:** Proper method instead of lambda
3. **Flexible:** Can derive min_frame from curve data, not hardcoded to 1
4. **Comprehensive:** Handles both image sequence AND curve data changes

---

## 4. Implementation Order

**Recommended sequence to minimize breakage:**

### Phase 4.1: Test Migrations (Low Risk)
1. ✅ **Migrate test current_frame setters** (13 files, ~82 occurrences)
   - Simple find-replace: `state_manager.current_frame =` → `get_application_state().set_frame(`
   - Run test suite to verify
   - **Risk:** Low (1:1 replacement)
   - **Duration:** 1-2 hours

2. ✅ **Migrate test total_frames setters** (~40 occurrences)
   - Replace with `ApplicationState.set_image_files([f"frame{i}.png" for i in range(1, n+1)])`
   - Create helper function in conftest.py for common patterns
   - Run test suite to verify
   - **Risk:** Medium (requires generating file lists)
   - **Duration:** 2-3 hours

### Phase 4.2: Signal Migrations (Medium Risk)
3. ⚠️ **Migrate selection_changed connections** (requires handler updates)
   - Audit all handlers connected to StateManager.selection_changed
   - Update handler signatures to accept `curve_name` parameter
   - Change connections to ApplicationState.selection_changed
   - Test selection behavior
   - **Risk:** Medium (handler signature changes)
   - **Duration:** 2-3 hours

4. ⚠️ **Replace total_frames_changed with image_sequence_changed**
   - Remove lambda connection to total_frames_changed
   - Add proper handler methods for image_sequence_changed and curves_changed
   - Test timeline frame range updates
   - **Risk:** Medium (signal flow changes)
   - **Duration:** 2-3 hours

### Phase 4.3: Production Code (Medium Risk)
5. ✅ **Remove production total_frames setter calls** (2 files)
   - Remove from timeline_tabs.py:620
   - Remove from timeline_controller.py:499
   - Verify frame range updates via signals from Step 4
   - **Risk:** Medium (depends on signal migration working)
   - **Duration:** 1 hour

### Phase 4.4: Cleanup (Low Risk)
6. ✅ **Remove deprecated StateManager code**
   - Delete `total_frames.setter` method
   - Delete `total_frames_changed` signal definition
   - Optional: Remove `current_frame.setter` if no longer needed
   - Run full test suite
   - **Risk:** Low (all callsites already migrated)
   - **Duration:** 30 minutes

**Total Estimated Duration:** 10-14 hours across 6 steps

---

## 5. Architectural Risks & Mitigations

### Risk 1: Signal Timing Changes ⚠️

**Impact:** Moving from StateManager forwarding to direct ApplicationState connections might change signal emission order.

**Example:**
```python
# Before: StateManager forwards synchronously
ApplicationState.set_frame(10)
  → ApplicationState.frame_changed.emit(10)
    → StateManager.frame_changed.emit(10) [SYNCHRONOUS]
      → MainWindow.on_frame_changed(10)

# After: Direct connection
ApplicationState.set_frame(10)
  → ApplicationState.frame_changed.emit(10)
    → MainWindow.on_frame_changed(10) [DIRECT]
```

**Mitigation:**
- FrameChangeCoordinator already handles deterministic frame change ordering (uses explicit phases)
- If selection_changed timing issues arise, apply similar coordinator pattern
- Qt signal ordering is non-deterministic anyway - rely on coordinator patterns, not signal order

**Action:** Monitor for race conditions during testing, add coordinators if needed.

---

### Risk 2: Handler Signature Changes for selection_changed ⚠️

**Impact:** ApplicationState.selection_changed emits `(indices, curve_name)`, StateManager.selection_changed emits just `indices`.

**Example:**
```python
# Before (works)
def on_selection_changed(self, indices: set[int]) -> None:
    pass

# After (breaks if not updated)
def on_selection_changed(self, indices: set[int]) -> None:
    # ERROR: Missing required curve_name parameter
    pass
```

**Mitigation:**
1. Audit ALL handlers connected to StateManager.selection_changed BEFORE migration
2. Update handler signatures to accept curve_name parameter
3. Use type checking (`./bpr`) to find signature mismatches
4. Add defensive checks if curve_name might be None

**Action:**
```bash
# Find all selection_changed handlers
grep -r "def.*on_selection_changed" ui/
grep -r "\.selection_changed\.connect" ui/ tests/

# Verify signature compatibility
./bpr ui/ --errors-only
```

---

### Risk 3: total_frames_changed Removal Breaks Timeline Updates ⚠️

**Impact:** Timeline frame range might not update when image sequence or curve data changes.

**Symptoms:**
- Timeline shows wrong frame range after loading images
- Timeline doesn't expand when tracking data extends beyond current range
- Timeline doesn't update when switching between curves

**Mitigation:**
1. Connect to BOTH `image_sequence_changed` AND `curves_changed` signals
2. Properly calculate frame range from curve data (min/max from actual frames)
3. Handle edge cases (empty curves, no image sequence, etc.)
4. Test all data loading scenarios

**Action:**
```python
# Comprehensive timeline update handler
def _update_timeline_from_data(self) -> None:
    """Update timeline frame range from all available data sources."""
    state = get_application_state()

    # Get frame range from image sequence
    image_total = state.get_total_frames()

    # Get frame range from active curve data
    active_curve = state.active_curve
    curve_min, curve_max = 1, 1
    if active_curve:
        curve_data = state.get_curve_data(active_curve)
        if curve_data:
            frames = [int(point[0]) for point in curve_data]
            curve_min = min(frames)
            curve_max = max(frames)

    # Use the wider range
    min_frame = min(1, curve_min)
    max_frame = max(image_total, curve_max)

    self.timeline_controller.set_frame_range(min_frame, max_frame)
```

---

### Risk 4: Test Fixtures Depend on Synthetic total_frames ⚠️

**Impact:** Tests might fail if they expect `total_frames` without `image_files`.

**Example:**
```python
# Before (Phase 3) - synthetic data
state_manager.total_frames = 100  # Creates fake image_files
assert state_manager.current_frame <= 100  # Works

# After (Phase 4) - no image_files set
# total_frames = 1 (default)
assert state_manager.current_frame <= 100  # FAILS!
```

**Mitigation:**
1. Review ALL test fixtures in conftest.py
2. Update fixtures to properly set image_files
3. Create helper functions for common patterns
4. Run full test suite after each fixture update

**Action:**
```python
# In conftest.py
@pytest.fixture
def app_state_with_frames(qtbot):
    """ApplicationState with 100 frames for testing."""
    state = get_application_state()
    state.set_image_files([f"frame{i:04d}.png" for i in range(1, 101)])
    yield state
    # Cleanup
    state.set_image_files([])
```

---

### Risk 5: StateManager Becomes Dead Code 🤔

**Impact:** After Phase 4, StateManager might only handle file/UI state, with most data access going through ApplicationState.

**Current StateManager Responsibilities:**
- ✅ File state (current_file, is_modified, file_format) - **STAYS**
- ✅ View state (zoom, pan, view_bounds) - **STAYS**
- ✅ UI state (window size, tool selection, history) - **STAYS**
- ❌ Data state (track_data, selection) - **MIGRATED** to ApplicationState
- ❌ Frame state (current_frame) - **MIGRATED** to ApplicationState
- ❌ Image state (image_files, total_frames) - **MIGRATED** to ApplicationState

**Post-Phase 4 StateManager Scope:**
- File metadata and modification tracking
- View state (zoom, pan, camera)
- UI preferences (window size, tool selection)
- Playback state
- History UI state (can_undo, can_redo)

**Evaluation:** StateManager still serves a valid purpose - **UI and workflow state management**. It's the complement to ApplicationState (data management).

**No Action Required:** Architecture is correct - two focused state managers:
- **ApplicationState:** Data and selection (single source of truth)
- **StateManager:** UI preferences and workflow state

---

## 6. Testing Strategy

### Unit Tests
- ✅ Test ApplicationState.set_frame() directly
- ✅ Test ApplicationState.set_image_files() with various inputs
- ✅ Test signal emissions from ApplicationState
- ✅ Verify StateManager no longer creates synthetic data

### Integration Tests
- ⚠️ Test timeline frame range updates from image loading
- ⚠️ Test timeline frame range updates from curve data changes
- ⚠️ Test selection changes propagate correctly with curve_name
- ⚠️ Test frame navigation with ApplicationState.set_frame()

### Regression Tests
- ⚠️ Run FULL test suite after each migration step
- ⚠️ Test manual workflows (load images, load curves, select points)
- ⚠️ Verify no broken signal connections
- ⚠️ Check for performance regressions (signal storms)

---

## 7. Success Criteria

Phase 4 is complete when:

1. ✅ **All test current_frame setters migrated** (0 occurrences of `state_manager.current_frame =` in tests)
2. ✅ **All test total_frames setters migrated** (0 occurrences of `state_manager.total_frames =` in tests)
3. ✅ **Production total_frames setter calls removed** (timeline_tabs.py, timeline_controller.py)
4. ✅ **StateManager.total_frames setter deleted** (deprecated code removed)
5. ✅ **StateManager.total_frames_changed signal removed** (replaced with image_sequence_changed)
6. ✅ **Signal connections migrated** (selection_changed to ApplicationState, total_frames_changed removed)
7. ✅ **All tests pass** (full test suite green)
8. ✅ **Type checking passes** (`./bpr` with no new errors)
9. ✅ **Manual testing confirms** timeline updates, selection, and frame navigation work correctly

---

## 8. Rollback Plan

If Phase 4 causes critical issues:

1. **Immediate Rollback:** Revert signal connection changes in signal_connection_manager.py
2. **Test Rollback:** Revert test file changes (git reset individual files)
3. **Production Rollback:** Restore total_frames setter calls in timeline_tabs.py and timeline_controller.py
4. **Full Rollback:** `git revert` all Phase 4 commits

**Prevention:** Commit each migration step separately for granular rollback capability.

---

## 9. Documentation Updates

After Phase 4 completion:

1. Update **CLAUDE.md** - Remove references to deprecated StateManager setters
2. Update **PLAN_TAU.md** - Mark Phase 4 complete
3. Create **PHASE4_MIGRATION_NOTES.md** - Document any gotchas or lessons learned
4. Update **StateManager docstrings** - Clarify its focused scope (UI state only)
5. Update **ApplicationState docstrings** - Emphasize it's the data source of truth

---

## Appendix A: Code Patterns

### Pattern 1: Test Frame Setup (Before/After)

```python
# ❌ BEFORE (Phase 3)
def test_frame_navigation(window):
    window.state_manager.total_frames = 100  # Synthetic data
    window.state_manager.current_frame = 50
    # ... test code

# ✅ AFTER (Phase 4)
def test_frame_navigation(window):
    state = get_application_state()
    state.set_image_files([f"frame{i:04d}.png" for i in range(1, 101)])
    state.set_frame(50)
    # ... test code

# ✅ BETTER (Phase 4) - Using helper
def test_frame_navigation(app_state_with_100_frames):
    app_state_with_100_frames.set_frame(50)
    # ... test code
```

### Pattern 2: Signal Connection (Before/After)

```python
# ❌ BEFORE (Phase 3)
class MainWindow(QMainWindow):
    def __init__(self):
        # ...
        _ = self.state_manager.total_frames_changed.connect(
            lambda total: self.timeline_controller.set_frame_range(1, total)
        )
        _ = self.state_manager.selection_changed.connect(self.on_selection_changed)

    def on_selection_changed(self, indices: set[int]) -> None:
        # Only knows indices, not which curve
        pass

# ✅ AFTER (Phase 4)
class MainWindow(QMainWindow):
    def __init__(self):
        # ...
        state = get_application_state()
        _ = state.image_sequence_changed.connect(self._on_image_sequence_changed)
        _ = state.curves_changed.connect(self._on_curves_changed)
        _ = state.selection_changed.connect(self.on_selection_changed)

    def _on_image_sequence_changed(self, files: list[str]) -> None:
        total = len(files) if files else 1
        self.timeline_controller.set_frame_range(1, max(1, total))

    def _on_curves_changed(self, curves: dict[str, CurveDataList]) -> None:
        # Calculate frame range from curve data
        # ...

    def on_selection_changed(self, indices: set[int], curve_name: str) -> None:
        # Now knows both indices AND which curve
        pass
```

---

## Appendix B: Affected Files Checklist

### Production Code (5 files)
- [ ] ui/state_manager.py - Remove total_frames setter, remove current_frame setter (optional)
- [ ] ui/timeline_tabs.py - Remove total_frames setter call (line 620)
- [ ] ui/controllers/timeline_controller.py - Remove total_frames setter call (line 499)
- [ ] ui/controllers/signal_connection_manager.py - Migrate signal connections
- [ ] ui/main_window.py - Update selection_changed handler signature

### Test Files - current_frame setters (13 files)
- [ ] tests/test_event_filter_navigation.py (7 occurrences)
- [ ] tests/test_keyframe_navigation.py (12 occurrences)
- [ ] tests/test_state_manager.py (28 occurrences)
- [ ] tests/test_tracking_point_status_commands.py (4 occurrences)
- [ ] tests/test_frame_change_coordinator.py (5 occurrences)
- [ ] tests/test_frame_highlight.py (7 occurrences)
- [ ] tests/test_global_shortcuts.py (2 occurrences)
- [ ] tests/test_multi_point_selection.py (2 occurrences)
- [ ] tests/test_unified_curve_rendering.py (3 occurrences)
- [ ] tests/test_keyboard_shortcuts_enhanced.py (2 occurrences)
- [ ] tests/test_data_service_synchronization.py (1 occurrence)
- [ ] tests/test_timeline_focus_behavior.py (1 occurrence)
- [ ] tests/stores/test_application_state_phase0a.py (8 occurrences)

### Test Files - total_frames setters (~10 files)
- [ ] tests/test_timeline_tabs.py
- [ ] tests/test_timeline_scrubbing.py
- [ ] tests/test_timeline_integration.py
- [ ] tests/test_timeline_functionality.py
- [ ] tests/test_timeline_focus_behavior.py
- [ ] tests/test_frame_change_coordinator.py
- [ ] tests/test_frame_highlight.py
- [ ] tests/test_state_manager.py
- [ ] tests/test_file_operations.py
- [ ] tests/test_multi_point_tracking_merge.py

### Test Fixtures (2 files)
- [ ] tests/conftest.py - Add helper for frame range setup
- [ ] tests/fixtures/main_window_fixtures.py - Update total_frames initialization

---

**End of Strategy Document**

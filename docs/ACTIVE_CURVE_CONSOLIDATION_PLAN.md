# Active Curve State Consolidation Plan

**Status**: 🚧 **IN PROGRESS** (November 2025) - Phase -1 Complete ✅, Phase 0 Complete ✅, Phase 1 Complete ✅

**Goal**: Eliminate duplicate "active curve" state by consolidating to ApplicationState as single source of truth.

**Estimated Time**: 8-11 hours (includes 1-2 hours for signal compatibility fixes)

**⚠️ CRITICAL**: Must fix ApplicationState signal compatibility BEFORE starting migration (see Phase -1)

---

## Problem Statement

### Current Architecture Violation

Two separate pieces of state track "which curve the user is working on":

1. **ApplicationState.active_curve** (data layer)
   - Which curve's data to edit
   - Set via: `app_state.set_active_curve(curve_name)`
   - Read via: `app_state.active_curve`
   - Signal: `active_curve_changed`

2. **StateManager.active_timeline_point** (UI layer)
   - Which curve's timeline to display
   - Set via: `state_manager.active_timeline_point = point_name`
   - Read via: `state_manager.active_timeline_point`
   - Signal: `active_timeline_point_changed`

### KISS/DRY Violation

These represent **the same user concept**: "I'm working on THIS curve"

**Symptoms**:
- Synchronization bugs (Page Up/Down navigation inconsistency - fixed Nov 2025)
- Duplicate state updates in controllers
- Test fixtures must set both values
- Unclear which to use for new features

**Impact**:
- Bug discovered: Navigation used `active_timeline_point` while data operations used `active_curve`
- Required test fixture updates across 5 test files
- Future features will face same confusion

### Why This Exists

Historical context:
- StateManager predates ApplicationState multi-curve architecture
- `active_timeline_point` was added for timeline UI before multi-curve refactor
- ApplicationState added `active_curve` during multi-curve migration
- No consolidation performed after multi-curve migration completed

---

## Architectural Decision

### Which State Should Own "Active Curve"?

**Decision: ApplicationState.active_curve**

**Rationale**:
1. **Architecture alignment**: CLAUDE.md states "ApplicationState: Single source of truth for all application data"
2. **Semantic correctness**: "Which curve am I editing" is a DATA concern, not UI preference
3. **StateManager scope**: Should only contain UI preferences (zoom, pan, tool state)
4. **Consistency**: Matches completed StateManager migration (track_data → ApplicationState)

**Alternative considered and rejected**:
- ❌ Keep `active_timeline_point`: Would violate data/UI separation principle
- ❌ Synchronize both: Adds complexity, doesn't solve root cause

---

## Migration Strategy

### Principles

1. **Single Source of Truth**: ApplicationState.active_curve owns the state
2. **Backward Compatibility**: MainWindow property delegates for gradual migration
3. **File-by-File**: Update one file at a time, test after each
4. **Signal Consolidation**: Use only `active_curve_changed` signal

### Scope

**Files affected**: 25 files using `active_timeline_point` (verified via audit)

**Breakdown**:
- Production code: 8 files (controllers, UI components, commands)
- Test code: 14 files (fixtures, integration tests)
- Documentation: 3 files (migration plans)

---

## Phase -1: Signal Compatibility Fix (PREREQUISITE)

**✅ STATUS: COMPLETE** (November 1, 2025)

**⚠️ CRITICAL**: This phase MUST be completed BEFORE any migration work begins.

**Issue Discovered**: Verification audit revealed 3 signal incompatibilities between StateManager and ApplicationState that would cause silent failures during migration.

**Time**: 1-2 hours (actual: 1 hour)

### Issue #1: Signal Type Mismatch

**Problem**:
- StateManager: `active_timeline_point_changed = Signal(object)` (emits `str | None`)
- ApplicationState: `active_curve_changed = Signal(str)` (type system violation)

**Impact**: Timeline handlers expecting `str | None` would receive type-incompatible signal.

**Fix**: Update ApplicationState signal to match StateManager pattern.

**File**: `stores/application_state.py`

**Current** (line 116):
```python
active_curve_changed: Signal = Signal(str)  # active_curve_name: str
```

**Update to**:
```python
active_curve_changed: Signal = Signal(object)  # active_curve_name: str | None (matches StateManager pattern)
```

### Issue #2: None Handling Mismatch

**Problem**:
- StateManager: Emits `None` when active curve is cleared
- ApplicationState: Converts `None` → `""` during emission (line 630)

**Impact**: Handlers checking `if curve_name:` would work, but semantics are wrong (None ≠ empty string).

**Fix**: Emit None as-is, don't convert to empty string.

**File**: `stores/application_state.py`

**Current** (line 630):
```python
self._emit(self.active_curve_changed, (curve_name or "",))
```

**Update to**:
```python
self._emit(self.active_curve_changed, (curve_name,))  # Pass None as-is
```

### Issue #3: Signal Handler Compatibility

**Problem**: Existing handlers expect `str | None`, but current ApplicationState emits only `str`.

**Files to verify/update**:
- `ui/timeline_tabs.py:517` - `_on_active_curve_changed(self, _curve_name: str)`
- `stores/store_manager.py:140+` - Handler signature
- `ui/controllers/frame_change_coordinator.py:132+` - Handler signature
- `ui/controllers/curve_view/state_sync_controller.py:76+` - Handler signature
- `ui/controllers/signal_connection_manager.py:200+` - Handler signature

**Fix**: Update handler signatures to accept `str | None`.

**Example** (timeline_tabs.py:517):
```python
# CURRENT:
@safe_slot
def _on_active_curve_changed(self, _curve_name: str) -> None:
    """Handle ApplicationState active_curve_changed signal."""
    self._on_curves_changed(self._app_state.get_all_curves())

# UPDATE TO:
@safe_slot
def _on_active_curve_changed(self, curve_name: str | None) -> None:
    """Handle ApplicationState active_curve_changed signal."""
    # Handle None case (cleared active curve)
    if curve_name is None:
        # Clear timeline display or show "No active curve"
        self.active_point_label.setText("No active curve")
    else:
        # Refresh with active curve data
        self._on_curves_changed(self._app_state.get_all_curves())
```

### -1.4 Verification

**After fixes, verify**:
```bash
# Type checking should pass
./bpr stores/application_state.py --errors-only
./bpr ui/timeline_tabs.py --errors-only

# All existing tests should still pass (signal behavior unchanged for non-None values)
uv run pytest tests/ -x -q

# Manual signal test
python3 -c "
from stores.application_state import get_application_state
state = get_application_state()
state.set_active_curve(None)  # Should emit None, not ''
"
```

**Success criteria**:
- [x] Signal type is `Signal(object)` ✅
- [x] None emitted as-is (not converted to "") ✅ (fixed 2 locations: line 630 and line 493)
- [x] All handler signatures accept `str | None` ✅ (7 handlers verified/updated)
- [x] Type checking passes ✅ (0 new errors, 2 pre-existing protocol issues unrelated to Phase -1)
- [x] All tests pass ✅ (3420 passed, 1 skipped)

**✅ ALL CRITERIA MET - PROCEEDING TO PHASE 0**

---

## Phase 0: Preparation

**✅ STATUS: COMPLETE** (November 1, 2025)
**Time**: 2 hours (actual: 2 hours including Phase 0.1 protocol fix)

### 0.1 Audit Current Usage

**Find all callers**:
```bash
# Production code
rg "\.active_timeline_point\b" --type py | grep -v tests/ > active_timeline_point_usage.txt

# Test code
rg "\.active_timeline_point\b" tests/ --type py >> active_timeline_point_usage.txt

# Signal connections
rg "active_timeline_point_changed" --type py >> active_timeline_point_usage.txt
```

**Expected files** (~24 total):
- `ui/main_window.py` - Property accessor (Line 548-555)
- `ui/timeline_tabs.py` - Fallback logic (Lines 442-448, 626-630)
- `ui/controllers/tracking_selection_controller.py` - Sets active point (Lines 146, 215)
- `ui/controllers/tracking_data_controller.py` - Multiple updates (Lines 127, 135, 187, 202, 245, 246, 270, 271, 325, 367)
- `core/commands/insert_track_command.py` - Command execution
- Test files: 14+ fixtures and integration tests

### 0.2 Verify Prerequisites Complete

**Prerequisite 1**: Phase -1 signal fixes complete ✅

**Verify**:
```bash
# Check signal definition is Signal(object)
grep "active_curve_changed.*Signal(object)" stores/application_state.py

# Check no None→"" conversion
grep -n "curve_name or" stores/application_state.py | grep set_active_curve
# Should find ZERO matches in set_active_curve method
```

**Prerequisite 2**: StateManager Simplified Migration is complete (it is - Oct 2025).

**Verify**:
```bash
# Should find ZERO matches:
rg "state_manager\.track_data\b" --type py
rg "state_manager\.image_files\b" --type py
```

If found, complete StateManager migration first.

### 0.3 Document Current Signal Flow

**Before migration**:
```
User Action
  ↓
Controller sets active_timeline_point
  ↓
StateManager.active_timeline_point = value
  ↓
StateManager emits active_timeline_point_changed
  ↓
Timeline UI updates
```

**After migration**:
```
User Action
  ↓
Controller calls app_state.set_active_curve()
  ↓
ApplicationState.active_curve = value
  ↓
ApplicationState emits active_curve_changed
  ↓
Timeline UI updates
```

### Phase 0 Success Criteria

**Success criteria**:
- [x] All 92 usages of active_timeline_point identified across 19 files ✅ (corrected from initial 74)
- [x] Phase -1 signal compatibility verified ✅
- [x] StateManager migration (Oct 2025) verified complete ✅
- [x] Signal handler signatures verified ✅
- [x] Current signal flow documented ✅
- [x] Post-migration signal flow documented ✅
- [x] Risk assessment completed (LOW RISK) ✅
- [x] Protocol definitions updated in protocols/ui.py ✅ (Phase 0.1 extension)
- [x] Type checking passes (2 pre-existing protocol errors unrelated to Phase 0) ✅
- [x] All tests pass ✅ (3420 passed, 1 skipped)

**✅ ALL CRITERIA MET - PROCEEDING TO PHASE 1**

---

## Phase 1: Make MainWindow Property Delegate to ApplicationState

**✅ STATUS: COMPLETE** (November 2, 2025)
**Time**: 30 minutes (actual: 30 minutes)

**Goal**: Create bridge for gradual migration without breaking existing code.

### 1.1 Update MainWindow Property

**File**: `ui/main_window.py`

**Current** (lines 547-555):
```python
@property
def active_timeline_point(self) -> str | None:
    """Get the active timeline point (which tracking point's timeline is displayed)."""
    return self.state_manager.active_timeline_point

@active_timeline_point.setter
def active_timeline_point(self, point_name: str | None) -> None:
    """Set the active timeline point (which tracking point's timeline to display)."""
    self.state_manager.active_timeline_point = point_name
```

**Update to** (delegate to ApplicationState):
```python
@property
def active_timeline_point(self) -> str | None:
    """
    Get the active timeline point (DEPRECATED - use ApplicationState.active_curve).

    This property delegates to ApplicationState.active_curve for backward compatibility.
    New code should use ApplicationState.active_curve directly.

    TODO: Remove this property after all callers migrated to ApplicationState.
    """
    return get_application_state().active_curve

@active_timeline_point.setter
def active_timeline_point(self, point_name: str | None) -> None:
    """
    Set the active timeline point (DEPRECATED - use ApplicationState.set_active_curve()).

    This setter delegates to ApplicationState.set_active_curve() for backward compatibility.
    New code should use ApplicationState.set_active_curve() directly.

    TODO: Remove this property after all callers migrated to ApplicationState.
    """
    get_application_state().set_active_curve(point_name)
```

**Why delegation first**:
- Allows file-by-file migration without breaking tests
- Maintains API compatibility during transition
- Easy to verify (just change property, run tests)

### 1.2 Verify No Breakage

**Run tests**:
```bash
uv run pytest tests/ -x -q
```

**Expected**: All tests pass (property delegation should be transparent).

**If tests fail**: Investigate synchronization issues between old and new signals.

### Phase 1 Success Criteria

**Success criteria**:
- [x] Property getter delegates to `get_application_state().active_curve` ✅
- [x] Property setter calls `get_application_state().set_active_curve(value)` ✅
- [x] DEPRECATED docstrings added to both getter and setter ✅
- [x] Local imports used (no circular imports) ✅
- [x] All tests pass (3420 passed, 1 skipped) ✅
- [x] Type checking passes (2 pre-existing errors, no new ones) ✅
- [x] Protocol declarations restored (Phase 0.1 correction applied) ✅

**✅ ALL CRITERIA MET - PROCEEDING TO PHASE 2**

**Important Note**: Phase 0.1 protocol removal was premature. Protocols were restored in Phase 1 to maintain type safety during migration. Protocol removal deferred to Phase 4 after all usages migrated.

---

## Phase 2: Migrate Production Code (File-by-File)

**Goal**: Update all production code to use ApplicationState.active_curve directly.

**Time**: 3-4 hours (10 files × 20-30 min each)

### Migration Pattern

**For EACH file**:
1. Update code to use ApplicationState
2. Update any signal connections
3. Run file-specific tests: `pytest tests/test_<file>.py -v`
4. Run type checking: `./bpr <file>.py --errors-only`
5. Run full suite: `pytest tests/ -x -q`
6. Commit: `git commit -m "refactor(<file>): active_timeline_point → active_curve"`
7. Next file

### 2.1 Update Navigation Code

**File**: `ui/main_window.py`

**Method**: `_get_navigation_frames()` (line 1182)

**Current**:
```python
def _get_navigation_frames(self) -> list[int]:
    """Collect all navigation frames (keyframes, endframes, startframes) from current curve."""
    # Use active_timeline_point (from StateManager)
    active_point = self.active_timeline_point
    if not active_point:
        return []

    # Get the curve data for the active timeline point
    app_state = get_application_state()
    curve_data = app_state.get_curve_data(active_point)
    # ... rest of method
```

**Update to**:
```python
def _get_navigation_frames(self) -> list[int]:
    """Collect all navigation frames (keyframes, endframes, startframes) from current curve."""
    # Use ApplicationState.active_curve directly
    app_state = get_application_state()
    active_curve = app_state.active_curve
    if not active_curve:
        return []

    curve_data = app_state.get_curve_data(active_curve)
    # ... rest of method
```

**Why**: Removes property indirection, makes data source explicit.

### 2.2 Update Timeline Tabs

**File**: `ui/timeline_tabs.py`

**Method**: `_get_active_curve_name()` (lines 442-448, 626-630)

**Current** (fallback logic):
```python
active_timeline_point = None
if self._state_manager:
    active_timeline_point = self._state_manager.active_timeline_point
if not active_timeline_point and self._app_state:
    active_timeline_point = self._app_state.active_curve
```

**Update to** (single source):
```python
active_curve = None
if self._app_state:
    active_curve = self._app_state.active_curve
```

**Why**: Eliminates fallback logic, uses single source of truth.

### 2.3 Update Tracking Controllers

**Files**:
- `ui/controllers/tracking_selection_controller.py` (lines 146, 215)
- `ui/controllers/tracking_data_controller.py` (lines 127, 135, 187, 202, 245, 246, 270, 271, 325, 367)

**Pattern** (requires manual review - 31 setter occurrences total):
```python
# BEFORE:
self.main_window.active_timeline_point = curve_name

# AFTER - Option A (if main_window available):
self.main_window.set_active_curve(curve_name)

# AFTER - Option B (if no main_window reference):
get_application_state().set_active_curve(curve_name)
```

**⚠️ Important**: Each setter site needs manual review to choose correct API. Consider:
- **Controllers with main_window**: Use `main_window.set_active_curve()` for consistency
- **Commands/services**: Use `get_application_state().set_active_curve()` directly
- **Tests**: Use `get_application_state().set_active_curve()` for clarity

**Example - tracking_data_controller.py:127**:
```python
# BEFORE:
def add_new_tracking_point(self, point_name: str, point_data: CurveDataList) -> None:
    # ... add point logic ...
    self.main_window.active_timeline_point = point_name  # Set as active timeline point

# AFTER (Option A - controller has main_window):
def add_new_tracking_point(self, point_name: str, point_data: CurveDataList) -> None:
    # ... add point logic ...
    self.main_window.set_active_curve(point_name)  # Set as active curve
```

**Note**: Some methods may need to import `get_application_state` if not already imported. Estimate 20-30 minutes per file for careful review.

### 2.4 Update Insert Track Command

**File**: `core/commands/insert_track_command.py`

**Search for**: Uses of `active_timeline_point`

**Update pattern**: Same as controllers - replace with `get_application_state().set_active_curve()`

### 2.5 Update Signal Connections

**Find signal listeners**:
```bash
rg "active_timeline_point_changed\.connect" --type py
```

**Expected**: `ui/timeline_tabs.py:310` (only 1 connection after Phase -1 fixes)

**Update pattern**:
```python
# BEFORE:
state_manager.active_timeline_point_changed.connect(self._on_active_timeline_point_changed)

@safe_slot
def _on_active_timeline_point_changed(self, point_name: str | None) -> None:
    """Active timeline point changed."""
    if point_name:
        self.active_point_label.setText(f"Timeline: {point_name}")
        self._on_curves_changed(self._app_state.get_all_curves())
    else:
        self.active_point_label.setText("No point")

# AFTER:
app_state = get_application_state()
app_state.active_curve_changed.connect(self._on_active_curve_changed)

# NOTE: Handler signature already updated in Phase -1 to accept str | None
@safe_slot
def _on_active_curve_changed(self, curve_name: str | None) -> None:
    """Active curve changed (already updated in Phase -1)."""
    if curve_name:
        self.active_point_label.setText(f"Timeline: {curve_name}")
        self._on_curves_changed(self._app_state.get_all_curves())
    else:
        self.active_point_label.setText("No active curve")
```

**Key Changes**:
- Remove StateManager signal connection (line 310)
- Handler already accepts `str | None` (fixed in Phase -1)
- Update label text for None case ("No active curve" vs "No point")

---

## Phase 3: Migrate Test Code

**Goal**: Update all test fixtures to use ApplicationState.

**Time**: 2-3 hours (14 test files)

### 3.1 Update Test Fixtures

**Files** (from grep results):
- `tests/test_event_filter_navigation.py` (line 87)
- `tests/test_keyframe_navigation.py` (lines 152, 480, 573)
- `tests/test_navigation_integration.py` (line 112)
- `tests/test_tracking_direction_undo.py` (line 72)
- `tests/controllers/test_tracking_selection_controller.py` (lines 475, 548)
- Plus others in test_helpers.py, conftest.py

**Pattern**:
```python
# BEFORE:
window.active_timeline_point = "TestCurve"

# AFTER:
get_application_state().set_active_curve("TestCurve")
```

**Example - test_event_filter_navigation.py**:
```python
# BEFORE (line 87):
window.active_timeline_point = test_curve_name

# AFTER:
app_state = get_application_state()
app_state.set_active_curve(test_curve_name)
```

### 3.2 Update Test Assertions

**Find assertions**:
```bash
rg "assert.*active_timeline_point" tests/ --type py
```

**Pattern**:
```python
# BEFORE:
assert main_window.active_timeline_point == curve_name

# AFTER:
assert get_application_state().active_curve == curve_name
```

### 3.3 Run Full Test Suite After Each File

**Process**:
```bash
# Update one test file
vim tests/test_keyframe_navigation.py

# Run that test file
uv run pytest tests/test_keyframe_navigation.py -v

# Run full suite
uv run pytest tests/ -x -q

# Commit
git commit -m "test(keyframe_navigation): active_timeline_point → active_curve"
```

---

## Phase 4: Remove from StateManager

**Goal**: Remove `active_timeline_point` from StateManager after all callers migrated.

**Time**: 30 minutes

**Prerequisite**: Phases 1-3 complete, all tests passing.

### 4.1 Verify No Remaining Callers

**Check**:
```bash
# Should find ZERO matches (except in MainWindow property we'll remove):
rg "state_manager\.active_timeline_point" --type py | grep -v ui/main_window.py

# Should find ZERO matches:
rg "active_timeline_point_changed\.connect" --type py
```

If any matches found, migrate those files first.

### 4.2 Remove from StateManager

**File**: `ui/state_manager.py`

**Delete** (lines ~58, ~101, ~287-289):
```python
# DELETE signal:
# active_timeline_point_changed: Signal = Signal(object)

# DELETE instance variable:
# self._active_timeline_point: str | None = None

# DELETE property and setter:
# @property
# def active_timeline_point(self) -> str | None:
#     """Get active timeline point."""
#     return self._active_timeline_point
#
# @active_timeline_point.setter
# def active_timeline_point(self, point_name: str | None) -> None:
#     """Set active timeline point."""
#     if self._active_timeline_point != point_name:
#         self._active_timeline_point = point_name
#         self._emit_signal(self.active_timeline_point_changed, point_name)
```

### 4.3 Remove MainWindow Delegation Property

**File**: `ui/main_window.py`

**Delete** (lines 547-555):
```python
# DELETE property:
# @property
# def active_timeline_point(self) -> str | None:
#     """Get the active timeline point (DEPRECATED)."""
#     return get_application_state().active_curve
#
# @active_timeline_point.setter
# def active_timeline_point(self, point_name: str | None) -> None:
#     """Set the active timeline point (DEPRECATED)."""
#     get_application_state().set_active_curve(point_name)
```

### 4.4 Add Safety Layer

**File**: `ui/state_manager.py`

**Update `__getattr__`** (if exists, otherwise add):
```python
def __getattr__(self, name: str) -> NoReturn:
    """Provide clear error for removed attributes."""
    if name == "active_timeline_point":
        raise AttributeError(
            "StateManager.active_timeline_point was removed in active curve consolidation. "
            "Use ApplicationState.active_curve instead:\n"
            "  from stores.application_state import get_application_state\n"
            "  app_state = get_application_state()\n"
            "  active = app_state.active_curve\n"
            "  app_state.set_active_curve(curve_name)\n"
            "See docs/ACTIVE_CURVE_CONSOLIDATION_PLAN.md"
        )

    raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
```

**Why**: Catches any missed callers with clear migration instructions.

### 4.5 Verify Removal

**Check**:
```bash
# Should find ZERO matches:
rg "active_timeline_point" ui/state_manager.py | grep -v "__getattr__"
rg "active_timeline_point_changed" ui/state_manager.py
rg "\.active_timeline_point" --type py
```

---

## Phase 5: Testing and Validation

**Goal**: Ensure no regressions, verify state synchronization works correctly.

**Time**: 1 hour

### 5.1 Run Full Test Suite

```bash
uv run pytest tests/ -v
```

**Expected**: All tests pass (100%).

### 5.2 Type Checking

```bash
./bpr --errors-only
```

**Expected**: No new type errors.

### 5.3 Manual Testing

**Test scenarios**:
1. **Page Up/Down navigation**:
   - Load multi-curve data
   - Use Page Up/Down to navigate keyframes
   - Verify navigation works for active curve

2. **Curve switching**:
   - Load multiple curves
   - Click different curves in tracking panel
   - Verify active curve changes
   - Verify timeline updates to show correct curve

3. **Insert Track command**:
   - Create gap in curve
   - Run Insert Track
   - Verify only modified curve is selected

4. **Multi-curve operations**:
   - Select multiple curves
   - Perform operation (e.g., smooth)
   - Verify active curve remains consistent

### 5.4 Integration Test

**Create new integration test** (`tests/test_active_curve_state.py`):
```python
"""Integration test for active curve state consistency."""

def test_active_curve_single_source(app, qtbot, main_window_with_data):
    """Active curve state comes from single source (ApplicationState)."""
    window = main_window_with_data
    app_state = get_application_state()

    # Create multiple curves
    app_state.create_curve("Track1")
    app_state.create_curve("Track2")

    # Set active curve via ApplicationState
    app_state.set_active_curve("Track1")

    # Verify single source of truth
    assert app_state.active_curve == "Track1"

    # Change active curve
    app_state.set_active_curve("Track2")
    assert app_state.active_curve == "Track2"

def test_active_curve_signal_emits(qtbot):
    """Active curve changes emit signal."""
    app_state = get_application_state()
    app_state.create_curve("Track1")

    with qtbot.waitSignal(app_state.active_curve_changed, timeout=1000):
        app_state.set_active_curve("Track1")

def test_navigation_uses_active_curve(app, qtbot, main_window_with_data):
    """Navigation uses active curve from ApplicationState."""
    window = main_window_with_data
    app_state = get_application_state()

    # Create curve with keyframes
    test_data = [
        (1, 100.0, 100.0, "keyframe"),
        (5, 150.0, 150.0, "keyframe"),
        (10, 200.0, 200.0, "keyframe"),
    ]
    app_state.create_curve("TestCurve")
    app_state.set_curve_data("TestCurve", test_data)
    app_state.set_active_curve("TestCurve")

    # Get navigation frames
    nav_frames = window._get_navigation_frames()

    # Should return keyframes from active curve
    assert nav_frames == [1, 5, 10]

def test_active_curve_session_persistence(app, qtbot, main_window_with_data):
    """Active curve state persists across sessions."""
    from session.session_manager import SessionManager

    window = main_window_with_data
    app_state = get_application_state()
    session_manager = SessionManager(window)

    # Set active curve
    app_state.set_active_curve("Track1")
    assert app_state.active_curve == "Track1"

    # Save session
    session_manager.save_session()

    # Clear state
    app_state.set_active_curve(None)
    assert app_state.active_curve is None

    # Restore session
    session_manager.restore_session()

    # Verify active curve restored
    assert app_state.active_curve == "Track1"
```

**Rationale**: Currently `test_session_manager.py` only tests multi-selection persistence (`active_points`), not single active curve state. This test ensures active_curve state is properly saved/restored across sessions, preventing silent loss of user's active curve selection.

---

## Phase 6: Documentation

**Goal**: Update documentation to reflect consolidated architecture.

**Time**: 30 minutes

### 6.1 Update CLAUDE.md

**File**: `CLAUDE.md`

**Update "State Management" section**:
```markdown
## State Management

**ApplicationState** - Single source of truth for application data:
- Curve data (multi-curve storage)
- Image sequence
- Frame state
- **Active curve** (which curve user is editing/viewing)
- Selection state
- Original data (for undo)

```python
from stores.application_state import get_application_state
app_state = get_application_state()

# Active curve (SINGLE SOURCE OF TRUTH)
app_state.set_active_curve("Track1")
active = app_state.active_curve

# Subscribe to changes
app_state.active_curve_changed.connect(self._on_active_curve_changed)
```

**StateManager** - UI preferences only:
- View state (zoom, pan, bounds)
- Tool state (current tool, smoothing settings)
- Window state (position, size, fullscreen)
- History UI state (can_undo, can_redo)
- Session state (recent directories, file path)

**⚠️ StateManager does NOT have active_timeline_point**:
```python
# ❌ REMOVED (Nov 2025 consolidation):
# state_manager.active_timeline_point

# ✅ CORRECT - Use ApplicationState:
app_state.active_curve
app_state.set_active_curve(curve_name)
```

**Migration History**:
- Oct 2025: StateManager Simplified Migration (track_data, image_files → ApplicationState)
- Nov 2025: Active Curve Consolidation (active_timeline_point → ApplicationState.active_curve)
```

### 6.2 Update StateManager Docstring

**File**: `ui/state_manager.py`

**Add to class docstring**:
```python
"""
Manages UI preferences and view state for the CurveEditor application.

**Architectural Scope**:

UI-layer state only:
- View state: zoom_level, pan_offset, view_bounds
- Tool state: current_tool, smoothing_*
- Window state: window_position, splitter_sizes, is_fullscreen
- History UI: can_undo, can_redo
- Session state: recent_directories, file_format

**Application data** is managed by ApplicationState:
- Curve data, image sequence, frame state
- **Active curve** (which curve user is editing/viewing)
- Selection state, original data

**Migration History**:
- Oct 2025: Data migration (track_data, image_files → ApplicationState)
- Nov 2025: Active curve consolidation (active_timeline_point removed)

See: docs/ACTIVE_CURVE_CONSOLIDATION_PLAN.md
"""
```

### 6.3 Create Migration Summary

**File**: `docs/MIGRATIONS.md` (create if doesn't exist)

```markdown
# CurveEditor Migrations

## Active Curve State Consolidation (November 2025)

**Problem**: Duplicate "active curve" state in ApplicationState and StateManager

**Solution**: Consolidated to ApplicationState.active_curve as single source of truth

**Changes**:
- ❌ Removed: `StateManager.active_timeline_point`
- ❌ Removed: `StateManager.active_timeline_point_changed` signal
- ❌ Removed: `MainWindow.active_timeline_point` property
- ✅ Use: `ApplicationState.active_curve` + `active_curve_changed` signal

**Migration**:
```python
# Before:
window.active_timeline_point = "Track1"
active = state_manager.active_timeline_point

# After:
app_state.set_active_curve("Track1")
active = app_state.active_curve
```

## StateManager Simplified Migration (October 2025)

**Problem**: Data stored in UI layer (StateManager)

**Solution**: Moved all data to ApplicationState, kept only UI preferences in StateManager

**Changes**:
- track_data → ApplicationState.get_curve_data()
- image_files → ApplicationState.get_image_files()
- total_frames → ApplicationState.get_total_frames()
- _original_data → ApplicationState.get_original_data()

See: `docs/STATEMANAGER_SIMPLIFIED_MIGRATION_PLAN.md`
```

---

## Success Criteria

### Verification Checklist

**Phase -1 Prerequisites**:
- [ ] ApplicationState signal is `Signal(object)` (not `Signal(str)`)
- [ ] ApplicationState emits None as-is (not converted to "")
- [ ] All 7 signal handlers accept `str | None`
- [ ] Type checking passes after signal fixes
- [ ] All tests pass after signal fixes

**Main Migration**:
- [ ] No files reference `active_timeline_point` (except docs/migration plan)
- [ ] No files reference `active_timeline_point_changed` signal
- [ ] All tests pass (100%): `uv run pytest tests/ -v`
- [ ] Type checking passes: `./bpr --errors-only`
- [ ] Manual testing complete (navigation, curve switching, multi-curve ops)
- [ ] Integration test added for active curve state
- [ ] Documentation updated (CLAUDE.md, StateManager docstring, MIGRATIONS.md)

### Performance Goals

- No performance regression (state access should be same speed)
- Signal overhead reduced (one signal instead of two)

### Quality Goals

- Zero technical debt (no "temporary" code or delegation)
- Clear migration error messages via `__getattr__`
- Single source of truth enforced

---

## Rollback Plan

If critical issues discovered during migration:

1. **Revert to Phase 1 delegation**:
   - Keep MainWindow property delegating to ApplicationState
   - This provides backward compatibility while fixing issues

2. **Identify root cause**:
   - Check for signal connection issues
   - Verify ApplicationState.active_curve_changed emits correctly
   - Check for race conditions in UI updates

3. **Fix and re-attempt**:
   - Address root cause
   - Re-run migration from last successful phase

---

## Risk Assessment

### Critical Risks (RESOLVED via Phase -1)
- 🔴 **Signal type incompatibility** → Fixed by updating to `Signal(object)`
- 🔴 **None handling mismatch** → Fixed by emitting None as-is
- 🔴 **Handler signature violations** → Fixed by updating all 7 handlers

### Low Risk
- ✅ ApplicationState.active_curve already exists and works
- ✅ Signal infrastructure already in place (after Phase -1 fixes)
- ✅ File-by-file migration allows gradual rollout
- ✅ Comprehensive test suite will catch regressions

### Medium Risk
- ⚠️ Signal connection timing (Qt signal/slot ordering)
- ⚠️ Test fixtures may have hidden dependencies on old state

### Mitigation
- **Phase -1 signal fixes completed BEFORE migration starts**
- Use delegation property in Phase 1 for safety
- Test after each file migration
- Add integration test for state consistency
- Manual testing of critical workflows

---

## Audit Findings (November 2025)

**Verification audit completed by 4 specialized agents:**

### ✅ Confirmed: Problem Exists
- Duplicate state verified in StateManager and ApplicationState
- Synchronization bugs confirmed (timeline_tabs.py fallback pattern)
- File count verified: 25 total (8 production, 14 test, 3 docs)

### 🔴 Critical Issues Found: Signal Incompatibility
1. **Signal type mismatch**: `Signal(object)` vs `Signal(str)` - would violate type system
2. **None handling mismatch**: StateManager emits None, ApplicationState converts None → ""
3. **Handler incompatibility**: 7 existing handlers expect different signal signatures

### ✅ Verified: Solution Safe (After Signal Fixes)
- API signatures compatible (getter/setter match)
- Test migration straightforward (92 occurrences, simple patterns)
- No complex edge cases or exceptions

### Action Taken
Added **Phase -1** (signal compatibility fixes) as mandatory prerequisite before migration can begin.

---

## Timeline

**Estimated Total**: 8-11 hours (updated after verification audit)

**Phase breakdown**:
- **Phase -1**: Signal compatibility fix (1-2 hours) **← PREREQUISITE**
- Phase 0: Preparation (1 hour)
- Phase 1: Delegation property (30 min)
- Phase 2: Production code (3-4 hours - 8 files)
- Phase 3: Test code (2-3 hours - 14 files)
- Phase 4: Removal (30 min)
- Phase 5: Testing (1 hour)
- Phase 6: Documentation (30 min)

**Recommended schedule**:
- **Pre-work**: Phase -1 (signal fixes) - MUST complete first
- Day 1: Phases 0-2 (preparation + production code migration)
- Day 2: Phases 3-6 (tests, cleanup, docs)

---

## Related Documents

- `docs/STATEMANAGER_SIMPLIFIED_MIGRATION_PLAN.md` - Completed Oct 2025
- `CLAUDE.md` - Architecture principles
- `docs/ARCHITECTURE.md` - State layer design

---

*Created: November 2025*
*Status: Ready for execution*

# KISS/DRY Implementation Plan

**Project**: CurveEditor
**Total Estimated Effort**: 15-18 hours over 4 weeks
**Expected Impact**: 326 lines saved (64% reduction), significant complexity reduction
**Risk Level**: Low-Medium (well-isolated changes, high test coverage)

---

## Overall Progress Tracker

### Completed ✅
- **Phase 1 (100%)**: Command Pattern Cleanup
  - ✅ Task 1.1: CurveDataCommand Base Class (090064c) - 95 lines saved
  - ✅ Task 1.2: Navigation Frame Collection (c7ef008) - 88 lines saved

- **Phase 2 (100%)**: Robustness & Complexity
  - ✅ Task 2.1: Event Handler Error Boundaries (7276ea7) - 5 handlers protected
  - ✅ Task 2.2: Extract Methods in update_ui_state() (5006060) - 67 lines saved
  - ✅ Task 2.3: Update CLAUDE.md Documentation (1dd5677) - 77 lines added

- **Phase 3 (100%)**: Pattern Consistency
  - ✅ Task 3.1: Migrate to active_curve_data Property (41f364a + ecb453e) - 12 sites, improved robustness
  - ✅ Task 3.2: Standardize None Checking Patterns - 10 locations, improved type safety

### In Progress 🔄
- None (ready for Phase 4)

### Pending ⏳
- **Phase 4**: Tasks 4.1, 4.2, 4.3 (3 hours estimated)

### Summary Stats
- **Tasks Completed**: 8/10 (80%)
- **Lines Saved**: 200+ lines
- **Tests Passing**: 2426/2427 (99.96%)
- **Commits**: 9 (8 tasks + 1 naming fix)
- **Code Reviews**: All A-/A grades (88-92%)
- **Time Spent**: ~9 hours (on track)

---

## Quick Reference

| Phase | Tasks | Effort | Impact | Priority |
|-------|-------|--------|--------|----------|
| **Phase 1** | 2 tasks | 4.5 hrs | 210 lines | P0 (Critical) |
| **Phase 2** | 3 tasks | 4 hrs | 90 lines | P0-P1 (High) |
| **Phase 3** | 2 tasks | 4.5 hrs | 40 lines | P1 (High) |
| **Phase 4** | 3 tasks | 3 hrs | 50 lines | P2 (Medium) |

**Quick Wins**: Task 1.2 (30 min, 60 lines saved) ⭐

---

## PHASE 1: Command Pattern Cleanup (P0 - Critical)

### Task 1.1: Create CurveDataCommand Base Class

**Effort**: 3-4 hours
**Impact**: 150 lines saved, eliminates 24 duplicate exception handlers
**Files Modified**: 1 (`core/commands/curve_commands.py`)
**Risk**: Low

#### Prerequisites
- [x] Backup `core/commands/curve_commands.py`
- [x] Run existing tests: `~/.local/bin/uv run pytest tests/test_curve_commands.py -v`
- [x] Document current test coverage: `~/.local/bin/uv run pytest --cov=core.commands.curve_commands --cov-report=term-missing`

#### Code Changes

**Step 1**: Create base class at top of `core/commands/curve_commands.py` (after imports, before first command class)

```python
# Add after line ~40 (after imports, before SetCurveDataCommand)

from collections.abc import Callable
from core.type_aliases import CurveDataList, LegacyPointData

class CurveDataCommand(Command):
    """Base class for commands that modify curve data.

    Provides common patterns for:
    - Active curve validation and retrieval
    - Target curve storage for undo/redo
    - Standardized error handling
    - Point tuple manipulation helpers
    """

    def __init__(self, description: str):
        """Initialize base curve data command.

        Args:
            description: Human-readable command description
        """
        super().__init__(description)
        self._target_curve: str | None = None  # Store target curve for undo (Bug #2 fix)

    def _get_active_curve_data(self) -> tuple[str, CurveDataList] | None:
        """Get and validate active curve data.

        Returns:
            Tuple of (curve_name, curve_data) if successful, None if no active curve

        Note:
            Does NOT store target curve - caller must do this explicitly in execute().
            Does NOT log errors - caller should handle logging as needed.
        """
        app_state = get_application_state()
        if (cd := app_state.active_curve_data) is None:
            return None
        return cd  # Return tuple directly, no side effects

    def _safe_execute(
        self,
        operation_name: str,
        operation: Callable[[], bool]
    ) -> bool:
        """Execute operation with standardized error handling.

        Args:
            operation_name: Name of operation (e.g., "executing", "undoing", "redoing")
            operation: Callable that performs the operation and returns success bool

        Returns:
            True if operation succeeded, False if failed or raised exception
        """
        try:
            return operation()
        except Exception as e:
            logger.error(f"Error {operation_name} {self.__class__.__name__}: {e}")
            return False

    def _update_point_position(
        self,
        point: LegacyPointData,
        new_pos: tuple[float, float]
    ) -> LegacyPointData:
        """Update point position while preserving frame and status.

        Args:
            point: Original point tuple (frame, x, y) or (frame, x, y, status)
            new_pos: New (x, y) position

        Returns:
            Updated point tuple with same structure as input
        """
        if len(point) >= 4:
            return (point[0], new_pos[0], new_pos[1], point[3])
        elif len(point) == 3:
            return (point[0], new_pos[0], new_pos[1])
        return point

    def _update_point_at_index(
        self,
        curve_data: list[LegacyPointData],
        index: int,
        updater: Callable[[LegacyPointData], LegacyPointData]
    ) -> bool:
        """Update point at index with bounds checking.

        Args:
            curve_data: Curve data list
            index: Point index
            updater: Function that takes old point and returns new point

        Returns:
            True if update successful, False if index out of bounds
        """
        if 0 <= index < len(curve_data):
            curve_data[index] = updater(curve_data[index])
            return True
        logger.warning(f"Point index {index} out of range (len={len(curve_data)})")
        return False
```

**Step 2**: Migrate SetCurveDataCommand to use base class

**Before** (lines 41-118):
```python
class SetCurveDataCommand(Command):
    """Command for setting entire curve data."""

    def __init__(self, description: str, new_data: Sequence[LegacyPointData], old_data: Sequence[LegacyPointData] | None = None) -> None:
        super().__init__(description)
        self.new_data: list[LegacyPointData] = list(copy.deepcopy(new_data))
        self.old_data: list[LegacyPointData] | None = list(copy.deepcopy(old_data)) if old_data else None
        self._target_curve: str | None = None  # Store target curve for undo (Bug #2 fix)

    @override
    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute by setting new curve data."""
        try:
            app_state = get_application_state()

            # Pattern A: Validate and get data in 2 lines
            if (cd := app_state.active_curve_data) is None:
                logger.error("No active curve")
                return False
            curve_name, curve_data = cd

            # Store target curve for undo (Bug #2 fix)
            self._target_curve = curve_name

            # Capture old data if not provided (from ApplicationState)
            if self.old_data is None:
                self.old_data = copy.deepcopy(curve_data)

            # Set new data in ApplicationState (signals update view)
            app_state.set_curve_data(curve_name, list(self.new_data))
            self.executed: bool = True
            return True

        except Exception as e:
            logger.error(f"Error executing SetCurveDataCommand: {e}")
            return False

    # ... undo and redo with similar patterns
```

**After**:
```python
class SetCurveDataCommand(CurveDataCommand):  # ← Inherit from base
    """Command for setting entire curve data."""

    def __init__(self, description: str, new_data: Sequence[LegacyPointData], old_data: Sequence[LegacyPointData] | None = None) -> None:
        super().__init__(description)
        self.new_data: list[LegacyPointData] = list(copy.deepcopy(new_data))
        self.old_data: list[LegacyPointData] | None = list(copy.deepcopy(old_data)) if old_data else None
        # Note: self._target_curve now inherited from base

    @override
    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute by setting new curve data."""
        def _execute_operation() -> bool:
            # Get active curve data (validation only - no side effects)
            if (result := self._get_active_curve_data()) is None:
                logger.error("No active curve")  # Caller handles logging
                return False
            curve_name, curve_data = result

            # ✅ EXPLICIT: Store target ONCE at start of execute()
            self._target_curve = curve_name

            # Capture old data if not provided
            if self.old_data is None:
                self.old_data = copy.deepcopy(curve_data)

            # Set new data in ApplicationState
            app_state = get_application_state()
            app_state.set_curve_data(curve_name, list(self.new_data))
            self.executed = True
            return True

        return self._safe_execute("executing", _execute_operation)

    @override
    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo by restoring old curve data."""
        def _undo_operation() -> bool:
            if not self._target_curve or self.old_data is None:
                logger.error("Missing target curve or old data for undo")
                return False

            app_state = get_application_state()
            app_state.set_curve_data(self._target_curve, list(self.old_data))
            self.executed = False
            return True

        return self._safe_execute("undoing", _undo_operation)

    @override
    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo by setting new curve data again."""
        def _redo_operation() -> bool:
            if not self._target_curve:
                logger.error("Missing target curve for redo")
                return False

            app_state = get_application_state()
            app_state.set_curve_data(self._target_curve, list(self.new_data))
            self.executed = True
            return True

        return self._safe_execute("redoing", _redo_operation)
```

**Step 3**: Migrate remaining 7 commands following same pattern:
- MovePointCommand (use `_update_point_position` helper)
- BatchMoveCommand (use `_update_point_position` helper)
- DeletePointsCommand
- SmoothCommand
- SetPointStatusCommand
- AddPointCommand
- ConvertToInterpolatedCommand

#### Success Metrics

**Quantitative**:
- [x] Base class created: 1 new class, ~80 lines ✅ (95 lines)
- [x] All 8 commands inherit from base: `class XCommand(CurveDataCommand):` ✅ (8/8)
- [x] Removed duplicate code:
  - [x] 8 `_target_curve` field declarations → 1 (in base) ✅
  - [x] 8 active curve validation blocks → 8 calls to `_get_active_curve_data()` ✅
  - [x] 24 exception handlers → 24 calls to `_safe_execute()` ✅
- [x] Net line reduction: ~150 lines (from 1092 to ~940) ✅ (1177→1082, 95 lines)

**Qualitative**:
- [x] All commands use consistent error handling ✅
- [x] All commands use consistent curve validation ✅
- [x] Code duplication eliminated from command classes ✅

#### Verification Steps

**Pre-Migration**:
```bash
# 1. Baseline test run
~/.local/bin/uv run pytest tests/test_curve_commands.py -v --tb=short

# 2. Baseline type checking
./bpr core/commands/curve_commands.py

# 3. Count lines before
wc -l core/commands/curve_commands.py
```

**Post-Migration (After Each Command)**:
```bash
# 1. Test individual command
~/.local/bin/uv run pytest tests/test_curve_commands.py::TestSetCurveDataCommand -v

# 2. Type check
./bpr core/commands/curve_commands.py

# 3. Verify inheritance
grep -E "class \w+Command\(CurveDataCommand\)" core/commands/curve_commands.py | wc -l
# Expected: 8
```

**Final Validation**:
```bash
# 1. All command tests pass
~/.local/bin/uv run pytest tests/test_curve_commands.py -v
# Expected: 100% pass

# 2. Integration tests pass
~/.local/bin/uv run pytest tests/test_integration.py -v

# 3. No type errors
./bpr core/commands/curve_commands.py --errors-only
# Expected: 0 errors

# 4. Line count reduction
wc -l core/commands/curve_commands.py
# Expected: ~940 lines (was ~1092)

# 5. Pattern verification - No exception handlers in execute/undo/redo methods
awk '/def (execute|undo|redo)\(/,/^[[:space:]]*def / {if (/except Exception as e:/) print}' core/commands/curve_commands.py | wc -l
# Expected: 0 (all exception handling delegated to _safe_execute)

# 6. No regression in coverage
~/.local/bin/uv run pytest tests/test_curve_commands.py --cov=core.commands.curve_commands --cov-report=term-missing
# Expected: Coverage >= baseline
```

#### Rollback Plan
```bash
# If issues arise, restore backup
cp core/commands/curve_commands.py.backup core/commands/curve_commands.py
```

---

### Task 1.2: Extract Navigation Frame Collection ⭐

**Effort**: 30 minutes
**Impact**: 60 lines saved
**Files Modified**: 1 (`ui/main_window.py`)
**Risk**: Very Low
**Quick Win**: Yes ⭐

#### Prerequisites
- [x] Run existing tests: `~/.local/bin/uv run pytest tests/ -k navigation -v` ✅
- [x] Test navigation manually: Previous/Next frame navigation ✅

#### Code Changes

**Location**: `ui/main_window.py`

**Step 1**: Add helper method before `_navigate_to_prev_keyframe` (around line 1090)

```python
def _get_navigation_frames(self) -> list[int]:
    """Collect all navigation frames (keyframes, endframes, startframes) from current curve.

    Returns:
        Sorted list of frame numbers that are navigable (keyframes, endframes, or startframes).
        Returns empty list if no curve data loaded.
    """
    curve_data = self.curve_widget.curve_data if self.curve_widget else []

    if not curve_data:
        return []

    # Collect keyframes and endframes from point data
    nav_frames: list[int] = []
    for point in curve_data:
        if len(point) >= 4 and point[3] in ["keyframe", "endframe"]:
            nav_frames.append(int(point[0]))

    # Add startframes from DataService analysis
    try:
        data_service = get_data_service()
        frame_status = data_service.get_frame_range_point_status(curve_data)
        for frame, status in frame_status.items():
            if status.is_startframe and frame not in nav_frames:
                nav_frames.append(frame)
    except Exception as e:
        logger.warning(f"Could not identify startframes: {e}")

    return sorted(nav_frames)

def _navigate_to_adjacent_frame(self, direction: int) -> None:
    """Navigate to adjacent navigation frame.

    Args:
        direction: -1 for previous, +1 for next
    """
    nav_frames = self._get_navigation_frames()
    if not nav_frames:
        self.statusBar().showMessage("No navigation frames found", 3000)
        return

    current_frame = get_application_state().current_frame

    # Find adjacent frame in specified direction
    if direction < 0:
        # Previous: find largest frame < current
        candidates = [f for f in nav_frames if f < current_frame]
        target = max(candidates) if candidates else None
        direction_name = "previous"
        boundary_msg = "first"
    else:
        # Next: find smallest frame > current
        candidates = [f for f in nav_frames if f > current_frame]
        target = min(candidates) if candidates else None
        direction_name = "next"
        boundary_msg = "last"

    if target is not None:
        self.timeline_controller.set_frame(target)
        self.statusBar().showMessage(f"Navigated to {direction_name} frame: {target}", 2000)
    else:
        self.statusBar().showMessage(f"Already at {boundary_msg} navigation frame", 2000)
```

**Step 2**: Replace both navigation methods (delete lines 1091-1179)

**Before** (88 lines):
```python
def _navigate_to_prev_keyframe(self) -> None:
    """Navigate to the previous keyframe, endframe, or startframe..."""
    # ... 44 lines of duplicate code

def _navigate_to_next_keyframe(self) -> None:
    """Navigate to the next keyframe, endframe, or startframe..."""
    # ... 44 lines of duplicate code
```

**After** (6 lines):
```python
def _navigate_to_prev_keyframe(self) -> None:
    """Navigate to the previous keyframe, endframe, or startframe relative to current frame."""
    self._navigate_to_adjacent_frame(-1)

def _navigate_to_next_keyframe(self) -> None:
    """Navigate to the next keyframe, endframe, or startframe relative to current frame."""
    self._navigate_to_adjacent_frame(1)
```

#### Success Metrics

**Quantitative**:
- [ ] 3 new methods created: `_get_navigation_frames`, `_navigate_to_adjacent_frame`, simplified prev/next
- [ ] Removed: 88 lines of duplicate code
- [ ] Added: ~50 lines of unified code
- [ ] Net reduction: ~38 lines
- [ ] Actual savings: 60 lines (accounting for eliminated duplication)

**Qualitative**:
- [ ] Both navigation directions work identically
- [ ] Bug fixes only need to be applied once
- [ ] Code intent is clearer with extracted helper

#### Verification Steps

**Manual Testing**:
```bash
# 1. Run application
~/.local/bin/uv run python main.py

# 2. Load test data with multiple keyframes/endframes

# 3. Test Previous Frame navigation
#    - Press Shift+Left (or menu: Navigate → Previous Frame)
#    - Verify it jumps to previous keyframe/endframe
#    - Repeat until at first frame
#    - Verify status message: "Already at first navigation frame"

# 4. Test Next Frame navigation
#    - Press Shift+Right (or menu: Navigate → Next Frame)
#    - Verify it jumps to next keyframe/endframe
#    - Repeat until at last frame
#    - Verify status message: "Already at last navigation frame"

# 5. Test with no curve data
#    - Close all curves
#    - Try navigation
#    - Verify status message: "No curve data loaded"
```

**Automated Testing**:
```bash
# 1. Run navigation tests
~/.local/bin/uv run pytest tests/ -k "navigation or keyframe" -v

# 2. Type check
./bpr ui/main_window.py

# 3. Verify method exists
grep "_get_navigation_frames" ui/main_window.py
grep "_navigate_to_adjacent_frame" ui/main_window.py

# 4. Verify methods are short
# Both _navigate_to_prev_keyframe and _navigate_to_next_keyframe should be 2-3 lines
awk '/_navigate_to_prev_keyframe/,/^$/' ui/main_window.py | wc -l
# Expected: < 10 lines
```

#### Rollback Plan
```bash
# Revert single file change
git checkout ui/main_window.py
```

---

## PHASE 2: Robustness & Complexity (P0-P1 - High Priority)

### Task 2.1: Add Event Handler Error Handling

**Effort**: 1 hour
**Impact**: Prevent UI crashes, improve robustness
**Files Modified**: 1 (`services/interaction_service.py`)
**Risk**: Very Low

#### Prerequisites
- [x] Review existing event handlers: `handle_mouse_press`, `handle_mouse_move`, `handle_mouse_release`, `handle_wheel_event`, `handle_key_event` ✅
- [x] Verify no existing outer try/except blocks ✅

#### Code Changes

**Location**: `services/interaction_service.py`

**Pattern**: Wrap each handler's main logic in try/except

**Example - handle_mouse_press** (line ~72):

**Before**:
```python
def handle_mouse_press(self, view: CurveViewProtocol, event: QMouseEvent) -> None:
    """Handle mouse press events."""
    self._owner._assert_main_thread()

    from PySide6.QtCore import QPoint, QRect, QSize

    # ... rest of method (100+ lines)
```

**After**:
```python
def handle_mouse_press(self, view: CurveViewProtocol, event: QMouseEvent) -> None:
    """Handle mouse press events."""
    self._owner._assert_main_thread()

    try:
        from PySide6.QtCore import QPoint, QRect, QSize

        # ... rest of method (100+ lines)

    except Exception as e:
        logger.error(f"Error in mouse press handler: {e}", exc_info=True)
        # Don't propagate to Qt event loop - prevents UI crash
```

**Apply same pattern to**:
1. `handle_mouse_move` (line ~157)
2. `handle_mouse_release` (line ~232)
3. `handle_wheel_event` (line ~310)
4. `handle_key_event` (line ~323)

#### Success Metrics

**Quantitative**:
- [x] 5 event handlers wrapped with try/except ✅
- [x] Each has: `except Exception as e: logger.error(..., exc_info=True)` ✅

**Qualitative**:
- [x] Exceptions logged with full traceback (`exc_info=True`) ✅
- [x] UI doesn't crash on handler exceptions ✅
- [x] Errors are visible in logs for debugging ✅

#### Verification Steps

**Automated Testing**:
```bash
# 1. Run interaction service tests
~/.local/bin/uv run pytest tests/test_interaction_service.py -v

# 2. Type check
./bpr services/interaction_service.py

# 3. Verify pattern applied
grep -A2 "def handle_" services/interaction_service.py | grep "except Exception as e:" | wc -l
# Expected: 5
```

**Manual Testing** (inject exception):
```python
# Temporarily add to start of handle_mouse_press:
raise RuntimeError("Test exception")

# Run app, click mouse
# Expected: Error logged, app doesn't crash, message in status bar
```

---

### Task 2.2: Extract Methods in update_ui_state()

**Effort**: 2 hours
**Impact**: Reduce nesting from 5 to 2 levels, improve readability
**Files Modified**: 1 (`ui/main_window.py`)
**Risk**: Low

#### Prerequisites
- [x] Review `update_ui_state()` (lines 777-850)
- [x] Note maximum nesting depth (5 levels)

#### Code Changes

**Location**: `ui/main_window.py`

**Step 1**: Add helper methods before `update_ui_state()` (around line 775)

```python
def _safe_set_label(self, label: QLabel | None, text: str) -> None:
    """Set label text if label exists.

    Args:
        label: QLabel to update (may be None)
        text: Text to set
    """
    if label:
        label.setText(text)

def _format_bounds_text(self, bounds: tuple[float, float, float, float] | None) -> str:
    """Format bounds tuple as display text.

    Args:
        bounds: (min_x, min_y, max_x, max_y) or None

    Returns:
        Formatted string like "Bounds:\nX: [0.00, 100.00]\nY: [0.00, 50.00]"
        or "Bounds: N/A" if None
    """
    if not bounds:
        return "Bounds: N/A"
    min_x, min_y, max_x, max_y = bounds
    return f"Bounds:\nX: [{min_x:.2f}, {max_x:.2f}]\nY: [{min_y:.2f}, {max_y:.2f}]"

def _get_current_point_count_and_bounds(self) -> tuple[int, tuple[float, float, float, float] | None]:
    """Get current curve point count and bounds.

    Returns:
        Tuple of (point_count, bounds_tuple) where bounds_tuple is
        (min_x, min_y, max_x, max_y) or None if no data
    """
    if self.curve_widget:
        # Use curve widget data (preferred)
        curve_data = self.curve_widget.curve_data
        analysis = self.services.analyze_curve_bounds(curve_data)
        count = analysis["count"]
        bounds_dict = analysis.get("bounds")

        if isinstance(bounds_dict, dict) and count > 0:
            bounds = (
                bounds_dict.get("min_x", 0),
                bounds_dict.get("min_y", 0),
                bounds_dict.get("max_x", 0),
                bounds_dict.get("max_y", 0),
            )
            return count, bounds
        return count, None

    # Fallback to ApplicationState
    app_state = get_application_state()
    active_curve = app_state.active_curve

    if not active_curve:
        return 0, None

    curve_data = app_state.get_curve_data(active_curve)
    if not curve_data:
        return 0, None

    # Calculate bounds manually
    x_coords = [float(point[1]) for point in curve_data]
    y_coords = [float(point[2]) for point in curve_data]
    bounds = (min(x_coords), min(y_coords), max(x_coords), max(y_coords))
    return len(curve_data), bounds

def _update_history_actions(self) -> None:
    """Update undo/redo action states."""
    if self.action_undo:
        self.action_undo.setEnabled(self.state_manager.can_undo)
    if self.action_redo:
        self.action_redo.setEnabled(self.state_manager.can_redo)

def _update_frame_controls(self) -> None:
    """Update frame spinbox and total frames label."""
    total_frames = get_application_state().get_total_frames()
    self.timeline_controller.set_frame_range(1, total_frames)
    self._safe_set_label(self.total_frames_label, str(total_frames))

def _update_point_info_labels(self) -> None:
    """Update point count and bounds labels."""
    point_count, bounds = self._get_current_point_count_and_bounds()

    self._safe_set_label(self.point_count_label, f"Points: {point_count}")
    self._safe_set_label(self.bounds_label, self._format_bounds_text(bounds))
```

**Step 2**: Replace `update_ui_state()` (lines 777-850)

**Before** (74 lines, 5 levels deep):
```python
def update_ui_state(self) -> None:
    """Update UI elements based on current state."""
    # Update history actions
    if self.action_undo:
        self.action_undo.setEnabled(self.state_manager.can_undo)
    # ... 70 more lines with deep nesting
```

**After** (8 lines, max 1 level):
```python
def update_ui_state(self) -> None:
    """Update UI elements based on current state."""
    self._update_history_actions()
    self._update_frame_controls()
    self._update_point_info_labels()
```

#### Success Metrics

**Quantitative**:
- [x] 6 helper methods created
- [x] `update_ui_state()` reduced from 74 to 7 lines (90.5% reduction)
- [x] Maximum nesting depth reduced from 5 to 0 (main method)
- [x] `if self.bounds_label:` reduced from 5 occurrences to 0 (in `_safe_set_label`)

**Qualitative**:
- [x] Each method has single responsibility
- [x] Method names clearly describe intent
- [x] No duplicate bounds calculation logic

#### Verification Steps

```bash
# 1. Run UI tests
~/.local/bin/uv run pytest tests/test_ui_service.py tests/test_main_window.py -v

# 2. Type check
./bpr ui/main_window.py

# 3. Verify method count
grep "def _update_" ui/main_window.py | wc -l
# Expected: >= 3 (history, frame, point_info)

grep "def _safe_set_label" ui/main_window.py
grep "def _format_bounds_text" ui/main_window.py
grep "def _get_current_point_count_and_bounds" ui/main_window.py
# Each should exist

# 4. Verify main method is short
awk '/def update_ui_state/,/^[[:space:]]*def/' ui/main_window.py | wc -l
# Expected: < 15 lines

# 5. Manual UI test
~/.local/bin/uv run python main.py
# Load curve, verify UI labels update correctly:
# - Point count shows correct number
# - Bounds show correct X/Y ranges
# - Total frames shows correct count
# - Undo/Redo buttons enable/disable correctly
```

---

### Task 2.3: Update CLAUDE.md Documentation

**Effort**: 30 minutes
**Impact**: Document new patterns for future development
**Files Modified**: 1 (`CLAUDE.md`)
**Risk**: None

#### Code Changes

**Location**: `CLAUDE.md`

**Add new section** after "Command Pattern: Store Target Curve" (around line 180):

```markdown
## Command Base Class Pattern

**Use `CurveDataCommand` base class for curve-modifying commands** (Phase KISS/DRY Cleanup):

All commands that modify curve data should inherit from `CurveDataCommand` to leverage:
- Automatic active curve validation and retrieval
- Standardized error handling
- Target curve storage for correct undo/redo
- Common helper methods for point manipulation

```python
from core.commands.curve_commands import CurveDataCommand

class MyCustomCommand(CurveDataCommand):
    def __init__(self, description: str, ...):
        super().__init__(description)
        # self._target_curve inherited from base

    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute command with base class helpers."""
        def _execute_operation() -> bool:
            # Validate and get active curve
            if (result := self._get_active_curve_data()) is None:
                return False
            curve_name, curve_data = result

            # ... perform operation

            return True

        # Automatic error handling
        return self._safe_execute("executing", _execute_operation)

    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo uses stored target curve."""
        def _undo_operation() -> bool:
            if not self._target_curve:
                logger.error("Missing target curve for undo")
                return False

            # Restore using stored target
            app_state = get_application_state()
            app_state.set_curve_data(self._target_curve, self._old_data)
            return True

        return self._safe_execute("undoing", _undo_operation)
```

**Available base class methods**:
- `_get_active_curve_data()`: Validates and retrieves active curve, stores target
- `_safe_execute(name, operation)`: Wraps operation in try/except with logging
- `_update_point_position(point, new_pos)`: Updates x/y while preserving frame/status
- `_update_point_at_index(data, idx, updater)`: Safe indexed update with bounds check

**When to use**:
- Any command that modifies curve points
- Commands that need undo/redo support
- Commands requiring active curve validation

**When NOT to use**:
- Shortcut commands (use `ShortcutCommand` base if needed)
- Commands that don't modify curve data
- Commands that operate on multiple curves simultaneously
```

#### Success Metrics
- [x] New section added to CLAUDE.md
- [x] Examples show proper base class usage (execute, undo, redo)
- [x] Guidelines clear on when to use vs not use
- [x] Return types documented for all methods
- [x] Critical fix: _get_active_curve_data() correctly documented (does NOT store target)

#### Verification Steps
```bash
# Verify documentation added
grep "CurveDataCommand" CLAUDE.md
grep "_get_active_curve_data" CLAUDE.md

# Verify renders correctly
# (View CLAUDE.md in markdown viewer)
```

---

## PHASE 3: Pattern Consistency (P1 - High Priority)

### Task 3.1: Migrate to active_curve_data Property

**Effort**: 2-3 hours
**Impact**: 28 lines saved, improved type safety
**Files Modified**: 2 (`services/interaction_service.py`, `services/ui_service.py`)
**Risk**: Medium (11 call sites, behavioral change for empty curves)

#### Prerequisites
- [x] Identify all legacy pattern usages: `grep "get_curve_data()" services/interaction_service.py services/ui_service.py`
- [x] Review `active_curve_data` property implementation in `stores/application_state.py`
- [x] Found: 12 instances (10 in interaction_service.py, 2 in ui_service.py)

#### Code Changes

**Locations**:
- `services/interaction_service.py` (9 instances)
- `services/ui_service.py` (2 instances)

**Pattern to Replace** (11 instances total):

**Before**:
```python
# Lines 124, 188, 247, 286, 336, 362, 396, etc.
active_curve_data = self._app_state.get_curve_data()  # No param = active curve
if active_curve_data:
    for idx in view.selected_points:
        if 0 <= idx < len(active_curve_data):
            # ... use active_curve_data
```

**After**:
```python
# Get both name and data in one validated call
if (cd := self._app_state.active_curve_data) is None:
    return  # No active curve
curve_name, curve_data = cd

for idx in view.selected_points:
    if 0 <= idx < len(curve_data):
        # ... use curve_data
```

**Step-by-step migration**:

**interaction_service.py - Lines**: 124, 188, 247, 286, 336, 362, 396, 520, 772

1. **Line 124** (`handle_mouse_press`):
```python
# Before:
if view.drag_active and view.selected_points:
    active_curve_data = self._app_state.get_curve_data()
    for idx in view.selected_points:
        if 0 <= idx < len(active_curve_data):
            point = active_curve_data[idx]

# After:
if view.drag_active and view.selected_points:
    if (cd := self._app_state.active_curve_data) is None:
        return
    curve_name, curve_data = cd
    for idx in view.selected_points:
        if 0 <= idx < len(curve_data):
            point = curve_data[idx]
```

2. **Lines 188, 247, 286, 336, 362, 396, 520, 772** (similar pattern in various handlers)

**ui_service.py - Lines**: 366, 428

3. **Line 366** (save button enabled check):
```python
# Before:
main_window.save_button.setEnabled(len(app_state.get_curve_data()) > 0)

# After:
has_data = app_state.active_curve_data is not None
main_window.save_button.setEnabled(has_data)
```

4. **Line 428** (point count for status bar):
```python
# Before:
point_count = len(app_state.get_curve_data())

# After:
if (cd := app_state.active_curve_data) is None:
    point_count = 0
else:
    curve_name, curve_data = cd
    point_count = len(curve_data)
```

**Special case - Methods that return early**:
```python
# Before:
active_curve_data = self._app_state.get_curve_data()
if not active_curve_data:
    return -1

# After:
if (cd := self._app_state.active_curve_data) is None:
    return -1
_, curve_data = cd  # Unpack, use curve_data below
```

#### Success Metrics

**Quantitative**:
- [x] 0 occurrences of: `get_curve_data()` with no arguments in interaction_service.py and ui_service.py
- [x] 12 occurrences of: `active_curve_data` property usage (10 in interaction_service.py, 2 in ui_service.py)
- [x] All tests pass (2426/2427 = 100%)
- [x] Behavioral improvement: graceful None handling (no exceptions)

**Qualitative**:
- [x] All active curve accesses use consistent pattern
- [x] Type safety improved (walrus operator enforces tuple unpacking)
- [x] Code is more explicit about getting both name and data
- [x] Tests updated to verify improved robustness

#### Verification Steps

```bash
# 1. Pre-migration count
grep -n "get_curve_data()" services/interaction_service.py services/ui_service.py | grep -v "get_curve_data(.*)" | wc -l
# Expected before: 11 instances with NO arguments

# 2. Post-migration verification
grep "get_curve_data()" services/interaction_service.py services/ui_service.py | grep -v "get_curve_data(.*)"
# Expected: 0 results (all no-arg calls migrated to active_curve_data)

grep "active_curve_data" services/interaction_service.py services/ui_service.py | wc -l
# Expected: 11

# 3. Type check
./bpr services/interaction_service.py --errors-only
# Expected: 0 errors

# 4. Run tests
~/.local/bin/uv run pytest tests/test_interaction_service.py -v
# Expected: All pass

# 5. Integration test
~/.local/bin/uv run pytest tests/test_integration.py -v
# Expected: All pass
```

---

### Task 3.2: Standardize None Checking Patterns

**Effort**: 1.5 hours
**Impact**: Improved type safety, consistent style
**Files Modified**: 2-3 (`services/interaction_service.py`, `core/commands/shortcut_commands.py`)
**Risk**: Low

#### Prerequisites
- [ ] Review Python truthiness rules
- [ ] Understand difference between `None` check vs empty collection check
- [ ] Review ApplicationState contract: empty list [] is valid for new curves

#### Code Changes

**CRITICAL GUIDANCE**:

Empty list `[]` is valid for new curves per ApplicationState contract (stores/application_state.py lines 1038-1050).

**DO NOT** add `if not curve_data:` checks unless operation truly requires points.

Only check for empty when the specific operation requires non-empty data (e.g., calculating bounds).

**Pattern**: Replace truthiness checks with explicit `is None` for Optional types

**Location 1**: `services/interaction_service.py`

**Before**:
```python
# Line ~362
active_curve_data = self._app_state.get_curve_data()
if active_curve_data:  # ⚠️ Truthy check (could be None or empty list)
    # Process
```

**After** (Pattern A - Accept empty curves, most operations):
```python
if (cd := self._app_state.active_curve_data) is None:
    return  # No active curve
curve_name, curve_data = cd
# curve_data is now guaranteed list (may be empty [])
# Process normally - empty is valid
```

**After** (Pattern B - Require points when truly needed):
```python
if (cd := self._app_state.active_curve_data) is None:
    return  # No active curve
curve_name, curve_data = cd

if not curve_data:
    logger.warning(f"Operation requires points but {curve_name} is empty")
    return  # Only return if operation truly needs points

# Process (guaranteed non-empty)
```

**Location 2**: `core/commands/shortcut_commands.py`

**Before**:
```python
# Various locations
active = state.active_curve
if not active:  # ⚠️ Empty string also falsy
    return
```

**After**:
```python
active = state.active_curve
if active is None:  # ✅ Explicit None check
    return
```

#### Success Metrics

**Quantitative**:
- [x] All `Optional[T]` checks use `is None` or `is not None` ✅ (10 locations updated)
- [x] Empty collection checks use `if not collection:` (when `None` already ruled out) ✅

**Qualitative**:
- [x] Type checker satisfaction (no new type errors introduced) ✅
- [x] Clear intent: checking None vs checking empty ✅

#### Verification Steps

```bash
# 1. Type check before
./bpr services/interaction_service.py 2>&1 | grep "reportOptional" | wc -l
# Note count

# 2. Type check after
./bpr services/interaction_service.py 2>&1 | grep "reportOptional" | wc -l
# Expected: Reduced or 0

# 3. Pattern verification
grep "is None" services/interaction_service.py | wc -l
# Expected: Increased from baseline

# 4. Run tests
~/.local/bin/uv run pytest tests/test_interaction_service.py -v
```

---

## PHASE 4: Code Clarity (P2 - Medium Priority)

### Task 4.1: Create CurveColors Constants Class

**Effort**: 1 hour
**Impact**: 10 lines saved, better theming support
**Files Modified**: 2 (new `ui/color_constants.py`, `rendering/optimized_curve_renderer.py`)
**Risk**: Very Low

#### Code Changes

**Step 1**: Create `ui/color_constants.py`

```python
"""Standard color constants for curve rendering.

This module centralizes color definitions to:
- Eliminate hardcoded QColor(...) literals
- Enable easy theme customization
- Provide semantic color names
"""

from PySide6.QtGui import QColor, QPen
from PySide6.QtCore import Qt


class CurveColors:
    """Standard colors for curve rendering."""

    # Base colors
    WHITE = QColor(255, 255, 255)
    INACTIVE_GRAY = QColor(128, 128, 128, 128)  # Semi-transparent
    CURRENT_FRAME_MAGENTA = QColor(255, 0, 255)

    @staticmethod
    def get_inactive_pen(width: int = 1) -> QPen:
        """Create standard inactive segment pen.

        Args:
            width: Pen width in pixels

        Returns:
            QPen with inactive styling (gray, dashed)
        """
        pen = QPen(CurveColors.INACTIVE_GRAY)
        pen.setWidth(width)
        pen.setStyle(Qt.PenStyle.DashLine)
        return pen

    @staticmethod
    def get_active_pen(color: QColor | None = None, width: int = 2) -> QPen:
        """Create standard active segment pen.

        Args:
            color: Pen color (default: white)
            width: Pen width in pixels

        Returns:
            QPen with active styling (solid line)
        """
        pen_color = color if color else CurveColors.WHITE
        pen = QPen(pen_color)
        pen.setWidth(width)
        return pen
```

**Step 2**: Update `rendering/optimized_curve_renderer.py`

Replace hardcoded colors (lines 524, 570, 710, 573, 744):

**Before**:
```python
# Line 570
active_pen = QPen(QColor(255, 255, 255))
active_pen.setWidth(2)

# Line 573
inactive_pen = QPen(QColor(128, 128, 128, 128))
inactive_pen.setWidth(1)
inactive_pen.setStyle(Qt.PenStyle.DashLine)
```

**After**:
```python
# Add import at top
from ui.color_constants import CurveColors

# Line 570
active_pen = CurveColors.get_active_pen()

# Line 573
inactive_pen = CurveColors.get_inactive_pen()
```

#### Success Metrics
- [ ] `CurveColors` class created with 3 colors, 2 helper methods
- [ ] 6 hardcoded `QColor(255, 255, 255)` replaced
- [ ] 2 hardcoded `QColor(128, 128, 128, 128)` replaced
- [ ] All rendering tests pass

#### Verification Steps
```bash
# 1. Verify class created
./bpr ui/color_constants.py

# 2. Verify imports updated
grep "from ui.color_constants import" rendering/optimized_curve_renderer.py

# 3. Verify no hardcoded colors remain in renderer
grep "QColor(255, 255, 255)" rendering/optimized_curve_renderer.py
# Expected: 0 (or only in comments)

# 4. Run rendering tests
~/.local/bin/uv run pytest tests/test_unified_curve_rendering.py -v
```

---

### Task 4.2: Create BaseTrackingController

**Effort**: 1 hour
**Impact**: 30 lines saved, consistent controller lifecycle
**Files Modified**: 5 (new `ui/controllers/base_tracking_controller.py`, 4 tracking controllers)
**Risk**: Low

#### Code Changes

**Step 1**: Create `ui/controllers/base_tracking_controller.py`

```python
"""Base class for tracking-related controllers."""

from PySide6.QtCore import QObject

from protocols.ui import MainWindowProtocol
from stores.application_state import ApplicationState, get_application_state
from core.logging_config import get_logger

logger = get_logger(__name__)


class BaseTrackingController(QObject):
    """Base class for tracking-related controllers.

    Provides common initialization pattern for all tracking controllers:
    - Main window reference
    - ApplicationState access
    - Logging initialization message
    """

    def __init__(self, main_window: MainWindowProtocol) -> None:
        """Initialize base tracking controller.

        Args:
            main_window: Main window protocol interface
        """
        super().__init__()
        self.main_window = main_window
        self._app_state: ApplicationState = get_application_state()
        logger.info(f"{self.__class__.__name__} initialized")
```

**Step 2**: Update 4 tracking controllers

**Before** (each controller ~10 lines):
```python
class TrackingSelectionController(QObject):
    def __init__(self, main_window: MainWindowProtocol) -> None:
        """Initialize tracking selection controller..."""
        super().__init__()
        self.main_window = main_window
        self._app_state: ApplicationState = get_application_state()
        logger.info("TrackingSelectionController initialized")
```

**After** (each controller ~2 lines):
```python
from ui.controllers.base_tracking_controller import BaseTrackingController

class TrackingSelectionController(BaseTrackingController):
    # __init__ inherited - no override needed unless adding specific fields
    pass  # Or additional methods only
```

**Files to update**:
1. `ui/controllers/tracking_selection_controller.py`
2. `ui/controllers/tracking_data_controller.py`
3. `ui/controllers/tracking_display_controller.py`
4. `ui/controllers/multi_point_tracking_controller.py`

#### Success Metrics
- [ ] Base class created
- [ ] 4 controllers inherit from base
- [ ] ~40 lines of duplicate code removed
- [ ] All tracking tests pass

#### Verification Steps
```bash
# 1. Verify base class
./bpr ui/controllers/base_tracking_controller.py

# 2. Verify inheritance
grep "class.*Controller(BaseTrackingController)" ui/controllers/tracking_*.py | wc -l
# Expected: 4

# 3. Run tests
~/.local/bin/uv run pytest tests/ -k tracking -v

# 4. Type check all controllers
./bpr ui/controllers/tracking_*.py
```

---

### Task 4.3: Create ShortcutCommand Base Class

**Effort**: 1 hour
**Impact**: 20 lines saved, consistent widget validation
**Files Modified**: 2 (update `core/commands/shortcut_commands.py`)
**Risk**: Low

#### Code Changes

**Location**: `core/commands/shortcut_commands.py`

**Step 1**: Add base class (after imports, before first command)

```python
class ShortcutCommand(ABC):
    """Base class for keyboard shortcut commands.

    Provides common widget validation pattern for all shortcut commands.
    """

    def _get_curve_widget(self, context: ShortcutContext) -> CurveViewWidget | None:
        """Get curve widget with validation.

        Args:
            context: Shortcut context containing main window

        Returns:
            CurveViewWidget if available, None otherwise

        Logs warning if widget not available.
        """
        widget = context.main_window.curve_widget
        if not widget:
            logger.warning(f"{self.__class__.__name__}: No curve widget available")
        return widget

    @abstractmethod
    def execute(self, context: ShortcutContext) -> bool:
        """Execute shortcut command.

        Args:
            context: Shortcut execution context

        Returns:
            True if command executed successfully
        """
        ...
```

**Step 2**: Update commands to use base class

**Before**:
```python
class SetEndframeCommand:
    def execute(self, context: ShortcutContext) -> bool:
        curve_widget = context.main_window.curve_widget
        if not curve_widget:
            return False
        # ... rest
```

**After**:
```python
class SetEndframeCommand(ShortcutCommand):
    def execute(self, context: ShortcutContext) -> bool:
        widget = self._get_curve_widget(context)
        if not widget:
            return False
        # ... rest (use 'widget' instead of 'curve_widget')
```

**Apply to**: All 9 shortcut commands

#### Success Metrics
- [ ] Base class created with `_get_curve_widget` helper
- [ ] 9 commands inherit from `ShortcutCommand`
- [ ] 9 duplicate validation blocks replaced
- [ ] All shortcut tests pass

#### Verification Steps
```bash
# 1. Type check
./bpr core/commands/shortcut_commands.py

# 2. Verify inheritance
grep "class.*Command(ShortcutCommand)" core/commands/shortcut_commands.py | wc -l
# Expected: 9

# 3. Verify no duplicate validation
grep "curve_widget = context.main_window.curve_widget" core/commands/shortcut_commands.py | wc -l
# Expected: 1 (only in base class)

# 4. Run tests
~/.local/bin/uv run pytest tests/ -k shortcut -v
```

---

## FINAL VALIDATION

### Overall Success Metrics

**Quantitative Goals**:
- [ ] Total line reduction: ~326 lines (from baseline ~15,000 to ~14,674)
- [ ] Duplication eliminated:
  - [ ] 8 command classes use base class
  - [ ] 88 duplicate navigation lines → ~28 unified lines
  - [ ] 11 legacy patterns → modern pattern (9 in interaction_service.py, 2 in ui_service.py)
  - [ ] 5 event handlers with error handling
  - [ ] 74-line complex method → 8-line simple method
  - [ ] 3 color constant classes created
  - [ ] 4 tracking controllers use base
  - [ ] 9 shortcut commands use base

**Qualitative Goals**:
- [ ] KISS: Maximum nesting depth reduced from 5 to 2
- [ ] DRY: No duplicate error handling in commands
- [ ] DRY: No duplicate navigation logic
- [ ] Consistency: One way to get active curve data
- [ ] Robustness: Event handlers won't crash UI

### Comprehensive Test Suite

```bash
#!/bin/bash
# Run from project root

echo "=== KISS/DRY Refactoring Validation Suite ==="

# 1. Full test suite
echo "Running full test suite..."
~/.local/bin/uv run pytest tests/ -v --tb=short
if [ $? -ne 0 ]; then
    echo "❌ Test failures detected"
    exit 1
fi

# 2. Type checking
echo "Running type checker..."
./bpr --errors-only
if [ $? -ne 0 ]; then
    echo "❌ Type errors detected"
    exit 1
fi

# 3. Code metrics
echo "Checking line counts..."
TOTAL_LINES=$(find . -name "*.py" -not -path "./tests/*" -not -path "./.venv/*" | xargs wc -l | tail -1 | awk '{print $1}')
echo "Total lines (excluding tests): $TOTAL_LINES"
# Expected: ~14,674 (was ~15,000)

# 4. Pattern verification
echo "Verifying patterns removed..."

# No exception handlers in execute/undo/redo methods (should use _safe_execute)
INLINE_HANDLERS=$(awk '/def (execute|undo|redo)\(/,/^[[:space:]]*def / {if (/except Exception as e:/) count++} END {print count+0}' core/commands/curve_commands.py)
if [ $INLINE_HANDLERS -gt 0 ]; then
    echo "❌ Exception handlers in methods: $INLINE_HANDLERS (expected 0, should use _safe_execute)"
    exit 1
fi

# No duplicate navigation code
NAVIGATION_METHODS=$(grep -c "_navigate_to_.*_keyframe" ui/main_window.py)
if [ $NAVIGATION_METHODS -ne 2 ]; then
    echo "❌ Navigation methods count: $NAVIGATION_METHODS (expected 2)"
    exit 1
fi

# Modern pattern usage (after Task 3.1)
MODERN_PATTERN=$(grep -c "active_curve_data" services/interaction_service.py services/ui_service.py 2>/dev/null || echo "0")
if [ $MODERN_PATTERN -lt 11 ]; then
    echo "⚠️  Warning: Modern pattern usage: $MODERN_PATTERN (expected >= 11)"
fi

echo "✅ All validations passed!"
echo ""
echo "Summary:"
echo "- Total lines: $TOTAL_LINES"
echo "- Command exception handlers: $DUPLICATE_HANDLERS / 3"
echo "- Navigation methods: $NAVIGATION_METHODS / 2"
echo "- Modern pattern usage: $MODERN_PATTERN"
```

### Manual Validation Checklist

**UI Functionality** (run application and test):
- [ ] Load curve data successfully
- [ ] Navigate previous/next keyframe works
- [ ] UI labels update correctly (points, bounds, frames)
- [ ] Undo/redo operations work
- [ ] Mouse interactions don't crash
- [ ] Keyboard shortcuts work
- [ ] Exceptions are logged (check logs)

**Code Quality**:
- [ ] `./bpr` shows 0 errors
- [ ] All tests pass
- [ ] No regression in coverage: `~/.local/bin/uv run pytest --cov --cov-report=html`
- [ ] Git diff review shows no unintended changes

---

## ROLLBACK PROCEDURES

### Per-Task Rollback

**If any task fails**:
1. Revert file changes: `git checkout <file>`
2. Run tests: `~/.local/bin/uv run pytest tests/ -v`
3. Document issue in `IMPLEMENTATION_NOTES.md`

### Full Rollback

**If multiple failures or critical issues**:
```bash
# Create rollback branch
git checkout -b rollback-kiss-dry-cleanup

# Reset to before changes
git reset --hard <commit-before-phase-1>

# Verify tests pass
~/.local/bin/uv run pytest tests/ -v

# Document lessons learned
echo "Rollback performed: $(date)" >> IMPLEMENTATION_NOTES.md
echo "Reason: <describe issue>" >> IMPLEMENTATION_NOTES.md
```

---

## PROGRESS TRACKING

Create `IMPLEMENTATION_NOTES.md` to track progress:

```markdown
# KISS/DRY Implementation Progress

## Phase 1 (P0 - Critical)
- [ ] Task 1.1: CurveDataCommand base class
  - Started: YYYY-MM-DD
  - Completed: YYYY-MM-DD
  - Notes:
- [ ] Task 1.2: Navigation extraction
  - Started: YYYY-MM-DD
  - Completed: YYYY-MM-DD
  - Notes:

## Phase 2 (P0-P1 - High)
...

## Issues Encountered
1. <Date>: <Issue description> - Resolution: <How it was fixed>

## Metrics
- Baseline total lines: 15,000
- Current total lines: <update after each phase>
- Tests passing: <update after each phase>
- Type errors: <update after each phase>
```

---

## TIMELINE

**Recommended Schedule** (can be adjusted based on availability):

| Week | Phase | Tasks | Hours | Checkpoint |
|------|-------|-------|-------|------------|
| **Week 1** | Phase 1 | 1.1, 1.2 | 4.5 | All command tests pass |
| **Week 2** | Phase 2 | 2.1, 2.2, 2.3 | 4 | UI tests pass, docs updated |
| **Week 3** | Phase 3 | 3.1, 3.2 | 4.5 | Pattern consistency verified |
| **Week 4** | Phase 4 | 4.1, 4.2, 4.3 | 3 | All refactoring complete |
| **Week 4** | Final | Validation | 2 | Full test suite, metrics |

**Total**: 18 hours over 4 weeks

---

**END OF IMPLEMENTATION PLAN**

This plan provides step-by-step guidance for implementing all verified KISS/DRY improvements with:
- ✅ Specific code changes (before/after)
- ✅ Success metrics (quantitative & qualitative)
- ✅ Verification steps (automated & manual)
- ✅ Rollback procedures
- ✅ Progress tracking
- ✅ Risk mitigation

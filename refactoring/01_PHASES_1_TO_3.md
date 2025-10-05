# Selection State Refactoring - Phases 1-3: Core Infrastructure

**Navigation**: [← Overview](00_OVERVIEW.md) | [Phases 4-6 →](02_PHASES_4_TO_6.md)

---

## Phase 1: Add Selection State to ApplicationState

**Files Modified**: `stores/application_state.py`
**Dependencies**: None
**Risk Level**: LOW (only adds new functionality)

### 🤖 Recommended Agent

**`python-implementation-specialist`**
- **Scope**: `stores/application_state.py` only
- **Task**: Add selection state fields, methods, computed property per detailed spec below
- **Reasoning**: Straightforward CRUD operations, clear requirements
- **Context to provide**: Full Phase 1 specification from this document

### Step 1.1: Add Fields and Signal

**Location**: `stores/application_state.py:114-130` (in `__init__` method)

**BEFORE**:
```python
def __init__(self):
    super().__init__()
    self._mutex = QMutex()
    self._batch_mode = False
    self._pending_signals: dict[Signal, set[tuple]] = {}

    # Initialize state
    self._curves_data: dict[str, CurveDataList] = {}
    self._curve_metadata: dict[str, dict[str, Any]] = {}
    self._active_curve: str | None = None
    self._selection: dict[str, set[int]] = {}  # Point-level selection
    self._current_frame: int = 1
    self._view_state: ViewState = ViewState()
```

**AFTER**:
```python
def __init__(self):
    super().__init__()
    self._mutex = QMutex()
    self._batch_mode = False
    self._pending_signals: dict[Signal, set[tuple]] = {}

    # Initialize state
    self._curves_data: dict[str, CurveDataList] = {}
    self._curve_metadata: dict[str, dict[str, Any]] = {}
    self._active_curve: str | None = None
    self._selection: dict[str, set[int]] = {}  # Point-level selection (indices within curves)
    self._current_frame: int = 1
    self._view_state: ViewState = ViewState()

    # NEW: Curve-level selection state (which trajectories to display)
    # Note: This is DISTINCT from _selection above:
    #   - _selected_curves: which curve trajectories to show (curve names)
    #   - _selection: which points within active curve are selected (frame indices)
    self._selected_curves: set[str] = set()
    self._show_all_curves: bool = False
```

### Step 1.2: Add Signal Declaration

**Location**: `stores/application_state.py:106-112` (after other signal declarations)

**BEFORE**:
```python
class ApplicationState(QObject):
    # Signals
    state_changed: Signal = Signal()
    curves_changed: Signal = Signal(str)
    selection_changed: Signal = Signal(str, set)
    active_curve_changed: Signal = Signal(str)
    frame_changed: Signal = Signal(int)
    view_changed: Signal = Signal()
    curve_visibility_changed: Signal = Signal(str, bool)
```

**AFTER**:
```python
class ApplicationState(QObject):
    # Signals
    state_changed: Signal = Signal()
    curves_changed: Signal = Signal(str)
    selection_changed: Signal = Signal(str, set)  # Point-level (frame indices)
    active_curve_changed: Signal = Signal(str)
    frame_changed: Signal = Signal(int)
    view_changed: Signal = Signal()
    curve_visibility_changed: Signal = Signal(str, bool)

    # NEW: Curve-level selection state changed (selected_curves, show_all)
    selection_state_changed: Signal = Signal(set, bool)
```

### Step 1.3: Add Getter/Setter Methods with Validation

**Location**: `stores/application_state.py` (add after existing methods, around line 462)

**CODE TO ADD**:
```python
# ========================================
# Curve-Level Selection State (NEW)
# ========================================

def get_selected_curves(self) -> set[str]:
    """
    Get selected curves for display (returns copy).

    This is curve-level selection (which trajectories to show),
    distinct from point-level selection (which points within active curve).

    Note on terminology:
    - get_selected_curves() → which curve trajectories to display (this method)
    - get_selection(curve_name) → which frame indices within a curve are selected

    Returns:
        Set of selected curve names (copy for safety)
    """
    self._assert_main_thread()
    return self._selected_curves.copy()

def set_selected_curves(self, curve_names: set[str]) -> None:
    """
    Set which curves are selected for display.

    Automatically updates derived display_mode property via signal.

    Validation: Warns about curves not yet loaded, but allows setting
    selection before curves are loaded (for session restoration).

    Args:
        curve_names: Set of curve names to select
    """
    self._assert_main_thread()
    new_selection = curve_names.copy()

    # FIX #4: Validate curve existence (permissive - warn but don't filter)
    # This allows setting selection before curves load (session restoration)
    if self._curves_data:  # Only validate if curves loaded
        all_curves = set(self._curves_data.keys())
        invalid = new_selection - all_curves
        if invalid:
            logger.warning(
                f"Selecting curves not yet loaded: {invalid}. "
                f"Available curves: {all_curves}"
            )
            # Note: We keep invalid curves in selection for initialization flexibility
            # RenderState will filter to valid curves during rendering

    if new_selection != self._selected_curves:
        self._selected_curves = new_selection
        self._emit(self.selection_state_changed, (new_selection.copy(), self._show_all_curves))
        logger.debug(f"Curve selection changed: {len(new_selection)} curves selected")

def get_show_all_curves(self) -> bool:
    """Get show-all-curves mode state."""
    self._assert_main_thread()
    return self._show_all_curves

def set_show_all_curves(self, show_all: bool) -> None:
    """
    Set show-all-curves mode.

    Automatically updates derived display_mode property via signal.

    Args:
        show_all: Whether to show all visible curves
    """
    self._assert_main_thread()

    if show_all != self._show_all_curves:
        self._show_all_curves = show_all
        self._emit(self.selection_state_changed, (self._selected_curves.copy(), show_all))
        logger.debug(f"Show all curves mode: {show_all}")
```

### Step 1.4: Add Computed display_mode Property

**Location**: `stores/application_state.py` (add after the setters above)

**CODE TO ADD**:
```python
@property
def display_mode(self) -> DisplayMode:
    """
    Compute display mode from selection inputs.

    This is DERIVED STATE - always consistent with inputs, no storage.

    Logic:
    - Show-all enabled → ALL_VISIBLE
    - Curves selected → SELECTED
    - Otherwise → ACTIVE_ONLY

    Important: This property reflects state immediately, even during batch mode.
    Batch mode only defers signal emissions, not state visibility.

    Returns:
        DisplayMode enum computed from current selection state

    Example:
        >>> app_state = get_application_state()
        >>> app_state.set_show_all_curves(True)
        >>> app_state.display_mode
        <DisplayMode.ALL_VISIBLE: 1>

        >>> app_state.set_show_all_curves(False)
        >>> app_state.set_selected_curves({"Track1", "Track2"})
        >>> app_state.display_mode
        <DisplayMode.SELECTED: 2>

        >>> # Batch mode: state visible immediately, signals deferred
        >>> app_state.begin_batch()
        >>> app_state.set_selected_curves(set())
        >>> app_state.display_mode  # Returns ACTIVE_ONLY immediately!
        <DisplayMode.ACTIVE_ONLY: 3>
        >>> app_state.end_batch()  # Signals emit now
    """
    # Optional enhancement: Add thread safety assertion for consistency
    self._assert_main_thread()

    if self._show_all_curves:
        return DisplayMode.ALL_VISIBLE
    elif self._selected_curves:
        return DisplayMode.SELECTED
    else:
        return DisplayMode.ACTIVE_ONLY
```

### Step 1.5: Add Import

**Location**: `stores/application_state.py` (top of file, around line 10-20)

**BEFORE**:
```python
from PySide6.QtCore import QMutex, QObject, Signal
from core.type_aliases import CurveDataList
```

**AFTER**:
```python
from PySide6.QtCore import QMutex, QObject, Signal
from core.type_aliases import CurveDataList
from core.display_mode import DisplayMode
```

### Verification Steps

1. **Run type checker**:
   ```bash
   ./bpr stores/application_state.py
   ```
   Expected: No type errors

2. **Test display_mode computation**:
   ```bash
   .venv/bin/python3 -c "
   from stores.application_state import get_application_state, reset_application_state
   from core.display_mode import DisplayMode

   reset_application_state()
   app_state = get_application_state()

   # Initially ACTIVE_ONLY
   assert app_state.display_mode == DisplayMode.ACTIVE_ONLY, 'Initial mode wrong'

   # Select curves → SELECTED
   app_state.set_selected_curves({'curve1', 'curve2'})
   assert app_state.display_mode == DisplayMode.SELECTED, 'Selected mode wrong'

   # Enable show all → ALL_VISIBLE
   app_state.set_show_all_curves(True)
   assert app_state.display_mode == DisplayMode.ALL_VISIBLE, 'All visible mode wrong'

   # Disable show all → back to SELECTED
   app_state.set_show_all_curves(False)
   assert app_state.display_mode == DisplayMode.SELECTED, 'Back to selected wrong'

   # Clear selection → ACTIVE_ONLY
   app_state.set_selected_curves(set())
   assert app_state.display_mode == DisplayMode.ACTIVE_ONLY, 'Active only mode wrong'

   print('✅ All display_mode computations correct!')
   "
   ```

3. **Test validation warnings**:
   ```python
   # Should warn about non-existent curves but not crash
   import warnings
   from stores.application_state import get_application_state, reset_application_state

   reset_application_state()
   app_state = get_application_state()

   # Set selection before loading curves (session restoration scenario)
   app_state.set_selected_curves({"Track1", "Track2"})
   # Should work, no crash

   # Load curves
   app_state.set_curve_data("Track1", [...])

   # Select non-existent curve
   with warnings.catch_warnings(record=True) as w:
       warnings.simplefilter("always")
       app_state.set_selected_curves({"Track1", "FakeCurve"})
       assert len(w) == 1
       assert "not yet loaded" in str(w[0].message)

   print("✅ Validation warnings work correctly")
   ```

### Rollback Instructions

If this phase fails:
1. Remove the added code (fields, signal, methods, property, import)
2. Run: `git checkout stores/application_state.py`
3. Run type checker to confirm: `./bpr stores/application_state.py`

---

## Phase 2: Update TrackingPointsPanel

**Files Modified**: `ui/tracking_points_panel.py`
**Dependencies**: Phase 1 complete
**Risk Level**: MEDIUM (changes UI behavior)

### 🤖 Recommended Agent

**`python-implementation-specialist`**
- **Scope**: `ui/tracking_points_panel.py` only
- **Task**: Update panel to use ApplicationState, add reverse sync handler
- **Reasoning**: Standard implementation with clear spec
- **Context to provide**:
  - Phase 1 implementation results
  - Full Phase 2 specification from this document
  - Note: "FIX #8: Qt signal timing with QTimer.singleShot"

### Step 2.1: Add ApplicationState Reference

**Location**: `ui/tracking_points_panel.py:142-155` (in `__init__`)

**BEFORE**:
```python
def __init__(self, parent: QWidget | None = None):
    super().__init__(parent)

    # Internal state
    self._point_metadata: dict[str, PointMetadata] = {}
    self._updating: bool = False
    self._updating_display_mode: bool = False
    self._active_point: str | None = None

    # Setup UI components
    self._init_ui()

    # Install event filter for table keyboard events
    self._table_event_filter = TrackingTableEventFilter(self)
    self.table.installEventFilter(self._table_event_filter)
```

**AFTER**:
```python
def __init__(self, parent: QWidget | None = None):
    super().__init__(parent)

    # Internal state
    self._point_metadata: dict[str, PointMetadata] = {}
    self._updating: bool = False
    self._updating_display_mode: bool = False
    self._active_point: str | None = None

    # NEW: ApplicationState reference
    from stores.application_state import get_application_state
    self._app_state = get_application_state()

    # Setup UI components
    self._init_ui()

    # Install event filter for table keyboard events
    self._table_event_filter = TrackingTableEventFilter(self)
    self.table.installEventFilter(self._table_event_filter)

    # NEW: Subscribe to ApplicationState changes (for reverse sync)
    self._app_state.selection_state_changed.connect(self._on_app_state_changed)
```

### Step 2.2: Update Selection Changed Handler

**Location**: `ui/tracking_points_panel.py:511-517`

**BEFORE**:
```python
def _on_selection_changed(self) -> None:
    """Handle table selection changes."""
    if self._updating:
        return

    selected_points = self.get_selected_points()
    self.points_selected.emit(selected_points)
```

**AFTER**:
```python
def _on_selection_changed(self) -> None:
    """Handle table selection changes - update ApplicationState."""
    if self._updating:
        return

    selected_points = self.get_selected_points()

    # NEW: Update ApplicationState (single source of truth)
    self._app_state.set_selected_curves(set(selected_points))

    # Still emit for backward compatibility during migration
    self.points_selected.emit(selected_points)
```

### Step 2.3: Update Checkbox Handler

**Location**: `ui/tracking_points_panel.py:428-449`

**BEFORE**:
```python
def _on_display_mode_checkbox_toggled(self, checked: bool) -> None:
    """Handle toggle of display mode checkbox.

    Emits display_mode_changed signal with the appropriate DisplayMode.
    Re-entrancy guard prevents infinite loops.

    Args:
        checked: Whether to show all curves
    """
    # Re-entrancy guard: prevent signal loops
    if self._updating_display_mode:
        return

    self._updating_display_mode = True
    try:
        # Determine display mode from checkbox state and selection context
        mode = self._determine_mode_from_checkbox(checked)

        # Emit display mode changed signal
        self.display_mode_changed.emit(mode)
    finally:
        self._updating_display_mode = False
```

**AFTER**:
```python
def _on_display_mode_checkbox_toggled(self, checked: bool) -> None:
    """Handle toggle of display mode checkbox - update ApplicationState.

    Updates ApplicationState which automatically computes correct display_mode.
    Re-entrancy guard prevents infinite loops.

    Args:
        checked: Whether to show all curves
    """
    # Re-entrancy guard: prevent signal loops
    if self._updating_display_mode:
        return

    self._updating_display_mode = True
    try:
        # NEW: Update ApplicationState (single source of truth)
        self._app_state.set_show_all_curves(checked)

        # KEEP: Emit legacy signal for backward compatibility during migration
        mode = self._determine_mode_from_checkbox(checked)
        self.display_mode_changed.emit(mode)
    finally:
        self._updating_display_mode = False
```

### Step 2.4: Add Reverse Sync Handler with Qt Signal Timing Fix

**Location**: `ui/tracking_points_panel.py` (add new method after `_on_display_mode_checkbox_toggled`)

**CODE TO ADD**:
```python
def _on_app_state_changed(self, selected_curves: set[str], show_all: bool) -> None:
    """
    Sync UI when ApplicationState changes (reverse flow).

    Handles external changes to selection state (e.g., from other UI or API).
    Uses _updating flag to prevent circular updates.

    FIX #8: Qt signal timing - use QTimer to defer flag release.
    Qt signals are queued, so setting _updating=False in finally block
    happens before queued signals fire. QTimer.singleShot(0, ...) ensures
    flag release happens AFTER all queued signals are processed.

    Args:
        selected_curves: Set of selected curve names from ApplicationState
        show_all: Show-all-curves mode from ApplicationState
    """
    if self._updating:
        return

    self._updating = True
    try:
        # Update table selection to match ApplicationState
        self.set_selected_points(list(selected_curves))

        # Update checkbox to match ApplicationState
        if self.display_mode_checkbox.isChecked() != show_all:
            self.display_mode_checkbox.setChecked(show_all)
    finally:
        # FIX #8: Defer flag release to next event loop cycle
        # Ensures all queued Qt signals are processed before flag is cleared
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: setattr(self, '_updating', False))
```

### Verification Steps

1. **Type check**:
   ```bash
   ./bpr ui/tracking_points_panel.py
   ```

2. **Manual test - Selection updates ApplicationState**:
   ```python
   from ui.tracking_points_panel import TrackingPointsPanel
   from stores.application_state import get_application_state, reset_application_state
   from core.models import CurvePoint
   from core.display_mode import DisplayMode
   from PySide6.QtWidgets import QApplication
   import sys

   app = QApplication(sys.argv)
   reset_application_state()
   panel = TrackingPointsPanel()
   app_state = get_application_state()

   # Simulate adding tracking points
   panel.set_tracked_data({
       "Track1": [CurvePoint(1, 10, 20)],
       "Track2": [CurvePoint(1, 30, 40)]
   })

   # Simulate table selection
   panel.set_selected_points(["Track1", "Track2"])

   # Verify ApplicationState updated
   assert app_state.get_selected_curves() == {"Track1", "Track2"}
   assert app_state.display_mode == DisplayMode.SELECTED
   print("✅ Panel updates ApplicationState correctly")
   ```

3. **Manual test - Checkbox updates ApplicationState**:
   ```python
   # Check the checkbox
   panel.display_mode_checkbox.setChecked(True)

   # Verify ApplicationState updated
   assert app_state.get_show_all_curves() is True
   assert app_state.display_mode == DisplayMode.ALL_VISIBLE
   print("✅ Checkbox updates ApplicationState correctly")
   ```

### Rollback Instructions

1. Revert changes: `git checkout ui/tracking_points_panel.py`
2. Run type checker: `./bpr ui/tracking_points_panel.py`

---

## Phase 2.5: Comprehensive Migration Audit (NEW)

**Files Created**: `/tmp/migration_audit/` (temporary audit files)
**Dependencies**: Phase 1-2 complete
**Risk Level**: NONE (read-only audit)

### 🤖 Recommended Approach

**Manual grep commands** (no agent needed)
- **Alternative**: `best-practices-checker` for deeper analysis
- **Reasoning**: Simple pattern matching, well-defined grep commands
- **Optional enhancement**: Use agent for comprehensive code review of affected areas

### Purpose

**CRITICAL**: Before making ANY breaking changes, we must find ALL code that will break.

This phase creates exhaustive checklists of:
1. All `display_mode` setter usages (will break when setter removed)
2. All `selected_curve_names` field accesses (will break when field removed)
3. All other potentially affected code

### Step 2.5.1: Search for All display_mode Setters

```bash
# Create audit directory
mkdir -p /tmp/migration_audit

# Find all display_mode setter usages
echo "=== Finding ALL display_mode setters ==="
grep -rn "\.display_mode\s*=" ui/ rendering/ services/ core/ tests/ --include="*.py" | \
  tee /tmp/migration_audit/display_mode_setters.txt

# Count total
wc -l /tmp/migration_audit/display_mode_setters.txt
```

**Expected output**: List of ALL files and line numbers where `display_mode` is set.

### Step 2.5.2: Search for All selected_curve_names Accesses

```bash
echo "=== Finding ALL selected_curve_names accesses ==="
grep -rn "\.selected_curve_names" ui/ rendering/ services/ core/ tests/ --include="*.py" | \
  tee /tmp/migration_audit/selected_curve_names_refs.txt

# Count total
wc -l /tmp/migration_audit/selected_curve_names_refs.txt
```

### Step 2.5.3: Search for Other Affected Patterns

```bash
echo "=== Finding set_selected_points calls ==="
grep -rn "\.set_selected_points(" ui/ tests/ --include="*.py" | \
  tee /tmp/migration_audit/set_selected_points_calls.txt

echo "=== Finding points_selected signal connections ==="
grep -rn "points_selected\.connect\|points_selected\.emit" ui/ tests/ --include="*.py" | \
  tee /tmp/migration_audit/points_selected_signals.txt

echo "=== Finding display_mode_changed signal connections ==="
grep -rn "display_mode_changed\.connect\|display_mode_changed\.emit" ui/ tests/ --include="*.py" | \
  tee /tmp/migration_audit/display_mode_changed_signals.txt
```

### Step 2.5.4: Create Migration Checklist

Create `/tmp/migration_audit/MIGRATION_CHECKLIST.md`:

```markdown
# Migration Checklist

Generated: [date]

## Phase 3: CurveViewWidget Changes
- [ ] Deprecation wrapper added to display_mode setter
- [ ] Widget field sync fixed in _on_selection_state_changed

## Phase 4: MultiCurveManager Changes

### display_mode setters to update:
[List each file:line from display_mode_setters.txt]
- [ ] ui/multi_curve_manager.py:801
- [ ] [... all other locations]

### selected_curve_names accesses to update:
[List each file:line from selected_curve_names_refs.txt]
- [ ] ui/multi_curve_manager.py:897
- [ ] [... all other locations]

## Phase 5: Controller Changes

### display_mode setters to update:
- [ ] ui/controllers/multi_point_tracking_controller.py:XXX
- [ ] [... all other locations]

## Phase 6: Test Changes

### display_mode setters to update:
- [ ] tests/test_display_mode_integration.py:58
- [ ] tests/test_display_mode_integration.py:79
- [ ] [... all other locations]

## Phase 8: Signal Cleanup

### Signals to review for removal:
- [ ] points_selected - check if still needed
- [ ] display_mode_changed - check if still needed

## Verification

- [ ] All items above checked off
- [ ] grep returns zero results for old patterns:
  ```bash
  grep -r "widget\.display_mode\s*=" --include="*.py" | grep -v "DEPRECATED"
  ```
- [ ] Zero DeprecationWarnings in test output
```

### Step 2.5.5: Manual Review

**ACTION REQUIRED**: Manually review each file in the audit outputs and:
1. Mark which phase will handle each location
2. Identify any complex cases needing special handling
3. Update the checklist with exact locations

### Verification Steps

1. **Verify audit files created**:
   ```bash
   ls -la /tmp/migration_audit/
   ```
   Expected: All 5 files present

2. **Review total counts**:
   ```bash
   echo "display_mode setters: $(wc -l < /tmp/migration_audit/display_mode_setters.txt)"
   echo "selected_curve_names refs: $(wc -l < /tmp/migration_audit/selected_curve_names_refs.txt)"
   ```

3. **No false positives in grep**:
   Manually scan first 10 lines of each audit file to confirm they're real usages, not comments.

### Success Criteria

- [ ] All audit files generated
- [ ] Migration checklist created
- [ ] Manual review completed
- [ ] All complex cases identified and documented

**DO NOT PROCEED to Phase 3 until this audit is complete and reviewed.**

### Rollback Instructions

This is a read-only phase - just delete audit files:
```bash
rm -rf /tmp/migration_audit/
```

---

## Phase 3: Update CurveViewWidget with Deprecation

**Files Modified**: `ui/curve_view_widget.py`
**Dependencies**: Phase 1, 2, 2.5 complete
**Risk Level**: LOW (backward compatible via deprecation wrapper)

**CRITICAL CHANGE**: Unlike original plan, this phase ADDS a deprecation wrapper instead of removing the setter entirely. This allows Phases 4-7 to complete before breaking changes occur.

### 🤖 Recommended Agent

**`python-implementation-specialist`**
- **Scope**: `ui/curve_view_widget.py` only
- **Task**: Convert display_mode to property with deprecation wrapper, add field sync
- **Reasoning**: Standard implementation with clear deprecation pattern
- **Context to provide**:
  - Phase 1-2 results
  - Full Phase 3 specification
  - Note: "FIX #2: Widget field synchronization in _on_selection_state_changed"

### 🔍 Post-Phase 3 Review (Launch in Parallel)

After completing Phases 1-3, **launch review team in parallel** (read-only, always safe):

**Agent 1: `python-code-reviewer`**
- **Task**: "Review all changes from Phases 1-3 for code quality, bugs, and edge cases"
- **Files**: `stores/application_state.py`, `ui/tracking_points_panel.py`, `ui/curve_view_widget.py`

**Agent 2: `type-system-expert`**
- **Task**: "Check for type errors in modified files, verify type annotations correct"
- **Files**: Same as above

**Synthesis**: Review both reports, fix any issues found before proceeding to Phase 4.

### Step 3.1: Remove Stored display_mode Field

**Location**: `ui/curve_view_widget.py:194-195`

**BEFORE**:
```python
# Display mode
self._display_mode: DisplayMode = DisplayMode.ACTIVE_ONLY
self._updating_display_mode: bool = False
```

**AFTER**:
```python
# Display mode management (removed _display_mode storage - now read from ApplicationState)
self._updating_display_mode: bool = False
```

### Step 3.2: Convert display_mode to Property with Deprecation Wrapper

**Location**: `ui/curve_view_widget.py:407-454`

**BEFORE**:
```python
@property
def display_mode(self) -> DisplayMode:
    """[existing docstring]"""
    return self._display_mode

@display_mode.setter
def display_mode(self, mode: DisplayMode) -> None:
    """[existing docstring]"""
    if self._updating_display_mode:
        return

    self._updating_display_mode = True
    try:
        self._display_mode = mode

        # If mode requires selection but none exists, select active curve
        if mode == DisplayMode.SELECTED and not self.selected_curve_names:
            if self._app_state.active_curve:
                self.selected_curve_names = {self._app_state.active_curve}
        # If mode is ACTIVE_ONLY, clear selection
        elif mode == DisplayMode.ACTIVE_ONLY:
            self.selected_curve_names = set()

        # Trigger repaint to reflect mode change
        self.update()
    finally:
        self._updating_display_mode = False
```

**AFTER**:
```python
@property
def display_mode(self) -> DisplayMode:
    """
    Get current display mode from ApplicationState.

    This is a VIEW of ApplicationState - always fresh, no stale data.
    Display mode is computed from selection inputs, never stored.

    Returns:
        DisplayMode computed from ApplicationState selection state

    Example:
        >>> widget = CurveViewWidget()
        >>> app_state = get_application_state()
        >>> app_state.set_show_all_curves(True)
        >>> widget.display_mode
        <DisplayMode.ALL_VISIBLE: 1>

        >>> app_state.set_selected_curves({"Track1", "Track2"})
        >>> app_state.set_show_all_curves(False)
        >>> widget.display_mode
        <DisplayMode.SELECTED: 2>
    """
    return self._app_state.display_mode

@display_mode.setter
def display_mode(self, mode: DisplayMode) -> None:
    """
    DEPRECATED: Set display mode via ApplicationState instead.

    This setter is deprecated and will be removed in Phase 8.

    Use ApplicationState methods:
    - app_state.set_show_all_curves(True) → ALL_VISIBLE
    - app_state.set_selected_curves({...}) → SELECTED
    - app_state.set_selected_curves(set()) → ACTIVE_ONLY

    This backward-compatibility wrapper converts old API calls to new API.

    Args:
        mode: DisplayMode to set (converted to ApplicationState calls)
    """
    import warnings
    warnings.warn(
        "Setting display_mode directly is deprecated. "
        "Use ApplicationState: "
        "app_state.set_show_all_curves(True) for ALL_VISIBLE, "
        "app_state.set_selected_curves({...}) for SELECTED, "
        "app_state.set_selected_curves(set()) for ACTIVE_ONLY",
        DeprecationWarning,
        stacklevel=2
    )

    if self._updating_display_mode:
        return

    self._updating_display_mode = True
    try:
        # Convert old API to new API
        if mode == DisplayMode.ALL_VISIBLE:
            self._app_state.set_show_all_curves(True)

        elif mode == DisplayMode.SELECTED:
            # Ensure something is selected
            current_selection = self._app_state.get_selected_curves()
            if not current_selection and self.active_curve_name:
                self._app_state.set_selected_curves({self.active_curve_name})
            self._app_state.set_show_all_curves(False)

        elif mode == DisplayMode.ACTIVE_ONLY:
            self._app_state.set_show_all_curves(False)
            self._app_state.set_selected_curves(set())

        # Trigger repaint
        self.update()
    finally:
        self._updating_display_mode = False
```

### Step 3.3: Subscribe to Selection State Changes

**Location**: `ui/curve_view_widget.py:166` (in `__init__`, after `self._app_state = get_application_state()`)

**BEFORE**:
```python
# ApplicationState integration
self._app_state = get_application_state()
```

**AFTER**:
```python
# ApplicationState integration
self._app_state = get_application_state()

# NEW: Subscribe to selection state changes for repainting
self._app_state.selection_state_changed.connect(self._on_selection_state_changed)
```

### Step 3.4: Add Selection State Change Handler with Field Sync Fix

**Location**: `ui/curve_view_widget.py` (add new method around line 1350, near other event handlers)

**CODE TO ADD**:
```python
def _on_selection_state_changed(self, selected_curves: set[str], show_all: bool) -> None:
    """
    Update widget and repaint when ApplicationState selection changes.

    FIX #2: Sync widget fields that renderer might use.
    The widget maintains local copies of selected_curve_names and
    selected_curves_ordered for rendering performance. These MUST
    be kept in sync with ApplicationState.

    Args:
        selected_curves: Selected curve names from ApplicationState
        show_all: Show-all mode from ApplicationState
    """
    # FIX #2: Update widget's local fields for rendering
    # These are caches of ApplicationState for O(1) membership checks
    self.selected_curve_names = selected_curves.copy()
    self.selected_curves_ordered = list(selected_curves)

    # Trigger repaint to reflect updated state
    # display_mode property automatically reflects new ApplicationState
    self.update()
```

### ⚠️ BACKWARD COMPATIBILITY NOTICE

After this phase:
- Setting `display_mode` still works but emits DeprecationWarning
- Old code continues functioning during Phases 4-7
- Warnings visible in logs to identify code needing updates
- Phase 8 will remove the setter entirely

### Verification Steps

1. **Type check**:
   ```bash
   ./bpr ui/curve_view_widget.py
   ```

2. **Test read-only property**:
   ```python
   from ui.curve_view_widget import CurveViewWidget
   from stores.application_state import get_application_state, reset_application_state
   from core.display_mode import DisplayMode

   reset_application_state()
   widget = CurveViewWidget()
   app_state = get_application_state()

   # Change ApplicationState
   app_state.set_show_all_curves(True)

   # Widget property reflects ApplicationState
   assert widget.display_mode == DisplayMode.ALL_VISIBLE
   print("✅ Widget reads display_mode from ApplicationState")
   ```

3. **Test deprecation wrapper works**:
   ```python
   import warnings

   # Old API still works but warns
   with warnings.catch_warnings(record=True) as w:
       warnings.simplefilter("always")
       widget.display_mode = DisplayMode.SELECTED
       assert len(w) == 1
       assert issubclass(w[0].category, DeprecationWarning)
       assert "deprecated" in str(w[0].message).lower()

   # But it DID update ApplicationState
   assert app_state.display_mode == DisplayMode.SELECTED
   print("✅ Deprecation wrapper works correctly")
   ```

4. **Test field synchronization**:
   ```python
   # Change ApplicationState externally
   app_state.set_selected_curves({"Track1", "Track2"})

   # Widget fields updated
   assert widget.selected_curve_names == {"Track1", "Track2"}
   assert set(widget.selected_curves_ordered) == {"Track1", "Track2"}
   print("✅ Widget fields synchronized correctly")
   ```

### Rollback Instructions

1. Revert: `git checkout ui/curve_view_widget.py`
2. Type check: `./bpr ui/curve_view_widget.py`

---

**Next**: [Phases 4-6: Integration & Testing](02_PHASES_4_TO_6.md)

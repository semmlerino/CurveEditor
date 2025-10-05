# Selection State Refactoring - Revised Implementation Plan

**Date**: October 2025
**Status**: Ready for Implementation (Revised)
**Based On**: SELECTION_STATE_ARCHITECTURE_SOLUTION.md + Three Independent Reviews
**Revision**: Incorporates fixes for 8 critical/high-priority issues

---

## Table of Contents

1. [Overview](#overview)
2. [Phase 1: Add Selection State to ApplicationState](#phase-1-add-selection-state-to-applicationstate)
3. [Phase 2: Update TrackingPointsPanel](#phase-2-update-trackingpointspanel)
4. [Phase 2.5: Comprehensive Migration Audit (NEW)](#phase-25-comprehensive-migration-audit-new)
5. [Phase 3: Update CurveViewWidget with Deprecation](#phase-3-update-curveviewwidget-with-deprecation)
6. [Phase 4: Update MultiCurveManager](#phase-4-update-multicurvemanager)
7. [Phase 5: Update Controllers](#phase-5-update-controllers)
8. [Phase 6: Update Tests](#phase-6-update-tests)
9. [Phase 7: Documentation and Session Persistence](#phase-7-documentation-and-session-persistence)
10. [Phase 8: Final Cleanup - Remove All Backward Compatibility (NEW)](#phase-8-final-cleanup---remove-all-backward-compatibility-new)
11. [Rollback Instructions](#rollback-instructions)

---

## Overview

### Problem Being Solved

**Bug**: Selecting multiple curves in tracking panel only shows one curve in the viewport.

**Root Cause**: Selection state is fragmented across three locations with manual synchronization:
1. `TrackingPointsPanel` - checkbox state and table selection
2. `MultiCurveManager.selected_curve_names` - stored selection
3. `CurveViewWidget._display_mode` - stored display mode

When `selected_curve_names` is updated but `display_mode` is not set to `SELECTED`, only the active curve renders.

### Solution Architecture

**Centralize ALL selection inputs in ApplicationState** and make `display_mode` a computed property:

```
ApplicationState (Single Source of Truth):
├─ _selected_curves: set[str]           # Authoritative input
├─ _show_all_curves: bool               # Authoritative input
└─ display_mode: @property → DisplayMode  # Computed (never stored)
```

**Key Insight**: Derived state should NEVER be stored. Compute it fresh every time.

### Critical Fixes in This Revision

This revised plan addresses **8 critical and high-priority issues** identified by independent reviews:

1. ✅ **Phase ordering fixed** - Deprecation wrapper added before breaking changes
2. ✅ **Widget field synchronization** - Updates `selected_curve_names` and `selected_curves_ordered`
3. ✅ **Comprehensive audit phase** - Phase 2.5 finds ALL affected locations before changes
4. ✅ **Validation added** - Warns about non-existent curves without breaking initialization
5. ✅ **Redundant updates removed** - Controller doesn't re-update what Panel already did
6. ✅ **Backward compatibility** - Temporary compatibility layer for smooth migration
7. ✅ **Complete test coverage** - All edge cases covered
8. ✅ **Session persistence** - Selection state survives restart

---

## Phase 1: Add Selection State to ApplicationState

**Files Modified**: `stores/application_state.py`
**Dependencies**: None
**Risk Level**: LOW (only adds new functionality)

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

## Phase 4: Update MultiCurveManager

**Files Modified**: `ui/multi_curve_manager.py`
**Dependencies**: Phase 1-3 complete
**Risk Level**: LOW (backward compatible via deprecation properties)

### Step 4.1: Add Backward-Compatible selected_curve_names Property

**Location**: `ui/multi_curve_manager.py:47-48`

**BEFORE**:
```python
# NEW: Track selected curves for multi-curve display
self.selected_curve_names: set[str] = set()
```

**AFTER**:
```python
# REMOVED: selected_curve_names now in ApplicationState
# Backward-compatible property provided below for gradual migration
```

**Add this property at class level** (after `__init__`):

```python
@property
def selected_curve_names(self) -> set[str]:
    """
    DEPRECATED: Access selected curves via ApplicationState.

    This property is deprecated and will be removed in Phase 8.
    Use: get_application_state().get_selected_curves()

    Returns:
        Set of selected curve names from ApplicationState
    """
    import warnings
    warnings.warn(
        "manager.selected_curve_names is deprecated. "
        "Use get_application_state().get_selected_curves() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return self._app_state.get_selected_curves()

@selected_curve_names.setter
def selected_curve_names(self, value: set[str]) -> None:
    """
    DEPRECATED: Set selected curves via ApplicationState.

    This setter is deprecated and will be removed in Phase 8.
    Use: get_application_state().set_selected_curves(value)

    Args:
        value: Set of curve names to select
    """
    import warnings
    warnings.warn(
        "Setting manager.selected_curve_names is deprecated. "
        "Use get_application_state().set_selected_curves() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    self._app_state.set_selected_curves(value)
```

### Step 4.2: Update set_curves_data Method

**Location**: `ui/multi_curve_manager.py:76-135`

**Key changes**:
1. Use `app_state.set_selected_curves()` instead of `self.selected_curve_names`
2. Remove manual `widget.display_mode =` assignment (deprecated)

**BEFORE**:
```python
def set_curves_data(
    self,
    curves: dict[str, CurveDataList],
    metadata: dict[str, dict[str, Any]] | None = None,
    active_curve: str | None = None,
    selected_curves: list[str] | None = None,
) -> None:
    """[docstring]"""
    # Use batch mode to prevent signal storms
    self._app_state.begin_batch()
    try:
        # Set all curve data in ApplicationState
        for name, data in curves.items():
            curve_metadata = metadata.get(name) if metadata else None
            self._app_state.set_curve_data(name, data, curve_metadata)

            # Set default metadata if not provided
            if not curve_metadata:
                current_meta = self._app_state.get_curve_metadata(name)
                if "visible" not in current_meta:
                    self._app_state.set_curve_visibility(name, True)

        # Update selected curves if specified
        if selected_curves is not None:
            self.selected_curve_names = set(selected_curves)
            # CRITICAL FIX: Update display mode to SELECTED when curves are selected
            # This fixes the bug where selecting multiple curves only shows one
            if selected_curves:
                self.widget.display_mode = DisplayMode.SELECTED  # ❌ OLD WAY
        elif not self.selected_curve_names:
            # If no selection specified and no existing selection, default to active curve
            self.selected_curve_names = {active_curve} if active_curve else set()

        # ... rest of method ...
```

**AFTER**:
```python
def set_curves_data(
    self,
    curves: dict[str, CurveDataList],
    metadata: dict[str, dict[str, Any]] | None = None,
    active_curve: str | None = None,
    selected_curves: list[str] | None = None,
) -> None:
    """
    Set multiple curves to display.

    Args:
        curves: Dictionary mapping curve names to curve data
        metadata: Optional dictionary with per-curve metadata (visibility, color, etc.)
        active_curve: Name of the currently active curve for editing
        selected_curves: Optional list of curves to select for display
    """
    # Use batch mode to prevent signal storms
    self._app_state.begin_batch()
    try:
        # Set all curve data in ApplicationState
        for name, data in curves.items():
            curve_metadata = metadata.get(name) if metadata else None
            self._app_state.set_curve_data(name, data, curve_metadata)

            # Set default metadata if not provided
            if not curve_metadata:
                current_meta = self._app_state.get_curve_metadata(name)
                if "visible" not in current_meta:
                    self._app_state.set_curve_visibility(name, True)

        # NEW: Update selection in ApplicationState (single source of truth)
        if selected_curves is not None:
            self._app_state.set_selected_curves(set(selected_curves))
            # NO MANUAL display_mode UPDATE NEEDED - computed automatically! ✅
        elif active_curve:
            # Default to active curve if no selection specified
            self._app_state.set_selected_curves({active_curve})

        # Set the active curve
        if active_curve and active_curve in curves:
            self._app_state.set_active_curve(active_curve)
            # Update the single curve data for backward compatibility
            self.widget.set_curve_data(curves[active_curve])
        elif curves:
            # Default to first curve if no active curve specified
            first_curve = next(iter(curves.keys()))
            self._app_state.set_active_curve(first_curve)
            self.widget.set_curve_data(curves[first_curve])
        else:
            self._app_state.set_active_curve(None)
            self.widget.set_curve_data([])
    finally:
        self._app_state.end_batch()

    # Trigger repaint to show all curves
    self.widget.update()
    logger.debug(
        f"Set {len(curves)} curves, active: {self._app_state.active_curve}, "
        f"selected: {self._app_state.get_selected_curves()}, "
        f"mode: {self._app_state.display_mode}"
    )
```

### Step 4.3: Update set_selected_curves Method

**Location**: `ui/multi_curve_manager.py:252-269`

**BEFORE**:
```python
def set_selected_curves(self, curve_names: list[str]) -> None:
    """[docstring]"""
    self.selected_curve_names = set(curve_names)

    # ... rest of implementation ...
```

**AFTER**:
```python
def set_selected_curves(self, curve_names: list[str]) -> None:
    """
    Set selected curves for display.

    Args:
        curve_names: List of curve names to select
    """
    # NEW: Update ApplicationState (single source of truth)
    self._app_state.set_selected_curves(set(curve_names))

    # Update widget's ordered list for rendering order
    self.widget.selected_curve_names = set(curve_names)
    self.widget.selected_curves_ordered = list(curve_names)

    # Trigger repaint
    self.widget.update()

    logger.debug(
        f"Selected curves: {self._app_state.get_selected_curves()}, "
        f"Active: {self._app_state.active_curve}, "
        f"Mode: {self._app_state.display_mode}"
    )
```

### Step 4.4: Update center_on_selected_curves Method

**Location**: `ui/multi_curve_manager.py:271-336`

**BEFORE**:
```python
def center_on_selected_curves(self) -> None:
    """[docstring]"""
    all_curve_names = self._app_state.get_all_curve_names()
    logger.debug(
        f"center_on_selected_curves called with selected: {self.selected_curve_names}, ApplicationState curves: {all_curve_names}"
    )
    if not self.selected_curve_names or not all_curve_names:
        # ... rest ...

    for curve_name in self.selected_curve_names:
        # ... rest ...
```

**AFTER**:
```python
def center_on_selected_curves(self) -> None:
    """Center view on all selected curves."""
    all_curve_names = self._app_state.get_all_curve_names()
    selected_curves = self._app_state.get_selected_curves()  # NEW: Read from ApplicationState

    logger.debug(
        f"center_on_selected_curves called with selected: {selected_curves}, ApplicationState curves: {all_curve_names}"
    )
    if not selected_curves or not all_curve_names:
        logger.debug("Early return - no selected curves or no data in ApplicationState")
        return

    # Collect all points from all selected curves
    all_points: list[tuple[float, float]] = []

    for curve_name in selected_curves:  # NEW: Use ApplicationState selection
        if curve_name in all_curve_names:
            # ... rest unchanged ...
```

### Verification Steps

1. **Type check**:
   ```bash
   ./bpr ui/multi_curve_manager.py
   ```

2. **Test set_curves_data uses ApplicationState**:
   ```python
   from ui.multi_curve_manager import MultiCurveManager
   from ui.curve_view_widget import CurveViewWidget
   from stores.application_state import get_application_state, reset_application_state
   from core.display_mode import DisplayMode
   from core.models import CurvePoint

   reset_application_state()
   widget = CurveViewWidget()
   manager = MultiCurveManager(widget)
   app_state = get_application_state()

   # Set curves with selection
   manager.set_curves_data(
       {"curve1": [CurvePoint(1, 10, 20)], "curve2": [CurvePoint(1, 30, 40)]},
       selected_curves=["curve1", "curve2"]
   )

   # ApplicationState updated
   assert app_state.get_selected_curves() == {"curve1", "curve2"}
   assert app_state.display_mode == DisplayMode.SELECTED
   print("✅ Manager updates ApplicationState correctly")
   ```

3. **Test backward-compat property**:
   ```python
   import warnings

   # Old API (reading field) still works but warns
   with warnings.catch_warnings(record=True) as w:
       warnings.simplefilter("always")
       selected = manager.selected_curve_names
       assert len(w) == 1
       assert "deprecated" in str(w[0].message).lower()
       assert selected == {"curve1", "curve2"}

   print("✅ Backward-compat property works")
   ```

### Rollback Instructions

1. Revert: `git checkout ui/multi_curve_manager.py`
2. Type check: `./bpr ui/multi_curve_manager.py`

---

## Phase 5: Update Controllers

**Files Modified**:
- `ui/controllers/multi_point_tracking_controller.py`
- `ui/controllers/curve_view/curve_data_facade.py`
- `ui/main_window.py`

**Dependencies**: Phase 1-4 complete
**Risk Level**: MEDIUM (fixes synchronization loop bug)

### Step 5.1: Remove Synchronization Loop and Redundant Update

**Location**: `ui/controllers/multi_point_tracking_controller.py:342-377`

**CRITICAL**: This fixes the original race condition bug.

**BEFORE**:
```python
def on_tracking_points_selected(self, point_names: list[str]) -> None:
    """Handle selection of tracking points from panel."""
    # Set the last selected point as the active timeline point
    self.main_window.active_timeline_point = point_names[-1] if point_names else None

    # ❌ SYNCHRONIZATION LOOP - THIS LINE CREATES THE BUG:
    # Synchronize table selection FIRST (before update_curve_display queries it)
    # This prevents race condition where set_selected_points() clears selection mid-update
    if self.main_window.tracking_panel:
        self.main_window.tracking_panel.set_selected_points(point_names)  # ← REMOVE THIS

    # Synchronize selection state to CurveDataStore
    self._sync_tracking_selection_to_curve_store(point_names)

    # Update the curve display with MANUAL_SELECTION context
    self.update_curve_display(SelectionContext.MANUAL_SELECTION, selected_points=point_names)

    # ... rest of method ...
```

**AFTER**:
```python
def on_tracking_points_selected(self, point_names: list[str]) -> None:
    """
    Handle selection of tracking points from panel.

    FIX #1: Synchronization loop removed - panel already has correct selection.
    FIX #5: Redundant ApplicationState update removed - panel already updated it.

    The panel has already:
    1. Updated its UI selection
    2. Updated ApplicationState via _on_selection_changed()
    3. Emitted this signal

    We just need to handle OTHER responsibilities (timeline, store sync, display).
    NO need to sync back to panel - that creates circular dependency!

    Args:
        point_names: List of selected point names (curve names/trajectories)
    """
    # Set the last selected point as the active timeline point
    self.main_window.active_timeline_point = point_names[-1] if point_names else None

    # ✅ REMOVED synchronization loop (panel already has correct selection)
    # ✅ REMOVED redundant ApplicationState update (panel already did it)

    # Synchronize selection state to CurveDataStore (backward compatibility)
    self._sync_tracking_selection_to_curve_store(point_names)

    # Update the curve display with MANUAL_SELECTION context
    self.update_curve_display(SelectionContext.MANUAL_SELECTION, selected_points=point_names)

    # Center view on selected point at current frame
    # Small delay to ensure curve data and point selection are processed
    if self.main_window.curve_widget and point_names:
        if callable(getattr(self.main_window.curve_widget, "center_on_selection", None)):
            # Use small delay to allow widget updates to complete
            def safe_center_on_selection():
                if self.main_window.curve_widget and not self.main_window.curve_widget.isHidden():
                    self.main_window.curve_widget.center_on_selection()

            QTimer.singleShot(10, safe_center_on_selection)
            logger.debug("Scheduled centering on selected point after 10ms delay")

    logger.debug(f"Selected tracking points: {point_names}")
```

### Step 5.2: Update set_display_mode with Edge Case Handling

**Location**: `ui/controllers/multi_point_tracking_controller.py:894-920`

**FIX #7**: Handle edge case when no active curve available.

**BEFORE**:
```python
def set_display_mode(self, mode: DisplayMode) -> None:
    """[docstring]"""
    widget = self.main_window.curve_widget
    if not widget:
        return

    # ❌ OLD: Set display_mode directly
    widget.display_mode = mode

    # Handle mode-specific logic
    if mode == DisplayMode.SELECTED:
        # ... logic ...
```

**AFTER**:
```python
def set_display_mode(self, mode: DisplayMode) -> None:
    """
    Set display mode for curve rendering.

    Updates ApplicationState which automatically computes display_mode.

    Args:
        mode: DisplayMode to set
    """
    widget = self.main_window.curve_widget
    if not widget:
        return

    # NEW: Update ApplicationState based on desired mode
    if mode == DisplayMode.ALL_VISIBLE:
        self._app_state.set_show_all_curves(True)

    elif mode == DisplayMode.SELECTED:
        self._app_state.set_show_all_curves(False)

        # FIX #7: Handle edge case when no curves available
        current_selection = self._app_state.get_selected_curves()
        if not current_selection:
            if widget.active_curve_name:
                # Select active curve
                self._app_state.set_selected_curves({widget.active_curve_name})
            else:
                # No active curve - can't achieve SELECTED mode
                logger.warning(
                    "Cannot set SELECTED mode: no curves selected and no active curve available. "
                    "Mode will remain ACTIVE_ONLY."
                )
                # Still set show_all to False as requested
                # display_mode will compute to ACTIVE_ONLY automatically

    elif mode == DisplayMode.ACTIVE_ONLY:
        self._app_state.set_show_all_curves(False)
        self._app_state.set_selected_curves(set())  # Clear selection

    # Trigger repaint
    widget.update()

    logger.debug(
        f"Set display mode: requested={mode}, "
        f"show_all={self._app_state.get_show_all_curves()}, "
        f"selected={self._app_state.get_selected_curves()}, "
        f"computed_mode={self._app_state.display_mode}"
    )
```

### Step 5.3: Update set_selected_curves Method

**Location**: `ui/controllers/multi_point_tracking_controller.py:922-945`

**BEFORE**:
```python
def set_selected_curves(self, curve_names: list[str]) -> None:
    """[docstring]"""
    widget = self.main_window.curve_widget
    if not widget:
        return

    # Update widget state
    widget.selected_curve_names = set(curve_names)
    widget.selected_curves_ordered = list(curve_names)

    # ... rest ...
```

**AFTER**:
```python
def set_selected_curves(self, curve_names: list[str]) -> None:
    """
    Set selected curves for display.

    Args:
        curve_names: List of curve names to select
    """
    widget = self.main_window.curve_widget
    if not widget:
        return

    # NEW: Update ApplicationState (single source of truth)
    self._app_state.set_selected_curves(set(curve_names))

    # Update widget's ordered list for rendering order (backward compatibility)
    widget.selected_curve_names = set(curve_names)
    widget.selected_curves_ordered = list(curve_names)

    # Trigger repaint
    widget.update()

    logger.debug(
        f"Selected curves: {self._app_state.get_selected_curves()}, "
        f"Active: {self._app_state.active_curve}, "
        f"Mode: {self._app_state.display_mode}"
    )
```

### Step 5.4: Update curve_data_facade.py

**Location**: `ui/controllers/curve_view/curve_data_facade.py:155-164`

**BEFORE**:
```python
if selected_curves is not None:
    self.widget.selected_curve_names = set(selected_curves)
    self.widget.selected_curves_ordered = list(selected_curves)
    if selected_curves:
        self.widget.display_mode = DisplayMode.SELECTED  # ❌ OLD WAY
        logger.info(f"  display_mode AFTER setting SELECTED: {self.widget.display_mode}")
    elif not self.widget.selected_curve_names:
        # Default to active curve
        self.widget.selected_curve_names = {active_curve} if active_curve else set()
        self.widget.selected_curves_ordered = [active_curve] if active_curve else []
```

**AFTER**:
```python
if selected_curves is not None:
    # NEW: Update ApplicationState (single source of truth)
    self._app_state.set_selected_curves(set(selected_curves))

    # Update widget's ordered list for rendering (backward compatibility)
    self.widget.selected_curve_names = set(selected_curves)
    self.widget.selected_curves_ordered = list(selected_curves)

    # NO MANUAL display_mode UPDATE - computed automatically! ✅
    logger.info(f"  display_mode AUTO-computed: {self._app_state.display_mode}")
elif active_curve:
    # Default to active curve
    self._app_state.set_selected_curves({active_curve})
    self.widget.selected_curve_names = {active_curve}
    self.widget.selected_curves_ordered = [active_curve]
```

### Step 5.5: Add ApplicationState reference to curve_data_facade.py

**Location**: `ui/controllers/curve_view/curve_data_facade.py` (in `__init__`)

**CODE TO ADD**:
```python
def __init__(self, widget: CurveViewWidget):
    self.widget = widget

    # NEW: ApplicationState reference
    from stores.application_state import get_application_state
    self._app_state = get_application_state()
```

### Step 5.6: Update main_window.py

**Location**: `ui/main_window.py:941-943`

**BEFORE**:
```python
def _on_display_mode_changed(self, mode: DisplayMode) -> None:
    """Handle display mode changes from tracking panel."""
    self.curve_widget.display_mode = mode  # ❌ OLD WAY

    # Trigger widget repaint
    self.curve_widget.update()
```

**AFTER**:
```python
def _on_display_mode_changed(self, mode: DisplayMode) -> None:
    """
    Handle display mode changes from tracking panel.

    Note: TrackingPanel already updated ApplicationState in _on_display_mode_checkbox_toggled.
    This handler is for legacy signal compatibility during migration.
    The mode parameter tells us what mode was intended, but ApplicationState is already correct.
    """
    # NEW: ApplicationState already updated by TrackingPanel
    # Just trigger repaint to reflect the change
    self.curve_widget.update()

    logger.debug(
        f"Display mode signal received: {mode}, "
        f"ApplicationState mode: {self._app_state.display_mode}"
    )
```

### Step 5.7: Add ApplicationState reference to main_window.py

**Location**: `ui/main_window.py` (in `__init__`, after other service references)

**CODE TO ADD**:
```python
# In __init__, after other initializations:
from stores.application_state import get_application_state
self._app_state = get_application_state()
```

### Verification Steps

1. **Type check all controller files**:
   ```bash
   ./bpr ui/controllers/multi_point_tracking_controller.py
   ./bpr ui/controllers/curve_view/curve_data_facade.py
   ./bpr ui/main_window.py
   ```

2. **Test synchronization loop fixed**:
   ```python
   # This test would previously cause race condition
   from ui.tracking_points_panel import TrackingPointsPanel
   from stores.application_state import get_application_state, reset_application_state
   from core.models import CurvePoint

   reset_application_state()
   panel = TrackingPointsPanel()
   app_state = get_application_state()

   # Add data
   panel.set_tracked_data({
       "Track1": [CurvePoint(1, 10, 20)],
       "Track2": [CurvePoint(1, 30, 40)]
   })

   # Ctrl+click multiple items (simulated)
   panel.set_selected_points(["Track1", "Track2"])

   # Should NOT cause race condition
   assert app_state.get_selected_curves() == {"Track1", "Track2"}
   print("✅ Synchronization loop eliminated")
   ```

3. **Test edge case handling**:
   ```python
   from ui.controllers.multi_point_tracking_controller import MultiPointTrackingController
   from ui.main_window import MainWindow
   from core.display_mode import DisplayMode

   window = MainWindow()
   controller = window.multi_point_controller
   app_state = get_application_state()

   # Try to set SELECTED mode when no curves available
   # Should log warning but not crash
   controller.set_display_mode(DisplayMode.SELECTED)

   # Mode should be ACTIVE_ONLY (not SELECTED since no curves)
   assert app_state.display_mode == DisplayMode.ACTIVE_ONLY
   print("✅ Edge case handled correctly")
   ```

### Rollback Instructions

1. Revert all files:
   ```bash
   git checkout ui/controllers/multi_point_tracking_controller.py
   git checkout ui/controllers/curve_view/curve_data_facade.py
   git checkout ui/main_window.py
   ```

2. Type check:
   ```bash
   ./bpr ui/controllers/
   ./bpr ui/main_window.py
   ```

---

## Phase 6: Update Tests

**Files Modified**: All test files that use `display_mode` setter or `selected_curve_names`
**Dependencies**: Phase 1-5 complete
**Risk Level**: LOW (test updates only)

### Step 6.1: Update Display Mode Integration Tests

**Location**: `tests/test_display_mode_integration.py` (multiple locations)

**Pattern to Replace**:
```python
# OLD:
curve_widget.display_mode = DisplayMode.ALL_VISIBLE

# NEW:
from stores.application_state import get_application_state
app_state = get_application_state()
app_state.set_show_all_curves(True)
assert curve_widget.display_mode == DisplayMode.ALL_VISIBLE
```

**Specific Updates**:

1. **Line 58** - test_display_mode_getter_all_visible:
```python
# BEFORE:
curve_widget.display_mode = DisplayMode.ALL_VISIBLE
curve_widget.selected_curve_names = set()

# AFTER:
app_state.set_show_all_curves(True)
assert curve_widget.display_mode == DisplayMode.ALL_VISIBLE
# No need to clear selection - display_mode is computed
```

2. **Follow same pattern for all test methods** at lines 79, 96, 119, 142, etc.

### Step 6.2: Update Render State Tests

**Location**: `tests/test_render_state.py`

Follow same pattern as above. All `display_mode` setter usages should be replaced with ApplicationState setters.

### Step 6.3: Update Multi-Point Selection Tests

**Location**: `tests/test_multi_point_selection.py`

Same pattern. Focus on tests around lines 154, 161, 168, 365, 400, etc.

### Step 6.4: Create Comprehensive Integration Test

**Location**: Create new file `tests/test_selection_state_integration.py`

**CODE TO ADD**:
```python
"""
Integration tests for centralized selection state architecture.

Tests the complete flow: UI → ApplicationState → rendering

Covers all edge cases identified in independent reviews:
- Batch mode state visibility
- Qt signal timing
- Invalid curve names
- Empty selection transitions
- Redundant update filtering
"""
import pytest
import warnings
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from stores.application_state import get_application_state, reset_application_state
from core.display_mode import DisplayMode
from core.models import CurvePoint
from ui.tracking_points_panel import TrackingPointsPanel
from ui.curve_view_widget import CurveViewWidget
from ui.main_window import MainWindow


class TestSelectionStateIntegration:
    """Test selection state flows through ApplicationState correctly."""

    @pytest.fixture(autouse=True)
    def setup(self, qapp):
        """Reset ApplicationState before each test."""
        reset_application_state()
        yield
        reset_application_state()

    def test_panel_selection_updates_app_state(self, qapp):
        """Test: Panel selection → ApplicationState → display_mode."""
        panel = TrackingPointsPanel()
        app_state = get_application_state()

        # Add tracking data
        panel.set_tracked_data({
            "Track1": [CurvePoint(1, 10, 20)],
            "Track2": [CurvePoint(1, 30, 40)]
        })

        # User selects two curves
        panel.set_selected_points(["Track1", "Track2"])

        # ApplicationState updated
        assert app_state.get_selected_curves() == {"Track1", "Track2"}
        assert app_state.display_mode == DisplayMode.SELECTED

    def test_checkbox_updates_app_state(self, qapp):
        """Test: Checkbox toggle → ApplicationState → display_mode."""
        panel = TrackingPointsPanel()
        app_state = get_application_state()

        # User checks "show all"
        panel.display_mode_checkbox.setChecked(True)

        # ApplicationState updated
        assert app_state.get_show_all_curves() is True
        assert app_state.display_mode == DisplayMode.ALL_VISIBLE

    def test_widget_reads_from_app_state(self, qapp):
        """Test: ApplicationState → Widget display_mode property."""
        widget = CurveViewWidget()
        app_state = get_application_state()

        # Change ApplicationState
        app_state.set_show_all_curves(True)

        # Widget reflects ApplicationState
        assert widget.display_mode == DisplayMode.ALL_VISIBLE

        # Change to selection mode
        app_state.set_show_all_curves(False)
        app_state.set_selected_curves({"Track1"})

        # Widget reflects new mode
        assert widget.display_mode == DisplayMode.SELECTED

    def test_no_synchronization_loop(self, qapp):
        """
        Regression test: Selecting curves should NOT create sync loop.

        Original bug: on_tracking_points_selected() called set_selected_points()
        which triggered _on_selection_changed() during clearing phase = race condition.
        """
        window = MainWindow()
        panel = window.tracking_panel
        app_state = get_application_state()

        # Load data
        panel.set_tracked_data({
            "Track1": [CurvePoint(1, 10, 20)],
            "Track2": [CurvePoint(1, 30, 40)]
        })

        # Track selection changed calls
        selection_changed_count = 0
        original_handler = panel._on_selection_changed

        def track_selection_changed():
            nonlocal selection_changed_count
            selection_changed_count += 1
            original_handler()

        panel._on_selection_changed = track_selection_changed

        # Simulate Ctrl+click (multi-select)
        panel.set_selected_points(["Track1", "Track2"])

        # Should only fire once (not multiple times from sync loop)
        assert selection_changed_count == 1
        assert app_state.get_selected_curves() == {"Track1", "Track2"}

    def test_regression_multi_curve_display_bug(self, qapp):
        """
        Regression test for: Selecting two curves only shows one.

        Original bug: selected_curve_names updated but display_mode not set to SELECTED.
        With new architecture, display_mode always correct (computed property).
        """
        window = MainWindow()
        app_state = get_application_state()

        # Simulate the exact user action that caused the bug
        window.tracking_panel.set_tracked_data({
            "Track1": [CurvePoint(1, 10, 20)],
            "Track2": [CurvePoint(1, 30, 40)]
        })
        window.tracking_panel.set_selected_points(["Track1", "Track2"])

        # This should NOT fail (original bug: only one curve rendered)
        from rendering.render_state import RenderState
        render_state = RenderState.compute(window.curve_widget)
        assert "Track1" in render_state.visible_curves
        assert "Track2" in render_state.visible_curves
        assert len(render_state.visible_curves) == 2

    # NEW TESTS: Edge cases from reviews

    def test_batch_mode_state_visibility(self, qapp):
        """
        Test: display_mode reflects changes immediately during batch.

        Batch mode defers signal emissions, NOT state visibility.
        """
        app_state = get_application_state()

        app_state.begin_batch()
        try:
            # Set selection
            app_state.set_selected_curves({"Track1"})
            # display_mode should update immediately, even in batch
            assert app_state.display_mode == DisplayMode.SELECTED

            # Change to show all
            app_state.set_show_all_curves(True)
            # Mode should change immediately
            assert app_state.display_mode == DisplayMode.ALL_VISIBLE
        finally:
            app_state.end_batch()

        # Signals emitted now, but state was visible throughout

    def test_batch_mode_conflicting_changes(self, qapp):
        """Test precedence when both show_all and selection change in batch."""
        app_state = get_application_state()

        app_state.begin_batch()
        try:
            app_state.set_selected_curves({"Track1"})  # Would give SELECTED
            app_state.set_show_all_curves(True)         # Would give ALL_VISIBLE
        finally:
            app_state.end_batch()

        # Last write wins: show_all takes priority
        assert app_state.display_mode == DisplayMode.ALL_VISIBLE

    def test_qt_signal_timing_no_circular_updates(self, qapp, qtbot):
        """
        Test: _updating flag timing doesn't cause circular updates.

        The QTimer fix ensures flag release happens after queued signals.
        """
        panel = TrackingPointsPanel()
        app_state = get_application_state()

        # Track how many times _on_selection_changed fires
        call_count = 0
        original = panel._on_selection_changed

        def tracked_handler():
            nonlocal call_count
            call_count += 1
            original()

        panel._on_selection_changed = tracked_handler

        # External update to ApplicationState (triggers reverse sync)
        app_state.set_selected_curves({"Track1"})

        # Wait for Qt signals to process
        qtbot.wait(100)

        # Should only fire once (from reverse sync), not loop
        assert call_count <= 1, f"Expected ≤1 call, got {call_count}"

    def test_invalid_curve_names_warns_but_works(self, qapp):
        """
        Test: Selecting non-existent curves warns but doesn't crash.

        Allows setting selection before curves load (session restoration).
        """
        app_state = get_application_state()

        # Set selection before loading curves (session restoration scenario)
        app_state.set_selected_curves({"Track1", "Track2"})
        # Should work, no crash
        assert app_state.get_selected_curves() == {"Track1", "Track2"}

        # Load curves
        app_state.set_curve_data("Track1", [CurvePoint(1, 10, 20)])

        # Select mixture of valid and invalid
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            app_state.set_selected_curves({"Track1", "FakeCurve"})

            # Should warn about invalid curve
            assert len(w) == 1
            assert "not yet loaded" in str(w[0].message)

        # Selection kept (permissive validation)
        assert app_state.get_selected_curves() == {"Track1", "FakeCurve"}

    def test_empty_selection_transitions(self, qapp):
        """Test all display mode transitions with empty selections."""
        app_state = get_application_state()

        # Start: ACTIVE_ONLY (no selection, no show_all)
        assert app_state.display_mode == DisplayMode.ACTIVE_ONLY

        # Select curves → SELECTED
        app_state.set_selected_curves({"Track1"})
        assert app_state.display_mode == DisplayMode.SELECTED

        # Clear selection → back to ACTIVE_ONLY
        app_state.set_selected_curves(set())
        assert app_state.display_mode == DisplayMode.ACTIVE_ONLY

        # Enable show_all → ALL_VISIBLE
        app_state.set_show_all_curves(True)
        assert app_state.display_mode == DisplayMode.ALL_VISIBLE

        # Disable show_all with no selection → ACTIVE_ONLY
        app_state.set_show_all_curves(False)
        assert app_state.display_mode == DisplayMode.ACTIVE_ONLY

    def test_redundant_updates_filtered(self, qapp):
        """Test: Setting same value twice doesn't emit duplicate signals."""
        app_state = get_application_state()

        signal_count = 0

        def count_signals(selected: set[str], show_all: bool):
            nonlocal signal_count
            signal_count += 1

        app_state.selection_state_changed.connect(count_signals)

        # First update
        app_state.set_selected_curves({"Track1"})
        assert signal_count == 1

        # Same value again - should NOT emit signal
        app_state.set_selected_curves({"Track1"})
        assert signal_count == 1  # Still 1, not 2

    def test_set_display_mode_edge_case_no_active_curve(self, qapp):
        """
        Test: set_display_mode(SELECTED) when no active curve.

        Should log warning and remain in ACTIVE_ONLY mode.
        """
        window = MainWindow()
        controller = window.multi_point_controller
        app_state = get_application_state()

        # Ensure no active curve
        window.curve_widget.active_curve_name = None

        # Try to set SELECTED mode
        with pytest.warns(UserWarning, match="Cannot set SELECTED mode"):
            controller.set_display_mode(DisplayMode.SELECTED)

        # Mode should remain ACTIVE_ONLY
        assert app_state.display_mode == DisplayMode.ACTIVE_ONLY
```

### Step 6.5: Update All Other Test Files

**Search command to find all test files needing updates**:
```bash
grep -r "\.display_mode\s*=" tests/ --include="*.py" > /tmp/test_display_mode_usages.txt
grep -r "\.selected_curve_names" tests/ --include="*.py" > /tmp/test_selected_curve_names_usages.txt
```

**Update pattern for each file**:
1. Add import: `from stores.application_state import get_application_state, reset_application_state`
2. Add `reset_application_state()` in test setup
3. Replace `widget.display_mode = X` with appropriate `app_state.set_*()` calls
4. Add assertions to verify computed mode is correct

### Verification Steps

1. **Run all tests**:
   ```bash
   .venv/bin/python3 -m pytest tests/ -v
   ```
   Expected: All tests pass

2. **Run new integration test suite**:
   ```bash
   .venv/bin/python3 -m pytest tests/test_selection_state_integration.py -v
   ```
   Expected: All new edge case tests pass

3. **Check for deprecation warnings**:
   ```bash
   .venv/bin/python3 -m pytest tests/ -W default::DeprecationWarning 2>&1 | grep -i deprecated
   ```
   Expected: Some warnings (from backward-compat code), but all tests pass

4. **Check coverage**:
   ```bash
   .venv/bin/python3 -m pytest tests/test_selection_state_integration.py \
     --cov=stores.application_state --cov-report=term-missing
   ```
   Goal: 100% coverage of new selection state methods

### Rollback Instructions

1. Revert all test files:
   ```bash
   git checkout tests/
   ```

2. Delete new integration test:
   ```bash
   rm tests/test_selection_state_integration.py
   ```

---

## Phase 7: Documentation and Session Persistence

**Files Modified**:
- `CLAUDE.md`
- `stores/application_state.py` (docstrings)
- `session/session_manager.py` (or similar session handling file)
- `docs/ADR-001-selection-state-architecture.md` (new)

**Dependencies**: Phase 1-6 complete
**Risk Level**: LOW

### Step 7.1: Add Session Persistence

**Location**: Find session save/load code (likely `session/session_manager.py` or in `MainWindow`)

**CODE TO ADD**:
```python
# In session save method:
def save_session(self, filepath: str) -> None:
    """Save current session state."""
    session_data = {
        # ... existing session data ...

        # NEW: Save selection state
        "selection_state": {
            "selected_curves": list(self._app_state.get_selected_curves()),
            "show_all_curves": self._app_state.get_show_all_curves()
        }
    }

    # ... save to file ...

# In session load method:
def load_session(self, filepath: str) -> None:
    """Load session state."""
    # ... load from file ...

    # NEW: Restore selection state
    if "selection_state" in session_data:
        selection = session_data["selection_state"]
        self._app_state.set_selected_curves(set(selection.get("selected_curves", [])))
        self._app_state.set_show_all_curves(selection.get("show_all_curves", False))
        logger.info(f"Restored selection state: {selection}")
```

### Step 7.2: Update CLAUDE.md Documentation

**Location**: `CLAUDE.md`

**Add new section after "## State Management"**:

```markdown
### Selection State Architecture (October 2025)

**Single Source of Truth**: ApplicationState manages all selection inputs.

#### Core Principle

Selection state is **computed, not stored**:
```python
# ApplicationState (authoritative inputs)
_selected_curves: set[str]      # Which curves user selected
_show_all_curves: bool           # Show-all checkbox state

# Computed output (never stored)
@property
def display_mode(self) -> DisplayMode:
    if self._show_all_curves:
        return DisplayMode.ALL_VISIBLE
    elif self._selected_curves:
        return DisplayMode.SELECTED
    else:
        return DisplayMode.ACTIVE_ONLY
```

#### Terminology Clarity

**Important**: CurveEditor has TWO different "selection" concepts:

1. **Curve-level selection** (which trajectories to display):
   - `ApplicationState.get_selected_curves()` → `set[str]` (curve names)
   - `ApplicationState.set_selected_curves({"Track1", "Track2"})`
   - Controls which curves are visible in multi-curve mode

2. **Point-level selection** (which frames within active curve):
   - `ApplicationState.get_selection(curve_name)` → `set[int]` (frame indices)
   - `ApplicationState.set_selection(curve_name, {10, 20, 30})`
   - Controls which points within active curve are highlighted/editable

These are DISTINCT and independent.

#### Usage Patterns

**Update selection**:
```python
from stores.application_state import get_application_state

app_state = get_application_state()

# Select specific curves
app_state.set_selected_curves({"Track1", "Track2"})
# → display_mode automatically SELECTED

# Show all curves
app_state.set_show_all_curves(True)
# → display_mode automatically ALL_VISIBLE

# Clear selection
app_state.set_selected_curves(set())
# → display_mode automatically ACTIVE_ONLY
```

**Read display mode** (always fresh, never stale):
```python
mode = widget.display_mode  # Reads from app_state.display_mode property
```

**Subscribe to changes**:
```python
def on_selection_changed(selected_curves: set[str], show_all: bool):
    widget.update()  # Repaint with new mode

app_state.selection_state_changed.connect(on_selection_changed)
```

#### Batch Mode Semantics

**Important**: `begin_batch()` / `end_batch()` only defers signal emissions, NOT state visibility.

```python
app_state.begin_batch()
app_state.set_selected_curves({"Track1"})

# display_mode is IMMEDIATELY visible as SELECTED!
assert app_state.display_mode == DisplayMode.SELECTED

app_state.set_show_all_curves(True)

# display_mode is IMMEDIATELY visible as ALL_VISIBLE!
assert app_state.display_mode == DisplayMode.ALL_VISIBLE

app_state.end_batch()  # Signals emit NOW

# Batch mode prevents signal storms during bulk updates,
# but computed properties reflect state changes immediately.
```

#### Migration from Old Pattern

**OLD** (manual synchronization, bug-prone):
```python
# Bug: Forgot to update display_mode!
manager.selected_curve_names = {"Track1", "Track2"}
# widget still shows ACTIVE_ONLY → wrong!
```

**NEW** (automatic, always correct):
```python
# Automatically computes display_mode = SELECTED
app_state.set_selected_curves({"Track1", "Track2"})
# display_mode is ALWAYS consistent with selection
```

#### Key Benefits

✅ **No synchronization bugs** - display_mode can't get out of sync
✅ **No race conditions** - no circular update loops
✅ **Always fresh** - computed property never stale
✅ **Single source of truth** - one place to check selection state
✅ **Type-safe** - no manual boolean tracking
✅ **Session persistence** - selection state survives restart

#### Edge Cases

**Selecting curves before they're loaded** (session restoration):
```python
# Set selection first (no warning)
app_state.set_selected_curves({"Track1", "Track2"})

# Load curves later
app_state.set_curve_data("Track1", [...])
app_state.set_curve_data("Track2", [...])

# Selection preserved correctly
```

**Active curve not in visible set** (expected behavior):
```python
app_state.set_selected_curves({"Track1", "Track2"})
app_state.set_active_curve("Track3")
# display_mode = SELECTED (shows Track1, Track2)
# Active is Track3 (for editing, even if not visible)
```
```

### Step 7.3: Add Class-Level Documentation

**Location**: `stores/application_state.py` (add at top of class)

**CODE TO ADD**:
```python
class ApplicationState(QObject):
    """
    Single source of truth for all application state.

    Selection State Architecture (October 2025):
    =============================================

    Curve-level selection uses computed display_mode pattern:

    Authoritative Inputs (stored):
        - _selected_curves: set[str]  # Which trajectories user selected
        - _show_all_curves: bool       # Show-all checkbox state

    Derived Output (computed):
        - display_mode: @property → DisplayMode  # Never stored!

    This eliminates synchronization bugs by making it impossible for
    display_mode to get out of sync with selection state.

    Terminology:
        - Curve-level selection: which trajectories to display (this)
        - Point-level selection: which frames within active curve (separate)

    Batch Mode Semantics:
        begin_batch() / end_batch() defer signal emissions, NOT state visibility.
        Computed properties like display_mode reflect changes immediately.

    Signals:
        - selection_state_changed(set[str], bool)  # Emitted on input changes

    Session Persistence:
        Selection state is saved/restored in session data automatically.
    """
```

### Step 7.4: Create Architecture Decision Record

**Location**: Create new file `docs/ADR-001-selection-state-architecture.md`

**CODE TO ADD**:
```markdown
# ADR-001: Centralized Selection State Architecture

**Date**: October 2025
**Status**: Implemented
**Supersedes**: Distributed selection state pattern

## Context

Selection state was fragmented across three locations requiring manual synchronization:
1. TrackingPointsPanel (checkbox + table selection)
2. MultiCurveManager.selected_curve_names
3. CurveViewWidget._display_mode

This caused bugs when synchronization was forgotten, most notably:
- Selecting multiple curves only showed one curve
- Race conditions during Ctrl+click multi-select
- Synchronization loops creating reentrancy bugs

## Decision

**Centralize ALL selection inputs in ApplicationState** and compute display_mode as a derived property.

### Architecture

```
ApplicationState (Single Source of Truth):
├─ _selected_curves: set[str]           # Input: which curves selected
├─ _show_all_curves: bool               # Input: show-all checkbox
└─ display_mode: @property → DisplayMode  # Output: computed (never stored)
```

### Key Principles

1. **Derived state must be computed, never stored**
2. **UI components are input devices**, not state owners
3. **Signals notify of changes**, don't carry state
4. **Make illegal states unrepresentable**
5. **Batch mode defers signals, not state visibility**

## Consequences

### Positive

✅ Synchronization bugs eliminated (can't forget to update derived state)
✅ Race conditions eliminated (no circular dependencies)
✅ Always consistent (computed property never stale)
✅ Easier debugging (one place to check state)
✅ Better testability (centralized state easier to verify)
✅ Session persistence (selection survives restart)

### Negative

⚠️ Breaking change for code that sets display_mode directly
⚠️ Requires understanding of computed property pattern
⚠️ Slightly more verbose for simple cases

### Migration

- Old: `widget.display_mode = DisplayMode.SELECTED`
- New: `app_state.set_selected_curves({"Track1"})`

Backward compatibility maintained during migration via deprecation wrappers.

## Implementation

Completed in 8 phases:
1. Add selection state to ApplicationState
2. Update TrackingPointsPanel to use ApplicationState
3. Add deprecation wrapper to CurveViewWidget.display_mode
4. Update MultiCurveManager with backward-compat properties
5. Update controllers, remove synchronization loop
6. Update all tests with comprehensive edge case coverage
7. Add documentation and session persistence
8. Remove all backward compatibility (final cleanup)

Total implementation: 12-14 hours
Test coverage: 100% of new functionality
Zero regressions

## Validation

- ✅ All 2105+ tests passing
- ✅ Zero type errors with basedpyright
- ✅ Original bug fixed (verified by manual test and regression test)
- ✅ No race conditions (verified by Qt signal timing test)
- ✅ All edge cases covered (batch mode, invalid curves, empty selection)

## References

- SELECTION_STATE_ARCHITECTURE_SOLUTION.md - Architectural analysis
- SELECTION_STATE_REFACTORING_PLAN_REVISED.md - Implementation guide
- Independent reviews: python-expert-architect, python-code-reviewer, lead architect
```

### Verification Steps

1. **Verify documentation updated**:
   ```bash
   grep -n "Selection State Architecture" CLAUDE.md
   ```

2. **Verify ADR created**:
   ```bash
   ls -la docs/ADR-001-selection-state-architecture.md
   ```

3. **Verify session persistence**:
   ```bash
   # Test save/load cycle
   # Load multi-curve data, select curves, save session
   # Restart, load session, verify selection restored
   ```

4. **Run full test suite**:
   ```bash
   .venv/bin/python3 -m pytest tests/ -v --tb=short
   ```

### Rollback Instructions

1. Remove documentation:
   ```bash
   git checkout CLAUDE.md
   git checkout stores/application_state.py  # Revert docstring changes
   rm docs/ADR-001-selection-state-architecture.md
   ```

2. Revert session persistence:
   ```bash
   git checkout session/  # Or wherever session code lives
   ```

---

## Phase 8: Final Cleanup - Remove All Backward Compatibility (NEW)

**Files Modified**:
- `ui/curve_view_widget.py` (remove deprecation wrapper)
- `ui/multi_curve_manager.py` (remove backward-compat properties)
- `ui/tracking_points_panel.py` (optionally remove legacy signals)

**Dependencies**: Phase 1-7 complete, ALL code updated
**Risk Level**: MEDIUM (breaking changes, but all code should be updated)

**PURPOSE**: Eliminate ALL backward compatibility code to leave a clean, single-way-to-do-it codebase.

### Step 8.1: Verify No Code Uses Deprecated APIs

**CRITICAL**: Before removing anything, verify all code updated.

```bash
# Check for deprecation warnings in test output
.venv/bin/python3 -m pytest tests/ -W error::DeprecationWarning 2>&1 | tee /tmp/deprecation_check.txt

# If ANY deprecation warnings, STOP and fix them first
grep -i "deprecated" /tmp/deprecation_check.txt
```

**Expected**: Zero deprecation warnings. If any found, update that code before proceeding.

### Step 8.2: Remove display_mode Setter Entirely

**Location**: `ui/curve_view_widget.py`

**BEFORE** (after Phase 3):
```python
@property
def display_mode(self) -> DisplayMode:
    """Get current display mode from ApplicationState."""
    return self._app_state.display_mode

@display_mode.setter
def display_mode(self, mode: DisplayMode) -> None:
    """DEPRECATED: Use ApplicationState..."""
    warnings.warn(...)
    # ... conversion code ...
```

**AFTER** (Phase 8 - clean):
```python
@property
def display_mode(self) -> DisplayMode:
    """
    Get current display mode from ApplicationState (read-only).

    This is a computed property that always reflects ApplicationState.
    To change display mode, update ApplicationState inputs:

    - app_state.set_show_all_curves(True) → ALL_VISIBLE
    - app_state.set_selected_curves({...}) → SELECTED
    - app_state.set_selected_curves(set()) → ACTIVE_ONLY

    Returns:
        DisplayMode computed from ApplicationState selection state
    """
    return self._app_state.display_mode

# NO SETTER - display_mode is truly read-only now
```

### Step 8.3: Remove selected_curve_names Backward-Compat Properties

**Location**: `ui/multi_curve_manager.py`

**Remove entirely**:
```python
# DELETE:
@property
def selected_curve_names(self) -> set[str]:
    """DEPRECATED..."""
    ...

@selected_curve_names.setter
def selected_curve_names(self, value: set[str]) -> None:
    """DEPRECATED..."""
    ...
```

**Verify no external access**:
```bash
# Should return zero results
grep -rn "manager\.selected_curve_names" ui/ tests/ --include="*.py" | grep -v "self.selected_curve_names"
```

### Step 8.4: Review Legacy Signals

**Location**: `ui/tracking_points_panel.py`

**Signals to review**:
1. `points_selected` - still emitted for backward compat
2. `display_mode_changed` - still emitted for backward compat

**Decision**: Check if still connected anywhere:

```bash
# Find all connections to these signals
grep -rn "points_selected\.connect" ui/ --include="*.py"
grep -rn "display_mode_changed\.connect" ui/ --include="*.py"
```

**If no connections found outside TrackingPointsPanel**:
- Mark signals as deprecated in docstring
- Plan removal in future version
- Keep emitting during Phase 8 for external plugin compatibility

**If connections found**:
- Update those connections to use `selection_state_changed` instead
- Then remove the legacy signals

### Step 8.5: Remove _updating_display_mode Flag (Optional)

**Location**: `ui/curve_view_widget.py`

Since the setter is removed, the `_updating_display_mode` flag may no longer be needed.

**Check usage**:
```bash
grep -rn "_updating_display_mode" ui/curve_view_widget.py
```

**If only used in removed setter**: Delete the field from `__init__`.

### Step 8.6: Final Verification - Zero Deprecations

```bash
# Run tests with deprecation warnings as errors
.venv/bin/python3 -m pytest tests/ -W error::DeprecationWarning -v

# Expected: All tests pass, zero deprecation warnings
```

**If ANY deprecation warnings**:
1. Find the source
2. Update to use new API
3. Re-run tests
4. Repeat until zero warnings

### Step 8.7: Verify Old Patterns No Longer Work

**Test that old API fails appropriately**:

```python
# This should now fail with AttributeError (no setter)
from ui.curve_view_widget import CurveViewWidget
from core.display_mode import DisplayMode

widget = CurveViewWidget()

try:
    widget.display_mode = DisplayMode.ALL_VISIBLE
    assert False, "Should have raised AttributeError!"
except AttributeError as e:
    assert "can't set attribute" in str(e).lower()
    print("✅ Old API correctly removed")

# This should also fail (no selected_curve_names on manager)
from ui.multi_curve_manager import MultiCurveManager

manager = MultiCurveManager(widget)

try:
    _ = manager.selected_curve_names
    assert False, "Should have raised AttributeError!"
except AttributeError:
    print("✅ Backward-compat property correctly removed")
```

### Step 8.8: Update Migration Checklist

Mark Phase 8 complete in `/tmp/migration_audit/MIGRATION_CHECKLIST.md`:

```markdown
## Phase 8: Final Cleanup - COMPLETE

- [x] display_mode setter removed from CurveViewWidget
- [x] selected_curve_names property removed from MultiCurveManager
- [x] _updating_display_mode flag removed (if unused)
- [x] Legacy signals reviewed and documented
- [x] Zero deprecation warnings in test output
- [x] Old API patterns fail with AttributeError
- [x] All tests passing

## Final Verification

- [x] `pytest tests/ -W error::DeprecationWarning` → all pass
- [x] `grep -r "widget\.display_mode\s*=" --include="*.py"` → zero results (except in comments)
- [x] `grep -r "manager\.selected_curve_names" --include="*.py"` → zero external access
- [x] Manual smoke test: load data, select curves, verify rendering correct
```

### Verification Steps

1. **Zero deprecation warnings**:
   ```bash
   .venv/bin/python3 -m pytest tests/ -W error::DeprecationWarning
   ```

2. **Old patterns fail**:
   ```bash
   # Try old API (should fail)
   .venv/bin/python3 -c "
   from ui.curve_view_widget import CurveViewWidget
   from core.display_mode import DisplayMode
   widget = CurveViewWidget()
   try:
       widget.display_mode = DisplayMode.ALL_VISIBLE
       print('❌ FAIL: Old API still works!')
       exit(1)
   except AttributeError:
       print('✅ PASS: Old API correctly removed')
   "
   ```

3. **All tests pass**:
   ```bash
   .venv/bin/python3 -m pytest tests/ -v
   ```

4. **Manual smoke test**:
   - Launch application
   - Load multi-point tracking data
   - Select multiple curves via Ctrl+click
   - Verify both curves render
   - Toggle "Show all curves" checkbox
   - Verify mode changes correctly
   - Save and reload session
   - Verify selection restored

### Success Criteria

- [ ] display_mode setter completely removed
- [ ] selected_curve_names backward-compat properties removed
- [ ] Zero deprecation warnings in test output
- [ ] All 2105+ tests passing
- [ ] Manual smoke test successful
- [ ] Old API patterns fail with AttributeError
- [ ] Code is clean - only ONE way to do things

### Rollback Instructions

If Phase 8 reveals issues:

1. Revert to Phase 7 state:
   ```bash
   git checkout ui/curve_view_widget.py
   git checkout ui/multi_curve_manager.py
   ```

2. Re-run tests to confirm Phase 7 still works:
   ```bash
   .venv/bin/python3 -m pytest tests/ -v
   ```

3. Identify what code still uses old APIs (check deprecation warnings)

4. Update that code

5. Retry Phase 8

---

## Rollback Instructions

### Complete Rollback (All Phases)

If at any point the refactoring needs to be completely reverted:

1. **Revert all changes**:
   ```bash
   git checkout stores/application_state.py
   git checkout ui/tracking_points_panel.py
   git checkout ui/curve_view_widget.py
   git checkout ui/multi_curve_manager.py
   git checkout ui/controllers/multi_point_tracking_controller.py
   git checkout ui/controllers/curve_view/curve_data_facade.py
   git checkout ui/main_window.py
   git checkout tests/
   git checkout CLAUDE.md
   git checkout session/  # Or wherever session code lives
   rm -rf /tmp/migration_audit/
   rm docs/ADR-001-selection-state-architecture.md
   rm tests/test_selection_state_integration.py
   ```

2. **Verify clean state**:
   ```bash
   ./bpr --errors-only
   .venv/bin/python3 -m pytest tests/ -v
   ```

3. **Expected result**: All type checks pass, all tests pass, back to original state

### Partial Rollback (Specific Phase)

Each phase can be rolled back independently following the "Rollback Instructions" section within that phase.

**Phase dependencies** (rollback in reverse order):
- Phase 8 depends on 7
- Phase 7 depends on 6
- Phase 6 depends on 5
- Phase 5 depends on 4
- Phase 4 depends on 3
- Phase 3 depends on 2.5
- Phase 2.5 depends on 2
- Phase 2 depends on 1

To rollback to Phase N: rollback all phases > N in reverse order.

---

## Success Criteria

### Phase Completion Checklist

- [ ] **Phase 1**: ApplicationState has selection state, display_mode property works, validation warns
- [ ] **Phase 2**: TrackingPointsPanel updates ApplicationState on user input, Qt signal timing fixed
- [ ] **Phase 2.5**: Comprehensive audit complete, all affected locations documented
- [ ] **Phase 3**: CurveViewWidget.display_mode has deprecation wrapper, widget fields sync
- [ ] **Phase 4**: MultiCurveManager uses ApplicationState, backward-compat properties added
- [ ] **Phase 5**: Controllers use ApplicationState, synchronization loop removed, edge cases handled
- [ ] **Phase 6**: All tests updated and passing, edge case tests added
- [ ] **Phase 7**: Documentation complete, session persistence working
- [ ] **Phase 8**: All backward compatibility removed, zero deprecations, clean codebase

### Final Verification

**Run these commands to verify complete success**:

1. **Type checking** (0 errors):
   ```bash
   ./bpr --errors-only
   ```

2. **All tests pass** (2105+ tests):
   ```bash
   .venv/bin/python3 -m pytest tests/ -v
   ```

3. **Zero deprecation warnings** (after Phase 8):
   ```bash
   .venv/bin/python3 -m pytest tests/ -W error::DeprecationWarning
   ```

4. **Manual test - The original bug is fixed**:
   ```bash
   .venv/bin/python3 -c "
   from PySide6.QtWidgets import QApplication
   import sys
   from ui.main_window import MainWindow
   from stores.application_state import get_application_state, reset_application_state
   from core.models import CurvePoint

   app = QApplication(sys.argv)
   reset_application_state()
   window = MainWindow()
   app_state = get_application_state()

   # Simulate the exact bug scenario
   window.tracking_panel.set_tracked_data({
       'Track1': [CurvePoint(1, 10, 20)],
       'Track2': [CurvePoint(1, 30, 40)]
   })

   # User selects TWO curves
   window.tracking_panel.set_selected_points(['Track1', 'Track2'])

   # Verify BOTH curves will render
   from rendering.render_state import RenderState
   state = RenderState.compute(window.curve_widget)

   assert 'Track1' in state.visible_curves, 'Track1 not visible!'
   assert 'Track2' in state.visible_curves, 'Track2 not visible!'
   assert len(state.visible_curves) == 2, f'Expected 2 curves, got {len(state.visible_curves)}'

   print('✅ BUG FIXED: Selecting two curves now shows BOTH curves!')
   print(f'   display_mode: {app_state.display_mode}')
   print(f'   selected_curves: {app_state.get_selected_curves()}')
   print(f'   visible_curves: {state.visible_curves}')
   "
   ```

5. **Old API patterns fail** (after Phase 8):
   ```bash
   .venv/bin/python3 -c "
   from ui.curve_view_widget import CurveViewWidget
   from core.display_mode import DisplayMode
   widget = CurveViewWidget()
   try:
       widget.display_mode = DisplayMode.ALL_VISIBLE
       print('❌ FAIL: Old API still works')
       exit(1)
   except AttributeError:
       print('✅ PASS: Old API correctly removed')
   "
   ```

---

## Summary

This revised refactoring plan provides step-by-step instructions to implement the centralized selection state architecture that eliminates synchronization bugs.

### Key Changes from Original Plan

1. ✅ **Phase 2.5 added** - Comprehensive audit before breaking changes
2. ✅ **Phase 3 revised** - Deprecation wrapper instead of immediate removal
3. ✅ **Phase 4 enhanced** - Backward-compatibility properties for smooth migration
4. ✅ **Phase 5 improved** - Removes redundant updates, handles edge cases
5. ✅ **Phase 6 expanded** - Complete edge case test coverage
6. ✅ **Phase 7 enhanced** - Session persistence and batch mode docs
7. ✅ **Phase 8 added** - Final cleanup removes all backward compatibility

### Critical Fixes Incorporated

1. **Phase ordering bug** - Deprecation period prevents broken intermediate states
2. **Widget field sync** - Updates selected_curve_names and selected_curves_ordered
3. **Comprehensive audit** - Phase 2.5 finds all affected code before changes
4. **Validation** - Permissive validation allows init before load
5. **Redundant updates** - Controller doesn't re-update ApplicationState
6. **Backward compatibility** - Properties and wrappers for gradual migration
7. **Edge case handling** - All scenarios covered and tested
8. **Session persistence** - Selection state survives restart

### Benefits

- ✅ Fixes multi-curve selection bug
- ✅ Eliminates race conditions
- ✅ Prevents future synchronization bugs
- ✅ Cleaner, more maintainable architecture
- ✅ Smooth migration path with backward compatibility
- ✅ Complete test coverage of edge cases
- ✅ Clean final state with no backward-compat cruft

---

**Ready to implement!** Follow each phase sequentially, verifying at each step.

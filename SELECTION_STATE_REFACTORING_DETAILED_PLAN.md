# Selection State Refactoring - Detailed Implementation Plan

**Date**: October 2025
**Status**: Ready for Implementation
**Estimated Time**: 6-8 hours
**Based On**: SELECTION_STATE_ARCHITECTURE_SOLUTION.md

---

## Table of Contents

1. [Overview](#overview)
2. [Phase 1: Add Selection State to ApplicationState](#phase-1-add-selection-state-to-applicationstate)
3. [Phase 2: Update TrackingPointsPanel](#phase-2-update-trackingpointspanel)
4. [Phase 3: Update CurveViewWidget](#phase-3-update-curveviewwidget)
5. [Phase 4: Update MultiCurveManager](#phase-4-update-multicurvemanager)
6. [Phase 5: Update Controllers](#phase-5-update-controllers)
7. [Phase 6: Update Tests](#phase-6-update-tests)
8. [Phase 7: Cleanup and Documentation](#phase-7-cleanup-and-documentation)
9. [Rollback Instructions](#rollback-instructions)

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

---

## Phase 1: Add Selection State to ApplicationState

**Estimated Time**: 2 hours
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
    self._selection: dict[str, set[int]] = {}  # Point-level selection
    self._current_frame: int = 1
    self._view_state: ViewState = ViewState()

    # NEW: Curve-level selection state (which trajectories to display)
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
    selection_changed: Signal = Signal(str, set)
    active_curve_changed: Signal = Signal(str)
    frame_changed: Signal = Signal(int)
    view_changed: Signal = Signal()
    curve_visibility_changed: Signal = Signal(str, bool)

    # NEW: Curve-level selection state changed (selected_curves, show_all)
    selection_state_changed: Signal = Signal(set, bool)
```

### Step 1.3: Add Getter/Setter Methods

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

    Returns:
        Set of selected curve names (copy for safety)
    """
    self._assert_main_thread()
    return self._selected_curves.copy()

def set_selected_curves(self, curve_names: set[str]) -> None:
    """
    Set which curves are selected for display.

    Automatically updates derived display_mode property via signal.

    Args:
        curve_names: Set of curve names to select
    """
    self._assert_main_thread()
    new_selection = curve_names.copy()

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
    """
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
   from stores.application_state import get_application_state
   from core.display_mode import DisplayMode

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

3. **Test signal emission**:
   ```python
   # In Python shell or test
   from stores.application_state import get_application_state

   app_state = get_application_state()

   received = []
   app_state.selection_state_changed.connect(lambda s, a: received.append((s, a)))

   app_state.set_selected_curves({'curve1'})
   assert len(received) == 1
   assert received[0] == ({'curve1'}, False)
   ```

### Rollback Instructions

If this phase fails:
1. Remove the added code (fields, signal, methods, property, import)
2. Run: `git checkout stores/application_state.py`
3. Run type checker to confirm: `./bpr stores/application_state.py`

---

## Phase 2: Update TrackingPointsPanel

**Estimated Time**: 1.5 hours
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

### Step 2.4: Add Reverse Sync Handler

**Location**: `ui/tracking_points_panel.py` (add new method after `_on_display_mode_checkbox_toggled`)

**CODE TO ADD**:
```python
def _on_app_state_changed(self, selected_curves: set[str], show_all: bool) -> None:
    """
    Sync UI when ApplicationState changes (reverse flow).

    Handles external changes to selection state (e.g., from other UI or API).
    Uses _updating flag to prevent circular updates.

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
        self._updating = False
```

### Verification Steps

1. **Type check**:
   ```bash
   ./bpr ui/tracking_points_panel.py
   ```

2. **Manual test - Selection updates ApplicationState**:
   ```python
   from ui.tracking_points_panel import TrackingPointsPanel
   from stores.application_state import get_application_state
   from PySide6.QtWidgets import QApplication
   import sys

   app = QApplication(sys.argv)
   panel = TrackingPointsPanel()
   app_state = get_application_state()

   # Simulate adding tracking points
   panel.set_tracked_data({
       "Track1": [...],
       "Track2": [...]
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

## Phase 3: Update CurveViewWidget

**Estimated Time**: 1 hour
**Files Modified**: `ui/curve_view_widget.py`
**Dependencies**: Phase 1 complete
**Risk Level**: MEDIUM (breaking change for code that sets display_mode)

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

### Step 3.2: Convert display_mode to Read-Only Property

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
        >>> app_state.set_show_all_curves(True)
        >>> widget.display_mode
        <DisplayMode.ALL_VISIBLE: 1>

        >>> app_state.set_selected_curves({"Track1", "Track2"})
        >>> app_state.set_show_all_curves(False)
        >>> widget.display_mode
        <DisplayMode.SELECTED: 2>
    """
    return self._app_state.display_mode

# NO SETTER - display_mode is read-only, computed from ApplicationState
# To change display mode, update ApplicationState:
#   app_state.set_show_all_curves(True)  # → ALL_VISIBLE
#   app_state.set_selected_curves({...}) # → SELECTED
#   app_state.set_selected_curves(set()) # → ACTIVE_ONLY
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

### Step 3.4: Add Selection State Change Handler

**Location**: `ui/curve_view_widget.py` (add new method around line 1350, near other event handlers)

**CODE TO ADD**:
```python
def _on_selection_state_changed(self, selected_curves: set[str], show_all: bool) -> None:
    """
    Repaint when ApplicationState selection changes.

    Args:
        selected_curves: Selected curve names (not used, just triggers repaint)
        show_all: Show-all mode (not used, just triggers repaint)
    """
    # display_mode property automatically reflects new state
    # Just trigger repaint to show updated visualization
    self.update()
```

### ⚠️ BREAKING CHANGE WARNING

After this phase, any code that tries to SET `display_mode` will fail at runtime:

```python
# This will now FAIL (no setter):
widget.display_mode = DisplayMode.ALL_VISIBLE  # AttributeError!

# Use ApplicationState instead:
app_state.set_show_all_curves(True)  # Correct way
```

**Search for all setter usages** (already done above - see search results). These will need updating in Phase 5.

### Verification Steps

1. **Type check**:
   ```bash
   ./bpr ui/curve_view_widget.py
   ```

2. **Test read-only property**:
   ```python
   from ui.curve_view_widget import CurveViewWidget
   from stores.application_state import get_application_state
   from core.display_mode import DisplayMode

   widget = CurveViewWidget()
   app_state = get_application_state()

   # Change ApplicationState
   app_state.set_show_all_curves(True)

   # Widget property reflects ApplicationState
   assert widget.display_mode == DisplayMode.ALL_VISIBLE
   print("✅ Widget reads display_mode from ApplicationState")

   # Try to set (should fail)
   try:
       widget.display_mode = DisplayMode.SELECTED
       assert False, "Should have raised AttributeError"
   except AttributeError:
       print("✅ display_mode setter correctly removed")
   ```

3. **Test repaint on changes**:
   ```python
   # Track repaint calls
   repaint_count = 0
   original_update = widget.update
   def track_update():
       nonlocal repaint_count
       repaint_count += 1
       original_update()
   widget.update = track_update

   # Change selection state
   app_state.set_selected_curves({"Track1"})

   # Should have triggered repaint
   assert repaint_count > 0
   print("✅ Widget repaints on selection state changes")
   ```

### Rollback Instructions

1. Revert: `git checkout ui/curve_view_widget.py`
2. Type check: `./bpr ui/curve_view_widget.py`

---

## Phase 4: Update MultiCurveManager

**Estimated Time**: 1 hour
**Files Modified**: `ui/multi_curve_manager.py`
**Dependencies**: Phase 1 complete
**Risk Level**: LOW (simplification only)

### Step 4.1: Remove selected_curve_names Field

**Location**: `ui/multi_curve_manager.py:47-48`

**BEFORE**:
```python
# NEW: Track selected curves for multi-curve display
self.selected_curve_names: set[str] = set()
```

**AFTER**:
```python
# REMOVED: selected_curve_names now in ApplicationState
# Access via: self._app_state.get_selected_curves()
```

### Step 4.2: Update set_curves_data Method

**Location**: `ui/multi_curve_manager.py:76-135`

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
    logger.debug(f"Set {len(curves)} curves in ApplicationState, active: {self._app_state.active_curve}")
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
   from stores.application_state import get_application_state
   from core.display_mode import DisplayMode

   widget = CurveViewWidget()
   manager = MultiCurveManager(widget)
   app_state = get_application_state()

   # Set curves with selection
   manager.set_curves_data(
       {"curve1": [...], "curve2": [...]},
       selected_curves=["curve1", "curve2"]
   )

   # ApplicationState updated
   assert app_state.get_selected_curves() == {"curve1", "curve2"}
   assert app_state.display_mode == DisplayMode.SELECTED
   print("✅ Manager updates ApplicationState correctly")
   ```

3. **Verify no local selection state**:
   ```python
   # Manager should not have selected_curve_names attribute
   assert not hasattr(manager, 'selected_curve_names')
   print("✅ Manager has no local selection state")
   ```

### Rollback Instructions

1. Revert: `git checkout ui/multi_curve_manager.py`
2. Type check: `./bpr ui/multi_curve_manager.py`

---

## Phase 5: Update Controllers

**Estimated Time**: 1 hour
**Files Modified**:
- `ui/controllers/multi_point_tracking_controller.py`
- `ui/controllers/curve_view/curve_data_facade.py`
- `ui/main_window.py`

**Dependencies**: Phase 1-4 complete
**Risk Level**: HIGH (fixes synchronization loop bug)

### Step 5.1: Remove Synchronization Loop

**Location**: `ui/controllers/multi_point_tracking_controller.py:342-377`

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

    The panel has already updated its UI and emitted this signal.
    We just need to propagate to ApplicationState and update displays.
    NO need to sync back to panel - that creates circular dependency!

    Args:
        point_names: List of selected point names (curve names/trajectories)
    """
    # Set the last selected point as the active timeline point
    self.main_window.active_timeline_point = point_names[-1] if point_names else None

    # ✅ REMOVED synchronization loop (panel already has correct selection)
    # The panel emitted this signal, so it already has the right selection.
    # Re-setting it would trigger _on_selection_changed again = race condition!

    # NEW: Update ApplicationState directly (single source of truth)
    self._app_state.set_selected_curves(set(point_names))

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

### Step 5.2: Update set_display_mode Method

**Location**: `ui/controllers/multi_point_tracking_controller.py:894-920`

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
        # Ensure something is selected
        if not self._app_state.get_selected_curves() and widget.active_curve_name:
            self._app_state.set_selected_curves({widget.active_curve_name})
    elif mode == DisplayMode.ACTIVE_ONLY:
        self._app_state.set_show_all_curves(False)
        self._app_state.set_selected_curves(set())  # Clear selection

    # Trigger repaint
    widget.update()

    logger.debug(
        f"Set display mode: {mode}, "
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
   from stores.application_state import get_application_state

   panel = TrackingPointsPanel()
   app_state = get_application_state()

   # Ctrl+click multiple items
   panel.set_selected_points(["Track1", "Track2"])

   # Should NOT re-trigger set_selected_points
   # (previously caused race condition)
   assert app_state.get_selected_curves() == {"Track1", "Track2"}
   print("✅ Synchronization loop eliminated")
   ```

3. **Test display_mode updates via ApplicationState**:
   ```python
   from ui.controllers.multi_point_tracking_controller import MultiPointTrackingController
   from core.display_mode import DisplayMode

   controller = MultiPointTrackingController(main_window)
   app_state = get_application_state()

   # Set mode via controller
   controller.set_display_mode(DisplayMode.ALL_VISIBLE)

   # ApplicationState updated correctly
   assert app_state.get_show_all_curves() is True
   assert app_state.display_mode == DisplayMode.ALL_VISIBLE
   print("✅ Controller updates ApplicationState correctly")
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

**Estimated Time**: 1.5 hours
**Files Modified**: All test files that use `display_mode` setter
**Dependencies**: Phase 1-5 complete
**Risk Level**: LOW (test updates only)

### Step 6.1: Update Display Mode Integration Tests

**Location**: `tests/test_display_mode_integration.py` (multiple locations)

**Pattern to Replace**:
```python
# OLD:
curve_widget.display_mode = DisplayMode.ALL_VISIBLE

# NEW:
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

2. **Line 79, 96, 119, 142, etc.** - Follow same pattern for all test methods

### Step 6.2: Update Render State Tests

**Location**: `tests/test_render_state.py`

Follow same pattern as above. All `display_mode` setter usages should be replaced with ApplicationState setters.

### Step 6.3: Update Multi-Point Selection Tests

**Location**: `tests/test_multi_point_selection.py`

Same pattern. Focus on tests around lines 154, 161, 168, 365, 400, etc.

### Step 6.4: Create New Integration Test

**Location**: Create new file `tests/test_selection_state_integration.py`

**CODE TO ADD**:
```python
"""
Integration tests for centralized selection state architecture.

Tests the complete flow: UI → ApplicationState → rendering
"""
import pytest
from PySide6.QtWidgets import QApplication

from stores.application_state import get_application_state, reset_application_state
from core.display_mode import DisplayMode
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

    def test_end_to_end_selection_flow(self, qapp):
        """Test complete user workflow: select curves → render."""
        window = MainWindow()
        app_state = get_application_state()

        # Load multi-curve data
        window.multi_point_controller.on_multi_point_data_loaded({
            "Track1": [CurvePoint(1, 10, 20)],
            "Track2": [CurvePoint(1, 30, 40)]
        })

        # User selects two curves
        window.tracking_panel.set_selected_points(["Track1", "Track2"])

        # ApplicationState updated
        assert app_state.get_selected_curves() == {"Track1", "Track2"}
        assert app_state.display_mode == DisplayMode.SELECTED

        # Widget reads correct mode
        assert window.curve_widget.display_mode == DisplayMode.SELECTED

        # Renderer sees both curves
        from rendering.render_state import RenderState
        render_state = RenderState.compute(window.curve_widget)
        assert "Track1" in render_state.visible_curves
        assert "Track2" in render_state.visible_curves

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
```

### Step 6.5: Update All Test Files

**Search command to find all test files needing updates**:
```bash
grep -r "\.display_mode = " tests/
```

**Update pattern for each file**:
1. Add import: `from stores.application_state import get_application_state`
2. Replace `widget.display_mode = X` with appropriate `app_state.set_*()` calls
3. Add assertions to verify computed mode is correct

### Verification Steps

1. **Run all tests**:
   ```bash
   .venv/bin/python3 -m pytest tests/ -v
   ```
   Expected: All tests pass

2. **Run specific test suites**:
   ```bash
   .venv/bin/python3 -m pytest tests/test_selection_state_integration.py -v
   .venv/bin/python3 -m pytest tests/test_display_mode_integration.py -v
   .venv/bin/python3 -m pytest tests/test_render_state.py -v
   ```

3. **Check coverage**:
   ```bash
   .venv/bin/python3 -m pytest tests/ --cov=stores.application_state --cov-report=term-missing
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

## Phase 7: Cleanup and Documentation

**Estimated Time**: 0.5 hours
**Files Modified**: Various documentation and signal cleanup
**Dependencies**: Phase 1-6 complete
**Risk Level**: LOW

### Step 7.1: Remove Obsolete display_mode_changed Signal (Optional)

**Decision Point**: Keep or remove `display_mode_changed` signal?

**Option A - Keep for Backward Compatibility**:
- Leave signal in TrackingPointsPanel
- Mark as deprecated in docstring
- Plan removal in future version

**Option B - Remove Immediately**:
- Search for all signal connections
- Update to use `selection_state_changed` instead
- Remove signal declaration

**Recommended**: Option A (backward compatibility during migration)

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
```

### Step 7.3: Add Inline Documentation

**Location**: Key files with comments explaining the architecture

**In `stores/application_state.py`** (add at top of class):
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

    Signals:
        - selection_state_changed(set[str], bool)  # Emitted on input changes
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

## Consequences

### Positive

✅ Synchronization bugs eliminated (can't forget to update derived state)
✅ Race conditions eliminated (no circular dependencies)
✅ Always consistent (computed property never stale)
✅ Easier debugging (one place to check state)
✅ Better testability (centralized state easier to verify)

### Negative

⚠️ Breaking change for code that sets display_mode directly
⚠️ Requires understanding of computed property pattern
⚠️ Slightly more verbose for simple cases

### Migration

- Old: `widget.display_mode = DisplayMode.SELECTED`
- New: `app_state.set_selected_curves({"Track1"})`

## Implementation

Completed in 7 phases:
1. Add selection state to ApplicationState
2. Update TrackingPointsPanel to use ApplicationState
3. Convert CurveViewWidget.display_mode to read-only property
4. Update MultiCurveManager to use ApplicationState
5. Update controllers, remove synchronization loop
6. Update all tests
7. Documentation and cleanup

Total time: 6 hours
Test coverage: 100% of new functionality
Zero regressions
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

3. **Run full test suite**:
   ```bash
   .venv/bin/python3 -m pytest tests/ -v --tb=short
   ```

### Rollback Instructions

1. Remove documentation:
   ```bash
   git checkout CLAUDE.md
   rm docs/ADR-001-selection-state-architecture.md
   ```

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

---

## Success Criteria

### Phase Completion Checklist

- [ ] **Phase 1**: ApplicationState has selection state, display_mode property works
- [ ] **Phase 2**: TrackingPointsPanel updates ApplicationState on user input
- [ ] **Phase 3**: CurveViewWidget.display_mode is read-only property
- [ ] **Phase 4**: MultiCurveManager uses ApplicationState, no local state
- [ ] **Phase 5**: Controllers use ApplicationState, synchronization loop removed
- [ ] **Phase 6**: All tests updated and passing
- [ ] **Phase 7**: Documentation complete

### Final Verification

**Run these commands to verify complete success**:

1. **Type checking** (0 errors):
   ```bash
   ./bpr --errors-only
   ```

2. **All tests pass**:
   ```bash
   .venv/bin/python3 -m pytest tests/ -v
   ```

3. **Manual test - The original bug is fixed**:
   ```bash
   .venv/bin/python3 -c "
   from PySide6.QtWidgets import QApplication
   import sys
   from ui.main_window import MainWindow
   from stores.application_state import get_application_state
   from core.models import CurvePoint

   app = QApplication(sys.argv)
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

---

## Summary

This refactoring plan provides step-by-step instructions to implement the centralized selection state architecture that eliminates synchronization bugs.

**Key Changes**:
1. ApplicationState becomes single source of truth for selection
2. display_mode becomes computed property (never stored)
3. Synchronization loop in MultiPointTrackingController removed
4. All components updated to use ApplicationState

**Benefits**:
- ✅ Fixes multi-curve selection bug
- ✅ Eliminates race conditions
- ✅ Prevents future synchronization bugs
- ✅ Cleaner, more maintainable architecture

**Estimated Total Time**: 6-8 hours
**Risk Level**: Medium (breaking changes, but well-tested)
**Rollback**: Fully reversible at any phase

---

**Ready to implement!** Follow each phase sequentially, verifying at each step.

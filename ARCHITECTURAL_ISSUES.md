# Display Mode Architecture Issues

## Problem: Multi-Curve Display Bug Was Hard to Debug

The bug where selecting two curves only displayed one was difficult to trace because of architectural issues.

## Root Cause Analysis

### 1. Signal Chain Length (9 hops!)

User Ctrl+clicks curve:
1. `QTableWidget.selectionModel` changes
2. `TrackingPointsPanel._on_selection_changed()`
3. Emits `points_selected` signal
4. `MainWindow.on_tracking_points_selected()` receives
5. Calls `MultiPointTrackingController.on_tracking_points_selected()`
6. Calls `MultiPointTrackingController.update_curve_display()`
7. Calls `MultiCurveManager.set_curves_data()`
8. Emits `display_mode_changed` signal (if my fix is applied)
9. `MainWindow.on_display_mode_changed()` receives
10. Sets `CurveViewWidget.display_mode`

**Problem**: Debugging requires tracing through 9-10 layers across 5 files.

### 2. Multiple Sources of Truth

Display mode state is scattered:

```
TrackingPointsPanel:
  - display_mode_checkbox.isChecked()  # Controls ALL_VISIBLE
  - table.selectedItems()              # Controls SELECTED

CurveViewWidget:
  - display_mode property              # Actual rendering state
  - selected_curve_names set           # Which curves are selected

RenderState:
  - display_mode field                 # Computed from widget
  - visible_curves set                 # Pre-computed visibility
```

**Problem**: No single component owns the "display mode policy". State must be synchronized across 3+ components.

### 3. Implicit State Machine

Display mode has 3 states but transitions are scattered:

```
ALL_VISIBLE → SELECTED:    (when checkbox unchecked + has selection)
SELECTED → ALL_VISIBLE:    (when checkbox checked)
SELECTED → ACTIVE_ONLY:    (when selection cleared)
ACTIVE_ONLY → SELECTED:    (when curves selected)
```

**Problem**: Transition logic is split between:
- `TrackingPointsPanel._determine_mode_from_checkbox()`
- `TrackingPointsPanel._on_selection_changed()` (added by my fix)
- `MultiCurveManager.set_curves_data()` (added by my fix)

### 4. Mixed Reactive/Imperative Patterns

Some parts use Qt signals (reactive), others use direct calls:

```python
# Reactive (hard to trace)
self.points_selected.emit(selected_points)  # Who handles this?

# Imperative (easy to trace)
self.curve_widget.display_mode = DisplayMode.SELECTED  # Clear cause/effect
```

**Problem**: Inconsistent patterns make it hard to reason about control flow.

### 5. The "Checkbox Checked" Bug

Current behavior when checkbox IS checked:

```
Checkbox: [X] Show all curves
Action: User Ctrl+clicks curves A and B
Expected: Show only curves A and B (switch to SELECTED mode)
Actual: Still shows ALL curves (stays in ALL_VISIBLE mode)
```

**Why**: My fix only updates display mode when checkbox is UNCHECKED:

```python
if not self.display_mode_checkbox.isChecked() and selected_points:
    self._emit_display_mode_signals(DisplayMode.SELECTED)
```

**Problem**: Checkbox state takes precedence over user selection intent.

## Architectural Solutions

### Option 1: DisplayModeController (Centralized)

Create a single component that owns all display mode logic:

```python
class DisplayModeController:
    """Single source of truth for display mode policy."""

    def __init__(self, widget: CurveViewWidget, panel: TrackingPointsPanel):
        self.widget = widget
        self.panel = panel

    def update_from_checkbox(self, checked: bool) -> None:
        """Checkbox toggled - decide display mode."""
        if checked:
            self.widget.display_mode = DisplayMode.ALL_VISIBLE
        else:
            # Defer to selection
            self.update_from_selection(self.panel.get_selected_points())

    def update_from_selection(self, selected: list[str]) -> None:
        """Selection changed - decide display mode."""
        # Checkbox takes precedence
        if self.panel.display_mode_checkbox.isChecked():
            return  # Stay in ALL_VISIBLE

        # No checkbox override - use selection
        if len(selected) > 0:
            self.widget.display_mode = DisplayMode.SELECTED
            self.widget.selected_curve_names = set(selected)
        else:
            self.widget.display_mode = DisplayMode.ACTIVE_ONLY
```

**Benefits**:
- Single place to understand display mode logic
- All transitions in one file
- Easy to test

**Drawbacks**:
- New component to maintain
- More coupling between panel and widget

### Option 2: State Machine Pattern

Make display mode transitions explicit:

```python
from enum import Enum
from typing import Protocol

class DisplayModeEvent(Enum):
    CHECKBOX_CHECKED = "checkbox_checked"
    CHECKBOX_UNCHECKED = "checkbox_unchecked"
    CURVES_SELECTED = "curves_selected"
    SELECTION_CLEARED = "selection_cleared"

class DisplayModeStateMachine:
    """Explicit state machine for display mode."""

    def __init__(self):
        self.state = DisplayMode.ACTIVE_ONLY
        self.transitions = {
            (DisplayMode.ACTIVE_ONLY, DisplayModeEvent.CHECKBOX_CHECKED): DisplayMode.ALL_VISIBLE,
            (DisplayMode.ACTIVE_ONLY, DisplayModeEvent.CURVES_SELECTED): DisplayMode.SELECTED,
            (DisplayMode.SELECTED, DisplayModeEvent.CHECKBOX_CHECKED): DisplayMode.ALL_VISIBLE,
            (DisplayMode.SELECTED, DisplayModeEvent.SELECTION_CLEARED): DisplayMode.ACTIVE_ONLY,
            (DisplayMode.ALL_VISIBLE, DisplayModeEvent.CHECKBOX_UNCHECKED): DisplayMode.SELECTED,
            # ... etc
        }

    def handle_event(self, event: DisplayModeEvent) -> DisplayMode:
        """Process event and return new state."""
        key = (self.state, event)
        if key in self.transitions:
            self.state = self.transitions[key]
        return self.state
```

**Benefits**:
- All transitions explicitly defined
- Easy to visualize (can generate state diagram)
- Prevents invalid transitions

**Drawbacks**:
- More boilerplate
- May be overkill for 3 states

### Option 3: Simplify Signal Chain (Direct Calls)

Replace long signal chains with direct method calls:

```python
# Before (9 hops via signals)
panel.points_selected.emit(selected)
→ window.on_tracking_points_selected()
→ controller.on_tracking_points_selected()
→ ... 6 more hops ...

# After (2 hops, direct calls)
panel._on_selection_changed():
    selected = self.get_selected_points()
    self.display_mode_controller.update_from_selection(selected)
    self.points_selected.emit(selected)  # Still emit for other listeners
```

**Benefits**:
- Easier to debug (can step through)
- Faster execution
- Clear control flow

**Drawbacks**:
- Less decoupled
- Breaks Qt signal/slot pattern

## Recommendation

**Hybrid approach**:
1. Create `DisplayModeCoordinator` (lightweight, not full controller)
2. Keep signals for cross-component communication
3. Use direct calls for display mode logic within coordinator
4. Add explicit state validation

```python
class DisplayModeCoordinator:
    """Coordinates display mode between checkbox, selection, and widget."""

    def __init__(self, widget, checkbox_widget):
        self.widget = widget
        self.checkbox = checkbox_widget

    def update(self, selected_curves: set[str]) -> DisplayMode:
        """
        Determine display mode based on current state.

        Called from:
        - TrackingPointsPanel._on_selection_changed()
        - TrackingPointsPanel._on_display_mode_checkbox_toggled()

        Returns:
            New display mode
        """
        # Rule 1: Checkbox checked → always ALL_VISIBLE
        if self.checkbox.isChecked():
            mode = DisplayMode.ALL_VISIBLE

        # Rule 2: Checkbox unchecked + has selection → SELECTED
        elif selected_curves:
            mode = DisplayMode.SELECTED
            self.widget.selected_curve_names = selected_curves

        # Rule 3: Checkbox unchecked + no selection → ACTIVE_ONLY
        else:
            mode = DisplayMode.ACTIVE_ONLY

        self.widget.display_mode = mode
        return mode
```

**Benefits**:
- Centralizes logic without major refactoring
- Clear, testable rules
- Easy to extend

**Implementation**:
- 1-2 hours to implement
- Update TrackingPointsPanel to use coordinator
- Add tests for all state transitions

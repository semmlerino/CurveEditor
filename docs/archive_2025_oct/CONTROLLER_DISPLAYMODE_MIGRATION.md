# Controller Migration to DisplayMode Architecture

**Status:** ✅ Phase 2 Complete (Part of v2.0 Release)
**Date:** October 2025
**Context:** All phases complete - DisplayMode is sole API, boolean removed in Phase 4

## Executive Summary

This document provides the architectural design for migrating 3 controller files from boolean `show_all_curves` to explicit `DisplayMode` enum, with full backward compatibility during the transition.

## Problem Statement

### Current State
- **Phase 1 Complete:** `CurveViewWidget._display_mode` is primary storage
- **Phase 2 Needed:** 3 controller files still use deprecated `show_all_curves` boolean
- **Backward Compatibility:** Must support gradual migration without breaking existing code

### Files to Migrate
1. `ui/controllers/multi_point_tracking_controller.py` - `toggle_show_all_curves()` method
2. `ui/main_window.py` - `on_show_all_curves_toggled()` method
3. `ui/tracking_points_panel.py` - `show_all_curves_toggled` signal (boolean)

### The Ambiguous Boolean Problem

The old boolean API has semantic ambiguity:

```python
# What does False mean? Two different states!
widget.show_all_curves = False  # Could mean:
# 1. Show selected curves (if selection exists)
# 2. Show active curve only (if no selection)
```

This creates a **conversion challenge**: When converting `False → DisplayMode`, we must check selection state to determine intent.

## Architecture Design

### Design Principle: Gradual Migration with Dual API

**Strategy:** Add new DisplayMode-based methods alongside deprecated boolean methods, with automatic forwarding.

```python
# OLD (deprecated but still works)
controller.toggle_show_all_curves(True)

# NEW (preferred)
controller.set_display_mode(DisplayMode.ALL_VISIBLE)
```

### Method Naming Convention

| Old Boolean Method | New DisplayMode Method | Conversion Method |
|-------------------|------------------------|-------------------|
| `toggle_show_all_curves(bool)` | `set_display_mode(DisplayMode)` | `_convert_bool_to_display_mode(bool)` |
| `on_show_all_curves_toggled(bool)` | `on_display_mode_changed(DisplayMode)` | `_convert_bool_to_display_mode(bool)` |

### Core Components

#### 1. New DisplayMode-Based Methods

```python
def set_display_mode(self, mode: DisplayMode) -> None:
    """
    Set the display mode for curve visibility.

    This is the preferred API that replaces toggle_show_all_curves().

    Args:
        mode: DisplayMode enum value (ALL_VISIBLE, SELECTED, ACTIVE_ONLY)

    Examples:
        >>> # Show all visible curves
        >>> controller.set_display_mode(DisplayMode.ALL_VISIBLE)

        >>> # Show only selected curves
        >>> controller.set_display_mode(DisplayMode.SELECTED)

        >>> # Show only active curve
        >>> controller.set_display_mode(DisplayMode.ACTIVE_ONLY)
    """
    if not self.main_window.curve_widget:
        return

    # Direct assignment - no conversion needed
    self.main_window.curve_widget.display_mode = mode
    logger.debug(f"Display mode set to: {mode}")
```

#### 2. Deprecated Boolean Methods with Forwarding

```python
def toggle_show_all_curves(self, show_all: bool) -> None:
    """
    Toggle whether to show all curves or just the active one.

    .. deprecated:: October 2025
        Use :meth:`set_display_mode` instead for explicit control.
        This method has ambiguous semantics when show_all=False.

    Args:
        show_all: If True, show all visible curves; if False, show active/selected

    Migration:
        OLD: controller.toggle_show_all_curves(True)
        NEW: controller.set_display_mode(DisplayMode.ALL_VISIBLE)

        OLD: controller.toggle_show_all_curves(False)  # Ambiguous!
        NEW: controller.set_display_mode(DisplayMode.SELECTED)  # Explicit
        NEW: controller.set_display_mode(DisplayMode.ACTIVE_ONLY)  # Explicit
    """
    warnings.warn(
        "toggle_show_all_curves() is deprecated, use set_display_mode() instead",
        DeprecationWarning,
        stacklevel=2
    )

    # Forward to new API using conversion logic
    mode = self._convert_bool_to_display_mode(show_all)
    self.set_display_mode(mode)
```

#### 3. Conversion Logic for Ambiguous Boolean Cases

```python
def _convert_bool_to_display_mode(self, show_all: bool) -> DisplayMode:
    """
    Convert legacy boolean to DisplayMode enum.

    Handles the ambiguous False case by checking current selection state.

    Args:
        show_all: Legacy boolean value

    Returns:
        DisplayMode enum value

    Conversion Logic:
        - True → ALL_VISIBLE (unambiguous)
        - False + has_selection → SELECTED (preserve selection intent)
        - False + no_selection → ACTIVE_ONLY (default to active)

    Note:
        This method uses current widget state to resolve ambiguity.
        For explicit control, use set_display_mode() directly.
    """
    if show_all:
        return DisplayMode.ALL_VISIBLE
    else:
        # Ambiguous case: check current selection state
        widget = self.main_window.curve_widget
        if widget and widget.selected_curve_names:
            # Preserve existing selection
            return DisplayMode.SELECTED
        else:
            # No selection, default to active only
            return DisplayMode.ACTIVE_ONLY
```

### Signal Migration Strategy

#### Problem: TrackingPointsPanel Emits Boolean Signal

```python
# Current implementation
class TrackingPointsPanel(QWidget):
    show_all_curves_toggled: Signal = Signal(bool)  # Boolean signal

    def _on_show_all_curves_toggled(self, checked: bool) -> None:
        self.show_all_curves_toggled.emit(checked)  # Emits boolean
```

#### Solution: Dual Signal Approach

```python
class TrackingPointsPanel(QWidget):
    # OLD: Deprecated boolean signal
    show_all_curves_toggled: Signal = Signal(bool)

    # NEW: DisplayMode signal (preferred)
    display_mode_changed: Signal = Signal(DisplayMode)

    def _on_show_all_curves_toggled(self, checked: bool) -> None:
        """Handle checkbox toggle (internal use only)."""
        # Emit both signals during transition
        self.show_all_curves_toggled.emit(checked)  # Backward compat

        # Convert and emit DisplayMode signal
        mode = DisplayMode.ALL_VISIBLE if checked else DisplayMode.ACTIVE_ONLY
        self.display_mode_changed.emit(mode)
```

#### Signal Connection Migration

```python
# ui/controllers/ui_initialization_controller.py

# OLD (deprecated)
_ = self.main_window.tracking_panel.show_all_curves_toggled.connect(
    self.main_window.on_show_all_curves_toggled
)

# NEW (preferred) - both connected during transition
_ = self.main_window.tracking_panel.show_all_curves_toggled.connect(
    self.main_window.on_show_all_curves_toggled
)
_ = self.main_window.tracking_panel.display_mode_changed.connect(
    self.main_window.on_display_mode_changed
)

# FUTURE (after full migration): Remove boolean signal connection
```

## Implementation Plan

### Phase 2.1: Add New DisplayMode Methods (Non-Breaking)

**Files to modify:**
1. `ui/controllers/multi_point_tracking_controller.py`
2. `ui/main_window.py`
3. `ui/tracking_points_panel.py`

**Changes:**
- ✅ Add `set_display_mode(mode: DisplayMode)` methods
- ✅ Add `on_display_mode_changed(mode: DisplayMode)` handlers
- ✅ Add `_convert_bool_to_display_mode(bool)` helper
- ✅ Add `display_mode_changed` signal to TrackingPointsPanel
- ✅ Keep all existing boolean methods unchanged

### Phase 2.2: Add Deprecation Warnings (Non-Breaking)

**Changes:**
- ✅ Add `warnings.warn()` to `toggle_show_all_curves()`
- ✅ Add `warnings.warn()` to `on_show_all_curves_toggled()`
- ✅ Update docstrings with deprecation notices and migration examples
- ✅ Forward deprecated methods to new DisplayMode API

### Phase 2.3: Update Internal Calls (Non-Breaking)

**Changes:**
- ✅ Update controller internal code to use `set_display_mode()` directly
- ✅ Connect `display_mode_changed` signal alongside boolean signal
- ✅ Update tests to use new API (keep old tests for backward compat)

### Phase 2.4: Documentation and Migration Guide (Non-Breaking)

**Changes:**
- ✅ Update CLAUDE.md with new controller API patterns
- ✅ Create migration examples for common use cases
- ✅ Add type hints and examples to all new methods

### Phase 2.5: Gradual External Migration (Future)

**Timeline:** Multiple weeks/months as needed

**Process:**
1. Monitor deprecation warnings in logs
2. Update external callers one-by-one
3. Once all external callers migrated, remove deprecated methods
4. Remove boolean signal from TrackingPointsPanel

## Detailed Method Signatures

### MultiPointTrackingController

```python
class MultiPointTrackingController:

    # ==================== NEW API (Preferred) ====================

    def set_display_mode(self, mode: DisplayMode) -> None:
        """Set the display mode for curve visibility (preferred API)."""
        if not self.main_window.curve_widget:
            return
        self.main_window.curve_widget.display_mode = mode
        logger.debug(f"Display mode set to: {mode}")

    # ==================== DEPRECATED API ====================

    def toggle_show_all_curves(self, show_all: bool) -> None:
        """Toggle curve visibility (deprecated, use set_display_mode)."""
        warnings.warn(
            "toggle_show_all_curves() is deprecated, use set_display_mode() instead",
            DeprecationWarning,
            stacklevel=2
        )
        mode = self._convert_bool_to_display_mode(show_all)
        self.set_display_mode(mode)

    # ==================== PRIVATE HELPERS ====================

    def _convert_bool_to_display_mode(self, show_all: bool) -> DisplayMode:
        """Convert legacy boolean to DisplayMode enum."""
        if show_all:
            return DisplayMode.ALL_VISIBLE
        else:
            widget = self.main_window.curve_widget
            if widget and widget.selected_curve_names:
                return DisplayMode.SELECTED
            else:
                return DisplayMode.ACTIVE_ONLY
```

### MainWindow

```python
class MainWindow(QMainWindow):

    # ==================== NEW API (Preferred) ====================

    def on_display_mode_changed(self, mode: DisplayMode) -> None:
        """Handle display mode change from tracking panel (preferred API)."""
        if self.curve_widget:
            self.curve_widget.display_mode = mode
            logger.debug(f"Display mode changed to: {mode}")

    # ==================== DEPRECATED API ====================

    def on_show_all_curves_toggled(self, show_all: bool) -> None:
        """Handle show all curves toggle (deprecated, use on_display_mode_changed)."""
        warnings.warn(
            "on_show_all_curves_toggled() is deprecated, use on_display_mode_changed() instead",
            DeprecationWarning,
            stacklevel=2
        )
        if self.curve_widget:
            mode = self.tracking_controller._convert_bool_to_display_mode(show_all)
            self.on_display_mode_changed(mode)
```

### TrackingPointsPanel

```python
class TrackingPointsPanel(QWidget):
    # OLD: Deprecated boolean signal
    show_all_curves_toggled: Signal = Signal(bool)

    # NEW: DisplayMode signal (preferred)
    display_mode_changed: Signal = Signal(DisplayMode)

    def _on_show_all_curves_toggled(self, checked: bool) -> None:
        """Handle checkbox toggle (internal handler)."""
        # Emit both signals during transition period
        self.show_all_curves_toggled.emit(checked)  # Backward compat

        # Convert to DisplayMode and emit new signal
        mode = DisplayMode.ALL_VISIBLE if checked else DisplayMode.ACTIVE_ONLY
        self.display_mode_changed.emit(mode)

        logger.debug(f"Display mode toggled: {mode}")
```

## Conversion Logic Decision Tree

```
Input: show_all (bool)
│
├─ show_all == True
│  └─> DisplayMode.ALL_VISIBLE (unambiguous)
│
└─ show_all == False (ambiguous!)
   │
   ├─ Has selected_curve_names?
   │  ├─ Yes → DisplayMode.SELECTED (preserve selection intent)
   │  └─ No  → DisplayMode.ACTIVE_ONLY (default to active)
```

## Migration Examples

### Example 1: Show All Curves

```python
# OLD (deprecated)
controller.toggle_show_all_curves(True)

# NEW (preferred)
controller.set_display_mode(DisplayMode.ALL_VISIBLE)
```

### Example 2: Show Selected Curves

```python
# OLD (ambiguous - depends on selection state!)
controller.toggle_show_all_curves(False)

# NEW (explicit)
controller.set_display_mode(DisplayMode.SELECTED)
```

### Example 3: Show Active Curve Only

```python
# OLD (ambiguous - depends on selection state!)
controller.toggle_show_all_curves(False)

# NEW (explicit)
controller.set_display_mode(DisplayMode.ACTIVE_ONLY)
```

### Example 4: Signal Connection

```python
# OLD (deprecated)
panel.show_all_curves_toggled.connect(main_window.on_show_all_curves_toggled)

# NEW (preferred)
panel.display_mode_changed.connect(main_window.on_display_mode_changed)

# TRANSITION (both connected)
panel.show_all_curves_toggled.connect(main_window.on_show_all_curves_toggled)
panel.display_mode_changed.connect(main_window.on_display_mode_changed)
```

## Testing Strategy

### Backward Compatibility Tests

```python
def test_toggle_show_all_curves_backward_compat():
    """Verify deprecated method still works."""
    controller = MultiPointTrackingController(main_window)

    with pytest.warns(DeprecationWarning):
        controller.toggle_show_all_curves(True)

    assert main_window.curve_widget.display_mode == DisplayMode.ALL_VISIBLE
```

### Conversion Logic Tests

```python
def test_convert_bool_false_with_selection():
    """Verify False converts to SELECTED when selection exists."""
    widget.selected_curve_names = {"Track1", "Track2"}

    mode = controller._convert_bool_to_display_mode(False)
    assert mode == DisplayMode.SELECTED

def test_convert_bool_false_no_selection():
    """Verify False converts to ACTIVE_ONLY when no selection."""
    widget.selected_curve_names = set()

    mode = controller._convert_bool_to_display_mode(False)
    assert mode == DisplayMode.ACTIVE_ONLY
```

### DisplayMode API Tests

```python
def test_set_display_mode_all_visible():
    """Verify new API sets ALL_VISIBLE mode."""
    controller.set_display_mode(DisplayMode.ALL_VISIBLE)
    assert widget.display_mode == DisplayMode.ALL_VISIBLE

def test_set_display_mode_selected():
    """Verify new API sets SELECTED mode."""
    controller.set_display_mode(DisplayMode.SELECTED)
    assert widget.display_mode == DisplayMode.SELECTED
```

## API Comparison Table

| Feature | Old Boolean API | New DisplayMode API |
|---------|----------------|---------------------|
| **Clarity** | Ambiguous (False has 2 meanings) | Explicit (3 distinct states) |
| **Type Safety** | `bool` (True/False) | `DisplayMode` enum (3 values) |
| **Intent** | Implicit (requires checking other state) | Self-documenting (intent clear from enum) |
| **Conversion** | Manual coordination needed | Handled by enum methods |
| **Deprecation** | Planned (with warnings) | Preferred going forward |
| **Migration** | Gradual with forwarding | Direct use immediately |

## Benefits

1. **Explicit Intent:** No more guessing what `False` means in different contexts
2. **Type Safety:** Enum prevents invalid states (can't accidentally pass wrong type)
3. **Self-Documenting:** Code clearly states ALL_VISIBLE vs SELECTED vs ACTIVE_ONLY
4. **Backward Compatible:** Old code continues working during gradual migration
5. **Testable:** Conversion logic is isolated and unit-testable
6. **Maintainable:** Single source of truth for display mode logic

## Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Breaking existing code | Keep deprecated methods working with forwarding |
| Confusion during transition | Clear deprecation warnings and migration examples |
| Selection state dependency | Explicit conversion logic with documented behavior |
| Signal incompatibility | Emit both boolean and DisplayMode signals during transition |

## Success Criteria

- ✅ All 3 controller files have new DisplayMode methods
- ✅ All deprecated methods emit DeprecationWarning
- ✅ All deprecated methods forward to new API
- ✅ Conversion logic handles ambiguous cases correctly
- ✅ 100% backward compatibility maintained
- ✅ All tests pass (existing + new)
- ✅ Documentation updated with migration guide

## Next Steps

1. **Implement Phase 2.1:** Add new DisplayMode methods to all 3 files
2. **Implement Phase 2.2:** Add deprecation warnings and forwarding logic
3. **Implement Phase 2.3:** Update internal calls to use new API
4. **Implement Phase 2.4:** Update documentation and create migration guide
5. **Monitor:** Track deprecation warnings in production/testing
6. **Migrate:** Gradually update external callers
7. **Cleanup:** Remove deprecated methods once all callers migrated

---

**Last Updated:** October 2025
**Author:** Claude (python-expert-architect agent)
**Document Status:** Historical - Phase 2 design document (completed as part of v2.0 release)
**Note:** Phase 4 removed all boolean code. This document shows the Phase 2 design for gradual migration with backward compatibility, which was completed before final boolean removal in Phase 4.

**Related Documents:**
- `core/DISPLAY_MODE_MIGRATION.md` - Phase 1 (CurveViewWidget migration)
- `RENDER_STATE_IMPLEMENTATION.md` - RenderState pattern for performance
- `DISPLAYMODE_MIGRATION_PLAN.md` - Complete 4-phase migration plan (all phases complete)

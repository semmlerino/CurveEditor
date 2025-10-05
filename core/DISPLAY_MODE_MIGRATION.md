# DisplayMode Migration Guide

**Status:** ✅ Phase 4 Complete - Boolean removed, DisplayMode is sole API

**Note:** This guide shows migration patterns from the legacy boolean API to DisplayMode enum. As of October 2025 (Phase 4 complete), the boolean `show_all_curves` has been completely removed. This document is kept for historical reference and to help understand the DisplayMode design.

## Problem Statement (Historical - Resolved in Phase 4)

The `show_all_curves` boolean created confusion because its meaning changed based on other state (`selected_curve_names`), requiring developers to remember implicit coordination rules.

### Old Confusing Pattern

```python
# Implicit semantics - meaning changes based on selection state
if show_all_curves:
    # Show all visible curves
    curves = get_all_visible_curves()
elif selected_curve_names:
    # Show selected curves
    curves = list(selected_curve_names)
else:
    # Show active curve only
    curves = [active_curve_name]
```

**Problems:**
1. Boolean doesn't capture three-way choice
2. True/False + selection creates implicit coordination
3. Developers must remember: False + empty selection = show active only
4. Hard to understand intent from code alone

## Solution: DisplayMode Enum

```python
from core import DisplayMode

# Explicit semantics - intent is clear
match display_mode:
    case DisplayMode.ALL_VISIBLE:
        curves = get_all_visible_curves()
    case DisplayMode.SELECTED:
        curves = list(selected_curve_names)
    case DisplayMode.ACTIVE_ONLY:
        curves = [active_curve_name]
```

## Migration Examples

### Example 1: Converting Existing Logic

**Before:**
```python
class MultiCurveManager:
    def __init__(self):
        self.show_all_curves: bool = False
        self.selected_curve_names: set[str] = set()

    def get_visible_curves(self) -> list[str]:
        if self.show_all_curves:
            return self._get_all_visible()
        elif self.selected_curve_names:
            return list(self.selected_curve_names)
        else:
            return [self.active_curve_name]
```

**After:**
```python
from core import DisplayMode

class MultiCurveManager:
    def __init__(self):
        self.display_mode: DisplayMode = DisplayMode.ACTIVE_ONLY

    def get_visible_curves(self) -> list[str]:
        if self.display_mode == DisplayMode.ALL_VISIBLE:
            return self._get_all_visible()
        elif self.display_mode == DisplayMode.SELECTED:
            return self._get_selected()
        else:  # ACTIVE_ONLY
            return [self.active_curve_name]
```

### Example 2: Gradual Migration with Compatibility

If you can't migrate all code at once, use the conversion helpers:

```python
from core import DisplayMode

# Convert from legacy boolean state
mode = DisplayMode.from_legacy(
    show_all_curves=self.show_all_curves,
    has_selection=len(self.selected_curve_names) > 0
)

# Use new DisplayMode in refactored code
curves = self._get_curves_for_mode(mode)

# Convert back to legacy for old APIs
show_all, should_select = mode.to_legacy()
old_api.set_visibility(show_all_curves=show_all)
```

### Example 3: UI Toggle Buttons

**Before:**
```python
def _on_show_all_toggled(self, checked: bool) -> None:
    self.show_all_curves = checked
    self.selected_curve_names.clear()  # Implicit: clear selection when showing all
    self.update_display()
```

**After:**
```python
def _on_display_mode_changed(self, mode: DisplayMode) -> None:
    self.display_mode = mode
    self.update_display()  # No implicit coordination needed!
```

### Example 4: RenderState Integration

**Before:**
```python
@dataclass
class RenderState:
    show_all_curves: bool
    selected_curve_names: set[str]

    def get_curves_to_render(self) -> list[str]:
        # Confusing logic duplicated everywhere
        if self.show_all_curves:
            return all_curves
        elif self.selected_curve_names:
            return list(self.selected_curve_names)
        else:
            return [active_curve]
```

**After:**
```python
from core import DisplayMode

@dataclass
class RenderState:
    display_mode: DisplayMode

    def get_curves_to_render(self) -> list[str]:
        # Intent is crystal clear
        match self.display_mode:
            case DisplayMode.ALL_VISIBLE:
                return all_curves
            case DisplayMode.SELECTED:
                return self._get_selected()
            case DisplayMode.ACTIVE_ONLY:
                return [active_curve]
```

## Best Practices

### 1. Use Explicit Mode Setting

**Good:**
```python
# Intent is immediately clear
self.display_mode = DisplayMode.ALL_VISIBLE
```

**Bad (old way):**
```python
# What does this mean? Must check selection state!
self.show_all_curves = False
```

### 2. Pattern Matching for Clarity

**Preferred (Python 3.10+):**
```python
match display_mode:
    case DisplayMode.ALL_VISIBLE:
        return all_curves
    case DisplayMode.SELECTED:
        return selected
    case DisplayMode.ACTIVE_ONLY:
        return [active]
```

**Alternative (any Python version):**
```python
if display_mode == DisplayMode.ALL_VISIBLE:
    return all_curves
elif display_mode == DisplayMode.SELECTED:
    return selected
else:  # ACTIVE_ONLY
    return [active]
```

### 3. Use Properties for UI Display

```python
# For menu items, tooltips, etc.
action.setText(display_mode.display_name)
action.setToolTip(display_mode.description)
```

## Migration Checklist

- [ ] Replace `show_all_curves: bool` with `display_mode: DisplayMode`
- [ ] Update initialization: `DisplayMode.ACTIVE_ONLY` instead of `False`
- [ ] Replace conditional logic with pattern matching or if/elif
- [ ] Remove implicit coordination with `selected_curve_names`
- [ ] Update RenderState and other dataclasses
- [ ] Update UI toggle handlers to set DisplayMode directly
- [ ] Update tests to use DisplayMode enum
- [ ] Remove legacy boolean from protocols and type hints

## Testing

The `test_display_mode.py` file provides comprehensive tests:

```bash
uv run pytest tests/test_display_mode.py -v
```

All 22 tests should pass, validating:
- Conversion from legacy state
- Conversion to legacy state
- Round-trip conversions
- Property access
- Enum comparisons
- Usage patterns

## Benefits

1. **Self-Documenting**: `DisplayMode.ALL_VISIBLE` is clearer than `show_all_curves=True`
2. **Type-Safe**: Enum prevents invalid states
3. **No Implicit Coordination**: Single value captures full intent
4. **IDE Support**: Auto-complete shows all valid options
5. **Easier to Extend**: Add new display modes without boolean gymnastics
6. **Clearer Code Reviews**: Intent is obvious from enum value

## Migration Status

### Phase 4 Complete ✅ (October 2025)

All legacy boolean code has been removed:
- ❌ `show_all_curves` property removed from CurveViewWidget
- ❌ `toggle_show_all_curves()` removed from controllers
- ❌ `on_show_all_curves_toggled()` removed from MainWindow
- ❌ `show_all_curves_toggled` signal removed from TrackingPointsPanel
- ✅ `display_mode` property is sole API
- ✅ `DisplayMode` enum used throughout codebase
- ✅ RenderState uses `display_mode: DisplayMode | None` field
- ✅ 183 DisplayMode/render tests passing
- ✅ 0 boolean references in production code

### Current API (v2.0)

```python
from core.display_mode import DisplayMode

# Set display mode (only way)
widget.display_mode = DisplayMode.ALL_VISIBLE
widget.display_mode = DisplayMode.SELECTED
widget.display_mode = DisplayMode.ACTIVE_ONLY

# Check display mode
if widget.display_mode == DisplayMode.ALL_VISIBLE:
    # ...
```

## Questions?

See the comprehensive docstrings in `core/display_mode.py` for:
- Detailed examples
- DisplayMode enum documentation
- Property documentation
- Usage patterns

**Related Documentation:**
- `DISPLAYMODE_MIGRATION_PLAN.md` - Complete 4-phase migration plan
- `RENDER_STATE_IMPLEMENTATION.md` - RenderState with DisplayMode
- `CLAUDE.md` - Curve Visibility Architecture section

# MainWindow Refactoring Plan

## Analysis Results
- **Total hasattr() calls**: 21
- **File**: ui/main_window.py
- **Key Finding**: Most attributes are already typed as Optional in class definition

## Attribute Categories

### 1. Already Optional (Replace hasattr with None checks)
These are defined as Optional in class attributes (lines 219-239):
- `timeline_tabs: Any = None` (3 occurrences)
- `show_info_cb: QCheckBox | None = None` (2 occurrences)
- `curve_widget: Any = None` (2 occurrences)

### 2. Always Initialized (Remove hasattr)
These are always initialized in __init__:
- `state_manager` - Line 251: `self.state_manager = StateManager(self)`
- `curve_view` - Line 273: `self.curve_view = None`

### 3. Dynamic/Conditional Attributes
These may need to remain as hasattr:
- `_stored_tooltips` - Dynamically added
- `_point_spinbox_connected` - Connection tracking
- `statusBar` - QMainWindow method

## Refactoring Patterns

### Pattern 1: Optional attribute checks
```python
# Before
if hasattr(self, "show_info_cb") and self.show_info_cb:

# After
if self.show_info_cb is not None:
```

### Pattern 2: Multiple Optional checks
```python
# Before
if hasattr(self, "timeline_tabs") and self.timeline_tabs:

# After
if self.timeline_tabs is not None:
```

### Pattern 3: Always initialized attributes
```python
# Before
if hasattr(self, "state_manager"):

# After
# Just use directly - always exists
if self.state_manager:
```

### Pattern 4: QMainWindow inherited methods
```python
# Before
if hasattr(self, "statusBar"):

# After
# statusBar() is a QMainWindow method, always available
self.statusBar().showMessage(...)
```

## Implementation Steps

1. **Replace Optional checks** (Lines: ~10)
   - show_info_cb checks
   - timeline_tabs checks
   - curve_widget/curve_view checks

2. **Remove unnecessary checks** (Lines: ~5)
   - state_manager (always initialized)
   - statusBar (inherited from QMainWindow)

3. **Keep dynamic checks** (Lines: ~6)
   - _stored_tooltips (dynamically added)
   - _point_spinbox_connected (tracking state)
   - frame-related dynamic attributes

## Expected Outcome
- Reduce hasattr() from 21 to ~6
- Improve type safety with None checks
- Better IDE autocomplete
- Clearer code intent

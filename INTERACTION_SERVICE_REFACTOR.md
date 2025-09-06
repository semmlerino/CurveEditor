# InteractionService Refactoring Plan

## Analysis Results
- **Total hasattr() calls**: 84
- **File**: services/interaction_service.py
- **Impact**: 40% of all hasattr() usage in codebase

## Pattern Categories Found

### 1. Required Protocol Attributes (Direct Access)
These are defined in CurveViewProtocol as required attributes:
- `selected_points: set[int]` - Line 99 in protocol
- `curve_data: CurveDataList` - Line 94 in protocol
- `drag_active: bool` - Line 109 in protocol
- `pan_active: bool` - Line 110 in protocol
- `rubber_band_active: bool` - Line 116 in protocol

**Refactoring**: Remove hasattr(), use direct access

### 2. Optional Protocol Attributes (None Checks)
These are defined as Optional in CurveViewProtocol:
- `rubber_band: QRubberBand | None` - Line 115 in protocol
- `last_drag_pos: QtPointF | None` - Line 111 in protocol
- `last_pan_pos: QtPointF | None` - Line 112 in protocol
- `main_window: MainWindowProtocol` - Line 126 (should be Optional)

**Refactoring**: Replace hasattr() with `is not None` checks

### 3. Dynamic Attributes (Need Protocol Updates)
These are checked but not in the protocol yet:
- `workflow_state`
- `set_points` / `setPoints` methods
- `zoom` method
- `pan` method

**Refactoring**: Add to protocol or use try/except for methods

## Replacement Patterns

### Pattern 1: hasattr for required attributes
```python
# Before
if not hasattr(view, "selected_points"):
    view.selected_points = set()

# After
if not view.selected_points:
    view.selected_points = set()
```

### Pattern 2: hasattr + None check
```python
# Before
if not hasattr(view, "rubber_band") or view.rubber_band is None:

# After
if view.rubber_band is None:
```

### Pattern 3: getattr with default
```python
# Before
if getattr(view, "drag_active", False):

# After
if view.drag_active:
```

### Pattern 4: hasattr before access
```python
# Before
if hasattr(view, "curve_data") and 0 <= idx < len(view.curve_data):

# After
if 0 <= idx < len(view.curve_data):
```

## Implementation Steps

1. **First Pass - Required Attributes** (Lines to fix: ~30)
   - Remove hasattr for selected_points
   - Remove hasattr for curve_data
   - Remove getattr for drag_active, pan_active

2. **Second Pass - Optional Attributes** (Lines to fix: ~20)
   - Replace hasattr with None checks for rubber_band
   - Replace hasattr with None checks for last_drag_pos
   - Replace hasattr with None checks for main_window

3. **Third Pass - Method Checks** (Lines to fix: ~15)
   - Add methods to protocol or use callable() checks
   - Replace hasattr for update, repaint, setCursor

4. **Fourth Pass - History Attributes** (Lines to fix: ~19)
   - Handle history, history_index attributes
   - These may need to stay as hasattr or be added to MainWindowProtocol

## Expected Outcome
- Reduce hasattr() calls from 84 to <10
- Improve type inference in basedpyright
- Maintain backward compatibility
- No runtime behavior changes

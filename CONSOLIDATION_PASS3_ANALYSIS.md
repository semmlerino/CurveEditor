# Third Consolidation Pass Analysis

## 🔍 Duplication Patterns Found

### 1. **Hardcoded Magic Numbers** 🔴
Found multiple instances of hardcoded values that should be in `ui_constants.py`:

#### Image Dimensions (1920x1080)
- `services/transform_service.py`: Lines 77-78, 109-110
- `ui/curve_view_widget.py`: Lines 167-168
- `ui/ui_scaling.py`: Line 77, 115 (fallback screen resolution)

#### Other Magic Numbers
- `ui/main_window.py`: Line 148 - `max_history_size = 100`
- `rendering/optimized_curve_renderer.py`: Line 100 - `_grid_size = 100`
- `core/migration_utils.py`: Line 66, 110 - `chunk_size = 10000`
- Multiple files: `zoom_factor = 1.0`, `background_opacity = 0.5/1.0`

**Recommendation**: Add these to `ui_constants.py`:
```python
# Default dimensions
DEFAULT_IMAGE_WIDTH = 1920
DEFAULT_IMAGE_HEIGHT = 1080

# Limits
MAX_HISTORY_SIZE = 100
DEFAULT_CHUNK_SIZE = 10000
GRID_CELL_SIZE = 100

# Defaults
DEFAULT_ZOOM_FACTOR = 1.0
DEFAULT_BACKGROUND_OPACITY = 0.5
```

### 2. **Widget Creation Patterns** 🟡
In `ui/main_window.py`, there are 30+ widget creations with similar patterns:
- QLabel creation: 15 instances
- QPushButton creation: 5 instances
- QSlider creation: 2 instances
- QSpinBox creation: 2 instances
- QCheckBox creation: 3 instances

Many follow pattern: Create → Configure → Add to layout

**Recommendation**: Already have `ui/widget_factory.py` - should use it more consistently.

### 3. **Signal Connection Patterns** 🟢
Found 30+ signal connections across files. Pattern is consistent:
- `widget.signal.connect(handler)`

**Status**: This is actually fine - Qt's standard pattern. No action needed.

### 4. **File I/O Patterns** 🟡
12 instances of `with open()` across the codebase with similar error handling:

```python
try:
    with open(file_path) as f:
        data = json.load(f)
except FileNotFoundError:
    # handle
except json.JSONDecodeError:
    # handle
```

**Recommendation**: Create a file utilities module with:
- `safe_json_load(path)`
- `safe_json_save(path, data)`
- `safe_text_read(path)`
- `safe_text_write(path, content)`

### 5. **Logger Creation Pattern** ✅
**Status**: Already consistent - each module creates its own logger with:
```python
logger = logging.getLogger("module_name")
```
This is the correct pattern. No changes needed.

### 6. **Try/Except Patterns** 🟡
Similar exception handling patterns found:
```python
except Exception as e:
    logger.error(f"Error in {operation}: {e}")
```

**Recommendation**: Could create error handling decorators:
- `@log_exceptions(logger)`
- `@silent_fail(default_value)`

### 7. **Status Update Patterns** 🟡
Multiple places updating status with similar logic:
- Update status text
- Log the action
- Optional timeout

Found in: `ui_service.py`, `interaction_service.py`, various UI components

**Recommendation**: Already consolidated in UIService. Need to ensure all components use it.

### 8. **Coordinate Transformation Calls** ✅
**Status**: Already properly centralized in TransformService. No duplication found.

### 9. **Default Values in Method Signatures** 🟡
Many methods have inline defaults that could be constants:
- `timeout: int = 3000` (multiple places)
- `decimals: int = 2` (input dialogs)
- `padding = 100` (rendering)

**Recommendation**: Move to constants for consistency.

## 📊 Estimated Impact

| Issue | Files Affected | Lines to Save | Priority |
|-------|---------------|---------------|----------|
| Magic Numbers | 6 | ~30 | High |
| Widget Creation | 1 | ~50 (if factored) | Medium |
| File I/O Utils | 8 | ~40 | Medium |
| Error Decorators | 10+ | ~20 | Low |
| Default Values | 5 | ~15 | Low |

**Total Potential Savings**: ~155 lines + improved maintainability

## 🎯 Recommended Actions

### Priority 1: Constants Consolidation
1. Move all magic numbers to `ui_constants.py`
2. Update all files to import from constants
3. Document what each constant represents

### Priority 2: File I/O Utilities
1. Create `core/file_utils.py` with safe I/O functions
2. Update all file operations to use utilities
3. Centralize error handling and logging

### Priority 3: Widget Factory Usage
1. Review `ui/widget_factory.py`
2. Update `ui/main_window.py` to use factory methods
3. Ensure consistent widget configuration

### Priority 4: Error Handling Decorators
1. Create `core/decorators.py` with common patterns
2. Apply decorators where appropriate
3. Reduce boilerplate exception handling

## ✅ What's Already Good

1. **Service Architecture**: Clean 4-service pattern
2. **Transform Logic**: Properly centralized
3. **Logger Creation**: Consistent pattern
4. **Signal Connections**: Standard Qt pattern
5. **Type Hints**: Comprehensive coverage

## 🚫 False Positives

1. **Signal Connections**: Look similar but each is unique - no duplication
2. **Logger Creation**: Appears repetitive but correct pattern for Python logging
3. **Widget-Specific Settings**: Some "magic numbers" are actually widget-specific and shouldn't be constants

## 📈 Next Steps

1. Fix the high-priority magic numbers (quick win)
2. Create file utilities module (medium effort, high value)
3. Review and apply widget factory consistently
4. Consider error handling decorators for future refactoring

---
*Analysis completed: August 2025*

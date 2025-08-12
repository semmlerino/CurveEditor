# CurveEditor Services Consolidation Guide

## Overview

The CurveEditor services have been consolidated from 8 separate services to 4 focused services for improved maintainability and reduced complexity. This guide explains the consolidation and provides migration instructions.

## Consolidation Summary

### Previous Architecture (8 Services)
1. **curve_service.py** - Point manipulation, selection, UI updates, analysis
2. **unified_transform.py** - Coordinate transformations  
3. **view_state.py** - View state management
4. **file_service.py** - File I/O operations
5. **image_service.py** - Image loading and manipulation
6. **input_service.py** - Mouse, keyboard, and UI event handling
7. **history_service.py** - Undo/redo functionality
8. **dialog_service.py** - UI dialogs

### New Architecture (4 Services)

#### 1. TransformService (`services/transform_service.py`)
**Merged from:** `unified_transform.py` + `view_state.py`

**Responsibilities:**
- All coordinate transformations (data ↔ screen)
- View state management
- Transform caching for performance
- Immutable Transform and ViewState classes

**Key Classes:**
- `TransformService` - Main service class
- `Transform` - Immutable transformation parameters
- `ViewState` - Immutable view state

#### 2. DataService (`services/data_service.py`)
**Merged from:** Analysis methods from `curve_service.py` + `file_service.py` + `image_service.py`

**Responsibilities:**
- Curve data analysis (smoothing, filtering, gap filling, outlier detection)
- File I/O operations (JSON/CSV loading and saving)
- Image sequence management
- Recent files tracking

**Key Methods:**
- `smooth_moving_average()`, `filter_median()`, `filter_butterworth()`
- `fill_gaps()`, `detect_outliers()`
- `load_track_data()`, `save_track_data()`
- `load_image_sequence()`, `set_current_image_by_frame()`

#### 3. InteractionService (`services/interaction_service.py`)
**Merged from:** Point manipulation from `curve_service.py` + `input_service.py` + `history_service.py`

**Responsibilities:**
- Point manipulation (selection, moving, deletion)
- Mouse and keyboard input handling
- History management (undo/redo)
- Rectangle selection
- View navigation (pan, zoom)

**Key Methods:**
- `on_point_moved()`, `on_point_selected()`
- `handle_mouse_press()`, `handle_mouse_move()`, `handle_mouse_release()`
- `handle_wheel_event()`, `handle_key_press()`
- `add_to_history()`, `undo()`, `redo()`

#### 4. UIService (`services/ui_service.py`)
**Merged from:** `dialog_service.py` + UI update methods from `curve_service.py`

**Responsibilities:**
- All dialog operations (input dialogs, message boxes)
- Status bar updates
- UI component state management
- User notifications
- Context menu creation

**Key Methods:**
- `show_error()`, `show_warning()`, `show_info()`, `confirm_action()`
- `get_smooth_window_size()`, `get_filter_params()`, `get_offset_values()`
- `set_status()`, `clear_status()`, `update_ui_from_data()`
- `enable_ui_components()`, `update_button_states()`

## Migration Guide

### For Application Code

The `ServiceFacade` class has been updated to provide backward compatibility while using the new consolidated services internally.

#### Option 1: Use ServiceFacade (Recommended)
```python
from ui.service_facade import get_service_facade

# Get the facade instance
facade = get_service_facade(main_window)

# All existing methods still work
facade.smooth_curve(data, window_size=5)
facade.load_track_data()
facade.handle_mouse_press(view, event)
facade.show_error("Error message")
```

#### Option 2: Direct Service Access
```python
from services import (
    get_transform_service,
    get_data_service, 
    get_interaction_service,
    get_ui_service
)

# Get service instances
transform_service = get_transform_service()
data_service = get_data_service()
interaction_service = get_interaction_service()
ui_service = get_ui_service()

# Use services directly
smoothed_data = data_service.smooth_moving_average(data, window_size=5)
interaction_service.handle_mouse_press(view, event)
ui_service.show_error(parent, "Error message")
```

### Migration Steps

1. **Update imports:** Replace individual service imports with consolidated service imports
2. **Use ServiceFacade:** For minimal changes, use the ServiceFacade which provides backward compatibility
3. **Gradual migration:** Migrate to direct service usage over time for better clarity

### Code Examples

#### Before (8 services):
```python
from services.curve_service import CurveService
from services.file_service import FileService
from services.input_service import InputService
from services.dialog_service import DialogService

# Multiple service instances
curve_service = CurveService()
file_service = FileService()
input_service = InputService()
dialog_service = DialogService()

# Use different services for different operations
curve_service.smooth_moving_average(data)
file_service.load_track_data(widget)
input_service.handle_mouse_press(view, event)
dialog_service.show_error(widget, "Error")
```

#### After (4 services):
```python
from services import (
    get_data_service,
    get_interaction_service,
    get_ui_service
)

# Fewer service instances with clear responsibilities
data_service = get_data_service()
interaction_service = get_interaction_service()
ui_service = get_ui_service()

# Clear service boundaries
data_service.smooth_moving_average(data)
data_service.load_track_data(widget)
interaction_service.handle_mouse_press(view, event)
ui_service.show_error(widget, "Error")
```

## Benefits of Consolidation

1. **Reduced Complexity:** From 8 services to 4 focused services
2. **Clear Responsibilities:** Each service has a single, well-defined purpose
3. **Eliminated Duplication:** Removed overlapping functionality
4. **Better Organization:** Related functionality is now grouped together
5. **Simplified Dependencies:** Fewer inter-service dependencies
6. **Improved Maintainability:** Easier to understand and modify

## Backward Compatibility

- The old service files remain in place for backward compatibility
- The ServiceFacade provides fallback to legacy services if new ones aren't available
- Gradual migration is supported - you can use both old and new services during transition

## Testing

When testing the consolidated services:

1. **Unit tests:** Update tests to use the new service structure
2. **Integration tests:** Verify that consolidated services work together correctly
3. **Regression tests:** Ensure all existing functionality still works

## Future Deprecation

The legacy 8-service architecture will be deprecated in a future version. Plan to migrate to the new 4-service architecture:

- **Phase 1 (Current):** Both architectures available, ServiceFacade provides compatibility
- **Phase 2:** Deprecation warnings added to legacy services
- **Phase 3:** Legacy services removed, only 4-service architecture remains

## Questions or Issues?

If you encounter any issues during migration or have questions about the new architecture, please refer to the service documentation or file an issue in the project repository.
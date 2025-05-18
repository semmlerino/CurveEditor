# CurveEditor API Reference

## Services

### CurveService

The primary service for curve manipulation operations.

#### Methods

##### Point Selection

```python
# Select all points in the curve
CurveService.select_all_points(curve_view, main_window)

# Clear the current selection
CurveService.clear_selection(curve_view, main_window)

# Select points within a rectangular region
CurveService.select_points_in_rect(curve_view, main_window, selection_rect)

# Select a specific point by index
CurveService.select_point_by_index(curve_view, main_window, index)
```

##### Point Manipulation

```python
# Update a point's position
CurveService.update_point_position(curve_view, main_window, index, x, y)

# Toggle a point's interpolation status
CurveService.toggle_point_interpolation(curve_view, index)

# Change the nudge increment for point movement
CurveService.change_nudge_increment(curve_view, increase=True)
```

##### View Operations

```python
# Reset the view to default zoom and position
CurveService.reset_view(curve_view)
```

### UnifiedTransformationService

Centralized service for all coordinate transformations with caching and performance optimizations.

#### Core Methods

```python
# Create transform from curve view or view state
transform = UnifiedTransformationService.from_curve_view(curve_view)
transform = UnifiedTransformationService.from_view_state(view_state)

# Transform single point
screen_x, screen_y = UnifiedTransformationService.transform_point(transform, data_x, data_y)

# Transform multiple points efficiently (returns QPointF list)
qt_points = UnifiedTransformationService.transform_points_qt(transform, points)

# Inverse transformation
data_x, data_y = UnifiedTransformationService.inverse_transform_point(transform, screen_x, screen_y)
```

#### Caching and Performance

```python
# Get cache statistics
stats = UnifiedTransformationService.get_cache_stats()
# Returns: {'cache_size': int, 'max_cache_size': int}

# Clear cache manually (automatic management usually sufficient)
UnifiedTransformationService.clear_cache()

# Create stable transform for operations that modify data
transform = UnifiedTransformationService.create_stable_transform(curve_view)
```

#### Stability Context

```python
# Ensure transformations remain stable during data modifications
with UnifiedTransformationService.stable_transformation_context(curve_view):
    # Perform operations that modify curve data
    modify_curve_data()
    # Transformations automatically remain consistent
```

### CenteringZoomService

Manages view positioning and zoom operations.

#### Methods

```python
# Calculate centering offsets for display
offset_x, offset_y = CenteringZoomService.calculate_centering_offsets(
    widget_width, widget_height, display_width, display_height, offset_x, offset_y)

# Center the view on a specific point
CenteringZoomService.center_on_point(curve_view, point_idx)

# Reset the view to default state
CenteringZoomService.reset_view(curve_view)

# Zoom operations
CenteringZoomService.zoom_in(curve_view, factor=1.2)
CenteringZoomService.zoom_out(curve_view, factor=0.8)

# Pan the view
CenteringZoomService.pan_view(curve_view, delta_x, delta_y)
```

### VisualizationService

Controls visual aspects of curve display.

#### Methods

```python
# Update visual properties
VisualizationService.update_display_properties(curve_view, properties)

# Handle visual state changes
VisualizationService.refresh_display(curve_view)
```

### FileService

Handles file input/output operations.

#### Methods

```python
# Load curve data from file
FileService.load_curve_data(file_path)

# Save curve data to file
FileService.save_curve_data(curve_data, file_path)

# Import/export different formats
FileService.import_csv(file_path)
FileService.export_csv(curve_data, file_path)
```

### HistoryService

Manages undo/redo operations.

#### Methods

```python
# Record operation for undo capability
HistoryService.record_operation(operation_type, data)

# Undo last operation
HistoryService.undo()

# Redo last undone operation
HistoryService.redo()

# Clear history
HistoryService.clear_history()
```

## Core Classes

### Transform

Immutable class representing a coordinate transformation.

#### Constructor

```python
transform = Transform(
    scale=1.0,
    center_offset_x=0.0,
    center_offset_y=0.0,
    pan_offset_x=0.0,
    pan_offset_y=0.0,
    manual_offset_x=0.0,
    manual_offset_y=0.0,
    image_scale_adjustment=1.0,
    flip_y=False
)
```

#### Methods

```python
# Forward transformation
screen_x, screen_y = transform.apply(data_x, data_y)

# Inverse transformation
data_x, data_y = transform.apply_inverse(screen_x, screen_y)

# Create modified transform
new_transform = transform.with_scale(new_scale)
new_transform = transform.with_offsets(offset_x, offset_y)
```

#### Properties

```python
# Access transformation parameters
scale = transform.scale
center_offset_x = transform.center_offset_x
# ... other parameters

# Get unique hash for caching
cache_key = transform.cache_key()
```

### ViewState

Immutable class representing the current view configuration.

#### Creation

```python
# Create from curve view
view_state = ViewState.from_curve_view(curve_view)

# Create manually
view_state = ViewState(
    offset_x=0.0,
    offset_y=0.0,
    zoom_factor=1.0,
    widget_width=800,
    widget_height=600,
    # ... other parameters
)
```

#### Properties

```python
# Access view parameters
offset_x = view_state.offset_x
zoom_factor = view_state.zoom_factor
widget_width = view_state.widget_width
# ... other parameters
```

## Integration Layer

For backward compatibility and convenient access:

### Convenience Functions

```python
from services import get_transform, transform_points, stable_transform_operation

# Quick transform access
transform = get_transform(curve_view)

# Efficient point transformation
qt_points = transform_points(curve_view, points)

# Stable operation context
with stable_transform_operation(curve_view):
    # Your code here
    pass
```

### Installation

```python
from services.transformation_integration import install_unified_system

# Install unified system in curve view (one-time setup)
install_unified_system(curve_view)
```

## Error Handling

All services include comprehensive error handling:

```python
try:
    result = service_method(parameters)
except CurveEditorException as e:
    # Handle application-specific errors
    logger.error(f"Operation failed: {e}")
except Exception as e:
    # Handle unexpected errors
    logger.error(f"Unexpected error: {e}")
```

## Type Hints

The codebase includes comprehensive type hints for better IDE support:

```python
from typing import List, Tuple, Optional
from PyQt6.QtCore import QPointF

def transform_points(points: List[Tuple[float, float]]) -> List[QPointF]:
    # Implementation
    pass
```

## Best Practices

1. **Use batch transformations** instead of transforming points individually
2. **Wrap data modifications** with stable transformation contexts
3. **Prefer service methods** over direct manipulation
4. **Check for None values** in optional parameters
5. **Use type hints** for better code maintainability

# Coordinate Transformation System Integration Guide

This guide explains how to use the new coordinate transformation system to fix issues like curve shifting during smoothing operations.

## Table of Contents

1. [Overview](#overview)
2. [Key Components](#key-components)
3. [Quick Start](#quick-start)
4. [Integration Examples](#integration-examples)
5. [Migration Guide](#migration-guide)
6. [Troubleshooting](#troubleshooting)

## Overview

The coordinate transformation system provides a centralized, consistent way to transform coordinates between data space and screen space. It addresses issues like curve shifting by ensuring that the same transformation logic is used throughout the application.

**Benefits:**
- Consistent coordinate transformations
- Immutable objects prevent accidental state changes
- Single source of truth for transformation parameters
- Improved debugging with detailed logging
- Transformation caching for better performance

## Key Components

### ViewState

`ViewState` encapsulates all parameters that affect coordinate transformations:

```python
from services.view_state import ViewState

# Create from curve view
state = ViewState.from_curve_view(curve_view)

# Create manually
state = ViewState(
    display_width=1920,
    display_height=1080,
    widget_width=800,
    widget_height=600,
    zoom_factor=1.5,
    offset_x=10,
    offset_y=20
)

# Create modified copy
new_state = state.with_updates(zoom_factor=2.0)
```

### Transform

`Transform` applies a specific transformation to coordinates:

```python
from services.transform import Transform

# Create directly
transform = Transform(
    scale=1.5,
    center_offset_x=100,
    center_offset_y=150,
    pan_offset_x=10,
    pan_offset_y=20
)

# Apply to point
screen_x, screen_y = transform.apply(data_x, data_y)
```

### TransformationService

`TransformationService` provides high-level methods for coordinate transformations:

```python
from services.transformation_service import TransformationService

# Calculate transform from view state
transform = TransformationService.calculate_transform(view_state)

# Transform a point
screen_x, screen_y = TransformationService.transform_point(view_state, data_x, data_y)

# Transform multiple points
transformed_points = TransformationService.transform_points(view_state, points)
```

## Quick Start

For the fastest integration, use the transformation shim:

```python
from services.transformation_shim import install, transform_point, transform_points

# Install in main window
def __init__(self):
    super().__init__()
    # ... existing initialization ...
    install(self.curve_view)

# Use in methods that transform coordinates
def find_point_at(self, x, y):
    transformed_points = transform_points(self.curve_view, self.points)
    # Find closest point...
```

## Integration Examples

### Fixing Curve Shifting in Smoothing Operations

The key to fixing curve shifting is to use the same transform before and after changes:

```python
def apply_smooth_operation(self):
    # 1. Create a stable transform before changes
    from services.view_state import ViewState
    from services.transformation_service import TransformationService

    view_state = ViewState.from_curve_view(self.curve_view)
    stable_transform = TransformationService.calculate_transform(view_state)

    # 2. Store position of reference points (like the first point)
    if self.curve_data:
        first_point = self.curve_data[0]
        original_pos = stable_transform.apply(first_point[1], first_point[2])

    # 3. Apply smoothing (existing code)
    # ...

    # 4. Update view with preserved transform
    self.curve_view.setPoints(self.curve_data, self.image_width, self.image_height, preserve_view=True)

    # 5. Force consistent transform for final rendering
    if hasattr(self.curve_view, 'set_force_transform'):
        self.curve_view.set_force_transform(stable_transform)
```

### Updating paintEvent

For best results, refactor the paintEvent to use the transformation system:

```python
def paintEvent(self, event):
    # Get consistent transform for all operations
    from services.view_state import ViewState
    from services.transformation_service import TransformationService

    # Use forced transform if available (for operations like smoothing)
    if hasattr(self, '_force_transform') and self._force_transform:
        transform = self._force_transform
    else:
        view_state = ViewState.from_curve_view(self)
        transform = TransformationService.calculate_transform(view_state)

    # Use transform for all coordinate conversions
    # ...
```

### Other Coordinate Transformations

Replace all manual coordinate transformations with the new system:

```python
# Before
def transform_point(self, curve_view, x, y):
    # Multiple steps of scale calculation, offset application, etc.

# After
def transform_point(self, curve_view, x, y):
    from services.transformation_service import TransformationService
    from services.view_state import ViewState

    view_state = ViewState.from_curve_view(curve_view)
    return TransformationService.transform_point(view_state, x, y)
```

## Migration Guide

Follow these steps to gradually adopt the new system:

1. **Install the transformation shim**:
   ```python
   from services.transformation_shim import install
   install(self.curve_view)
   ```

2. **Fix critical operations** like smoothing:
   - Modify the smooth operation as shown in the examples
   - Add reference point tracking to detect shifts

3. **Update core rendering** in paintEvent:
   - Refactor to use a single transform for all coordinates
   - Add support for forced transforms

4. **Gradually replace other coordinate transformations**:
   - Update methods in CurveService
   - Update methods in CurveViewOperations
   - Update any custom coordinate transformations

5. **Remove the shim** once all code is migrated

## Troubleshooting

### Curve Still Shifting

If the curve is still shifting during operations:

1. Check that the same transform is used before and after changes:
   ```python
   # Log transform parameters
   params = transform.get_parameters()
   logger.info(f"Transform: scale={params['scale']}, center={params['center_offset']}")
   ```

2. Verify reference point positions:
   ```python
   # Track the first point
   first_point = self.curve_data[0]
   before_pos = transform.apply(first_point[1], first_point[2])
   # ... after changes ...
   after_pos = transform.apply(first_point[1], first_point[2])
   dx = after_pos[0] - before_pos[0]
   dy = after_pos[1] - before_pos[1]
   logger.info(f"Point shifted by ({dx}, {dy}) pixels")
   ```

3. Force consistent transformation:
   ```python
   # Store the initial transform
   self._saved_transform = transform

   # In paintEvent:
   transform = getattr(self, '_saved_transform', None) or calculate_transform()
   ```

### Performance Issues

If you notice performance issues:

1. Use transform caching:
   ```python
   # TransformationService caches transforms automatically
   # To clear cache if needed:
   TransformationService.clear_cache()
   ```

2. Transform points in bulk:
   ```python
   # Instead of:
   for point in points:
       tx, ty = transform.apply(point[1], point[2])

   # Use:
   transformed = TransformationService.transform_points(view_state, points)
   ```

3. Only recalculate transforms when necessary:
   ```python
   # Cache view state and transform
   if not hasattr(self, '_cached_view_state'):
       self._cached_view_state = ViewState.from_curve_view(self)
       self._cached_transform = TransformationService.calculate_transform(self._cached_view_state)

   # Only invalidate cache when parameters change
   def on_zoom_changed(self):
       self._cached_view_state = None  # Force recalculation
   ```

---

For more details, refer to the [full refactoring plan](coordinate_transformation_refactoring_plan.md) and the [example implementation](../examples/fix_curve_shift.py).

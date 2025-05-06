# Curve Shifting Fix Documentation

## Background

The CurveEditor application had a recurring issue where applying operations like smoothing, filtering, or other data modifications would cause the curve to visibly shift in the display. This happened despite efforts to preserve the view state using the `preserve_view=True` parameter in `setPoints` calls.

The underlying issue was that coordinate transformations were not being consistently applied before and after operations, leading to different transformations being used to display the same points.

## Solution Overview

We implemented a comprehensive solution consisting of:

1. A centralized **transformation service** that ensures consistent coordinate transformations
2. A **transform stabilizer** system that maintains view stability during curve operations
3. Modified **rendering code** that uses these stable transformations

This approach addresses the curve shifting problem by ensuring that the same transformation logic is applied consistently throughout the application lifecycle.

## Key Components

### TransformationService

The `TransformationService` provides a central point for calculating and applying transforms, ensuring consistent coordinate mappings throughout the application.

Key features:
- Creates transforms from view state objects
- Caches transforms for performance
- Provides methods for applying transforms to individual points or collections of points
- Methods to detect and diagnose curve shifting issues

### Transform Class

The `Transform` class represents a specific coordinate transformation with these components:
- Scale factor
- Center offset (for centering in widget)
- Pan offset (for user panning)
- Manual offset (for fine adjustments)
- Y-axis flip flag
- Display dimensions

### ViewState Class

The `ViewState` class captures all parameters that affect coordinate transformations:
- Widget dimensions
- Display dimensions
- Zoom factor
- Offset values
- Scale-to-image flag
- Y-axis flip flag

### TransformStabilizer

The `TransformStabilizer` module ensures stability during operations by:
- Tracking reference points before operations
- Verifying point positions after operations
- Providing additional stabilization if needed
- Offering a high-level API for wrapping operations in stable transformations

## Implementation Details

### Smoothing Operations

The smoothing operations have been refactored to use the stable transformation system:

1. Before any changes:
   - Get the current view state
   - Create a stable transform
   - Track reference point positions

2. During the operation:
   - Apply the smoothing to the data
   - Update data while maintaining view properties

3. After the operation:
   - Apply the same transform to the new data
   - Verify reference point positions to ensure stability
   - Apply additional stabilization if needed

### Rendering System

The `paintEvent` method in `CurveView` now uses the transformation system:

1. Get the current view state
2. Calculate a transform using TransformationService
3. Use this transform consistently for all rendering (curve, points, background)

### Diagnostics

The system includes diagnostic capabilities:
- Reference point tracking before/after operations
- Shift detection with configurable thresholds
- Warning logs when shifts exceed thresholds
- Debug visualization of transform parameters

## Benefits

This solution provides several key benefits:

1. **Consistency**: The same transformation logic is used everywhere
2. **Stability**: Operations maintain visual stability
3. **Extensibility**: Easy to add new operations that maintain stability
4. **Maintainability**: Centralized logic is easier to maintain
5. **Diagnostics**: Built-in shift detection helps identify issues

## Usage Examples

### Applying a Smooth Operation

```python
# Import the necessary modules
from services.transform_stabilizer import TransformStabilizer
from services.transformation_service import TransformationService

# Create a stable transform
transform = TransformationService.create_stable_transform_for_operation(curve_view)

# Track reference points
reference_points = TransformStabilizer.track_reference_points(curve_data, transform)

# Apply the operation
# ...

# Verify stability
is_stable = TransformStabilizer.verify_reference_points(
    modified_data, reference_points, transform, threshold=1.0
)
```

### Rendering with Stable Transforms

```python
# In paintEvent:
from services.view_state import ViewState
from services.transformation_service import TransformationService

# Get current view state
view_state = ViewState.from_curve_view(self)

# Create stable transform
transform = TransformationService.calculate_transform(view_state)

# Use it for all rendering
for point in points:
    tx, ty = transform.apply(point.x, point.y)
    # Draw at tx, ty
```

## Troubleshooting

If curve shifting issues persist:

1. Check the logs for warnings about significant point shifts
2. Verify that all parameters affecting the transformation are being preserved
3. Ensure the transformation system is installed (`install(curve_view)`)
4. Explicitly restore view properties after operations
5. Use `preserve_view=True` when setting points

### Common Issues

#### QPointF vs Tuple Return Type

In some cases, transformation functions may return QPointF objects instead of tuples, leading to unpacking errors. The system has robust handling for this:

- `CurveService.transform_point()` checks return types and converts QPointF to tuples when needed
- `enhanced_curve_view.py` has a wrapper around transform_point that converts different return types
- `TransformationService.transform_point_to_widget()` explicitly ensures tuple return values

If you see errors like `cannot unpack non-iterable PySide6.QtCore.QPointF object`, check that these conversion mechanisms are working properly in your context.

#### "Floating Curve" Issue

Sometimes the curve appears to "float" and not stick to the intended features in the background image. This happens when transformation parameters aren't applied consistently between the curve points and the background image rendering.

This has been fixed by ensuring:

1. The background image and curve points use identical transformation parameters
2. All offset components are applied consistently:
   - Center offsets (for positioning in the view)
   - Pan offsets (for user panning)
   - Manual offsets (for fine-tuning alignment)

If the curve still appears misaligned with the background:

1. Enable debug mode to see detailed transform parameters
2. Check that both curve and image are using the same transform logic
3. Ensure all offset components (center, pan, manual) are consistently applied
4. Verify that scale_to_image setting is respected for both curve and image

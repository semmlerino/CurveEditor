# Transformation System Guide

## Overview

The CurveEditor features a unified transformation system that handles all coordinate conversions between data space and screen space. This system replaced a fragmented approach that had multiple transformation implementations across different modules.

## Key Benefits

- **Performance**: 50-80% reduction in transformation calculations through intelligent caching
- **Consistency**: Single source of truth for all transformations
- **Stability**: Built-in drift detection and stability guarantees
- **Maintainability**: Clear, documented transformation pipeline

## Core Concepts

### Transformation Pipeline

Every transformation follows this 6-step pipeline:

1. **Image Scale Adjustment**: Adjusts for display scaling (optional)
2. **Y-Axis Flipping**: Inverts Y-coordinates if needed (optional)
3. **Main Scaling**: Applies the primary zoom factor
4. **Centering Offset**: Centers content in the viewport
5. **Pan Offset**: Applies user pan/drag movements
6. **Manual Offset**: Additional manual positioning adjustments

### Transform Class

The `Transform` class is immutable and encapsulates all transformation parameters:

```python
from services.unified_transform import Transform

# Create a transform
transform = Transform(
    scale=1.5,
    center_offset_x=10.0,
    center_offset_y=20.0,
    pan_offset_x=0.0,
    pan_offset_y=0.0,
    manual_offset_x=0.0,
    manual_offset_y=0.0,
    image_scale_adjustment=1.0,
    flip_y=False
)

# Apply transformations
screen_x, screen_y = transform.apply(data_x, data_y)
data_x, data_y = transform.apply_inverse(screen_x, screen_y)
```

### Caching System

The transformation service includes intelligent caching:

```python
from services.unified_transformation_service import UnifiedTransformationService

# Transforms are automatically cached based on their parameters
transform1 = UnifiedTransformationService.from_curve_view(curve_view)
transform2 = UnifiedTransformationService.from_curve_view(curve_view)  # Cache hit!

# Monitor cache performance
stats = UnifiedTransformationService.get_cache_stats()
print(f"Cache: {stats['cache_size']}/{stats['max_cache_size']}")
```

## Usage Patterns

### Basic Point Transformation

```python
# Single point
transform = get_transform(curve_view)
screen_x, screen_y = transform.apply(data_x, data_y)

# Multiple points efficiently
qt_points = transform_points(curve_view, points)
```

### Stable Operations

When modifying curve data, use the stability context to prevent transformation drift:

```python
from services import stable_transform_operation

def smooth_curve(curve_view):
    with stable_transform_operation(curve_view):
        # Modify curve data here
        curve_view.curve_data = apply_smoothing(curve_view.curve_data)
        # Transformations remain stable automatically
```

### Paint Event Optimization

Replace inefficient point-by-point transformations with batch operations:

```python
# OLD (inefficient)
def paintEvent(self, event):
    painter = QPainter(self)
    for point in self.points:
        tx, ty = transform_individual_point(point[1], point[2])
        painter.drawEllipse(tx, ty, 3, 3)

# NEW (efficient)
def paintEvent(self, event):
    painter = QPainter(self)
    if self.points:
        qt_points = transform_points(self, self.points)
        for qt_point in qt_points:
            painter.drawEllipse(qt_point, 3, 3)
```

## Advanced Features

### ViewState Integration

The `ViewState` class provides a complete snapshot of the view configuration:

```python
# Create view state
view_state = ViewState.from_curve_view(curve_view)

# Use with transformation service
transform = UnifiedTransformationService.from_view_state(view_state)
```

### Custom Transform Creation

For specialized use cases, create custom transforms:

```python
# Create transform with specific parameters
custom_transform = Transform(
    scale=2.0,
    center_offset_x=100.0,
    center_offset_y=50.0,
    flip_y=True
)

# Use for batch operations
results = [custom_transform.apply(x, y) for x, y in data_points]
```

### Debugging and Monitoring

Enable detailed logging to monitor transformation behavior:

```python
from services.logging_service import LoggingService

# Enable debug logging for transformations
LoggingService.set_level("unified_transform", "DEBUG")

# Monitor cache behavior
def monitor_cache():
    stats = UnifiedTransformationService.get_cache_stats()
    print(f"Cache efficiency: {stats['cache_size']} transforms cached")
```

## Migration from Legacy System

### Quick Migration

For immediate compatibility, install the unified system in your curve view:

```python
from services.transformation_integration import install_unified_system

# One-time installation
install_unified_system(curve_view)
```

### Gradual Migration

Replace old transformation calls incrementally:

```python
# Old approach
def old_transform_method(curve_view, x, y):
    # Complex manual transformation logic
    return transformed_x, transformed_y

# New approach
def new_transform_method(curve_view, x, y):
    transform = get_transform(curve_view)
    return transform.apply(x, y)
```

### Feature Flags

Control rollout with feature flags:

```python
from services.transformation_integration import set_use_unified_system

# Disable unified system if needed
set_use_unified_system(False)
```

## Performance Optimization

### Batch Processing

Always prefer batch operations for multiple points:

```python
# Inefficient
transformed_points = []
for point in points:
    tx, ty = transform.apply(point[0], point[1])
    transformed_points.append((tx, ty))

# Efficient
qt_points = UnifiedTransformationService.transform_points_qt(transform, points)
```

### Cache Management

The cache manages itself automatically, but you can optimize manually:

```python
# Clear cache during memory pressure
if memory_usage_high():
    UnifiedTransformationService.clear_cache()

# Customize cache size
UnifiedTransformationService.set_max_cache_size(200)
```

## Error Handling

The transformation system includes comprehensive error handling:

```python
try:
    transform = get_transform(curve_view)
    result = transform.apply(x, y)
except TransformationError as e:
    logger.error(f"Transformation failed: {e}")
    # Fallback to identity transform
    result = (x, y)
```

## Mathematical Foundation

### Forward Transformation

```
screen_x = (data_x * scale + center_offset_x + pan_offset_x + manual_offset_x) * image_scale_adjustment
screen_y = ((flip_y ? -data_y : data_y) * scale + center_offset_y + pan_offset_y + manual_offset_y) * image_scale_adjustment
```

### Inverse Transformation

```
data_x = (screen_x / image_scale_adjustment - center_offset_x - pan_offset_x - manual_offset_x) / scale
data_y = ((screen_y / image_scale_adjustment - center_offset_y - pan_offset_y - manual_offset_y) / scale) * (flip_y ? -1 : 1)
```

## Best Practices

1. **Use the Integration Layer**: Import convenience functions from `services`
2. **Batch Transformations**: Process multiple points at once
3. **Stable Contexts**: Wrap data modifications with stable operations
4. **Monitor Performance**: Check cache efficiency periodically
5. **Handle Errors**: Always include transformation error handling
6. **Document Assumptions**: Clearly document coordinate system assumptions

## Troubleshooting

### Common Issues

**Points appear to drift during operations**
- Ensure you're using `stable_transform_operation` context
- Check that you're not manually modifying transformation parameters during operations

**Poor performance with many points**
- Use batch transformation methods instead of individual point transforms
- Verify cache is enabled and working properly

**Inconsistent transformations**
- Ensure ViewState is created correctly from curve view
- Check that all transformation parameters are properly set

**Memory usage continues to grow**
- Monitor cache size with `get_cache_stats()`
- Consider manual cache clearing during intensive operations

### Debugging

Enable comprehensive logging to trace transformation behavior:

```python
import logging
logging.getLogger('unified_transform').setLevel(logging.DEBUG)
```

Check transformation parameters:

```python
transform = get_transform(curve_view)
print(f"Scale: {transform.scale}")
print(f"Offsets: {transform.center_offset_x}, {transform.center_offset_y}")
print(f"Cache key: {transform.cache_key()}")
```

Verify cache performance:

```python
stats = UnifiedTransformationService.get_cache_stats()
print(f"Cache hit ratio: {stats['cache_size']}/{stats['total_requests']}")
```

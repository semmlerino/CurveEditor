# Unified Transformation System Documentation

## Overview

The Unified Transformation System consolidates the previously fragmented coordinate transformation logic across the CurveEditor application. This system replaces multiple overlapping implementations with a single, coherent approach that ensures consistency and maintainability.

## Architecture

### Core Components

#### 1. Transform (`services/unified_transform.py`)
The immutable core class that encapsulates all transformation parameters and logic.

**Key Features:**
- Immutable design ensuring consistency
- Clear, documented transformation pipeline
- Efficient caching through hash-based keys
- Support for forward and inverse transformations

**Transformation Pipeline:**
1. Image scaling adjustment (if enabled)
2. Y-axis flipping (optional)
3. Main scaling application
4. Centering offset application
5. Pan offset application
6. Manual offset application

#### 2. UnifiedTransformationService (`services/unified_transformation_service.py`)
The centralized service providing transformation operations with caching and stability features.

**Key Features:**
- Transform creation from ViewState or CurveView
- Efficient batch point transformation
- Intelligent caching with size management
- Stability tracking for operations
- Backward compatibility methods

#### 3. TransformationIntegration (`services/transformation_integration.py`)
Integration layer providing backward compatibility and migration utilities.

**Key Features:**
- Drop-in replacements for existing methods
- Convenience functions for common operations
- Migration helpers and patches
- Feature flags for controlled rollout

## Usage Examples

### Basic Usage

```python
from services.transformation_integration import get_transform, transform_point

# Get a transform for a curve view
transform = get_transform(curve_view)

# Transform a single point
screen_x, screen_y = transform.apply(data_x, data_y)

# Transform using the convenience function
screen_x, screen_y = transform_point(curve_view, data_x, data_y)
```

### Batch Transformation

```python
from services.transformation_integration import transform_points

# Transform multiple points efficiently
points = [(0, 100, 200), (1, 300, 400), (2, 500, 600)]
qt_points = transform_points(curve_view, points)

# Use the points for drawing
for qt_point in qt_points:
    painter.drawEllipse(qt_point, 3, 3)
```

### Stable Operations

```python
from services.transformation_integration import stable_transform_operation

# Perform an operation with stable transformations
with stable_transform_operation(curve_view):
    # Modify curve data
    apply_smoothing_operation()
    # Transformations remain stable throughout
```

### Enhanced PaintEvent

```python
def paintEvent(self, event):
    painter = QPainter(self)

    # Get transform once for the entire paint operation
    transform = get_transform(self)

    # Transform all points efficiently
    if self.points:
        qt_points = UnifiedTransformationService.transform_points_qt(
            transform, self.points
        )

        # Draw using transformed points
        for qt_point in qt_points:
            painter.drawEllipse(qt_point, 3, 3)

    # Draw background image with correct positioning
    if self.background_image:
        img_x, img_y = transform.apply_for_image_position()
        # ... draw image at calculated position
```

## Migration Guide

### Step 1: Install Integration Layer

```python
from services.transformation_integration import install_unified_system

# Install in your curve view
install_unified_system(curve_view)
```

### Step 2: Update Code Gradually

**Old Approach:**
```python
# Recalculating transform for each operation
for point in self.points:
    tx, ty = CurveService.transform_point(self, point[1], point[2])
    painter.drawEllipse(tx, ty, 3, 3)
```

**New Approach:**
```python
# Calculate transform once, use many times
transform = get_transform(self)
qt_points = UnifiedTransformationService.transform_points_qt(transform, self.points)
for qt_point in qt_points:
    painter.drawEllipse(qt_point, 3, 3)
```

### Step 3: Apply Compatibility Patches

```python
from services.transformation_integration import MigrationHelper

# Apply all patches for backward compatibility
MigrationHelper.apply_all_patches()
```

### Step 4: Use Migration Script

```bash
# Run the migration script
python migrate_to_unified_transforms.py --full

# Or run individual steps
python migrate_to_unified_transforms.py --validate --patch-all --test --report
```

## Performance Benefits

### 1. Reduced Calculations
- Single transform calculation per operation instead of per-point
- Intelligent caching prevents redundant calculations
- Batch operations optimize memory usage

### 2. Cache Efficiency
- Transform caching with automatic size management
- Hash-based cache keys for fast lookups
- Cache statistics for monitoring

### 3. Memory Usage
- Immutable objects reduce memory allocation
- Efficient batch processing
- Automatic cache cleanup

## Stability Features

### 1. Drift Detection
The system can detect when points unexpectedly move in screen space:

```python
# Detect transformation drift during operations
drift_detected, drift_details = UnifiedTransformationService.detect_transformation_drift(
    before_points, after_points, before_transform, after_transform
)

if drift_detected:
    logger.warning(f"Transformation drift detected: {max(drift_details.values()):.2f}px")
```

### 2. Stable Context Manager
Ensures transformations remain stable during operations:

```python
with stable_transform_operation(curve_view) as stable_transform:
    # Perform operations that modify curve data
    # Reference points are tracked to verify stability
    perform_curve_modification()
```

### 3. Reference Point Tracking
Automatically tracks key points to verify transformation stability.

## Testing

### Running Tests

```bash
# Run all transformation tests
python -m pytest tests/test_unified_transformation_system.py -v

# Run specific test classes
python -m pytest tests/test_unified_transformation_system.py::TestUnifiedTransform -v
```

### Test Coverage
- Core Transform functionality
- UnifiedTransformationService operations
- Integration layer compatibility
- ViewState integration
- Error handling and edge cases

## Configuration

### Feature Flags

```python
from services.transformation_integration import set_use_unified_system

# Enable/disable the unified system
set_use_unified_system(True)  # Default: True
```

### Cache Configuration

```python
# Adjust cache size (default: 20)
UnifiedTransformationService._max_cache_size = 50

# Monitor cache usage
cache_stats = UnifiedTransformationService.get_cache_stats()
print(f"Cache usage: {cache_stats['cache_size']}/{cache_stats['max_cache_size']}")
```

## Backward Compatibility

### Existing Interfaces Supported
- `CurveService.transform_point()` - Patched to use unified system
- `TransformationService.transform_point_to_widget()` - Redirected to unified system
- All parameter signatures maintained

### Deprecation Strategy
1. **Phase 1**: Install unified system with compatibility patches
2. **Phase 2**: Update code to use new interfaces gradually
3. **Phase 3**: Remove old implementations
4. **Phase 4**: Clean up compatibility code

## Troubleshooting

### Common Issues

#### Transform Drift
**Symptoms**: Points appear to move during operations
**Solution**: Use stable transformation context
```python
with stable_transform_operation(curve_view):
    # Perform operation here
```

#### Performance Issues
**Symptoms**: Slow rendering or transformation
**Solution**: Use batch transformations
```python
# Instead of transforming points individually
qt_points = transform_points(curve_view, points)
```

#### Cache Memory Usage
**Symptoms**: Memory growth over time
**Solution**: Adjust cache size or clear periodically
```python
# Clear cache when needed
UnifiedTransformationService.clear_cache()
```

### Debug Logging

```python
from services.logging_service import LoggingService

# Enable debug logging for transformation components
LoggingService.set_level("unified_transform", "DEBUG")
LoggingService.set_level("unified_transformation_service", "DEBUG")
```

## API Reference

### Transform Class Methods

#### `apply(x: float, y: float) -> Tuple[float, float]`
Transform point from data to screen space.

#### `apply_inverse(screen_x: float, screen_y: float) -> Tuple[float, float]`
Transform point from screen to data space.

#### `apply_qt_point(x: float, y: float) -> QPointF`
Transform point and return as QPointF.

#### `apply_for_image_position() -> Tuple[float, float]`
Calculate background image position.

#### `with_updates(**kwargs) -> Transform`
Create new transform with updated parameters.

### UnifiedTransformationService Methods

#### `from_view_state(view_state: ViewState) -> Transform`
Create transform from ViewState.

#### `from_curve_view(curve_view) -> Transform`
Create transform from curve view.

#### `transform_points(transform: Transform, points: List) -> List[Tuple[float, float]]`
Transform multiple points efficiently.

#### `stable_transformation_context(curve_view)`
Context manager for stable operations.

### Integration Functions

#### `get_transform(curve_view) -> Transform`
Get transform for curve view.

#### `transform_point(curve_view, x: float, y: float) -> Tuple[float, float]`
Transform single point.

#### `transform_points(curve_view, points: List) -> List[QPointF]`
Transform multiple points.

#### `install_unified_system(curve_view)`
Install unified system in curve view.

## Future Improvements

### Planned Features
1. **GPU Acceleration**: Offload transformations to GPU for large datasets
2. **Advanced Caching**: Implement LRU cache with smarter eviction
3. **Transformation Animations**: Smooth transitions between transform states
4. **Undo/Redo Integration**: Better integration with history system

### Performance Optimizations
1. **SIMD Instructions**: Use vectorized operations for batch transformations
2. **Memory Pooling**: Reuse objects to reduce garbage collection
3. **Parallel Processing**: Transform points in parallel for large datasets

## Conclusion

The Unified Transformation System provides a robust, efficient, and maintainable approach to coordinate transformations in the CurveEditor. By consolidating fragmented implementations into a coherent system, it improves both performance and reliability while maintaining full backward compatibility.

For questions or issues, refer to the comprehensive test suite and example implementations provided in the `services/enhanced_curve_view_integration.py` module.

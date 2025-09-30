# Coordinate Transformation Migration Guide

This guide shows how to refactor existing code to use the unified transformation architecture.

## Architecture Overview

### Data Flow Pipeline
```
Raw Data (3DEqualizer, Nuke, etc.)
    ↓ [CoordinateMetadata.to_normalized()]
Normalized Internal Format (Qt top-left origin)
    ↓ [Transform.data_to_screen()]
Screen Coordinates (with zoom, pan, etc.)
```

### Key Components
1. **CoordinateMetadata**: Describes a coordinate system (origin, dimensions, etc.)
2. **CurveDataWithMetadata**: Wraps curve data with its coordinate system info
3. **UnifiedTransformService**: Single source of truth for ALL transformations
4. **Transform**: Handles display transformations (zoom, pan, etc.)

## Migration Examples

### 1. DataService - Burger Tracking Data Loader

#### BEFORE (Hardcoded Y-flip):
```python
# In services/data_service.py, lines 683-687
x = float(parts[1])
y = float(parts[2])
# Apply Y-flip for 3DEqualizer coordinates (bottom-origin to top-origin)
y = 720 - y  # HARDCODED HEIGHT!
trajectory.append((frame, x, y))
```

#### AFTER (Using unified system):
```python
from services.unified_transform_service import get_unified_transform_service
from core.coordinate_system import CoordinateSystem

# At the start of the method
transform_service = get_unified_transform_service()

# Detect or set source coordinate system
transform_service.set_source_coordinate_system("3de_720p")  # or detect from file

# When loading points
x = float(parts[1])
y = float(parts[2])
trajectory.append((frame, x, y))  # Keep raw coordinates

# After loading all data, normalize once
normalized_data = transform_service.normalize_curve_data(trajectory)
return normalized_data
```

### 2. FileLoadWorker - Direct 2D Track Loading

#### BEFORE (Hardcoded flip parameters):
```python
# In ui/main_window.py, line 180
data = self._load_2dtrack_data_direct(
    self.tracking_file_path,
    flip_y=True,  # HARDCODED!
    image_height=720  # HARDCODED!
)
```

#### AFTER (Using unified system):
```python
from services.unified_transform_service import get_unified_transform_service

# In FileLoadWorker.run()
transform_service = get_unified_transform_service()

# Detect coordinate system from file
metadata = transform_service.detect_coordinate_system(self.tracking_file_path)
transform_service.set_source_coordinate_system(
    metadata.system,
    metadata.width,
    metadata.height
)

# Load raw data without any transformation
raw_data = self._load_2dtrack_data_direct(
    self.tracking_file_path,
    flip_y=False,  # NO FLIP HERE!
    image_height=None  # Not needed
)

# Normalize data using the service
normalized_data = transform_service.normalize_curve_data(raw_data)
self.signals.tracking_data_loaded.emit(normalized_data)
```

### 3. FileLoadWorker - Refactored Loading Method

#### BEFORE (Flip logic in loader):
```python
def _load_2dtrack_data_direct(
    self, file_path: str, flip_y: bool = False, image_height: float = 720
) -> list[tuple[int, float, float]]:
    """Load with optional Y-flip."""
    # ... loading code ...
    if flip_y:
        y = image_height - y  # Manual flip
    data.append((frame, x, y))
```

#### AFTER (Clean separation):
```python
def _load_2dtrack_data_direct(
    self, file_path: str
) -> list[tuple[int, float, float]]:
    """Load raw data without transformation."""
    # ... loading code ...
    data.append((frame, x, y))  # Just raw data
    return data

# Transformation happens OUTSIDE the loader
```

### 4. CurveViewWidget - Using Complete Transform

#### BEFORE (Manual flip handling):
```python
# Somewhere in curve_view_widget.py
if self.flip_y_axis:
    y = self.height() - y
screen_x, screen_y = self.data_to_screen(x, y)
```

#### AFTER (Unified transformation):
```python
from services.unified_transform_service import get_unified_transform_service

# In initialization
self.transform_service = get_unified_transform_service()

# When transforming points
transform = self.transform_service.create_complete_transform(view_state)
screen_x, screen_y = transform.data_to_screen(x, y)
# Flip is handled automatically based on source metadata!
```

## Step-by-Step Migration Process

### Phase 1: Add New System (Parallel Operation)
1. Import `unified_transform_service` alongside existing code
2. Set source metadata when loading files
3. Log both old and new transformations to verify correctness

### Phase 2: Validate Transformations
```python
# Validation helper
def validate_transformation(old_point, new_point, tolerance=0.01):
    """Compare old and new transformation results."""
    old_x, old_y = old_point
    new_x, new_y = new_point

    if abs(old_x - new_x) > tolerance or abs(old_y - new_y) > tolerance:
        logger.warning(
            f"Transform mismatch: old=({old_x:.2f}, {old_y:.2f}), "
            f"new=({new_x:.2f}, {new_y:.2f})"
        )
        return False
    return True
```

### Phase 3: Remove Old Code
1. Remove hardcoded Y-flip logic from DataService
2. Remove flip_y parameters from FileLoadWorker
3. Remove hardcoded height values (720, etc.)
4. Update tests to use new system

## Benefits of Migration

1. **Single Source of Truth**: All transformations go through TransformService
2. **No Hardcoded Values**: Heights and flip logic are metadata-driven
3. **Extensible**: Easy to add new coordinate systems (Maya, Houdini, etc.)
4. **Type-Safe**: Coordinate metadata travels with data
5. **Testable**: Clear transformation pipeline with discrete steps

## Common Patterns

### Loading Files with Auto-Detection
```python
transform_service = get_unified_transform_service()

# Auto-detect from file
metadata = transform_service.detect_coordinate_system(file_path)
transform_service.set_source_coordinate_system(
    metadata.system,
    metadata.width,
    metadata.height
)

# Load and normalize
raw_data = load_raw_data(file_path)
normalized_data = transform_service.normalize_curve_data(raw_data)
```

### Exporting to Specific Format
```python
from core.coordinate_system import COORDINATE_SYSTEMS

# Get current normalized data
normalized_data = self.curve_widget.get_curve_data()

# Convert to target system
target_metadata = COORDINATE_SYSTEMS["nuke_hd"]
export_data = transform_service.denormalize_curve_data(
    normalized_data,
    target_metadata
)

# Save in target format
save_to_nuke(export_data)
```

### Handling Dynamic Image Dimensions
```python
# When loading an image sequence
image = load_first_image(image_path)
width, height = image.width(), image.height()

# Update source metadata with actual dimensions
transform_service.set_source_coordinate_system(
    "3de",  # or detected type
    width=width,
    height=height
)
```

## Testing the Migration

### Unit Test Example
```python
def test_coordinate_transformation():
    """Test that 3DE coordinates are properly normalized."""
    service = UnifiedTransformService()

    # Set 3DE 720p source
    service.set_source_coordinate_system("3de_720p")

    # Test data (3DE bottom-origin)
    raw_data = [(1, 640, 100)]  # Y=100 from bottom

    # Normalize (should flip Y)
    normalized = service.normalize_curve_data(raw_data)

    # In Qt coordinates, Y=100 from bottom is Y=620 from top
    assert normalized[0][2] == 620  # 720 - 100
```

### Integration Test Example
```python
def test_full_pipeline():
    """Test complete transformation pipeline."""
    service = UnifiedTransformService()

    # Simulate loading 3DE data
    service.set_source_coordinate_system("3de_720p")
    raw_data = [(1, 640, 360)]  # Center of 720p

    # Normalize
    normalized = service.normalize_curve_data(raw_data)

    # Create view state and transform
    view_state = ViewState(
        display_width=1280,
        display_height=720,
        widget_width=1920,
        widget_height=1080,
        zoom_factor=1.5
    )

    transform = service.create_complete_transform(view_state)

    # Transform to screen
    screen_x, screen_y = transform.data_to_screen(
        normalized[0][1],
        normalized[0][2]
    )

    # Verify screen coordinates
    assert screen_x > 0 and screen_y > 0
```

## Troubleshooting

### Issue: Points appear flipped after migration
**Solution**: Check that you're not applying flip twice. The unified system handles it automatically.

### Issue: Hardcoded height values don't match
**Solution**: Use `detect_coordinate_system()` or explicitly set dimensions when loading.

### Issue: Export doesn't match original format
**Solution**: Use `denormalize_curve_data()` with the correct target metadata.

## Summary

The unified transformation architecture provides:
- **Clear separation**: Raw → Normalized → Display
- **Type safety**: Metadata travels with data
- **Flexibility**: Easy to add new coordinate systems
- **Maintainability**: Single source of truth for transformations

By following this migration guide, you can safely refactor existing code to use the new system while maintaining backward compatibility during the transition.

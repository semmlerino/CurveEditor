# Migration Guide: Unified Transformation System

## Overview

This guide helps you migrate from the old fragmented transformation system to the new unified approach. The migration is designed to be gradual and backward-compatible.

## Migration Strategies

### Option 1: Automatic Migration

Use the migration script for a complete automated upgrade:

```bash
# Validate current code
python migrate_to_unified_transforms.py --validate

# Apply automatic patches
python migrate_to_unified_transforms.py --full

# Verify the migration
python migrate_to_unified_transforms.py --test
```

### Option 2: Manual Migration

For more control, migrate components manually:

```python
# Step 1: Install the unified system
from services.transformation_integration import install_unified_system
install_unified_system(curve_view)

# Step 2: Update imports
# Old:
from services.transformation_service import TransformationService

# New:
from services import get_transform, transform_points, stable_transform_operation
```

### Option 3: Gradual Migration

Migrate one component at a time while maintaining compatibility:

```python
# Enable the unified system with fallback
from services.transformation_integration import set_use_unified_system
set_use_unified_system(True)

# Old code continues to work through compatibility layer
# Gradually replace with new APIs
```

## Common Migration Patterns

### 1. Single Point Transformations

**Before:**
```python
# Old method
tx, ty = TransformationService.transform_point(view_state, x, y)

# Old service method
screen_x, screen_y = CurveService.transform_point(curve_view, data_x, data_y)
```

**After:**
```python
# New unified approach
transform = get_transform(curve_view)
screen_x, screen_y = transform.apply(data_x, data_y)

# Or using convenience function
screen_x, screen_y = transform_point(curve_view, data_x, data_y)
```

### 2. Batch Point Transformations

**Before:**
```python
# Inefficient: transforming points individually
transformed_points = []
for point in points:
    view_state = ViewState.from_curve_view(curve_view)
    tx, ty = TransformationService.transform_point(view_state, point[1], point[2])
    transformed_points.append(QPointF(tx, ty))
```

**After:**
```python
# Efficient: batch transformation
qt_points = transform_points(curve_view, points)
```

### 3. Paint Event Updates

**Before:**
```python
def paintEvent(self, event):
    painter = QPainter(self)
    for point in self.curve_data:
        view_state = ViewState.from_curve_view(self)
        tx, ty = TransformationService.transform_point(view_state, point[1], point[2])
        painter.drawEllipse(tx - 2, ty - 2, 4, 4)
```

**After:**
```python
def paintEvent(self, event):
    painter = QPainter(self)
    if self.curve_data:
        qt_points = transform_points(self, self.curve_data)
        for qt_point in qt_points:
            painter.drawEllipse(qt_point.x() - 2, qt_point.y() - 2, 4, 4)
```

### 4. Stable Transform Context

**Before:**
```python
def modify_curve_data(self):
    # Risk of transformation drift
    self.curve_data = apply_operation(self.curve_data)
    self.update()
```

**After:**
```python
def modify_curve_data(self):
    with stable_transform_operation(self):
        self.curve_data = apply_operation(self.curve_data)
        self.update()
```

### 5. ViewState Creation

**Before:**
```python
# Manual ViewState creation
view_state = ViewState(
    offset_x=self.offset_x,
    offset_y=self.offset_y,
    zoom_factor=self.zoom_factor,
    # ... many parameters
)
transform = TransformationService.create_transform(view_state)
```

**After:**
```python
# Simplified creation
transform = get_transform(self)
```

## Migration Checklist

### Phase 1: Preparation
- [ ] Run migration validation: `python migrate_to_unified_transforms.py --validate`
- [ ] Review current transformation usage in your code
- [ ] Backup important files before migration
- [ ] Test critical functionality before changes

### Phase 2: Installation
- [ ] Install unified system: `install_unified_system(curve_view)`
- [ ] Update imports to use convenience functions
- [ ] Apply compatibility patches if needed
- [ ] Verify basic functionality still works

### Phase 3: Code Updates
- [ ] Replace individual point transformations with batch operations
- [ ] Update paint event methods to use `transform_points()`
- [ ] Wrap data-modifying operations with `stable_transform_operation()`
- [ ] Remove manual ViewState creation where possible

### Phase 4: Optimization
- [ ] Monitor cache performance with `get_cache_stats()`
- [ ] Profile performance to identify remaining bottlenecks
- [ ] Update documentation and code comments
- [ ] Remove deprecated import statements

### Phase 5: Validation
- [ ] Run comprehensive tests
- [ ] Verify transformation stability during operations
- [ ] Check memory usage patterns
- [ ] Test with large datasets

## Breaking Changes

### Removed APIs

These APIs are deprecated and should be replaced:

```python
# DEPRECATED: Do not use
TransformationService.transform_point_direct()
TransformStabilizer.apply_stabilization()
transform_fix.compensate_for_drift()

# REPLACED WITH: Unified APIs
get_transform()
transform_points()
stable_transform_operation()
```

### Changed Behavior

1. **Transform Caching**: Transforms are now cached automatically
2. **Stable Operations**: Drift compensation is automatic within stable contexts
3. **Batch Processing**: Multiple points are processed more efficiently
4. **Error Handling**: More comprehensive error handling and logging

### Import Changes

Update these imports:

```python
# Old imports to replace:
from services.transformation_service import TransformationService
from services.transform_stabilizer import TransformStabilizer
from transform_fix import compensate_for_drift

# New unified imports:
from services import get_transform, transform_points, stable_transform_operation
from services.unified_transformation_service import UnifiedTransformationService
```

## Rollback Plan

If you need to rollback the migration:

```python
# Disable unified system
from services.transformation_integration import set_use_unified_system
set_use_unified_system(False)

# Old system will continue to work through compatibility layer
```

For complete rollback:

```bash
# Use git to revert changes
git revert <migration-commit-hash>

# Or restore from backup
cp -r backup/ ./
```

## Testing Migration

### Automated Tests

```bash
# Run the full test suite
python -m pytest tests/

# Test specifically transformation functionality
python -m pytest tests/test_unified_transformation_system.py

# Run performance benchmarks
python migrate_to_unified_transforms.py --benchmark
```

### Manual Testing

1. **Load a test curve file**
2. **Verify point selection works correctly**
3. **Test zoom and pan operations**
4. **Check point editing functionality**
5. **Verify paint performance is improved**

### Validation Script

Run the migration validation to check for issues:

```bash
python migrate_to_unified_transforms.py --validate
```

This will check for:
- Deprecated API usage
- Performance bottlenecks
- Potential compatibility issues
- Missing error handling

## Common Issues and Solutions

### Issue: Points appear in wrong positions
**Solution**: Ensure ViewState creation includes all required parameters

### Issue: Performance doesn't improve
**Solution**: Verify you're using batch transformations instead of individual point operations

### Issue: Tests fail after migration
**Solution**: Update test expectations for new transformation behavior

### Issue: Memory usage increases
**Solution**: Monitor cache size and clear manually if needed

## Performance Expectations

After migration, you should see:
- **50-80% reduction** in transformation calculations
- **30-50% faster** rendering with large datasets
- **Stable memory usage** through intelligent caching
- **Eliminated transformation drift** during operations

## Support

For migration assistance:
1. Check the [transformation system documentation](transformation-system.md)
2. Review the [API reference](api-reference.md)
3. Examine example implementations in `services/enhanced_curve_view_integration.py`
4. Create an issue in the repository for specific problems

The migration is designed to be safe and incremental. Start with the automatic migration script, then gradually optimize with manual changes as needed.

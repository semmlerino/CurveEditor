# Transformation Stabilization Guide

## Overview

This guide explains the transformation stabilization system that prevents curve point shifting during operations like smoothing, filtering, and interpolation.

## Problem Background

During operations that modify curve data (like smoothing), users observed unexpected curve shifting in the UI. This occurred even when the actual data points weren't substantially changed. The issue stemmed from inconsistent coordinate transformations being applied before and after operations.

For example, during a smooth operation:
1. Original data is displayed with transformation X
2. Data is modified by the smoothing algorithm
3. Modified data is displayed with a slightly different transformation Y
4. This results in visual "jumping" of the curve even though the data points were only slightly adjusted

## Solution: Stable Transformation System

The solution is to consistently apply the same transformation throughout an operation. The key components are:

### 1. TransformStabilizer Module

Located in `services/transform_stabilizer.py`, this module provides utilities for:
- Tracking reference points before operations
- Verifying point positions after operations
- Applying consistent transformations

### 2. ViewState and Transform Classes

- `ViewState`: Captures all parameters affecting the view state (zoom, offset, dimensions, etc.)
- `Transform`: Encapsulates a specific transformation that can be applied consistently

### 3. Implementation Pattern

For operations that modify curve data, follow this pattern:

```python
# 1. Create a stable transform BEFORE modification
stable_transform = TransformationService.create_stable_transform_for_operation(curve_view)

# 2. Track reference points with this transform
reference_points = TransformStabilizer.track_reference_points(original_data, stable_transform)

# 3. Modify the data
modified_data = perform_operation(original_data)

# 4. Update the view with preserve_view=True
curve_view.setPoints(modified_data, width, height, preserve_view=True)

# 5. Verify stability and apply corrections if needed
is_stable = TransformStabilizer.verify_reference_points(
    modified_data, reference_points, stable_transform)
```

## How It Works

1. **Parameter Consistency**:
   - All view parameters (zoom, offset, scale mode) are explicitly preserved
   - The same transform is used to position points before and after operations

2. **Reference Point Tracking**:
   - Key points (first, middle, last) are tracked in screen coordinates
   - After operations, their screen positions are verified to be stable

3. **Delayed Updates**:
   - A small delay is added after updates to ensure proper rendering
   - Secondary verification is performed after the delay

## Best Practices

1. Always use `preserve_view=True` when calling `setPoints` after modifying data

2. Explicitly restore view state parameters (zoom, offset, scale mode) before setting points:
   ```python
   curve_view.zoom_factor = saved_zoom
   curve_view.offset_x = saved_offset_x
   curve_view.offset_y = saved_offset_y
   curve_view.scale_to_image = saved_scale_to_image
   ```

3. Use the TransformStabilizer for any operation that modifies curve data:
   ```python
   from services.transform_stabilizer import TransformStabilizer
   ```

4. Disable auto-centering during operations to prevent unexpected view changes

## Debugging

When point shifting occurs, the system logs detailed information:
- Point positions before and after operations
- Transform parameters
- Shift distances for reference points

To diagnose persistent issues:
1. Check the logs for warnings about significant point shifts
2. Review the transform parameters before and after operations
3. Ensure all view state parameters are correctly preserved
4. Check for any setPoints calls without preserve_view=True

## Example Implementation

See `main_window.py:apply_smooth_operation()` for a complete implementation of the stabilization pattern.

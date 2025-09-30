# Zoom Floating Bug - Root Cause Analysis and Fix

## Issue Summary
When zooming with the mouse wheel, curves appeared to float/drift instead of zooming smoothly around the cursor position. The point under the mouse cursor should remain stationary during zoom, with everything else scaling around it.

## Root Cause

The bug was caused by a **mismatch between the scale used for center offset calculations and the scale used for the actual coordinate transformations**.

### The Problem

In `services/transform_service.py`, there were two critical locations where center offsets were calculated:

1. **`Transform.from_view_state()` method (lines 829-862)**
2. **`TransformService._create_transform_cached()` method (lines 1018-1036)**

Both methods were using `base_scale` to calculate center offsets, while the actual transformation was using `scale` (which equals `view_state.zoom_factor`, which is actually `base_scale * user_zoom_factor`).

### Mathematical Analysis

Given:
- `base_scale` = 0.421875 (fitting scale for content in widget)
- `user_zoom` = 1.0 initially, then 1.1 after zoom
- `total_scale` = `base_scale * user_zoom`

**Before zoom (user_zoom = 1.0):**
- `total_scale` = 0.421875
- Center offsets calculated with `base_scale` (0.421875) ✓ Correct
- Transformation uses `total_scale` (0.421875) ✓ Matches

**After zoom (user_zoom = 1.1):**
- `total_scale` = 0.4640625
- Center offsets calculated with `base_scale` (0.421875) ✗ Wrong!
- Transformation uses `total_scale` (0.4640625) ✗ Mismatch!

This mismatch caused the centering to be incorrect for the actual scale being applied, resulting in points drifting during zoom operations.

### Code Flow Analysis

1. **CurveViewWidget._update_transform()** (ui/curve_view_widget.py:556-572)
   - Calculates `total_scale = base_scale * self.zoom_factor`
   - Creates ViewState with `zoom_factor=total_scale` and `base_scale=base_scale`

2. **Transform.from_view_state()** (services/transform_service.py:819-894)
   - Sets `scale = view_state.zoom_factor` (the total_scale)
   - **BUG**: Used `base_scale` for center offset calculations instead of `scale`

3. **Transform.data_to_screen()** (services/transform_service.py:637-691)
   - Applies transformation using `self.scale` (the total_scale)
   - Center offsets don't match the scale, causing drift

## The Fix

Replace `base_scale` with `scale` in all center offset calculations to ensure the centering matches the transformation scale.

### Changes Made

**File: `services/transform_service.py`**

1. **In `Transform.from_view_state()` method:**
   - Lines 836, 837, 841, 842, 845, 846, 849, 855, 856
   - Changed from: `* base_scale`
   - Changed to: `* scale`

2. **In `TransformService._create_transform_cached()` method:**
   - Lines 1023, 1024, 1026, 1027, 1028, 1034, 1035
   - Changed from: `* base_scale` and `elif base_scale == 1.0`
   - Changed to: `* scale` and `elif scale == 1.0`

## Verification

### Test Results

**Before Fix:**
```
Initial position: data(640, 360) -> screen(400.00, 300.00)
After zoom 1.1x: data(640, 360) -> screen(436.00, 320.25)
Drift: (36.00, 20.25)
BUG CONFIRMED: Points drift during zoom!
```

**After Fix:**
```
Initial position: data(640, 360) -> screen(400.00, 300.00)
After zoom 1.1x: data(640, 360) -> screen(400.00, 300.00)
Drift: (0.00, 0.00)
✓ SUCCESS: No drift detected - zoom is working correctly!
```

### WheelEvent Simulation

The fix was verified to work correctly with the actual `wheelEvent` handler logic:
- Point under cursor stays fixed at (500.0, 350.0)
- Pan offsets are correctly adjusted to compensate for zoom
- No floating or drifting behavior

## Impact

This fix resolves the persistent zoom floating bug that occurred when:
- Zooming with the mouse wheel
- Using any data type (3DEqualizer, pixel tracking, etc.)
- At any zoom level

The fix ensures that the mathematical relationship between center offsets and transformation scale is consistent, providing smooth, stable zoom behavior with the cursor position as the pivot point.

## Prevention

To prevent similar issues in the future:
1. **Consistent Scale Usage**: Always use the same scale value for both center offset calculations and transformations
2. **Clear Variable Naming**: Distinguish between `base_scale`, `user_zoom`, and `total_scale`
3. **Mathematical Verification**: Ensure transformations are mathematically reversible
4. **Comprehensive Testing**: Test zoom behavior at multiple zoom levels and cursor positions

---
*Fix applied: January 2025*

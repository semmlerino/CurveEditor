# Zoom-Float Bug Fix Summary

## Problem
The curves were floating/drifting during zoom operations because the widget was passing a compound scale (`fit_scale * zoom_factor`) as the `zoom_factor` to ViewState, causing incorrect pan adjustments.

## Root Cause
- `curve_view_widget.py` calculated `total_scale = fit_scale * zoom_factor`
- Passed `total_scale` as `zoom_factor` to ViewState
- Transform treated this as simple zoom, not compound
- Pan adjustments assumed wrong scale basis

## Solution Implemented

### 1. Separated fit_scale and zoom_factor
- Added `fit_scale: float = 1.0` field to ViewState dataclass
- Changed ViewState to track both values independently
- `zoom_factor` now represents user zoom only
- `fit_scale` represents scale to fit content in widget

### 2. Fixed precision loss
- Changed ViewState `display_width` and `display_height` from `int` to `float`
- Removed premature `int()` conversions in curve_view_widget
- Maintains sub-pixel precision throughout pipeline

### 3. Fixed Transform to apply scales correctly
- Transform now calculates: `scale = view_state.fit_scale * view_state.zoom_factor`
- Applied consistently in:
  - `Transform.from_view_state()`
  - `TransformService._create_transform_cached()`
  - `TransformService._create_transform_direct()`

### 4. Made zoom operations atomic
- Capture state before changes
- Calculate all adjustments with consistent state
- Single cache invalidation after all changes
- Simplified pan adjustment calculation

## Files Modified
1. `services/transform_service.py`
   - Added `fit_scale` field to ViewState
   - Changed display dimensions to float
   - Updated Transform methods to use `fit_scale * zoom_factor`

2. `ui/curve_view_widget.py`
   - Removed `total_scale` compound calculation
   - Pass `fit_scale` and `zoom_factor` separately to ViewState
   - Removed `int()` conversions
   - Made wheelEvent zoom operations atomic

## Test Results
✅ All tests pass:
- Custom zoom bug test confirms no drift
- Scale compounding test verifies correct application
- All existing transform tests pass (12/12)
- All curve view tests pass (39/39)

## Impact
- **Bug Fixed**: Curves no longer float during zoom
- **Precision Improved**: Sub-pixel accuracy maintained
- **Architecture Clarified**: Clear separation of concerns between fit and user zoom
- **Code Simplified**: Removed confusing compound scale calculations

## Next Steps (Optional)
While the critical bug is fixed, the architecture could be further simplified by:
1. Merging ViewState and Transform classes
2. Removing unused configuration classes
3. Reducing abstraction layers from 10 to 3
4. Implementing vectorized coordinate transformations

The zoom-float bug is now resolved with minimal, surgical changes to the codebase.

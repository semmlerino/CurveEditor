# Background-Curve Zoom Synchronization Fix

## Problem
The curve points and background image were moving separately during zoom operations, causing them to drift apart. This made it impossible to accurately track features in the background image.

## Root Cause
The background rendering was using a simplified transformation approach:
```python
# OLD CODE - Incorrect approach
screen_x, screen_y = transform.data_to_screen(0, 0)
scale = params.get("scale", 1.0)
scaled_width = int(background_image.width() * scale)
scaled_height = int(background_image.height() * scale)
```

This bypassed critical parts of the transformation pipeline, particularly the **pan offset adjustments** that occur during zoom to keep the mouse position stationary.

## The Fix
Transform **both corners** of the background through the complete transformation pipeline:

```python
# NEW CODE - Correct approach
# Transform top-left corner
top_left_x, top_left_y = transform.data_to_screen(0, 0)

# Transform bottom-right corner
bottom_right_x, bottom_right_y = transform.data_to_screen(
    background_image.width(), background_image.height()
)

# Calculate dimensions from transformed corners
target_width = bottom_right_x - top_left_x
target_height = bottom_right_y - top_left_y

# Draw using fully transformed coordinates
painter.drawPixmap(
    int(top_left_x), int(top_left_y),
    int(target_width), int(target_height),
    background_image
)
```

## Why This Works
The Transform service applies these transformations in order:
1. **Image scaling** - Scales the image data
2. **Main scaling** - Applies zoom factor
3. **Center offset** - Centers the view
4. **Pan offset** - User panning AND zoom-point adjustments
5. **Manual offset** - Additional user adjustments

During zoom operations, the pan offset is adjusted to keep the mouse position stationary on screen. By transforming both corners through this pipeline, the background receives all the same adjustments as curve points.

## Technical Details
- **File**: `rendering/optimized_curve_renderer.py`
- **Method**: `_render_background_optimized()`
- **Lines**: 444-486

The key insight is that extracting just the scale parameter missed the pan offset adjustments. The full transformation pipeline must be used for both background and curve points to stay synchronized.

## Result
✅ Background and curve stay perfectly synchronized during zoom
✅ Zoom at mouse position works correctly for both elements
✅ Pan operations maintain alignment
✅ All transformations are mathematically consistent

---
*Fixed: Sprint 11 Day 3 - Critical Rendering Synchronization Bug*

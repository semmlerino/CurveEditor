# Background Image Panning Bug Fix

## Issue
When panning the view (dragging with middle mouse button), the curve points moved correctly but the background image remained static at a fixed position.

## Root Cause
The bug was in `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/rendering/optimized_curve_renderer.py` at line 457 in the `_render_background_optimized` method.

The background was being drawn at fixed coordinates:
```python
painter.drawPixmap(0, 0, curve_view.width(), curve_view.height(), background_image)
```

This ignored all transformations (pan offsets, zoom, centering) that were being applied to the curve points.

## Why Previous Fix Attempts Failed
- Attempts to fix `rendering/curve_renderer.py` didn't work because that file is not being used
- The actual rendering path uses `OptimizedCurveRenderer` (introduced for 47x performance improvement)
- The rendering pipeline is: `CurveViewWidget.paintEvent()` → `OptimizedCurveRenderer.render()` → `_render_background_optimized()`

## Solution
Modified the `_render_background_optimized` method to:
1. Get the Transform object from curve_view
2. Transform the background image position using `transform.data_to_screen(0, 0)`
3. Apply the scale factor to the image dimensions
4. Draw the pixmap at the transformed position with scaled size

## Fixed Code
The method now properly transforms the background:
```python
def _render_background_optimized(self, painter: QPainter, curve_view: Any) -> None:
    """Optimized background rendering with proper transformations."""
    background_image = getattr(curve_view, "background_image", None)
    if not background_image:
        return

    opacity = getattr(curve_view, "background_opacity", 1.0)
    if opacity < 1.0:
        painter.setOpacity(opacity)

    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform,
                         self._render_quality == RenderQuality.HIGH)

    # Apply transformations to background
    if hasattr(curve_view, "get_transform"):
        transform = curve_view.get_transform()

        # Transform top-left corner from data to screen coordinates
        screen_x, screen_y = transform.data_to_screen(0, 0)

        # Get scale factor
        params = transform.get_parameters()
        scale = params.get("scale", 1.0)

        # Calculate scaled dimensions
        scaled_width = int(background_image.width() * scale)
        scaled_height = int(background_image.height() * scale)

        # Draw at transformed position with scaled size
        painter.drawPixmap(
            int(screen_x),
            int(screen_y),
            scaled_width,
            scaled_height,
            background_image
        )
    else:
        # Fallback if transform not available
        painter.drawPixmap(0, 0, curve_view.width(), curve_view.height(), background_image)

    if opacity < 1.0:
        painter.setOpacity(1.0)
```

## Verification
The fix has been tested and verified to work correctly. The background image now:
- Moves synchronously with curve points when panning
- Scales properly when zooming
- Respects all transformation parameters (pan_offset, manual_offset, center_offset)

## Files Modified
- `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/rendering/optimized_curve_renderer.py` (lines 444-486)

## Backup
A backup of the original file was created at:
- `/mnt/c/CustomScripts/Python/Work/Linux/CurveEditor/rendering/optimized_curve_renderer.py.backup`

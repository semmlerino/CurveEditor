"""Improved background rendering implementation for OptimizedCurveRenderer."""

from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPainter, QPen


def _render_background_optimized_improved(painter: QPainter, curve_view) -> None:
    """
    Improved background rendering with proper transformations and Y-flip support.

    This implementation addresses:
    - Y-axis flipping support
    - Better subpixel accuracy with QRectF
    - Proper coordinate transformation chain
    """
    background_image = getattr(curve_view, "background_image", None)
    if not background_image:
        return

    opacity = getattr(curve_view, "background_opacity", 1.0)
    if opacity <= 0:
        return  # Skip rendering if fully transparent

    painter.save()

    # Set opacity if needed
    if opacity < 1.0:
        painter.setOpacity(opacity)

    # Use appropriate rendering quality
    painter.setRenderHint(
        QPainter.RenderHint.SmoothPixmapTransform, getattr(curve_view, "_render_quality", "high") == "high"
    )

    # Get the transform for consistent coordinate mapping
    if hasattr(curve_view, "get_transform"):
        transform = curve_view.get_transform()
        params = transform.get_parameters()

        # Get background position in screen coordinates
        # Background image starts at data coordinates (0, 0)
        screen_x, screen_y = transform.data_to_screen(0, 0)

        # Get scale from transform
        scale = params.get("scale", 1.0)

        # Calculate scaled dimensions
        img_width = background_image.width()
        img_height = background_image.height()
        scaled_width = img_width * scale
        scaled_height = img_height * scale

        # Handle Y-axis flipping if enabled
        flip_y = params.get("flip_y", False)
        if flip_y:
            display_height = params.get("display_height", curve_view.height())
            if display_height > 0:
                # Apply Y-flip transformation
                painter.translate(0, display_height)
                painter.scale(1, -1)
                # Adjust Y position for flipped coordinates
                screen_y = display_height - screen_y - scaled_height

        # Use QRectF for better subpixel accuracy
        target_rect = QRectF(screen_x, screen_y, scaled_width, scaled_height)
        source_rect = QRectF(0, 0, img_width, img_height)

        # Draw the background with proper transformations
        painter.drawPixmap(target_rect, background_image, source_rect)

    else:
        # Fallback to simple scaling if transform not available
        painter.drawPixmap(0, 0, curve_view.width(), curve_view.height(), background_image)

    painter.restore()


def _render_grid_optimized_improved(painter: QPainter, curve_view) -> None:
    """
    Improved grid rendering that moves with the coordinate system.

    Grid lines are drawn in data space and transformed to screen space,
    ensuring they stay aligned with the background and curve data.
    """
    if not hasattr(curve_view, "get_transform"):
        # Fallback to static grid if transform not available
        _render_grid_static(painter, curve_view)
        return

    transform = curve_view.get_transform()
    params = transform.get_parameters()

    # Set grid appearance
    pen = QPen(QColor(100, 100, 100, 50))
    pen.setWidth(1)
    painter.setPen(pen)

    # Determine grid spacing in data coordinates
    scale = params.get("scale", 1.0)
    base_spacing = 50  # Base grid spacing in pixels

    # Adjust spacing based on zoom level to maintain reasonable density
    if scale > 2:
        data_spacing = base_spacing / scale
    elif scale < 0.5:
        data_spacing = base_spacing * 2 / scale
    else:
        data_spacing = base_spacing / scale

    # Round to nice numbers
    if data_spacing < 1:
        data_spacing = 0.5
    elif data_spacing < 5:
        data_spacing = round(data_spacing)
    elif data_spacing < 10:
        data_spacing = 5
    elif data_spacing < 50:
        data_spacing = round(data_spacing / 10) * 10
    else:
        data_spacing = round(data_spacing / 50) * 50

    # Get visible data range
    width = curve_view.width()
    height = curve_view.height()

    # Convert screen corners to data coordinates to find visible range
    data_min_x, data_max_y = transform.screen_to_data(0, 0)
    data_max_x, data_min_y = transform.screen_to_data(width, height)

    # Draw vertical grid lines
    start_x = (data_min_x // data_spacing) * data_spacing
    end_x = (data_max_x // data_spacing + 1) * data_spacing

    x = start_x
    while x <= end_x:
        screen_x, _ = transform.data_to_screen(x, 0)
        if 0 <= screen_x <= width:
            painter.drawLine(int(screen_x), 0, int(screen_x), height)
        x += data_spacing

    # Draw horizontal grid lines
    start_y = (data_min_y // data_spacing) * data_spacing
    end_y = (data_max_y // data_spacing + 1) * data_spacing

    y = start_y
    while y <= end_y:
        _, screen_y = transform.data_to_screen(0, y)
        if 0 <= screen_y <= height:
            painter.drawLine(0, int(screen_y), width, int(screen_y))
        y += data_spacing


def _render_grid_static(painter: QPainter, curve_view) -> None:
    """Fallback static grid rendering."""
    pen = QPen(QColor(100, 100, 100, 50))
    pen.setWidth(1)
    painter.setPen(pen)

    step = 50
    width = curve_view.width()
    height = curve_view.height()

    # Vertical lines
    for x in range(0, width + step, step):
        painter.drawLine(x, 0, x, height)

    # Horizontal lines
    for y in range(0, height + step, step):
        painter.drawLine(0, y, width, y)

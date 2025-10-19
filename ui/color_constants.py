"""Standard color constants for curve rendering.

This module centralizes color definitions to:
- Eliminate hardcoded QColor(...) literals
- Enable easy theme customization
- Provide semantic color names

TODO: Integrate with ui/color_manager.py theming system for runtime theme
switching. Current implementation uses hardcoded values but there is parallel
color management in color_manager.py that should eventually be unified.
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPen


class CurveColors:
    """Standard colors for curve rendering.

    Note: INACTIVE_GRAY is unique to this module and has no equivalent in
    color_manager.py. WHITE corresponds to STATUS_COLORS["normal"] in
    color_manager.py.
    """

    # Base colors
    WHITE: QColor = QColor(255, 255, 255)
    INACTIVE_GRAY: QColor = QColor(128, 128, 128, 128)  # Semi-transparent

    @staticmethod
    def get_inactive_pen(width: int = 1) -> QPen:
        """Create standard inactive segment pen.

        Args:
            width: Pen width in pixels

        Returns:
            QPen with inactive styling (gray, dashed)
        """
        pen = QPen(CurveColors.INACTIVE_GRAY)
        pen.setWidth(width)
        pen.setStyle(Qt.PenStyle.DashLine)
        return pen

    @staticmethod
    def get_active_pen(color: QColor | None = None, width: int = 2) -> QPen:
        """Create standard active segment pen.

        Args:
            color: Pen color (default: white)
            width: Pen width in pixels

        Returns:
            QPen with active styling (solid line)
        """
        pen_color = color if color else CurveColors.WHITE
        pen = QPen(pen_color)
        pen.setWidth(width)
        return pen

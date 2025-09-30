#!/usr/bin/env python

"""
Rendering components for CurveView.

This package contains specialized rendering classes extracted from the monolithic
CurveView paintEvent method to improve maintainability and testability.
"""

try:
    from .optimized_curve_renderer import OptimizedCurveRenderer

    CurveRenderer = OptimizedCurveRenderer  # pyright: ignore[reportAssignmentType]

    __all__ = ["CurveRenderer"]
except ImportError:
    # Stub when PySide6 is not available
    class CurveRenderer:  # type: ignore[no-redef]
        """Stub renderer for startup compatibility."""

        def __init__(self) -> None:
            pass

    __all__ = ["CurveRenderer"]

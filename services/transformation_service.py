#!/usr/bin/env python

"""
Unified Transformation Service for CurveEditor

This service consolidates all transformation-related functionality that was
previously scattered across 4 different services:
- TransformationService: Transform creation, point transformation, caching
- TransformationService: View centering, zooming, fit operations
- TransformationIntegration: Compatibility layer and drift detection
- UnifiedTransform: Core Transform class (kept as separate module)

Following KISS principle: One service for all coordinate transformation operations.
"""

import threading
from typing import TYPE_CHECKING

from PySide6.QtCore import QPointF

from core.protocols import CurveViewProtocol
from services.logging_service import LoggingService
from services.unified_transform import Transform
from services.view_state import ViewState

if TYPE_CHECKING:
    from PySide6.QtGui import QWheelEvent

logger = LoggingService.get_logger("transformation_service")


class TransformationService:
    """
    Unified service for all coordinate transformation operations.

    This service consolidates the functionality of 4 previously separate services
    into a single, maintainable class following KISS and DRY principles.

    Responsibilities:
    - Transform creation from ViewState or CurveView
    - Point coordinate transformations with caching
    - View operations (centering, zooming, panning)
    - Stability tracking and drift detection
    - Compatibility with existing interfaces
    """

    # Transform cache for performance optimization
    _transform_cache: dict[int, Transform] = {}
    _max_cache_size: int = 20
    _cache_lock: threading.RLock = threading.RLock()

    # Stable transform cache for maintaining consistency
    _stable_transform_cache: dict[int, Transform] = {}
    _stable_cache_lock: threading.RLock = threading.RLock()

    # =============================================================================
    # TRANSFORM CREATION (formerly TransformationService)
    # =============================================================================

    @staticmethod
    def from_view_state(view_state: ViewState) -> Transform:
        """
        Create a Transform from a ViewState object.

        Args:
            view_state: ViewState containing transformation parameters

        Returns:
            Transform object configured from the view state
        """
        logger.debug(
            f"Creating transform from ViewState: scale={view_state.zoom_factor}, "
            + f"center=({view_state.offset_x}, {view_state.offset_y})"
        )

        return Transform(
            scale=view_state.zoom_factor,
            center_offset_x=view_state.offset_x,
            center_offset_y=view_state.offset_y,
            pan_offset_x=0.0,  # ViewState doesn't have pan offsets - use defaults
            pan_offset_y=0.0,  # ViewState doesn't have pan offsets - use defaults
            manual_offset_x=view_state.manual_x_offset,
            manual_offset_y=view_state.manual_y_offset,
            flip_y=view_state.flip_y_axis,
            display_height=view_state.display_height,
            image_scale_x=1.0,  # Default image scaling
            image_scale_y=1.0,  # Default image scaling
            scale_to_image=view_state.scale_to_image,
        )

    @staticmethod
    def from_curve_view(curve_view: CurveViewProtocol) -> Transform:
        """
        Create a Transform from a CurveView object.

        Args:
            curve_view: CurveView instance with transformation attributes

        Returns:
            Transform object configured from the curve view
        """
        # Extract transformation parameters from curve view attributes
        scale = getattr(curve_view, "zoom_factor", 1.0)
        center_offset_x = getattr(curve_view, "center_offset_x", 0.0)
        center_offset_y = getattr(curve_view, "center_offset_y", 0.0)
        pan_offset_x = getattr(curve_view, "offset_x", 0.0)
        pan_offset_y = getattr(curve_view, "offset_y", 0.0)
        manual_offset_x = getattr(curve_view, "x_offset", 0.0)
        manual_offset_y = getattr(curve_view, "y_offset", 0.0)
        flip_y_axis = getattr(curve_view, "flip_y_axis", True)
        scale_to_image = getattr(curve_view, "scale_to_image", True)

        # Get image dimensions if available
        background_image = getattr(curve_view, "background_image", None)
        if background_image and not background_image.isNull():
            background_image.width()
            image_height = background_image.height()
        else:
            getattr(curve_view, "width", lambda: 800)()
            image_height = getattr(curve_view, "height", lambda: 600)()

        logger.debug(f"Creating transform from CurveView: scale={scale}, center=({center_offset_x}, {center_offset_y})")

        return Transform(
            scale=scale,
            center_offset_x=center_offset_x,
            center_offset_y=center_offset_y,
            pan_offset_x=pan_offset_x,
            pan_offset_y=pan_offset_y,
            manual_offset_x=manual_offset_x,
            manual_offset_y=manual_offset_y,
            flip_y=flip_y_axis,
            display_height=image_height,
            scale_to_image=scale_to_image,
        )

    # =============================================================================
    # POINT TRANSFORMATION (formerly TransformationService)
    # =============================================================================

    @staticmethod
    def transform_point(transform: Transform, x: float, y: float) -> tuple[float, float]:
        """
        Transform a single point from data coordinates to screen coordinates.

        Args:
            transform: Transform object to apply
            x: Data X coordinate
            y: Data Y coordinate

        Returns: tuple of (screen_x, screen_y)
        """
        return transform.apply(x, y)

    @staticmethod
    def transform_points(transform: Transform, points: list[tuple[int, float, float]]) -> list[tuple[float, float]]:
        """
        Transform multiple points from data coordinates to screen coordinates.

        Args:
            transform: Transform object to apply
            points: list of points in format [(frame, x, y), ...]

        Returns: list of transformed points as [(screen_x, screen_y), ...]
        """
        logger.debug(f"Transforming {len(points)} points")
        return [transform.apply(p[1], p[2]) for p in points]

    @staticmethod
    def transform_points_qt(transform: Transform, points: list[tuple[int, float, float]]) -> list[QPointF]:
        """
        Transform multiple points to Qt QPointF objects.

        Args:
            transform: Transform object to apply
            points: list of points in format [(frame, x, y), ...]

        Returns: list of QPointF objects
        """
        logger.debug(f"Transforming {len(points)} points to QPointF")
        return [QPointF(*transform.apply(p[1], p[2])) for p in points]

    # =============================================================================
    # STABILITY TRACKING AND CACHING (formerly TransformationService)
    # =============================================================================

    @staticmethod
    def get_stable_transform(curve_view: CurveViewProtocol) -> Transform:
        """
        Get a stable transform for the curve view, using caching for consistency.

        Args:
            curve_view: CurveView instance

        Returns:
            Cached Transform object for stable operations
        """
        curve_view_id = id(curve_view)

        with TransformationService._stable_cache_lock:
            if curve_view_id not in TransformationService._stable_transform_cache:
                transform = TransformationService.from_curve_view(curve_view)
                TransformationService._stable_transform_cache[curve_view_id] = transform
                logger.debug(f"Created stable transform for curve_view {curve_view_id}")

                # Manage cache size
                if len(TransformationService._stable_transform_cache) > TransformationService._max_cache_size:
                    # Remove oldest entries
                    items = list(TransformationService._stable_transform_cache.items())
                    for key, _ in items[: -TransformationService._max_cache_size]:
                        del TransformationService._stable_transform_cache[key]

            return TransformationService._stable_transform_cache[curve_view_id]

    @staticmethod
    def create_stable_transform(curve_view: CurveViewProtocol) -> Transform:
        """
        Create a new stable transform for the curve view, bypassing cache.

        Args:
            curve_view: CurveView instance

        Returns:
            New Transform object
        """
        transform = TransformationService.from_curve_view(curve_view)
        curve_view_id = id(curve_view)

        with TransformationService._stable_cache_lock:
            TransformationService._stable_transform_cache[curve_view_id] = transform

        logger.debug(f"Created new stable transform for curve_view {curve_view_id}")
        return transform

    # =============================================================================
    # VIEW OPERATIONS (formerly TransformationService)
    # =============================================================================

    @staticmethod
    def calculate_centering_offsets(
        widget_width: float,
        widget_height: float,
        display_width: float,
        display_height: float,
        offset_x: float = 0,
        offset_y: float = 0,
    ) -> tuple[float, float]:
        """
        Calculate offsets needed to center content in the widget.

        Args:
            widget_width: Width of the widget in pixels
            widget_height: Height of the widget in pixels
            display_width: Width of content to display
            display_height: Height of content to display
            offset_x: Additional X offset
            offset_y: Additional Y offset

        Returns: tuple of (center_x, center_y) offsets
        """
        center_x = (widget_width - display_width) / 2.0 + offset_x
        center_y = (widget_height - display_height) / 2.0 + offset_y

        logger.debug(
            f"Calculated centering offsets: ({center_x:.2f}, {center_y:.2f}) "
            f"for widget ({widget_width}, {widget_height}) and display ({display_width}, {display_height})"
        )

        return center_x, center_y

    @staticmethod
    def center_on_point(curve_view: CurveViewProtocol, point_idx: int) -> bool:
        """
        Center the view on a specific point.

        Args:
            curve_view: CurveView instance
            point_idx: Index of point to center on

        Returns:
            True if centering was successful
        """
        try:
            main_window = getattr(curve_view, "main_window", None)
            if not main_window or not hasattr(main_window, "curve_data"):
                return False

            curve_data = main_window.curve_data
            if not curve_data or point_idx < 0 or point_idx >= len(curve_data):
                # Update status message about failure
                if main_window and hasattr(main_window, "update_status_message"):
                    if not curve_data:
                        main_window.update_status_message("Centering failed: No curve data")
                    else:
                        main_window.update_status_message(f"Centering failed: Invalid point index {point_idx}")
                curve_view.update()
                return False

            point = curve_data[point_idx]
            point_x, point_y = point[1], point[2]

            # Get widget dimensions
            widget_width = curve_view.width()
            widget_height = curve_view.height()

            # Center the view on this point
            center_x = widget_width / 2.0
            center_y = widget_height / 2.0

            # Update offsets to center on the point
            offset_x = center_x - point_x
            offset_y = center_y - point_y
            setattr(curve_view, "center_offset_x", offset_x)
            setattr(curve_view, "center_offset_y", offset_y)
            setattr(curve_view, "offset_x", offset_x)
            setattr(curve_view, "offset_y", offset_y)

            curve_view.update()

            # Update status message if main_window has status bar
            if hasattr(main_window, "update_status_message"):
                main_window.update_status_message(f"Centered view on point {point_idx}")

            logger.info(f"Centered view on point {point_idx} at ({point_x:.2f}, {point_y:.2f})")
            return True

        except Exception as e:
            logger.error(f"Failed to center on point {point_idx}: {e}")
            return False

    @staticmethod
    def pan_view(curve_view: CurveViewProtocol, dx: float, dy: float) -> None:
        """
        Pan the view by the specified offsets.

        Args:
            curve_view: CurveView instance
            dx: X offset to pan by
            dy: Y offset to pan by
        """
        try:
            current_offset_x = getattr(curve_view, "offset_x", 0.0)
            current_offset_y = getattr(curve_view, "offset_y", 0.0)

            setattr(curve_view, "offset_x", current_offset_x + dx)
            setattr(curve_view, "offset_y", current_offset_y + dy)

            curve_view.update()
            logger.debug(f"Panned view by ({dx:.2f}, {dy:.2f})")

        except Exception as e:
            logger.error(f"Failed to pan view: {e}")

    @staticmethod
    def center_on_selected_point(
        curve_view: CurveViewProtocol | None, point_idx: int = -1, preserve_zoom: bool = True
    ) -> bool:
        """
        Center the view on the selected point.

        Args:
            curve_view: CurveView instance
            point_idx: Point index to center on (-1 for current selection)
            preserve_zoom: Whether to preserve current zoom level

        Returns:
            True if centering was successful
        """
        if not curve_view:
            return False

        try:
            # Determine point index to center on
            if point_idx == -1:
                point_idx = getattr(curve_view, "selected_point_idx", -1)

            if point_idx == -1:
                # Try to get from selected_points set
                selected_points = getattr(curve_view, "selected_points", set())
                if selected_points:
                    point_idx = min(selected_points)

            if point_idx == -1:
                logger.warning("No point selected for centering")
                # Update status message about failure
                main_window = getattr(curve_view, "main_window", None)
                if main_window and hasattr(main_window, "update_status_message"):
                    main_window.update_status_message("Centering failed: No point selected")
                curve_view.update()
                return False

            result = TransformationService.center_on_point(curve_view, point_idx)

            # Handle preserve_zoom parameter
            if result and not preserve_zoom:
                setattr(curve_view, "zoom_factor", 1.0)
                curve_view.update()

            return result

        except Exception as e:
            logger.error(f"Failed to center on selected point: {e}")
            return False

    @staticmethod
    def zoom_to_fit(curve_view: CurveViewProtocol) -> None:
        """
        Zoom to fit all curve data in the view.

        Args:
            curve_view: CurveView instance
        """
        try:
            main_window = getattr(curve_view, "main_window", None)
            if not main_window or not hasattr(main_window, "curve_data"):
                return

            curve_data = main_window.curve_data
            if not curve_data:
                return

            # Find bounding box of all points
            x_coords = [p[1] for p in curve_data]
            y_coords = [p[2] for p in curve_data]

            if not x_coords or not y_coords:
                return

            min_x, max_x = min(x_coords), max(x_coords)
            min_y, max_y = min(y_coords), max(y_coords)

            data_width = max_x - min_x
            data_height = max_y - min_y

            if data_width <= 0 or data_height <= 0:
                return

            # Get widget dimensions
            widget_width = curve_view.width()
            widget_height = curve_view.height()

            # Calculate zoom factor to fit data with some padding
            padding_factor = 0.9  # 10% padding
            zoom_x = (widget_width * padding_factor) / data_width
            zoom_y = (widget_height * padding_factor) / data_height
            zoom_factor = min(zoom_x, zoom_y)

            # Set zoom factor
            setattr(curve_view, "zoom_factor", zoom_factor)

            # Center on data
            center_x = (min_x + max_x) / 2.0
            center_y = (min_y + max_y) / 2.0

            setattr(curve_view, "center_offset_x", widget_width / 2.0 - center_x * zoom_factor)
            setattr(curve_view, "center_offset_y", widget_height / 2.0 - center_y * zoom_factor)

            curve_view.update()
            logger.info(f"Zoomed to fit: zoom={zoom_factor:.3f}, center=({center_x:.2f}, {center_y:.2f})")

        except Exception as e:
            logger.error(f"Failed to zoom to fit: {e}")

    @staticmethod
    def fit_selection(curve_view: CurveViewProtocol) -> bool:
        """
        Zoom to fit the selected points.

        Args:
            curve_view: CurveView instance

        Returns:
            True if fit selection was successful
        """
        try:
            main_window = getattr(curve_view, "main_window", None)
            selected_points = getattr(curve_view, "selected_points", set())

            if not main_window or not hasattr(main_window, "curve_data") or not selected_points:
                return False

            curve_data = main_window.curve_data
            if not curve_data:
                return False

            # Get coordinates of selected points
            selected_coords = []
            for idx in selected_points:
                if 0 <= idx < len(curve_data):
                    point = curve_data[idx]
                    selected_coords.append((point[1], point[2]))

            if not selected_coords:
                return False

            # Find bounding box of selected points
            x_coords = [p[0] for p in selected_coords]
            y_coords = [p[1] for p in selected_coords]

            min_x, max_x = min(x_coords), max(x_coords)
            min_y, max_y = min(y_coords), max(y_coords)

            data_width = max_x - min_x
            data_height = max_y - min_y

            # Handle single point case
            if data_width <= 0:
                data_width = 100  # Arbitrary width for single point
            if data_height <= 0:
                data_height = 100  # Arbitrary height for single point

            # Get widget dimensions
            widget_width = curve_view.width()
            widget_height = curve_view.height()

            # Calculate zoom factor with padding
            padding_factor = 0.8  # 20% padding for selection
            zoom_x = (widget_width * padding_factor) / data_width
            zoom_y = (widget_height * padding_factor) / data_height
            zoom_factor = min(zoom_x, zoom_y)

            # Set zoom factor
            setattr(curve_view, "zoom_factor", zoom_factor)

            # Center on selection
            center_x = (min_x + max_x) / 2.0
            center_y = (min_y + max_y) / 2.0

            setattr(curve_view, "center_offset_x", widget_width / 2.0 - center_x * zoom_factor)
            setattr(curve_view, "center_offset_y", widget_height / 2.0 - center_y * zoom_factor)

            curve_view.update()
            logger.info(f"Fit selection: zoom={zoom_factor:.3f}, {len(selected_points)} points")
            return True

        except Exception as e:
            logger.error(f"Failed to fit selection: {e}")
            return False

    @staticmethod
    def handle_wheel_event(curve_view: CurveViewProtocol, event: "QWheelEvent") -> None:
        """
        Handle mouse wheel events for zooming.

        Args:
            curve_view: CurveView instance
            event: Qt wheel event
        """
        try:
            # Get zoom parameters
            angle_delta = event.angleDelta().y()
            zoom_in_factor = 1.2
            zoom_out_factor = 0.8

            current_zoom = getattr(curve_view, "zoom_factor", 1.0)

            if angle_delta > 0:
                # Zoom in
                new_zoom = current_zoom * zoom_in_factor
            else:
                # Zoom out
                new_zoom = current_zoom * zoom_out_factor

            # Clamp zoom factor
            new_zoom = max(0.1, min(50.0, new_zoom))

            setattr(curve_view, "zoom_factor", new_zoom)
            curve_view.update()

            logger.debug(f"Wheel zoom: {current_zoom:.3f} → {new_zoom:.3f}")

        except Exception as e:
            logger.error(f"Failed to handle wheel event: {e}")

    @staticmethod
    def zoom_in(curve_view: CurveViewProtocol, factor: float = 1.2) -> None:
        """
        Zoom in by the specified factor.

        Args:
            curve_view: CurveView instance
            factor: Zoom factor to apply
        """
        try:
            current_zoom = getattr(curve_view, "zoom_factor", 1.0)
            new_zoom = max(0.1, min(50.0, current_zoom * factor))

            setattr(curve_view, "zoom_factor", new_zoom)
            curve_view.update()

            logger.debug(f"Zoom in: {current_zoom:.3f} → {new_zoom:.3f}")

        except Exception as e:
            logger.error(f"Failed to zoom in: {e}")

    @staticmethod
    def zoom_out(curve_view: CurveViewProtocol, factor: float = 0.8) -> None:
        """
        Zoom out by the specified factor.

        Args:
            curve_view: CurveView instance
            factor: Zoom factor to apply
        """
        try:
            current_zoom = getattr(curve_view, "zoom_factor", 1.0)
            new_zoom = max(0.1, min(50.0, current_zoom * factor))

            setattr(curve_view, "zoom_factor", new_zoom)
            curve_view.update()

            logger.debug(f"Zoom out: {current_zoom:.3f} → {new_zoom:.3f}")

        except Exception as e:
            logger.error(f"Failed to zoom out: {e}")

    @staticmethod
    def toggle_auto_center(curve_view: CurveViewProtocol) -> bool:
        """
        Toggle auto-centering mode.

        Args:
            curve_view: CurveView instance

        Returns:
            New auto-center state
        """
        try:
            main_window = getattr(curve_view, "main_window", None)
            if not main_window:
                return False

            current_state = getattr(main_window, "auto_center_enabled", False)
            new_state = not current_state

            setattr(main_window, "auto_center_enabled", new_state)

            logger.info(f"Auto-center toggled: {current_state} → {new_state}")
            return new_state

        except Exception as e:
            logger.error(f"Failed to toggle auto center: {e}")
            return False

    @staticmethod
    def reset_view(curve_view: CurveViewProtocol) -> None:
        """
        Reset the view to default zoom, position, and transformation parameters.

        Args:
            curve_view: CurveView instance to reset
        """
        try:
            # Reset zoom to default
            setattr(curve_view, "zoom_factor", 1.0)

            # Reset all offsets to zero
            setattr(curve_view, "center_offset_x", 0.0)
            setattr(curve_view, "center_offset_y", 0.0)
            setattr(curve_view, "offset_x", 0.0)
            setattr(curve_view, "offset_y", 0.0)
            setattr(curve_view, "pan_offset_x", 0.0)
            setattr(curve_view, "pan_offset_y", 0.0)
            setattr(curve_view, "manual_offset_x", 0.0)
            setattr(curve_view, "manual_offset_y", 0.0)
            setattr(curve_view, "x_offset", 0.0)
            setattr(curve_view, "y_offset", 0.0)

            # Reset transformation flags to defaults
            setattr(curve_view, "flip_y_axis", True)
            setattr(curve_view, "scale_to_image", True)

            # Clear any cached transforms for this view
            curve_view_id = id(curve_view)
            with TransformationService._stable_cache_lock:
                if curve_view_id in TransformationService._stable_transform_cache:
                    del TransformationService._stable_transform_cache[curve_view_id]

            # Trigger a repaint
            curve_view.update()

            logger.info("View reset to default settings")

        except Exception as e:
            logger.error(f"Failed to reset view: {e}")

    # =============================================================================
    # CACHE MANAGEMENT
    # =============================================================================

    @staticmethod
    def clear_caches() -> None:
        """Clear all transformation caches."""
        with TransformationService._cache_lock:
            TransformationService._transform_cache.clear()

        with TransformationService._stable_cache_lock:
            TransformationService._stable_transform_cache.clear()

        logger.info("All transformation caches cleared")

    @staticmethod
    def clear_cache() -> None:
        """Clear all transformation caches (alias for clear_caches)."""
        TransformationService.clear_caches()

    @staticmethod
    def auto_center_view(main_window, preserve_zoom: bool = False) -> bool:
        """Auto-center the view on all curve data.

        Args:
            main_window: Main window instance with curve_view and curve_data
            preserve_zoom: Whether to preserve current zoom level

        Returns:
            True if centering was successful
        """
        try:
            if not hasattr(main_window, "curve_view") or not hasattr(main_window, "curve_data"):
                return False

            curve_view = main_window.curve_view
            curve_data = main_window.curve_data

            if not curve_data:
                return False

            # Get all point coordinates
            x_coords = [point[1] for point in curve_data]
            y_coords = [point[2] for point in curve_data]

            if not x_coords or not y_coords:
                return False

            # Calculate center of all data
            center_x = sum(x_coords) / len(x_coords)
            center_y = sum(y_coords) / len(y_coords)

            # Get widget dimensions
            widget_width = curve_view.width()
            widget_height = curve_view.height()

            # Calculate centering offsets
            view_center_x = widget_width / 2.0
            view_center_y = widget_height / 2.0

            # Update offsets to center on data
            setattr(curve_view, "center_offset_x", view_center_x - center_x)
            setattr(curve_view, "center_offset_y", view_center_y - center_y)
            setattr(curve_view, "offset_x", view_center_x - center_x)
            setattr(curve_view, "offset_y", view_center_y - center_y)

            if not preserve_zoom:
                # Auto-fit zoom as well
                TransformationService.zoom_to_fit(curve_view)

            curve_view.update()
            logger.info(f"Auto-centered view on data center ({center_x:.2f}, {center_y:.2f})")
            return True

        except Exception as e:
            logger.error(f"Failed to auto-center view: {e}")
            return False


# Backward compatibility aliases
TransformationService = TransformationService
TransformationService = TransformationService
ExtendedUnifiedTransformationService = TransformationService

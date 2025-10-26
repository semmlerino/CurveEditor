#!/usr/bin/env python
"""
Coordinate system service for transform operations.

Handles coordinate system detection, metadata management, and coordinate
transformations between different systems (3DEqualizer, Maya, Qt, etc.).
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.transform_core import Transform, ViewState

from core.coordinate_system import (
    COORDINATE_SYSTEMS,
    CoordinateMetadata,
    CoordinateOrigin,
    CoordinateSystem,
    create_source_metadata,
)
from core.type_aliases import CurveDataList

logger = logging.getLogger("coordinate_service")


class CoordinateService:
    """
    Service for coordinate system handling and transformations.

    Manages coordinate metadata, system detection, and data normalization
    between different coordinate systems used by various tools.
    """

    def __init__(self) -> None:
        """Initialize the CoordinateService."""
        # Coordinate system tracking
        self._source_metadata: CoordinateMetadata | None = None
        self._data_normalized: bool = False

    def set_source_coordinate_system(
        self, system: "CoordinateSystem | str", width: int | None = None, height: int | None = None
    ) -> None:
        """Set the source coordinate system for incoming data.

        Args:
            system: CoordinateSystem enum or string key (e.g., "3de_720p")
            width: Optional width override
            height: Optional height override
        """
        if isinstance(system, str):
            if system in COORDINATE_SYSTEMS:
                self._source_metadata = COORDINATE_SYSTEMS[system]
                if width is not None:
                    self._source_metadata = CoordinateMetadata(
                        system=self._source_metadata.system,
                        origin=self._source_metadata.origin,
                        width=width,
                        height=height or self._source_metadata.height,
                        unit_scale=self._source_metadata.unit_scale,
                        pixel_aspect_ratio=self._source_metadata.pixel_aspect_ratio,
                    )
            else:
                # Try to infer from file type
                self._source_metadata = create_source_metadata(system, width, height)
        else:
            self._source_metadata = CoordinateMetadata(
                system=system,
                origin=CoordinateOrigin.BOTTOM_LEFT if "3de" in system.value.lower() else CoordinateOrigin.TOP_LEFT,
                width=width or 1920,
                height=height or 1080,
            )

        self._data_normalized = False
        logger.info(f"Set source coordinate system: {self._source_metadata.system.value}")

    def get_source_metadata(self) -> "CoordinateMetadata | None":
        """Get the current source coordinate system metadata."""
        return self._source_metadata

    def detect_coordinate_system(self, file_path: str) -> "CoordinateMetadata":
        """Detect coordinate system from file path/type.

        Args:
            file_path: Path to the data file

        Returns:
            Detected CoordinateMetadata
        """
        file_lower = file_path.lower()

        # Check for specific file patterns
        if "2dtrack" in file_lower or ".txt" in file_lower:
            # 3DEqualizer tracking data
            return COORDINATE_SYSTEMS["3de_720p"]
        elif ".nk" in file_lower or "nuke" in file_lower:
            return COORDINATE_SYSTEMS["nuke_hd"]
        else:
            # Default to Qt coordinates for CSV/JSON
            return COORDINATE_SYSTEMS["qt"]

    def normalize_curve_data(
        self, data: "CurveDataList", source_metadata: "CoordinateMetadata | None" = None
    ) -> "CurveDataList":
        """Normalize curve data from source coordinates to internal format.

        This is the entry point for all data coming into CurveEditor.

        Args:
            data: Raw curve data in source coordinate system
            source_metadata: Optional metadata override (uses stored if not provided)

        Returns:
            Normalized curve data in internal coordinate system
        """
        from core.curve_data import CurveDataWithMetadata

        metadata = source_metadata or self._source_metadata
        if metadata is None:
            # No transformation needed, assume already normalized
            logger.warning("No source metadata, assuming data is already normalized")
            return data

        # Wrap data with metadata and normalize
        wrapped = CurveDataWithMetadata(data=data, metadata=metadata, is_normalized=False)
        normalized = wrapped.to_normalized()

        logger.info(f"Normalized {len(data)} points from {metadata.system.value} (origin: {metadata.origin.value})")

        return normalized.data

    def denormalize_curve_data(
        self, data: "CurveDataList", target_metadata: "CoordinateMetadata | None" = None
    ) -> "CurveDataList":
        """Convert normalized data back to a target coordinate system.

        This is used when exporting data or converting for specific tools.

        Args:
            data: Normalized curve data
            target_metadata: Target coordinate system (uses source if not provided)

        Returns:
            Curve data in target coordinate system
        """
        from core.curve_data import CurveDataWithMetadata

        metadata = target_metadata or self._source_metadata
        if metadata is None:
            # No transformation needed
            return data

        # Create normalized wrapper
        internal_metadata = COORDINATE_SYSTEMS["internal"]
        if metadata.width != internal_metadata.width:
            internal_metadata = CoordinateMetadata(
                system=CoordinateSystem.CURVE_EDITOR_INTERNAL,
                origin=CoordinateOrigin.TOP_LEFT,
                width=metadata.width,
                height=metadata.height,
            )

        wrapped = CurveDataWithMetadata(data=data, metadata=internal_metadata, is_normalized=True)

        # Convert to target system
        denormalized = wrapped.from_normalized(metadata)

        logger.info(f"Denormalized {len(data)} points to {metadata.system.value} (origin: {metadata.origin.value})")

        return denormalized.data

    def create_transform_from_metadata(
        self, view_state: "ViewState", data_metadata: CoordinateMetadata | None = None
    ) -> "Transform":
        """
        Create a Transform using coordinate metadata for automatic Y-flip detection.

        This is the new unified transformation approach that determines Y-flip
        based on the coordinate system metadata rather than manual flags.

        Args:
            view_state: The current view state
            data_metadata: Optional coordinate metadata describing the data's origin.
                         If provided, Y-flip is determined from the origin type.
                         If None, falls back to view_state.flip_y_axis.

        Returns:
            Transform instance with appropriate Y-flip setting
        """
        # Import here to avoid circular imports
        from services.cache_service import CacheService
        from services.transform_core import ViewState

        # Determine if Y-flip is needed based on metadata
        if data_metadata is not None:
            # Use metadata to determine if Y-flip is needed
            # Data with BOTTOM_LEFT origin needs Y-flip for Qt display (TOP_LEFT)
            needs_flip = data_metadata.origin == CoordinateOrigin.BOTTOM_LEFT

            # Log the decision for debugging
            logger.debug(
                f"[COORD] Transform from metadata: system={data_metadata.system.value}, " +
                f"origin={data_metadata.origin.value}, needs_flip={needs_flip}"
            )
        else:
            # Fall back to manual flag if no metadata
            needs_flip = view_state.flip_y_axis
            logger.debug(f"[COORD] Transform using manual flip_y: {needs_flip}")

        # Create a modified view state with the determined flip value
        # ViewState is frozen, so we need to create a new one
        modified_state = ViewState(
            zoom_factor=view_state.zoom_factor,
            offset_x=view_state.offset_x,
            offset_y=view_state.offset_y,
            flip_y_axis=needs_flip,  # Use determined value
            display_width=view_state.display_width,
            display_height=view_state.display_height,
            image_width=view_state.image_width,
            image_height=view_state.image_height,
            widget_width=view_state.widget_width,
            widget_height=view_state.widget_height,
            manual_x_offset=view_state.manual_x_offset,
            manual_y_offset=view_state.manual_y_offset,
            scale_to_image=view_state.scale_to_image,
        )

        # Use cache service for transform creation
        cache_service = CacheService()
        return cache_service.create_transform_from_view_state(modified_state)

    @property
    def is_data_normalized(self) -> bool:
        """Check if the current data has been normalized."""
        return self._data_normalized

    def mark_data_normalized(self) -> None:
        """Mark the current data as normalized."""
        self._data_normalized = True

    def reset_normalization_state(self) -> None:
        """Reset the normalization state (used when loading new data)."""
        self._data_normalized = False


__all__ = [
    "CoordinateService",
]

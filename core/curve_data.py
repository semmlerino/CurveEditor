"""Metadata-aware curve data structures for unified coordinate transformation.

This module provides data structures that carry coordinate system metadata
alongside curve data, enabling proper transformation through the pipeline
without relying on scattered flip_y flags.
"""

from dataclasses import dataclass

from core.coordinate_system import CoordinateMetadata, CoordinateOrigin, CoordinateSystem
from core.type_aliases import CurveDataInput, CurveDataList, LegacyPointData


@dataclass
class CurveDataWithMetadata:
    """Curve data that carries coordinate system information.

    This wrapper ensures that curve data always carries information about
    its coordinate system, preventing transformation errors and eliminating
    the need for manual flip_y flags scattered throughout the code.

    Attributes:
        data: The curve data as a list of tuples (frame, x, y, [status])
        metadata: Coordinate system metadata describing the data's origin
        is_normalized: Whether data has been normalized to internal format
    """

    data: CurveDataList
    metadata: CoordinateMetadata | None = None
    is_normalized: bool = False

    def __init__(
        self,
        data: CurveDataInput,
        metadata: CoordinateMetadata | None = None,
        is_normalized: bool = False,
    ):
        """Initialize with covariant input type, store as invariant list."""
        self.data = list(data) if not isinstance(data, list) else data
        self.metadata = metadata
        self.is_normalized = is_normalized

        # Validate data structure
        if self.data and len(self.data[0]) < 3:
            raise ValueError(f"Invalid curve data format: {self.data[0]}")

    @property
    def is_metadata_aware(self) -> bool:
        """Check if this data has coordinate metadata attached."""
        return self.metadata is not None

    @property
    def needs_y_flip_for_display(self) -> bool:
        """Check if this data needs Y-flip for Qt display."""
        if not self.metadata:
            return False
        return self.metadata.needs_y_flip_for_qt

    @property
    def coordinate_system(self) -> CoordinateSystem | None:
        """Get the coordinate system of this data."""
        return self.metadata.system if self.metadata else None

    @property
    def frame_count(self) -> int:
        """Get the number of frames in this data."""
        return len(self.data)

    def to_legacy_format(self) -> CurveDataList:
        """Convert to legacy tuple format for backward compatibility.

        Returns:
            List of tuples without metadata, compatible with existing code
        """
        return self.data

    def to_normalized(self) -> "CurveDataWithMetadata":
        """Convert data to normalized internal coordinates.

        The normalized format uses Qt-style top-left origin for consistency
        across the application.

        Returns:
            New instance with normalized coordinates
        """
        if self.is_normalized:
            return self

        if not self.metadata:
            # No metadata, assume already in Qt coordinates
            return CurveDataWithMetadata(
                data=self.data,
                metadata=CoordinateMetadata(
                    system=CoordinateSystem.QT_SCREEN, origin=CoordinateOrigin.TOP_LEFT, width=1920, height=1080
                ),
                is_normalized=True,
            )

        # Transform each point using metadata
        normalized_data: CurveDataList = []
        for point in self.data:
            if len(point) >= 3:
                frame, x, y = point[:3]
                norm_x, norm_y = self.metadata.to_normalized(x, y)

                # Preserve additional data like status
                if len(point) > 3:
                    # Preserve status field (4th element) if present
                    status = point[3]
                    if isinstance(status, str):
                        normalized_data.append((frame, norm_x, norm_y, status))
                    else:
                        # Handle bool status (legacy format)
                        normalized_data.append((frame, norm_x, norm_y, status))
                else:
                    # Point has exactly 3 elements, no status field
                    normalized_data.append((frame, norm_x, norm_y))
            else:
                # Invalid point, keep as-is
                normalized_data.append(point)

        # Create normalized metadata
        normalized_metadata = CoordinateMetadata(
            system=CoordinateSystem.CURVE_EDITOR_INTERNAL,
            origin=CoordinateOrigin.TOP_LEFT,
            width=self.metadata.width,
            height=self.metadata.height,
            unit_scale=self.metadata.unit_scale,
            pixel_aspect_ratio=self.metadata.pixel_aspect_ratio,
        )

        return CurveDataWithMetadata(data=normalized_data, metadata=normalized_metadata, is_normalized=True)

    def from_normalized(self, target_metadata: CoordinateMetadata) -> "CurveDataWithMetadata":
        """Convert normalized data to a target coordinate system.

        Args:
            target_metadata: The target coordinate system metadata

        Returns:
            New instance with data in target coordinate system

        Raises:
            ValueError: If data is not normalized
        """
        if not self.is_normalized:
            raise ValueError("Data must be normalized before converting to target system")

        # Transform each point to target system
        converted_data: CurveDataList = []
        for point in self.data:
            if len(point) >= 3:
                frame, x, y = point[:3]
                target_x, target_y = target_metadata.from_normalized(x, y)

                if len(point) > 3:
                    # Preserve status field (4th element) if present
                    status = point[3]
                    if isinstance(status, str):
                        converted_data.append((frame, target_x, target_y, status))
                    else:
                        # Handle bool status (legacy format)
                        converted_data.append((frame, target_x, target_y, status))
                else:
                    # Point has exactly 3 elements, no status field
                    converted_data.append((frame, target_x, target_y))
            else:
                converted_data.append(point)

        return CurveDataWithMetadata(data=converted_data, metadata=target_metadata, is_normalized=False)

    def with_metadata(self, metadata: CoordinateMetadata) -> "CurveDataWithMetadata":
        """Create a copy with updated metadata.

        Args:
            metadata: New coordinate metadata

        Returns:
            New instance with updated metadata
        """
        return CurveDataWithMetadata(data=self.data.copy(), metadata=metadata, is_normalized=self.is_normalized)

    def get_point_at_frame(self, frame: int) -> LegacyPointData | None:
        """Get the curve point at a specific frame.

        Args:
            frame: The frame number to look up

        Returns:
            The point tuple at that frame, or None if not found
        """
        for point in self.data:
            if len(point) >= 1 and point[0] == frame:
                return point
        return None

    def get_bounds(self) -> tuple[float, float, float, float]:
        """Get the bounding box of the curve data.

        Returns:
            Tuple of (min_x, min_y, max_x, max_y)
        """
        if not self.data:
            return (0.0, 0.0, 0.0, 0.0)

        xs = [p[1] for p in self.data if len(p) >= 3]
        ys = [p[2] for p in self.data if len(p) >= 3]

        if not xs or not ys:
            return (0.0, 0.0, 0.0, 0.0)

        return (min(xs), min(ys), max(xs), max(ys))

    def __len__(self) -> int:
        """Get the number of points in the curve."""
        return len(self.data)

    def __iter__(self):
        """Iterate over curve points."""
        return iter(self.data)

    def __getitem__(self, index: int) -> LegacyPointData:
        """Get a point by index."""
        return self.data[index]


def create_metadata_from_file_type(
    file_path: str, width: int | None = None, height: int | None = None
) -> CoordinateMetadata:
    """Create appropriate coordinate metadata based on file type.

    This is a simplified version that will be expanded in coordinate_detector.py

    Args:
        file_path: Path to the file being loaded
        width: Optional image width
        height: Optional image height

    Returns:
        CoordinateMetadata for the detected file type
    """
    file_lower = file_path.lower()

    # 3DEqualizer files
    if "2dtrack" in file_lower or "3de" in file_lower or "3dequalizer" in file_lower:
        return CoordinateMetadata(
            system=CoordinateSystem.THREE_DE_EQUALIZER,
            origin=CoordinateOrigin.BOTTOM_LEFT,
            width=width or 1280,
            height=height or 720,
        )

    # Nuke files
    if "nuke" in file_lower or ".nk" in file_lower:
        return CoordinateMetadata(
            system=CoordinateSystem.NUKE,
            origin=CoordinateOrigin.BOTTOM_LEFT,
            width=width or 1920,
            height=height or 1080,
        )

    # Maya files
    if "maya" in file_lower or ".ma" in file_lower or ".mb" in file_lower:
        return CoordinateMetadata(
            system=CoordinateSystem.MAYA, origin=CoordinateOrigin.CENTER, width=width or 1920, height=height or 1080
        )

    # Default to Qt screen coordinates
    return CoordinateMetadata(
        system=CoordinateSystem.QT_SCREEN,
        origin=CoordinateOrigin.TOP_LEFT,
        width=width or 1920,
        height=height or 1080,
    )


def wrap_legacy_data(
    data: CurveDataInput, file_path: str | None = None, width: int | None = None, height: int | None = None
) -> CurveDataWithMetadata:
    """Wrap legacy curve data with metadata for compatibility.

    Args:
        data: Legacy curve data as list of tuples
        file_path: Optional file path for auto-detection
        width: Optional width for metadata
        height: Optional height for metadata

    Returns:
        CurveDataWithMetadata instance
    """
    if file_path:
        # Use the advanced coordinate detector that checks content
        from core.coordinate_detector import detect_coordinate_system

        metadata = detect_coordinate_system(file_path)

        # Override dimensions if provided
        if width is not None:
            metadata.width = width
        if height is not None:
            metadata.height = height
    else:
        # Default to Qt coordinates if no file path
        metadata = CoordinateMetadata(
            system=CoordinateSystem.QT_SCREEN,
            origin=CoordinateOrigin.TOP_LEFT,
            width=width or 1920,
            height=height or 1080,
        )

    return CurveDataWithMetadata(data=list(data), metadata=metadata)


# Type alias for functions that can accept either format
CurveDataUnion = CurveDataList | CurveDataWithMetadata


def ensure_metadata_aware(
    data: CurveDataInput | CurveDataWithMetadata, file_path: str | None = None
) -> CurveDataWithMetadata:
    """Ensure data is metadata-aware, wrapping if necessary.

    Args:
        data: Either legacy or metadata-aware curve data
        file_path: Optional file path for metadata detection

    Returns:
        CurveDataWithMetadata instance
    """
    if isinstance(data, CurveDataWithMetadata):
        return data

    # Wrap legacy data
    return wrap_legacy_data(data, file_path)

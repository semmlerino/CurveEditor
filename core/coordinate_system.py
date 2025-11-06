"""Coordinate system definitions and transformation pipeline for CurveEditor.

This module provides a unified architecture for coordinate transformations,
establishing a clear data flow from raw file formats through internal
representation to display coordinates.

Data Flow Pipeline:
1. Raw Data (file format, e.g., 3DEqualizer)
2. → Normalized Data (internal CurveEditor format)
3. → Display Data (Qt screen coordinates)

All transformations go through TransformService as the single source of truth.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

# Removed unused TYPE_CHECKING imports to prevent circular dependency


class CoordinateOrigin(Enum):
    """Defines where the origin (0,0) is located in a coordinate system."""

    TOP_LEFT = "top_left"  # Qt/Screen: Y=0 at top, increases downward
    BOTTOM_LEFT = "bottom_left"  # 3DEqualizer/OpenGL: Y=0 at bottom, increases upward
    CENTER = "center"  # Some math systems: (0,0) at center


class CoordinateSystem(Enum):
    """Common coordinate systems used in VFX and animation.

    Each system has specific conventions that must be preserved during transformation.
    """

    QT_SCREEN = "qt_screen"  # Qt/PySide: top-left origin
    THREE_DE_EQUALIZER = "3dequalizer"  # 3DEqualizer: bottom-left origin
    MAYA = "maya"  # Maya: configurable, usually Y-up
    NUKE = "nuke"  # Nuke: bottom-left origin
    OPENGL = "opengl"  # OpenGL: bottom-left origin
    CURVE_EDITOR_INTERNAL = "curve_editor"  # Internal normalized format


@dataclass
class CoordinateMetadata:
    """Complete metadata about a coordinate system for proper transformation.

    This class encapsulates all information needed to correctly transform
    coordinates between different systems.
    """

    system: CoordinateSystem
    origin: CoordinateOrigin
    width: int
    height: int
    # Optional: Unit scale (e.g., pixels per unit)
    unit_scale: float = 1.0
    # Optional: Aspect ratio correction
    pixel_aspect_ratio: float = 1.0
    # Flag for normalized coordinates (0-1 range that need denormalization)
    uses_normalized_coordinates: bool = False

    @property
    def needs_y_flip_for_qt(self) -> bool:
        """Check if this coordinate system needs Y-flip for Qt display."""
        return self.origin == CoordinateOrigin.BOTTOM_LEFT

    @property
    def needs_y_flip_from_qt(self) -> bool:
        """Check if Qt coordinates need Y-flip to convert to this system."""
        return self.origin == CoordinateOrigin.BOTTOM_LEFT

    def denormalize_coordinates(self, x: float, y: float) -> tuple[float, float]:
        """Convert normalized [0-1] coordinates to pixel coordinates.

        Args:
            x: Normalized X coordinate (0-1)
            y: Normalized Y coordinate (0-1)

        Returns:
            Tuple of (pixel_x, pixel_y)
        """
        if not self.uses_normalized_coordinates:
            return x, y

        pixel_x = x * self.width
        pixel_y = y * self.height
        return pixel_x, pixel_y

    def normalize_coordinates(self, x: float, y: float) -> tuple[float, float]:
        """Convert pixel coordinates to normalized [0-1] coordinates.

        Args:
            x: Pixel X coordinate
            y: Pixel Y coordinate

        Returns:
            Tuple of (normalized_x, normalized_y)
        """
        if not self.uses_normalized_coordinates:
            return x, y

        normalized_x = x / self.width if self.width > 0 else 0.0
        normalized_y = y / self.height if self.height > 0 else 0.0
        return normalized_x, normalized_y

    def to_normalized(self, x: float, y: float) -> tuple[float, float]:
        """Convert from this coordinate system to normalized internal format.

        The normalized format uses Qt-style top-left origin for consistency.
        """
        # Apply aspect ratio correction if needed
        if self.pixel_aspect_ratio != 1.0:
            x *= self.pixel_aspect_ratio

        # Apply unit scaling
        x *= self.unit_scale
        y *= self.unit_scale

        # Flip Y if this system uses bottom-left origin
        if self.origin == CoordinateOrigin.BOTTOM_LEFT:
            y = self.height - y
        elif self.origin == CoordinateOrigin.CENTER:
            # Convert from center origin to top-left
            x += self.width / 2
            y = (self.height / 2) - y  # Flip Y and offset

        return x, y

    def from_normalized(self, x: float, y: float) -> tuple[float, float]:
        """Convert from normalized internal format to this coordinate system."""
        # Reverse the normalization process
        if self.origin == CoordinateOrigin.BOTTOM_LEFT:
            y = self.height - y
        elif self.origin == CoordinateOrigin.CENTER:
            x -= self.width / 2
            y = (self.height / 2) - y

        # Reverse unit scaling
        if self.unit_scale != 0:
            x /= self.unit_scale
            y /= self.unit_scale

        # Reverse aspect ratio correction
        if self.pixel_aspect_ratio != 0:
            x /= self.pixel_aspect_ratio

        return x, y


class TransformableData(Protocol):
    """Protocol for data that can be transformed between coordinate systems."""

    @property
    def coordinate_metadata(self) -> CoordinateMetadata:
        """Get the coordinate system metadata for this data."""
        ...

    def with_metadata(self, metadata: CoordinateMetadata) -> "TransformableData":
        """Create a copy with updated coordinate metadata."""
        ...


# Removed CurveDataWithMetadata import to break circular dependency
# coordinate_system.py should not depend on curve_data.py


# Transformation Pipeline Functions
def create_source_metadata(file_type: str, width: int | None = None, height: int | None = None) -> CoordinateMetadata:
    """Create appropriate coordinate metadata based on file type.

    Args:
        file_type: Type of file (e.g., "2dtrack", "csv", "json")
        width: Image width (optional, uses defaults if not provided)
        height: Image height (optional, uses defaults if not provided)

    Returns:
        CoordinateMetadata for the file type
    """
    if file_type.lower() in ("2dtrack", "3de", "3dequalizer"):
        return CoordinateMetadata(
            system=CoordinateSystem.THREE_DE_EQUALIZER,
            origin=CoordinateOrigin.BOTTOM_LEFT,
            width=width or 1280,
            height=height or 720,
        )
    if file_type.lower() == "nuke":
        return CoordinateMetadata(
            system=CoordinateSystem.NUKE,
            origin=CoordinateOrigin.BOTTOM_LEFT,
            width=width or 1920,
            height=height or 1080,
        )
    # Default to Qt/screen coordinates for unknown types
    return CoordinateMetadata(
        system=CoordinateSystem.QT_SCREEN,
        origin=CoordinateOrigin.TOP_LEFT,
        width=width or 1920,
        height=height or 1080,
    )


# Pre-configured coordinate systems for common use cases
COORDINATE_SYSTEMS = {
    "qt": CoordinateMetadata(
        system=CoordinateSystem.QT_SCREEN, origin=CoordinateOrigin.TOP_LEFT, width=1920, height=1080
    ),
    "3de_720p": CoordinateMetadata(
        system=CoordinateSystem.THREE_DE_EQUALIZER, origin=CoordinateOrigin.BOTTOM_LEFT, width=1280, height=720
    ),
    "3de_1080p": CoordinateMetadata(
        system=CoordinateSystem.THREE_DE_EQUALIZER, origin=CoordinateOrigin.BOTTOM_LEFT, width=1920, height=1080
    ),
    "nuke_hd": CoordinateMetadata(
        system=CoordinateSystem.NUKE, origin=CoordinateOrigin.BOTTOM_LEFT, width=1920, height=1080
    ),
    "internal": CoordinateMetadata(
        system=CoordinateSystem.CURVE_EDITOR_INTERNAL, origin=CoordinateOrigin.TOP_LEFT, width=1920, height=1080
    ),
}

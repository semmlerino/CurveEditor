#!/usr/bin/env python
"""
Performance fix for zoom cache floating bug in CurveEditor.

Based on comprehensive profiling analysis, this fix addresses the root cause
of curve floating during zoom operations.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import logging

from core.error_messages import ValidationError
from services.transform_service import ViewState

logger = logging.getLogger("zoom_cache_fix")


class ImprovedViewState(ViewState):
    """Enhanced ViewState with improved quantization for zoom operations."""

    def quantized_for_cache(self, precision: float = 0.1) -> "ViewState":
        """
        Create a quantized version of ViewState with improved zoom precision.

        FIX: Reduces zoom quantization precision from 0.01 to 0.001 to prevent
        cache collisions that cause floating behavior during smooth zoom operations.

        Args:
            precision: Rounding precision for float parameters (default 0.1 pixels)

        Returns:
            ViewState with improved quantized floating-point values
        """
        # Validate precision parameter
        if precision <= 0:
            raise ValidationError(
                "precision", precision, "must be positive", "Use 0.1 for coarse or 0.01 for fine precision"
            )

        def quantize(value: float, prec: float, min_value: float = 0.0) -> float:
            """Round value to specified precision with NaN/infinity handling."""
            from core.validation_utils import validate_finite

            value = validate_finite(value, "quantize_value", 0.0)
            result = round(value / prec) * prec
            # Ensure result is not below minimum value (e.g., prevent 0 for scale factors)
            if min_value > 0 and 0 < result < min_value:
                result = min_value
            return result

        # CRITICAL FIX: Use much finer zoom precision to prevent cache collisions
        # The original precision/10 = 0.01 was too coarse and caused floating
        zoom_precision = precision / 100  # Use 1/100th = 0.001 instead of 0.01

        # Also quantize base_scale with same precision as zoom for consistency
        base_precision = zoom_precision  # Keep base_scale and zoom_factor aligned

        # Check if quantization actually changes values (optimization)
        # Use minimum value of 1e-10 for zoom to prevent validation errors
        new_zoom = quantize(self.zoom_factor, zoom_precision, min_value=1e-10)
        new_base = quantize(self.base_scale, base_precision, min_value=1e-10)  # NEW: quantize base_scale
        new_offset_x = quantize(self.offset_x, precision)
        new_offset_y = quantize(self.offset_y, precision)
        new_manual_x = quantize(self.manual_x_offset, precision)
        new_manual_y = quantize(self.manual_y_offset, precision)

        # Return self if no changes needed (expanded to include base_scale)
        if (
            self.zoom_factor == new_zoom
            and self.base_scale == new_base  # NEW: include base_scale in comparison
            and self.offset_x == new_offset_x
            and self.offset_y == new_offset_y
            and self.manual_x_offset == new_manual_x
            and self.manual_y_offset == new_manual_y
        ):
            return self

        return ViewState(
            # Integer parameters - no quantization needed
            display_width=self.display_width,
            display_height=self.display_height,
            widget_width=self.widget_width,
            widget_height=self.widget_height,
            image_width=self.image_width,
            image_height=self.image_height,
            # Boolean parameters - no quantization needed
            scale_to_image=self.scale_to_image,
            flip_y_axis=self.flip_y_axis,
            # Quantized floating-point parameters with improved precision
            zoom_factor=new_zoom,
            base_scale=new_base,  # NEW: quantize base_scale
            offset_x=new_offset_x,
            offset_y=new_offset_y,
            manual_x_offset=new_manual_x,
            manual_y_offset=new_manual_y,
            # Background image - excluded from hash anyway
            background_image=self.background_image,
        )


def test_fix_effectiveness():
    """Test the effectiveness of the zoom cache fix."""

    logger.info("Testing quantization precision improvement...")

    # Test cache collision scenario with original precision
    values = [1.001, 1.002, 1.003, 1.004, 1.005]

    # Test original quantization (0.01 precision)
    original_quantized = []
    for val in values:
        state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=val,
            base_scale=0.8,
        )
        quantized = state.quantized_for_cache()  # Original method
        original_quantized.append(quantized.zoom_factor)

    # Test improved quantization (0.001 precision)
    ImprovedViewState(
        display_width=1920, display_height=1080, widget_width=800, widget_height=600, zoom_factor=1.001, base_scale=0.8
    )

    improved_quantized = []
    for val in values:
        state = ImprovedViewState(
            display_width=1920,
            display_height=1080,
            widget_width=800,
            widget_height=600,
            zoom_factor=val,
            base_scale=0.8,
        )
        quantized = state.quantized_for_cache()  # Improved method
        improved_quantized.append(quantized.zoom_factor)

    original_unique = set(original_quantized)
    improved_unique = set(improved_quantized)

    logger.info(f"Test values: {values}")
    logger.info(f"Original quantization (0.01): {original_quantized}")
    logger.info(f"Improved quantization (0.001): {improved_quantized}")
    logger.info(
        f"Original unique values: {len(original_unique)}/{len(values)} ({len(values) - len(original_unique)} collisions)"
    )
    logger.info(
        f"Improved unique values: {len(improved_unique)}/{len(values)} ({len(values) - len(improved_unique)} collisions)"
    )

    if len(improved_unique) > len(original_unique):
        logger.info("✓ Fix successful - reduced cache collisions")
        return True
    else:
        logger.warning("⚠ Fix did not improve cache collisions")
        return False


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_fix_effectiveness()

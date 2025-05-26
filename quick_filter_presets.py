#!/usr/bin/env python
# -*- coding: utf-8 -*-

import copy  # Keep copy for unknown preset case
from typing import List, Tuple

from services.analysis_service import AnalysisService, PointsList
from services.logging_service import LoggingService

logger = LoggingService.get_logger("quick_filter_presets")

def apply_filter_preset(curve_data: PointsList, indices: List[int], preset_name: str) -> PointsList:
    """Apply a predefined filter preset to the selected points.

    Args:
        curve_data: List of (frame, x, y) tuples
        indices: List of indices to filter
        preset_name: Name of the preset to apply

    Returns:
        Modified copy of curve_data
    """
    if not curve_data or not indices:
        return copy.deepcopy(curve_data)  # Return copy if no data or indices

    try:
        # Apply moving average smoothing with different window sizes based on preset name
        copied_data = copy.deepcopy(curve_data)
        processor = AnalysisService(copied_data)

        if preset_name == "Light Smooth":
            processor.smooth_moving_average(indices, window_size=3)
            return processor.get_data()

        elif preset_name == "Medium Smooth":
            processor.smooth_moving_average(indices, window_size=5)
            return processor.get_data()

        elif preset_name == "Heavy Smooth":
            processor.smooth_moving_average(indices, window_size=7)
            return processor.get_data()

        elif preset_name == "Reduce Noise":
            processor.smooth_moving_average(indices, window_size=5)
            return processor.get_data()

        elif preset_name == "Fix Outliers":
            processor.smooth_moving_average(indices, window_size=3)
            return processor.get_data()

        elif preset_name == "Remove Jitter":
            # Apply moving average with slightly larger window
            processor.smooth_moving_average(indices, window_size=5)
            return processor.get_data()

        elif preset_name == "Preserve Corners" or preset_name == "Low-Pass":
            # Just use moving average for all filters
            processor.smooth_moving_average(indices, window_size=5)
            return processor.get_data()

        else:
            # Unknown preset, return original data copy
            logger.warning(f"Unknown filter preset '{preset_name}'")
            return copy.deepcopy(curve_data)

    except Exception as e:
        logger.error(f"Error applying filter preset '{preset_name}': {e}")
        # Return original data copy in case of error
        return copy.deepcopy(curve_data)


def get_filter_presets() -> List[Tuple[str, str]]:
    """Get a list of available filter presets with descriptions.

    Returns:
        List of (preset_name, description) tuples
    """
    presets = [
        ("Light Smooth", "Gentle smoothing to reduce slight jitter"),
        ("Medium Smooth", "Moderate smoothing for general purpose noise reduction"),
        ("Heavy Smooth", "Strong smoothing for very noisy tracks"),
        ("Reduce Noise", "Median filter to eliminate noise spikes"),
        ("Fix Outliers", "Fix individual tracking errors without changing overall shape"),
        ("Remove Jitter", "Two-step filter designed specifically for high-frequency jitter"),
        ("Preserve Corners", "Smooth while preserving sharp transitions in the track"),
        ("Low-Pass", "Remove high-frequency noise while preserving motion")
    ]

    return presets

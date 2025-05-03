#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import curve_operations as ops # Removed old import
from services.analysis_service import AnalysisService
import copy # Keep copy for unknown preset case

def apply_filter_preset(curve_data, indices, preset_name):
    """Apply a predefined filter preset to the selected points.

    Args:
        curve_data: List of (frame, x, y) tuples
        indices: List of indices to filter
        preset_name: Name of the preset to apply

    Returns:
        Modified copy of curve_data
    """
    if not curve_data or not indices:
        return copy.deepcopy(curve_data) # Return copy if no data or indices

    try:
        # Apply the appropriate filter based on preset name
        if preset_name == "Light Smooth":
            return AnalysisService.smooth_curve(
                curve_data, indices, method='gaussian', window_size=5, sigma=1.0)

        elif preset_name == "Medium Smooth":
            return AnalysisService.smooth_curve(
                curve_data, indices, method='gaussian', window_size=7, sigma=1.5)

        elif preset_name == "Heavy Smooth":
            return AnalysisService.smooth_curve(
                curve_data, indices, method='gaussian', window_size=9, sigma=2.0)

        elif preset_name == "Reduce Noise":
            return AnalysisService.filter_curve(
                curve_data, indices, method='median', window_size=5)

        elif preset_name == "Fix Outliers":
            return AnalysisService.filter_curve(
                curve_data, indices, method='median', window_size=3)

        elif preset_name == "Remove Jitter":
            # Two-step process: median filter followed by gaussian smooth
            filtered_data = AnalysisService.filter_curve(
                curve_data, indices, method='median', window_size=3)
            return AnalysisService.smooth_curve(
                filtered_data, indices, method='gaussian', window_size=5, sigma=1.0)

        elif preset_name == "Preserve Corners":
            return AnalysisService.smooth_curve(
                curve_data, indices, method='savitzky_golay', window_size=7)

        elif preset_name == "Low-Pass":
            return AnalysisService.filter_curve(
                curve_data, indices, method='butterworth', cutoff=0.2, order=2)

        else:
            # Unknown preset, return original data copy
            print(f"Warning: Unknown filter preset '{preset_name}'")
            return copy.deepcopy(curve_data)

    except Exception as e:
        print(f"Error applying filter preset '{preset_name}': {e}")
        # Return original data copy in case of error
        return copy.deepcopy(curve_data)


def get_filter_presets():
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

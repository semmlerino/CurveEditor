#!/usr/bin/env python
# -*- coding: utf-8 -*-

import curve_operations as ops

def apply_filter_preset(curve_data, indices, preset_name):
    """Apply a predefined filter preset to the selected points.
    
    Args:
        curve_data: List of (frame, x, y) tuples
        indices: List of indices to filter
        preset_name: Name of the preset to apply
        
    Returns:
        Modified copy of curve_data
    """
    # Apply the appropriate filter based on preset name using the unified dispatcher
    if preset_name == "Light Smooth":
        result = ops.apply_smoothing_filtering(curve_data, indices, method="gaussian", window_size=5, sigma=1.0)
        
    elif preset_name == "Medium Smooth":
        result = ops.apply_smoothing_filtering(curve_data, indices, method="gaussian", window_size=7, sigma=1.5)
        
    elif preset_name == "Heavy Smooth":
        result = ops.apply_smoothing_filtering(curve_data, indices, method="gaussian", window_size=9, sigma=2.0)
        
    elif preset_name == "Reduce Noise":
        result = ops.apply_smoothing_filtering(curve_data, indices, method="median", window_size=5)
        
    elif preset_name == "Fix Outliers":
        result = ops.apply_smoothing_filtering(curve_data, indices, method="median", window_size=3)
        
    elif preset_name == "Remove Jitter":
        # Two-step process: median filter followed by gaussian smooth
        temp_result = ops.apply_smoothing_filtering(curve_data, indices, method="median", window_size=3)
        result = ops.apply_smoothing_filtering(temp_result, indices, method="gaussian", window_size=5, sigma=1.0)
        
    elif preset_name == "Preserve Corners":
        result = ops.apply_smoothing_filtering(curve_data, indices, method="savitzky_golay", window_size=7)
        
    elif preset_name == "Low-Pass":
        result = ops.apply_smoothing_filtering(curve_data, indices, method="butterworth", cutoff=0.2, order=2)
        
    else:
        # Unknown preset, return original data (or raise error?)
        import copy
        result = copy.deepcopy(curve_data) # Ensure a copy is returned even if no operation applied
        
    return result


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
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
    # Apply the appropriate filter based on preset name
    if preset_name == "Light Smooth":
        # Gentle Gaussian smoothing good for slight jitter
        window_size = 5
        sigma = 1.0
        result = ops.smooth_gaussian(curve_data, indices, window_size, sigma)
        
    elif preset_name == "Medium Smooth":
        # Moderate Gaussian smoothing
        window_size = 7
        sigma = 1.5
        result = ops.smooth_gaussian(curve_data, indices, window_size, sigma)
        
    elif preset_name == "Heavy Smooth":
        # Stronger Gaussian smoothing for problematic tracks
        window_size = 9
        sigma = 2.0
        result = ops.smooth_gaussian(curve_data, indices, window_size, sigma)
        
    elif preset_name == "Reduce Noise":
        # Median filter to remove outliers
        window_size = 5
        result = ops.filter_median(curve_data, indices, window_size)
        
    elif preset_name == "Fix Outliers":
        # Apply median filter with a small window to fix individual outliers
        window_size = 3
        result = ops.filter_median(curve_data, indices, window_size)
        
    elif preset_name == "Remove Jitter":
        # Two-step process: median filter followed by gaussian smooth
        window_size = 3
        result = ops.filter_median(curve_data, indices, window_size)
        result = ops.smooth_gaussian(result, indices, 5, 1.0)
        
    elif preset_name == "Preserve Corners":
        # Savitzky-Golay filter that preserves shape better than Gaussian
        window_size = 7
        result = ops.smooth_savitzky_golay(curve_data, indices, window_size)
        
    elif preset_name == "Low-Pass":
        # Butterworth low-pass filter
        cutoff = 0.2
        order = 2
        result = ops.filter_butterworth(curve_data, indices, cutoff, order)
        
    else:
        # Unknown preset, return original data
        result = curve_data
        
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
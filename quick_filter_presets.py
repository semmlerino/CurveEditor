#!/usr/bin/env python
# -*- coding: utf-8 -*-

# import curve_operations as ops # Removed old import
from curve_data_operations import CurveDataOperations # Import new class
import copy # Keep copy for unknown preset case

def apply_filter_preset(curve_data, indices, preset_name):
    """Apply a predefined filter preset to the selected points using CurveDataOperations.
    
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
        # Instantiate the operations class with the data
        data_ops = CurveDataOperations(curve_data)

        # Apply the appropriate filter based on preset name
        if preset_name == "Light Smooth":
            data_ops.smooth_gaussian(indices, window_size=5, sigma=1.0)
            
        elif preset_name == "Medium Smooth":
            data_ops.smooth_gaussian(indices, window_size=7, sigma=1.5)
            
        elif preset_name == "Heavy Smooth":
            data_ops.smooth_gaussian(indices, window_size=9, sigma=2.0)
            
        elif preset_name == "Reduce Noise":
            data_ops.filter_median(indices, window_size=5)
            
        elif preset_name == "Fix Outliers":
            data_ops.filter_median(indices, window_size=3)
            
        elif preset_name == "Remove Jitter":
            # Two-step process: median filter followed by gaussian smooth
            data_ops.filter_median(indices, window_size=3)
            # Apply next step on the already modified internal data
            data_ops.smooth_gaussian(indices, window_size=5, sigma=1.0)
            
        elif preset_name == "Preserve Corners":
            data_ops.smooth_savitzky_golay(indices, window_size=7)
            
        elif preset_name == "Low-Pass":
            data_ops.filter_butterworth(indices, cutoff=0.2, order=2)
            
        else:
            # Unknown preset, return original data copy
            print(f"Warning: Unknown filter preset '{preset_name}'")
            return copy.deepcopy(curve_data)
            
        # Return the modified data from the instance
        return data_ops.get_data()

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
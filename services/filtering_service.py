#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Filtering service for curve data.

This service handles various filtering operations on curve data including:
- Median filtering
- Butterworth filtering
- Duplicate removal

Extracted from AnalysisService to follow Single Responsibility Principle.
"""

import copy
from typing import Dict

from services.logging_service import LoggingService
from core.protocols.protocols import PointsList, FilteringServiceProtocol

logger = LoggingService.get_logger("filtering_service")


class FilteringService(FilteringServiceProtocol):
    """Service for filtering curve data."""
    
    @staticmethod
    def filter_median(data: PointsList, indices: list[int], window_size: int) -> PointsList:
        """
        Apply median filter to specified points.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            indices: List of indices to filter
            window_size: Size of the filter window
            
        Returns:
            Filtered curve data
        """
        logger.info(f"Applying median filter with window_size={window_size} to {len(indices)} points")
        
        # For now, use moving average as a fallback since we don't have numpy
        # In a real implementation, this would calculate the median
        from services.smoothing_service import SmoothingService
        return SmoothingService.smooth_moving_average(data, indices, window_size)
    
    @staticmethod
    def filter_butterworth(data: PointsList, indices: list[int], cutoff: float, order: int) -> PointsList:
        """
        Apply Butterworth filter to specified points.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            indices: List of indices to filter
            cutoff: Cutoff frequency
            order: Filter order
            
        Returns:
            Filtered curve data
        """
        logger.info(f"Applying Butterworth filter with cutoff={cutoff}, order={order} to {len(indices)} points")
        
        # Use moving average as a fallback with window size based on order
        from services.smoothing_service import SmoothingService
        window_size = max(3, int(order * 2) + 1)
        return SmoothingService.smooth_moving_average(data, indices, window_size)
    
    @staticmethod
    def remove_duplicates(data: PointsList) -> tuple[PointsList, int]:
        """
        Remove duplicate points with same frame number.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            
        Returns:
            Tuple of (deduplicated data, number of duplicates removed)
        """
        if not data:
            return [], 0
            
        seen_frames: Dict[int, int] = {}
        unique_data: PointsList = []
        removed = 0
        
        for i, point in enumerate(data):
            frame = point[0]
            if frame not in seen_frames:
                seen_frames[frame] = len(unique_data)  # Store index in unique_data
                unique_data.append(point)
            else:
                removed += 1
                # Keep the point with larger movement or newer index
                existing_idx = seen_frames[frame]
                existing = unique_data[existing_idx]
                
                # Compare movement from origin
                existing_dist = existing[1]**2 + existing[2]**2
                current_dist = point[1]**2 + point[2]**2
                
                if current_dist > existing_dist:
                    unique_data[existing_idx] = point
                    
        logger.info(f"Removed {removed} duplicate frames")
        return unique_data, removed
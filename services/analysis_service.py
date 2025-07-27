#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Analysis service facade for curve data operations.

This service acts as a unified interface to all specialized analysis services,
maintaining backward compatibility while following Single Responsibility Principle.

The actual operations are delegated to:
- GeometryService: Rotation, offset, velocity normalization
- ProblemDetectionService: Problem detection, outliers, curvature
- SmoothingService: Moving average, Gaussian, spline smoothing
- FilteringService: Median, Butterworth filtering, duplicate removal
- GapFillingService: Linear, spline, velocity-based gap filling
- ExtrapolationService: Forward/backward extrapolation, frame interpolation
"""

import copy
from typing import List, Tuple, Optional, Dict, Sequence

from services.logging_service import LoggingService
from services.geometry_service import GeometryService
from services.problem_detection_service import ProblemDetectionService
from services.smoothing_service import SmoothingService
from services.filtering_service import FilteringService
from services.gap_filling_service import GapFillingService
from services.extrapolation_service import ExtrapolationService
from core.protocols.protocols import PointsList

logger = LoggingService.get_logger("analysis_service")


class AnalysisService:
    """
    Facade for curve data analysis and transformations.
    
    This class maintains the same API as the original monolithic AnalysisService
    but delegates all operations to specialized services.
    """
    
    def __init__(self, data: PointsList) -> None:
        """
        Initialize with curve data.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
        """
        self.data: PointsList = data
        
    def create_processor(self, data: PointsList) -> 'ConcreteCurveProcessor':
        """
        Create a processor instance for the given data.
        
        Args:
            data: Curve data to process
            
        Returns:
            An instance of ConcreteCurveProcessor
        """
        return ConcreteCurveProcessor(data)
    
    def get_data(self) -> PointsList:
        """
        Get the current curve data.
        
        Returns:
            Current curve data
        """
        return self.data
    
    # Delegation to GeometryService
    @classmethod
    def rotate_curve(cls, curve_data: List[Tuple[int, float, float]], angle_degrees: float = 0.0,
                     center_x: Optional[float] = None, center_y: Optional[float] = None) -> List[Tuple[int, float, float]]:
        """Rotate curve data around a center point."""
        return GeometryService.rotate_curve(curve_data, angle_degrees, center_x, center_y)
    
    def offset_points(self, indices: List[int], dx: float, dy: float) -> None:
        """Offset specified points by given delta values."""
        self.data = GeometryService.offset_points(self.data, indices, dx, dy)
    
    def normalize_velocity(self, target_velocity: float) -> None:
        """Normalize velocity between points to target value."""
        self.data = GeometryService.normalize_velocity(self.data, target_velocity)
    
    # Delegation to ProblemDetectionService
    def detect_problems(self) -> Dict[int, Dict[str, str]]:
        """Detect common problems in tracking data."""
        return ProblemDetectionService.detect_problems(self.data)
    
    @classmethod
    def find_velocity_outliers(cls, curve_data: List[Tuple[int, float, float]], threshold_factor: float = 2.0) -> List[int]:
        """Find points with velocity significantly different from neighbors."""
        return ProblemDetectionService.find_velocity_outliers(curve_data, threshold_factor)
    
    def calculate_curvature(self) -> List[float]:
        """Calculate curvature at each point."""
        return ProblemDetectionService.calculate_curvature(self.data)
    
    # Delegation to SmoothingService
    def smooth_moving_average(self, indices: Sequence[int], window_size: int, real_view: Optional[object] = None) -> None:
        """Apply moving average smoothing to specified points."""
        self.data = SmoothingService.smooth_moving_average(self.data, list(indices), window_size)
    
    def smooth_gaussian(self, indices: List[int], window_size: int, sigma: float) -> None:
        """Apply Gaussian smoothing to specified points."""
        self.data = SmoothingService.smooth_gaussian(self.data, indices, window_size, sigma)
    
    def apply_spline(self, control_indices: List[int]) -> None:
        """Apply spline interpolation using control points."""
        self.data = SmoothingService.apply_spline(self.data, control_indices)
    
    # Delegation to FilteringService
    def filter_median(self, indices: List[int], window_size: int) -> None:
        """Apply median filter to specified points."""
        self.data = FilteringService.filter_median(self.data, indices, window_size)
    
    def filter_butterworth(self, indices: List[int], cutoff: float, order: int) -> None:
        """Apply Butterworth filter to specified points."""
        self.data = FilteringService.filter_butterworth(self.data, indices, cutoff, order)
    
    def remove_duplicates(self) -> int:
        """Remove duplicate points with same frame number."""
        self.data, removed = FilteringService.remove_duplicates(self.data)
        return removed
    
    # Delegation to GapFillingService
    def fill_gap_linear(self, start_frame: int, end_frame: int) -> None:
        """Fill a gap between start_frame and end_frame using linear interpolation."""
        self.data = GapFillingService.fill_gap_linear(self.data, start_frame, end_frame)
    
    def fill_gap_spline(self, start_frame: int, end_frame: int) -> None:
        """Fill a gap between start_frame and end_frame using spline interpolation."""
        self.data = GapFillingService.fill_gap_spline(self.data, start_frame, end_frame)
    
    def fill_linear(self, start_frame: int, end_frame: int, preserve_endpoints: bool = True) -> None:
        """Fill a gap using linear interpolation."""
        self.fill_gap_linear(start_frame, end_frame)
    
    def fill_cubic_spline(self, start_frame: int, end_frame: int, preserve_endpoints: bool = True) -> None:
        """Fill a gap using cubic spline interpolation."""
        self.fill_gap_spline(start_frame, end_frame)
    
    def fill_constant_velocity(self, start_frame: int, end_frame: int, preserve_endpoints: bool = True) -> None:
        """Fill a gap assuming constant velocity."""
        self.data = GapFillingService.fill_constant_velocity(self.data, start_frame, end_frame)
    
    def fill_accelerated_motion(self, start_frame: int, end_frame: int, preserve_endpoints: bool = True) -> None:
        """Fill a gap assuming accelerated motion."""
        self.data = GapFillingService.fill_accelerated_motion(self.data, start_frame, end_frame)
    
    def fill_average(self, start_frame: int, end_frame: int, window_size: int, preserve_endpoints: bool = True) -> None:
        """Fill a gap using average of surrounding points."""
        self.data = GapFillingService.fill_average(self.data, start_frame, end_frame, window_size)
    
    # Delegation to ExtrapolationService
    def extrapolate_forward(self, num_frames: int, method: int, fit_points: int) -> None:
        """Extrapolate curve forward."""
        self.data = ExtrapolationService.extrapolate_forward(self.data, num_frames, method, fit_points)
    
    def extrapolate_backward(self, num_frames: int, method: int, fit_points: int) -> None:
        """Extrapolate curve backward."""
        self.data = ExtrapolationService.extrapolate_backward(self.data, num_frames, method, fit_points)
    
    @classmethod
    def interpolate_missing_frames(cls, curve_data: List[Tuple[int, float, float]]) -> List[Tuple[int, float, float]]:
        """Interpolate points for missing frame numbers."""
        return ExtrapolationService.interpolate_missing_frames(curve_data)


# Legacy support - ConcreteCurveProcessor for backward compatibility
class ConcreteCurveProcessor:
    """Concrete implementation of CurveProcessor for backward compatibility."""
    
    def __init__(self, data: PointsList) -> None:
        """Initialize with curve data."""
        self.data: PointsList = copy.deepcopy(data)
        
    def get_data(self) -> PointsList:
        """Get the processed curve data."""
        return self.data
        
    def smooth_moving_average(self, indices: Sequence[int], window_size: int, real_view: Optional[object] = None) -> None:
        """Apply moving average smoothing to x and y coordinates."""
        self.data = SmoothingService.smooth_moving_average(self.data, list(indices), window_size)
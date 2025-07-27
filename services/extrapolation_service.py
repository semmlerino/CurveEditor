#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Extrapolation service for curve data.

This service handles curve extension operations including:
- Forward extrapolation
- Backward extrapolation
- Missing frame interpolation

Extracted from AnalysisService to follow Single Responsibility Principle.
"""

import copy

from services.logging_service import LoggingService
from core.protocols.protocols import PointsList, ExtrapolationServiceProtocol

logger = LoggingService.get_logger("extrapolation_service")


class ExtrapolationService(ExtrapolationServiceProtocol):
    """Service for extrapolating curve data beyond existing points."""
    
    @staticmethod
    def extrapolate_forward(data: PointsList, num_frames: int, method: int, fit_points: int) -> PointsList:
        """
        Extrapolate curve forward.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            num_frames: Number of frames to extrapolate
            method: Extrapolation method (0=linear, 1=quadratic, etc.)
            fit_points: Number of points to use for fitting
            
        Returns:
            Curve data with extrapolated points added
        """
        logger.info(f"Extrapolating {num_frames} frames forward using method={method} with {fit_points} fit points")
        
        if not data or len(data) < 2:
            return data
            
        # Get last points to establish direction
        last_points = sorted(data, key=lambda p: p[0])[-fit_points:]
        if len(last_points) < 2:
            return data
            
        result = copy.deepcopy(data)
        
        if method == 0:  # Linear extrapolation
            # Use last two points to establish direction
            p1 = last_points[-2]
            p2 = last_points[-1]
            
            dx = p2[1] - p1[1]
            dy = p2[2] - p1[2]
            dframe = p2[0] - p1[0]
            
            if dframe == 0:  # Avoid division by zero
                return result
                
            # Calculate velocity per frame
            vx = dx / dframe
            vy = dy / dframe
            
            # Create new points
            last_frame = p2[0]
            for i in range(1, num_frames + 1):
                frame = last_frame + i
                x = p2[1] + vx * i
                y = p2[2] + vy * i
                result.append((frame, x, y))
                
        # Additional methods could be implemented here (quadratic, cubic, etc.)
        
        return result
    
    @staticmethod
    def extrapolate_backward(data: PointsList, num_frames: int, method: int, fit_points: int) -> PointsList:
        """
        Extrapolate curve backward.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            num_frames: Number of frames to extrapolate
            method: Extrapolation method (0=linear, 1=quadratic, etc.)
            fit_points: Number of points to use for fitting
            
        Returns:
            Curve data with extrapolated points added
        """
        logger.info(f"Extrapolating {num_frames} frames backward using method={method} with {fit_points} fit points")
        
        if not data or len(data) < 2:
            return data
            
        # Get first points to establish direction
        first_points = sorted(data, key=lambda p: p[0])[:fit_points]
        if len(first_points) < 2:
            return data
            
        result = copy.deepcopy(data)
        
        if method == 0:  # Linear extrapolation
            # Use first two points to establish direction
            p1 = first_points[0]
            p2 = first_points[1]
            
            dx = p2[1] - p1[1]
            dy = p2[2] - p1[2]
            dframe = p2[0] - p1[0]
            
            if dframe == 0:  # Avoid division by zero
                return result
                
            # Calculate velocity per frame
            vx = dx / dframe
            vy = dy / dframe
            
            # Create new points
            first_frame = p1[0]
            for i in range(1, num_frames + 1):
                frame = first_frame - i
                x = p1[1] - vx * i
                y = p1[2] - vy * i
                result.append((frame, x, y))
                
        # Sort result by frame
        result.sort(key=lambda p: p[0])
        
        return result
    
    @staticmethod
    def interpolate_missing_frames(data: PointsList) -> PointsList:
        """
        Interpolate points for missing frame numbers.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            
        Returns:
            Curve data with interpolated points for missing frames
        """
        if len(data) < 2:
            return copy.deepcopy(data)
            
        # Sort by frame number
        sorted_data = sorted(data, key=lambda p: p[0])
        result: PointsList = []
        
        for i in range(len(sorted_data) - 1):
            p1 = sorted_data[i]
            p2 = sorted_data[i + 1]
            result.append(p1)
            
            # Check for gap
            frame_gap = p2[0] - p1[0]
            if frame_gap > 1:
                # Interpolate missing frames
                for j in range(1, frame_gap):
                    t = j / frame_gap
                    frame = p1[0] + j
                    x = p1[1] * (1 - t) + p2[1] * t
                    y = p1[2] * (1 - t) + p2[2] * t
                    result.append((frame, x, y))
                    
        # Add last point
        result.append(sorted_data[-1])
        
        logger.info(f"Interpolated {len(result) - len(data)} missing frames")
        
        return result
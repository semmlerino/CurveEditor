#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Problem detection service for curve data analysis.

This service handles detection and analysis of issues in curve data including:
- Gap detection between frames
- Jitter detection (small movements)
- Jump detection (sudden large movements)
- Velocity outlier detection
- Curvature calculation

Extracted from AnalysisService to follow Single Responsibility Principle.
"""

import math
from typing import Dict

from services.logging_service import LoggingService
from core.protocols.protocols import PointsList, ProblemDetectionServiceProtocol

logger = LoggingService.get_logger("problem_detection_service")


class ProblemDetectionService(ProblemDetectionServiceProtocol):
    """Service for detecting problems and analyzing curve characteristics."""
    
    @staticmethod
    def detect_problems(data: PointsList) -> Dict[int, Dict[str, str]]:
        """
        Detect common problems in tracking data.
        
        Detects issues such as:
        - Jitter (very small movements)
        - Sudden jumps (unusually large movements)
        - Gaps in frame sequence
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            
        Returns:
            Dictionary mapping frame numbers to problem descriptions
        """
        if len(data) < 2:
            return {}
            
        logger.info(f"Detecting problems in {len(data)} points")
        
        # Sort data by frame number
        sorted_data = sorted(data, key=lambda p: p[0])
        
        # Calculate movement statistics for all points
        movements: list[float] = []
        for i in range(len(sorted_data) - 1):
            p1 = sorted_data[i]
            p2 = sorted_data[i + 1]
            
            # Calculate distance for all adjacent points
            dx = p2[1] - p1[1]
            dy = p2[2] - p1[2]
            distance = math.sqrt(dx**2 + dy**2)
            movements.append(distance)
            
        # If no movements, can't calculate statistics
        if not movements:
            return {}
            
        # Calculate mean movement
        mean_movement = sum(movements) / len(movements)
        
        # More aggressive thresholds to catch more problems
        jitter_threshold = 0.5  # Fixed small threshold for jitter
        jump_threshold = mean_movement * 2  # Any movement twice the mean is a jump
        
        # Detect problems
        problems: Dict[int, Dict[str, str]] = {}
        
        # Check for gaps first
        for i in range(len(sorted_data) - 1):
            p1 = sorted_data[i]
            p2 = sorted_data[i + 1]
            frame1 = p1[0]
            frame2 = p2[0]
            
            # Check for gaps between frames
            if frame2 - frame1 > 1:
                problems[frame1] = {
                    'type': 'gap',
                    'description': f'Gap detected after frame {frame1}: {frame2 - frame1 - 1} missing frames'
                }
                
        # Now check for movement issues
        for i in range(len(sorted_data) - 1):
            p1 = sorted_data[i]
            p2 = sorted_data[i + 1]
            frame1 = p1[0]
            frame2 = p2[0]
            
            # Calculate movement distance
            dx = p2[1] - p1[1]
            dy = p2[2] - p1[2]
            distance = math.sqrt(dx**2 + dy**2)
            
            # Special case: detect jumps between non-consecutive frames (after a gap)
            if frame2 - frame1 > 1:
                # Check for big position changes after gaps
                if abs(dx) > jump_threshold or abs(dy) > jump_threshold:
                    problems[frame2] = {
                        'type': 'jump_after_gap',
                        'description': f'Position jump after gap at frame {frame2}'
                    }
            else:  # For consecutive frames
                # Check for jitter (very small movement)
                if distance < jitter_threshold:
                    problems[frame2] = {
                        'type': 'jitter',
                        'description': f'Jitter detected at frame {frame2}: movement {distance:.2f} below threshold {jitter_threshold:.2f}'
                    }
                # Check for sudden jumps (unusually large movement)
                elif distance > jump_threshold:
                    problems[frame2] = {
                        'type': 'jump',
                        'description': f'Sudden jump detected at frame {frame2}: movement {distance:.2f} above threshold {jump_threshold:.2f}'
                    }
                    
        # Handle the special case of the last point if it's a jump
        if len(sorted_data) >= 2:
            # Check if last point is significantly different from previous
            last = sorted_data[-1]
            prev = sorted_data[-2]
            dx = last[1] - prev[1]
            dy = last[2] - prev[2]
            distance = math.sqrt(dx**2 + dy**2)
            
            if distance > jump_threshold:
                problems[last[0]] = {
                    'type': 'jump',
                    'description': f'Sudden jump detected at frame {last[0]}: movement {distance:.2f} above threshold {jump_threshold:.2f}'
                }
                
        logger.info(f"Detected {len(problems)} problems")
        return problems
    
    @staticmethod
    def find_velocity_outliers(data: PointsList, threshold_factor: float = 2.0) -> list[int]:
        """
        Find points with velocity significantly different from neighbors.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            threshold_factor: Factor for determining outliers (default: 2.0 * mean velocity)
            
        Returns:
            List of indices of outlier points
        """
        if len(data) < 3:
            return []
            
        # Calculate velocities between consecutive points
        velocities: list[float] = []
        for i in range(1, len(data)):
            p1 = data[i-1]
            p2 = data[i]
            frame_diff = p2[0] - p1[0]
            if frame_diff > 0:
                dx = p2[1] - p1[1]
                dy = p2[2] - p1[2]
                velocity = math.sqrt(dx*dx + dy*dy) / frame_diff
                velocities.append(velocity)
                
        if not velocities:
            return []
            
        # Calculate mean velocity
        mean_velocity = sum(velocities) / len(velocities)
        threshold = mean_velocity * threshold_factor
        
        # Find outliers
        outliers: list[int] = []
        
        # Check first point (velocity from point 0 to 1)
        if velocities[0] >= threshold:
            outliers.append(1)  # Point 1 is the destination of the high velocity
            
        # Check middle points (velocity from point i to i+1)
        for i in range(1, len(velocities)):
            if velocities[i] >= threshold:
                outliers.append(i + 1)  # Point i+1 is the destination of the high velocity
                
        logger.info(f"Found {len(outliers)} velocity outliers with threshold {threshold:.2f}")
        return outliers
    
    @staticmethod
    def calculate_curvature(data: PointsList) -> list[float]:
        """
        Calculate curvature at each point.
        
        Args:
            data: List of points in format [(frame, x, y), ...]
            
        Returns:
            List of curvature values for each point
        """
        if len(data) < 3:
            return [0.0] * len(data)
            
        curvatures: list[float] = []
        
        # First point
        curvatures.append(0.0)
        
        # Middle points
        for i in range(1, len(data) - 1):
            p1 = data[i-1]
            p2 = data[i]
            p3 = data[i+1]
            
            # Calculate vectors
            v1_x = p2[1] - p1[1]
            v1_y = p2[2] - p1[2]
            v2_x = p3[1] - p2[1]
            v2_y = p3[2] - p2[2]
            
            # Calculate angle between vectors
            dot = v1_x * v2_x + v1_y * v2_y
            det = v1_x * v2_y - v1_y * v2_x
            angle = math.atan2(det, dot)
            
            # Curvature is change in angle over distance
            dist1 = math.sqrt(v1_x*v1_x + v1_y*v1_y)
            dist2 = math.sqrt(v2_x*v2_x + v2_y*v2_y)
            avg_dist = (dist1 + dist2) / 2
            
            if avg_dist > 0:
                curvature = abs(angle) / avg_dist
            else:
                curvature = 0.0
                
            curvatures.append(curvature)
            
        # Last point
        curvatures.append(0.0)
        
        return curvatures
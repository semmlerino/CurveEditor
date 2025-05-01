# services/analysis_service.py

# Import error handling decorator with fallback
try:
    from error_handling import safe_operation
except ImportError:
    # Define a simple decorator as fallback if error_handling module is not available
    def safe_operation(operation_name, record_history=True):
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"Error in {operation_name}: {e}")
                    return None
            return wrapper
        return decorator

from typing import List, Tuple, Any, Dict, Optional
import math

# Type alias for curve data
CurveDataType = List[Tuple[int, float, float]]

class AnalysisService:
    """Service for analyzing tracking data and detecting potential problems."""

    @staticmethod
    @safe_operation("Detect Problems")
    def detect_problems(curve_data: CurveDataType) -> List[Tuple[int, str, float, str]]:
        """
        Detect potential problems in the tracking data.
        
        Args:
            curve_data: List of (frame, x, y) tuples representing the tracking data
            
        Returns:
            List of (frame, problem_type, severity, description) tuples
        """
        if not curve_data or len(curve_data) < 10:
            return []
            
        # Sort by frame
        sorted_data = sorted(curve_data, key=lambda x: x[0])
        
        # Initialize problems list
        problems: List[Tuple[int, str, float, str]] = []
        
        # Check various problem types
        
        # 1. Check for gaps
        gaps = AnalysisService._detect_gaps(sorted_data)
        for start_frame, end_frame in gaps:
            frame = start_frame
            severity = min(1.0, (end_frame - start_frame) / 10)  # Normalize severity
            problems.append((
                frame,
                "gap",
                severity,
                f"Gap detected from frame {start_frame} to {end_frame} ({end_frame - start_frame + 1} frames)"
            ))
        
        # 2. Check for sudden moves (velocity spikes)
        velocity_issues = AnalysisService._detect_velocity_spikes(sorted_data)
        problems.extend(velocity_issues)
        
        # 3. Check for jitter (oscillation)
        jitter_issues = AnalysisService._detect_jitter(sorted_data)
        problems.extend(jitter_issues)
        
        # 4. Check for static segments (no movement)
        static_issues = AnalysisService._detect_static_segments(sorted_data)
        problems.extend(static_issues)
        
        # Sort problems by severity (highest first)
        problems.sort(key=lambda x: x[2], reverse=True)
        
        return problems

    @staticmethod
    def _detect_gaps(sorted_data: CurveDataType) -> List[Tuple[int, int]]:
        """
        Detect gaps in the tracking data.
        
        Args:
            sorted_data: Frame-sorted list of (frame, x, y) tuples
            
        Returns:
            List of (start_frame, end_frame) tuples representing gaps
        """
        gaps: List[Tuple[int, int]] = []
        
        for i in range(1, len(sorted_data)):
            prev_frame = sorted_data[i-1][0]
            curr_frame = sorted_data[i][0]
            
            if curr_frame - prev_frame > 1:
                # Found a gap
                gaps.append((prev_frame + 1, curr_frame - 1))
                
        return gaps

    @staticmethod
    def _detect_velocity_spikes(sorted_data: CurveDataType) -> List[Tuple[int, str, float, str]]:
        """
        Detect sudden changes in velocity (spikes).
        
        Args:
            sorted_data: Frame-sorted list of (frame, x, y) tuples
            
        Returns:
            List of (frame, problem_type, severity, description) tuples
        """
        problems: List[Tuple[int, str, float, str]] = []
        
        if len(sorted_data) < 3:
            return problems
            
        # Calculate velocities for each frame
        velocities: List[Tuple[int, float]] = []
        
        for i in range(1, len(sorted_data)):
            prev_frame, prev_x, prev_y = sorted_data[i-1]
            curr_frame, curr_x, curr_y = sorted_data[i]
            
            frame_diff = curr_frame - prev_frame
            if frame_diff <= 0:
                continue
                
            dx = curr_x - prev_x
            dy = curr_y - prev_y
            distance = math.sqrt(dx*dx + dy*dy)
            velocity = distance / frame_diff
            
            velocities.append((curr_frame, velocity))
        
        if not velocities:
            return problems
            
        # Calculate mean and standard deviation of velocities
        mean_velocity = sum(v[1] for v in velocities) / len(velocities)
        variance = sum((v[1] - mean_velocity)**2 for v in velocities) / len(velocities)
        std_dev = math.sqrt(variance) if variance > 0 else 0
        
        # Define threshold for velocity spikes (e.g., 3 standard deviations)
        threshold = mean_velocity + 3 * std_dev
        
        # Find velocity spikes
        for frame, velocity in velocities:
            if velocity > threshold:
                # Calculate severity based on how much the velocity exceeds the threshold
                severity = min(1.0, (velocity - mean_velocity) / (5 * std_dev)) if std_dev > 0 else 0.5
                
                problems.append((
                    frame,
                    "velocity_spike",
                    severity,
                    f"Velocity spike detected at frame {frame} ({velocity:.2f} vs mean {mean_velocity:.2f})"
                ))
        
        return problems

    @staticmethod
    def _detect_jitter(sorted_data: CurveDataType) -> List[Tuple[int, str, float, str]]:
        """
        Detect oscillating movement (jitter) in the tracking data.
        
        Args:
            sorted_data: Frame-sorted list of (frame, x, y) tuples
            
        Returns:
            List of (frame, problem_type, severity, description) tuples
        """
        problems: List[Tuple[int, str, float, str]] = []
        
        if len(sorted_data) < 5:
            return problems
            
        # Look for direction changes in consecutive frames
        window_size = 5
        
        for i in range(window_size, len(sorted_data)):
            # Get window of frames
            window = sorted_data[i-window_size:i+1]
            
            # Calculate directions
            directions = []
            
            for j in range(1, len(window)):
                prev_x, prev_y = window[j-1][1], window[j-1][2]
                curr_x, curr_y = window[j][1], window[j][2]
                
                dx = curr_x - prev_x
                dy = curr_y - prev_y
                
                # Simplify direction to quadrants (up, down, left, right)
                # This helps detect oscillations even in diagonal movements
                if abs(dx) > abs(dy):
                    # Horizontal movement dominates
                    if dx > 0:
                        direction = "right"
                    else:
                        direction = "left"
                else:
                    # Vertical movement dominates
                    if dy > 0:
                        direction = "up"
                    else:
                        direction = "down"
                    
                directions.append(direction)
            
            # Count direction changes
            direction_changes = 0
            for j in range(1, len(directions)):
                if directions[j] != directions[j-1]:
                    direction_changes += 1
            
            # If there are too many direction changes in the window, it's likely jitter
            # We expect at most 1 direction change in this window for smooth movement
            if direction_changes >= 3:
                # Calculate jitter severity
                severity = min(1.0, direction_changes / window_size)
                
                problems.append((
                    window[-1][0],  # Use the latest frame in the window
                    "jitter",
                    severity,
                    f"Jitter detected at frame {window[-1][0]} ({direction_changes} direction changes in {window_size} frames)"
                ))
        
        return problems

    @staticmethod
    def _detect_static_segments(sorted_data: CurveDataType) -> List[Tuple[int, str, float, str]]:
        """
        Detect segments where there is no movement (static) when there should be.
        
        Args:
            sorted_data: Frame-sorted list of (frame, x, y) tuples
            
        Returns:
            List of (frame, problem_type, severity, description) tuples
        """
        problems: List[Tuple[int, str, float, str]] = []
        
        if len(sorted_data) < 5:
            return problems
            
        # Define minimum expected movement threshold
        movement_threshold = 0.1
        static_threshold = 5  # Minimum number of frames to consider a segment static
        
        # Find static segments
        static_start = None
        static_length = 0
        static_frames = []
        
        for i in range(1, len(sorted_data)):
            prev_frame, prev_x, prev_y = sorted_data[i-1]
            curr_frame, curr_x, curr_y = sorted_data[i]
            
            dx = curr_x - prev_x
            dy = curr_y - prev_y
            distance = math.sqrt(dx*dx + dy*dy)
            
            if distance < movement_threshold:
                # This is a static point
                if static_start is None:
                    static_start = prev_frame
                static_length += 1
                static_frames.append(curr_frame)
            else:
                # Movement detected, check if we had a static segment
                if static_start is not None and static_length >= static_threshold:
                    # Calculate severity based on static segment length
                    severity = min(1.0, static_length / 20)  # Normalize to 0-1
                    
                    problems.append((
                        static_frames[len(static_frames) // 2],  # Use middle frame for reporting
                        "static_segment",
                        severity,
                        f"Static segment detected from frame {static_start} to {curr_frame} ({static_length} frames)"
                    ))
                
                # Reset static segment detection
                static_start = None
                static_length = 0
                static_frames = []
        
        # Check for static segment at the end
        if static_start is not None and static_length >= static_threshold:
            severity = min(1.0, static_length / 20)
            problems.append((
                static_frames[len(static_frames) // 2],  # Use middle frame for reporting
                "static_segment",
                severity,
                f"Static segment detected from frame {static_start} to {sorted_data[-1][0]} ({static_length} frames)"
            ))
        
        return problems

    @staticmethod
    @safe_operation("Analyze Track Quality")
    def analyze_track_quality(curve_data: CurveDataType) -> Dict[str, Any]:
        """
        Perform a comprehensive quality analysis of the tracking data.
        
        Args:
            curve_data: List of (frame, x, y) tuples representing the tracking data
            
        Returns:
            Dictionary with various quality metrics
        """
        if not curve_data or len(curve_data) < 5:
            return {"error": "Not enough points for analysis"}
            
        # Sort by frame
        sorted_data = sorted(curve_data, key=lambda x: x[0])
        
        # Initialize metrics
        metrics: Dict[str, Any] = {
            "point_count": len(sorted_data),
            "frame_range": (sorted_data[0][0], sorted_data[-1][0]),
            "total_frames": sorted_data[-1][0] - sorted_data[0][0] + 1,
            "coverage": 0.0,
            "avg_velocity": 0.0,
            "max_velocity": 0.0,
            "smoothness": 0.0,
            "consistency": 0.0,  # Add consistency for backward compatibility
            "quality_score": 0.0,
            "gaps": []
        }
        
        # Calculate coverage
        metrics["coverage"] = 100.0 * len(sorted_data) / metrics["total_frames"]
        
        # Calculate velocity metrics
        velocities = []
        
        for i in range(1, len(sorted_data)):
            prev_frame, prev_x, prev_y = sorted_data[i-1]
            curr_frame, curr_x, curr_y = sorted_data[i]
            
            frame_diff = curr_frame - prev_frame
            if frame_diff <= 0:
                continue
                
            dx = curr_x - prev_x
            dy = curr_y - prev_y
            distance = math.sqrt(dx*dx + dy*dy)
            velocity = distance / frame_diff
            
            velocities.append(velocity)
        
        if velocities:
            metrics["avg_velocity"] = sum(velocities) / len(velocities)
            metrics["max_velocity"] = max(velocities)
            # Add velocities data for UI display
            metrics["velocities"] = [(sorted_data[i][0], velocities[i-1]) for i in range(1, len(sorted_data))]
        
        # Calculate smoothness (inverse of average acceleration)
        accelerations = []
        
        for i in range(1, len(velocities)):
            accel = abs(velocities[i] - velocities[i-1])
            accelerations.append(accel)
        
        if accelerations:
            avg_accel = sum(accelerations) / len(accelerations)
            # Convert to smoothness score (0-100, higher is better)
            metrics["smoothness"] = 100.0 / (1.0 + avg_accel * 10)
            # Add consistency metric (same as smoothness for backward compatibility)
            metrics["consistency"] = metrics["smoothness"]
            # Add accelerations data for UI display
            metrics["accelerations"] = [(sorted_data[i+1][0], accelerations[i-1]) for i in range(1, len(velocities))]
        
        # Find gaps
        metrics["gaps"] = AnalysisService._detect_gaps(sorted_data)
        
        # Detect problems
        metrics["problems"] = AnalysisService.detect_problems(sorted_data)
        
        # Format problems for TrackQualityUI compatibility
        metrics["problems"] = [(problem_type, description) 
                              for _, problem_type, _, description in metrics["problems"]]
        
        # Overall quality score
        metrics["quality_score"] = AnalysisService._calculate_quality_score(metrics)
        
        return metrics

    @staticmethod
    def _calculate_quality_score(metrics: Dict[str, Any]) -> float:
        """
        Calculate an overall quality score for the track based on metrics.
        
        Args:
            metrics: Dictionary of track quality metrics
            
        Returns:
            Quality score between 0 and 100 (higher is better)
        """
        # Initialize weights and scores
        weights = {
            "coverage": 0.3,
            "smoothness": 0.4,
            "problems": 0.3
        }
        
        scores = {}
        
        # Coverage score (higher is better)
        scores["coverage"] = min(100.0, metrics["coverage"])
        
        # Smoothness score (already normalized, higher is better)
        scores["smoothness"] = min(100.0, metrics["smoothness"])
        
        # Problems score (inverse of problem count, higher is better)
        problem_count = len(metrics.get("problems", []))
        if problem_count == 0:
            scores["problems"] = 100.0
        else:
            # Calculate problems score (0-100, higher means fewer problems)
            scores["problems"] = 100.0 / (1.0 + problem_count / 10.0)
        
        # Calculate weighted score
        overall_score = sum(scores[key] * weights[key] for key in weights)
        
        # Ensure the score is between 0 and 100
        return max(0.0, min(100.0, overall_score))
        
    @staticmethod
    def get_quality_description(quality_score: float) -> str:
        """
        Get a text description of the track quality.
        
        Args:
            quality_score: Numeric quality score (0-100)
            
        Returns:
            Text description of quality
        """
        if quality_score >= 90:
            return "Excellent - Tracking data is very clean and reliable"
        elif quality_score >= 75:
            return "Good - Tracking data has minor issues but is usable"
        elif quality_score >= 50:
            return "Fair - Tracking data has some problems that should be addressed"
        elif quality_score >= 25:
            return "Poor - Tracking data has significant issues requiring cleanup"
        else:
            return "Very Poor - Tracking data has major problems and may need to be redone"
    
    @staticmethod
    def suggest_improvements(analysis: Dict[str, Any]) -> List[str]:
        """
        Suggest improvements based on track analysis.
        
        Args:
            analysis: Analysis results from analyze_track_quality()
            
        Returns:
            List of suggestion strings
        """
        suggestions = []
        
        # Suggestions based on smoothness
        if analysis.get("smoothness", 0) < 50:
            suggestions.append("Apply smoothing to reduce jitter (try Gaussian smoothing)")
        
        # Suggestions based on consistency
        if analysis.get("consistency", 0) < 50:
            suggestions.append("Check for tracking errors or use a median filter to remove outliers")
        
        # Suggestions based on coverage
        if analysis.get("coverage", 0) < 100:
            suggestions.append("Fill gaps in the tracking data using interpolation")
        
        # Suggestions based on specific problems
        for problem_type, description in analysis.get("problems", []):
            if "Gap" in problem_type:
                suggestions.append("Use cubic spline or constant velocity to fill missing frames")
            elif "Velocity" in problem_type or "Jump" in problem_type:
                suggestions.append("Check frames with velocity spikes for tracking errors")
            elif "Jitter" in problem_type:
                suggestions.append("Use 'Remove Jitter' preset to smooth out high-frequency noise")
            elif "Static" in problem_type:
                suggestions.append("Verify if static segments are intentional or need correction")
        
        return suggestions

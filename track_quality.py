#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
from PySide6.QtWidgets import QMessageBox
from typing import Dict, Tuple, List, Any
from dialog_operations import DialogOperations
from services.analysis_service import AnalysisService

class TrackQualityAnalyzer:
    """Analyzes tracking data to determine quality metrics and potential issues."""
    
    @staticmethod
    def analyze_track(curve_data):
        """Analyze track data to calculate quality metrics.
        
        Args:
            curve_data: List of (frame, x, y) tuples
            
        Returns:
            Dictionary of quality metrics
        """
        if not curve_data or len(curve_data) < 3:
            return {
                "quality_score": 0,
                "smoothness": 0,
                "consistency": 0,
                "coverage": 0,
                "problems": []
            }
        
        # Sort data by frame number
        sorted_data = sorted(curve_data, key=lambda p: p[0])
        
        # Calculate basic metrics
        frame_count = len(sorted_data)
        first_frame = sorted_data[0][0]
        last_frame = sorted_data[-1][0]
        expected_frames = last_frame - first_frame + 1
        
        # Calculate velocities and accelerations
        velocities = []
        for i in range(1, len(sorted_data)):
            prev_frame, prev_x, prev_y = sorted_data[i-1]
            curr_frame, curr_x, curr_y = sorted_data[i]
            
            frame_diff = curr_frame - prev_frame
            if frame_diff == 0:
                continue
                
            dx = curr_x - prev_x
            dy = curr_y - prev_y
            distance = math.sqrt(dx*dx + dy*dy)
            velocity = distance / frame_diff
            velocities.append((curr_frame, velocity))
        
        accelerations = []
        for i in range(1, len(velocities)):
            prev_frame, prev_vel = velocities[i-1]
            curr_frame, curr_vel = velocities[i]
            
            frame_diff = curr_frame - prev_frame
            if frame_diff == 0:
                continue
                
            accel = abs(curr_vel - prev_vel) / frame_diff
            accelerations.append((curr_frame, accel))
        
        # Calculate smoothness - inverse of acceleration variance
        if accelerations:
            accel_values = [a[1] for a in accelerations]
            avg_accel = sum(accel_values) / len(accel_values)
            accel_variance = sum((a - avg_accel) ** 2 for a in accel_values) / len(accel_values)
            
            # Normalize to 0-100 scale (higher is better)
            smoothness = 100 / (1 + 10 * accel_variance)
            smoothness = max(0, min(100, smoothness))
        else:
            smoothness = 100  # Perfect smoothness if no accelerations
        
        # Calculate consistency - steadiness of velocity
        if velocities:
            vel_values = [v[1] for v in velocities]
            avg_vel = sum(vel_values) / len(vel_values)
            vel_variance = sum((v - avg_vel) ** 2 for v in vel_values) / len(vel_values)
            
            # Normalize to 0-100 scale (higher is better)
            consistency = 100 / (1 + vel_variance / avg_vel if avg_vel > 0 else 1)
            consistency = max(0, min(100, consistency))
        else:
            consistency = 100  # Perfect consistency if no velocities
        
        # Calculate coverage - percentage of expected frames that have data
        coverage = 100 * frame_count / expected_frames
        
        # Look for problems
        problems = []
        
        # Check for gaps
        frame_set = {f for f, _, _ in sorted_data}
        gap_count = 0
        
        for frame in range(first_frame, last_frame + 1):
            if frame not in frame_set:
                gap_count += 1
                
        if gap_count > 0:
            problems.append(("Gaps", f"Missing {gap_count} of {expected_frames} frames"))
        
        # Check for sudden spikes in velocity
        if velocities:
            avg_vel = sum(v[1] for v in velocities) / len(velocities)
            vel_threshold = 3 * avg_vel  # 3x average is suspicious
            
            spike_frames = []
            for frame, vel in velocities:
                if vel > vel_threshold:
                    spike_frames.append(frame)
                    
            if spike_frames:
                if len(spike_frames) <= 3:
                    frames_str = ", ".join(str(f) for f in spike_frames)
                    problems.append(("Velocity Spikes", f"Sudden movement at frames {frames_str}"))
                else:
                    problems.append(("Velocity Spikes", f"Sudden movement at {len(spike_frames)} frames"))
        
        # Check for jitter
        if accelerations:
            avg_accel = sum(a[1] for a in accelerations) / len(accelerations)
            accel_threshold = 3 * avg_accel  # 3x average is suspicious
            
            jitter_frames = []
            for frame, accel in accelerations:
                if accel > accel_threshold:
                    jitter_frames.append(frame)
                    
            if jitter_frames:
                if len(jitter_frames) <= 3:
                    frames_str = ", ".join(str(f) for f in jitter_frames)
                    problems.append(("Jitter", f"High acceleration at frames {frames_str}"))
                else:
                    problems.append(("Jitter", f"High acceleration at {len(jitter_frames)} frames"))
        
        # Calculate overall quality score (0-100)
        # Weighted average of smoothness, consistency, and coverage
        quality_score = (
            0.4 * smoothness +  # Smoothness is most important
            0.3 * consistency +  # Consistency is next
            0.3 * coverage       # Coverage also matters
        )
        
        # Reduce score based on number of problems
        problem_penalty = 5 * len(problems)
        quality_score = max(0, quality_score - problem_penalty)
        
        return {
            "quality_score": quality_score,
            "smoothness": smoothness,
            "consistency": consistency,
            "coverage": coverage,
            "problems": problems,
            "velocities": velocities,
            "accelerations": accelerations
        }
    
    @staticmethod
    def get_quality_description(quality_score):
        """Get a text description of the track quality.
        
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
    def suggest_improvements(analysis):
        """Suggest improvements based on track analysis.
        
        Args:
            analysis: Analysis results from analyze_track()
            
        Returns:
            List of suggestion strings
        """
        suggestions = []
        
        # Suggestions based on smoothness
        if analysis["smoothness"] < 50:
            suggestions.append("Apply smoothing to reduce jitter (try Gaussian smoothing)")
        
        # Suggestions based on consistency
        if analysis["consistency"] < 50:
            suggestions.append("Check for tracking errors or use a median filter to remove outliers")
        
        # Suggestions based on coverage
        if analysis["coverage"] < 100:
            suggestions.append("Fill gaps in the tracking data using interpolation")
        
        # Suggestions based on specific problems
        for problem_type, description in analysis["problems"]:
            if problem_type == "Gaps":
                suggestions.append("Use cubic spline or constant velocity to fill missing frames")
            elif problem_type == "Velocity Spikes":
                suggestions.append("Check frames with velocity spikes for tracking errors")
            elif problem_type == "Jitter":
                suggestions.append("Use 'Remove Jitter' preset to smooth out high-frequency noise")
        
        return suggestions

    @staticmethod
    def detect_problems(curve_data):
        """Detect potential problems in the tracking data.
        
        Args:
            curve_data: List of (frame, x, y) tuples.
            
        Returns:
            A list of detected problems with format [(frame, type, severity, description), ...]
            Severity is a float between 0.0 and 1.0 (higher is worse).
        """
        if not curve_data or len(curve_data) < 2: # Need at least 2 points for most checks
            return []
            
        # Sort by frame
        sorted_data = sorted(curve_data, key=lambda x: x[0])
        
        problems = []
        
        # 1. Check for sudden jumps in position
        for i in range(1, len(sorted_data)):
            prev_frame, prev_x, prev_y = sorted_data[i-1]
            frame, x, y = sorted_data[i]
            
            # Calculate distance between consecutive points
            distance = math.sqrt((x - prev_x)**2 + (y - prev_y)**2)
            
            # Also check if frames are consecutive
            frame_gap = frame - prev_frame
            
            # Normalize by frame gap (for non-consecutive frames)
            if frame_gap > 0: # Avoid division by zero
                normalized_distance = distance / frame_gap
            else:
                normalized_distance = distance # Treat as consecutive if frame_gap is 0 or negative (unlikely but safe)
                
            # Define thresholds for jumps
            medium_threshold = 10.0  # Adjust based on typical movement
            high_threshold = 30.0
            
            if normalized_distance > high_threshold:
                severity = min(1.0, normalized_distance / (high_threshold * 2)) # Cap severity at 1.0
                problems.append((frame, "Sudden Jump", severity, 
                                f"Distance of {distance:.2f} pixels from frame {prev_frame} ({normalized_distance:.2f}/frame)"))
            elif normalized_distance > medium_threshold:
                severity = min(0.7, normalized_distance / high_threshold) # Cap severity
                problems.append((frame, "Large Movement", severity,
                                f"Distance of {distance:.2f} pixels from frame {prev_frame} ({normalized_distance:.2f}/frame)"))
        
        # 2. Check for acceleration (changes in velocity)
        if len(sorted_data) >= 3: # Need at least 3 points for acceleration
            for i in range(2, len(sorted_data)):
                frame_2, x_2, y_2 = sorted_data[i-2]
                frame_1, x_1, y_1 = sorted_data[i-1]
                frame_0, x_0, y_0 = sorted_data[i]
                
                # Calculate velocities (distance per frame)
                time_1 = frame_1 - frame_2
                time_0 = frame_0 - frame_1
                
                # Avoid division by zero if frames are identical
                if time_1 == 0 or time_0 == 0:
                    continue
                    
                dx_1 = (x_1 - x_2) / time_1
                dy_1 = (y_1 - y_2) / time_1
                
                dx_0 = (x_0 - x_1) / time_0
                dy_0 = (y_0 - y_1) / time_0
                
                # Calculate change in velocity (acceleration)
                accel_x = abs(dx_0 - dx_1)
                accel_y = abs(dy_0 - dy_1)
                
                # Calculate magnitude of acceleration
                accel_mag = math.sqrt(accel_x**2 + accel_y**2)
                
                # Define thresholds for acceleration
                medium_threshold = 0.8  # Adjust based on typical acceleration
                high_threshold = 2.0
                
                if accel_mag > high_threshold:
                    severity = min(0.9, accel_mag / (high_threshold * 2)) # Cap severity
                    problems.append((frame_0, "High Acceleration", severity,
                                    f"Acceleration of {accel_mag:.2f} pixels/frame²"))
                elif accel_mag > medium_threshold:
                    severity = min(0.6, accel_mag / high_threshold) # Cap severity
                    problems.append((frame_0, "Medium Acceleration", severity,
                                    f"Acceleration of {accel_mag:.2f} pixels/frame²"))
        
        # 3. Check for gaps in tracking
        for i in range(1, len(sorted_data)):
            prev_frame = sorted_data[i-1][0]
            frame = sorted_data[i][0]
            
            frame_gap = frame - prev_frame
            
            if frame_gap > 10: # Large gap threshold
                severity = min(1.0, frame_gap / 30.0) # Cap severity
                problems.append((prev_frame, "Large Gap", severity,
                                f"Gap of {frame_gap} frames after this point"))
            elif frame_gap > 1: # Small gap threshold (changed from 3 to 1 to catch any gap)
                severity = min(0.5, frame_gap / 10.0) # Cap severity
                problems.append((prev_frame, "Small Gap", severity,
                                f"Gap of {frame_gap} frames after this point"))
        
        # 4. Check for excessive jitter (local variance)
        if len(sorted_data) >= 5:
            window_size = 5
            half_window = window_size // 2
            
            for i in range(half_window, len(sorted_data) - half_window):
                # Define window around point i
                start_idx = i - half_window
                end_idx = i + half_window
                window = sorted_data[start_idx : end_idx + 1]
                
                # Calculate the average position in the window
                avg_x = sum(p[1] for p in window) / window_size
                avg_y = sum(p[2] for p in window) / window_size
                
                # Calculate the variance (mean squared difference from average)
                var_x = sum((p[1] - avg_x)**2 for p in window) / window_size
                var_y = sum((p[2] - avg_y)**2 for p in window) / window_size
                
                # Calculate the total variance magnitude (jitter)
                jitter = math.sqrt(var_x + var_y)
                
                # Define thresholds for jitter
                medium_threshold = 2.0  # Adjust based on typical jitter
                high_threshold = 5.0
                
                current_frame = sorted_data[i][0]
                if jitter > high_threshold:
                    severity = min(0.8, jitter / (high_threshold * 2)) # Cap severity
                    problems.append((current_frame, "High Jitter", severity,
                                    f"Jitter of {jitter:.2f} pixels in a {window_size}-frame window"))
                elif jitter > medium_threshold:
                    severity = min(0.5, jitter / high_threshold) # Cap severity
                    problems.append((current_frame, "Medium Jitter", severity,
                                    f"Jitter of {jitter:.2f} pixels in a {window_size}-frame window"))
        
        # Sort problems by frame for easier navigation
        problems.sort(key=lambda x: x[0])
        
        # Remove duplicate problems (same frame, same type) - keep highest severity
        unique_problems: dict[tuple[int, str], tuple[str, float, str]] = {}
        for frame, p_type, severity, desc in problems:
            key = (frame, p_type)
            if key not in unique_problems or severity > unique_problems[key][1]:
                 unique_problems[key] = (p_type, severity, desc)

        # Convert back to list format
        final_problems = [(frame, p_type, severity, desc) for (frame, p_type), (p_type_val, severity, desc) in unique_problems.items()]
        final_problems.sort(key=lambda x: x[0]) # Sort again after potential reordering

        return final_problems


class TrackQualityUI:
    """Handles UI interactions for track quality analysis.
    
    This class separates UI logic from the analysis logic, making it easier to
    maintain and extend.
    """
    
    def __init__(self, parent_window):
        """Initialize with reference to parent window for UI interactions.
        
        Args:
            parent_window: The main window that will display quality information
        """
        self.parent = parent_window
        self.analyzer = TrackQualityAnalyzer()
        
    def analyze_and_update_ui(self, curve_data):
        """Analyze track quality and update UI components with results.
        
        Args:
            curve_data: List of (frame, x, y) tuples
            
        Returns:
            Analysis results dictionary
        """
        if not curve_data:
            QMessageBox.warning(self.parent, "No Data", "No tracking data loaded.")
            return None
            
        # Run the quality analysis using the AnalysisService
        analysis = AnalysisService.analyze_track_quality(curve_data)
        
        # Update the UI with the results if we have access to the UI components
        if hasattr(self.parent, 'quality_score_label'):
            quality_score = analysis["quality_score"]
            self.parent.quality_score_label.setText(f"{quality_score:.1f}/100")
            
            # Set color based on score
            if quality_score >= 75:
                self.parent.quality_score_label.setStyleSheet("color: green;")
            elif quality_score >= 50:
                self.parent.quality_score_label.setStyleSheet("color: orange;")
            else:
                self.parent.quality_score_label.setStyleSheet("color: red;")
            
            # Update metrics
            if hasattr(self.parent, 'smoothness_label'):
                self.parent.smoothness_label.setText(f"{analysis['smoothness']:.1f}/100")
            if hasattr(self.parent, 'consistency_label'):
                self.parent.consistency_label.setText(f"{analysis['consistency']:.1f}/100")
            if hasattr(self.parent, 'coverage_label'):
                self.parent.coverage_label.setText(f"{analysis['coverage']:.1f}%")
            
            # Get quality description from AnalysisService
            quality_desc = AnalysisService.get_quality_description(quality_score)
            
            # Update status bar with description
            self.parent.statusBar().showMessage(f"Track Quality: {quality_desc}")
            
            # If problems were found, offer to view them
            if analysis["problems"]:
                problems_count = len(analysis["problems"])
                reply = QMessageBox.question(
                    self.parent, 
                    "Problems Detected", 
                    f"{problems_count} potential problems detected in the tracking data. Would you like to view them?",
                    QMessageBox.Yes | QMessageBox.No)
                    
                if reply == QMessageBox.Yes:
                    # Use the AnalysisService to detect problems
                    problems = AnalysisService.detect_problems(self.parent.curve_data)
                    DialogOperations.show_problem_detection_dialog(self.parent, problems)
                    
            # Show suggestions in a tooltip on the analyze button
            if hasattr(self.parent, 'analyze_button'):
                suggestions = AnalysisService.suggest_improvements(analysis)
                if suggestions:
                    suggestion_text = "\n".join([f"• {s}" for s in suggestions])
                    self.parent.analyze_button.setToolTip(f"Suggestions:\n{suggestion_text}")
                else:
                    self.parent.analyze_button.setToolTip("No suggestions - track quality is good")
                
            # If EnhancedCurveView is being used, show the velocities if available
            if hasattr(self.parent, 'curve_view') and hasattr(self.parent.curve_view, 'toggleVelocityVectors') and "velocities" in analysis:
                self.parent.curve_view.setVelocityData(analysis["velocities"])
                # Only show vectors if there are problems
                if analysis["problems"] and hasattr(self.parent, 'toggle_vectors_button'):
                    self.parent.curve_view.toggleVelocityVectors(True)
                    self.parent.toggle_vectors_button.setChecked(True)
        
        return analysis

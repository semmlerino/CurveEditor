#!/usr/bin/env python
# -*- coding: utf-8 -*-

import math
from PySide6.QtWidgets import QMessageBox
from dialog_operations import DialogOperations
from curve_operations import CurveOperations

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
            
        # Run the quality analysis
        analysis = self.analyzer.analyze_track(curve_data)
        
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
            
            # Get quality description
            quality_desc = self.analyzer.get_quality_description(quality_score)
            
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
                    problems = CurveOperations.detect_problems(self.parent)
                    DialogOperations.show_problem_detection_dialog(self.parent, problems)
                    
            # Show suggestions in a tooltip on the analyze button
            if hasattr(self.parent, 'analyze_button'):
                suggestions = self.analyzer.suggest_improvements(analysis)
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

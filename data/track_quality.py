#!/usr/bin/env python

"""Track quality analysis module for evaluating tracking data quality.

This module provides two main classes:
1. TrackQualityAnalysisService - Core analysis of tracking data quality and problem detection
2. TrackQualityUI - UI integration for displaying analysis results
"""

# Standard library imports
import math
from typing import TypedDict

from PySide6.QtWidgets import QMessageBox

from services.dialog_service import DialogService
from ui.ui_scaling import UIScaling

class TrackPoint(TypedDict):
    frame: int
    x: float
    y: float
    interpolated: bool

class VelocityPoint(TypedDict):
    frame: int
    value: float

class AccelerationPoint(TypedDict):
    frame: int
    value: float

class BasicMetrics(TypedDict):
    frame_count: int
    first_frame: int
    last_frame: int
    expected_frames: int
    coverage: float

class FrameDetails(TypedDict):
    first_frame: int
    last_frame: int
    total_frames: int
    expected_frames: int
    frame_set: set[int]

class QualityAnalysis(TypedDict):
    quality_score: float
    smoothness: float
    consistency: float
    coverage: float
    problems: list[tuple[str, str]]
    velocities: list[VelocityPoint]
    accelerations: list[AccelerationPoint]

class TrackQualityAnalysisService:
    """Analyzes tracking data to determine quality metrics and potential issues.

    This class provides methods for analyzing track quality, detecting problems,
    and suggesting improvements for tracking data quality.
    """

    @staticmethod
    def analyze_track(curve_data) -> QualityAnalysis:
        """Analyze track data to calculate quality metrics.

        Args:
            curve_data: list of (frame, x, y) tuples

        Returns:
            Dictionary of quality metrics
        """
        if not curve_data or len(curve_data) < 3:
            return {
                "quality_score": 0,
                "smoothness": 0,
                "consistency": 0,
                "coverage": 0,
                "problems": [],
                "velocities": [],
                "accelerations": [],
            }

        # Get sorted track data and basic metrics
        sorted_data = sorted(curve_data, key=lambda p: p[0])
        basic_metrics = TrackQualityAnalysisService._calculate_basic_metrics(sorted_data)

        # Calculate velocity and acceleration
        velocities = TrackQualityAnalysisService._calculate_velocities(sorted_data)
        accelerations = TrackQualityAnalysisService._calculate_accelerations(velocities)

        # Calculate quality metrics
        smoothness = TrackQualityAnalysisService._calculate_smoothness(accelerations)
        consistency = TrackQualityAnalysisService._calculate_consistency(velocities)
        coverage = 100 * len(sorted_data) / basic_metrics["expected_frames"]

        # Detect problems
        problems = TrackQualityAnalysisService._detect_track_problems(
            sorted_data, velocities, accelerations, basic_metrics
        )

        # Calculate quality score
        quality_score = TrackQualityAnalysisService._calculate_quality_score(
            smoothness, consistency, coverage, problems
        )

        return {
            "quality_score": quality_score,
            "smoothness": smoothness,
            "consistency": consistency,
            "coverage": coverage,
            "problems": problems,
            "velocities": velocities,
            "accelerations": accelerations,
        }

    @staticmethod
    def _calculate_basic_metrics(sorted_data) -> BasicMetrics:
        """Calculate basic track metrics (frame count, first/last frame, etc).

        Args:
            sorted_data: list of sorted (frame, x, y) tuples

        Returns:
            Dictionary of basic metrics
        """
        frame_details = TrackQualityAnalysisService._get_frame_details(sorted_data)
        frame_count = frame_details["total_frames"]
        expected_frames = frame_details["expected_frames"]

        return {
            "frame_count": frame_count,
            "first_frame": frame_details["first_frame"],
            "last_frame": frame_details["last_frame"],
            "expected_frames": expected_frames,
            "coverage": 100 * frame_count / expected_frames,
        }

    @staticmethod
    def _calculate_velocities(sorted_data) -> list[VelocityPoint]:
        """Calculate velocity values from track data.

        Args:
            sorted_data: list of sorted (frame, x, y) tuples

        Returns: list of VelocityPoint objects
        """
        velocities: list[VelocityPoint] = []

        for i in range(1, len(sorted_data)):
            # Get current and previous positions
            prev_frame, prev_x, prev_y = sorted_data[i - 1][:3]
            curr_frame, curr_x, curr_y = sorted_data[i][:3]

            # Calculate time (frame) difference
            frame_diff = curr_frame - prev_frame
            if frame_diff <= 0:  # Skip if frames are identical or out of order
                continue

            # Calculate distance between positions
            dist = math.sqrt((curr_x - prev_x) ** 2 + (curr_y - prev_y) ** 2)

            # Calculate velocity (distance / time)
            velocity = dist / frame_diff

            # Store as VelocityPoint
            velocities.append({"frame": curr_frame, "value": velocity})

        return velocities

    @staticmethod
    def _calculate_accelerations(velocities: list[VelocityPoint]) -> list[AccelerationPoint]:
        """Calculate acceleration values from velocity data.

        Args:
            velocities: list of VelocityPoint objects

        Returns: list of AccelerationPoint objects
        """
        accelerations: list[AccelerationPoint] = []

        for i in range(1, len(velocities)):
            prev_frame = velocities[i - 1]["frame"]
            prev_vel = velocities[i - 1]["value"]
            curr_frame = velocities[i]["frame"]
            curr_vel = velocities[i]["value"]

            frame_diff = curr_frame - prev_frame
            if frame_diff == 0:
                continue

            accel = (curr_vel - prev_vel) / frame_diff
            accelerations.append({"frame": curr_frame, "value": accel})

        return accelerations

    @staticmethod
    def _calculate_smoothness(accelerations: list[AccelerationPoint]) -> float:
        """Calculate smoothness metric from acceleration data.

        Args:
            accelerations: list of AccelerationPoint objects

        Returns:
            Smoothness value (0-100, higher is better)
        """
        if not accelerations or len(accelerations) < 2:
            return 100.0  # No accelerations means perfectly smooth (or no data)

        # Calculate average acceleration
        accel_values = [abs(a["value"]) for a in accelerations]
        avg_accel = sum(accel_values) / len(accel_values)

        # Higher accelerations mean less smoothness
        # Scale to 0-100 range with 0 being worst
        smoothness = 100.0 - min(100.0, avg_accel * 10.0)

        return max(0.0, min(100.0, smoothness))

    @staticmethod
    def _calculate_consistency(velocities: list[VelocityPoint]) -> float:
        """Calculate consistency metric from velocity data.

        Args:
            velocities: list of VelocityPoint objects

        Returns:
            Consistency value (0-100, higher is better)
        """
        if not velocities or len(velocities) < 2:
            return 100.0  # No velocities means perfectly consistent (or no data)

        # Calculate standard deviation of velocity
        values = [v["value"] for v in velocities]
        mean_vel = sum(values) / len(values)
        variance = sum((v - mean_vel) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance)

        # Calculate coefficient of variation (normalized std dev)
        # Avoid division by zero
        if mean_vel == 0:
            cv: float = 0.0
        else:
            cv = std_dev / mean_vel

        # Scale to 0-100 range with 100 being most consistent
        # A CV of 0.5 or greater is considered inconsistent
        consistency = 100.0 * (1.0 - min(1.0, cv / 0.5))

        return consistency

    @staticmethod
    def _detect_track_problems(
        sorted_data,
        velocities: list[VelocityPoint],
        accelerations: list[AccelerationPoint],
        basic_metrics: BasicMetrics,
    ) -> list[tuple[str, str]]:
        """Detect common problems in track data.

        Args:
            sorted_data: list of sorted (frame, x, y) tuples
            velocities: list of (frame, velocity) tuples
            accelerations: list of (frame, acceleration) tuples
            basic_metrics: dictionary of basic track metrics

        Returns: list of (problem_type, description) tuples
        """
        problems: list[tuple[str, str]] = []

        # Create a set of frames for gap detection
        first_frame = basic_metrics["first_frame"]
        last_frame = basic_metrics["last_frame"]
        expected_frames = basic_metrics["expected_frames"]
        frame_set: set[int] = {p[:3][0] for p in sorted_data}

        # Detect gaps
        gap_count = 0
        for frame in range(first_frame, last_frame + 1):
            if frame not in frame_set:
                gap_count += 1
        if gap_count > 0:
            problems.append(("Gaps", f"Missing {gap_count} of {expected_frames} frames"))

        # Detect velocity spikes
        if velocities:
            # Calculate average and standard deviation
            values = [v["value"] for v in velocities]
            mean_velocity = sum(values) / len(values)
            std_dev = math.sqrt(sum((v - mean_velocity) ** 2 for v in values) / len(values))

            # Look for outliers beyond 3 standard deviations
            threshold = mean_velocity + 3 * std_dev
            spike_count = sum(1 for v in values if v > threshold)

            if spike_count > 0:
                problems.append(("Velocity Spikes", f"Found {spike_count} large velocity changes"))

        # Detect jitter
        if accelerations:
            # Calculate average acceleration magnitude
            acc_values = [abs(a["value"]) for a in accelerations]
            mean_acc = sum(acc_values) / len(acc_values)

            # Check for significant jitter
            if mean_acc > 5.0:  # Threshold for jittery motion
                problems.append(("Jitter", f"Detected unstable motion (avg acceleration: {mean_acc:.1f})"))

        return problems

    @staticmethod
    def _get_frame_details(sorted_data) -> FrameDetails:
        """Extract frame details from sorted track data.

        Args:
            sorted_data: list of sorted (frame, x, y) tuples

        Returns:
            Dictionary with frame details
        """
        frames = [p[0] for p in sorted_data]
        return {
            "first_frame": frames[0],
            "last_frame": frames[-1],
            "total_frames": len(sorted_data),
            "expected_frames": frames[-1] - frames[0] + 1,
            "frame_set": set(frames),
        }

    @staticmethod
    def _calculate_quality_score(
        smoothness: float, consistency: float, coverage: float, problems: list[tuple[str, str]]
    ) -> float:
        """Calculate overall quality score from individual metrics.

        Args:
            smoothness: Smoothness metric (0-100)
            consistency: Consistency metric (0-100)
            coverage: Coverage metric (0-100)
            problems: list of detected problems

        Returns:
            Overall quality score (0-100)
        """
        # Weighted average of smoothness, consistency, and coverage
        quality_score = (
            0.4 * smoothness  # Smoothness is most important
            + 0.3 * consistency  # Consistency is next
            + 0.3 * coverage  # Coverage also matters
        )

        # Reduce score based on number of problems
        problem_penalty = 5 * len(problems)
        quality_score = max(0, quality_score - problem_penalty)

        return quality_score

    @staticmethod
    def get_quality_description(quality_score: float) -> str:
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
    def suggest_improvements(analysis: QualityAnalysis) -> list[str]:
        """Suggest improvements based on track analysis.

        Args:
            analysis: Analysis results from analyze_track()

        Returns: list of suggestion strings
        """
        suggestions: list[str] = []

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
        problems: list[tuple[str, str]] = analysis["problems"]
        for problem_type, _ in problems:
            if problem_type == "Gaps":
                suggestions.append("Use cubic spline or constant velocity to fill missing frames")
            elif problem_type == "Velocity Spikes":
                suggestions.append("Check frames with velocity spikes for tracking errors")
            elif problem_type == "Jitter":
                suggestions.append("Use 'Remove Jitter' preset to smooth out high-frequency noise")

        return suggestions

    @staticmethod
    def detect_problems(curve_data) -> list[tuple[int, str, float, str]]:
        """Detect potential problems in the tracking data with detailed information.

        Args:
            curve_data: list of (frame, x, y) tuples.

        Returns:
            A list of detected problems with format [(frame, type, severity, description), ...]
            Severity is a float between 0.0 and 1.0 (higher is worse).
        """
        if not curve_data or len(curve_data) < 3:
            return []

        sorted_data = sorted(curve_data, key=lambda p: p[0])
        problems: list[tuple[int, str, float, str]] = []

        # Detect position jumps (sudden changes in position)
        for i in range(1, len(sorted_data)):
            prev_x, prev_y = sorted_data[i - 1][1:3]
            x, y = sorted_data[i][1:3]

            # Calculate distance between consecutive points
            distance = math.sqrt((x - prev_x) ** 2 + (y - prev_y) ** 2)

            # Check for a jump (threshold depends on your data scale)
            if distance > 30:  # Significant jump
                severity = min(1.0, distance / 50.0)
                problems.append(
                    (sorted_data[i][0], "Position Jump", severity, f"Jump of {distance:.1f} pixels detected")
                )

        # Detect velocity/acceleration issues
        if len(sorted_data) >= 3:
            velocities = TrackQualityAnalysisService._calculate_velocities(sorted_data)
            accelerations = TrackQualityAnalysisService._calculate_accelerations(velocities)

            # Detect velocity spikes
            if velocities:
                v_values = [v["value"] for v in velocities]
                v_mean = sum(v_values) / len(v_values)
                v_std = math.sqrt(sum((v - v_mean) ** 2 for v in v_values) / len(v_values)) if len(v_values) > 1 else 0

                for velocity_point in velocities:
                    frame = velocity_point["frame"]
                    velocity = velocity_point["value"]
                    if velocity > v_mean + 3 * v_std and velocity > 20:  # Threshold
                        severity = min(1.0, (velocity - v_mean) / (4 * v_std)) if v_std > 0 else 0.5
                        problems.append(
                            (
                                frame,
                                "Velocity Spike",
                                severity,
                                f"Velocity of {velocity:.1f} (threshold: {v_mean + 3 * v_std:.1f})",
                            )
                        )

            # Detect acceleration issues
            if accelerations:
                a_values = [abs(a["value"]) for a in accelerations]
                a_mean = sum(a_values) / len(a_values)

                for accel_point in accelerations:
                    frame = accel_point["frame"]
                    acc_abs = abs(accel_point["value"])
                    if acc_abs > a_mean * 3 and acc_abs > 10:  # Threshold
                        severity = min(1.0, acc_abs / 20.0)
                        problems.append(
                            (frame, "Acceleration Issue", severity, f"Acceleration of {acc_abs:.1f} detected")
                        )

        # Detect gaps in tracking
        for i in range(1, len(sorted_data)):
            prev_frame = sorted_data[i - 1][0]
            frame = sorted_data[i][0]
            frame_gap = frame - prev_frame

            if frame_gap > 10:  # Large gap threshold
                severity = min(1.0, frame_gap / 30.0)  # Cap severity
                problems.append((prev_frame, "Large Gap", severity, f"Gap of {frame_gap} frames after this point"))
            elif frame_gap > 1:  # Small gap threshold (catch any gap)
                severity = min(0.5, frame_gap / 10.0)  # Cap severity
                problems.append((prev_frame, "Small Gap", severity, f"Gap of {frame_gap} frames after this point"))

        # Check for excessive jitter (local variance)
        if len(sorted_data) >= 5:
            window_size = 5
            half_window = window_size // 2
            medium_threshold = 2.0  # Adjust based on typical jitter
            high_threshold = 5.0

            for i in range(half_window, len(sorted_data) - half_window):
                # Define window around point i
                start_idx = i - half_window
                end_idx = i + half_window
                window = [p[:3] for p in sorted_data[start_idx : end_idx + 1]]

                # Calculate the average position in the window
                avg_x = sum(p[1] for p in window) / window_size
                avg_y = sum(p[2] for p in window) / window_size

                # Calculate the variance (mean squared difference from average)
                var_x = sum((p[1] - avg_x) ** 2 for p in window) / window_size
                var_y = sum((p[2] - avg_y) ** 2 for p in window) / window_size

                # Calculate the total variance magnitude (jitter)
                jitter = math.sqrt(var_x + var_y)

                # Define thresholds for jitter
                current_frame = sorted_data[i][:3][0]
                if jitter > high_threshold:
                    severity = min(0.8, jitter / (high_threshold * 2))  # Cap severity
                    problems.append(
                        (
                            current_frame,
                            "High Jitter",
                            severity,
                            f"Jitter of {jitter:.2f} pixels in a {window_size}-frame window",
                        )
                    )
                elif jitter > medium_threshold:
                    severity = min(0.5, jitter / high_threshold)  # Cap severity
                    problems.append(
                        (
                            current_frame,
                            "Medium Jitter",
                            severity,
                            f"Jitter of {jitter:.2f} pixels in a {window_size}-frame window",
                        )
                    )

        # Sort problems by frame number
        problems.sort(key=lambda p: p[0])

        return problems

    # Removed _detect_jitter_issues: Functionality integrated into detect_problems

class TrackQualityUI:
    """Handles UI interactions for track quality analysis.

    This class separates UI logic from the analysis logic, making it easier to
    maintain and extend. It uses the TrackQualityUIProtocol for type checking
    and safer UI interactions.
    """

    def __init__(self, parent_window: "TrackQualityUIProtocol") -> None:
        """Initialize with reference to main window for UI interactions.

        Args:
            parent_window: The main window (must implement TrackQualityUIProtocol)
                that will display quality information
        """
        self.parent = parent_window

    def analyze_and_update_ui(self, curve_data) -> QualityAnalysis | None:
        """Analyze track quality and update UI components with results.

        Args:
            curve_data: list of (frame, x, y) tuples

        Returns:
            Analysis results dictionary
        """
        if not curve_data:
            QMessageBox.warning(self.parent.widget, "No Data", "No tracking data loaded.")
            return None

        # Run the quality analysis
        analysis = TrackQualityAnalysisService.analyze_track(curve_data)

        # Update UI components using the protocol's fields
        self._update_quality_score(analysis)
        self._update_metric_labels(analysis)
        self._update_status_bar(analysis["quality_score"])
        self._handle_problems(analysis, curve_data)
        self._update_suggestions(analysis)
        self._update_velocity_visualization(analysis)

        return analysis

    def _update_quality_score(self, analysis: QualityAnalysis) -> None:
        """Update the quality score label with color coding.

        Args:
            analysis: Analysis results dictionary
        """
        quality_score = analysis["quality_score"]
        self.parent.quality_score_label.setText(f"{quality_score:.1f}/100")

        # Set color based on score using theme-aware colors
        if quality_score >= 75:
            color = UIScaling.get_color("text_success")
            self.parent.quality_score_label.setStyleSheet(f"color: {color};")
        elif quality_score >= 50:
            color = UIScaling.get_color("text_warning")
            self.parent.quality_score_label.setStyleSheet(f"color: {color};")
        else:
            color = UIScaling.get_color("text_error")
            self.parent.quality_score_label.setStyleSheet(f"color: {color};")

    def _update_metric_labels(self, analysis: QualityAnalysis) -> None:
        """Update metric labels with analysis results.

        Args:
            analysis: Analysis results dictionary
        """
        self.parent.smoothness_label.setText(f"{analysis['smoothness']:.1f}/100")
        self.parent.consistency_label.setText(f"{analysis['consistency']:.1f}/100")
        self.parent.coverage_label.setText(f"{analysis['coverage']:.1f}%")

    def _update_status_bar(self, quality_score: float) -> None:
        """Update status bar with quality description.

        Args:
            quality_score: Numeric quality score
        """
        quality_desc = TrackQualityAnalysisService.get_quality_description(quality_score)
        self.parent.statusBar().showMessage(f"Track Quality: {quality_desc}")

    def _handle_problems(self, analysis: QualityAnalysis, curve_data) -> None:
        """Handle problem detection and dialog display.

        Args:
            analysis: Analysis results dictionary
            curve_data: Track point data
        """
        if not analysis["problems"]:
            return

        problems_count = len(analysis["problems"])
        reply = QMessageBox.question(
            self.parent.widget,
            "Problems Detected",
            f"{problems_count} potential problems detected in the tracking data. Would you like to view them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Use the TrackQualityAnalyzer to detect detailed problems
            problems = TrackQualityAnalysisService.detect_problems(self.parent.curve_data)
            DialogService.show_problem_detection_dialog(self.parent, problems)

    def _update_suggestions(self, analysis: QualityAnalysis) -> None:
        """Update tooltip with improvement suggestions.

        Args:
            analysis: Analysis results dictionary
        """
        suggestions = TrackQualityAnalysisService.suggest_improvements(analysis)
        if suggestions:
            suggestion_text = "\n".join([f"• {s}" for s in suggestions])
            self.parent.analyze_button.setToolTip(f"Suggestions:\n{suggestion_text}")
        else:
            self.parent.analyze_button.setToolTip("No suggestions - track quality is good")

    def _update_velocity_visualization(self, analysis: QualityAnalysis) -> None:
        """Update velocity vector visualization if available.

        Args:
            analysis: Analysis results dictionary
        """
        # Check if the curve view supports velocity vectors
        if self.parent.curve_view is None or not hasattr(self.parent.curve_view, "toggleVelocityVectors"):
            return

        if "velocities" not in analysis:
            return

        # Set velocity data and toggle vectors if problems were found
        # Convert VelocityPoint list to velocity vector format expected by setVelocityData
        velocity_vectors = [(v["value"], 0.0) for v in analysis["velocities"]]
        self.parent.curve_view.setVelocityData(velocity_vectors)

        if analysis["problems"]:
            self.parent.curve_view.toggleVelocityVectors(True)
            self.parent.toggle_vectors_button.setChecked(True)

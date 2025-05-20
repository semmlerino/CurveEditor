from typing import List, Tuple, Optional, Dict, TypeVar, Protocol, Any
import copy
from services.protocols import PointsList
import math

from services.logging_service import LoggingService
from services.unified_transformation_service import UnifiedTransformationService

# Configure logger for this module
logger = LoggingService.get_logger("analysis_service")

# Track if scipy is available
has_scipy = False

# Define CubicSpline type and implementation
CubicSplineType = Any  # This avoids issues with complex type annotations


class CurveProcessor(Protocol):
    """Protocol defining the interface for curve processors"""

    def get_data(self) -> PointsList:
        """Get the processed curve data"""
        ...

    def smooth_moving_average(self, indices: List[int], window_size: int) -> None:
        """Apply moving average smoothing"""
        ...


T = TypeVar('T', bound=CurveProcessor)


class ConcreteCurveProcessor:
    """Concrete implementation of CurveProcessor"""

    def __init__(self, data: PointsList) -> None:
        """Initialize with curve data"""
        self.data: PointsList = copy.deepcopy(data)

    def get_data(self) -> PointsList:
        """Get the processed curve data"""
        return self.data

    def smooth_moving_average(self, indices: List[int], window_size: int, real_view: Any = None) -> None:
        """Apply moving average smoothing to x and y coordinates.

        This implementation uses all points with indices in the 'indices' parameter
        to calculate the average values, then applies these averages to each point.
        Uses the UnifiedTransformationService's stable_transformation_context to prevent
        point drift in screen space.
        
        Args:
            indices: List of indices to smooth
            window_size: Size of the smoothing window
            real_view: Optional reference to the actual curve view for stable transformation
        """
        logger.info(f"Starting smooth_moving_average with {len(indices)} indices and window_size={window_size}")
        if not self.data or not indices:
            logger.warning(f"Smoothing skipped: data={bool(self.data)}, indices={bool(indices)}, window={window_size}")
            return

        # Sort indices to maintain data structure and filter out invalid indices
        sorted_indices = [idx for idx in sorted(indices) if 0 <= idx < len(self.data)]
        if not sorted_indices:
            logger.warning("No valid indices to smooth")
            return
        
        logger.info(f"Valid indices: first={sorted_indices[0]}, last={sorted_indices[-1]}, count={len(sorted_indices)}")

        # Create a copy of the data for processing
        result = copy.deepcopy(self.data)
        
        # Create a mock curve view to use with the transformation service
        # This allows us to use the stable_transformation_context
        from PySide6.QtWidgets import QWidget
        
        class MockCurveView(QWidget):
            """
            Mock curve view used for operations requiring transformation.
            This allows for consistent work with transformation while allowing reuse of 
            processing routines.
            """
            def __init__(self, points, real_view=None):
                super().__init__()
                self.points = points
                self._real_view = real_view  # Store reference to real view for stable transforms
                
                # Copy parameters from real view if provided
                if real_view is not None:
                    self.zoom_factor = getattr(real_view, 'zoom_factor', 1.0)
                    self.offset_x = getattr(real_view, 'offset_x', 0)
                    self.offset_y = getattr(real_view, 'offset_y', 0)
                    self.flip_y_axis = getattr(real_view, 'flip_y_axis', True)
                    self.scale_to_image = getattr(real_view, 'scale_to_image', True)
                    self.x_offset = getattr(real_view, 'x_offset', 0)
                    self.y_offset = getattr(real_view, 'y_offset', 0)
                    self.image_width = getattr(real_view, 'image_width', None)
                    self.image_height = getattr(real_view, 'image_height', None)
                    self._width = getattr(real_view, 'width', lambda: 800)()
                    self._height = getattr(real_view, 'height', lambda: 600)()
                    
                    # Log the copied parameters for debugging
                    logger.debug(f"MockCurveView created with parameters: zoom_factor={self.zoom_factor}, " + 
                                 f"offset=({self.offset_x}, {self.offset_y}), flip_y={self.flip_y_axis}, " +
                                 f"scale_to_image={self.scale_to_image}, dimensions={self._width}x{self._height}")
                else:
                    # Default values if no real view provided
                    self.zoom_factor = 1.0
                    self.offset_x = 0
                    self.offset_y = 0
                    self.flip_y_axis = True
                    self.scale_to_image = True
                    self.x_offset = 0
                    self.y_offset = 0
                    self.image_width = 1920  # Default image width
                    self.image_height = 1080  # Default image height
                    self._width = 800
                    self._height = 600
                    self.display_width = 1920  # Standard display width
                    self.display_height = 1080  # Standard display height
                
                self.background_image = None
            
            def width(self) -> int:
                return 800  # Default width
            
            def height(self) -> int:
                return 600  # Default height
            
            def update(self, arg__1=None) -> None:
                # QWidget.update() expects arg__1 parameter name in PySide6
                super().update()  # Call parent implementation
                
            def transform_point(self, x: float, y: float) -> tuple[float, float]:
                """Transform a data point to screen coordinates using stable transform."""
                from services.unified_transformation_service import UnifiedTransformationService
                # Use the real view's stable transform if available
                if self._real_view is not None:
                    # Use the stable transform flag to ensure consistent transformations
                    return UnifiedTransformationService.transform_point_to_widget(
                        self._real_view, x, y, use_stable_transform=True
                    )
                else:
                    # Fall back to using this mock view's transform
                    return UnifiedTransformationService.transform_point_to_widget(
                        self, x, y
                    )
        
        # Get the minimum and maximum coordinate values to properly setup the mock view
        min_x = min(point[1] for point in self.data) if self.data else 0
        max_x = max(point[1] for point in self.data) if self.data else 100
        min_y = min(point[2] for point in self.data) if self.data else 0
        max_y = max(point[2] for point in self.data) if self.data else 100
        data_width = max(1, max_x - min_x)
        data_height = max(1, max_y - min_y)
        
        # Create mock curve view with the real view to ensure consistent transformation
        mock_view = MockCurveView(self.data, real_view=real_view)
        
        # Calculate averages for each point with respect to screen coordinates
        # Use the stable transformation context to prevent drift
        try:
            # Create a reference set of points for tracking transformation stability
            reference_points = {}
            for idx in sorted_indices:
                if 0 <= idx < len(self.data):
                    reference_points[idx] = self.data[idx]
            
            # Use the transformation service with a properly tracked transformation context
            with UnifiedTransformationService.stable_transformation_context(mock_view) as transform:
                logger.info("Using stable transformation context for smoothing")
                
                # Log sample points before smoothing
                for sample_idx in sorted_indices[:2] + [sorted_indices[-1]] if len(sorted_indices) > 2 else sorted_indices:
                    if sample_idx in reference_points:
                        before_point = reference_points[sample_idx]
                        tx, ty = transform.apply(before_point[1], before_point[2])
                        logger.info(f"BEFORE - Point idx={sample_idx}: frame={before_point[0]}, data=({before_point[1]:.2f},{before_point[2]:.2f}), screen=({tx:.2f},{ty:.2f})")
                
                # Instead of calculating average in screen space, let's take a different approach
                # First, get the screen-space positions of all points
                screen_positions = {}
                for idx in sorted_indices:
                    if 0 <= idx < len(self.data):
                        point = self.data[idx]
                        # Transform data coordinates to screen coordinates
                        screen_x, screen_y = mock_view.transform_point(point[1], point[2])
                        screen_positions[idx] = (point[0], screen_x, screen_y)
                
                # Calculate average position in screen space
                if screen_positions:
                    # Calculate centroid in screen space
                    sum_screen_x = sum(float(screen_positions[idx][1]) for idx in screen_positions)
                    sum_screen_y = sum(float(screen_positions[idx][2]) for idx in screen_positions)
                    count = len(screen_positions)
                    avg_screen_x = sum_screen_x / count
                    avg_screen_y = sum_screen_y / count
                    
                    # Use a fixed smoothing radius in screen space
                    # This gives more consistent results regardless of zoom level
                    smooth_radius = 5.0  # pixels
                    
                    logger.info(f"Target screen space centroid: x={avg_screen_x:.2f}, y={avg_screen_y:.2f} from {count} points")
                    
                    # Instead of making all points identical, blend them toward the average
                    # This preserves the curve shape while reducing noise
                    for idx in sorted_indices:
                        if idx not in screen_positions:
                            continue
                            
                        point = self.data[idx]
                        frame_num = point[0]
                        screen_x, screen_y = screen_positions[idx][1], screen_positions[idx][2]
                        
                        # Calculate blend factor based on distance from average
                        dx = screen_x - avg_screen_x
                        dy = screen_y - avg_screen_y
                        distance = math.sqrt(dx*dx + dy*dy)
                        blend_factor = min(1.0, distance / smooth_radius) * 0.5
                        
                        # Blend current position with average position
                        new_screen_x = screen_x * blend_factor + avg_screen_x * (1.0 - blend_factor)
                        new_screen_y = screen_y * blend_factor + avg_screen_y * (1.0 - blend_factor)
                        
                        # Convert back to data coordinates
                        data_x, data_y = transform.apply_inverse(new_screen_x, new_screen_y)
                        
                        # Preserve status if available, otherwise mark as modified
                        if len(point) > 3 and isinstance(point[3], bool):
                            result[idx] = (frame_num, data_x, data_y, point[3])
                        else:
                            result[idx] = (frame_num, data_x, data_y, False)
                    
                    # Log sample points after smoothing to verify consistency
                    for sample_idx in sorted_indices[:2] + [sorted_indices[-1]] if len(sorted_indices) > 2 else sorted_indices:
                        if sample_idx in screen_positions and sample_idx < len(result):
                            after_point = result[sample_idx]
                            tx, ty = transform.apply(after_point[1], after_point[2])
                            logger.info(f"AFTER - Point idx={sample_idx}: frame={after_point[0]}, screen=({tx:.2f},{ty:.2f})")
            
            logger.info(f"Applied smoothing with blending to {len(sorted_indices)} points using stable transformation")
        
        except Exception as e:
            logger.error(f"Error during stable transformation smoothing: {e}")
            # Create a more sophisticated fallback method that maintains curve shape
            # while still reducing noise
            window_points = [self.data[idx] for idx in sorted_indices]
            if window_points:
                # Calculate centroid of points in data space
                sum_x = sum(float(p[1]) for p in window_points)
                sum_y = sum(float(p[2]) for p in window_points)
                count = len(window_points)
                avg_x = sum_x / count
                avg_y = sum_y / count
                
                logger.info(f"Fallback smoothing: centroid=({avg_x:.2f},{avg_y:.2f}) from {count} points")
                
                # Calculate average distance from centroid for scaling
                total_dist = sum(math.sqrt((p[1] - avg_x)**2 + (p[2] - avg_y)**2) for p in window_points)
                avg_dist = total_dist / max(1, count)
                smooth_radius = avg_dist * 0.3  # Use 30% of average distance as smoothing radius
                
                for idx in sorted_indices:
                    if idx >= len(self.data):
                        continue
                        
                    point = self.data[idx]
                    frame_num = point[0]
                    
                    # Calculate blend factor based on distance from average
                    dx = point[1] - avg_x
                    dy = point[2] - avg_y
                    distance = math.sqrt(dx*dx + dy*dy)
                    blend_factor = min(1.0, distance / max(0.001, smooth_radius)) * 0.7
                    
                    # Blend toward average position, but preserve more of original shape
                    new_x = point[1] * blend_factor + avg_x * (1.0 - blend_factor)
                    new_y = point[2] * blend_factor + avg_y * (1.0 - blend_factor)
                    
                    # Preserve status if available
                    if len(point) > 3 and isinstance(point[3], bool):
                        result[idx] = (frame_num, new_x, new_y, point[3])
                    else:
                        result[idx] = (frame_num, new_x, new_y, False)
                        
                logger.warning(f"Used fallback smoothing algorithm due to error")
        
        # Update the data with the smoothed values
        self.data = result
        logger.info(f"Smoothing complete, updated {len(sorted_indices)} points")


class AnalysisService:
    """
    Service for curve data analysis and transformations
    """

    def __init__(self, data: PointsList) -> None:
        """
        Initialize with curve data

        Args:
            data: List of points in format [(frame, x, y), ...]
        """
        self.data: PointsList = data

    def create_processor(self, data: PointsList) -> CurveProcessor:
        """
        Create a curve processor instance for the given data

        Args:
            data: Curve data to process

        Returns:
            An instance of a curve processor
        """
        # Return an instance of ConcreteCurveProcessor instead of self
        return ConcreteCurveProcessor(data)

    @classmethod
    def rotate_curve(cls, curve_data: List[Tuple[int, float, float]], angle_degrees: float = 0.0,
                     center_x: Optional[float] = None, center_y: Optional[float] = None) -> List[Tuple[int, float, float]]:
        """
        Rotate curve data around a center point.

        Args:
            curve_data: List of points in format [(frame, x, y), ...]
            angle_degrees: Rotation angle in degrees
            center_x: X coordinate of rotation center (None for centroid)
            center_y: Y coordinate of rotation center (None for centroid)

        Returns:
            List[Tuple[int, float, float]]: Rotated curve data
        """
        # Create a copy of the curve data
        result: List[Tuple[int, float, float]] = copy.deepcopy(curve_data)

        # Convert angle to radians
        angle_rad = math.radians(angle_degrees)

        # If no center provided, use centroid of selected points
        if center_x is None or center_y is None:
            sum_x = 0
            sum_y = 0
            count = 0

            for _, x, y in curve_data:
                sum_x += x
                sum_y += y
                count += 1

            if count > 0:
                center_x = sum_x / count if center_x is None else center_x
                center_y = sum_y / count if center_y is None else center_y
            else:
                # No valid points to rotate
                return result

        # Apply rotation to all points
        for i, (frame, x, y) in enumerate(curve_data):
            # Translate point to origin
            dx = x - center_x
            dy = y - center_y

            # Rotate point
            new_x = center_x + dx * math.cos(angle_rad) - dy * math.sin(angle_rad)
            new_y = center_y + dx * math.sin(angle_rad) + dy * math.cos(angle_rad)

            # Update point
            result[i] = (frame, new_x, new_y)

        return result

    def get_data(self) -> PointsList:
        """
        Get the current curve data.

        Returns:
            PointsList: Current curve data
        """
        return copy.deepcopy(self.data)

    def smooth_moving_average(self, indices: List[int], window_size: int, curve_view=None) -> None:
        """Apply moving average smoothing to the specified indices.

        Args:
            indices: List of indices to smooth
            window_size: Size of the smoothing window
            curve_view: Optional reference to the actual curve view for stable transformation
        """
        processor = self.create_processor(self.data)
        processor.smooth_moving_average(indices, window_size, curve_view)
        self.data = processor.get_data()

    def fill_gap(self, data: PointsList, start_frame: int, end_frame: int, method: str = 'linear') -> PointsList:
        """
        Fill a gap in the curve data using the specified method.

        Args:
            data: PointsList (list of tuples in format (frame, x, y) or (frame, x, y, bool))
            start_frame: First frame in the gap
            end_frame: Last frame in the gap
            method: Interpolation method ('linear' or 'cubic_spline')

        Returns:
            PointsList: List of interpolated points within the gap
        """
        logger.debug(f"Filling gap from frame {start_frame} to {end_frame} using {method} method")
        if method == 'linear':
            # Identify the boundary points that surround the gap
            start_point = next((pt for pt in data if pt[0] == start_frame), None)
            end_point = next((pt for pt in data if pt[0] == end_frame), None)

            # Fallbacks if the exact boundary frames are missing
            if start_point is None:
                # Latest point _before_ the gap (frame < start_frame)
                start_point = max((pt for pt in data if pt[0] < start_frame), key=lambda p: p[0], default=None)
            if end_point is None:
                # Earliest point _after_ the gap (frame > end_frame)
                end_point = min((pt for pt in data if pt[0] > end_frame), key=lambda p: p[0], default=None)

            # If we don't have valid boundary points we can't interpolate – return data unchanged
            if start_point is None or end_point is None:
                return data

            start_frame_num, start_x, start_y = start_point[:3]
            end_frame_num, end_x, end_y = end_point[:3]

            # Avoid division by zero (shouldn't happen if frames are distinct)
            if end_frame_num == start_frame_num:
                return data

            # Linear interpolation coefficients per-frame
            slope_x = (end_x - start_x) / (end_frame_num - start_frame_num)
            slope_y = (end_y - start_y) / (end_frame_num - start_frame_num)

            # Insert interpolated points strictly inside the gap (exclusive of boundaries)
            interpolated_points: PointsList = []
            for frame in range(start_frame_num + 1, end_frame_num):
                # Skip if point already exists
                if any(pt[0] == frame for pt in data):
                    continue
                x_val = start_x + slope_x * (frame - start_frame_num)
                y_val = start_y + slope_y * (frame - start_frame_num)
                interpolated_points.append((frame, x_val, y_val))

            data.extend(interpolated_points)

        elif method == 'cubic_spline':
            # Find the points before and after the gap
            prev_points = [point for point in data if point[0] < start_frame]
            next_points = [point for point in data if point[0] > end_frame]

            logger.debug(f"Found {len(prev_points)} points before gap and {len(next_points)} points after gap")

            if prev_points and next_points:
                # Combine the points before and after the gap
                points = prev_points + next_points

                # Sort the points by frame
                points.sort(key=lambda point: point[0])

                # For fallback method if cubic spline isn't available
                if not has_scipy:
                    logger.debug("SciPy not available, falling back to linear interpolation")
                    return self.fill_gap(data, start_frame, end_frame, method='linear')

                try:
                    # Try importing here to keep the import local to this method
                    from scipy.interpolate import CubicSpline  # type: ignore

                    # Separate the x, y coordinates
                    frames_list: List[int] = []
                    xs_list: List[float] = []
                    ys_list: List[float] = []

                    for frame, x, y in points:
                        frames_list.append(frame)
                        xs_list.append(x)
                        ys_list.append(y)

                    # Create a cubic spline interpolation
                    cs_x = CubicSpline(frames_list, xs_list)
                    cs_y = CubicSpline(frames_list, ys_list)

                    # Insert all interpolated points
                    interpolated_points: PointsList = []
                    for frame in range(start_frame, end_frame + 1):
                        # Convert numpy values to Python floats
                        x_interp = float(cs_x(frame))
                        y_interp = float(cs_y(frame))
                        interpolated_points.append((frame, x_interp, y_interp))

                    logger.debug(f"Generated {len(interpolated_points)} interpolated points using cubic spline")
                    return interpolated_points
                except (ImportError, ValueError, TypeError):
                    # Fall back to linear interpolation if there's any issue
                    return self.fill_gap(data, start_frame, end_frame, method='linear')
            else:
                # Fall back to linear interpolation if scipy not available
                return self.fill_gap(data, start_frame, end_frame, method='linear')

        return data

    def fill_gap_linear(self, start_frame: int, end_frame: int) -> None:
        """
        Fill a gap with linear interpolation between start_frame and end_frame.

        Args:
            start_frame: First frame of the gap
            end_frame: Last frame of the gap
        """
        self.data = self.fill_gap(self.data, start_frame, end_frame, method='linear')

    def fill_gap_spline(self, start_frame: int, end_frame: int) -> None:
        """
        Fill a gap with cubic spline interpolation between start_frame and end_frame.

        Args:
            start_frame: First frame of the gap
            end_frame: Last frame of the gap
        """
        self.data = self.fill_gap(self.data, start_frame, end_frame, method='cubic_spline')

    def normalize_velocity(self, target_velocity: float) -> None:
        """
        Normalize the velocity between consecutive points to the target value.

        Args:
            target_velocity: Target velocity in pixels per frame
        """
        if not self.data or len(self.data) < 2:
            return

        # Sort data by frame number to ensure proper normalization
        sorted_data = sorted(self.data, key=lambda p: p[0])
        result = [sorted_data[0]]  # Keep the first point unchanged

        for i in range(1, len(sorted_data)):
            prev_frame, prev_x, prev_y = result[-1][:3]  # Use the last adjusted point as reference
            curr_frame, curr_x, curr_y = sorted_data[i][:3]

            # Calculate direction vector from previous point to current point
            dx = curr_x - prev_x
            dy = curr_y - prev_y
            distance = math.sqrt(dx*dx + dy*dy)

            if distance > 0:
                # Normalize direction vector
                dx /= distance
                dy /= distance

                # Calculate new position based on target velocity
                frame_diff = curr_frame - prev_frame
                if frame_diff > 0:
                    # Adjust for multi-frame gaps
                    adjusted_velocity = target_velocity * frame_diff
                else:
                    adjusted_velocity = target_velocity

                # Set new position at exactly the right distance
                new_x = prev_x + dx * adjusted_velocity
                new_y = prev_y + dy * adjusted_velocity

                result.append((curr_frame, new_x, new_y))
            else:
                # If points are at the same location, keep as is
                result.append((curr_frame, curr_x, curr_y))

        self.data = result

    def detect_problems(self) -> Dict[int, Dict[str, str]]:
        """
        Detect potential problems in tracking data.

        Identifies issues such as:
        - Jitter (very small movements)
        - Sudden jumps (large movements between consecutive frames)
        - Gaps in tracking (missing frames)

        Returns:
            Dict[int, Dict[str, str]]: Dictionary of detected problems with frame numbers as keys
        """
        # Use instance data
        if not self.data or len(self.data) < 2:
            return {}

        problems: Dict[int, Dict[str, str]] = {}

        # Parameters for problem detection
        jitter_threshold = 0.5  # pixels - movements smaller than this might be jitter
        jump_threshold = 30.0   # pixels - movements larger than this might be sudden jumps
        gap_threshold = 1       # frames - gaps larger than this are detected

        # Sort data by frame number to ensure proper analysis
        sorted_data = sorted(self.data, key=lambda p: p[0])

        # Analyze movements between consecutive points
        for i in range(1, len(sorted_data)):
            prev_frame, prev_x, prev_y = sorted_data[i-1][:3]
            curr_frame, curr_x, curr_y = sorted_data[i][:3]

            # Check for gaps in frame numbers
            frame_diff = curr_frame - prev_frame
            if frame_diff > gap_threshold + 1:
                problems[prev_frame] = {
                    'type': 'gap',
                    'description': f'Gap of {frame_diff-1} frames after frame {prev_frame}'
                }

            # Only check motion issues for consecutive or near-consecutive frames
            if frame_diff <= gap_threshold + 1:
                # Calculate distance moved
                dx = curr_x - prev_x
                dy = curr_y - prev_y
                distance = math.sqrt(dx*dx + dy*dy)

                # Check for jitter
                if distance < jitter_threshold:
                    problems[curr_frame] = {
                        'type': 'jitter',
                        'description': f'Minimal movement ({distance:.2f} px) at frame {curr_frame}'
                    }

                # Check for sudden jumps
                elif distance > jump_threshold:
                    problems[curr_frame] = {
                        'type': 'jump',
                        'description': f'Sudden jump ({distance:.2f} px) at frame {curr_frame}'
                    }

        return problems

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

    def get_data(self) -> List[Tuple[int, float, float]]:
        """
        Get the current curve data.

        Returns:
            List[Tuple[int, float, float]]: Current curve data
        """
        return copy.deepcopy(self.data)

    def smooth_moving_average(self, indices: List[int], window_size: int) -> None:
        """
        Apply moving average smoothing to the specified indices.

        Args:
            indices: List of indices to smooth
            window_size: Size of the smoothing window
        """
        processor = self.create_processor(self.data)
        processor.smooth_moving_average(indices, window_size)
        self.data = processor.get_data()

    def smooth_gaussian(self, indices: List[int], window_size: int, sigma: float) -> None:
        """
        Apply Gaussian smoothing to the specified indices.

        Args:
            indices: List of indices to smooth
            window_size: Size of the smoothing window
            sigma: Standard deviation for Gaussian kernel
        """
        processor = self.create_processor(self.data)
        processor.smooth_gaussian(indices, window_size, sigma)
        self.data = processor.get_data()

    def smooth_savitzky_golay(self, indices: List[int], window_size: int) -> None:
        """
        Apply Savitzky-Golay smoothing to the specified indices.

        Args:
            indices: List of indices to smooth
            window_size: Size of the smoothing window
        """
        processor = self.create_processor(self.data)
        processor.smooth_savitzky_golay(indices, window_size)
        self.data = processor.get_data()

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
            prev_frame, prev_x, prev_y = result[-1]  # Use the last adjusted point as reference
            curr_frame, curr_x, curr_y = sorted_data[i]

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
            dict: Dictionary of detected problems with frame numbers as keys
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
            prev_frame, prev_x, prev_y = sorted_data[i-1]
            curr_frame, curr_x, curr_y = sorted_data[i]

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

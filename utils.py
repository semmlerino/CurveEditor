#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import math
import copy
import re  # Added import for regex support


def get_image_files(directory):
    """Get all image files in a directory."""
    if not os.path.isdir(directory):
        return []

    # Supported image extensions
    image_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tif', '.tiff']

    # Filter files by extension
    image_files = []
    for filename in os.listdir(directory):
        ext = os.path.splitext(filename)[1].lower()
        if ext in image_extensions:
            image_files.append(filename)

    # Sort alphabetically
    image_files.sort()

    return image_files


def extract_frame_number(filename, fallback=None):
    """
    Try to extract frame number from filename using multiple methods.

    This is a consolidated implementation that combines specific pattern matching
    and regular expressions to handle various naming conventions.

    Args:
        filename: The filename to extract frame number from
        fallback: Value to return if extraction fails (default: None)

    Returns:
        int: Extracted frame number, or fallback value if extraction fails
    """
    try:
        # Ensure we're working with the basename, not a full path
        base = os.path.basename(filename)

        # Method 1: Try format name.####.ext
        parts = base.split('.')
        if len(parts) >= 2 and parts[-2].isdigit():
            return int(parts[-2])

        # Method 2: Try format name_####.ext
        name_parts = parts[0].split('_')
        if name_parts[-1].isdigit():
            return int(name_parts[-1])

        # Method 3: Use regex to find any sequence of digits
        match = re.search(r'(\d+)', base)
        if match:
            return int(match.group(1))
    except Exception:
        # Handle any exception during extraction
        pass

    # Could not extract frame number
    return fallback


def map_frames_to_images(filenames):
    """Map frame numbers to image filenames."""
    frame_map = {}

    for i, filename in enumerate(filenames):
        # Try to extract frame number
        frame = extract_frame_number(filename)

        # If extraction failed, use sequential index
        if frame is None:
            frame = i

        frame_map[frame] = filename

    return frame_map


def find_closest_image(frame, frame_map):
    """Find the image closest to the given frame."""
    if not frame_map:
        return None

    closest_frame = None
    min_diff = float('inf')

    for f in frame_map.keys():
        diff = abs(f - frame)
        if diff < min_diff:
            min_diff = diff
            closest_frame = f

    return frame_map.get(closest_frame)


def load_3de_track(file_path):
    """Load 3DE track data from a file."""
    if not os.path.isfile(file_path):
        return None, None, None, []

    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()

        if len(lines) < 4:
            return None, None, None, []

        # Parse header
        num_points = int(lines[0].strip())

        line_idx = 1
        # Point name
        point_name = lines[line_idx].strip()
        line_idx += 1

        # Point color
        point_color = int(lines[line_idx].strip())
        line_idx += 1

        # Number of frames
        num_frames = int(lines[line_idx].strip())
        line_idx += 1

        # Read points
        curve_data = []

        for i in range(num_frames):
            if line_idx >= len(lines):
                break

            parts = lines[line_idx].strip().split()
            if len(parts) >= 3:
                frame = int(parts[0])
                x = float(parts[1])
                y = float(parts[2])
                curve_data.append((frame, x, y))

            line_idx += 1

        return point_name, point_color, num_frames, curve_data
    except Exception as e:
        print(f"Error loading track: {str(e)}")
        return None, None, None, []


def save_3de_track(file_path, point_name, point_color, curve_data):
    """Save 3DE track data to a file."""
    try:
        with open(file_path, 'w') as f:
            # Write header
            f.write("1\n")  # Number of points
            f.write(f"{point_name}\n")
            f.write(f"{point_color}\n")
            f.write(f"{len(curve_data)}\n")

            # Write points
            for frame, x, y in sorted(curve_data, key=lambda p: p[0]):
                f.write(f"{frame} {x:.15f} {y:.15f}\n")

        return True
    except Exception as e:
        print(f"Error saving track: {str(e)}")
        return False


def estimate_image_dimensions(curve_data):
    """Estimate appropriate image dimensions from curve data."""
    if not curve_data:
        return 1920, 1080  # Default HD dimensions

    # Find max coordinates
    max_x = max(x for _, x, _ in curve_data)
    max_y = max(y for _, _, y in curve_data)

    # Add some margin
    width = max(1920, int(max_x * 1.1))
    height = max(1080, int(max_y * 1.1))

    return width, height

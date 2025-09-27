# 3DE4.script.name: Change tracking direction to Backwards
# 3DE4.script.version: v1.1
# 3DE4.script.gui: Main Window::Matchmove::Gabriel
# 3DE4.script.comment: Set tracking direction to backward for multiple points

import os
from datetime import datetime

import tde4

# Set up logging
LOG_FILE = "/home/gabriel-ha/3DElog/tracking_direction.log"


def log_message(msg):
    """Write message to both console and log file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msg = f"[{timestamp}] {msg}"
    print(full_msg)

    # Ensure directory exists
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    # Append to log file
    with open(LOG_FILE, "a") as f:
        f.write(full_msg + "\n")


def set_tracking_backward():
    log_message("Starting to set tracking direction to backward...")

    # Get current point group and camera
    pg = tde4.getCurrentPGroup()
    cam = tde4.getCurrentCamera()

    if not pg or not cam:
        log_message("Error: No point group or camera selected")
        tde4.postQuestionRequester("Error", "No point group or camera selected", "OK")
        return

    # Get selected points
    points = tde4.getPointList(pg, 1)  # 1 means only selected points

    if not points:
        log_message("Error: No points selected")
        tde4.postQuestionRequester("Error", "No points selected", "OK")
        return

    # Get number of frames
    frames = tde4.getCameraNoFrames(cam)
    if not frames:
        log_message("Error: Camera has no frames")
        tde4.postQuestionRequester("Error", "Camera has no frames", "OK")
        return

    # Push to undo stack before making changes
    tde4.pushPointsToUndoStack()

    processed_count = 0

    for point in points:
        point_name = tde4.getPointName(pg, point)
        log_message(f"Processing point: {point_name}")

        # Get 2D tracking data for all frames
        tracking_data = tde4.getPointPosition2DBlock(pg, point, cam, 1, frames)

        # Process all keyframes
        end_keyframes_to_normal = []  # End keyframes to convert to normal
        normal_keyframes_to_end = []  # Normal keyframes to convert to end

        for frame in range(1, frames + 1):
            status = tde4.getPointStatus2D(pg, point, cam, frame)

            # Skip non-keyframes
            if status not in ["POINT_KEYFRAME", "POINT_KEYFRAME_END"]:
                continue

            curr_pos = tracking_data[frame - 1]
            if curr_pos == [-1, -1]:  # Skip invalid positions
                continue

            prev_frame = max(1, frame - 1)
            next_frame = min(frames, frame + 1)
            prev_pos = tracking_data[prev_frame - 1]
            next_pos = tracking_data[next_frame - 1]

            # Process end keyframes - Rule 1
            if status == "POINT_KEYFRAME_END":
                if prev_pos != [-1, -1]:
                    end_keyframes_to_normal.append(frame)
                    log_message(f"Frame {frame}: End keyframe will be converted to normal keyframe (Rule 1)")

            # Process normal keyframes - Rule 2
            elif status == "POINT_KEYFRAME":
                if next_pos != [-1, -1] and prev_pos == [-1, -1]:
                    normal_keyframes_to_end.append(frame)
                    log_message(f"Frame {frame}: Normal keyframe will be converted to end keyframe (Rule 2)")

        # Change tracking direction
        current_direction = tde4.getPointTrackingDirection(pg, point)
        log_message(f"Current tracking direction: {current_direction}")
        log_message("Setting tracking direction to: TRACKING_BW")
        tde4.setPointTrackingDirection(pg, point, "TRACKING_BW")

        # Update keyframe statuses
        for frame in end_keyframes_to_normal:
            tde4.setPointStatus2D(pg, point, cam, frame, "POINT_KEYFRAME")
            log_message(f"Frame {frame}: Converted end keyframe to normal keyframe")

        for frame in normal_keyframes_to_end:
            tde4.setPointStatus2D(pg, point, cam, frame, "POINT_KEYFRAME_END")
            log_message(f"Frame {frame}: Converted normal keyframe to end keyframe")

        processed_count += 1

    log_message(f"Set tracking direction to backward for {processed_count} points")


# Execute main function
set_tracking_backward()

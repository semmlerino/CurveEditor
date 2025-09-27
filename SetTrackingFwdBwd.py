# 3DE4.script.name:    TrackDirFwdBwd
# 3DE4.script.version: v1.1
# 3DE4.script.gui:    Main Window::Matchmove::Gabriel::TrackingDir
# 3DE4.script.comment: Sets tracking direction to Forward/Backward while preserving keyframe structure

import os
from datetime import datetime

import tde4

# Set up logging
LOG_FILE = "/home/gabriel-ha/3DElog/track_dir_fwdbwd.log"


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


def update_keyframes_for_point(pg, point, cam, nframes):
    """Update keyframe status for a point's tracking curve"""
    point_name = tde4.getPointName(pg, point)
    log_message(f"Processing keyframes for point: {point_name}")

    # Get the current tracking direction
    current_direction = tde4.getPointTrackingDirection(pg, point)
    log_message(f"Current tracking direction: {current_direction}")

    # Get the point's current tracking curve
    curve = tde4.getPointPosition2DBlock(pg, point, cam, 1, nframes)

    # First pass: Store all keyframes and determine if adjustments are needed
    keyframe_data = []
    for frame in range(1, nframes + 1):
        status = tde4.getPointStatus2D(pg, point, cam, frame)
        if status in ["POINT_KEYFRAME", "POINT_KEYFRAME_END"]:
            # Check for special cases when transitioning from backward tracking
            if current_direction == "TRACKING_BW":
                next_frame_valid = False
                if frame < nframes:
                    next_frame_valid = curve[frame] != [-1, -1]

                # Case 1: POINT_KEYFRAME with no valid position in next frame should become an end keyframe
                if status == "POINT_KEYFRAME" and not next_frame_valid:
                    log_message(
                        f"Frame {frame}: Regular keyframe with no valid next position - marking for conversion to end keyframe"
                    )
                    status = "POINT_KEYFRAME_END"

                # Case 2: POINT_KEYFRAME_END with valid position in next frame should become a regular keyframe
                elif status == "POINT_KEYFRAME_END" and next_frame_valid:
                    log_message(
                        f"Frame {frame}: End keyframe with valid next position - marking for conversion to regular keyframe"
                    )
                    status = "POINT_KEYFRAME"

            keyframe_data.append((frame, status))
            log_message(f"Frame {frame}: Storing as {status}")

    if not keyframe_data:
        log_message("No keyframes found for point")
        return

    # Only change the tracking direction if it's not already FW_BW
    if current_direction != "TRACKING_FW_BW":
        log_message(f"Setting tracking direction to forward/backward for point: {point_name}")
        tde4.setPointTrackingDirection(pg, point, "TRACKING_FW_BW")
    else:
        log_message("Point already has forward/backward tracking direction")

    # Second pass: Restore keyframe statuses with the adjusted types
    for frame, status in keyframe_data:
        # Only restore if position data exists at this frame
        if curve[frame - 1] != [-1, -1]:
            tde4.setPointStatus2D(pg, point, cam, frame, status)
            log_message(f"Restored {status} at frame {frame}")
        else:
            log_message(f"Warning: Cannot restore keyframe at frame {frame} - no valid position data")

    # Verify keyframes were restored correctly
    verification_count = 0
    for frame, expected_status in keyframe_data:
        if curve[frame - 1] != [-1, -1]:
            current_status = tde4.getPointStatus2D(pg, point, cam, frame)
            if current_status == expected_status:
                verification_count += 1
            else:
                log_message(
                    f"Warning: Status mismatch at frame {frame} - expected {expected_status}, got {current_status}"
                )

    log_message(f"Successfully restored {verification_count} of {len(keyframe_data)} keyframes")


def main():
    log_message("Starting TrackDirFwdBwd script v1.1")

    # Get current point group
    pg = tde4.getCurrentPGroup()
    if not pg:
        log_message("Error: No point group selected")
        return

    # Get selected points
    points = tde4.getPointList(pg, 1)
    if not points:
        log_message("Error: No points selected")
        return

    # Get current camera
    cam = tde4.getCurrentCamera()
    if not cam:
        log_message("Error: No camera selected")
        return

    nframes = tde4.getCameraNoFrames(cam)
    log_message(f"Found {len(points)} selected points")

    # Push to undo stack before making changes
    tde4.pushPointsToUndoStack()

    # Process each selected point
    for point in points:
        update_keyframes_for_point(pg, point, cam, nframes)

    log_message("Script completed successfully")


# Run main function
main()

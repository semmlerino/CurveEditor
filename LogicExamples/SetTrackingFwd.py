# 3DE4.script.name:    TrackDirFwd
# 3DE4.script.version: v1.9
# 3DE4.script.gui:    Main Window::Matchmove::Gabriel::TrackingDir
# 3DE4.script.comment: Sets tracking direction to Forward and updates keyframe types. Preserves keyframes with subsequent tracked frames.

import os
from datetime import datetime

import tde4

LOG_FILE = "/home/gabriel-ha/3DElog/track_dir_fwd.log"


def log_message(msgs):
    """Logs a list of messages with timestamps to console and file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    full_msgs = [f"[{timestamp}] {msg}" for msg in msgs]
    print("\n".join(full_msgs))

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, "a") as f:
        f.write("\n".join(full_msgs) + "\n")


def get_position(pg, point, cam, frame):
    """Get position for a frame, returns [-1, -1] if invalid."""
    if frame < 1:
        return [-1, -1]
    return tde4.getPointPosition2DBlock(pg, point, cam, frame, frame)[0]


def update_keyframes(pg, point, cam, nframes, messages):
    """Updates keyframes for a single point."""
    point_name = tde4.getPointName(pg, point)
    messages.append(f"Processing point: {point_name}")

    current_dir = tde4.getPointTrackingDirection(pg, point)
    messages.append(f"Current tracking direction: {current_dir}")
    messages.append("Setting tracking direction to forward")
    tde4.setPointTrackingDirection(pg, point, "TRACKING_FW")

    for frame in range(1, nframes + 1):
        current_status = tde4.getPointStatus2D(pg, point, cam, frame)
        current_pos = get_position(pg, point, cam, frame)
        prev_pos = get_position(pg, point, cam, frame - 1)
        next_pos = get_position(pg, point, cam, frame + 1) if frame < nframes else [-1, -1]

        if current_status in {"POINT_KEYFRAME", "POINT_KEYFRAME_END"}:
            messages.append(f"Frame {frame} - Current status: {current_status}, Position: {current_pos}")
            messages.append(f"Frame {frame} - Previous frame position: {prev_pos}")
            messages.append(f"Frame {frame} - Next frame position: {next_pos}")

            # If there's valid tracking data after this frame, it should be a regular keyframe
            if next_pos != [-1, -1]:
                if current_status == "POINT_KEYFRAME_END":
                    tde4.setPointStatus2D(pg, point, cam, frame, "POINT_KEYFRAME")
                    messages.append(f"Frame {frame} converted to POINT_KEYFRAME - has valid tracking after")
                else:
                    messages.append(f"Frame {frame} remains POINT_KEYFRAME - has valid tracking after")
            # If there's no valid tracking data after this frame, it should be an end keyframe
            else:
                if current_status == "POINT_KEYFRAME":
                    tde4.setPointStatus2D(pg, point, cam, frame, "POINT_KEYFRAME_END")
                    messages.append(f"Frame {frame} converted to POINT_KEYFRAME_END - no valid tracking after")
                else:
                    messages.append(f"Frame {frame} remains POINT_KEYFRAME_END - no valid tracking after")


def main():
    """Main function to set tracking direction and update keyframes."""
    messages = ["Starting tracking direction change process..."]

    pg = tde4.getCurrentPGroup()
    if not pg:
        messages.append("Error: No point group selected")
        log_message(messages)
        return

    points = tde4.getPointList(pg, 1)
    if not points:
        messages.append("Error: No points selected")
        log_message(messages)
        return

    cam = tde4.getCurrentCamera()
    if not cam:
        messages.append("Error: No camera selected")
        log_message(messages)
        return

    nframes = tde4.getCameraNoFrames(cam)
    if nframes < 1:
        messages.append("Error: Invalid frame range")
        log_message(messages)
        return

    tde4.pushPointsToUndoStack()

    for point in points:
        update_keyframes(pg, point, cam, nframes, messages)

    messages.append("Process completed")
    log_message(messages)


if __name__ == "__main__":
    main()

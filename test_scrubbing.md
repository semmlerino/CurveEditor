# Timeline Scrubbing Test Instructions

## Feature Added
Mouse scrubbing functionality has been added to the timeline widget.

## How to Test

1. **Click and Hold**: Click on any frame tab in the timeline and hold the mouse button down
2. **Drag**: While holding the button, drag left or right across the timeline
3. **Observe**: The current frame should update in real-time as you drag
4. **Release**: Release the mouse button to stop scrubbing

## Expected Behavior
- Clicking on a frame tab should immediately jump to that frame
- Holding and dragging should smoothly update the frame as you move the mouse
- The frame indicator should follow your mouse position
- Releasing the mouse button should leave you at the last frame you dragged to

## Implementation Details
- Added `mousePressEvent` to start scrubbing
- Added `mouseMoveEvent` to update frame while dragging
- Added `mouseReleaseEvent` to stop scrubbing
- Added `_get_frame_from_position` to calculate frame from mouse X coordinate
- Enabled mouse tracking for smooth updates

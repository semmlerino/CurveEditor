# Oscillating Timeline Playback - System Design

## Overview
Implement spacebar-triggered oscillating timeline playback at configurable FPS (default 12fps). The timeline will bounce back and forth between frame boundaries continuously.

## Architecture Components

### 1. Playback State Management

```python
from enum import Enum, auto

class PlaybackMode(Enum):
    STOPPED = auto()
    PLAYING_FORWARD = auto()
    PLAYING_BACKWARD = auto()

@dataclass
class PlaybackState:
    mode: PlaybackMode = PlaybackMode.STOPPED
    fps: int = 12
    current_frame: int = 1
    min_frame: int = 1
    max_frame: int = 100
    loop_boundaries: bool = True  # True for oscillation, False for loop-to-start
```

### 2. Core Playback Controller

**Location**: `ui/main_window.py` (extend existing methods)

```python
class MainWindow:
    def __init__(self):
        # Fix broken initialization
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._on_playback_timer)

        # Playback state
        self.playback_state = PlaybackState()

    def _toggle_oscillating_playback(self) -> None:
        """Toggle oscillating playbook on spacebar."""
        if self.playback_state.mode == PlaybackMode.STOPPED:
            self._start_oscillating_playback()
        else:
            self._stop_oscillating_playback()

    def _start_oscillating_playback(self) -> None:
        """Start oscillating playback."""
        # Update frame boundaries from data
        self._update_playback_bounds()

        # Set FPS-based timer interval
        fps = self.fps_spinbox.value() if self.fps_spinbox else 12
        interval = int(1000 / fps)  # Convert to milliseconds

        # Start forward playback
        self.playback_state.mode = PlaybackMode.PLAYING_FORWARD
        self.playback_timer.start(interval)

    def _stop_oscillating_playback(self) -> None:
        """Stop oscillating playback."""
        self.playback_timer.stop()
        self.playback_state.mode = PlaybackMode.STOPPED
```

### 3. Oscillation Logic

```python
def _on_playback_timer(self) -> None:
    """Handle oscillating playback timer tick."""
    current = self.playback_state.current_frame

    if self.playback_state.mode == PlaybackMode.PLAYING_FORWARD:
        # Move forward
        if current >= self.playback_state.max_frame:
            # Hit upper boundary - reverse direction
            self.playback_state.mode = PlaybackMode.PLAYING_BACKWARD
            next_frame = current - 1
        else:
            next_frame = current + 1

    elif self.playback_state.mode == PlaybackMode.PLAYING_BACKWARD:
        # Move backward
        if current <= self.playback_state.min_frame:
            # Hit lower boundary - reverse direction
            self.playback_state.mode = PlaybackMode.PLAYING_FORWARD
            next_frame = current + 1
        else:
            next_frame = current - 1

    # Update frame and UI
    self._set_current_frame(next_frame)
```

### 4. Frame Bounds Detection

```python
def _update_playback_bounds(self) -> None:
    """Update playback bounds based on actual data."""
    data_service = get_data_service()

    if hasattr(self, 'curve_view') and self.curve_view.curve_data:
        bounds = data_service.get_data_bounds(self.curve_view.curve_data)
        self.playback_state.min_frame = max(1, bounds.get('min_frame', 1))
        self.playback_state.max_frame = bounds.get('max_frame', 100)
    else:
        # Default bounds
        self.playback_state.min_frame = 1
        self.playback_state.max_frame = 100

    # Ensure current frame is within bounds
    current = self._get_current_frame()
    if current < self.playback_state.min_frame:
        self._set_current_frame(self.playback_state.min_frame)
    elif current > self.playback_state.max_frame:
        self._set_current_frame(self.playback_state.max_frame)
```

### 5. Keyboard Integration

**Location**: `ui/keyboard_shortcuts.py`

```python
def _setup_frame_shortcuts(self) -> None:
    """Set up frame navigation shortcuts."""
    # Existing shortcuts...
    self.register_shortcut("oscillate_playback", "Space", self._on_oscillate_playback)

def _on_oscillate_playback(self) -> None:
    """Handle oscillating playback toggle (spacebar)."""
    self.shortcut_activated.emit("oscillate_playback")
```

**Location**: `ui/main_window.py`

```python
def _setup_shortcuts(self) -> None:
    """Setup keyboard shortcuts."""
    # Connect oscillation shortcut
    self.shortcut_manager.shortcut_activated.connect(self._handle_shortcut)

def _handle_shortcut(self, shortcut_name: str) -> None:
    """Handle shortcut activation."""
    if shortcut_name == "oscillate_playback":
        self._toggle_oscillating_playback()
    # ... other shortcuts
```

### 6. Timeline UI Integration

```python
def _set_current_frame(self, frame: int) -> None:
    """Set current frame with UI updates."""
    # Update internal state
    self.playback_state.current_frame = frame

    # Update spinbox
    if self.frame_spinbox:
        self.frame_spinbox.setValue(frame)

    # Update timeline widget
    if hasattr(self, 'timeline_tabs'):
        self.timeline_tabs.set_current_frame(frame)

    # Update curve view if needed
    if hasattr(self, 'curve_view'):
        self.curve_view.current_image_idx = frame - 1  # Convert to 0-based index
        self.curve_view.update()
```

### 7. FPS Configuration

**UI Integration** (in `ui_components.py`):
- Use existing `fps_spinbox` for configuration
- Default value: 12 FPS
- Range: 1-60 FPS

```python
def _setup_fps_control(self) -> None:
    """Setup FPS control."""
    if self.fps_spinbox:
        self.fps_spinbox.setMinimum(1)
        self.fps_spinbox.setMaximum(60)
        self.fps_spinbox.setValue(12)  # Default 12fps
        self.fps_spinbox.valueChanged.connect(self._on_fps_changed)

def _on_fps_changed(self, fps: int) -> None:
    """Handle FPS change during playback."""
    self.playback_state.fps = fps

    # Update timer interval if playing
    if self.playback_state.mode != PlaybackMode.STOPPED:
        interval = int(1000 / fps)
        self.playback_timer.setInterval(interval)
```

## Implementation Order

1. **Fix broken playback timer initialization** (critical)
2. **Add PlaybackState and PlaybackMode classes**
3. **Implement basic toggle functionality** (spacebar to start/stop)
4. **Add oscillation logic** (forward/backward bouncing)
5. **Integrate timeline UI updates**
6. **Add FPS configuration**
7. **Add frame bounds detection**
8. **Test and polish**

## User Experience

- **Spacebar**: Toggle oscillating playback on/off
- **Visual Feedback**: Timeline tabs highlight current frame during playback
- **Smooth Animation**: Configurable FPS for different animation speeds
- **Boundary Bouncing**: Seamless direction reversal at frame boundaries
- **Persistent Settings**: FPS setting remembered between sessions

## Edge Cases Handled

- **Empty Data**: Graceful handling when no curve data is loaded
- **Single Frame**: Playback stops if only one frame exists
- **Frame Changes During Playback**: Bounds recalculated dynamically
- **Timer Precision**: Millisecond-accurate timing for smooth playback
- **Resource Cleanup**: Proper timer cleanup on window close

## Performance Considerations

- **Efficient Frame Updates**: Minimal UI updates per frame
- **Smart Bounds Calculation**: Only recalculate bounds when data changes
- **Timer Management**: Proper start/stop to avoid resource leaks
- **Responsive UI**: Non-blocking frame updates

This design leverages existing CurveEditor infrastructure while adding robust oscillating playback functionality.

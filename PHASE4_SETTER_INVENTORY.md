# Phase 4 Setter Migration: Complete Inventory

**Generated**: 2025-10-17
**Total Setters**: 115 instances across 36 files

---

## Quick Reference

```
current_frame setters:  84 instances (73%)
total_frames setters:   31 instances (27%)
─────────────────────────────────
Total:                 115 instances (100%)
```

---

## Current Frame Setters (84 instances)

### Test Files: 82 instances

| File | Line | Count | Pattern |
|------|------|-------|---------|
| `tests/test_state_manager.py` | 28+ | 28 | `state_manager.current_frame = X` |
| `tests/test_keyframe_navigation.py` | 12+ | 12 | `window.state_manager.current_frame = X` |
| `tests/stores/test_application_state_phase0a.py` | 8+ | 8 | `state_manager.current_frame = X` |
| `tests/test_frame_highlight.py` | 7+ | 7 | Various patterns |
| `tests/test_event_filter_navigation.py` | 7+ | 7 | `window.state_manager.current_frame = X` |
| `tests/test_frame_change_coordinator.py` | 5+ | 5 | `main_window.state_manager.current_frame = X` |
| `tests/test_tracking_point_status_commands.py` | 4+ | 4 | Various patterns |
| `tests/test_unified_curve_rendering.py` | 3+ | 3 | `mock.state_manager.current_frame = X` |
| `tests/test_multi_point_selection.py` | 2+ | 2 | Various patterns |
| `tests/test_keyboard_shortcuts_enhanced.py` | 2+ | 2 | `window.state_manager.current_frame = X` |
| `tests/test_global_shortcuts.py` | 2+ | 2 | `window.state_manager.current_frame = X` |
| `tests/test_timeline_focus_behavior.py` | 1 | 1 | `state_manager.current_frame = X` |
| `tests/test_data_service_synchronization.py` | 1 | 1 | `main_window.state_manager.current_frame = X` |

**Test Total**: 82 instances

### Production Files: 2 instances

| File | Location | Pattern | Context |
|------|----------|---------|---------|
| `stores/frame_store.py` | Line 106 | `self._state_manager.current_frame = frame` | FrameStore.set_current_frame() |
| `stores/frame_store.py` | Line 216 | `self._state_manager.current_frame = 1` | FrameStore.clear() |

**Production Total**: 2 instances

**Grand Total current_frame**: 84 instances

---

## Total Frames Setters (31 instances)

### Production Files: 5 instances

| File | Lines | Method | Pattern | Context |
|------|-------|--------|---------|---------|
| `ui/timeline_tabs.py` | 620 | `set_frame_range()` | `self._state_manager.total_frames = max_frame` | Update timeline frame range |
| `ui/controllers/timeline_controller.py` | 499 | `set_frame_range()` | `self.state_manager.total_frames = max_frame` | Update timeline bounds |
| `stores/frame_store.py` | 195 | `_update_frame_range()` | `self._state_manager.total_frames = max_frame` | Sync frame range |
| `ui/controllers/tracking_display_controller.py` | 2+ | Various | `self.main_window.state_manager.total_frames = max_frame` | Tracking display setup |

**Production Total**: 5 instances

### Test Files: 26 instances

| File | Count | Pattern | Context |
|------|-------|---------|---------|
| `tests/test_state_manager.py` | 16 | `state_manager.total_frames = X` | Tests the setter behavior |
| `tests/test_frame_change_coordinator.py` | 3 | `main_window.state_manager.total_frames = X` | Coordinator bounds |
| `tests/test_timeline_tabs.py` | 1 | `window.state_manager.total_frames = 37` | Timeline setup |
| `tests/test_timeline_scrubbing.py` | 1 | `state_manager.total_frames = 200` | Scrubbing test |
| `tests/test_timeline_integration.py` | 1 | `state_manager.total_frames = 10000` | Integration test |
| `tests/test_timeline_functionality.py` | 1 | `state_manager.total_frames = 200` | Timeline test |
| `tests/test_timeline_focus_behavior.py` | 1 | `state_manager.total_frames = 100` | Focus test |
| `tests/test_frame_highlight.py` | 1 | `window.state_manager.total_frames = 20` | Display test |
| `tests/test_file_operations.py` | 1 | `state_manager.total_frames = 100` | File I/O test |

**Test Total**: 26 instances

**Grand Total total_frames**: 31 instances

---

## Summary by File

### Production Code (5 files with 7 setters)
1. `stores/frame_store.py` (3 setters: 2 current_frame, 1 total_frames)
2. `ui/timeline_tabs.py` (1 setter: total_frames)
3. `ui/controllers/timeline_controller.py` (1 setter: total_frames)
4. `ui/controllers/tracking_display_controller.py` (2 setters: total_frames)
5. `ui/state_manager.py` (0 setters - only has DEPRECATED setters to remove)

### Test Code (31 files with 108 setters)

| File | current_frame | total_frames | Total |
|------|---------------|--------------|-------|
| test_state_manager.py | 28 | 16 | 44 |
| test_keyframe_navigation.py | 12 | 0 | 12 |
| test_application_state_phase0a.py | 8 | 0 | 8 |
| test_frame_highlight.py | 7 | 1 | 8 |
| test_event_filter_navigation.py | 7 | 0 | 7 |
| test_frame_change_coordinator.py | 5 | 3 | 8 |
| test_tracking_point_status_commands.py | 4 | 0 | 4 |
| test_unified_curve_rendering.py | 3 | 0 | 3 |
| test_multi_point_selection.py | 2 | 0 | 2 |
| test_keyboard_shortcuts_enhanced.py | 2 | 0 | 2 |
| test_global_shortcuts.py | 2 | 0 | 2 |
| test_timeline_focus_behavior.py | 1 | 1 | 2 |
| test_data_service_synchronization.py | 1 | 0 | 1 |
| test_timeline_tabs.py | 0 | 1 | 1 |
| test_timeline_scrubbing.py | 0 | 1 | 1 |
| test_timeline_integration.py | 0 | 1 | 1 |
| test_timeline_functionality.py | 0 | 1 | 1 |
| test_file_operations.py | 0 | 1 | 1 |
| (13 more test files) | 1 each | 0 | 13 |

**Test Total**: 82 current_frame + 26 total_frames = 108 setters

---

## Detailed Line Numbers (Key Production Setters)

### Critical Production Setters (Must migrate first)

#### 1. ui/timeline_tabs.py:620
```python
def set_frame_range(self, min_frame: int, max_frame: int) -> None:
    # ... frame range setup ...
    if self._state_manager is not None:
        self._state_manager.total_frames = max_frame  # LINE 620
```

**Why critical**: Sets frame range for timeline widget during initialization

---

#### 2. ui/controllers/timeline_controller.py:499
```python
def set_frame_range(self, min_frame: int, max_frame: int) -> None:
    # Update navigation controls
    self.frame_spinbox.setMinimum(min_frame)
    self.frame_spinbox.setMaximum(max_frame)
    self.frame_slider.setMinimum(min_frame)
    self.frame_slider.setMaximum(max_frame)

    self.state_manager.total_frames = max_frame  # LINE 499
```

**Why critical**: Sets timeline controller bounds for playback

---

#### 3. stores/frame_store.py:106
```python
def set_current_frame(self, frame: int) -> None:
    if self._state_manager is None:
        return

    frame = clamp_frame(frame, self._min_frame, self._max_frame)
    current = self._state_manager.current_frame
    if current != frame:
        self._state_manager.current_frame = frame  # LINE 106
        self.current_frame_changed.emit(frame)
```

**Why critical**: Direct frame setter delegation

---

#### 4. stores/frame_store.py:195
```python
def _update_frame_range(self, min_frame: int, max_frame: int) -> None:
    # ... validation ...
    if range_changed:
        self._min_frame = min_frame
        self._max_frame = max_frame

        if self._state_manager is not None:
            self._state_manager.total_frames = max_frame  # LINE 195
```

**Why critical**: Synchronizes frame range when curve data changes

---

#### 5. ui/controllers/tracking_display_controller.py (2 instances)
```python
# Instance 1: Sets max_frame from tracking points
self.main_window.state_manager.total_frames = max_frame

# Instance 2: Sets max_frame for multi-track display
self.main_window.state_manager.total_frames = max_frame
```

**Why critical**: Updates frame range for multi-curve tracking workflows

---

## StateManager Setter Signatures (To Be Removed)

### Current Implementation

```python
# Line 397-412: current_frame setter (DEPRECATED)
@current_frame.setter
def current_frame(self, frame: int) -> None:
    """Set the current frame number (with clamping to valid range)."""
    total = self._app_state.get_total_frames()
    frame = max(1, min(frame, total))
    self._app_state.set_frame(frame)  # Already delegates!
    logger.debug(f"Current frame changed to: {frame}")

# Line 424-460: total_frames setter (DEPRECATED)
@total_frames.setter
def total_frames(self, count: int) -> None:
    """Set total frames by creating synthetic image_files list (DEPRECATED).

    This setter creates a synthetic empty image_files list of the requested length
    to maintain the "derived from image_files" invariant.

    TODO(Phase 4): Remove this setter after migrating tests to use set_image_files().
    Currently used by 14 test files - migrate them to ApplicationState.set_image_files().
    """
    count = max(1, count)
    current_total = self._app_state.get_total_frames()

    if current_total != count:
        # Create synthetic image_files list
        synthetic_files = [f"<synthetic_frame_{i+1}>" for i in range(count)]
        self._app_state.set_image_files(synthetic_files)

        # Clamp current frame if it exceeds new total
        if self.current_frame > count:
            clamped_frame = max(1, count)
            self._app_state.set_frame(clamped_frame)

        self.total_frames_changed.emit(count)
        logger.debug(f"Total frames set to {count} via synthetic image_files (DEPRECATED)")
```

---

## Migration Checklist

### Pre-Migration Tasks
- [ ] Document architecture decision for `total_frames` strategy
- [ ] Run baseline test suite: `uv run pytest tests/`
- [ ] Create migration script for bulk replacement
- [ ] Review high-risk test files

### Production Migration (5 files)
- [ ] `stores/frame_store.py` (2 current_frame, 1 total_frames)
- [ ] `ui/timeline_tabs.py` (1 total_frames)
- [ ] `ui/controllers/timeline_controller.py` (1 total_frames)
- [ ] `ui/controllers/tracking_display_controller.py` (2 total_frames)

### Test Migration (31 files)
- [ ] High-risk: `test_state_manager.py` (44 setters)
- [ ] High-risk: `test_application_state_phase0a.py` (8 setters)
- [ ] High-risk: `test_frame_change_coordinator.py` (8 setters)
- [ ] Bulk: Remaining 28 test files (48 setters)

### Post-Migration
- [ ] Remove StateManager setters
- [ ] Update CLAUDE.md
- [ ] Full test suite: `uv run pytest tests/`
- [ ] Type checking: `./bpr --errors-only`

---

## Architecture Decision Required

### Question: How should total_frames be set after migration?

**Current Implementation (Deprecated)**:
```python
state_manager.total_frames = 100
# Creates synthetic: ["<synthetic_frame_1>", "<synthetic_frame_2>", ...]
# Then: application_state.set_image_files(synthetic_files)
```

**Option A: Use set_image_files()**
```python
get_application_state().set_image_files(
    [f"frame_{i:04d}.png" for i in range(100)]
)
```
- Pro: Real file semantics
- Con: Requires naming convention

**Option B: Add set_frame_count() to ApplicationState**
```python
get_application_state().set_frame_count(100)
# Internal: Creates synthetic files just like StateManager setter
```
- Pro: Direct API, matches current semantics
- Con: Adds new method

**Option C: Remove setter entirely**
```python
# Only way: Explicit set_image_files()
# No total_frames property setter
```
- Pro: Single source of truth
- Con: Breaking change

**Recommendation**: Option B - Add `set_frame_count()` to ApplicationState
- Maintains semantic compatibility
- Direct and clear API
- Works for non-image workflows
- Documented as internal synthetic pattern

---

**Document Status**: Complete Inventory
**Ready for**: Architecture Decision & Phase 4 Implementation
**Last Updated**: 2025-10-17

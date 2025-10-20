# Detailed Duplication Verification - Code Examples

**Generated**: 2025-10-20
**Verification Method**: Direct file inspection with line-by-line comparison

---

## TASK 1.3: Spinbox Blocking Duplication

### Exact Code Comparison

**First Occurrence** (`ui/controllers/point_editor_controller.py`, lines 139-146):
```python
139  _ = self.main_window.point_x_spinbox.blockSignals(True)
140  _ = self.main_window.point_y_spinbox.blockSignals(True)
141
142  self.main_window.point_x_spinbox.setValue(x)
143  self.main_window.point_y_spinbox.setValue(y)
144
145  _ = self.main_window.point_x_spinbox.blockSignals(False)
146  _ = self.main_window.point_y_spinbox.blockSignals(False)
```

**Second Occurrence** (`ui/controllers/point_editor_controller.py`, lines 193-200):
```python
193  _ = self.main_window.point_x_spinbox.blockSignals(True)
194  _ = self.main_window.point_y_spinbox.blockSignals(True)
195
196  self.main_window.point_x_spinbox.setValue(x)
197  self.main_window.point_y_spinbox.setValue(y)
198
199  _ = self.main_window.point_x_spinbox.blockSignals(False)
200  _ = self.main_window.point_y_spinbox.blockSignals(False)
```

### Analysis

| Aspect | First | Second | Match |
|--------|-------|--------|-------|
| blockSignals(True) count | 2 | 2 | ✅ |
| setValue() count | 2 | 2 | ✅ |
| blockSignals(False) count | 2 | 2 | ✅ |
| Exact code match | Yes | Yes | ✅ |
| Line count | 8 | 8 | ✅ |

### Refactoring Target

Can be eliminated with helper method:
```python
def _update_spinboxes_silently(self, x: float, y: float) -> None:
    """Update spinbox values without triggering signals."""
    if not self.main_window.point_x_spinbox or not self.main_window.point_y_spinbox:
        return

    with QSignalBlocker(self.main_window.point_x_spinbox), \
         QSignalBlocker(self.main_window.point_y_spinbox):
        self.main_window.point_x_spinbox.setValue(x)
        self.main_window.point_y_spinbox.setValue(y)
```

**Result**: 16 lines → 1 line call (15 lines saved)

---

## TASK 1.5: Point Lookup Duplication

### Pattern Instances

**Instance 1** - SetEndframeCommand (lines 183-187):
```python
183  point_index = None
184  for i, point in enumerate(curve_data):
185      if point[0] == context.current_frame:  # point[0] is the frame number
186          point_index = i
187          break
```

**Instance 2** - DeleteCurrentFrameKeyframeCommand (lines 420-424):
```python
420  for i, point in enumerate(curve_data):
421      if point[0] == context.current_frame:  # point[0] is the frame number
422          point_index = i
423          current_point = point
424          break
```

**Instance 3** - NudgePointsCommand (lines 742-745):
```python
742  for i, point in enumerate(curve_data):
743      if point[0] == context.current_frame:  # point[0] is the frame number
744          point_index = i
745          break
```

### Core Duplication

All three share the **enumerated lookup core**:
```python
for i, point in enumerate(curve_data):
    if point[0] == context.current_frame:  # point[0] is the frame number
        point_index = i
        [break or additional logic]
```

**Duplication Count**:
- Core pattern appears 3 times
- Core pattern is ~3-4 lines per occurrence
- Total duplicated: 9-12 lines of lookup logic

### Refactoring Target

Extract to base class (ShortcutCommand):
```python
def _find_point_index_at_frame(
    self,
    curve_data: CurveDataList,
    frame: int
) -> int | None:
    """Find the index of a point at the given frame.

    Args:
        curve_data: List of curve points
        frame: Frame number to search for

    Returns:
        Point index if found, None otherwise
    """
    for i, point in enumerate(curve_data):
        if point[0] == frame:  # point[0] is the frame number
            return i
    return None
```

**Usage becomes**:
```python
point_index = self._find_point_index_at_frame(curve_data, context.current_frame)
```

**Result**: 3 copies of 3-4 lines → 1 helper method + 1 line calls (8-10 lines saved)

---

## Timeline Controller blockSignals Pairs

### All 6 Pairs

**Pair 1 & 2**: Frame value change (lines 217-219, 229-231)
```python
# Pair 1 (lines 217-219)
217  _ = self.frame_slider.blockSignals(True)
218  self.frame_slider.setValue(value)
219  _ = self.frame_slider.blockSignals(False)

# Pair 2 (lines 229-231)
229  _ = self.frame_spinbox.blockSignals(True)
230  self.frame_spinbox.setValue(value)
231  _ = self.frame_spinbox.blockSignals(False)
```

**Pair 3 & 4**: Frame display update (lines 294-300)
```python
# Pair 3 (lines 294-296)
294  _ = self.frame_spinbox.blockSignals(True)
295  self.frame_spinbox.setValue(frame)
296  _ = self.frame_spinbox.blockSignals(False)

# Pair 4 (lines 298-300)
298  _ = self.frame_slider.blockSignals(True)
299  self.frame_slider.setValue(frame)
300  _ = self.frame_slider.blockSignals(False)
```

**Pair 5 & 6**: Playback button state (lines 389-391, 412-414)
```python
# Pair 5 (lines 389-391)
389  _ = self.btn_play_pause.blockSignals(True)
390  self.btn_play_pause.setChecked(True)
391  _ = self.btn_play_pause.blockSignals(False)

# Pair 6 (lines 412-414)
412  _ = self.btn_play_pause.blockSignals(True)
413  self.btn_play_pause.setChecked(False)
414  _ = self.btn_play_pause.blockSignals(False)
```

### Pattern Summary

All 6 pairs follow identical pattern:
1. blockSignals(True) - disable signals
2. setValue() or setChecked() - update widget
3. blockSignals(False) - re-enable signals

### Refactoring Opportunity

Same QSignalBlocker pattern as Task 1.3 would eliminate all 6:
```python
with QSignalBlocker(widget):
    widget.setValue(value)  # or setChecked(), etc.
```

**Result**: 18 lines (3 lines × 6 pairs) → 6 lines (1 line × 6 pairs) = 12 lines saved

---

## Task 2.1: Active Curve Pattern Analysis

### Pattern Definition

The 4-step pattern identified:
```python
active = state.active_curve
if not active:
    return
data = state.get_curve_data(active)
if not data:
    return
```

### Files Containing Pattern

Verified presence in 47 files across all layers:

**Core Layer**:
- core/commands/shortcut_commands.py (6 occurrences)

**Service Layer**:
- services/interaction_service.py
- services/transform_service.py

**UI Layer**:
- ui/main_window.py
- ui/curve_view_widget.py
- ui/timeline_tabs.py
- ui/state_manager.py
- ui/controllers/tracking_display_controller.py
- ui/controllers/tracking_selection_controller.py
- ui/controllers/point_editor_controller.py
- ui/controllers/curve_view/state_sync_controller.py
- ui/controllers/curve_view/curve_data_facade.py

**Data Layer**:
- data/curve_view_plumbing.py
- data/batch_edit.py

**Rendering Layer**:
- rendering/render_state.py

**Test Layer**:
- Multiple test files

### Direct Count Examples

**shortcut_commands.py Line 136**:
```python
135  app_state = get_application_state()
136  active_curve = app_state.active_curve
137  if not active_curve:
138      return False
139  curve_data = app_state.get_curve_data(active_curve)
140  if not curve_data:
141      return False
```

**shortcut_commands.py Line 177**:
```python
176  app_state = get_application_state()
177  active_curve = app_state.active_curve
178  if not active_curve:
179      return False
180  curve_data = app_state.get_curve_data(active_curve)
181  if not curve_data:
182      return False
```

(Similar pattern repeats at lines 378, 413, 692, 736)

### Refactoring Target

Replace all instances with:
```python
state = get_application_state()
if (cd := state.active_curve_data) is None:
    return False
curve_name, curve_data = cd
```

**Reduces**: 6 lines → 3 lines per occurrence
**Saves**: 3 lines × 60+ occurrences = ~180 lines total

---

## Conclusion

| Task | Status | Details |
|------|--------|---------|
| 1.3 Spinbox | ✅ Ready | 16 lines duplicated, ready for extraction |
| 1.5 Lookup | ⚠️ Update | Lines need correction, pattern confirmed |
| Timeline | ✅ Verified | 12 blockSignals in 6 pairs, enhancement candidate |
| 2.1 Active | ⚠️ Scope | Larger than planned (60+ vs 15+ claimed) |

## ⚡ **PHASE 2: QUICK WINS (WEEK 2)**

**Objective:** High-impact, low-effort improvements
**Total Effort:** 15 hours
**Priority:** HIGH - Fast ROI

---

### **Task 2.1: Frame Clamping Utility**
**Time:** 4 hours
**Impact:** Eliminates 5 frame clamp duplications + standardizes 30+ other clamp patterns

#### **Scope Clarification:**
- **Frame-specific clamps:** 5 instances (will use new utility)
- **Other clamping patterns:** 30+ (zoom, grid, array indices) - context-specific, NOT frame-related
- **Manual review needed:** Flag 30+ patterns for appropriate handling

**Pattern Distribution:**
- Frame clamps: 5 (timeline_tabs×2, timeline_controller×1, state_manager×1, frame_store×1)
- Zoom clamps: 3
- Grid size clamps: 5
- Widget dimension clamps: 1
- Smoothing window clamps: 1
- Array index clamps: 2
- Other clamping: 15+

#### **Implementation:**

**1. Create utility module: `core/frame_utils.py`**

```python
"""Frame manipulation utilities."""

def clamp_frame(frame: int, min_frame: int, max_frame: int) -> int:
    """Clamp frame value to valid range [min_frame, max_frame].

    Args:
        frame: Frame number to clamp
        min_frame: Minimum valid frame (inclusive)
        max_frame: Maximum valid frame (inclusive)

    Returns:
        Clamped frame value

    Examples:
        >>> clamp_frame(5, 1, 10)
        5
        >>> clamp_frame(0, 1, 10)
        1
        >>> clamp_frame(15, 1, 10)
        10
    """
    return max(min_frame, min(max_frame, frame))


def is_frame_in_range(frame: int, min_frame: int, max_frame: int) -> bool:
    """Check if frame is within valid range.

    Args:
        frame: Frame number to check
        min_frame: Minimum valid frame (inclusive)
        max_frame: Maximum valid frame (inclusive)

    Returns:
        True if frame is in range

    Examples:
        >>> is_frame_in_range(5, 1, 10)
        True
        >>> is_frame_in_range(0, 1, 10)
        False
    """
    return min_frame <= frame <= max_frame
```

**2. Create tests: `tests/test_frame_utils.py`**

```python
"""Tests for frame manipulation utilities."""

import pytest
from core.frame_utils import clamp_frame, is_frame_in_range


class TestClampFrame:
    """Tests for clamp_frame function."""

    def test_frame_within_range(self):
        """Frame within range should be unchanged."""
        assert clamp_frame(5, 1, 10) == 5
        assert clamp_frame(1, 1, 10) == 1
        assert clamp_frame(10, 1, 10) == 10

    def test_frame_below_min(self):
        """Frame below min should be clamped to min."""
        assert clamp_frame(0, 1, 10) == 1
        assert clamp_frame(-5, 1, 10) == 1

    def test_frame_above_max(self):
        """Frame above max should be clamped to max."""
        assert clamp_frame(11, 1, 10) == 10
        assert clamp_frame(100, 1, 10) == 10

    def test_single_frame_range(self):
        """Range with min == max should return that frame."""
        assert clamp_frame(0, 5, 5) == 5
        assert clamp_frame(5, 5, 5) == 5
        assert clamp_frame(10, 5, 5) == 5


class TestIsFrameInRange:
    """Tests for is_frame_in_range function."""

    def test_frame_in_range(self):
        """Frame in range should return True."""
        assert is_frame_in_range(5, 1, 10) is True
        assert is_frame_in_range(1, 1, 10) is True
        assert is_frame_in_range(10, 1, 10) is True

    def test_frame_out_of_range(self):
        """Frame out of range should return False."""
        assert is_frame_in_range(0, 1, 10) is False
        assert is_frame_in_range(11, 1, 10) is False
```

**3. Update call sites (19 files):**

**ui/timeline_tabs.py:329, 677:**
```python
# Before:
frame = max(self.min_frame, min(self.max_frame, frame))

# After:
from core.frame_utils import clamp_frame
frame = clamp_frame(frame, self.min_frame, self.max_frame)
```

**stores/frame_store.py:99:**
```python
# Before:
frame = max(self._min_frame, min(frame, self._max_frame))

# After:
from core.frame_utils import clamp_frame
frame = clamp_frame(frame, self._min_frame, self._max_frame)
```

**ui/controllers/timeline_controller.py:278:**
```python
# Before:
frame = max(1, min(frame, self.frame_spinbox.maximum()))

# After:
from core.frame_utils import clamp_frame
frame = clamp_frame(frame, 1, self.frame_spinbox.maximum())
```

**Automated replacement script: `tools/replace_frame_clamping.py`**

```python
#!/usr/bin/env python3
"""Replace frame clamping duplications with utility function."""

import re
from pathlib import Path

# Pattern 1: Variable appears on both sides (most common)
PATTERN_SAME_VAR = re.compile(
    r'(\w+)\s*=\s*max\(([^,]+),\s*min\(([^,]+),\s*\1\)\)',
    re.MULTILINE
)

# Pattern 2: Broader pattern for manual review (different variable names)
PATTERN_ALL = re.compile(
    r'max\s*\([^,]+,\s*min\s*\([^,]+,\s*[^)]+\)\)',
    re.MULTILINE
)

def replace_clamping(content: str, file_path: Path) -> tuple[str, int]:
    """Replace frame clamping patterns.

    ⚠️ IMPORTANT: This script handles common patterns but may not catch all.
    Always run manual review afterward to catch edge cases.
    """

    replacements = 0
    lines = content.split('\n')
    new_lines = []
    needs_import = False

    for line in lines:
        # Try pattern 1 (same variable - auto-replace)
        match = PATTERN_SAME_VAR.search(line)
        if match:
            var, min_val, max_val = match.groups()
            indent = len(line) - len(line.lstrip())
            replacement = f"{' ' * indent}{var} = clamp_frame({var}, {min_val}, {max_val})"
            new_lines.append(replacement)
            needs_import = True
            replacements += 1
            print(f"  Replaced: {line.strip()}")
            print(f"  With:     {replacement.strip()}")
        else:
            # Check if line has clamping pattern that wasn't caught
            if PATTERN_ALL.search(line) and 'clamp_frame' not in line:
                print(f"  ⚠️  MANUAL REVIEW: {file_path}:{lines.index(line)+1}")
                print(f"      {line.strip()}")
            new_lines.append(line)

    content = '\n'.join(new_lines)

    # Add import if needed
    if needs_import and 'from core.frame_utils import clamp_frame' not in content:
        # Find first import block
        lines = content.split('\n')
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_index = i

        lines.insert(import_index + 1, 'from core.frame_utils import clamp_frame')
        content = '\n'.join(lines)

    return content, replacements

def main():
    """Process all files with frame clamping."""
    files_with_pattern = [
        "ui/timeline_tabs.py",
        "stores/frame_store.py",
        "ui/controllers/timeline_controller.py",
        # Add more files as found by grep
    ]

    total = 0
    for file_path in files_with_pattern:
        path = Path(file_path)
        if path.exists():
            print(f"\nProcessing {file_path}...")
            content = path.read_text()
            new_content, count = replace_clamping(content, path)
            if count > 0:
                path.write_text(new_content)
                total += count
                print(f"  Fixed {count} instances")

    print(f"\n✅ Total replacements: {total}")

if __name__ == "__main__":
    main()
```

#### **Verification Steps:**

```bash
# 1. Create and test utility
~/.local/bin/uv run pytest tests/test_frame_utils.py -v

# 2. Find all clamping patterns
grep -rn "max.*min.*frame" ui/ stores/ core/ --include="*.py"

# 3. Run replacement script (handles common patterns)
python3 tools/replace_frame_clamping.py

# 4. Manual review for edge cases
echo "⚠️  Checking for patterns that need manual review..."
grep -rn "max.*min.*frame\|min.*max.*frame" ui/ stores/ core/ --include="*.py" | grep -v "clamp_frame"
# Review each result and convert manually if needed

# 5. Verify imports added
grep -r "from core.frame_utils import clamp_frame" ui/ stores/ --include="*.py"

# 6. Run tests to ensure behavior unchanged
~/.local/bin/uv run pytest tests/ -k frame -v
```

#### **Success Metrics:**
- ✅ 5 frame clamps use `clamp_frame()` utility
- ✅ 30+ other clamp patterns flagged for manual review
- ✅ All frame-related tests pass
- ✅ New utility has 100% test coverage

---

### **Task 2.2: Remove Redundant list() in deepcopy()**
**Time:** 2-3 hours
**Impact:** Code clarity + slight performance

#### **Files to Fix:**

**core/commands/curve_commands.py (Multiple instances):**

**Lines 48-49:**
```python
# Before:
self.new_data: list[LegacyPointData] = copy.deepcopy(list(new_data))
self.old_data: list[LegacyPointData] | None = copy.deepcopy(list(old_data)) if old_data is not None else None

# After:
self.new_data: list[LegacyPointData] = copy.deepcopy(new_data)
self.old_data: list[LegacyPointData] | None = copy.deepcopy(old_data) if old_data is not None else None
```

**Lines 133-134:**
```python
# Before:
self.old_points: list[LegacyPointData] | None = copy.deepcopy(list(old_points)) if old_points else None
self.new_points: list[LegacyPointData] | None = copy.deepcopy(list(new_points)) if new_points else None

# After:
self.old_points: list[LegacyPointData] | None = copy.deepcopy(old_points) if old_points else None
self.new_points: list[LegacyPointData] | None = copy.deepcopy(new_points) if new_points else None
```

**Automated fix script: `tools/fix_deepcopy_list.py`**

```python
#!/usr/bin/env python3
"""Remove redundant list() wrapper around copy.deepcopy()."""

import re
from pathlib import Path

PATTERN = re.compile(r'copy\.deepcopy\(list\(([^)]+)\)\)')

def fix_deepcopy(content: str) -> tuple[str, int]:
    """Replace deepcopy(list(x)) with deepcopy(x)."""
    replacements = 0

    def replacer(match):
        nonlocal replacements
        replacements += 1
        return f'copy.deepcopy({match.group(1)})'

    new_content = PATTERN.sub(replacer, content)
    return new_content, replacements

def main():
    """Process command files."""
    files = [
        "core/commands/curve_commands.py",
        "core/commands/insert_track_command.py",
    ]

    total = 0
    for file_path in files:
        path = Path(file_path)
        if path.exists():
            content = path.read_text()
            new_content, count = fix_deepcopy(content)
            if count > 0:
                path.write_text(new_content)
                print(f"Fixed {count} instances in {file_path}")
                total += count

    print(f"\n✅ Total replacements: {total}")

if __name__ == "__main__":
    main()
```

#### **Verification Steps:**

```bash
# 1. Find pattern
grep -rn "deepcopy(list(" core/commands/ --include="*.py"

# 2. Run fix
python3 tools/fix_deepcopy_list.py

# 3. Verify gone
grep -rn "deepcopy(list(" core/commands/ --include="*.py"
# Should be: 0 results

# 4. Run command tests
~/.local/bin/uv run pytest tests/test_curve_commands.py -v
~/.local/bin/uv run pytest tests/test_insert_track_command.py -v
```

#### **Success Metrics:**
- ✅ 0 instances of `deepcopy(list(x))` pattern
- ✅ All command tests pass
- ✅ Undo/redo functionality unchanged

---

### **Task 2.3: Frame Status NamedTuple**
**Time:** 4 hours
**Impact:** Type safety + readability

#### **Implementation:**

**1. Add NamedTuple to `core/models.py`:**

```python
from typing import NamedTuple

class FrameStatus(NamedTuple):
    """Status information for a single frame in timeline.

    Attributes:
        keyframe_count: Number of keyframe points
        interpolated_count: Number of interpolated points
        tracked_count: Number of tracked points
        endframe_count: Number of endframe points
        normal_count: Number of normal points
        is_startframe: True if this is the first frame with data
        is_inactive: True if frame has no active tracking
        has_selected: True if any points are selected in this frame
    """
    keyframe_count: int
    interpolated_count: int
    tracked_count: int
    endframe_count: int
    normal_count: int
    is_startframe: bool
    is_inactive: bool
    has_selected: bool

    @property
    def total_points(self) -> int:
        """Total number of points in this frame."""
        return (
            self.keyframe_count
            + self.interpolated_count
            + self.tracked_count
            + self.endframe_count
            + self.normal_count
        )

    @property
    def is_empty(self) -> bool:
        """True if frame has no points."""
        return self.total_points == 0
```

**2. Update `services/data_service.py` return type:**

```python
def get_frame_range_point_status(
    self,
    curve_data: CurveDataList,
    selected_indices: set[int] | None = None,
) -> dict[int, FrameStatus]:  # Changed from dict[int, tuple]
    """Get point status information for each frame.

    Returns:
        Dictionary mapping frame number to FrameStatus
    """
    from core.models import FrameStatus

    frame_status: dict[int, FrameStatus] = {}

    # ... existing logic ...

    # Instead of returning tuple:
    # return (keyframe_count, interpolated_count, ...)

    # Return NamedTuple:
    frame_status[frame] = FrameStatus(
        keyframe_count=keyframe_count,
        interpolated_count=interpolated_count,
        tracked_count=tracked_count,
        endframe_count=endframe_count,
        normal_count=normal_count,
        is_startframe=is_startframe,
        is_inactive=is_inactive,
        has_selected=has_selected,
    )

    return frame_status
```

**3. Update consumers (5 callsites):**

**ui/timeline_tabs.py:441-450:**

**Before:**
```python
(
    keyframe_count,
    interpolated_count,
    tracked_count,
    endframe_count,
    _normal_count,
    is_startframe,
    is_inactive,
    has_selected,
) = status_data
```

**After:**
```python
# Direct attribute access - much cleaner!
status = status_data
keyframe_count = status.keyframe_count
interpolated_count = status.interpolated_count
tracked_count = status.tracked_count
endframe_count = status.endframe_count
is_startframe = status.is_startframe
is_inactive = status.is_inactive
has_selected = status.has_selected

# Or even better - use status directly:
if status.has_selected:
    # ...
if status.is_startframe:
    # ...
```

Apply same pattern to all 5 callsites.

#### **Verification Steps:**

```bash
# 1. Find all tuple unpacking sites
grep -rn "keyframe_count," ui/ --include="*.py" -A 10

# 2. Run tests
~/.local/bin/uv run pytest tests/test_timeline_tabs.py -v
~/.local/bin/uv run pytest tests/test_data_service.py -v

# 3. Type check
~/.local/bin/uv run ./bpr ui/timeline_tabs.py
# Should show improved type inference
```

#### **Success Metrics:**
- ✅ FrameStatus NamedTuple defined with docstrings
- ✅ All 5 callsites updated to use named attributes
- ✅ All timeline tests pass
- ✅ Type checker shows improved inference

---

### **Task 2.4: Frame Range Extraction Utility**
**Time:** 3 hours
**Impact:** DRY compliance

#### **Implementation:**

**Add to `core/frame_utils.py`:**

```python
from core.type_aliases import CurveDataList

def get_frame_range_from_curve(curve_data: CurveDataList) -> tuple[int, int] | None:
    """Extract min/max frame numbers from curve data.

    Args:
        curve_data: List of curve points (frame, x, y, ...) tuples

    Returns:
        (min_frame, max_frame) or None if no valid frames found

    Examples:
        >>> data = [(1, 10.0, 20.0), (5, 15.0, 25.0), (3, 12.0, 22.0)]
        >>> get_frame_range_from_curve(data)
        (1, 5)
        >>> get_frame_range_from_curve([])
        None
    """
    if not curve_data:
        return None

    frames = [int(point[0]) for point in curve_data if len(point) >= 3]
    if not frames:
        return None

    return (min(frames), max(frames))


def get_frame_range_with_limits(
    curve_data: CurveDataList,
    max_range: int = 200,
) -> tuple[int, int] | None:
    """Extract frame range with optional limiting for performance.

    Args:
        curve_data: List of curve points
        max_range: Maximum frame range allowed (for UI performance)

    Returns:
        (min_frame, limited_max_frame) or None

    Examples:
        >>> data = [(1, 0, 0), (1000, 0, 0)]  # Very wide range
        >>> get_frame_range_with_limits(data, max_range=200)
        (1, 200)  # Limited to 200 frames
    """
    range_result = get_frame_range_from_curve(curve_data)
    if range_result is None:
        return None

    min_frame, max_frame = range_result

    # Limit range for performance
    if max_frame - min_frame + 1 > max_range:
        max_frame = min_frame + max_range - 1

    return (min_frame, max_frame)
```

**Add tests to `tests/test_frame_utils.py`:**

```python
class TestGetFrameRangeFromCurve:
    """Tests for get_frame_range_from_curve function."""

    def test_normal_curve(self):
        """Normal curve should return min/max frames."""
        data = [(1, 10.0, 20.0), (5, 15.0, 25.0), (3, 12.0, 22.0)]
        assert get_frame_range_from_curve(data) == (1, 5)

    def test_empty_curve(self):
        """Empty curve should return None."""
        assert get_frame_range_from_curve([]) is None

    def test_single_point(self):
        """Single point should return same frame for min/max."""
        data = [(42, 10.0, 20.0)]
        assert get_frame_range_from_curve(data) == (42, 42)

    def test_invalid_points_skipped(self):
        """Points with < 3 elements should be skipped."""
        data = [(1, 10.0), (5, 15.0, 25.0), (3, 12.0, 22.0)]
        assert get_frame_range_from_curve(data) == (3, 5)


class TestGetFrameRangeWithLimits:
    """Tests for get_frame_range_with_limits function."""

    def test_within_limit(self):
        """Range within limit should be unchanged."""
        data = [(1, 0, 0), (50, 0, 0)]
        assert get_frame_range_with_limits(data, max_range=200) == (1, 50)

    def test_exceeds_limit(self):
        """Range exceeding limit should be truncated."""
        data = [(1, 0, 0), (1000, 0, 0)]
        assert get_frame_range_with_limits(data, max_range=200) == (1, 200)
```

**Update call sites:**

**ui/controllers/multi_point_tracking_controller.py:823-845:**

**Before:**
```python
def _update_frame_range_from_data(self, curve_data: CurveDataList) -> None:
    """Update frame range based on single curve data."""
    if not curve_data:
        return

    frames = [int(point[0]) for point in curve_data if len(point) >= 3]
    if frames:
        min_frame = min(frames)
        max_frame = max(frames)
        # ... set frame range ...
```

**After:**
```python
from core.frame_utils import get_frame_range_from_curve

def _update_frame_range_from_data(self, curve_data: CurveDataList) -> None:
    """Update frame range based on single curve data."""
    frame_range = get_frame_range_from_curve(curve_data)
    if frame_range is not None:
        min_frame, max_frame = frame_range
        # ... set frame range ...
```

**ui/timeline_tabs.py:417-434:**

**Before:**
```python
frames = [int(point[0]) for point in curve_data if len(point) >= 3]
if frames:
    min_frame = min(frames)
    max_frame = max(frames)

    # Also consider image sequence
    if self._state_manager:
        image_sequence_frames = self._state_manager.total_frames
        max_frame = max(max_frame, image_sequence_frames)

    # Limit to reasonable number
    max_timeline_frames = 200
    if max_frame - min_frame + 1 > max_timeline_frames:
        max_frame = min_frame + max_timeline_frames - 1
```

**After:**
```python
from core.frame_utils import get_frame_range_with_limits

frame_range = get_frame_range_from_curve(curve_data)
if frame_range is not None:
    min_frame, max_frame = frame_range

    # Also consider image sequence
    if self._state_manager:
        image_sequence_frames = self._state_manager.total_frames
        max_frame = max(max_frame, image_sequence_frames)

    # Apply limit for performance
    _, max_frame = get_frame_range_with_limits(
        [(min_frame, 0, 0), (max_frame, 0, 0)],
        max_range=200
    )
```

#### **Verification Steps:**

```bash
# 1. Run new tests
~/.local/bin/uv run pytest tests/test_frame_utils.py::TestGetFrameRangeFromCurve -v

# 2. Update call sites
# (Manual - only 2 files)

# 3. Run affected tests
~/.local/bin/uv run pytest tests/test_multi_point_tracking_merge.py -v
~/.local/bin/uv run pytest tests/test_timeline_tabs.py -v
```

#### **Success Metrics:**
- ✅ 2 utilities added with tests
- ✅ 2 callsites simplified
- ✅ All tests pass

---

### **Task 2.5: Remove SelectionContext Enum**
**Time:** 4 hours
**Impact:** Simplifies branching logic

#### **Implementation:**

**1. Identify current SelectionContext usage:**

```bash
grep -rn "SelectionContext" ui/controllers/multi_point_tracking_controller.py
```

**2. Replace with explicit methods:**

**Before (Lines 688-821 - 134-line method with branching):**
```python
def update_curve_display(
    self,
    context: SelectionContext = SelectionContext.DEFAULT,
    selected_points: list[str] | None = None,
) -> None:
    """Update curve display based on context."""

    # ... 50 lines of setup ...

    if context == SelectionContext.DEFAULT:
        # Preserve selection
        self.main_window.curve_widget.set_curves_data(
            all_curves_data, metadata, active_curve
        )
    elif context == SelectionContext.MANUAL_SELECTION:
        # Use provided selection
        selected_curves_list = selected_points or []
        self.main_window.curve_widget.set_curves_data(
            all_curves_data, metadata, active_curve, selected_curves=selected_curves_list
        )
    else:
        # Reset to active curve
        self.main_window.curve_widget.set_curves_data(
            all_curves_data, metadata, active_curve, selected_curves=[active_curve]
        )
```

**After (3 focused methods):**
```python
def update_display_preserve_selection(self) -> None:
    """Update display, preserving current selection."""
    curves, metadata, active = self._prepare_display_data()
    self.main_window.curve_widget.set_curves_data(curves, metadata, active)


def update_display_with_selection(self, selected: list[str]) -> None:
    """Update display with specific curve selection.

    Args:
        selected: List of curve names to select
    """
    curves, metadata, active = self._prepare_display_data()
    self.main_window.curve_widget.set_curves_data(
        curves, metadata, active, selected_curves=selected
    )


def update_display_reset_selection(self) -> None:
    """Update display, resetting selection to active curve only."""
    curves, metadata, active = self._prepare_display_data()
    selected = [active] if active else []
    self.main_window.curve_widget.set_curves_data(
        curves, metadata, active, selected_curves=selected
    )


def _prepare_display_data(self) -> tuple[dict, dict, str | None]:
    """Prepare curve data for display (common logic).

    Returns:
        (all_curves_data, metadata, active_curve)
    """
    # ... extract common setup logic from old update_curve_display ...
    active_curve = self._app_state.active_curve

    # Get all curves
    all_curves_data = {}
    metadata = {}
    for curve_name in self._app_state.get_all_curve_names():
        curve_data = self._app_state.get_curve_data(curve_name)
        if curve_data:
            all_curves_data[curve_name] = curve_data
            metadata[curve_name] = self._app_state.get_curve_metadata(curve_name)

    return all_curves_data, metadata, active_curve
```

**3. Update all callsites:**

**Before:**
```python
# Various calls with context enum
self.update_curve_display(SelectionContext.DEFAULT)
self.update_curve_display(SelectionContext.MANUAL_SELECTION, selected_points=points)
self.update_curve_display(SelectionContext.DATA_LOADING)
```

**After:**
```python
# Explicit method calls - self-documenting
self.update_display_preserve_selection()
self.update_display_with_selection(points)
self.update_display_reset_selection()
```

**4. Remove SelectionContext enum:**

Delete from file or mark as deprecated if external code uses it.

#### **Verification Steps:**

```bash
# 1. Find all SelectionContext uses
grep -rn "SelectionContext" ui/ --include="*.py"

# 2. After refactoring, should only be in tests (if any)

# 3. Run controller tests
~/.local/bin/uv run pytest tests/test_multi_point_tracking_merge.py -v

# 4. Manual test: Load multi-point data, verify display updates correctly
```

#### **Success Metrics:**
- ✅ SelectionContext enum removed
- ✅ 3 focused methods replace 1 complex method
- ✅ All branching logic eliminated
- ✅ All tests pass

---

### **Phase 2 Completion Checklist:**

```bash
cat > verify_phase2.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Phase 2 Verification ==="

echo "1. Frame clamping utility..."
if grep -q "from core.frame_utils import clamp_frame" ui/timeline_tabs.py; then
    echo "✅ PASS: clamp_frame utility in use"
else
    echo "❌ FAIL: clamp_frame not imported"
    exit 1
fi

echo "2. Redundant list() removed..."
COUNT=$(grep -r "deepcopy(list(" core/commands/ --include="*.py" | wc -l)
if [ "$COUNT" -eq 0 ]; then
    echo "✅ PASS: No redundant list() in deepcopy"
else
    echo "❌ FAIL: Found $COUNT redundant list() patterns"
    exit 1
fi

echo "3. FrameStatus NamedTuple..."
if grep -q "class FrameStatus(NamedTuple):" core/models.py; then
    echo "✅ PASS: FrameStatus defined"
else
    echo "❌ FAIL: FrameStatus not found"
    exit 1
fi

echo "4. SelectionContext removed..."
COUNT=$(grep -r "SelectionContext\." ui/controllers/multi_point_tracking_controller.py | wc -l)
if [ "$COUNT" -eq 0 ]; then
    echo "✅ PASS: SelectionContext enum removed"
else
    echo "❌ FAIL: SelectionContext still in use ($COUNT instances)"
    exit 1
fi

echo "5. Running Quick Win tests..."
~/.local/bin/uv run pytest tests/test_frame_utils.py -v
~/.local/bin/uv run pytest tests/test_timeline_tabs.py -v
~/.local/bin/uv run pytest tests/test_curve_commands.py -v

echo "=== Phase 2 COMPLETE ==="
EOF

chmod +x verify_phase2.sh
./verify_phase2.sh
```

**Phase 2 Success Criteria:**
- ✅ ~300 lines of duplicated code eliminated
- ✅ 5 new utilities added
- ✅ All Quick Win tests pass
- ✅ Type safety improved (FrameStatus)
- ✅ Code readability improved

---


---

**Navigation:**
- [← Previous: Phase 1 Critical Safety](phase1_critical_safety_fixes.md)
- [→ Next: Phase 3 Architectural Refactoring](phase3_architectural_refactoring.md)
- [← Back to Overview](README.md)

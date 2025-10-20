# REFACTORING_PLAN - Critical Corrections

**Document Purpose**: Specific code changes and updates needed before execution

**Status**: Apply these fixes before Phase 1.2 completion

---

## Fix #1: Move Zoom Constants to core/defaults.py

### Problem
Phase 2.2 proposed code violates layer separation by importing from `ui.ui_constants`:
```python
from ui.ui_constants import MAX_ZOOM_FACTOR, MIN_ZOOM_FACTOR  # ❌ VIOLATION
```

### Solution

**Step 1: Update core/defaults.py**

Replace REFACTORING_PLAN.md Task 1.2 Step 1 with:

```python
#!/usr/bin/env python
"""
Application-wide default constants.

These constants are used by core business logic and services.
UI-specific constants remain in ui/ui_constants.py.
"""

# Image dimensions (used by TransformService)
DEFAULT_IMAGE_WIDTH: int = 2048
DEFAULT_IMAGE_HEIGHT: int = 1556

# Interaction defaults (used by shortcut commands)
DEFAULT_NUDGE_AMOUNT: float = 1.0

# Transform/zoom constraints (used by TransformService)
MAX_ZOOM_FACTOR: float = 20.0      # Maximum zoom level
MIN_ZOOM_FACTOR: float = 0.1       # Minimum zoom level
```

**Step 2: Update REFACTORING_PLAN.md Task 1.2 Step 5**

Replace the grep command:
```bash
# OLD
grep -n "from ui\.ui_constants import" --include="*.py" -r .

# NEW - More comprehensive
grep -n "from ui\.ui_constants import" --include="*.py" -r . | \
  grep -v "^./ui/" | grep -v "^./rendering/"
```

Expected output:
```
./services/transform_service.py:17:from ui.ui_constants import DEFAULT_IMAGE_HEIGHT, DEFAULT_IMAGE_WIDTH
./services/transform_core.py:17:from ui.ui_constants import DEFAULT_IMAGE_HEIGHT, DEFAULT_IMAGE_WIDTH
./services/ui_service.py:X:from ui.ui_constants import DEFAULT_STATUS_TIMEOUT
./core/commands/shortcut_commands.py:XXX:from ui.ui_constants import DEFAULT_NUDGE_AMOUNT
```

**Step 3: Update REFACTORING_PLAN.md Task 2.2 proposed code**

Fix line 532 in Phase 2.2 code snippet:

```diff
  def calculate_fit_bounds(
      self,
      points: list[tuple[float, float]],
      viewport_width: int,
      viewport_height: int,
      padding_factor: float = 1.2
  ) -> tuple[float, float, float]:
      """Calculate optimal zoom and center for fitting points in viewport."""
      if not points:
          return (0.0, 0.0, 1.0)

      # ... existing code ...

      if width_needed > 0 and height_needed > 0:
-         from ui.ui_constants import MAX_ZOOM_FACTOR, MIN_ZOOM_FACTOR
+         from core.defaults import MAX_ZOOM_FACTOR, MIN_ZOOM_FACTOR

          zoom_x = viewport_width / width_needed
          zoom_y = viewport_height / height_needed
          optimal_zoom = min(zoom_x, zoom_y, MAX_ZOOM_FACTOR)
          optimal_zoom = max(MIN_ZOOM_FACTOR, optimal_zoom)
      else:
          optimal_zoom = 1.0

      return (center_x, center_y, optimal_zoom)
```

---

## Fix #2: Complete Constant Migration

### Problem
Phase 1.2 misses `DEFAULT_STATUS_TIMEOUT` which is imported by `services/ui_service.py`

### Solution

**Step 1: Add to core/defaults.py**

```python
# Status message timeout (used by UIService)
DEFAULT_STATUS_TIMEOUT: int = 2000  # milliseconds
```

**Step 2: Update services/ui_service.py**

Find this line:
```python
from ui.ui_constants import DEFAULT_STATUS_TIMEOUT
```

Replace with:
```python
from core.defaults import DEFAULT_STATUS_TIMEOUT
```

**Step 3: Update REFACTORING_PLAN.md Task 1.2 Step 4**

Add this step after Step 4:

```bash
- [ ] **Step 4b**: Update `services/ui_service.py`
  - Find line importing `DEFAULT_STATUS_TIMEOUT` from `ui.ui_constants`
  - Replace with: `from core.defaults import DEFAULT_STATUS_TIMEOUT`
```

---

## Fix #3: Enhance Phase 1.4 Helper Documentation

### Problem
Proposed helper method lacks documentation of implicit assumptions

### Solution

**Update REFACTORING_PLAN.md Task 1.4 Step 2**

Replace proposed helper code with:

```python
def _find_point_index_at_frame(
    self,
    curve_data: CurveDataList,
    frame: int
) -> int | None:
    """Find the index of a point at the given frame.

    Searches for the first point whose frame number matches the given frame.

    Args:
        curve_data: List of curve points. Each point is a tuple:
                   (frame: int, x: float, y: float, [status: str])
        frame: Frame number to search for

    Returns:
        Point index if found, None otherwise

    Note:
        - Assumes points may be in any order (O(n) complexity)
        - Uses legacy tuple format (point[0] = frame)
        - Future: Consider migrating to CurvePoint dataclass for type safety
        - No validation of point tuple structure (assume well-formed data)

    Example:
        >>> curve_data = [(1, 100.0, 200.0), (3, 150.0, 250.0)]
        >>> idx = self._find_point_index_at_frame(curve_data, 3)
        >>> idx
        1
    """
    for i, point in enumerate(curve_data):
        if len(point) > 0 and point[0] == frame:  # Defensive: check length
            return i
    return None
```

---

## Fix #4: Correct Phase 1.3 Scope Documentation

### Problem
Task 1.3 claims 16 lines duplicated but actual is 8 lines in 1 location

### Solution

**Update REFACTORING_PLAN.md Task 1.3**

Replace:
```markdown
**Current Duplication**:
- `ui/controllers/point_editor_controller.py:139-146` (8 lines)
- `ui/controllers/point_editor_controller.py:193-200` (8 lines)
- Total: 16 lines duplicated
```

With:
```markdown
**Current Usage**:
- `ui/controllers/point_editor_controller.py:192-201` in `_update_point_editor()` (8 lines)
- Total: 8 lines, 1 location
- Note: Still beneficial for extraction to improve readability and single responsibility
```

---

## Fix #5: Add Verification Step for Phase 2.1

### Problem
No documented verification of how many occurrences of old pattern exist

### Solution

**Add new Step 1 to Task 2.1**

```markdown
- [ ] **Step 1**: Find all occurrences of old pattern
  ```bash
  # Search for 4-step pattern (manual count needed, no regex match)
  grep -n "state\.active_curve$" --include="*.py" -r . | \
    grep -v "def active_curve" | grep -v "@property" | grep -v "active_curve_data"
  ```
  - Document locations found
  - Update plan with actual count (estimate: 15+ occurrences across commands and controllers)
```

---

## Summary of Changes to REFACTORING_PLAN.md

### In Task 1.2

**Add to Step 5 after existing grep:**

```markdown
- [ ] **Step 5b**: Verify zoom constants also need migration
  ```bash
  grep -n "from ui\.ui_constants import.*MAX_ZOOM_FACTOR\|MIN_ZOOM_FACTOR" \
    --include="*.py" -r .
  ```
  Expected: Should find 2 files (transform_service.py and transform_core.py)
  These will be updated by Phase 2.2, but constants moved now

- [ ] **Step 5c**: Update `services/ui_service.py`
  - Replace: `from ui.ui_constants import DEFAULT_STATUS_TIMEOUT`
  - With: `from core.defaults import DEFAULT_STATUS_TIMEOUT`
```

### In Task 1.3

**Replace scope section** (as shown in Fix #4)

### In Task 1.4

**Replace proposed code** (as shown in Fix #3)

### In Task 2.1

**Add Step 1** (as shown in Fix #5)

### In Task 2.2

**Replace line 532** in proposed code (as shown in Fix #1)

---

## Implementation Checklist

### Before Phase 1 Execution
- [ ] Read this document completely
- [ ] Review REFACTORING_PLAN.md for accuracy
- [ ] Create updated core/defaults.py locally
- [ ] Test grep commands locally

### During Phase 1.2 Execution
- [ ] Execute Fix #1 Step 1 (create core/defaults.py)
- [ ] Execute Fix #1 Step 2 (update grep command)
- [ ] Execute Fix #2 Step 1 (add DEFAULT_STATUS_TIMEOUT)
- [ ] Execute original Task 1.2 steps 2-4
- [ ] Execute Fix #2 Step 2 (update ui_service.py)
- [ ] Run type checking: `~/.local/bin/uv run basedpyright`
- [ ] Run tests: `~/.local/bin/uv run pytest tests/ -v`

### Before Phase 2 Execution
- [ ] Execute Fix #3 (document assumptions)
- [ ] Execute Fix #4 (correct scope claim)
- [ ] Execute Fix #5 (verify phase 2.1 scope)
- [ ] Execute Fix #1 Step 3 (update Phase 2.2 code)

---

## Validation

**After all fixes applied, core/defaults.py should contain:**
```python
DEFAULT_IMAGE_WIDTH: int = 2048
DEFAULT_IMAGE_HEIGHT: int = 1556
DEFAULT_NUDGE_AMOUNT: float = 1.0
MAX_ZOOM_FACTOR: float = 20.0
MIN_ZOOM_FACTOR: float = 0.1
DEFAULT_STATUS_TIMEOUT: int = 2000
```

**All services should import from core/defaults or ui/ui_constants, never both:**
- ✅ services/transform_service.py: imports from core/defaults
- ✅ services/transform_core.py: imports from core/defaults
- ✅ services/ui_service.py: imports from core/defaults
- ✅ core/commands/shortcut_commands.py: imports from core/defaults

---

**Document Status**: Ready for implementation
**Last Updated**: 2025-10-20
**Review Status**: Approved for Phase 1 execution with fixes

# CurveEditor Refactoring Plan

**Generated**: 2025-10-20
**Last Updated**: 2025-10-20 (Post-Verification)
**Status**: Ready for Execution
**Total Estimated Time**: 3 weeks (1 week critical, 2 weeks optional)

---

## Executive Summary

After comprehensive analysis with verification, we identified **5 major refactoring priorities**:

1. **Dead Code Removal**: ~450 lines of unused `/commands/` directory (403 Python + 50 Markdown)
2. **Layer Violations**: 12 total violations (5 constant imports + 6 color imports + 1 protocol import) - services/core/rendering importing from ui/
3. **Duplicate Code**: 120-140 lines of repeated patterns
4. **Business Logic Location**: 65 lines of geometry in UI controller (should be in service)
5. **God Object**: MainWindow has 101 methods (some extractable)

**Quick Wins** (Week 1): ~500 lines cleaned, 12 layer violations fixed, ~6 hours effort, minimal risk.

---

## Verification Summary

| Finding | Agent Claim | Verified? | Correction |
|---------|-------------|-----------|------------|
| `/commands/` unused | ~450 dead lines (403 Python + 50 Markdown) | ✅ YES | Zero imports from main codebase |
| UI constants in services | 5 constant violations | ✅ YES | Confirmed in transform_service.py:17, shortcut_commands.py, etc. |
| UI colors in rendering | 6 color violations | ✅ YES | Added Task 1.4 to fix (critical finding) |
| Protocol import violation | 1 protocol violation | ✅ YES | StateManager import in rendering_protocols.py (fixed in Task 1.4) |
| Duplicate patterns | 120-140 lines | ✅ YES | Visually confirmed point lookup, spinbox blocking, validation |
| MainWindow 101 methods | God object | ✅ YES | Exact count confirmed |
| Algorithm in CurveViewWidget | 65 lines in widget | ⚠️ LOCATION | Actually in TrackingDisplayController (still wrong layer) |

**Accuracy**: 95% (1 location correction, problem still valid)
**Total Layer Violations**: 12 (5 constants + 6 colors + 1 protocol)

---

## Phase 1: Critical Quick Wins (Week 1)

**Estimated Time**: 6 hours (realistic estimate after verification)
**LOC Impact**: ~500 lines cleaned (450 removed, ~100 added for core/defaults.py + core/colors.py)
**Risk**: Minimal
**Dependencies**: Task 1.4 must complete before Task 1.2 (both fix layer violations)

**Note**: Tasks renumbered in execution order (1.1 → 1.2 → 1.3 → 1.4 → 1.5)

### Task 1.1: Delete Dead Code (15 minutes)

**Objective**: Remove unused `/commands/` directory (~450 lines: 403 Python + 50 Markdown)

**Verification Evidence**:
- `grep "^from commands import"` found 0 files outside `/commands/`
- Only internal self-references exist
- Modern equivalent exists in `/core/commands/`

**Steps**:

- [ ] **Step 1**: Verify no imports (safety check)
  ```bash
  grep -r "^from commands import\|^import commands\." --include="*.py" . | grep -v "^./commands/"
  ```
  Expected: No output

- [ ] **Step 2**: Delete directory
  ```bash
  rm -rf commands/
  ```

- [ ] **Step 3**: Delete deprecated files
  ```bash
  rm -f core/workers/thumbnail_worker.py
  rm -f SetTrackingBwd.py SetTrackingFwd.py SetTrackingFwdBwd.py
  rm -f test_quick_check.py test_zoom_bug_fix.py analyze_handlers.py
  ```

- [ ] **CHECKPOINT 1.1**: Verify clean state
  ```bash
  # Type checking
  ~/.local/bin/uv run basedpyright

  # Linting
  ~/.local/bin/uv run ruff check .

  # Test suite
  ~/.local/bin/uv run pytest tests/ -x -q
  ```
  **Expected**: All pass (no code changes, just deletions)

**Rollback**: `git restore <files>` if any issues

---

### Task 1.2: Fix Layer Violations - Constants (30 minutes)

**Objective**: Move UI constants to `core/defaults.py`, fix imports

**Dependencies**: ⚠️ Must complete Task 1.4 first (fixes 7 additional violations: 6 colors + 1 protocol)

**Current Violations** (5 constant imports):
1. `services/transform_service.py:17` - imports `DEFAULT_IMAGE_HEIGHT, DEFAULT_IMAGE_WIDTH`
2. `services/transform_core.py:27` - imports `DEFAULT_IMAGE_HEIGHT, DEFAULT_IMAGE_WIDTH`
3. `core/commands/shortcut_commands.py:718` - imports `DEFAULT_NUDGE_AMOUNT`
4. `services/ui_service.py:19` - imports `DEFAULT_STATUS_TIMEOUT`
5. `rendering/optimized_curve_renderer.py:26` - imports `GRID_CELL_SIZE, RENDER_PADDING`

**Steps**:

- [ ] **Step 1**: Create `core/defaults.py`
  ```python
  #!/usr/bin/env python
  """
  Application-wide default constants.

  These constants are used by core business logic and services.
  UI-specific constants remain in ui/ui_constants.py.
  """

  # Image dimensions
  DEFAULT_IMAGE_WIDTH: int = 1920
  DEFAULT_IMAGE_HEIGHT: int = 1080

  # Interaction defaults
  DEFAULT_NUDGE_AMOUNT: float = 1.0

  # UI operation defaults
  DEFAULT_STATUS_TIMEOUT: int = 2000  # milliseconds

  # View constraints
  MAX_ZOOM_FACTOR: float = 10.0
  MIN_ZOOM_FACTOR: float = 0.1

  # Rendering defaults
  GRID_CELL_SIZE: int = 100
  RENDER_PADDING: int = 50
  ```

- [ ] **Step 2**: Update `services/transform_service.py` (line 17)
  - Replace: `from ui.ui_constants import DEFAULT_IMAGE_HEIGHT, DEFAULT_IMAGE_WIDTH`
  - With: `from core.defaults import DEFAULT_IMAGE_HEIGHT, DEFAULT_IMAGE_WIDTH`

- [ ] **Step 3**: Update `services/transform_core.py` (line 27)
  - Replace: `from ui.ui_constants import DEFAULT_IMAGE_HEIGHT, DEFAULT_IMAGE_WIDTH`
  - With: `from core.defaults import DEFAULT_IMAGE_HEIGHT, DEFAULT_IMAGE_WIDTH`

- [ ] **Step 4**: Update `core/commands/shortcut_commands.py` (line 718)
  - Replace: `from ui.ui_constants import DEFAULT_NUDGE_AMOUNT`
  - With: `from core.defaults import DEFAULT_NUDGE_AMOUNT`

- [ ] **Step 5**: Update `services/ui_service.py` (line 19)
  - Replace: `from ui.ui_constants import DEFAULT_STATUS_TIMEOUT`
  - With: `from core.defaults import DEFAULT_STATUS_TIMEOUT`

- [ ] **Step 6**: Update `rendering/optimized_curve_renderer.py` (line 26)
  - Replace: `from ui.ui_constants import GRID_CELL_SIZE, RENDER_PADDING`
  - With: `from core.defaults import GRID_CELL_SIZE, RENDER_PADDING`

- [ ] **Step 7**: Verify all constant violations fixed
  ```bash
  # Should only show UI layer files (ui/, not core/ or services/ or rendering/)
  grep -n "from ui\.ui_constants import" --include="*.py" -r core/ services/ rendering/
  ```
  - Expected: No output (all 5 constant violations fixed)

  - Note: Task 1.4 already fixed the 6 color violations and 1 protocol violation

- [ ] **CHECKPOINT 1.2**: Verify layer separation
  ```bash
  # Type checking (ensure imports resolve)
  ~/.local/bin/uv run basedpyright

  # Linting
  ~/.local/bin/uv run ruff check .

  # Test suite (ensure no functionality broken)
  ~/.local/bin/uv run pytest tests/ -x -q

  # Manual smoke test
  ~/.local/bin/uv run python main.py
  # - Load a curve file
  # - Use nudge commands (numpad 2/4/6/8)
  # - Verify transforms work (zoom, pan)
  # - Verify status messages appear with correct timeout
  # - Verify grid rendering displays correctly
  # - Test zoom limits (should cap at 10x max, 0.1x min)
  ```
  **Expected**: All pass, no visual regressions

**Rollback**: `git restore core/defaults.py services/ core/commands/ rendering/` if issues

---

### Task 1.4: Extract Colors to Core (45 minutes) 🔴 CRITICAL

**Objective**: Fix 6 color-related layer violations in rendering/ plus 1 protocol violation

**Current Violations**:
- `rendering/optimized_curve_renderer.py:25` - imports `CurveColors` from `ui.color_constants`
- `rendering/optimized_curve_renderer.py:892` - runtime import of `SPECIAL_COLORS, get_status_color` from `ui.color_manager`
- `rendering/optimized_curve_renderer.py:963` - runtime import of `COLORS_DARK` from `ui.color_manager`
- `rendering/optimized_curve_renderer.py:1014` - runtime import of `get_status_color` from `ui.color_manager`
- `rendering/optimized_curve_renderer.py:1209` - runtime import of `COLORS_DARK` from `ui.color_manager`
- `rendering/optimized_curve_renderer.py:1282` - runtime import of `COLORS_DARK` from `ui.color_manager`

**Analysis**: Method-level imports are workarounds for circular imports (verified by `# pyright: reportImportCycles=false` in renderer). Colors are presentation concerns, but rendering layer needs them. Solution: Extract to core/.

**Steps**:

- [ ] **Step 1**: Create `core/colors.py`
  ```python
  #!/usr/bin/env python
  """
  Application-wide color definitions.

  Colors belong here if used by rendering/ layer.
  UI-specific styling colors remain in ui/color_constants.py.
  """

  from dataclasses import dataclass
  from PySide6.QtGui import QColor


  @dataclass(frozen=True)
  class CurveColors:
      """Color scheme for curve rendering."""

      point: QColor
      selected_point: QColor
      line: QColor
      interpolated: QColor
      keyframe: QColor
      endframe: QColor
      tracked: QColor

      @classmethod
      def default(cls) -> "CurveColors":
          """Create default color scheme."""
          return cls(
              point=QColor(255, 255, 255),
              selected_point=QColor(255, 100, 100),
              line=QColor(200, 200, 200),
              interpolated=QColor(150, 150, 255),
              keyframe=QColor(255, 255, 0),
              endframe=QColor(255, 0, 0),
              tracked=QColor(0, 255, 0),
          )


  # Status-specific colors (used by renderer)
  COLORS_DARK = {
      "normal": QColor(200, 200, 200),
      "interpolated": QColor(100, 100, 255),
      "keyframe": QColor(255, 255, 100),
      "tracked": QColor(100, 255, 100),
      "endframe": QColor(255, 100, 100),
  }

  SPECIAL_COLORS = {
      "selected": QColor(255, 100, 100),
      "hover": QColor(255, 200, 100),
  }


  def get_status_color(status: str, selected: bool = False) -> QColor:
      """Get color for point status.

      Args:
          status: Point status string
          selected: Whether point is selected

      Returns:
          QColor for the status
      """
      if selected:
          return SPECIAL_COLORS["selected"]
      return COLORS_DARK.get(status, COLORS_DARK["normal"])
  ```

- [ ] **Step 2**: Update `rendering/optimized_curve_renderer.py` imports
  - Replace line 25: `from ui.color_constants import CurveColors`
  - With: `from core.colors import CurveColors, COLORS_DARK, SPECIAL_COLORS, get_status_color`
  - Remove all 5 method-level imports (lines 892, 963, 1014, 1209, 1282)

- [ ] **Step 3**: Update `ui/color_constants.py` to re-export from core
  ```python
  # At top of file, add:
  from core.colors import CurveColors, COLORS_DARK, SPECIAL_COLORS, get_status_color

  # Remove duplicate definitions if they exist
  ```

- [ ] **Step 4**: Update `ui/color_manager.py` to re-export from core
  ```python
  # At top of file, add:
  from core.colors import COLORS_DARK, SPECIAL_COLORS, get_status_color

  # Remove duplicate definitions
  ```

- [ ] **Step 5**: Fix Protocol import in `rendering/rendering_protocols.py`
  - Move line 51 import to TYPE_CHECKING block:
  ```python
  # At top of file, in TYPE_CHECKING block:
  if TYPE_CHECKING:
      from PySide6.QtGui import QImage, QPixmap
      from services.transform_service import Transform
      from ui.state_manager import StateManager  # ← Move here

  class MainWindowProtocol(Protocol):
      """Protocol for main window objects."""

      state_manager: "StateManager"  # ← String annotation (was: StateManager without import)
  ```

- [ ] **Step 6**: Verify all color violations fixed
  ```bash
  # Should show NO imports of ui.color_* in rendering/
  grep -n "from ui\.color" rendering/

  # Should show NO imports of StateManager outside TYPE_CHECKING
  grep -A5 "class MainWindowProtocol" rendering/rendering_protocols.py | grep "from ui"
  ```
  - Expected: No output

- [ ] **CHECKPOINT 1.4**: Verify color rendering
  ```bash
  # Type checking
  ~/.local/bin/uv run basedpyright rendering/ core/colors.py

  # Linting
  ~/.local/bin/uv run ruff check rendering/ core/colors.py

  # Rendering tests
  ~/.local/bin/uv run pytest tests/rendering/ -v

  # Manual smoke test
  ~/.local/bin/uv run python main.py
  # - Load a curve file
  # - Verify point colors display correctly (keyframes, interpolated, etc.)
  # - Select points, verify selection color
  # - Verify status colors match expected (no regressions)
  ```
  **Expected**: All pass, colors render identically

**Rollback**: `git restore core/colors.py rendering/ ui/color_constants.py ui/color_manager.py`

**Note**: This task MUST complete before Task 1.2, as both fix layer violations. Order: 1.4 (colors + protocol) → 1.2 (constants).

---

### Task 1.3: Extract Spinbox Helper with QSignalBlocker (1 hour)

**Note**: Verification found 6 additional `blockSignals()` uses in `timeline_controller.py` (lines 217/219, 229/231, 294/296/298/300, 389/391, 412/414). Consider applying this pattern there in Phase 2 or as future enhancement.

**Objective**: Eliminate duplicate spinbox signal blocking code using modern Qt pattern

**Current Duplication**:
- `ui/controllers/point_editor_controller.py:139-146` (8 lines)
- `ui/controllers/point_editor_controller.py:193-200` (8 lines)
- Total: 16 lines duplicated

**Steps**:

- [ ] **Step 1**: Read current implementation
  ```bash
  ~/.local/bin/uv run python -c "
  from pathlib import Path
  lines = Path('ui/controllers/point_editor_controller.py').read_text().splitlines()
  print('\\n'.join(lines[138:147]))
  "
  ```

- [ ] **Step 2**: Add helper method to `PointEditorController` using QSignalBlocker
  - Location: After `_set_spinboxes_enabled()` method
  - Add import at top of file: `from PySide6.QtCore import QSignalBlocker`
  - Add:
  ```python
  def _update_spinboxes_silently(self, x: float, y: float) -> None:
      """Update spinbox values without triggering signals.

      Uses QSignalBlocker for exception-safe signal blocking (RAII pattern).
      Signals are automatically restored when blockers go out of scope.

      Args:
          x: X coordinate value
          y: Y coordinate value
      """
      if not self.main_window.point_x_spinbox or not self.main_window.point_y_spinbox:
          return

      # QSignalBlocker is exception-safe (RAII pattern) - preferred over blockSignals()
      with QSignalBlocker(self.main_window.point_x_spinbox), \
           QSignalBlocker(self.main_window.point_y_spinbox):
          self.main_window.point_x_spinbox.setValue(x)
          self.main_window.point_y_spinbox.setValue(y)
      # Signals automatically restored here, even if setValue() raises exception
  ```

  **Why QSignalBlocker**: Modern Qt best practice (since Qt 5.3). Benefits:
  - Exception-safe (RAII pattern - signals restored even if exception thrown)
  - More Pythonic (context manager pattern)
  - Eliminates manual state management bugs

- [ ] **Step 3**: Replace first occurrence (lines 139-146)
  - Replace 8 lines with: `self._update_spinboxes_silently(x, y)`

- [ ] **Step 4**: Replace second occurrence (lines 193-200)
  - Replace 8 lines with: `self._update_spinboxes_silently(x, y)`

- [ ] **Step 5**: Verify no other occurrences
  ```bash
  grep -n "blockSignals.*point_x_spinbox\|blockSignals.*point_y_spinbox" \
    ui/controllers/point_editor_controller.py
  ```
  **Expected**: Only see the helper method, not in callers

- [ ] **CHECKPOINT 1.3**: Verify point editing
  ```bash
  # Type checking
  ~/.local/bin/uv run basedpyright ui/controllers/point_editor_controller.py

  # Linting
  ~/.local/bin/uv run ruff check ui/controllers/point_editor_controller.py

  # Relevant tests
  ~/.local/bin/uv run pytest tests/ui/controllers/ -k point_editor -v

  # Manual smoke test
  ~/.local/bin/uv run python main.py
  # - Select a point
  # - Verify spinboxes update (no signal loops)
  # - Change spinbox value
  # - Verify point moves
  # - Select multiple points
  # - Verify spinboxes disable
  ```
  **Expected**: All pass, spinbox behavior unchanged

**Rollback**: `git restore ui/controllers/point_editor_controller.py`

---

### Task 1.5: Extract Point Lookup Helper (2 hours)

**Objective**: Eliminate repeated "find point by frame" pattern

**Current Duplication**:
- `core/commands/shortcut_commands.py:187-190` (SetEndframeCommand.execute) - enumerated lookup
- `core/commands/shortcut_commands.py:423-426` (DeleteCurrentFrameKeyframeCommand.execute) - enumerated lookup
- `core/commands/shortcut_commands.py:745-748` (NudgePointsCommand.execute) - enumerated lookup
- **3 enumerated lookups** requiring index (main target)
- **Additional simple existence checks** at lines 149, 388, 702 (can be refactored separately if desired)
- Total: ~12-15 lines duplicated in enumerated pattern

**Steps**:

- [ ] **Step 1**: Verify base class exists
  ```bash
  grep -n "class ShortcutCommand" core/commands/shortcut_command.py
  ```

- [ ] **Step 2**: Add helper to `ShortcutCommand` base class
  - File: `core/commands/shortcut_command.py`
  - Location: After `_get_curve_widget()` method
  - Add:
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

- [ ] **Step 3**: Update `SetEndframeCommand.execute()`
  - Find lines 187-190 (point lookup loop)
  - Replace with:
  ```python
  point_index = self._find_point_index_at_frame(curve_data, context.current_frame)
  ```
  - Remove the loop

- [ ] **Step 4**: Update `DeleteCurrentFrameKeyframeCommand.execute()`
  - Find similar pattern around line 243
  - Replace with same helper call

- [ ] **Step 5**: Update `NudgePointsCommand` (if frame-based)
  - Search for similar pattern
  - Replace with helper call

- [ ] **Step 6**: Search for remaining occurrences
  ```bash
  grep -n "for.*enumerate.*curve_data" core/commands/shortcut_commands.py
  grep -n "point\[0\] == .*frame" core/commands/shortcut_commands.py
  ```
  - Verify only 3 enumerated lookups remain (should all be refactored)
  - Note: Simple existence checks at lines 149, 388, 702 are a different pattern (can be addressed later if desired)

- [ ] **CHECKPOINT 1.5**: Verify shortcut commands
  ```bash
  # Type checking
  ~/.local/bin/uv run basedpyright core/commands/

  # Linting
  ~/.local/bin/uv run ruff check core/commands/

  # Command tests
  ~/.local/bin/uv run pytest tests/core/commands/ -v

  # Integration tests
  ~/.local/bin/uv run pytest tests/ -k "shortcut or endframe or delete" -v

  # Manual smoke test
  ~/.local/bin/uv run python main.py
  # - Load curve with multiple points
  # - Navigate to a frame with a point
  # - Press 'E' (toggle endframe)
  # - Verify point status changes
  # - Press 'D' (delete current frame)
  # - Verify point removed
  # - Use numpad nudge commands
  # - Verify points move correctly
  ```
  **Expected**: All pass, shortcut behavior unchanged

**Rollback**: `git restore core/commands/`

---

### Phase 1 Completion Checkpoint

- [ ] **FINAL CHECKPOINT 1**: Full verification
  ```bash
  # Full type check
  ~/.local/bin/uv run basedpyright

  # Full linting
  ~/.local/bin/uv run ruff check .

  # Full test suite
  ~/.local/bin/uv run pytest tests/ -v --tb=short

  # Coverage check (optional)
  ~/.local/bin/uv run pytest tests/ --cov=. --cov-report=term-missing
  ```

- [ ] **COMMIT**: Phase 1 complete
  ```bash
  git add -A
  git commit -m "refactor(phase1): Remove dead code, fix layer violations, eliminate duplication

  Tasks completed in order:
  - Task 1.1: Delete unused /commands/ directory and deprecated files (450 lines)
  - Task 1.2: Move UI constants to core/defaults.py (fix 5 violations)
  - Task 1.3: Extract _update_spinboxes_silently() with QSignalBlocker (16 lines saved)
  - Task 1.4: Extract colors to core/colors.py (fix 6 color + 1 protocol violations)
  - Task 1.5: Extract _find_point_index_at_frame() helper (12 lines saved)

  Total cleanup: ~500 lines net (450 removed, ~100 added for core files)
  All 12 layer violations fixed (services/rendering no longer import from ui/)
  All tests passing, no functionality changes.

  🤖 Generated with Claude Code

  Co-Authored-By: Claude <noreply@anthropic.com>"
  ```

**Phase 1 Success Criteria**:
- ✅ All type checks pass
- ✅ All lints pass
- ✅ All tests pass
- ✅ Manual smoke tests confirm no regressions
- ✅ ~950 lines of code removed/consolidated
- ✅ No layer violations from services→UI

---

## Phase 2: Consolidation (Week 2)

**Estimated Time**: 1-2 days
**LOC Impact**: ~145 lines
**Risk**: Medium
**Dependencies**: Phase 1 complete

### Task 2.1: Enforce active_curve_data Property (1 day)

**Objective**: Replace 4-step pattern with property-based access

**Current State**:
- Property exists: `ApplicationState.active_curve_data` (lines 1038-1082)
- Old pattern repeated 15+ times:
  ```python
  active = state.active_curve
  if not active:
      return
  data = state.get_curve_data(active)
  if not data:
      return
  ```

**New Pattern**:
  ```python
  if (cd := state.active_curve_data) is None:
      return
  curve_name, data = cd
  ```

**Steps**:

- [ ] **Step 1**: Find all old pattern occurrences
  ```bash
  # Search for the 4-step pattern
  grep -n "state.active_curve" --include="*.py" -r core/ services/ ui/ | \
    grep -v "active_curve_data"
  ```
  - Document all locations (create checklist)

- [ ] **Step 2**: Update `core/commands/shortcut_commands.py`
  - For each command using old pattern:
    - [ ] SetEndframeCommand
    - [ ] DeleteCurrentFrameKeyframeCommand
    - [ ] NudgePointsCommand
    - [ ] (Add others as found)
  - Replace with property pattern

- [ ] **Step 3**: Update controllers (if any use old pattern)
  - Search `ui/controllers/` for old pattern
  - Replace with property pattern

- [ ] **Step 4**: Update services (if any use old pattern)
  - Search `services/` for old pattern
  - Replace with property pattern

- [ ] **CHECKPOINT 2.1**: Verify pattern consistency
  ```bash
  # Type checking
  ~/.local/bin/uv run basedpyright

  # Verify old pattern is gone (should find only the property definition)
  grep -n "state.active_curve$" --include="*.py" -r . | \
    grep -v "def active_curve" | grep -v "ApplicationState/active_curve"

  # Test suite
  ~/.local/bin/uv run pytest tests/ -v

  # Manual smoke test
  ~/.local/bin/uv run python main.py
  # - Load multi-curve file
  # - Switch active curve
  # - Use commands (E, D, numpad)
  # - Verify commands work on correct curve
  ```
  **Expected**: All pass, ~80 lines consolidated

**Rollback**: `git restore core/ services/ ui/`

---

### Task 2.2: Extract Geometry to TransformService (2 hours)

**Objective**: Move bounding box/centering logic from UI controller to service

**Dependencies**: Requires Task 1.2 completion (MAX/MIN_ZOOM_FACTOR moved to core/defaults.py)

**Note on Service Responsibility**: This extends TransformService scope to include "viewport fitting calculations" alongside coordinate transformations. While this slightly expands SRP, it's pragmatic for a single-user application. Future consideration: If TransformService grows beyond 5-6 methods, consider extracting to dedicated `core/geometry.py` module.

**Current Location**:
- `ui/controllers/tracking_display_controller.py:402-467` (65 lines)
- Contains: bounding box calculation, zoom calculation, centering logic

**Target Location**:
- `services/transform_service.py` (new method)
- Update TransformService docstring to document viewport fitting as in-scope

**Steps**:

- [ ] **Step 1**: Read current implementation
  ```bash
  ~/.local/bin/uv run python -c "
  from pathlib import Path
  lines = Path('ui/controllers/tracking_display_controller.py').read_text().splitlines()
  print('\\n'.join(lines[401:468]))
  "
  ```

- [ ] **Step 2**: Add method to `TransformService`
  - File: `services/transform_service.py`
  - Add:
  ```python
  def calculate_fit_bounds(
      self,
      points: list[tuple[float, float]],
      viewport_width: int,
      viewport_height: int,
      padding_factor: float = 1.2
  ) -> tuple[float, float, float]:
      """Calculate optimal zoom and center for fitting points in viewport.

      Args:
          points: List of (x, y) coordinate tuples
          viewport_width: Width of viewport in pixels
          viewport_height: Height of viewport in pixels
          padding_factor: Extra space around points (1.2 = 20% padding)

      Returns:
          Tuple of (center_x, center_y, optimal_zoom)
      """
      if not points:
          return (0.0, 0.0, 1.0)

      # Calculate bounding box
      x_coords = [p[0] for p in points]
      y_coords = [p[1] for p in points]

      min_x, max_x = min(x_coords), max(x_coords)
      min_y, max_y = min(y_coords), max(y_coords)

      # Calculate center point
      center_x = (min_x + max_x) / 2
      center_y = (min_y + max_y) / 2

      # Calculate required zoom to fit all points with padding
      width_needed = (max_x - min_x) * padding_factor
      height_needed = (max_y - min_y) * padding_factor

      if width_needed > 0 and height_needed > 0:
          from core.defaults import MAX_ZOOM_FACTOR, MIN_ZOOM_FACTOR

          zoom_x = viewport_width / width_needed
          zoom_y = viewport_height / height_needed
          optimal_zoom = min(zoom_x, zoom_y, MAX_ZOOM_FACTOR)
          optimal_zoom = max(MIN_ZOOM_FACTOR, optimal_zoom)
      else:
          optimal_zoom = 1.0

      return (center_x, center_y, optimal_zoom)
  ```

- [ ] **Step 3**: Update `TrackingDisplayController.center_on_selected_curves()`
  - Replace bounding box/zoom calculation (lines ~438-460)
  - With:
  ```python
  # Collect points (keep existing loop)
  all_points: list[tuple[float, float]] = []
  # ... existing point collection code ...

  # Calculate fit bounds using service
  from services import get_transform_service
  transform_service = get_transform_service()

  center_x, center_y, optimal_zoom = transform_service.calculate_fit_bounds(
      all_points,
      widget.width(),
      widget.height(),
      padding_factor=1.2
  )

  # Apply zoom and center
  widget.zoom_factor = optimal_zoom
  widget._center_view_on_point(center_x, center_y)
  ```

- [ ] **Step 4**: Update fallback in `CurveViewWidget.center_on_selected_curves()`
  - Apply same refactor to test fallback code
  - Should mirror controller change

- [ ] **CHECKPOINT 2.2**: Verify centering behavior
  ```bash
  # Type checking
  ~/.local/bin/uv run basedpyright services/transform_service.py \
    ui/controllers/tracking_display_controller.py

  # Service tests (if any)
  ~/.local/bin/uv run pytest tests/services/ -k transform -v

  # Integration tests
  ~/.local/bin/uv run pytest tests/ -k "center or fit" -v

  # Manual smoke test
  ~/.local/bin/uv run python main.py
  # - Load multi-curve file
  # - Select multiple curves
  # - Press 'C' (center on selection)
  # - Verify curves centered and zoomed appropriately
  # - Try with different numbers of curves
  # - Verify consistent behavior
  ```
  **Expected**: All pass, centering behavior unchanged, 65 lines moved to service

**Rollback**: `git restore services/ ui/`

---

### Phase 2 Completion Checkpoint

- [ ] **FINAL CHECKPOINT 2**: Full verification
  ```bash
  # Full type check
  ~/.local/bin/uv run basedpyright

  # Full linting
  ~/.local/bin/uv run ruff check .

  # Full test suite
  ~/.local/bin/uv run pytest tests/ -v --tb=short

  # Integration test (critical paths)
  ~/.local/bin/uv run pytest tests/ -k "integration" -v
  ```

- [ ] **COMMIT**: Phase 2 complete
  ```bash
  git add -A
  git commit -m "refactor(phase2): Consolidate patterns, extract geometry service

  - Enforce active_curve_data property usage (~80 lines consolidated)
  - Move bounding box/centering logic to TransformService (65 lines)
  - Improve layer separation (UI controllers use service for geometry)

  Total consolidation: ~145 lines
  All tests passing, behavior preserved.

  🤖 Generated with Claude Code

  Co-Authored-By: Claude <noreply@anthropic.com>"
  ```

**Phase 2 Success Criteria**:
- ✅ All type checks pass
- ✅ All lints pass
- ✅ All tests pass
- ✅ Manual centering tests confirm correct behavior
- ✅ ~145 lines consolidated
- ✅ Geometry logic moved from UI to service layer

---

## Phase 3: Strategic (Optional - Week 3+)

**Estimated Time**: 1 week
**LOC Impact**: Variable
**Risk**: High
**Dependencies**: Phases 1-2 complete, stable for 1+ week

### Task 3.1: MainWindow Method Extraction (1 week)

**Objective**: Reduce MainWindow from 101 methods to ~60-70

**Analysis Required**:
- Review all 101 methods
- Identify template/pattern methods
- Determine which can move to controllers
- Evaluate risk/benefit for each

**Decision Point**: Only proceed if:
- [ ] Phases 1-2 have been stable for 1+ week
- [ ] No regressions observed in production use
- [ ] Clear patterns identified for extraction
- [ ] Time available for careful refactoring

**NOT PLANNED IN DETAIL** - Requires further analysis and design discussion.

**If proceeding, follow this general pattern**:
1. Create detailed extraction plan per controller
2. Extract one method at a time
3. Run full test suite after each extraction
4. Commit frequently (per-method or per-controller)
5. Be prepared to pause/rollback if issues arise

---

## Testing Strategy

### Automated Testing

**Per-Task Testing** (after each task):
```bash
# Type checking (specific files)
~/.local/bin/uv run basedpyright <changed_files>

# Linting (specific files)
~/.local/bin/uv run ruff check <changed_files>

# Relevant unit tests
~/.local/bin/uv run pytest tests/ -k <relevant_keyword> -v
```

**Checkpoint Testing** (after each checkpoint):
```bash
# Full type checking
~/.local/bin/uv run basedpyright

# Full linting
~/.local/bin/uv run ruff check .

# Full test suite
~/.local/bin/uv run pytest tests/ -v --tb=short

# Coverage report (optional, for confidence)
~/.local/bin/uv run pytest tests/ --cov=. --cov-report=term-missing
```

### Manual Smoke Testing

**After each phase**:

1. **Basic Operations**:
   - [ ] Launch application
   - [ ] Load a curve file (.txt)
   - [ ] Load image sequence
   - [ ] Navigate frames (arrows, slider, spinbox)
   - [ ] Verify curve renders correctly

2. **Point Operations**:
   - [ ] Select single point
   - [ ] Select multiple points (drag box)
   - [ ] Move points (drag, spinboxes)
   - [ ] Delete points (Delete key)
   - [ ] Add points (double-click)

3. **Shortcuts** (Phase 1 critical):
   - [ ] 'E' - Toggle endframe
   - [ ] 'D' - Delete current frame keyframe
   - [ ] Numpad 2/4/6/8 - Nudge points
   - [ ] Ctrl+Z/Y - Undo/Redo
   - [ ] Ctrl+A - Select all
   - [ ] Escape - Deselect

4. **View Operations**:
   - [ ] Mouse wheel - Zoom
   - [ ] Middle-drag - Pan
   - [ ] 'F' - Fit to view
   - [ ] 'C' - Center on selection (Phase 2 critical)

5. **Multi-Curve** (Phase 2 critical):
   - [ ] Load multi-curve file
   - [ ] Switch active curve (timeline tabs)
   - [ ] Commands work on correct curve
   - [ ] Center on multiple curves

### Regression Test Checklist

If ANY of these fail during manual testing, STOP and investigate:

- [ ] Application crashes on startup
- [ ] Cannot load curve files
- [ ] Cannot load image sequences
- [ ] Points don't render
- [ ] Commands don't execute (E, D, nudge)
- [ ] Undo/Redo broken
- [ ] Selection broken
- [ ] Zoom/Pan broken
- [ ] Active curve switching broken

---

## Rollback Procedures

### Per-Task Rollback

If a task fails verification:
```bash
# Restore specific files
git restore <changed_files>

# Or restore entire directory
git restore <directory>/
```

### Per-Phase Rollback

If a phase checkpoint fails:
```bash
# Restore all changes since last commit
git restore .

# Or reset to last good commit
git reset --hard HEAD~1  # If you committed bad changes
```

### Emergency Rollback

If production issues discovered after phase complete:
```bash
# Create hotfix branch from last stable point
git checkout -b hotfix/rollback-phase-X <last_stable_commit>

# OR revert the phase commit
git revert <phase_commit_hash>

# Test and commit
```

---

## Success Metrics

### Phase 1 Metrics
- **Code Reduction**: ~500 lines net reduction (450 removed, ~100 added for core/defaults.py + core/colors.py)
- **Architecture**: Zero layer violations (12 violations fixed: 5 constants + 6 colors + 1 protocol)
- **Duplication**: ~28 lines of duplicate code eliminated (16 spinbox + 12 point lookup enumerated pattern)
- **Test Coverage**: No coverage reduction
- **Type Safety**: Zero new type errors
- **Time**: ~6 hours (realistic estimate: 15m + 30m + 1h + 45m + 2h + checkpoints)

### Phase 2 Metrics
- **Code Reduction**: ~145 lines consolidated
- **Architecture**: Geometry logic in service layer (not UI)
- **Pattern Consistency**: 100% usage of `active_curve_data` property
- **Test Coverage**: No coverage reduction
- **Type Safety**: Zero new type errors
- **Time**: <2 days actual vs. 1-2 days estimated

### Overall Success
- **Total LOC Impact**: ~1100 lines (10% of codebase)
- **Zero Regressions**: All existing functionality preserved
- **Improved Maintainability**: Reduced duplication, better architecture
- **Team Velocity**: Faster feature development (cleaner patterns)

---

## Risk Mitigation

### Identified Risks

1. **Test Coverage Gaps**: Some code paths may lack tests
   - **Mitigation**: Comprehensive manual smoke testing per phase
   - **Severity**: Medium

2. **Hidden Dependencies**: Code may have undocumented dependencies
   - **Mitigation**: Thorough grep searches before each change
   - **Severity**: Low (small, single-user codebase)

3. **Type Checking False Positives**: basedpyright may miss runtime issues
   - **Mitigation**: Manual testing supplements type checking
   - **Severity**: Low

4. **Refactoring Fatigue**: 3-week effort could introduce mistakes
   - **Mitigation**: Frequent commits, clear rollback points, optional Phase 3
   - **Severity**: Medium

### Risk Response Plan

**If automated tests fail**:
1. Read failure message carefully
2. Check if test needs updating (expected for refactors)
3. If functionality broken, rollback task immediately
4. Investigate, fix, re-attempt

**If manual tests fail**:
1. Document exact reproduction steps
2. Rollback to last checkpoint
3. Investigate in isolation (separate branch)
4. Fix and re-integrate carefully

**If production issues found**:
1. Assess severity (crash vs. minor UX issue)
2. If severe: emergency rollback (see procedures above)
3. If minor: log issue, continue, fix in follow-up
4. Always prioritize stability over perfection

---

## Timeline

### Week 1: Phase 1 (Critical Path)
- **Monday AM**: Task 1.1 (delete dead code) - 15 min
- **Monday AM**: Task 1.2 (constants to core/) - 30 min
- **Monday PM**: Task 1.3 (spinbox QSignalBlocker) - 1 hour
- **Tuesday AM**: Task 1.4 (colors to core/) - 45 min
- **Tuesday PM**: Task 1.5 (point lookup helper) - 2 hours
- **Wednesday**: Final Checkpoint 1, commit, documentation - 1 hour
- **Thursday-Friday**: Buffer/additional testing

**Total**: ~6 hours + 2-day buffer

**Task Execution Order**: 1.1 → 1.2 → 1.3 → 1.4 → 1.5 (colors before constants dependency)

### Week 2: Phase 2 (Consolidation)
- **Monday-Tuesday**: Task 2.1 (active_curve_data) - 1 day
- **Wednesday**: Task 2.2 (geometry extraction) - 2 hours
- **Thursday**: Final Checkpoint 2, commit - 30 min
- **Friday**: Buffer/monitoring

**Total**: 1.5 days + 0.5 day buffer

### Week 3+: Phase 3 (Optional)
- **Decision Point**: End of Week 2
- **If Proceed**: 1 week careful extraction
- **If Skip**: Monitor stability, move to next project

---

## Appendix A: File Inventory

### Files Modified (Phase 1)
- `core/defaults.py` (NEW) - Task 1.2
- `core/colors.py` (NEW) - Task 1.4
- `services/transform_service.py` - Task 1.2
- `services/transform_core.py` - Task 1.2
- `services/ui_service.py` - Task 1.2
- `rendering/optimized_curve_renderer.py` - Task 1.2, 1.4
- `rendering/rendering_protocols.py` - Task 1.4
- `ui/color_constants.py` - Task 1.4 (re-exports)
- `ui/color_manager.py` - Task 1.4 (re-exports)
- `core/commands/shortcut_command.py` - Task 1.5
- `core/commands/shortcut_commands.py` - Task 1.2, 1.5
- `ui/controllers/point_editor_controller.py` - Task 1.3

### Files Deleted (Phase 1)
- `commands/` (directory, 884 lines)
- `core/workers/thumbnail_worker.py`
- `SetTrackingBwd.py`
- `SetTrackingFwd.py`
- `SetTrackingFwdBwd.py`
- `test_quick_check.py`
- `test_zoom_bug_fix.py`
- `analyze_handlers.py`

### Files Modified (Phase 2)
- `services/transform_service.py` (new method)
- `ui/controllers/tracking_display_controller.py`
- `ui/curve_view_widget.py` (fallback path)
- Multiple files using old `active_curve` pattern (TBD during execution)

### Files Modified (Phase 3)
- TBD (requires further analysis)

---

## Appendix B: Command Reference

### Quick Commands

```bash
# Type check entire project
~/.local/bin/uv run basedpyright

# Type check specific file
~/.local/bin/uv run basedpyright path/to/file.py

# Lint entire project
~/.local/bin/uv run ruff check .

# Lint with auto-fix
~/.local/bin/uv run ruff check . --fix

# Run all tests
~/.local/bin/uv run pytest tests/ -v

# Run tests with keyword filter
~/.local/bin/uv run pytest tests/ -k "shortcut or endframe" -v

# Run tests with coverage
~/.local/bin/uv run pytest tests/ --cov=. --cov-report=term-missing

# Run tests, stop on first failure
~/.local/bin/uv run pytest tests/ -x -q

# Search for pattern
grep -rn "pattern" --include="*.py" path/

# Count lines
wc -l path/to/file.py

# Launch application
~/.local/bin/uv run python main.py
```

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2025-10-20 | 1.0 | Initial plan after verification analysis |
| 2025-10-20 | 1.1 | Post-verification amendments: (1) Renumbered tasks in execution order (1.1→1.2→1.3→1.4→1.5), (2) Updated timeline 4.5h→6h, (3) Clarified point lookup count (3 enumerated, not 5), (4) Added notes on additional blockSignals() uses, (5) Added TransformService scope documentation, (6) Updated all cross-references |

---

**Next Step**: Review this amended plan, then begin Phase 1, Task 1.1 when ready.

**Key Changes from v1.0**:
- Tasks renumbered in execution order for clarity
- Realistic 6-hour timeline (was 4.5 hours)
- Task 1.4 (colors) now executes BEFORE Task 1.2 (constants) due to dependency
- Point lookup helper targets 3 enumerated lookups (verified accurate)
- Added future enhancement notes for timeline_controller.py blockSignals()
- Added TransformService scope expansion documentation

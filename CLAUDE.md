# CurveEditor Development Guide

Quick reference for CurveEditor - a Python/PySide6 application for editing animation curves with VFX workflow tools.

## Project Scope

**Personal VFX Tool**: This is a single-user desktop application for personal VFX workflow needs. While it follows professional coding standards (type safety, testing, clean architecture), it optimizes for maintainability and pragmatic solutions over enterprise concerns.

**What still matters:**
- **Code quality**: Type safety, readable code, proper architecture (future-you deserves good code)
- **Testing**: Comprehensive tests prevent regressions and enable confident refactoring
- **Performance**: Responsive UI, efficient algorithms (this is interactive software)
- **Maintainability**: Clear patterns, good documentation, low technical debt
- **Robustness**: Handle corrupt files, validate inputs, graceful error recovery

**Not applicable (single-user desktop context):**
- **Enterprise security**: No authentication, authorization, or adversarial threat modeling
- **Scale engineering**: No distributed systems, cloud deployment, or ops infrastructure
- **Multi-user patterns**: No concurrent access, locking, or team coordination features
- **Runtime extensibility**: No plugin systems or runtime module loading

**Decision-making guidance**: When choosing between solutions, prefer:
- Simple and working over theoretically perfect
- Pragmatic over defensive (e.g., trust local filesystem, not untrusted network input)
- Readable over clever (but don't sacrifice performance where it matters)
- "Good enough for single-user" over "scales to enterprise"

**Professional-quality code for a personal tool, not enterprise software.**

## Refactoring Status (October 2025)

**Phase 1 Complete:** Quick wins delivered (docstrings, cleanup, nesting reduction)
**Phase 2 In Progress:** Protocol foundation established, ongoing controller migration

### Protocol Adoption Status

The project uses protocol-based typing for loose coupling and type safety:

**Protocols Defined** (`protocols/ui.py`):
- ✅ 16 protocols fully defined (QLabelProtocol, ServicesProtocol, FileOperationsProtocol, etc.)
- ✅ StateManagerProtocol extended with 4 properties (zoom_level, pan_offset, smoothing_window_size, smoothing_filter_type)
- ✅ MainWindowProtocol complete (226 lines, 80+ members)
- ✅ 0 type errors in protocol definitions

**Controller Migration Status** (`ui/controllers/`):
- ✅ ActionHandlerController: Uses StateManagerProtocol, MainWindowProtocol (100% migrated)
- ⚠️ 7 other controllers: Still use concrete types (ViewManagementController, TimelineController, etc.)

**Current Approach (Pragmatic Migration)**
Protocol adoption proved architecturally sound. Remaining 7 controllers use concrete types:
- **Migration effort**: 3-4 hours to add 15-20 missing UI widget attributes to MainWindowProtocol
- **Current priority**: Test coverage and functional improvements provide higher value
- **Personal tool context**: Concrete types acceptable (no team coordination needs)

ActionHandlerController establishes the pattern. Controllers will adopt protocols as they're refactored.

### Controller Tests Status

**Coverage:** 12/14 controllers tested (86%), 220+ tests, 100% pass rate

**October 2025 Update:** Created comprehensive test suites for 4 high-priority components (TrackingDisplayController, TrackingSelectionController, ViewCameraController, CommandManager). Test suite discovered and helped fix cache invalidation bug in ViewCameraController.pan().

**Remaining:** base_tracking_controller (abstract base), progressive_disclosure_controller (lower priority)

### Refactoring Metrics

**Key Metrics:**
- Quality: 62 → 72/100 (+10 points)
- Type errors: 47 → 0 (maintained)
- Test coverage: 3,065 → 3,175 tests (+110 tests)
- Controller coverage: 57% → 86%

**October 2025:** Completed high-priority test gap closure (+112 controller tests), fixed 2 production bugs (pan_offset sync, cache invalidation), documented 10+ methods, removed 80 lines redundant code, aligned StateManagerProtocol with migration.

**Next:** Protocol migration for remaining controllers, functional improvements, feature development

---

## Code Quality Standards

1. **Type Safety First**: Use type hints, prefer `None` checks over `hasattr()`
2. **Service Architecture**: 4 services (Data, Interaction, Transform, UI)
3. **Single Source of Truth**: ApplicationState for all data
4. **Protocol Interfaces**: Type-safe duck-typing via protocols
5. **Component Container Pattern**: Access UI via `self.ui.<group>.<widget>`

## Architecture Overview

### Layers
```
UI Layer          → MainWindow, CurveViewWidget, Controllers
Service Layer     → DataService, InteractionService, TransformService, UIService
State Layer       → ApplicationState (single source of truth)
Core Models       → CurvePoint, PointCollection, Commands
```

### 4 Services

1. **TransformService**: Coordinate transformations, view state
2. **DataService**: Data operations, file I/O, image management
3. **InteractionService**: User interactions, point manipulation, command history
4. **UIService**: UI operations, dialogs, status updates

```python
from services import get_data_service, get_interaction_service, get_transform_service, get_ui_service
```

### Multi-Curve Support

InteractionService supports multi-curve operations with optional `curve_name` parameter:

```python
service = get_interaction_service()

# Search modes
result = service.find_point_at(view, x, y, mode="active")      # Single curve
result = service.find_point_at(view, x, y, mode="all_visible") # All curves

# Operations default to active curve when curve_name=None
service.select_all_points(view, main_window)                   # Active curve
service.select_all_points(view, main_window, curve_name="Track1")  # Specific curve
```

## State Management

**ApplicationState** is the single source of truth for **application data**.

```python
from stores.application_state import get_application_state

state = get_application_state()

# Explicit multi-curve API (one way to do things)
active = state.active_curve
if active:
    # Curve data
    state.set_curve_data(active, curve_data)
    data = state.get_curve_data(active)

    # Original data (for undo)
    state.set_original_data(active, original_data)
    original = state.get_original_data(active)

# Image sequence
state.set_image_files(files, directory="/path/to/images")
files = state.get_image_files()

# Frame state
state.set_frame(42)
frame = state.get_current_frame()

# Subscribe to changes
state.curves_changed.connect(self._on_data_changed)
state.image_sequence_changed.connect(self._on_images_changed)

# Batch operations (prevent signal storms)
with state.batch_updates():
    state.set_curve_data("Track1", data1)
    state.set_curve_data("Track2", data2)
    # Signals emitted once at end
```

### Focused Protocols for ApplicationState (Interface Segregation)

**Phase 1 Addition** (October 2025): Use minimal protocols instead of depending on full ApplicationState.

```python
from protocols.state import FrameProvider, CurveDataProvider, SelectionProvider

# ✅ RECOMMENDED - Depend on minimal protocol
class FrameDisplay:
    def __init__(self, frames: FrameProvider):
        self._frames = frames  # Only needs current_frame property

    def show_frame(self):
        print(f"Frame: {self._frames.current_frame}")

# ✅ Test with 1-line mock (98% simpler than mocking ApplicationState)
class MockFrameProvider:
    current_frame: int = 42

test_frame_display(MockFrameProvider())  # Done!

# ❌ OLD WAY - Depend on full ApplicationState (50+ methods)
class FrameDisplay:
    def __init__(self, state: ApplicationState):
        self._state = state  # Depends on 50+ methods for 1 property!
```

**Available Protocols** (see `protocols/state.py` for details):
- `FrameProvider` - Current frame access only
- `CurveDataProvider` - Read-only curve data
- `CurveDataModifier` - Write curve data
- `SelectionProvider` - Read-only selection
- `SelectionModifier` - Write selection
- `ImageSequenceProvider` - Image sequence info
- Composite: `CurveState`, `SelectionState`, `FrameAndCurveProvider`

**Benefits**:
- **Test mocks**: 1-3 methods instead of 50+ methods (98% reduction)
- **Clear dependencies**: Protocol name documents exact needs
- **Decoupling**: Changes to unrelated features don't affect clients
- **Flexibility**: Easy to create lightweight test implementations

**Compatibility**: ApplicationState automatically satisfies all protocols via structural typing (duck typing). No code changes needed to existing ApplicationState.

---

**StateManager** handles **UI preferences and view state**.

```python
from ui.state_manager import StateManager

# View state
state_manager.zoom_level = 2.0
state_manager.pan_offset = (100, 50)

# Tool state
state_manager.current_tool = "smooth"

# Window state
state_manager.window_position = (100, 100)
state_manager.is_fullscreen = True

# History UI state
state_manager.set_history_state(can_undo=True, can_redo=False)

# Subscribe to UI state changes
state_manager.view_state_changed.connect(self._on_view_changed)
state_manager.undo_state_changed.connect(self._update_undo_button)
state_manager.tool_state_changed.connect(self._update_tool_selection)
```

**Migration Complete** (October 2025):
- StateManager Simplified Migration completed in 4 phases
- Result: Single source of truth, one API, zero technical debt
- ApplicationState owns all data, StateManager owns all UI state

**⚠️ StateManager has NO data access methods**:
```python
# ❌ WRONG - These don't exist
state_manager.track_data
state_manager.image_files
state_manager.total_frames

# ✅ CORRECT - Use ApplicationState directly
state = get_application_state()
active = state.active_curve
if active:
    data = state.get_curve_data(active)
    state.set_curve_data(active, new_data)
```

### Active Curve Data Pattern

**Use `active_curve_data` property for safe access** (Phase 4 Task 4.4):

```python
from stores.application_state import get_application_state

state = get_application_state()

# ✅ GOOD - Property-based (modern pattern, Phase 4+)
if (curve_data := state.active_curve_data) is None:
    return
curve_name, data = curve_data
# Use curve_name and data safely

# ❌ BAD - Manual 4-step pattern (pre-Phase 4, avoid in new code)
active = state.active_curve
if not active:
    return
data = state.get_curve_data(active)
if not data:
    return
# Use active and data
```

**Pattern Established**: Complex state retrieval patterns should use `@property` or service methods, not be repeated across business logic. This:
- **Reduces code**: 4 lines → 2 lines (50% reduction)
- **Improves discoverability**: Property visible in IDE autocomplete
- **Ensures consistency**: One way to do it
- **Type safety**: Single source of truth for return type

**When to use**:
- Command `execute()`/`undo()` methods needing curve data
- Service operations requiring active curve + data
- UI event handlers that modify curve data
- Any code path requiring both curve name AND curve data

**When NOT to use**:
- Only need curve name (use `state.active_curve` directly)
- Only need selection (use `state.get_selection(curve_name)`)
- Only need to check if active curve exists (partial pattern is fine)

**Command Pattern: Automatic Target Storage** (Phase 1 Refactoring - October 2025):

`CurveDataCommand` base class **automatically** stores target curve when you call `_get_active_curve_data()`:

```python
class SmoothCommand(CurveDataCommand):
    def __init__(self, ...):
        super().__init__(...)
        # self._target_curve inherited from base (stored automatically)

    def execute(self, main_window: MainWindowProtocol) -> bool:
        # Get active curve - AUTOMATIC target storage!
        if (result := self._get_active_curve_data()) is None:
            return False
        curve_name, data = result
        # self._target_curve is now set automatically (no manual storage needed)

        # ... execute logic

    def undo(self, main_window: MainWindowProtocol) -> bool:
        # ✅ Use stored target (set automatically during execute)
        if not self._target_curve:
            return False
        state.set_curve_data(self._target_curve, self._old_data)

    def redo(self, main_window: MainWindowProtocol) -> bool:
        # ✅ Use stored target (NOT current active)
        if not self._target_curve:
            return False
        state.set_curve_data(self._target_curve, self._new_data)
```

**Why This Matters**: Undo/redo must target the curve where command executed, not current active curve. Automatic storage eliminates Bug #2 (forgetting to store target manually).

**Key Benefit**: Impossible to forget target storage - it's automatic when you call `_get_active_curve_data()`.

### Data Access Patterns (Architectural Guidance)

**Prefer direct ApplicationState access in MainWindow and services:**

```python
# ✅ RECOMMENDED - Direct ApplicationState access (MainWindow pattern)
from stores.application_state import get_application_state

app_state = get_application_state()
if (cd := app_state.active_curve_data) is None:
    return []  # No active curve
curve_name, curve_data = cd
# Use curve_name and curve_data
```

**Convenience pattern acceptable for other UI components:**

```python
# ⚠️ ACCEPTABLE - For UI components outside MainWindow
curve_data = self.curve_view.curve_data  # Delegates to ApplicationState internally
```

**Why prefer direct access in MainWindow?**
- MainWindow is the central coordinator - should use canonical patterns
- More explicit about data flow and single source of truth
- Consistent with refactored methods (e.g., `_get_current_point_count_and_bounds`)
- Sets clear example for future code
- Direct access to ApplicationState eliminates unnecessary indirection

**Implementation Note**: `CurveViewWidget.curve_data` is a convenience wrapper that delegates to ApplicationState. It's not a separate data source, but direct access is preferred in MainWindow for architectural clarity.


## Command Base Class Pattern

**Use `CurveDataCommand` base class for curve-modifying commands** (Phase KISS/DRY Cleanup):

All commands that modify curve data should inherit from `CurveDataCommand` to leverage:
- Automatic active curve validation and retrieval
- Standardized error handling
- Target curve storage for correct undo/redo
- Common helper methods for point manipulation

```python
from core.commands.curve_commands import CurveDataCommand

class MyCustomCommand(CurveDataCommand):
    def __init__(self, description: str, ...):
        super().__init__(description)
        # self._target_curve inherited from base

    def execute(self, main_window: MainWindowProtocol) -> bool:
        """Execute command with base class helpers."""
        def _execute_operation() -> bool:
            # Validate and get active curve (AUTOMATIC target storage)
            if (result := self._get_active_curve_data()) is None:
                return False
            curve_name, curve_data = result
            # self._target_curve is now set automatically!

            # ... perform operation

            return True

        # Automatic error handling
        return self._safe_execute("executing", _execute_operation)

    def undo(self, main_window: MainWindowProtocol) -> bool:
        """Undo uses stored target curve."""
        def _undo_operation() -> bool:
            if not self._target_curve:
                logger.error("Missing target curve for undo")
                return False

            # Restore using stored target
            app_state = get_application_state()
            app_state.set_curve_data(self._target_curve, self._old_data)
            return True

        return self._safe_execute("undoing", _undo_operation)

    def redo(self, main_window: MainWindowProtocol) -> bool:
        """Redo uses stored target curve (do NOT call execute())."""
        def _redo_operation() -> bool:
            if not self._target_curve:
                logger.error("Missing target curve for redo")
                return False

            # Apply using stored target (NOT current active curve)
            app_state = get_application_state()
            app_state.set_curve_data(self._target_curve, self._new_data)
            return True

        return self._safe_execute("redoing", _redo_operation)
```

**Available base class methods**:
- `_get_active_curve_data() -> tuple[str, CurveDataList] | None`: Validates and retrieves active curve, **automatically stores `self._target_curve` for undo/redo** (Phase 1 improvement)
- `_safe_execute(name: str, operation) -> bool`: Wraps operation in try/except with logging
- `_update_point_position(point, new_pos) -> LegacyPointData`: Updates x/y while preserving frame/status
- `_update_point_at_index(data, idx, updater) -> bool`: Safe indexed update with bounds check

**When to use**:
- Any command that modifies curve points
- Commands that need undo/redo support
- Commands requiring active curve validation

**When NOT to use**:
- Shortcut commands (use `ShortcutCommand` base if needed)
- Commands that don't modify curve data
- Commands that operate on multiple curves simultaneously

## Core Data Models

```python
from core.models import CurvePoint, PointCollection, PointStatus

@dataclass(frozen=True)
class CurvePoint:
    frame: int
    x: float
    y: float
    status: PointStatus = PointStatus.NORMAL

class PointStatus(Enum):
    NORMAL, INTERPOLATED, KEYFRAME, TRACKED, ENDFRAME
```

## Terminology

**Critical Distinction** (matches 3DEqualizer):
- **"Curve"** = One tracking point's trajectory over time (e.g., "pp56_TM_138G")
- **"Point"** = Position at ONE frame within a trajectory (e.g., frame 42 in "pp56_TM_138G")
- **"Multiple Curves"** = Multiple independent tracking points

## Gap Handling

**Gaps** represent inactive segments in a curve trajectory, created by marking points with `PointStatus.ENDFRAME`.

**How Gaps Work:**
- `point.status = PointStatus.ENDFRAME` creates segment boundary
- Frames after ENDFRAME (until next KEYFRAME) become "inactive"
- Inactive segments return held position (ENDFRAME coordinates)
- Active segments interpolate normally between keyframes

**Key Files:**
- `core/curve_segments.py` - `SegmentedCurve` breaks curves into active/inactive segments
- `services/data_service.py:get_position_at_frame()` - Returns held positions during gaps
- `rendering/optimized_curve_renderer.py` - Solid lines for active, dashed for gap segments

**Visual Display:**
- Active segments: Solid lines, interpolated positions
- Gap segments: Dashed lines, held ENDFRAME position
- Timeline colors: Cyan (ENDFRAME), dark gray (inactive), light blue (STARTFRAME)

**Multi-Curve:**
- Each curve maintains independent segment structure
- Gaps in one curve don't affect others

```python
# Gap creation (E key shortcut)
point.status = PointStatus.ENDFRAME  # Creates gap at this frame

# Position retrieval handles gaps automatically
data_service = get_data_service()
x, y = data_service.get_position_at_frame(curve_name, frame)  # Returns held position in gaps
```

**Design**: Gaps preserve tracked data for restoration, enable clean rendering without lines crossing inactive regions.

### Insert Track (Gap Filling)

**Insert Track** fills gaps using 3DEqualizer-style deformation algorithm. Critical status handling:

- **First filled point**: `KEYFRAME` status (starts new active segment after gap)
- **Subsequent points**: `TRACKED` status (continuation of interpolated data)
- **Original ENDFRAME**: Converted to `KEYFRAME` (gap is now closed)

**Why this matters**: `SegmentedCurve` treats `TRACKED` points after `ENDFRAME` as inactive segments (3DEqualizer gap semantics). The first `KEYFRAME` signals "gap is filled, resume active segment" so renderer draws solid lines instead of dashed gap visualization.

**Files**: `core/insert_track_algorithm.py` (status assignment), `core/curve_segments.py:from_points()` (segment activity logic)

## Selection State

**Two types of selection:**

1. **Curve-Level** (which trajectories to display)
   - `state.get_selected_curves()` / `state.set_selected_curves(set)`
   - `state.get_show_all_curves()` / `state.set_show_all_curves(bool)`

2. **Point-Level** (which frames within active curve)
   - `state.get_selection(curve_name)` / `state.set_selection(curve_name, indices)`

## Display Modes

```python
from core.display_mode import DisplayMode

# Display mode is computed from selection state
state.set_show_all_curves(True)   # → DisplayMode.ALL_VISIBLE
state.set_show_all_curves(False)  # → DisplayMode.SELECTED or ACTIVE_ONLY
```

## UI Controllers

Specialized controllers in `ui/controllers/`:
1. **ActionHandlerController**: Menu/toolbar actions
2. **MultiPointTrackingController**: Multi-curve tracking, Insert Track
3. **PointEditorController**: Point editing logic
4. **SignalConnectionManager**: Signal/slot connections
5. **TimelineController**: Frame navigation, playback
6. **UIInitializationController**: UI component setup
7. **ViewCameraController**: Camera movement
8. **ViewManagementController**: View state (zoom, pan, fit)
9. **FrameChangeCoordinator**: Coordinates frame change responses in deterministic order, eliminating race conditions from Qt signal ordering

## Keyboard Shortcuts

**Editing**:
- E: Toggle endframe status
- D: Delete current frame keyframe
- Delete: Remove selected points
- Numpad 2/4/6/8: Nudge (Shift=10x, Ctrl=0.1x)
- Ctrl+Shift+I: Insert Track

**Selection**:
- Ctrl+A: Select all
- Escape: Deselect all

**View**:
- C: Center on selection
- F: Fit to view
- Mouse wheel: Zoom
- Middle-drag: Pan

**Undo/Redo**:
- Ctrl+Z: Undo
- Ctrl+Y: Redo

## File Organization

```
CurveEditor/
├── core/           # Models, commands, algorithms
├── data/           # Data operations
├── rendering/      # Optimized rendering pipeline
├── services/       # 4 services
├── stores/         # ApplicationState
├── ui/             # MainWindow, widgets, controllers
├── tests/          # Test suite
├── session/        # Session persistence
├── main.py         # Entry point
├── bpr             # Basedpyright wrapper
└── pyproject.toml  # Dependencies, tools
```

## Development Environment

### Setup
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Activate (optional - uv run handles automatically)
source .venv/bin/activate
```

### WSL Environment

**If `uv` unavailable, use `.venv/bin/python3` directly:**

```bash
uv run pytest tests/        → .venv/bin/python3 -m pytest tests/
uv run ruff check .         → .venv/bin/python3 -m ruff check .
uv run ./bpr                → .venv/bin/python3 ./bpr
```

### Linting & Testing

```bash
# Type checking
./bpr                      # All files
./bpr --errors-only        # Errors only
./bpr ui/main_window.py    # Specific file

# Linting
uv run ruff check . --fix

# Testing (prefer -x for development)
uv run pytest tests/ -xq           # PREFERRED: Stop at first failure, quiet output
uv run pytest tests/ -x            # Stop at first failure, normal output
uv run pytest tests/ -v            # Full run (pre-commit validation)
python3 -m py_compile <file.py>    # Quick syntax check
```

**Test workflow**:
- **Development** (default): Use `-x` to stop at first failure for fast iteration
- **Pre-commit**: Use `-v` for full validation before committing
- **Impact analysis**: Use full run to see total breakage after refactoring

## Type Safety

### Avoid hasattr()
```python
# ❌ BAD - Type lost
if hasattr(self, 'main_window') and self.main_window:
    frame = self.main_window.current_frame

# ✅ GOOD - Type preserved
if self.main_window is not None:
    frame = self.main_window.current_frame
```

### Use Specific Type Ignores
```python
# ❌ BAD - Blanket ignore
data = func()  # type: ignore

# ✅ GOOD - Specific rule
data = func()  # pyright: ignore[reportArgumentType]
```

**See `BASEDPYRIGHT_STRATEGY.md` for comprehensive type checking guide.**

## Serena MCP Tools

**When to Use Serena:**
- ✅ Exploring unfamiliar code (start with `get_symbols_overview`)
- ✅ Tracing logic across files (`find_referencing_symbols`)
- ✅ Refactoring symbols (`replace_symbol_body`)

**When to Use Traditional Tools:**
- ⚡ Reading known files → `Read`
- ⚡ Text search → `Grep`
- ⚡ Line edits → `Edit`

**Progressive Exploration Pattern:**
```python
# Save ~75% tokens
get_symbols_overview(file.py)              # See structure
find_symbol(ClassName, depth=1)            # See methods
find_symbol(ClassName/method, include_body=true)  # Read specific method
```

**Key Tools:**
- `mcp__serena__get_symbols_overview` - High-level file structure
- `mcp__serena__find_symbol` - Find symbols by name path
- `mcp__serena__find_referencing_symbols` - Where symbol is used
- `mcp__serena__search_for_pattern` - Regex search
- `mcp__serena__replace_symbol_body` - Surgical edits

## Common Patterns

```python
# Services
from services import get_data_service, get_interaction_service, get_transform_service, get_ui_service

# State
from stores.application_state import get_application_state

# Core types
from core.models import CurvePoint, PointCollection, PointStatus
from core.type_aliases import CurveDataList
from core.display_mode import DisplayMode

# UI
from ui.curve_view_widget import CurveViewWidget
from ui.main_window import MainWindow
```

### Transform Service Pattern

**Recommended**: Use `get_transform()` for coordinate transformations:

```python
# ✅ RECOMMENDED - Single method call
from services import get_transform_service

transform_service = get_transform_service()
transform = transform_service.get_transform(view)

# Use transform
screen_x, screen_y = transform.data_to_screen(data_x, data_y)
data_x, data_y = transform.screen_to_data(screen_x, screen_y)
```

**Legacy Pattern** (still supported but verbose):

```python
# ⚠️ LEGACY - Two-step pattern (still works but verbose)
view_state = transform_service.create_view_state(view)
transform = transform_service.create_transform_from_view_state(view_state)
```

**When to use legacy pattern**:
- Need to modify `view_state` between creation and transform
- Advanced test scenarios requiring view state manipulation
- 99% of code should use `get_transform()` directly

## Adding Configurable Visual Rendering Parameters

**Pattern:** All visual rendering parameters are centralized in `VisualSettings` dataclass.

### 4-Step Process

1. **Add to VisualSettings** (`rendering/visual_settings.py`):
   ```python
   @dataclass
   class VisualSettings:
       # ... existing fields
       new_param: int = 10  # Add new parameter with default
   ```

2. **Add Validation** (if numeric):
   ```python
   def __post_init__(self) -> None:
       # ... existing validations
       if self.new_param <= 0:
           raise ValueError(f"new_param must be > 0, got {self.new_param}")
   ```

3. **Update Renderer** (`rendering/optimized_curve_renderer.py`):
   ```python
   # Access via render_state.visual.new_param
   value = render_state.visual.new_param
   ```

4. **Add UI Control** (if user-configurable):
   ```python
   # In controller
   def update_new_param(self, value: int) -> None:
       self.curve_view.visual.new_param = value
       self.curve_view.update()
   ```

### Test Pattern

```python
from rendering.visual_settings import VisualSettings

def test_new_param_default():
    visual = VisualSettings()
    assert visual.new_param == 10

def test_new_param_validation():
    with pytest.raises(ValueError, match="new_param must be > 0"):
        VisualSettings(new_param=0)

def test_new_param_rendering():
    visual = VisualSettings(new_param=15)
    # Verify renderer uses new value
```

### Key Principles
- **Single source**: VisualSettings is the ONLY place for visual parameters
- **Validation**: All numeric fields validated in `__post_init__`
- **Immutability NOT required**: VisualSettings is mutable for runtime updates
- **Access pattern**: Always `widget.visual.param` or `render_state.visual.param`
- **Migration complete**: Deprecated widget properties removed (Phase 5, Oct 2025)

### Example: Adding Grid Opacity

```python
# 1. Add field (visual_settings.py)
@dataclass
class VisualSettings:
    grid_opacity: float = 0.5  # 0.0-1.0

# 2. Validate (visual_settings.py)
def __post_init__(self) -> None:
    if not 0.0 <= self.grid_opacity <= 1.0:
        raise ValueError(f"grid_opacity must be 0.0-1.0, got {self.grid_opacity}")

# 3. Use in renderer (optimized_curve_renderer.py)
def _draw_grid(self, painter: QPainter, render_state: RenderState) -> None:
    opacity = render_state.visual.grid_opacity
    color = QColor(100, 100, 100, int(opacity * 255))

# 4. Add UI slider (view_management_controller.py)
def update_grid_opacity(self, value: float) -> None:
    self.main_window.curve_widget.visual.grid_opacity = value
    self.main_window.curve_widget.update()
```

## Key Design Patterns

1. **Component Container**: UI attributes in `ui/ui_components.py`
2. **Service Singleton**: Thread-safe service instances
3. **Protocol-based**: Type-safe interfaces
4. **Interface Segregation**: Focused protocols in `protocols/state.py` (Phase 1)
5. **Immutable Models**: Thread-safe CurvePoint
6. **Transform Caching**: LRU cache
7. **Command Pattern**: Undo/redo support with automatic target storage

## Common Pitfalls

### ❌ WRONG: Modifying controller snapshot dict

Controller properties that return dicts (like `tracked_data`) return **snapshots** (fresh dict each call). Item assignment doesn't persist:

```python
# ❌ WRONG - Modifications lost immediately
tracked_data = controller.tracked_data  # Get snapshot
tracked_data[curve_name] = new_data     # Modify temporary dict - LOST!
```

**Why this fails:**
- `tracked_data` property returns a new dict on each access
- Modifying the returned dict doesn't affect ApplicationState
- Changes disappear when the dict is garbage collected
- No error is raised - **fails silently**

### ✅ CORRECT: Direct ApplicationState access

```python
# ✅ CORRECT - Direct ApplicationState access (preferred)
from stores.application_state import get_application_state

app_state = get_application_state()
app_state.set_curve_data(curve_name, new_data)  # Persists correctly
```

**Alternative (bulk operations only):**
```python
# ✅ ACCEPTABLE - Bulk replacement via setter
controller.tracked_data = loaded_data  # Triggers property setter
```

**When to use which:**
- **Direct ApplicationState**: All command/service operations (preferred)
- **Bulk replacement**: File loading, session restore (valid but less common)
- **Snapshot read**: Read-only iteration over all curves (safe)

## Development Tips

1. Check `which uv` first - use `.venv/bin/python3` if unavailable
2. Type checking: `./bpr` (works with or without uv)
3. Syntax check: `python3 -m py_compile <file>` (no deps)
4. Prefer None checks over `hasattr()` for type safety
5. Use `pyright: ignore[rule]` not `type: ignore`
6. Keep `uv.lock` committed for reproducible builds
7. Validate before integration to prevent silent failures

---
*Last Updated: October 2025*

# Important Reminders
- Do what's asked; nothing more, nothing less
- **NEVER** make assumptions
- ALWAYS prefer editing existing files
- NEVER create documentation unless explicitly requested

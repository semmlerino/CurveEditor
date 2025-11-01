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
 

### Protocol Adoption Status

The project uses protocol-based typing for loose coupling and type safety:

**Protocols Defined** (organized in `protocols/` package):
- ✅ **`protocols/ui.py`**: 16 UI component protocols (MainWindowProtocol, CurveViewProtocol, StateManagerProtocol, etc.)
- ✅ **`protocols/data.py`**: Data model protocols (PointProtocol, CurveDataProtocol, ImageProtocol, etc.)
- ✅ **`protocols/services.py`**: Service layer protocols (DataServiceProtocol, InteractionServiceProtocol, TransformServiceProtocol, UIServiceProtocol)
- ✅ Centralized in `protocols/__init__.py` for single import point
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

## Architectural Map: Where Things Happen

**Selection & Interaction:**
- `services/interaction_service.py`: Mouse/point selection (_SelectionManager, _MouseHandler)
- `stores/application_state.py`: Selection storage (active_curve, get_selection, set_selection)

**Rendering:**
- `rendering/optimized_curve_renderer.py`: Curve/point rendering (OptimizedCurveRenderer)
- `core/curve_segments.py`: Gap visualization (SegmentedCurve.from_points)
- `ui/timeline_tabs.py`: Timeline frame status display
- `rendering/visual_settings.py`: Centralized visual parameters

**Frame Management:**
- `stores/application_state.py`: Current frame state (set_frame, frame_changed signal)
- `ui/controllers/frame_change_coordinator.py`: Deterministic frame change ordering
- `ui/controllers/timeline_controller.py`: Navigation (next_frame, prev_frame, jump_to_frame)

**Data Flow:**
- `stores/application_state.py`: Central data store (get_curve_data, set_curve_data, active_curve_data)
- `services/data_service.py`: File I/O (load_csv, save_json, get_position_at_frame)
- `services/image_cache_manager.py`: Image caching (SafeImageCacheManager)

**Commands:**
- `core/commands/command_manager.py`: Undo/redo (execute, undo, redo)
- `core/commands/curve_commands.py`: Base class (CurveDataCommand - automatic target storage)
- `core/commands/shortcut_commands.py`: Keyboard commands (E, D, Delete, arrows)

**Coordinate Transforms:**
- `services/transform_service.py`: get_transform(view) - data_to_screen / screen_to_data

## State Management

**Two separate state stores:**

**ApplicationState** - Application data (curves, images, frames):
```python
from stores.application_state import get_application_state
state = get_application_state()

# Multi-curve API
state.set_curve_data(curve_name, data)
data = state.get_curve_data(curve_name)

# Active curve property (recommended)
if (curve_data := state.active_curve_data) is None:
    return
curve_name, data = curve_data  # Safe access to active curve + data

# Signals: curves_changed, selection_changed, frame_changed
```

**StateManager** - UI preferences (zoom, pan, window state):
```python
from ui.state_manager import StateManager

state_manager.zoom_level = 2.0
state_manager.pan_offset = (100, 50)
# Signals: view_state_changed, undo_state_changed, tool_state_changed
```

**⚠️ Critical**: StateManager has NO data access. Use ApplicationState for all curve/image/frame data.


## Command Base Class Pattern

Commands modifying curve data inherit from `CurveDataCommand`:

```python
from core.commands.curve_commands import CurveDataCommand

class MyCommand(CurveDataCommand):
    def execute(self, main_window: MainWindowProtocol) -> bool:
        # AUTOMATIC target storage when calling _get_active_curve_data()
        if (result := self._get_active_curve_data()) is None:
            return False
        curve_name, data = result
        # ... perform operation, save old_data/new_data
        return self._safe_execute("executing", operation)

    def undo(self, main_window: MainWindowProtocol) -> bool:
        # Use stored self._target_curve (NOT current active)
        state.set_curve_data(self._target_curve, self._old_data)
```

**Key benefits**: Automatic active curve validation, target storage for undo/redo, standardized error handling.

**Base methods**: `_get_active_curve_data()`, `_safe_execute()`, `_update_point_position()`, `_update_point_at_index()`

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

- **All filled points**: `TRACKED` status (tracking data copied from source)
- **Original ENDFRAME**: Converted to `KEYFRAME` (gap is now closed)

**Why this matters**: The converted ENDFRAME->KEYFRAME activates the segment. All filled frames are tracking data, so they get TRACKED status. The KEYFRAME at the gap boundary signals "segment is active" so the renderer draws solid lines instead of dashed gap visualization.

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

Specialized controllers in `ui/controllers/` handle focused responsibilities:
- **Action handling**: Menu/toolbar actions (ActionHandlerController)
- **Tracking**: Multi-curve tracking, Insert Track workflow (MultiPointTrackingController, BaseTrackingController, Tracking*Controller)
- **Point editing**: Point manipulation, selection (PointEditorController)
- **Frame management**: Navigation, playback, deterministic frame change coordination (TimelineController, FrameChangeCoordinator)
- **View management**: Camera movement, zoom, pan, fit-to-view (ViewCameraController, ViewManagementController)
- **UI setup**: Component initialization, signal connections (UIInitializationController, SignalConnectionManager)
- **Progressive disclosure**: Collapsible UI sections (ProgressiveDisclosureController)

Key architectural pattern: **FrameChangeCoordinator** eliminates race conditions from Qt signal ordering by enforcing deterministic frame change response order.

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

```python
from services import get_transform_service
transform = get_transform_service().get_transform(view)
screen_x, screen_y = transform.data_to_screen(data_x, data_y)
```

## Common Development Workflows

### Adding a View Option Checkbox

**Signal Flow**: User toggles checkbox → Signal → StateManager → view_state_changed → CurveWidget.update()

**Files to Touch** (in order):
1. `ui/state_manager.py` - Add property with getter/setter, emit `view_state_changed`
2. `ui/main_window.py` - Declare `QCheckBox | None` attribute
3. `ui/controllers/ui_initialization_controller.py` - Create checkbox in `_init_toolbar()`
4. `ui/controllers/signal_connection_manager.py` - Connect `stateChanged` signal
5. `ui/controllers/view_management_controller.py` - Add handler (update StateManager, call `update()`)
6. `rendering/render_state.py` - Add field if needed for rendering
7. `rendering/optimized_curve_renderer.py` - Use the state if needed

**Example**: `show_current_point_only` (see `tests/test_current_point_only_mode.py`)

### Adding a Keyboard Shortcut

**Signal Flow**: Key press → GlobalEventFilter → ShortcutRegistry → Command.execute()

**Files to Touch**:
1. `core/commands/shortcut_commands.py` - Create command class inheriting from `ShortcutCommand`
2. `ui/main_window.py:_init_global_shortcuts()` - Register with `shortcut_registry.register()`

**Example**: See `SetEndframeCommand`, `DeletePointsCommand`

### Adding a Menu/Toolbar Action

**Signal Flow**: Action triggered → ActionHandlerController → Service calls → ApplicationState update

**Files to Touch**:
1. `ui/controllers/ui_initialization_controller.py:_init_actions()` - Create `QAction`
2. `ui/controllers/ui_initialization_controller.py:_init_menus()` - Add to menu
3. `ui/controllers/ui_initialization_controller.py:_init_toolbar()` - Add to toolbar (optional)
4. `ui/controllers/action_handler_controller.py` - Add handler method
5. `ui/controllers/signal_connection_manager.py` - Connect signal

### Modifying Rendering Behavior

**Data Flow**: ApplicationState → RenderState.compute() → OptimizedCurveRenderer.render()

**Files to Touch**:
1. `rendering/render_state.py` - Add field, update `compute()` to extract from widget
2. `rendering/optimized_curve_renderer.py` - Use `render_state.your_field` in render methods

**Key Insight**: Renderer only accesses state via `RenderState`, never directly from widgets/StateManager

### Adding Multi-Curve Support

**Files to Touch**:
1. `stores/application_state.py` - Already multi-curve aware
2. `rendering/render_state.py` - Add to `curves_data` dict if needed
3. `rendering/optimized_curve_renderer.py:_render_multiple_curves()` - Handle per-curve logic

## Key Design Patterns

1. **Component Container**: UI attributes in `ui/ui_components.py`
2. **Service Singleton**: Thread-safe service instances
3. **Protocol-based Architecture**: Type-safe interfaces organized in `protocols/` package
4. **Interface Segregation**: Focused protocols for UI, data, and services
5. **Immutable Models**: Thread-safe CurvePoint
6. **Transform Caching**: LRU cache
7. **Command Pattern**: Undo/redo support with automatic target storage

## Common Pitfalls

**❌ Don't modify controller snapshot dicts** - Controller properties return fresh dict copies. Modifications are lost:
```python
# ❌ WRONG - Modification lost
controller.tracked_data[curve_name] = data

# ✅ CORRECT - Direct ApplicationState access
get_application_state().set_curve_data(curve_name, data)
```

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

<!-- Testing auto-push debug logging - third test with error capture -->

# Important Reminders
- Do what's asked; nothing more, nothing less
- **NEVER** make assumptions
- ALWAYS prefer editing existing files
- NEVER create documentation unless explicitly requested

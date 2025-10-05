# CurveEditor Development Guide

Comprehensive reference for the CurveEditor codebase - a Python/PySide6 application for editing animation curves with a consolidated 4-service architecture.

## Code Quality Standards

1. **Type Safety First**: Use type hints, avoid `hasattr()` (destroys type information)
2. **Service Architecture**: Respect the 4-service pattern
3. **Protocol Interfaces**: Type-safe duck-typing
4. **Component Container Pattern**: Access UI via `self.ui.<group>.<widget>`
5. **Validation Before Integration**: Prevent silent attribute creation

## Architecture

### Core Services
1. **TransformService**: Coordinate transformations, view state (99.9% cache hit rate)
2. **DataService**: Data operations, file I/O, image management
3. **InteractionService**: User interactions, point manipulation, command history
4. **UIService**: UI operations, dialogs, status updates

### Service Access
```python
from services import get_data_service, get_interaction_service, get_transform_service, get_ui_service
```

### InteractionService Multi-Curve API

**Phase 8 Complete (October 2025)**: InteractionService now supports multi-curve operations with backward compatibility.

**Key Methods with Multi-Curve Support:**

```python
from services import get_interaction_service

service = get_interaction_service()

# find_point_at - Search with mode parameter
result = service.find_point_at(view, x, y, mode="active")      # Single curve (default)
result = service.find_point_at(view, x, y, mode="all_visible") # All visible curves
if result.found:
    print(f"Point {result.index} in {result.curve_name}")

# Selection methods - Optional curve_name parameter
service.clear_selection(view, main_window)                     # Active curve
service.clear_selection(view, main_window, curve_name="pp56_TM_138G")

service.select_all_points(view, main_window)                   # Active curve
service.select_all_points(view, main_window, curve_name="pp56_TM_138G")

service.select_points_in_rect(view, main_window, rect)         # Active curve
service.select_points_in_rect(view, main_window, rect, curve_name="pp56_TM_138G")

# Manipulation methods - Optional curve_name parameter
service.delete_selected_points(view, main_window)              # Active curve
service.delete_selected_points(view, main_window, curve_name="pp56_TM_138G")

service.nudge_selected_points(view, main_window, 1.0, 0.0)     # Active curve
service.nudge_selected_points(view, main_window, 1.0, 0.0, curve_name="pp56_TM_138G")

# State callbacks - Curve-aware signals
service.on_data_changed(curve_name)
service.on_selection_changed(indices, curve_name=None)
service.on_frame_changed(frame, curve_name=None)
```

**PointSearchResult** (returned by `find_point_at`):
- `.index`: Point index (-1 if not found)
- `.curve_name`: Curve name (None if not found)
- `.found`: Boolean property (True if index >= 0)
- `.distance`: Distance from click (for all_visible mode)
- Comparison operators: `result >= 0`, `result == -1` work for backward compatibility

**SearchMode** options:
- `"active"`: Search active curve only (default, backward compatible)
- `"all_visible"`: Search all visible curves (multi-curve mode)

**Backward Compatibility:**
- All methods default to active curve when `curve_name=None`
- Existing code continues to work without modifications
- PointSearchResult acts like int for comparisons

### Command System
- **CommandManager**: Manages undo/redo history with command pattern
- **Command Classes**:
  - **Curve Commands**: BatchMoveCommand, MovePointCommand, DeletePointsCommand, SetPointStatusCommand, SmoothCommand, AddPointCommand, ConvertToInterpolatedCommand, SetCurveDataCommand
  - **Shortcut Commands**: InsertTrackShortcutCommand, SetEndframeCommand, DeleteCurrentFrameKeyframeCommand, SetTrackingDirectionCommand, CenterViewCommand, FitBackgroundCommand, NudgePointsCommand, SelectAllCommand, DeselectAllCommand, UndoCommand, RedoCommand
  - **Utility Commands**: CompositeCommand, NullCommand, InsertTrackCommand
- **ShortcutRegistry**: Global keyboard shortcut registration and handling
- **GlobalEventFilter**: Application-level keyboard event interception

## Serena MCP Integration

Serena provides semantic code intelligence tools for token-efficient navigation and surgical code modifications across CurveEditor's 66-file codebase.

### When to Use Serena vs Traditional Tools

**Use Serena when:**
- ✅ Exploring unfamiliar code structure (get_symbols_overview first, then targeted reads)
- ✅ Tracing logic across multiple files (find_referencing_symbols)
- ✅ Debugging complex issues requiring cross-file analysis
- ✅ Refactoring symbols (surgical edits without string matching)
- ✅ Finding implementation patterns (search_for_pattern with multiline)

**Use Traditional Tools when:**
- ⚡ Reading specific known file paths → `Read`
- ⚡ Simple text search (filenames, imports) → `Grep`
- ⚡ Line-specific edits (comments, single line) → `Edit`
- ⚡ Quick syntax validation → `python3 -m py_compile`

**Rule of Thumb:** If you need to understand relationships between code, use Serena. If you know exactly what to change, use traditional tools.

### Core Serena Tools

**Code Navigation:**
- `mcp__serena__list_dir`, `find_file` - Locate files and understand project structure
- `mcp__serena__get_symbols_overview` - Get high-level view of symbols (classes, functions, methods) WITHOUT reading entire file
- `mcp__serena__find_symbol` - Find specific symbols by name path with optional body content
- `mcp__serena__find_referencing_symbols` - Discover where symbols are used across codebase
- `mcp__serena__search_for_pattern` - Flexible regex search across codebase

**Code Editing:**
- `mcp__serena__replace_symbol_body` - Replace entire symbol (function, method, class)
- `mcp__serena__insert_after_symbol` - Add new code after a symbol
- `mcp__serena__insert_before_symbol` - Add new code before a symbol (useful for imports)

**Meta-Cognitive:**
- `mcp__serena__think_about_collected_information` - Assess if information is sufficient
- `mcp__serena__think_about_task_adherence` - Verify on-track (ALWAYS before editing)
- `mcp__serena__think_about_whether_you_are_done` - Confirm task completion

### Token-Efficient Exploration Pattern

**Progressive code exploration saves ~75% tokens:**

```python
# ❌ BAD: Read entire file (500+ lines)
Read(ui/controllers/timeline_controller.py)

# ✅ GOOD: Progressive exploration (saves 375 lines)
get_symbols_overview(ui/controllers/timeline_controller.py)  # See structure (50 lines)
find_symbol(TimelineController, depth=1, include_body=false)  # See methods (100 lines)
find_symbol(TimelineController/_on_frame_changed, include_body=true)  # Read specific method (20 lines)
```

**Best Practices:**
1. **Always start with `get_symbols_overview`** before reading full files
2. Use `find_symbol(depth=0)` to see method signatures without bodies
3. Use `include_body=true` only after you know which symbol you need
4. Set `relative_path` to narrow search scope (e.g., `relative_path="ui/controllers"`)

### Threading/Concurrency Debugging Pattern

**Real Example** (segfault during test teardown - saved 80% tokens vs grep + Read):

1. **Identify crash location** (from stacktrace: line 183 in conftest.py)
   ```python
   get_symbols_overview("tests/conftest.py")  # See structure first
   find_symbol("reset_all_services", include_body=true)  # Read specific function
   ```

2. **Find threading patterns across codebase**
   ```python
   search_for_pattern(
     substring_pattern="threading\.Thread|QThread",
     restrict_search_to_code_files=true,
     context_lines_after=3
   )
   ```

3. **Trace cleanup logic** (MainWindow → FileOperations → FileLoadWorker)
   ```python
   find_symbol("MainWindow/closeEvent")  # See what cleanup happens
   find_referencing_symbols("FileLoadWorker", "io_utils/file_load_worker.py")  # Where is worker used?
   ```

4. **Surgical fix without string matching**
   ```python
   replace_symbol_body(
     name_path="_cleanup_main_window_event_filter",
     relative_path="tests/fixtures/qt_fixtures.py",
     body="..."  # New implementation
   )
   ```

### Cross-File Navigation Patterns

**Understanding component relationships:**
- `find_referencing_symbols` reveals symbol usage patterns faster than grep
- `search_for_pattern` with `multiline=true` finds complex patterns (e.g., decorators + function)
- Use `relative_path` to scope searches: `relative_path="ui/controllers"` for controller-specific searches

**Example: Refactoring across multiple files**
```python
# Find all usages of a service method
find_referencing_symbols(
  name_path="get_data_service",
  relative_path="services/__init__.py"
)
# Returns: List of all files/locations using get_data_service with code snippets
```

### Common Import Patterns

```python
# Serena tools are available directly via MCP
# No imports needed - just use mcp__serena__* tool names
```

## Core Data Models (`core/models.py`)

```python
@dataclass(frozen=True)
class CurvePoint:
    frame: int
    x: float
    y: float
    status: PointStatus = PointStatus.NORMAL
    # Methods: distance_to(), with_status(), with_coordinates(), to_tuple3/4()

class PointCollection:
    # Methods: get_keyframes(), find_at_frame(), sorted_by_frame()

class PointStatus(Enum):
    NORMAL, INTERPOLATED, KEYFRAME, TRACKED, ENDFRAME
```

## Point/Curve Data Architecture

**Critical Distinction**: Understanding the point vs. curve terminology is essential for working with multi-point tracking features.

### Data Hierarchy

1. **Single Point** (`CurvePoint`): Position of a tracking point at ONE specific frame
   - Contains: `frame: int`, `x: float`, `y: float`, `status: PointStatus`
   - Example: Frame 100 position of tracking point "pp56_TM_138G"

2. **Single Trajectory/Curve** (`List[CurvePoint]` or `CurveDataList`): ONE tracking point's movement over time
   - A complete trajectory showing how one tracking point moves across multiple frames
   - Example: All positions of "pp56_TM_138G" from frame 1 to 100

3. **Multiple Trajectories** (`Dict[str, CurveDataList]`): MULTIPLE independent tracking points
   - Dictionary mapping tracking point names to their trajectories
   - Example: `{"pp56_TM_138G": [...], "pp53_TM_134G": [...], "pp50_TM_134G": [...]}`

### Storage Locations

```python
# Multi-point tracking data (all tracking points)
MultiPointTrackingController.tracked_data: dict[str, CurveDataList]

# Multi-curve display data
multi_curve_manager.curves_data: dict[str, CurveDataList]
multi_curve_manager.selected_curve_names: set[str]  # Which tracking points selected
multi_curve_manager.active_curve_name: str          # Active curve for editing

# Active timeline point (whose timeline is displayed)
main_window.active_timeline_point: str
```

### Terminology Clarification

**IMPORTANT**: In CurveEditor terminology (matching 3DEqualizer):
- **"Curve"** = One tracking point's complete trajectory over time
  - Example: "pp56_TM_138G" is ONE curve showing that point's path
- **"Point"** = Position at a specific frame within a trajectory
  - Example: Frame 42 position within "pp56_TM_138G" trajectory
- **"Multiple Curves"** = Multiple independent tracking points
  - Like having 10 different tracking points in 3DEqualizer

This distinction is **critical** for features like Insert Track that operate on multiple tracking points (curves) to fill gaps by transferring data between trajectories.

### Access Patterns

```python
# Get all tracking point names
point_names = main_window.multi_point_controller.tracked_data.keys()

# Get specific tracking point's trajectory
trajectory = main_window.multi_point_controller.tracked_data["pp56_TM_138G"]

# Get selected tracking points
selected = main_window.curve_widget.multi_curve_manager.selected_curve_names

# Get current frame number
frame = main_window.current_frame

# Access active curve (currently edited trajectory)
active_data = main_window.curve_widget.curve_data
```

## Main UI Components

### CurveViewWidget (`ui/curve_view_widget.py`)
- **Data**: `curve_data`, `selected_indices`
- **View**: `zoom_factor`, `pan_offset_x/y`, `background_image`
- **Transform**: `data_to_screen()`, `screen_to_data()`, `get_transform()`
- **Operations**: `set_curve_data()`, `add_point()`, `update_point()`, `remove_point()`
- **Signals**: `point_selected`, `point_moved`, `selection_changed`, `view_changed`

### MainWindow (`ui/main_window.py`)
- **Components**: `curve_widget`, `timeline_tabs`, `playback_state`, `ui` (UIComponents)
- **File Ops**: Delegated to FileOperations class
- **State**: Managed by StateManager class
- **Frame Nav**: `_on_frame_changed()`, `_update_frame_display()`
- **Playback**: Oscillating playback with timer
- **Features**: Background thread loading, keyboard shortcuts

### Card Widget (`ui/widgets/card.py`)
- **Modern UI Container**: Replaces QGroupBox with professional card design
- **Features**: Rounded corners (8px), subtle shadows, clean visual hierarchy
- **Collapsible**: Optional expand/collapse with toggle button
- **Styling**: Matches VFX tools like Nuke, Houdini, 3DEqualizer
- **Grid System**: Uses 8px spacing system for consistency
- **Signals**: `collapsed_changed` emitted on state change

## UI Controllers (`ui/controllers/`)

Specialized controllers for separating UI concerns:

1. **ActionHandlerController**: Menu and toolbar action handling
2. **MultiPointTrackingController**: Multi-curve tracking and Insert Track operations
3. **PointEditorController**: Point editing and manipulation logic
4. **SignalConnectionManager**: Centralized signal/slot connection management
5. **TimelineController**: Frame navigation, playback, timeline state
6. **UIInitializationController**: UI component setup and initialization
7. **ViewCameraController**: Camera movement and viewport navigation
8. **ViewManagementController**: View state management (zoom, pan, fit)

## State Management

CurveEditor uses **ApplicationState** as the single source of truth for all application data.

### ApplicationState Architecture

- **Location:** `stores/application_state.py`
- **Pattern:** Singleton with Qt signal-based reactivity
- **Design:** Multi-curve native (`dict[str, CurveDataList]` at core)
- **Signals:** `curves_changed`, `selection_changed`, `active_curve_changed`, `frame_changed`, `view_changed`, `curve_visibility_changed`, `selection_state_changed`

### Usage

```python
from stores.application_state import get_application_state

state = get_application_state()

# Set curve data
state.set_curve_data("pp56_TM_138G", curve_data)

# Get curve data
data = state.get_curve_data("pp56_TM_138G")

# Subscribe to changes
state.curves_changed.connect(self._on_data_changed)

# Batch operations (prevent signal storms)
state.begin_batch()
try:
    for curve in curves:
        state.set_curve_data(curve, data)
finally:
    state.end_batch()
```

### Key Principles

1. **NO local storage** - All components read from ApplicationState
2. **Subscribe to signals** - Automatic updates via Qt signals
3. **Batch operations** - Use `begin_batch()`/`end_batch()` for bulk changes
4. **Immutability** - `get_*` methods return copies for safety

### Migration Complete ✅

**Status**: Production-ready as of October 2025

✅ All 66 files migrated to ApplicationState
✅ All 5 storage locations consolidated into single source
✅ 811+ references updated
✅ Single source of truth established
✅ 83.3% memory reduction achieved (4.67 MB vs 28 MB)
✅ 14.9x batch operation speedup
✅ 100% test pass rate (2105/2105 tests passing)
✅ 0 production type errors
✅ Thread-safe with QMutex protection
✅ Reactive signal subscriptions in all controllers
✅ Exception handling for batch operations

### Legacy Stores (Compatibility)

#### CurveDataStore
- **Status**: Legacy (superseded by ApplicationState)
- **Purpose**: Single-curve data management (kept for backward compatibility)
- **Usage**: Prefer ApplicationState for new code

#### FrameStore
- **Purpose**: Current frame state management
- **Pattern**: Observable state with change notifications
- **Integration**: Syncs with timeline, playback, and curve display

#### StoreManager
- **Purpose**: Coordinates multiple stores and ensures consistency
- **Features**: Cross-store validation and transaction coordination

#### ConnectionVerifier
- **Purpose**: Validates Qt signal/slot connections during development
- **Features**: Detects orphaned connections and missing slots
- **Usage**: Development-time debugging tool for signal integrity

## Selection State Architecture

**Critical Distinction**: CurveEditor has TWO types of selection:

1. **Curve-Level Selection** (which trajectories to display)
   - Managed by `ApplicationState._selected_curves` and `._show_all_curves`
   - Controls which curves are visible in multi-curve mode
   - Affects rendering and multi-curve operations

2. **Point-Level Selection** (which frames within active curve)
   - Managed by `ApplicationState._selection[curve_name]`
   - Frame indices selected within a single curve's trajectory
   - Affects editing operations (move, delete, status changes)

### Curve-Level Selection API

```python
from stores.application_state import get_application_state

state = get_application_state()

# Get which curves are selected for display
selected = state.get_selected_curves()  # Returns: set[str]

# Set which curves to display (multi-curve mode)
state.set_selected_curves({"Track1", "Track2", "Track3"})

# Show all curves vs. only selected
is_showing_all = state.get_show_all_curves()  # Returns: bool
state.set_show_all_curves(True)  # Show all visible curves
state.set_show_all_curves(False)  # Show only selected curves

# Subscribe to selection state changes
state.selection_state_changed.connect(on_selection_changed)
# Signal signature: (selected_curves: set[str], show_all: bool)
```

### Display Mode (Computed Property)

The `display_mode` property is **computed** from selection state inputs:

```python
@property
def display_mode(self) -> DisplayMode:
    """Computed from _selected_curves and _show_all_curves."""
    if self._show_all_curves:
        return DisplayMode.ALL_VISIBLE
    elif self._selected_curves:
        return DisplayMode.SELECTED
    else:
        return DisplayMode.ACTIVE_ONLY
```

**Important**: `display_mode` has NO setter - it's read-only. To change display mode:

```python
# ❌ Wrong: No setter exists
widget.display_mode = DisplayMode.ALL_VISIBLE  # DeprecationWarning (Phase 7)

# ✅ Correct: Set inputs
state.set_show_all_curves(True)  # → display_mode becomes ALL_VISIBLE
```

### Batch Mode for Coordinated Changes

When changing both selection fields together, use batch mode:

```python
# ❌ Bad: Two signals, two repaints
state.set_show_all_curves(False)
state.set_selected_curves({"Track1", "Track2"})

# ✅ Good: One signal, one repaint
state.begin_batch()
try:
    state.set_show_all_curves(False)
    state.set_selected_curves({"Track1", "Track2"})
finally:
    state.end_batch()
```

### Session Persistence

Selection state is automatically persisted in session files:

```python
# SessionManager saves/loads selection state
session_data = session_manager.create_session_data(
    tracking_file="tracking.txt",
    selected_curves=["Track1", "Track2"],
    show_all_curves=False,
)

# On restore, ApplicationState is updated via:
# state.set_selected_curves(set(session_data["selected_curves"]))
# state.set_show_all_curves(session_data["show_all_curves"])
```

**See Also**:
- `stores/application_state.py` - Full implementation
- `SELECTION_STATE_REFACTORING_TRACKER.md` - Migration history
- `tests/test_selection_state_integration.py` - Comprehensive test coverage

## Key Operations

### Point Manipulation
- **Select**: Left-click (single), Ctrl+click (multi), Alt+drag (rubber band)
- **Move**: Drag & drop, Numpad 2/4/6/8 (with Shift=10x, Ctrl=0.1x)
- **Delete**: Delete key
- **Status**: E key toggles Normal/Keyframe/Endframe

### View Controls
- **Zoom**: Mouse wheel (cursor-centered)
- **Pan**: Middle-click drag
- **Center**: C key (on selection)
- **Fit**: F key (to background/curve)

### Keyboard Shortcuts

**Editing**:
- E: Toggle endframe status (current frame only)
- D: Delete current frame keyframe
- Delete: Remove selected points
- Numpad 2/4/6/8: Nudge points (Shift=10x, Ctrl=0.1x)
- Ctrl+Shift+I: Insert Track (3DEqualizer-style gap filling)

**Selection**:
- Ctrl+A: Select all points
- Escape: Deselect all

**View**:
- C: Center on selection
- F: Fit to view (background/curve)
- Mouse wheel: Zoom (cursor-centered)
- Middle-click drag: Pan view

**Tracking Direction**:
- Shift+1 (or !): Backward tracking
- Shift+2 (or " or @): Forward tracking
- Shift+F3: Bidirectional tracking

**Undo/Redo**:
- Ctrl+Z: Undo
- Ctrl+Y: Redo

### Undo/Redo System
- **Command Pattern**: All operations use commands for undo/redo support
- **Global Shortcuts**: Ctrl+Z/Ctrl+Y work via ShortcutRegistry and GlobalEventFilter
- **Command Merging**: Continuous operations (e.g., dragging) merge into single undo step
- **Full Coverage**: Move, delete, status changes, smoothing all undoable

## Insert Track Feature (3DEqualizer-style Gap Filling)

**Purpose**: Fill gaps in tracking trajectories by interpolating or copying data from other curves.

**Shortcut**: Ctrl+Shift+I

**Implementation**:
- **Algorithm** (`core/insert_track_algorithm.py`): Core gap detection and filling logic
- **Command** (`core/commands/insert_track_command.py`): Undoable insert track operation
- **Controller**: MultiPointTrackingController handles multi-curve operations

**Usage Scenarios**:
1. **Single Curve Interpolation**: When only one curve selected, fills gaps by linear interpolation
2. **Multi-Curve Copy**: When multiple curves selected, copies data from source curves with offset correction
3. **Averaged Curves**: Can create averaged trajectories from multiple sources

**Gap Detection**:
- `find_gap_around_frame()`: Identifies continuous frame ranges without tracking data
- Works on current frame to find surrounding gap boundaries
- Respects ENDFRAME status to preserve intentional segment breaks

**3DEqualizer Compatibility**: Based on 3DEqualizer's Insert Track functionality for seamless workflow integration.

## Rendering Pipeline (`rendering/optimized_curve_renderer.py`)

**47x Performance Improvement**:
- Viewport culling with spatial indexing
- Level-of-detail based on zoom
- NumPy vectorized transformations
- Adaptive quality based on FPS

## Curve Visibility Architecture

**Phase 4 Complete (October 2025)**: Boolean removal complete - DisplayMode enum is the sole visibility API.

Curve rendering uses **three coordinated visibility filters**:

1. **metadata.visible** - Per-curve permanent flag (checked first)
2. **DisplayMode** - Three-state enum (replaces legacy `show_all_curves` boolean)
3. **selected_curve_names** - Selection set (used in SELECTED mode)

### DisplayMode Enum

```python
from core.display_mode import DisplayMode

# Set display mode
widget.display_mode = DisplayMode.ALL_VISIBLE   # Show all visible curves
widget.display_mode = DisplayMode.SELECTED      # Show only selected curves
widget.display_mode = DisplayMode.ACTIVE_ONLY   # Show active curve only
```

### Performance: RenderState Pattern

```python
from rendering.render_state import RenderState
from core.display_mode import DisplayMode

# Pre-compute visibility once per frame (in paintEvent)
render_state = RenderState.compute(widget)

# RenderState fields (frozen dataclass):
# - display_mode: DisplayMode | None  (replaces legacy show_all_curves boolean)
# - visible_curves: frozenset[str]    (pre-computed visibility)
# - selected_curve_names: frozenset[str] | None
# - active_curve_name: str | None
# - curves_data: dict[str, CurveDataList] | None

# O(1) membership check
if curve_name in render_state.visible_curves:
    render_curve(curve_name)

# Multi-curve mode detection
is_multi_curve = render_state.display_mode in (DisplayMode.ALL_VISIBLE, DisplayMode.SELECTED)
```

**Benefits**: Eliminates N ApplicationState lookups, O(1) checks, thread-safe, immutable

### Common Patterns

```python
# Show all
widget.display_mode = DisplayMode.ALL_VISIBLE

# Show selected
widget.display_mode = DisplayMode.SELECTED
widget.selected_curve_names = {"Track1", "Track2"}

# Hide permanently
metadata = state.get_curve_metadata("Track1")
metadata["visible"] = False
state.set_curve_metadata("Track1", metadata)
```

**See Also**: `core/DISPLAY_MODE_MIGRATION.md`, `RENDER_STATE_IMPLEMENTATION.md`

## File Organization

```
CurveEditor/
├── core/           # Data models (CurvePoint, PointCollection), commands, algorithms
├── data/           # Data operations, batch editing
├── rendering/      # Optimized rendering (47x faster)
├── services/       # 4 consolidated services
├── stores/         # Reactive data stores (CurveDataStore, FrameStore)
├── ui/             # MainWindow, CurveViewWidget, UIComponents, FileOperations
│   ├── controllers/  # UI controllers (Timeline, MultiPoint, ViewManagement, etc.)
│   └── widgets/      # Custom widgets (Card, etc.)
├── tests/          # Test suite (106 test files, 1945+ test cases)
├── session/        # Session state persistence
├── main.py         # Entry point
├── bpr             # Python wrapper for basedpyright with enhanced features
├── .venv/          # uv-managed virtual environment (Python 3.13+)
├── uv.lock         # Dependency lockfile (committed for reproducible builds)
└── pyproject.toml  # Project config, dependencies, and tool settings
```

## Development Environment

### Setup
```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv sync

# Activate environment (optional - uv run handles this automatically)
source .venv/bin/activate
```

### Using uv in WSL Environment

**IMPORTANT**: This project runs in WSL. If `uv` command is not available, use `.venv/bin/python3` directly.

```bash
# Check availability
which uv  # Should show path, otherwise uv not installed

# Command translations (when uv unavailable):
uv run pytest tests/        → .venv/bin/python3 -m pytest tests/
uv run ruff check .         → .venv/bin/python3 -m ruff check .
uv run ./bpr                → .venv/bin/python3 ./bpr
uv add <package>            → .venv/bin/python3 -m pip install <package>
```

### Linting & Type Checking
```bash
# Ruff (use uv run OR direct path)
uv run ruff check . --fix              # If uv available
.venv/bin/python3 -m ruff check . --fix  # Always works

# Basedpyright wrapper
./bpr                      # Check all
./bpr --errors-only        # Errors only
./bpr --summary            # Counts only
./bpr ui/main_window.py    # Specific file
```

### Testing
```bash
# Run tests (use uv run OR direct path)
uv run pytest tests/                   # If uv available
.venv/bin/python3 -m pytest tests/     # Always works

# Quick syntax check (no venv needed)
python3 -m py_compile <file.py>
```

## Type Safety Best Practices

### Avoid hasattr() - Destroys Type Information
```python
# BAD - Type becomes Any
if hasattr(self, 'main_window') and self.main_window:
    current_frame = self.main_window.current_frame  # Type lost!

# GOOD - Type preserved
if self.main_window is not None:
    current_frame = self.main_window.current_frame  # Type safe!
```

### Use Properties & Protocols
```python
@property
def current_frame(self) -> int:
    return self._get_current_frame()

class HasCurrentFrame(Protocol):
    @property
    def current_frame(self) -> int: ...
```

### When hasattr() is OK
- Dynamic runtime attributes
- Duck-typing multiple object types
- Cache initialization checks
- Optional debug flags

## Basedpyright Type Ignores

### Use `pyright: ignore` with Specific Rules
```python
# BAD - Old style, less safe
data = something()  # type: ignore

# BAD - Blanket ignore without rule
self.curve_widget.set_curve_data(data)  # pyright: ignore

# GOOD - Basedpyright preferred with specific rule
self.curve_widget.set_curve_data(data)  # pyright: ignore[reportArgumentType]
```

### Common Diagnostic Rules
- **reportArgumentType**: Argument type mismatches
- **reportReturnType**: Return type mismatches
- **reportAssignmentType**: Assignment incompatibilities
- **reportOptionalMemberAccess**: Accessing potentially None attributes
- **reportUnknownVariableType**: Unknown variable types
- **reportUnknownMemberType**: Unknown class/instance member types

### Enforced in Configuration
```json
// basedpyrightconfig.json
{
  "reportIgnoreCommentWithoutRule": "error"  // Requires specific rules
}
```

### Better Alternatives to Type Ignores
1. **Type Casting**: `cast(TargetType, value)`
2. **Fix Root Cause**: Update protocols and type definitions
3. **Union Types**: Handle multiple possibilities explicitly
4. **Type Guards**: Use isinstance() or custom type guards

## Integration Pitfalls


### Prevention
```python
# Validate structure first
assert hasattr(ui.timeline, 'frame_spinbox')
assert isinstance(self.point_x_spinbox, QDoubleSpinBox)

# Use built-in validation
missing = window.ui.validate_completeness()
if missing:
    raise ValueError(f"Missing: {missing}")
```

## Performance Optimizations

- **Rendering**: 47x faster (viewport culling, LOD, vectorization)
- **Point Queries**: 64.7x faster (spatial indexing)
- **Transforms**: 99.9% cache hit rate
- **Threading**: Background file loading

## Common Import Patterns

```python
# Services
from services import get_data_service, get_interaction_service

# Core types
from core.models import CurvePoint, PointCollection
from core.type_aliases import CurveDataList

# UI
from ui.curve_view_widget import CurveViewWidget
from ui.main_window import MainWindow
from ui.file_operations import FileOperations
```

## Known Issues

1. **All tests passing**: 1945+ tests fully functional (test suite takes ~2 minutes)

## Type Checking Configuration

**See `BASEDPYRIGHT_STRATEGY.md`** for comprehensive type checking strategy:
- Current state: 0 production errors, 20 test infrastructure errors
- 4-phase improvement plan (Baseline → Gradual → Strict)
- Basedpyright best practices and configuration guide

## Curve Segmentation & Endframes

**Multiple Endframes**: Segments containing ENDFRAME points must remain active. When deactivating/splitting segments after endframes, check `any(p.is_endframe for p in segment.points)` before marking inactive - prevents second/subsequent endframes from being incorrectly deactivated (bug fixed in `core/curve_segments.py:536-549, 607-637`).

## Key Design Patterns

1. **Component Container**: 85+ UI attributes organized in `ui/ui_components.py`
2. **Service Singleton**: Thread-safe service instances
3. **Protocol-based**: Type-safe interfaces without tight coupling
4. **Immutable Models**: Thread-safe CurvePoint
5. **Transform Caching**: LRU cache for coordinate transforms
6. **Spatial Indexing**: Grid-based point location

## Development Tips

1. **Check uv availability first**: `which uv` - if not available, use `.venv/bin/python3` directly
2. **Use direct paths in WSL**: `.venv/bin/python3 -m pytest tests/` always works
3. **Type checking**: Use `./bpr` (works with or without uv)
4. **Syntax check first**: `python3 -m py_compile <file>` (no dependencies)
5. **Validate before integration** to prevent silent failures
6. **Prefer None checks over hasattr()** for type safety
7. **Use `pyright: ignore[rule]`** not `type: ignore` for suppressions
8. **Keep uv.lock committed** for reproducible builds
9. **See "Using uv in WSL Environment"** section above for full command translation guide

---
*Last Updated: October 2025*

# Important Reminders
- Do what's asked; nothing more, nothing less
- **NEVER** make assumptions
- ALWAYS prefer editing existing files
- NEVER create documentation unless explicitly requested

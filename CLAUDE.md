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

### Command System
- **CommandManager**: Manages undo/redo history with command pattern
- **Command Classes**:
  - **Curve Commands**: BatchMoveCommand, MovePointCommand, DeletePointsCommand, SetPointStatusCommand, SmoothCommand, AddPointCommand, ConvertToInterpolatedCommand, SetCurveDataCommand
  - **Shortcut Commands**: InsertTrackShortcutCommand, SetEndframeCommand, DeleteCurrentFrameKeyframeCommand, SetTrackingDirectionCommand, CenterViewCommand, FitBackgroundCommand, NudgePointsCommand, SelectAllCommand, DeselectAllCommand, UndoCommand, RedoCommand
  - **Utility Commands**: CompositeCommand, NullCommand, InsertTrackCommand
- **ShortcutRegistry**: Global keyboard shortcut registration and handling
- **GlobalEventFilter**: Application-level keyboard event interception

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

## Reactive Stores (`stores/`)

Single source of truth for application state with Qt signal-based reactivity:

### CurveDataStore
- **Purpose**: Centralized curve data management with automatic UI updates
- **Signals**: `data_changed`, `point_added`, `point_updated`, `point_removed`, `point_status_changed`, `selection_changed`
- **Features**: Batch operation mode, undo/redo stack integration
- **Pattern**: All UI components subscribe to signals for automatic synchronization

### FrameStore
- **Purpose**: Current frame state management
- **Pattern**: Observable state with change notifications
- **Integration**: Syncs with timeline, playback, and curve display

### StoreManager
- **Purpose**: Coordinates multiple stores and ensures consistency
- **Features**: Cross-store validation and transaction coordination

### ConnectionVerifier
- **Purpose**: Validates Qt signal/slot connections during development
- **Features**: Detects orphaned connections and missing slots
- **Usage**: Development-time debugging tool for signal integrity

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
└── venv/           # Python 3.12.3, PySide6==6.4.0
```

## Development Environment

### Linting & Type Checking
```bash
source venv/bin/activate

# Ruff
ruff check . --fix

# Basedpyright (Python wrapper with enhanced features)
./bpr                      # Check all
./bpr --errors-only        # Show only errors
./bpr --summary            # Show just error/warning counts
./bpr ui/main_window.py    # Check specific file
./bpr --check-config       # Check if config excludes irrelevant folders

# Wrapper features: clean piping, JSON output, automatic folder exclusion
```

### Testing
```bash
python -m pytest tests/           # All tests
python -m pytest tests/ -x        # Stop on first failure
python3 -m py_compile <file.py>  # Syntax check
```

## Agent-Assisted Development

**Proactive Agent Usage**: Claude Code provides specialized agents for complex tasks. Use them proactively to improve code quality, catch issues early, and accelerate development.

### Quick Decision Guide

**Ask yourself:**
1. **Simple file operation?** → Use Read/Glob/Grep tools directly
2. **Complex multi-step task?** → Use agents
3. **Multiple independent analyses?** → Use agents **in parallel** (60% faster!)

**When to Use Agents**:
- ✅ **After implementing features**: python-code-reviewer, type-system-expert
- ✅ **Before committing**: python-code-reviewer + type-system-expert in parallel
- ✅ **For complex bugs**: deep-debugger, threading-debugger, qt-concurrency-architect
- ✅ **Performance issues**: performance-profiler
- ✅ **Test coverage**: test-development-master
- ✅ **Refactoring**: code-refactoring-expert → python-code-reviewer verification

**When NOT to Use Agents**:
- ⛔ Reading specific files → Use Read tool
- ⛔ Finding files by name → Use Glob tool
- ⛔ Searching 1-3 files → Use Read/Grep tools

### CurveEditor-Specific Agent Workflows

**User Prompts** (copy to chat):

```text
# After refactoring CurveViewWidget (Week 3 migration)
"Use python-code-reviewer and type-system-expert in parallel to analyze ui/curve_view_widget.py after ApplicationState migration"

# Qt threading safety in controllers
"Use qt-concurrency-architect to verify signal/slot threading safety in ui/controllers/multi_point_tracking_controller.py"

# Performance validation after optimization
"Use performance-profiler to verify 47x rendering speedup is maintained in rendering/optimized_curve_renderer.py"

# Test migration to ApplicationState
"Use test-development-master to update test fixtures in tests/conftest.py for ApplicationState migration"

# Verify data duplication eliminated
"Use code-refactoring-expert to verify no duplicate curve storage remains in ui/ and services/"

# Multi-curve Insert Track feature review
"Use python-code-reviewer to analyze Insert Track implementation in core/commands/insert_track_command.py and core/insert_track_algorithm.py"

# Command system review
"Use python-code-reviewer to verify all commands properly use ApplicationState in core/commands/"

# Full pre-commit review (parallel = 60% faster!)
"Use python-code-reviewer, type-system-expert, and performance-profiler in parallel to audit changes before commit"
```

### Understanding Agent Results

**How results are presented:**
- Agents return findings to Claude (not shown directly to you)
- Claude summarizes results in clear, actionable format
- You receive: analysis reports, code changes, or recommendations

**What to expect from each agent:**

| Agent | What You Get |
|-------|--------------|
| python-code-reviewer | List of bugs, style issues, design problems |
| type-system-expert | Type annotations added + basedpyright errors fixed |
| test-development-master | Test suite with coverage report |
| deep-debugger | Root cause analysis + fix strategy |
| performance-profiler | Bottleneck analysis with metrics |
| code-refactoring-expert | Improved code structure |
| qt-concurrency-architect | Qt-safe threading fixes |

**Acting on results:**
1. Review agent findings
2. Ask clarifying questions if needed
3. Request implementation of fixes
4. Verify changes with tests

**See QUICK-REFERENCE.md for complete agent workflows and decision matrix.**
**See ORCHESTRATION.md for detailed recipes and troubleshooting.**

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

1. **PySide6 Type Stubs**: Not installed (causes expected warnings)
2. **All tests passing**: 1945+ tests fully functional (test suite takes ~2 minutes)

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

1. Always activate venv: `source venv/bin/activate`
2. Use `./bpr` for type checking - enhanced Python wrapper with clean output
3. Check syntax first: `python3 -m py_compile <file>`
4. Validate before integration to prevent silent failures
5. Prefer None checks over hasattr() for type safety
6. Use `pyright: ignore[rule]` not `type: ignore` for suppressions

---
*Last Updated: October 2025*

# Important Reminders
- Do what's asked; nothing more, nothing less
- **NEVER** make assumptions
- ALWAYS prefer editing existing files
- NEVER create documentation unless explicitly requested

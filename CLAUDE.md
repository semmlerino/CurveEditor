# CurveEditor Development Guide

Quick reference for CurveEditor - a Python/PySide6 application for editing animation curves with professional VFX workflow integration.

## Code Quality Standards

1. **Type Safety First**: Use type hints, prefer `None` checks over `hasattr()`
2. **Service Architecture**: 4 services (Data, Interaction, Transform, UI)
3. **Single Source of Truth**: ApplicationState for all data
4. **Protocol Interfaces**: Type-safe duck-typing via protocols
5. **Component Container Pattern**: Access UI via `self.ui.<group>.<widget>`

## Architecture Overview

**See `ARCHITECTURE.md` for detailed architecture documentation.**

### Layers
```
UI Layer          → MainWindow, CurveViewWidget, Controllers
Service Layer     → DataService, InteractionService, TransformService, UIService
State Layer       → ApplicationState (single source of truth)
Core Models       → CurvePoint, PointCollection, Commands
```

### 4 Services

1. **TransformService**: Coordinate transformations, view state (99.9% cache hit rate)
2. **DataService**: Data operations, file I/O, image management
3. **InteractionService**: User interactions, point manipulation, command history
4. **UIService**: UI operations, dialogs, status updates

```python
from services import get_data_service, get_interaction_service, get_transform_service, get_ui_service
```

### Multi-Curve Support

**See `INTERACTIONSERVICE_MULTI_CURVE_ARCHITECTURE.md` for comprehensive API details.**

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

**ApplicationState** is the single source of truth for all data.

```python
from stores.application_state import get_application_state

state = get_application_state()

# Basic operations
state.set_curve_data("Track1", curve_data)
data = state.get_curve_data("Track1")

# Subscribe to changes
state.curves_changed.connect(self._on_data_changed)

# Batch operations (prevent signal storms)
state.begin_batch()
try:
    state.set_curve_data("Track1", data1)
    state.set_curve_data("Track2", data2)
finally:
    state.end_batch()
```

**Migration Complete** (October 2025): All 66 files migrated, 83.3% memory reduction, 14.9x batch speedup, 100% test pass rate.

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

## Selection State

**Two types of selection:**

1. **Curve-Level** (which trajectories to display)
   - `state.get_selected_curves()` / `state.set_selected_curves(set)`
   - `state.get_show_all_curves()` / `state.set_show_all_curves(bool)`

2. **Point-Level** (which frames within active curve)
   - `state.get_selection(curve_name)` / `state.set_selection(curve_name, indices)`

**See `SELECTION_STATE_REFACTORING_TRACKER.md` for migration details.**

## Display Modes

```python
from core.display_mode import DisplayMode

# Display mode is computed from selection state
state.set_show_all_curves(True)   # → DisplayMode.ALL_VISIBLE
state.set_show_all_curves(False)  # → DisplayMode.SELECTED or ACTIVE_ONLY
```

**See `RENDER_STATE_IMPLEMENTATION.md` for rendering details.**

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
├── rendering/      # Optimized rendering (47x faster)
├── services/       # 4 services
├── stores/         # ApplicationState + legacy stores
├── ui/             # MainWindow, widgets, controllers
├── tests/          # 106 test files, 2105+ tests
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

# Testing
uv run pytest tests/
python3 -m py_compile <file.py>  # Quick syntax check
```

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

## Performance

- **Rendering**: 47x faster (viewport culling, LOD, vectorization)
- **Point Queries**: 64.7x faster (spatial indexing)
- **Transforms**: 99.9% cache hit rate
- **State**: 83.3% memory reduction, 14.9x batch speedup

## Key Design Patterns

1. **Component Container**: UI attributes in `ui/ui_components.py`
2. **Service Singleton**: Thread-safe service instances
3. **Protocol-based**: Type-safe interfaces
4. **Immutable Models**: Thread-safe CurvePoint
5. **Transform Caching**: LRU cache
6. **Command Pattern**: Undo/redo support

## Documentation Index

- `ARCHITECTURE.md` - Detailed architecture
- `INTERACTIONSERVICE_MULTI_CURVE_ARCHITECTURE.md` - Multi-curve API
- `SELECTION_STATE_REFACTORING_TRACKER.md` - Selection state details
- `RENDER_STATE_IMPLEMENTATION.md` - Rendering pipeline
- `BASEDPYRIGHT_STRATEGY.md` - Type checking strategy
- `PHASE_8_INTERACTION_SERVICE_REFACTOR.md` - Phase 8 migration
- `QUICK-REFERENCE.md` - Quick command reference

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

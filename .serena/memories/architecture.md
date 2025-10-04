# CurveEditor Architecture

## Core Design Pattern: 4-Service Architecture

The codebase uses a consolidated 4-service architecture with singleton pattern:

### Services (`services/`)
1. **DataService** (`data_service.py`): Data operations, file I/O, image management
2. **InteractionService** (`interaction_service.py`): User interactions, point manipulation, command history
3. **TransformService** (`transform_service.py`): Coordinate transformations, view state (99.9% cache hit rate)
4. **UIService** (`ui_service.py`): UI operations, dialogs, status updates

Access services via:
```python
from services import get_data_service, get_interaction_service, get_transform_service, get_ui_service
```

## State Management: ApplicationState

**Single Source of Truth**: `stores/application_state.py`

- **Pattern**: Singleton with Qt signal-based reactivity
- **Multi-curve native**: `dict[str, CurveDataList]` at core
- **Signals**: `curves_changed`, `selection_changed`, `active_curve_changed`, `frame_changed`, `view_changed`

Usage:
```python
from stores.application_state import get_application_state

state = get_application_state()
state.set_curve_data("curve_name", data)
data = state.get_curve_data("curve_name")
state.curves_changed.connect(self._on_data_changed)
```

## Command System

Undo/redo using command pattern (`core/commands/`):
- **CommandManager**: Manages history
- **Command classes**: MovePointCommand, DeletePointsCommand, SetPointStatusCommand, etc.
- **ShortcutRegistry**: Global keyboard shortcuts
- All operations undoable via Ctrl+Z/Ctrl+Y

## UI Controllers (`ui/controllers/`)

Separation of concerns via specialized controllers:
- **ActionHandlerController**: Menu/toolbar actions
- **MultiPointTrackingController**: Multi-curve tracking, Insert Track
- **TimelineController**: Frame navigation, playback
- **ViewManagementController**: Zoom, pan, fit
- **SignalConnectionManager**: Centralized signal/slot connections

## Core Data Models (`core/models.py`)

```python
@dataclass(frozen=True)
class CurvePoint:
    frame: int
    x: float
    y: float
    status: PointStatus  # NORMAL, INTERPOLATED, KEYFRAME, TRACKED, ENDFRAME
```

**Terminology** (matches 3DEqualizer):
- **"Curve"** = One tracking point's complete trajectory over time
- **"Point"** = Position at a specific frame within a trajectory
- **"Multiple Curves"** = Multiple independent tracking points

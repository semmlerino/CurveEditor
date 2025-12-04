# CurveEditor Architecture

## Core Design Pattern: 4-Service Architecture

The codebase uses a consolidated 4-service architecture with singleton pattern:

### Services (`services/`)
1. **DataService** (`data_service.py`): Data operations, file I/O, image management
2. **InteractionService** (`interaction_service.py`): User interactions, point manipulation, command history
3. **TransformService** (`transform_service.py`, `transform_core.py`): Coordinate transformations, view state (99.9% cache hit rate)
4. **UIService** (`ui_service.py`): UI operations, dialogs, status updates

**Additional Service Components:**
- **SafeImageCacheManager** (`image_cache_manager.py`): Thread-safe image caching with LRU eviction

Access services via:
```python
from services import get_data_service, get_interaction_service, get_transform_service, get_ui_service
```

## Protocol-Based Architecture (`protocols/`)

Type-safe interfaces organized in dedicated package:
- **`protocols/ui.py`**: 16 UI component protocols (MainWindowProtocol, CurveViewProtocol, StateManagerProtocol, etc.)
- **`protocols/data.py`**: Data model protocols (PointProtocol, CurveDataProtocol, ImageProtocol, etc.)
- **`protocols/services.py`**: Service layer protocols (DataServiceProtocol, InteractionServiceProtocol, etc.)

```python
from protocols import MainWindowProtocol, CurveViewProtocol, StateManagerProtocol
```

## State Management

### ApplicationState (`stores/application_state.py`)
**Single Source of Truth** for application data:

- **Pattern**: Singleton with Qt signal-based reactivity
- **Multi-curve native**: `dict[str, CurveDataList]` at core
- **Signals**: `curves_changed`, `selection_changed`, `active_curve_changed`, `frame_changed`, `view_changed`

```python
from stores.application_state import get_application_state

state = get_application_state()
state.set_curve_data("curve_name", data)
data = state.get_curve_data("curve_name")

# Active curve property (recommended)
if (curve_data := state.active_curve_data) is None:
    return
curve_name, data = curve_data  # Safe access
```

### StateManager (`ui/state_manager.py`)
**UI preferences only** (zoom, pan, window state):
- NOT for data access
- Signals: `view_state_changed`, `undo_state_changed`, `tool_state_changed`

### Supporting Stores
- **FrameStore** (`stores/frame_store.py`): Frame state management
- **StoreManager** (`stores/store_manager.py`): Store coordination
- **ConnectionVerifier** (`stores/connection_verifier.py`): Signal connection verification

## Command System (`core/commands/`)

Undo/redo using command pattern:
- **CommandManager**: Manages history
- **CurveDataCommand**: Base class with automatic target storage
- **Command classes**: MovePointCommand, DeletePointsCommand, SetPointStatusCommand, etc.
- **ShortcutRegistry**: Global keyboard shortcuts
- All operations undoable via Ctrl+Z/Ctrl+Y

## UI Controllers (`ui/controllers/`)

13 specialized controllers with separation of concerns:

### Core Controllers
- **ActionHandlerController**: Menu/toolbar actions (uses protocols)
- **PointEditorController**: Point manipulation, selection (uses protocols)
- **TimelineController**: Frame navigation, playback
- **ViewManagementController**: Zoom, pan, fit
- **ViewCameraController**: Camera movement

### Frame Management
- **FrameChangeCoordinator**: Deterministic frame change ordering (eliminates race conditions)

### Tracking Controllers
- **MultiPointTrackingController**: Multi-curve tracking, Insert Track workflow
- **BaseTrackingController**: Tracking base class
- **TrackingDataController**: Tracking data management
- **TrackingDisplayController**: Tracking visualization
- **TrackingSelectionController**: Tracking selection

### UI Setup
- **UIInitializationController**: Component initialization
- **SignalConnectionManager**: Centralized signal/slot connections
- **ProgressiveDisclosureController**: Collapsible UI sections

### CurveView Submodule (`ui/controllers/curve_view/`)
- **CurveDataFacade**: Data access facade
- **RenderCacheController**: Render caching
- **StateSyncController**: State synchronization

## Rendering Pipeline (`rendering/`)

- **OptimizedCurveRenderer**: Main renderer (47x faster than original)
- **RenderState**: Computed render state from widgets
- **VisualSettings**: Centralized visual parameters

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

## Image Loading (`io_utils/`)

- **exr_loader.py**: Multi-backend EXR loading (OIIO, OpenEXR, Pillow, imageio)
- **color_pipeline.py**: Color space handling
- **file_load_worker.py**: Background file loading

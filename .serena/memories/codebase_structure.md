# CurveEditor Codebase Structure

## Directory Organization

```
CurveEditor/
├── core/                    # Core data models, commands, algorithms
│   ├── models.py           # CurvePoint, PointCollection, PointStatus
│   ├── commands/           # Undo/redo command classes
│   ├── insert_track_algorithm.py  # Gap filling logic (3DEqualizer-style)
│   ├── curve_segments.py   # Gap visualization, active/inactive segments
│   ├── coordinate_system.py # Coordinate handling
│   ├── image_sequence.py   # Image sequence detection
│   ├── frame_status_aggregator.py # Frame status computation
│   └── type_aliases.py     # Type definitions
│
├── protocols/              # Type-safe protocol interfaces
│   ├── ui.py              # 16 UI component protocols
│   ├── data.py            # Data model protocols
│   ├── services.py        # Service layer protocols
│   └── __init__.py        # Centralized imports
│
├── services/               # 4-service architecture (singletons)
│   ├── data_service.py     # Data operations, file I/O
│   ├── interaction_service.py  # User interactions, commands
│   ├── transform_service.py    # Coordinate transformations
│   ├── transform_core.py   # Transform implementation
│   ├── ui_service.py       # UI operations, dialogs
│   ├── image_cache_manager.py  # Thread-safe image caching (SafeImageCacheManager)
│   ├── service_protocols.py    # Service interfaces
│   └── __init__.py         # Service getters
│
├── stores/                 # State management
│   ├── application_state.py   # Single source of truth (PRIMARY)
│   ├── frame_store.py      # Frame state
│   ├── store_manager.py    # Store coordination
│   └── connection_verifier.py # Signal connection verification
│
├── io_utils/               # File I/O utilities
│   ├── exr_loader.py       # Multi-backend EXR loading (OIIO, OpenEXR, Pillow, imageio)
│   ├── color_pipeline.py   # Color space handling
│   └── file_load_worker.py # Background file loading
│
├── ui/                     # User interface
│   ├── main_window.py      # Main application window
│   ├── curve_view_widget.py   # Curve display and editing
│   ├── ui_components.py    # Component container (85+ widgets)
│   ├── state_manager.py    # UI preferences (zoom, pan, window state)
│   ├── file_operations.py  # File I/O operations
│   ├── controllers/        # UI controllers (13 specialized + curve_view submodule)
│   │   ├── action_handler_controller.py    # Menu/toolbar actions
│   │   ├── base_tracking_controller.py     # Tracking base class
│   │   ├── frame_change_coordinator.py     # Deterministic frame ordering
│   │   ├── multi_point_tracking_controller.py  # Multi-curve tracking
│   │   ├── point_editor_controller.py      # Point manipulation
│   │   ├── progressive_disclosure_controller.py # Collapsible UI
│   │   ├── signal_connection_manager.py    # Signal/slot connections
│   │   ├── timeline_controller.py          # Frame navigation
│   │   ├── tracking_data_controller.py     # Tracking data management
│   │   ├── tracking_display_controller.py  # Tracking visualization
│   │   ├── tracking_selection_controller.py # Tracking selection
│   │   ├── ui_initialization_controller.py # Component setup
│   │   ├── view_camera_controller.py       # Camera movement
│   │   ├── view_management_controller.py   # Zoom, pan, fit
│   │   └── curve_view/     # CurveView-specific controllers
│   │       ├── curve_data_facade.py        # Data access facade
│   │       ├── render_cache_controller.py  # Render caching
│   │       └── state_sync_controller.py    # State synchronization
│   └── widgets/            # Custom widgets
│       ├── card.py         # Modern card container
│       └── sequence_list_widget.py  # Sequence browser
│
├── rendering/              # Optimized rendering pipeline
│   ├── optimized_curve_renderer.py  # Main renderer
│   ├── render_state.py     # Render state management
│   └── visual_settings.py  # Centralized visual parameters
│
├── data/                   # Data operations
│   └── batch_editor.py     # Batch data editing
│
├── tests/                  # Test suite (174 files, 3100+ tests)
│   ├── conftest.py         # Pytest fixtures
│   ├── fixtures/           # Test fixture modules
│   ├── test_*.py           # Test modules
│   └── ui/                 # UI-specific tests
│
├── main.py                 # Application entry point
├── bpr                     # Basedpyright wrapper script
├── pyproject.toml          # Dependencies, ruff, pytest config
├── basedpyrightconfig.json # Type checking configuration (note: .bak exists)
├── CLAUDE.md               # Development guide
└── .venv/                  # Virtual environment (managed by uv)
```

## Key Files

- **Entry point**: `main.py` - Initializes Qt app and MainWindow
- **Type checking**: `./bpr` - Enhanced basedpyright wrapper
- **State**: `stores/application_state.py` - Single source of truth
- **Services**: `services/__init__.py` - Service access points
- **Models**: `core/models.py` - Core data structures
- **Main UI**: `ui/main_window.py` - Application window
- **Curve widget**: `ui/curve_view_widget.py` - Curve display/editing
- **Image loading**: `io_utils/exr_loader.py` - Multi-backend EXR support
- **Image caching**: `services/image_cache_manager.py` - Thread-safe cache

## Import Patterns

```python
# Services
from services import get_data_service, get_interaction_service

# State
from stores.application_state import get_application_state

# Models
from core.models import CurvePoint, PointStatus, PointCollection

# Protocols
from protocols import MainWindowProtocol, CurveViewProtocol, StateManagerProtocol

# Commands
from core.commands.move_point_command import MovePointCommand
```

## Files to Ignore

Excluded from type checking and linting:
- `venv/`, `.venv/`
- `archive_*/`, `docs/archive/`
- `test_images_output/`, `footage/`
- `*.txt`, `*.md`, `*.bat`, `*.sh`
- `.pytest_cache/`, `__pycache__/`

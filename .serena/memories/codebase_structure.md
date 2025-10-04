# CurveEditor Codebase Structure

## Directory Organization

```
CurveEditor/
├── core/                    # Core data models, commands, algorithms
│   ├── models.py           # CurvePoint, PointCollection, PointStatus
│   ├── commands/           # Undo/redo command classes
│   ├── insert_track_algorithm.py  # Gap filling logic (3DEqualizer-style)
│   └── type_aliases.py     # Type definitions
│
├── services/               # 4-service architecture (singletons)
│   ├── data_service.py     # Data operations, file I/O
│   ├── interaction_service.py  # User interactions, commands
│   ├── transform_service.py    # Coordinate transformations
│   ├── ui_service.py       # UI operations, dialogs
│   ├── service_protocols.py    # Service interfaces
│   └── __init__.py         # Service getters
│
├── stores/                 # State management
│   ├── application_state.py   # Single source of truth (PRIMARY)
│   ├── curve_data_store.py    # Legacy (compatibility only)
│   └── frame_store.py      # Frame state
│
├── ui/                     # User interface
│   ├── main_window.py      # Main application window
│   ├── curve_view_widget.py   # Curve display and editing
│   ├── ui_components.py    # Component container (85+ widgets)
│   ├── file_operations.py  # File I/O operations
│   ├── controllers/        # UI controllers (8 specialized)
│   │   ├── action_handler_controller.py
│   │   ├── multi_point_tracking_controller.py
│   │   ├── timeline_controller.py
│   │   ├── view_management_controller.py
│   │   └── ...
│   └── widgets/            # Custom widgets
│       └── card.py         # Modern card container
│
├── rendering/              # Optimized rendering (47x faster)
│   └── optimized_curve_renderer.py
│
├── data/                   # Data operations
│   └── batch_editor.py     # Batch data editing
│
├── tests/                  # Test suite (106 files, 1945+ tests)
│   ├── conftest.py         # Pytest fixtures
│   ├── test_*.py           # Test modules
│   └── ...
│
├── main.py                 # Application entry point
├── bpr                     # Basedpyright wrapper script
├── pyproject.toml          # Dependencies, ruff, pytest config
├── basedpyrightconfig.json # Type checking configuration
├── CLAUDE.md               # Development guide (THIS FILE)
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

## Import Patterns

```python
# Services
from services import get_data_service, get_interaction_service

# State
from stores.application_state import get_application_state

# Models
from core.models import CurvePoint, PointStatus, PointCollection

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

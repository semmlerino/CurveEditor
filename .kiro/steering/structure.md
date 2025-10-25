# CurveEditor Project Structure

## Top-Level Organization
```
CurveEditor/
├── core/              # Core models and utilities
├── data/              # Data manipulation modules  
├── rendering/         # Rendering components
├── services/          # Service layer (4 core services)
├── ui/               # UI components and main window
├── tests/            # Test suite with organized fixtures
├── main.py           # Application entry point
├── pyproject.toml    # Project config and dependencies
└── uv.lock           # Dependency lockfile
```

## Core Architecture (4-Service Model)

### Services Layer (`services/`)
- **TransformService**: Coordinate transformations and view state management
- **DataService**: All data operations (analysis, file I/O, images)
- **InteractionService**: User interactions, point manipulation, and history
- **UIService**: UI operations, dialogs, and status updates

### UI Layer (`ui/`)
```
ui/
├── controllers/      # MVC controllers
├── protocols/        # UI protocol definitions
├── widgets/          # Reusable UI components
├── main_window.py    # Main application window
├── curve_view_widget.py  # Primary curve editing widget
└── [various UI modules]
```

### Core Layer (`core/`)
- Protocol definitions for interface contracts
- Service registry for dependency management
- Event system for loose coupling
- Path security and validation utilities

### Data Layer (`data/`)
- Data manipulation and processing modules
- File format handlers
- Data validation and analysis

### Rendering Layer (`rendering/`)
- High-performance rendering components
- QPainter optimizations
- Viewport culling and batch rendering

## Key Conventions

### Service Pattern
- Services use singleton pattern with module-level instances
- Thread-safe with RLock for concurrent access
- Protocol-based interfaces for type safety
- No direct imports between services (use service getters)

### UI Components
- Component-based architecture with single responsibility
- Controllers follow MVC pattern
- Protocols define interfaces between UI and services
- Qt-specific naming conventions allowed (N802, N815 ruff ignores)

### File Organization
- `__init__.py` files provide clean public APIs
- Related functionality grouped in packages
- Test files mirror source structure in `tests/`
- Fixtures organized by category in `tests/fixtures/`

### Import Patterns
- Lazy imports in service getters to avoid circular dependencies
- TYPE_CHECKING blocks for forward references
- Protocol imports at module level (always safe)
- Concrete type imports only when needed

## Testing Structure
```
tests/
├── fixtures/         # Organized test fixtures
├── test_*.py        # Test files mirror source structure
└── conftest.py      # Global pytest configuration
```

### Test Categories (Markers)
- `unit`: Fast tests, no Qt dependencies
- `qt_required`: Tests requiring Qt/QApplication
- `integration`: Integration tests
- `production`: Production workflow simulation
- `performance`: Performance and benchmark tests
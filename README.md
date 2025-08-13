# CurveEditor

[![Tests](https://github.com/yourusername/CurveEditor/actions/workflows/tests.yml/badge.svg)](https://github.com/yourusername/CurveEditor/actions/workflows/tests.yml)
[![Quick Check](https://github.com/yourusername/CurveEditor/actions/workflows/quick-check.yml/badge.svg)](https://github.com/yourusername/CurveEditor/actions/workflows/quick-check.yml)
[![codecov](https://codecov.io/gh/yourusername/CurveEditor/branch/main/graph/badge.svg)](https://codecov.io/gh/yourusername/CurveEditor)

A professional Python/PySide6 application for editing animation curves and tracking data with high-performance rendering and intuitive controls.

## Features

### Core Functionality
- **Animation Curve Editing**: Create and edit keyframe animation curves with interpolation
- **Multi-Point Selection**: Select and manipulate multiple points simultaneously
- **Real-time Visualization**: High-performance rendering with optimized QPainter
- **Undo/Redo System**: Full history tracking with unlimited undo/redo
- **Import/Export**: Support for CSV, JSON, and custom curve formats
- **Background Images**: Load reference images for rotoscoping and tracking

### Advanced Features
- **Smooth Operations**: Apply smoothing algorithms to curve data
- **Batch Editing**: Edit multiple points with batch operations
- **Centering & Zoom**: Auto-center curves with intelligent zoom controls
- **Velocity Vectors**: Visualize motion with velocity vector display
- **Grid & Guides**: Optional grid overlay for precise positioning
- **Frame Navigation**: Timeline controls with playback simulation

## Installation

### Prerequisites
- Python 3.12 or higher
- Virtual environment (recommended)

### Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/CurveEditor.git
cd CurveEditor
```

2. Create and activate virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Running the Application
```bash
python main.py
```

### Basic Operations

#### Loading Data
- **File → Open**: Load curve data from CSV or JSON files
- **File → Import Image**: Load background reference image
- Drag and drop supported for quick file loading

#### Editing Curves
- **Click**: Select a point
- **Ctrl+Click**: Add to selection
- **Drag**: Move selected points
- **Right-click**: Context menu with point operations
- **Delete**: Remove selected points
- **Ctrl+Z/Y**: Undo/Redo

#### View Controls
- **Mouse Wheel**: Zoom in/out
- **Middle Mouse Drag**: Pan view
- **Home**: Reset view
- **F**: Frame selected points
- **G**: Toggle grid
- **V**: Toggle velocity vectors

#### Timeline
- **Space**: Play/Pause animation
- **Left/Right Arrow**: Previous/Next frame
- **Shift+Arrow**: Jump 10 frames
- Use slider or spinbox for direct frame navigation

## Architecture

### Service Architecture (4-Service Model)

```
┌─────────────────────────────────────────────┐
│              UI Layer                       │
│  (MainWindow, CurveViewWidget, Controllers) │
└─────────────────────────────────────────────┘
                    │
    ┌───────────────┼───────────────┬───────────────┐
    ▼               ▼               ▼               ▼
┌─────────┐ ┌─────────────┐ ┌──────────────┐ ┌──────────┐
│Transform│ │DataService  │ │Interaction   │ │UIService │
│Service  │ │             │ │Service       │ │          │
└─────────┘ └─────────────┘ └──────────────┘ └──────────┘
```

#### Service Responsibilities

1. **TransformService**: Coordinate transformations and view state
   - Screen ↔ Data coordinate conversion
   - Zoom and pan operations
   - View state management

2. **DataService**: Data operations and I/O
   - Curve data management
   - File operations (load/save)
   - Data validation and analysis
   - Image cache management

3. **InteractionService**: User interactions
   - Mouse/keyboard handling
   - Point selection and manipulation
   - History/undo management
   - Edit operations

4. **UIService**: UI operations
   - Dialog management
   - Status updates
   - Component coordination
   - Settings persistence

### Component Architecture

The UI uses a component-based architecture with specialized managers:

- **CurveRenderer**: Handles all rendering operations
- **SelectionManager**: Manages point selection
- **InteractionHandler**: Processes user input
- **TransformManager**: Manages view transformations
- **CurveDataManager**: Handles curve data operations

## Development

### Project Structure

```
CurveEditor/
├── core/              # Core models and utilities
├── data/              # Data manipulation modules
├── rendering/         # Rendering components
├── services/          # Service layer (4 services)
├── ui/               # UI components and main window
│   ├── components/   # Refactored UI components
│   └── controllers/  # MVC controllers
├── tests/            # Test suite
│   └── fixtures/     # Organized test fixtures
├── main.py           # Application entry point
└── requirements.txt  # Dependencies
```

### Testing

Run the test suite:
```bash
# All tests
pytest tests/

# Specific test file
pytest tests/test_curve_service.py -v

# With coverage
pytest --cov=. --cov-report=html tests/
```

### Code Quality

#### Linting with Ruff
```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check . --fix
```

#### Type Checking with Basedpyright
```bash
# Use the wrapper script (avoids shell redirection bug)
./bpr

# Check specific files
./bpr ui/main_window.py services/
```

### Development Guidelines

1. **Service Singletons**: Services use singleton pattern with module-level instances
2. **Protocol Interfaces**: Use protocols for type safety across services
3. **Component Pattern**: UI components should be focused and single-responsibility
4. **Immutable Transforms**: Transform objects are immutable for consistency
5. **Thread Safety**: Services use RLock for thread-safe operations

## Configuration

### Settings File
User preferences stored in: `~/.curveEditor/settings.json`

### Configurable Options
- Default point radius and colors
- Grid spacing and appearance
- Auto-save interval
- Performance settings
- UI theme preferences

## Performance

### Optimizations
- **Batch Rendering**: Points rendered in batches for performance
- **Dirty Flag System**: Only redraw when necessary
- **Viewport Culling**: Only render visible points
- **Cached Transforms**: Transform matrices cached
- **Lazy Loading**: Images loaded on demand

### Benchmarks
- Handle 10,000+ points smoothly
- 60 FPS rendering on modern hardware
- Sub-millisecond coordinate transformations
- Memory efficient with large datasets

## Troubleshooting

### Common Issues

#### Application Won't Start
- Ensure Python 3.12+ is installed
- Check all dependencies are installed: `pip install -r requirements.txt`
- Verify PySide6 installation: `python -c "import PySide6"`

#### Performance Issues
- Disable velocity vectors for large datasets
- Reduce point radius in settings
- Enable viewport culling in preferences

#### File Loading Errors
- Check file format (CSV should have frame,x,y columns)
- Ensure file permissions are correct
- Validate JSON structure for JSON files

## Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run tests and linting: `pytest tests/ && ruff check .`
5. Commit with descriptive message
6. Push and create pull request

### Code Style
- Follow PEP 8 guidelines
- Use type hints for all functions
- Add docstrings to public methods
- Keep functions focused and small
- Write tests for new features

## License

MIT License - See LICENSE file for details

## Credits

Developed by [Your Name]
Built with PySide6 and Python

## Version History

### v2.0.0 (2024)
- Major refactoring to 4-service architecture
- Component-based UI redesign
- Performance optimizations
- Comprehensive test suite

### v1.0.0 (2023)
- Initial release
- Basic curve editing functionality
- File import/export
- Undo/redo system

---

For bug reports and feature requests, please use the GitHub issue tracker.

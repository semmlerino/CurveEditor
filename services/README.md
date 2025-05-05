# CurveEditor Services

This directory contains the service layer implementations for the CurveEditor application. The service-based architecture provides a clear separation of concerns and improves code organization, maintainability, and testability.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         UI Components                           │
│  ┌───────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │ MainWindow│  │ CurveView  │  │ Timeline   │  │ Controls   │  │
│  └─────┬─────┘  └──────┬─────┘  └──────┬─────┘  └──────┬─────┘  │
└────────┼────────────────┼──────────────┼───────────────┼────────┘
          │               │              │               │
          ▼               ▼              ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Service Layer                           │
│  ┌───────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │CurveService│  │ImageService│  │FileService │  │HistoryService│
│  └───────────┘  └────────────┘  └────────────┘  └────────────┘  │
│  ┌───────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │DialogSvc  │  │AnalysisSvc │  │SettingsSvc │  │VisualSvc   │  │
│  └───────────┘  └────────────┘  └────────────┘  └────────────┘  │
└────────┬────────────────┬──────────────┬───────────────┬────────┘
          │               │              │               │
          ▼               ▼              ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                          Data Layer                             │
│  ┌───────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │
│  │ Curve Data│  │Image Data  │  │ Settings   │  │History Data│  │
│  └───────────┘  └────────────┘  └────────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Service Architecture

The CurveEditor application follows a service-based architecture where each service is responsible for a specific domain of functionality. Services are implemented as classes with static methods to provide a functional interface.

### Service Pattern

Services follow this standard pattern:

```python
from services.some_service import SomeService as LegacyName
```

This pattern ensures backward compatibility while moving to a cleaner architecture.

## Available Services

| Service | Description | Legacy Equivalent | Status |
|---------|-------------|------------------|--------|
| `CurveService` | Curve view and point manipulation operations | CurveViewOperations | ✅ Complete |
| `AnalysisService` | Curve data analysis and manipulation | CurveDataOperations | ✅ Complete |
| `CenteringZoomService` | View centering and zoom operations | ZoomOperations | ✅ Complete |
| `InputService` | Keyboard and mouse input handling | N/A | ✅ Complete |
| `TransformationService` | Coordinate transformation between spaces | N/A | ✅ Complete |
| `VisualizationService` | Visualization features (grid, vectors, crosshair) | VisualizationOperations | ✅ Complete |
| `ImageService` | Image sequence handling and manipulation | ImageOperations | ✅ Complete |
| `FileService` | File loading and saving operations | FileOperations | ✅ Complete |
| `HistoryService` | Undo/redo and history management | HistoryOperations | ✅ Complete |
| `DialogService` | Dialog management and UI interactions | DialogOperations | ✅ Complete |
| `SettingsService` | Application settings management | SettingsOperations | ✅ Complete |
| `LoggingService` | Centralized logging system | N/A | ✅ Complete |

## Implementation Notes

Most services follow a phase-based implementation approach:

1. **Phase 1**: Create a service facade that forwards to the legacy implementation
2. **Phase 2**: Migrate functionality directly into the service class
3. **Phase 3**: Enhance with better type hints and documentation
4. **Phase 4**: Implement protocol-based interfaces for improved type safety

## Protocol System

The CurveEditor services now use a comprehensive protocol system to enforce consistent interfaces and improve type safety. All services have been updated to use protocol types for their method signatures, which provides:

- Strong type checking for method parameters
- Enhanced IDE support for completion and documentation
- Direct property access instead of `getattr()` calls
- Consistent interfaces across components

See the [Protocol System Documentation](../docs/protocol_system.md) for details on the available protocols and how to use them.

## Usage Examples

### Curve Operations

```python
from services.curve_service import CurveService

# Select a point
CurveService.select_point_by_index(curve_view, main_window, index)

# Update point position
CurveService.update_point_position(curve_view, main_window, index, x, y)
```

### Image Operations

```python
from services.image_service import ImageService

# Load image sequence
ImageService.load_image_sequence(main_window)

# Set current image by frame
ImageService.set_current_image_by_frame(curve_view, frame)
```

### Analysis Operations

```python
from services.analysis_service import AnalysisService

# Smooth curve data
smoothed_data = AnalysisService.smooth_curve(
    curve_data,
    indices=[0, 1, 2, 3],
    method='gaussian',
    window_size=5
)

# Fill gaps in data
filled_data = AnalysisService.fill_gap(
    curve_data,
    start_frame=10,
    end_frame=20,
    method='cubic_spline'
)
```

### Logging Operations

```python
from services.logging_service import LoggingService

# Get a logger for a specific module
logger = LoggingService.get_logger("my_module")

# Use different log levels
logger.debug("Detailed debugging information")
logger.info("General operational information")
logger.warning("Warning about potential issues")
logger.error("Error that prevents functionality")
logger.critical("Critical error that requires immediate attention")

# Configure logging globally
LoggingService.setup_logging(
    level="INFO",                      # Global log level
    log_file="~/.curve_editor/logs/curve_editor.log",  # Log file location
    console=True                       # Also output to console
)

# Set module-specific log levels
LoggingService.set_module_level("curve_view", "DEBUG")
LoggingService.set_module_level("services.curve_service", "DEBUG")
```

## Adding New Services

When adding a new service:

1. Create a new file in the `services` directory with the naming pattern `*_service.py`
2. Implement a class with a name ending in `Service`
3. Use static methods for all functionality
4. Add proper type hints and docstrings using the protocol system
5. Register in this README.md file

## Testing Services

Services are designed to be easily testable. Test files should be placed in the `tests` directory and follow the naming pattern `test_*_service.py`.

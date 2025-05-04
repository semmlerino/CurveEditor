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
| `VisualizationService` | Visualization features (grid, vectors, crosshair) | VisualizationOperations | ⏳ In Progress |
| `ImageService` | Image sequence handling and manipulation | ImageOperations | ⏳ In Progress |
| `FileService` | File loading and saving operations | FileOperations | ⏳ In Progress |
| `HistoryService` | Undo/redo and history management | HistoryOperations | ⏳ In Progress |
| `DialogService` | Dialog management and UI interactions | DialogOperations | ⏳ In Progress |
| `SettingsService` | Application settings management | SettingsOperations | ⏳ In Progress |
| `LoggingService` | Centralized logging system | N/A | ✅ Complete |

## Implementation Notes

Most services follow a phase-based implementation approach:

1. **Phase 1**: Create a service facade that forwards to the legacy implementation
2. **Phase 2**: Migrate functionality directly into the service class
3. **Phase 3**: Enhance with better type hints and documentation

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
image_files = ImageService.load_image_sequence(directory_path)

# Display an image
ImageService.display_image(image_files[0], curve_view)
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
4. Add proper type hints and docstrings
5. Register in this README.md file

## Testing Services

Services are designed to be easily testable. Test files should be placed in the `tests` directory and follow the naming pattern `test_*_service.py`.

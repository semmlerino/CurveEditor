# CurveEditor

CurveEditor is an interactive Qt-based application for creating, editing, and visualizing tracking curves for 3D camera tracking data.

## Architecture

CurveEditor uses a service-based architecture to maintain clean separation of concerns and improve maintainability:

- **UI Layer**: Qt-based user interface components
- **Service Layer**: Business logic organized by domain ([service documentation](services/README.md))
- **Data Layer**: Data structures and persistence

## Documentation

### Architecture
- [Architecture Overview](docs/architecture.md)
- [Refactoring Guide](docs/refactoring_guide.md)
- [Services Reference](services/README.md)
- [Refactoring Status](refactoring_status.md) (NEW - consolidated status report)

### Development Plans
- [Implementation Progress](docs/implementation_progress.md)
- [Debug Cleanup Plan](docs/debug_cleanup_plan.md)
- [Service Testing Plan](docs/service_testing_plan.md)

### Technical Guides
- [Feature Catalogue](docs/features.md)
- [Coordinate Transformation Guide](docs/coordinate_transformation_guide.md)
- [Logging Guide](docs/logging_guide.md)
- [Logging Migration Guide](docs/logging_migration_guide.md) (NEW)
- [Testing Guide](docs/testing_guide.md)

## Recent Changes

- ✅ Completed migration to service-based architecture
- ✅ Added comprehensive service interfaces for all core functionality
- ✅ Standardized import patterns for consistency
- ✅ Improved module organization and reduced duplication
- ✅ Enhanced error handling and type annotations
- ✅ Removed all deprecated files from codebase
- ✅ Added proper logging throughout service implementations
- ✅ Consolidated duplicate code in coordinate transformation logic

## Current Status

The refactoring to a service-based architecture is now complete. All major functionality has been migrated to appropriate service classes, all deprecated files have been removed, and debug prints have been replaced with proper logging across all service implementations.

For detailed metrics and next steps, see the [Refactoring Status](refactoring_status.md) document.

### Major Updates (May 2025)

- **Initial Refactoring**:
  - Fixed legacy imports to use service-based architecture
  - Created documentation and validation tools
  - Added debug cleanup and logging system

- **Latest Improvements (May 5, 2025)**:
  - Completed debug cleanup across all service implementations
  - Removed all deprecated files from codebase
  - Modernized service import patterns
  - Consolidated duplicate code for coordinate transformations

See [Refactoring Status](refactoring_status.md) for current metrics and detailed plans.

### Future Development

The project roadmap is organized into short, medium, and long-term goals. For details, see the [Refactoring Status](refactoring_status.md) document.

## Services

The application uses the following services:

| Service | Description | Status |
|---------|-------------|--------|
| `CurveService` | Curve view and point manipulation | ✅ Complete |
| `AnalysisService` | Curve data analysis and manipulation | ✅ Complete |
| `CenteringZoomService` | View centering and zoom operations | ✅ Complete |
| `InputService` | Keyboard and mouse input handling | ✅ Complete |
| `LoggingService` | Centralized logging system | ✅ Complete |
| `VisualizationService` | Grid, vectors, and display features | ✅ Complete |
| `ImageService` | Image sequence handling | ⏳ In Progress |
| `FileService` | File I/O operations | ⏳ In Progress |
| `HistoryService` | Undo/redo functionality | ⏳ In Progress |
| `DialogService` | UI dialog management | ⏳ In Progress |
| `SettingsService` | Application settings management | ⏳ In Progress |

For more details on the service architecture, including implementation status and usage examples, see the [services documentation](services/README.md).

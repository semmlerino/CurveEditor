# CurveEditor

CurveEditor is an interactive Qt-based application for creating, editing, and visualizing tracking curves for 3D camera tracking data.

## Architecture

CurveEditor uses a service-based architecture to maintain clean separation of concerns and improve maintainability:

- **UI Layer**: Qt-based user interface components
- **Service Layer**: Business logic organized by domain ([service documentation](services/README.md))
- **Data Layer**: Data structures and persistence

## Documentation

- [Architecture Overview](docs/architecture.md)
- [Feature Catalogue](docs/features.md)
- [Refactoring Notes](docs/refactoring_notes.md)
- [Code Consolidation](docs/code_consolidation.md)
- [Coordinate Transformation Guide](docs/coordinate_transformation_guide.md)
- [Services Reference](services/README.md)

## Recent Changes

- ✅ Completed migration to service-based architecture
- ✅ Added comprehensive service interfaces for all core functionality
- ✅ Standardized import patterns for consistency
- ✅ Improved module organization and reduced duplication
- ✅ Enhanced error handling and type annotations
- ✅ Added validation tools for architecture compliance
- ✅ Updated documentation to reflect current architecture
- ✅ Added detailed next steps for ongoing development
- ✅ Completed code consolidation:
  - ✅ Fixed circular imports between services
  - ✅ Renamed all legacy operations files to .deprecated
  - ✅ Created proper deprecation stubs with clear warnings

## Current Status

The refactoring to a service-based architecture is now complete. All major functionality has been migrated to appropriate service classes, with legacy operations modules either renamed to `.deprecated` or replaced with forwarding stubs that provide proper deprecation warnings.

The code consolidation phase has also been completed:
- All legacy operations files have been properly renamed with the `.deprecated` extension
- Circular dependencies between services have been resolved
- Import patterns have been standardized across the codebase
- Proper deprecation warnings have been added to all legacy files

The documentation has been updated to reflect the current architecture, including updated workflow diagrams, service descriptions, and next steps for further development. A detailed [Code Consolidation](docs/code_consolidation.md) document has been created to summarize the changes made.

## Services

The application uses the following services:

| Service | Description |
|---------|-------------|
| `CurveService` | Curve view and point manipulation |
| `ImageService` | Image sequence handling |
| `VisualizationService` | Grid, vectors, and display features |
| `CenteringZoomService` | View centering and zoom operations |
| `AnalysisService` | Curve data analysis and manipulation |
| `HistoryService` | Undo/redo functionality |
| `FileService` | File I/O operations |
| `DialogService` | UI dialog management |
| `SettingsService` | Application settings management |

For more details on the service architecture, see the [services documentation](services/README.md).

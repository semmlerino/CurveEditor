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
- [Coordinate Transformation Guide](docs/coordinate_transformation_guide.md)
- [Services Reference](services/README.md)

## Recent Changes

- Completed migration to service-based architecture
- Added comprehensive service interfaces for all core functionality
- Standardized import patterns for consistency
- Improved module organization and reduced duplication
- Enhanced error handling and type annotations
- Added validation tools for architecture compliance

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

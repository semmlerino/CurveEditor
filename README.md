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
- [Refactoring Notes](docs/refactoring_notes.md)
- [Code Consolidation](docs/code_consolidation.md)
- [Services Reference](services/README.md)

### Development Plans
- [Debug Cleanup Plan](docs/debug_cleanup_plan.md)
- [Service Testing Plan](docs/service_testing_plan.md)
- [Implementation Progress](docs/implementation_progress.md) (NEW)
- [Refactoring Update Summary](refactoring_update_summary.md)

### Technical Guides
- [Feature Catalogue](docs/features.md)
- [Coordinate Transformation Guide](docs/coordinate_transformation_guide.md)
- [Logging Guide](docs/logging_guide.md)
- [Testing Guide](docs/testing_guide.md)

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

### May 2025 Updates

#### Initial Review (Early May 2025)
A code review has been completed with the following improvements:
- Fixed remaining legacy imports to use the service-based architecture
- Enhanced documentation with detailed [Refactoring Notes](docs/refactoring_notes.md)
- Improved validation tools for architecture compliance
- Created a comprehensive [Refactoring Update Summary](refactoring_update_summary.md)

#### Latest Updates (May 4, 2025)
Additional improvements have been implemented:
- Fixed redundant import in `curve_view.py` resetView() method
- Updated documentation in [Refactoring Notes](docs/refactoring_notes.md) with clearer next steps
- Created [Debug Cleanup Plan](docs/debug_cleanup_plan.md) for handling debug statements
- Created [Service Testing Plan](docs/service_testing_plan.md) for verifying architecture
- Enhanced architecture documentation with more detailed timelines and priorities

#### Implementation Progress (May 4, 2025 - Continued)
The implementation of improvement plans has begun:
- Created `LoggingService` to provide centralized logging system
- Replaced debug prints in `curve_view.py` with proper logging
- Created comprehensive test suite for `CurveService` and `AnalysisService`
- Implemented test runner with coverage reporting capabilities
- Added [Implementation Progress](docs/implementation_progress.md) tracker

#### Latest Implementation (May 4, 2025 - Evening)
Additional implementation progress:
- Added debug cleanup for `main_window.py`
- Created comprehensive test suite for `CenteringZoomService`
- Implemented logging configuration system with JSON support
- Updated main application to use configurable logging
- Enabled per-module log level configuration
- Created comprehensive logging guide documentation
- Added testing guide with detailed instructions for running and creating tests
- Updated services documentation to include LoggingService
- Cleaned up project by removing obsolete components

### Future Development

The project roadmap has been organized into short, medium, and long-term goals:

#### Short-term (0-1 month)
- Clean up debug print statements according to [Debug Cleanup Plan](docs/debug_cleanup_plan.md)
- Implement comprehensive test suite following [Service Testing Plan](docs/service_testing_plan.md)
- Enhance validation tools to verify architecture compliance
- Implement proper logging system to replace debug prints

#### Medium-term (1-3 months)
- Remove `.deprecated` files once all functionality is verified
- Enhance error handling and recovery mechanisms
- Optimize performance in key areas identified during testing
- Update user-facing documentation to reflect architectural changes

#### Long-term (3+ months)
- Define explicit interfaces for all services
- Create comprehensive API documentation
- Implement dependency injection for better testability
- Evolve to a plugin-based architecture for extensibility

For full details on the development roadmap, see the [Refactoring Notes](docs/refactoring_notes.md), [Debug Cleanup Plan](docs/debug_cleanup_plan.md), and [Service Testing Plan](docs/service_testing_plan.md).

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

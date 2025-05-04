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
- [Refactoring Guide](docs/refactoring_guide.md) (NEW - consolidated reference)
- [Services Reference](services/README.md)

### Development Plans
- [Implementation Progress](docs/implementation_progress.md)
- [Debug Cleanup Plan](docs/debug_cleanup_plan.md)
- [Service Testing Plan](docs/service_testing_plan.md)

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
- Added debug cleanup for `main_window.py` and `enhanced_curve_view.py`
- Created comprehensive test suites for `CurveService`, `AnalysisService`, `CenteringZoomService`, and `InputService`
- Implemented logging configuration system with JSON support
- Updated main application to use configurable logging with per-module log levels
- Created comprehensive logging guide documentation with configuration instructions
- Added testing guide with detailed instructions for running and creating tests
- Updated services documentation to include implementation status
- Cleaned up project by removing obsolete components
- Added initial UI component tests in `test_main_window.py`

#### Current Status (Updated May 4, 2025 - Night)
- Debug print cleanup: ~60% complete (focused on core components)
- Test coverage: ~45% overall (core services at 75-85%)
- Services implementation: 5 complete, 6 in progress
- Documentation: All major systems documented with comprehensive guides

### Future Development

The project roadmap has been organized into short, medium, and long-term goals:

#### Short-term (0-1 month)
- Complete VisualizationService tests (highest priority)
- Finish debug cleanup in service implementations
- Complete test implementation for remaining services
- Add integration tests between services (especially CurveService and HistoryService)
- Enhance validation tools to verify architecture compliance

#### Medium-term (1-3 months)
- Remove `.deprecated` files once all functionality is verified
- Enhance error handling and recovery mechanisms
- Optimize performance in key areas identified during testing
- Update user-facing documentation to reflect architectural changes
- Implement log rotation and environment variable support for logging

#### Long-term (3+ months)
- Define explicit interfaces for all services
- Create comprehensive API documentation
- Implement dependency injection for better testability
- Evolve to a plugin-based architecture for extensibility

For full details on the development roadmap, see the [Refactoring Notes](docs/refactoring_notes.md), [Debug Cleanup Plan](docs/debug_cleanup_plan.md), and [Service Testing Plan](docs/service_testing_plan.md).

## Services

The application uses the following services:

| Service | Description | Status |
|---------|-------------|--------|
| `CurveService` | Curve view and point manipulation | ✅ Complete |
| `AnalysisService` | Curve data analysis and manipulation | ✅ Complete |
| `CenteringZoomService` | View centering and zoom operations | ✅ Complete |
| `InputService` | Keyboard and mouse input handling | ✅ Complete |
| `LoggingService` | Centralized logging system | ✅ Complete |
| `VisualizationService` | Grid, vectors, and display features | ⏳ In Progress |
| `ImageService` | Image sequence handling | ⏳ In Progress |
| `FileService` | File I/O operations | ⏳ In Progress |
| `HistoryService` | Undo/redo functionality | ⏳ In Progress |
| `DialogService` | UI dialog management | ⏳ In Progress |
| `SettingsService` | Application settings management | ⏳ In Progress |

For more details on the service architecture, including implementation status and usage examples, see the [services documentation](services/README.md).

# 3DE4 Curve Editor Documentation

## Overview

The 3DE4 Curve Editor is a specialized application designed for editing 2D tracking curves used in visual effects and camera tracking workflows. It allows users to load, visualize, edit, and save 2D tracking data, with support for image sequence backgrounds to provide visual context for the tracking points. The application includes a configuration system that remembers the last used file and folder paths for a smoother workflow. The editor features a robust coordinate transformation system that properly aligns tracking points with background images, ensuring accurate visual feedback during the editing process.

## Framework and Dependencies

The application is built using the following technologies:

1. **Python 3.12**: Core programming language
2. **PySide6**: Qt binding for the GUI framework, replacing the previously used PyQt5
3. **NumPy**: For numerical operations and data manipulation
4. **PIL/Pillow**: For image processing and loading

## Application Structure

The application follows a modular architecture with clear separation of concerns:

### Main Components

1. **Main Entry Point** (`main.py`)
   - Initializes the Qt application and main window
   - Entry point for the application

2. **Main Window** (`main_window.py`)
   - Central component that integrates all UI elements and functionality
   - Manages application state and data flow
   - Delegates specific operations to specialized utility classes
   - Handles keyboard events and shortcuts
   - **Refactored to minimize redundancy** by directly connecting signals to utility class methods

3. **Curve View** (`curve_view.py`)
   - Custom widget for visualizing and interacting with tracking curves
   - Handles rendering of points, curves, and background images
   - Manages user interactions like point selection, dragging, and zooming
   - Implements precise coordinate transformation between image space and widget space
   - Supports image sequence backgrounds
   - Provides visual feedback with information overlays

4. **Enhanced Curve View** (`enhanced_curve_view.py`)
   - Extended version of the standard curve view with additional visualization options
   - Supports grid display, velocity vectors, and frame number visualization
   - Implements wheel event handling for zooming with proper position tracking
   - Provides advanced visual feedback for tracking quality analysis
   - **Interpolated Points** feature allows "soft deletion" of points while maintaining navigation
   - **Refactored to delegate functionality** to specialized utility classes through dynamic imports

### Service-Based Architecture

The application has been refactored to follow a service-based architecture where functionality is centralized in specialized service classes rather than duplicated in the MainWindow class. This improves code maintainability, testability, and organization.

#### Key Services

1. **CurveService** (`services/curve_service.py`)
   - Handles all operations related to the curve view widget
   - Manages point selection, editing, and manipulation
   - Provides methods for view controls like reset view and zooming
   - Used directly through signal connections from UI elements
   - **Enhanced Curve View Integration**: Provides specialized methods for the enhanced curve view:
     - `find_point_at`: Finds a point at a given position
     - `finalize_selection`: Handles multi-selection rectangle functionality
     - `get_point_data`: Retrieves point data in a consistent format
     - `is_point_interpolated`: Checks if a point has interpolated status
     - `toggle_point_interpolation`: Toggles a point's interpolation status
     - `update_point_position`: Updates a point's position while preserving its status
     - `transform_point`: Transforms coordinates between different coordinate systems
     - `nudge_selected_points`: Applies nudging to selected points

2. **VisualizationService** (`services/visualization_service.py`)
   - Centralizes all visualization-related functionality
   - Controls grid, vectors, and frame number display
   - Manages background image visibility and opacity
   - Provides unified view centering and navigation methods via `CenteringZoomService`
   - **Enhanced Curve View Integration**: Provides specialized methods for visualization features:
     - `toggle_grid`: Toggles grid visibility
     - `set_point_radius`: Controls the size of points in the view
     - `set_grid_color`: Manages grid color settings
     - `set_grid_line_width`: Controls grid line thickness
     - `update_timeline_for_image`: Synchronizes timeline with image navigation

3. **UIComponents** (`ui_components.py`)
   - Creates and organizes UI elements
   - Builds toolbar, timeline controls, and editing panels
   - Manages the timeline slider and frame navigation
   - Synchronizes timeline with point selection and image display
   - Provides structured containers for different UI sections (point editing, view controls)

4. **FileService** (`services/file_service.py`)
   - Handles loading and saving track data
   - Manages file dialogs and data parsing
   - Provides standardized interfaces for file operations

5. **ImageService** (`services/image_service.py`)
   - Manages loading and display of image sequences
   - Controls image navigation and background visibility
   - Provides image processing and caching utilities

6. **HistoryService** (`services/history_service.py`)
   - Implements undo/redo functionality
   - Manages state history for tracking changes
   - Provides methods for recording and replaying operations

7. **AnalysisService** (`services/analysis_service.py`)
   - Implements curve analysis and editing algorithms
   - Provides smoothing, filtering, gap filling, and extrapolation
   - Implements problem detection for tracking quality analysis
   - Centralizes batch operations on curve data

8. **DialogService** (`services/dialog_service.py`)
   - Centralizes dialog creation and management
   - Handles parameter collection and validation
   - Ensures consistent dialog behavior throughout the application

9. **CenteringZoomService** (`services/centering_zoom_service.py`)
   - Manages view centering and zoom operations
   - Provides standardized view navigation methods
   - Handles coordinate transformation for zooming and panning

10. **SettingsService** (`services/settings_service.py`)
    - Manages application settings and preferences
    - Handles loading and saving of user configurations
    - Provides centralized access to application settings

11. **InputService** (`services/input_service.py`)
    - Manages keyboard and mouse input handling
    - Provides consistent keyboard shortcut management
    - Centralizes input processing logic

### Additional Modules

1. **Keyboard Shortcuts** (`keyboard_shortcuts.py`)
   - Manages keyboard shortcut setup and handling
   - Centralizes all shortcut definitions and connections

2. **Batch Edit** (`batch_edit.py`)
   - Provides functionality for batch operations on multiple points
   - Implements scaling, offsetting, and rotating groups of points

3. **Quick Filter Presets** (`quick_filter_presets.py`)
   - Defines and applies predefined filter settings for common operations
   - Provides efficient workflow for standard filtering tasks

4. **Track Quality** (`track_quality.py`)
   - Analyzes tracking data for quality assessment
   - Identifies potential issues and provides recommendations

5. **Utilities** (`utils.py`)
   - Common utility functions
   - Data loading/saving helpers

6. **Configuration** (`config.py`)
   - Manages application settings and preferences
   - Stores and retrieves the last opened file and folder paths
   - Uses JSON format for persistent storage in app_config.json

7. **Dialogs** (`dialogs.py`)
   - Specialized dialog windows for various operations
   - Includes smoothing, filtering, gap filling, and problem detection dialogs

## Key Features

### Track Data Management

- **Loading Tracks**: Load 2D tracking data from text files
- **Saving Tracks**: Save modified tracking data back to files
- **Multiple Tracks**: Support for loading multiple tracks
- **Session Persistence**: Remembers the last opened file and folder paths

### Visualization

- **Curve Display**: Visualization of tracking points and interpolated curves
- **Image Backgrounds**: Support for loading and displaying image sequences as backgrounds
   - Supports various image naming conventions (name.1234.ext or name_1234.ext)
   - Automatic frame number detection from filenames
   - Image sequence navigation with keyboard shortcuts
   - Proper scaling and alignment with tracking data coordinates
   - Adjustable opacity for better visualization

- **Enhanced Visualization Options**:
   - Toggle grid display for better spatial reference
   - Show velocity vectors to visualize point movement
   - Display frame numbers for all points
   - Analyze tracking quality with visual indicators

- **View Navigation**:
   - Middle mouse button panning for easy view navigation
   - Mouse wheel zooming centered on cursor position
   - Reset view functionality with 'R' key

- **Information Overlay**: Real-time display of zoom level, selected points, and image information

### Editing Tools

- **Point Editing**: Direct manipulation of tracking points
- **Batch Editing**: Scale, offset, and rotate multiple points at once
- **Selection Tools**: Select all points or specific ranges for bulk operations
- **Smoothing**: Algorithms for smoothing tracking curves
- **Gap Filling**: Tools to interpolate missing tracking data
- **Filtering**: Noise reduction and filtering options with quick presets
- **Extrapolation**: Extend tracking data beyond available frames
- **Track Quality Analysis**: Analyze tracking quality with metrics for smoothness, consistency, and coverage

### Timeline Navigation

- **Frame Navigation**: Timeline slider for navigating through frames
- **Frame Synchronization**: Synchronization between timeline, points, and background images
- **Timeline Integration**: Timeline functionality fully integrated into the UI Components system for better cohesion
- **Timeline Methods**:
  - `setup_timeline`: Configures the timeline slider based on frame range in the curve data
  - `on_timeline_changed`: Handles timeline slider value changes, updates frame display, and selects corresponding points
  - `on_frame_edit_changed`: Processes manual frame number input and updates the timeline position

### History Management

- **Undo/Redo**: Support for undoing and redoing editing operations
- **History Stack**: Maintains a history of changes for reverting

## Service-Based Refactoring

The application has been significantly refactored to use a service-based architecture for improved code organization and maintainability:

1. **Standardized Import Pattern**:
   - Core application components now import services using a consistent pattern
   - Example: `from services.curve_service import CurveService`
   - For backward compatibility, legacy imports are supported with alias syntax:
     - `from services.curve_service import CurveService as CurveViewOperations`
   - This approach ensures a smooth transition while maintaining a clear architecture

2. **Service Delegation**:
   - Core functionality is implemented in service classes with static methods
   - UI components act as facades, providing a consistent API while delegating implementation to services
   - This pattern reduces code duplication and centralizes implementation in specialized service classes
   - Methods like `update_point_position`, `find_point_at`, and `toggle_grid` now delegate to appropriate services

3. **Legacy Code Handling**:
   - Legacy operations files have been refactored in three ways:
     - Renamed to `.deprecated` to clearly mark end-of-life
     - Replaced with forward stubs that redirect to service implementations with deprecation warnings
     - Fully migrated to new service classes
   - This approach maintains backward compatibility while moving toward a cleaner architecture

4. **Service Class Integration**:
   - `CurveService` handles point manipulation, selection, and data management
   - `VisualizationService` manages visual elements like grid, point radius, and timeline synchronization
   - `CenteringZoomService` manages view centering and zoom operations
   - Each service class typically receives relevant UI components as parameters to access necessary properties
   - Services are designed to be stateless, with state maintained in the UI components

## Signal-Slot Architecture

The application implements a centralized signal-slot architecture for better code organization and maintainability:

1. **Centralized Signal Connection System**:
   - All signal connections are managed through the `UIComponents.connect_all_signals` method
   - This provides a single location for managing and organizing all UI signal connections
   - Groups signal connections by functional area (curve view, editing controls, visualization, etc.)
   - Implements defensive programming with attribute checks to prevent errors from missing UI components
   - Follows consistent connection patterns throughout the application

2. **Direct Service Class Connections**:
   - UI signals are connected directly to methods in service classes
   - Example: `button.clicked.connect(lambda checked: VisualizationService.toggle_grid(self, checked))`
   - This approach eliminates redundant wrapper methods in the MainWindow class
   - Services provide stateless functions that operate on the UI components

3. **Lambda Functions**:
   - Used for passing additional parameters to handler methods
   - Allows direct connection to static service methods while providing context
   - Example: `spinbox.valueChanged.connect(lambda value: CurveService.update_point_from_edit(self))`

4. **Initialization Sequence**:
   - Signal connections are performed after all UI components are fully initialized
   - This prevents errors from connecting signals to components that don't exist yet
   - Clear separation between UI component creation and signal connection

5. **Component Encapsulation**:
   - UI components like the EnhancedCurveView are properly encapsulated with setup methods
   - Each component follows the same pattern for initialization and signal connection
   - `setup_enhanced_curve_view` and `setup_enhanced_controls` methods handle specialized UI components

## UI Components Architecture

The `UIComponents` class serves as the central manager for all UI-related functionality:

1. **Key Responsibilities**:
   - Creating and arranging UI widgets and layouts
   - Centralizing signal connections through `connect_all_signals`
   - Providing utility methods for UI operations
   - Ensuring proper error handling for UI components

2. **Architecture Benefits**:
   - Clear separation between UI component management and application logic
   - Consistent approach to UI creation and signal connection
   - Single point of maintenance for all UI-related code
   - Improved code organization and modularity
   - Better error handling with defensive programming

3. **Key UI Component Methods**:
   - `create_toolbar`: Creates the main application toolbar
   - `create_view_and_timeline`: Sets up the curve view and timeline components
   - `create_control_panel`: Creates the point editing controls
   - `setup_enhanced_curve_view`: Initializes the enhanced curve view with extended visualization features
   - `setup_enhanced_controls`: Creates controls for enhanced visualization options
   - `connect_all_signals`: Connects all UI signals to their respective handlers

4. **Signal Connection Organization**:
   - Curve view signals for point selection and manipulation
   - Point editing signals for coordinate input and manipulation
   - Visualization signals for display options
   - Timeline signals for frame navigation
   - File operation signals for loading and saving data
   - Enhanced view signals for grid, vectors, and other visualization options

## File Formats

The application works with 3DE4 compatible track files, which are text-based files containing:
- Point name and color information
- Frame numbers
- X and Y coordinates for each frame

## Configuration System

The application uses a JSON-based configuration system to store user preferences and session information:

1. **Configuration File**: `app_config.json` in the application directory
2. **Stored Information**:
   - `last_file_path`: Path to the last loaded track data file
   - `last_folder_path`: Path to the last accessed directory
   - `last_image_path`: Path to the last loaded image sequence
3. **Usage**:
   - Configuration is automatically loaded at application startup
   - File and folder paths are updated when the user loads or saves files
   - Previously used files and image sequences are automatically loaded when available
   - Provides a smoother workflow by remembering previous session locations and settings

## Image Sequence Handling

The application supports loading and displaying image sequences as backgrounds for tracking data:

1. **Loading Methods**:
   - Select the first image in a sequence via file dialog
   - Automatic detection of other images in the sequence based on filename pattern
   - Automatic loading of previously used image sequences at startup
2. **Supported Naming Conventions**:
   - `name.1234.ext` format (e.g., shot.0001.jpg)
   - `name_1234.ext` format (e.g., shot_0001.jpg)
3. **Navigation**:
   - Left/Right arrow keys to move between images
   - Timeline synchronization with tracking data frames
   - UI buttons for sequential navigation
   - Up/Down arrow keys to adjust frame nudging increments
4. **Display Options**:
   - Toggle background visibility
   - Adjust background opacity via slider control
   - Automatic scaling to match tracking data coordinates
   - Fullscreen mode (F11 key) for maximized workspace
   - Proper aspect ratio preservation
   - Visual indicator for current nudge increment value
5. **Coordinate Alignment**:
   - Precise alignment between image space and tracking data space
   - Automatic centering of images and views using unified logic in `ZoomOperations`

## Coordinate Transformation System

The application implements a sophisticated coordinate transformation system to ensure proper alignment between tracking data and visual elements:

1. **Coordinate Spaces**:
   - **Image Space**: Coordinates in the original image (pixels)
   - **Widget Space**: Coordinates in the display widget (pixels)
   - **Tracking Space**: Coordinates in the tracking data (typically normalized)

2. **Transformation Functions**:
   - `map_to_widget`: Converts tracking coordinates to widget space
   - `map_from_widget`: Converts widget coordinates to tracking space
   - Functions account for zoom level, panning offset, and coordinate system differences

3. **Scale Handling**:
   - Automatic calculation of appropriate scaling factors
   - Maintenance of proper aspect ratios
   - Dynamic adjustment based on widget size and zoom level

## Recent Framework Changes

The application has recently undergone a major framework update, transitioning from PyQt5 to PySide6:

1. **Migration Benefits**:
   - Better compatibility with Python 3.12
   - Access to newer Qt features and improvements
   - More consistent license approach
   - Performance improvements

2. **Key Changes**:
   - Updated signal/slot mechanism (Signal/Slot instead of pyqtSignal/pyqtSlot)
   - Revised event handling (QEvent constant access through explicit namespaces)
   - Updated method and property access patterns (e.g., QWheelEvent.position() instead of x()/y())
   - Explicit imports from specific Qt modules (QtCore, QtGui, QtWidgets)
   - Proper hierarchical UI component structure with clear parent-child relationships

## Keyboard and Mouse Interaction

The application provides comprehensive keyboard and mouse interaction:

1. **Keyboard Navigation**:
   - Left/Right arrows: Navigate between images
   - Space: Play/pause animation
   - Comma/Period: Previous/next frame
   - 'R': Reset view

2. **Mouse Interaction**:
   - Left click: Select points
   - Left drag: Move selected points
   - Middle drag: Pan view
   - Wheel: Zoom view centered on cursor
   - Shift+click: Add to selection
   - Ctrl+click: Remove from selection

3. **Shortcut System**:
   - Global keyboard shortcuts managed through the ShortcutManager
   - All shortcuts (global, view-specific, dialog-specific) are registered and connected via ShortcutManager
   - Direct key handling via `keyPressEvent` or `eventFilter` has been removed

## Next Steps After Refactoring

The service-based architecture refactoring is now complete. The following steps are recommended to further improve the application:

1. **Testing Improvements**:
   - Expand test coverage for all services
   - Add comprehensive unit tests for each service class
   - Implement integration tests to ensure services work together correctly
   - Create automated test suite for regression testing

2. **Code Cleanup**:
   - Remove deprecated files when no longer needed
   - Standardize all import patterns across the codebase
   - Remove any lingering references to the old utility classes
   - Verify no circular dependencies exist between services

3. **Documentation Enhancements**:
   - Create detailed API documentation for each service
   - Update all docstrings to reflect service methods
   - Add examples of common service usage patterns
   - Provide migration guides for developers familiar with the old architecture

4. **Architecture Validation**:
   - Run validation tools to verify architecture compliance
   - Check for any remaining import inconsistencies
   - Ensure proper type hints and static analysis support
   - Validate performance impact of the new architecture

5. **Feature Enhancements**:
   - Implement new features leveraging the improved architecture
   - Refine existing functionality using service-based approach
   - Consider adding new services for specialized functionality
   - Improve error handling and user feedback

This documentation will be updated as the application evolves and new features are added.

# 3DE4 Curve Editor Documentation

## Overview

The 3DE4 Curve Editor is a specialized application designed for editing 2D tracking curves used in visual effects and camera tracking workflows. It allows users to load, visualize, edit, and save 2D tracking data, with support for image sequence backgrounds to provide visual context for the tracking points. The application includes a configuration system that remembers the last used file and folder paths for a smoother workflow. The editor features a robust coordinate transformation system that properly aligns tracking points with background images, ensuring accurate visual feedback during the editing process.

## Application Structure

The application follows a modular architecture with clear separation of concerns:

### Main Components

1. **Main Entry Point** (`main.py`)
   - Initializes the Qt application and main window
   - Entry point for the application

2. **Main Window** (`main_window.py`)
   - Central component that integrates all UI elements and functionality
   - Manages application state and data flow
   - Delegates specific operations to specialized modules

3. **Curve View** (`curve_view.py`)
   - Custom widget for visualizing and interacting with tracking curves
   - Handles rendering of points, curves, and background images
   - Manages user interactions like point selection, dragging, and zooming
   - Implements precise coordinate transformation between image space and widget space
   - Supports image sequence backgrounds
   - Provides visual feedback with crosshairs and information overlays

### Operation Modules

The application functionality is organized into specialized modules:

1. **UI Components** (`ui_components.py`)
   - Creates and organizes UI elements
   - Builds toolbar, timeline controls, and editing panels

2. **File Operations** (`file_operations.py`)
   - Handles loading and saving track data
   - Manages file dialogs and data parsing

3. **Image Operations** (`image_operations.py`)
   - Manages loading and display of image sequences
   - Controls image navigation and background visibility

4. **Timeline Operations** (`timeline_operations.py`)
   - Manages the timeline slider and frame navigation
   - Synchronizes timeline with point selection and image display

5. **History Operations** (`history_operations.py`)
   - Implements undo/redo functionality
   - Manages state history for tracking changes

6. **Curve Operations** (`curve_operations.py`)
   - Implements curve editing algorithms
   - Provides smoothing, filtering, gap filling, and extrapolation

7. **Utilities** (`utils.py`)
   - Common utility functions
   - Data loading/saving helpers

8. **Configuration** (`config.py`)
   - Manages application settings and preferences
   - Stores and retrieves the last opened file and folder paths
   - Uses JSON format for persistent storage in app_config.json

9. **Dialogs** (`dialogs.py`)
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

- **Information Overlay**: Real-time display of zoom level, selected points, and image information

### Editing Tools

- **Point Editing**: Direct manipulation of tracking points
- **Smoothing**: Algorithms for smoothing tracking curves
- **Gap Filling**: Tools to interpolate missing tracking data
- **Filtering**: Noise reduction and filtering options
- **Extrapolation**: Extend tracking data beyond available frames

### Timeline Navigation

- **Frame Navigation**: Timeline slider for navigating through frames
- **Frame Synchronization**: Synchronization between timeline, points, and background images

### History Management

- **Undo/Redo**: Support for undoing and redoing editing operations
- **History Stack**: Maintains a history of changes for reverting

## Data Flow

1. **Loading Data**:
   - User loads track data via File Operations
   - Data is parsed and stored in MainWindow
   - CurveView is updated to display the loaded points
   - Timeline is configured based on frame range
   - File path is saved to configuration for future sessions

2. **Editing Points**:
   - User interacts with points in CurveView
   - CurveView emits signals when points are moved or selected
   - MainWindow updates internal data and UI elements
   - Changes are added to history stack

3. **Applying Operations**:
   - User initiates operations like smoothing or filtering
   - Dialog windows collect parameters
   - Curve Operations apply algorithms to the data
   - Results are displayed in CurveView
   - Changes are added to history stack

4. **Saving Data**:
   - User initiates save operation
   - File Operations handle file dialog and data formatting
   - Modified track data is written to file

## UI Structure

1. **Toolbar**: Contains buttons for all major operations
2. **Curve View**: Main visualization area for tracks and images
3. **Timeline**: Controls for navigating through frames
4. **Control Panel**: Tools for precise point editing and information

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
4. **Display Options**:
   - Toggle background visibility
   - Adjust background opacity via slider control
   - Automatic scaling to match tracking data coordinates
   - Proper aspect ratio preservation
5. **Coordinate Alignment**:
   - Precise alignment between image space and tracking data space
   - Automatic centering of images relative to tracking area
   - Visual indicators (crosshairs) for alignment verification

## Coordinate Transformation System

The application implements a sophisticated coordinate transformation system to ensure proper alignment between tracking data and visual elements:

1. **Coordinate Spaces**:
   - **Image Space**: The original coordinate system of the tracking data
   - **Widget Space**: The pixel coordinates of the UI widget

2. **Transformation Process**:
   - Scaling based on widget size and zoom factor
   - X-axis flipping to match 3DE4 coordinate system
   - Y-axis adjustment to match image coordinates
   - Offset application for panning and centering

3. **Implementation**:
   - Bidirectional transformation between spaces
   - Consistent application across all visual elements
   - Proper handling of aspect ratios and scaling

4. **Visual Feedback**:
   - Crosshair indicators at center points
   - Information overlay showing coordinates
   - Real-time updates during interaction

## Dependencies

- **PyQt5**: UI framework
- **Python Standard Library**: File operations, math functions

---

This documentation will be updated as the application evolves and new features are added.
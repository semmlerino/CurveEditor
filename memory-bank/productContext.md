# Product Context

This file provides a high-level overview of the project and the expected product that will be created. Initially it is based upon projectBrief.md (if provided) and all other available project-related information in the working directory. This file is intended to be updated as the project evolves, and should be used to inform all other modes of the project's goals and context.
2025-04-11 14:36:03 - Log of updates made will be appended as footnotes to the end of this file.

*

## Project Goal

* The 3DE4 Curve Editor is designed to provide a specialized environment for editing 2D tracking curves used in visual effects and camera tracking workflows. It enables users to load, visualize, edit, and save 2D tracking data, supporting image sequence backgrounds for visual context and accurate editing.

## Key Features

* Load, visualize, and edit 2D tracking data
* Support for image sequence backgrounds and precise coordinate transformation
* Batch editing (scale, offset, rotate multiple points)
* Smoothing, filtering, gap filling, and extrapolation tools
* Undo/redo and history management
* Track quality analysis and visualization
* Session persistence and configuration system
* Modular, utility-class-based architecture for maintainability

## Overall Architecture

* Modular architecture with clear separation of concerns
* Main components: Main Entry Point, Main Window, Curve View, Enhanced Curve View
* Utility classes for curve operations, visualization, UI components, file/image/history/settings/dialog operations, and track quality
* Centralized signal-slot system for UI event handling
* JSON-based configuration and session persistence
* Support for 3DE4-compatible text-based track files
2025-04-11 14:44:49 - UMB: Memory Bank synchronized with documentation and codebase context.
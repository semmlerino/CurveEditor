# CurveEditor Product Overview

CurveEditor is a professional Python/PySide6 application for editing animation curves and tracking data with high-performance rendering and intuitive controls.

## Core Purpose
- Edit keyframe animation curves with interpolation
- Handle multi-point selection and manipulation
- Provide real-time visualization with optimized rendering
- Support import/export of curve data (CSV, JSON, custom formats)
- Enable rotoscoping and tracking workflows with background image support

## Key Features
- **Animation Curve Editing**: Create and edit keyframe animation curves
- **Multi-Point Selection**: Select and manipulate multiple points simultaneously  
- **Real-time Visualization**: High-performance rendering with optimized QPainter
- **Undo/Redo System**: Full history tracking with unlimited undo/redo
- **Background Images**: Load reference images for rotoscoping and tracking
- **Advanced Operations**: Smoothing algorithms, batch editing, velocity vectors
- **Timeline Controls**: Frame navigation with playback simulation

## Performance Targets
- Handle 10,000+ points smoothly
- 60 FPS rendering on modern hardware
- Sub-millisecond coordinate transformations
- Memory efficient with large datasets

## Architecture Philosophy
- 4-service architecture for clean separation of concerns
- Service singletons with dependency injection
- Protocol-based interfaces for type safety
- Component-based UI architecture
- Thread-safe operations with proper locking
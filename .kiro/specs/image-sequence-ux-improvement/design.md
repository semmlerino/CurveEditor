# Design Document

## Overview

This design addresses the usability issues in CurveEditor's image sequence loading functionality by implementing a streamlined, user-friendly interface that maintains the existing powerful features while significantly improving the user experience. The solution focuses on reducing cognitive load, providing better visual feedback, and implementing intuitive workflows.

## Architecture

### Current Architecture Analysis

The existing image sequence browser (`ui/image_sequence_browser.py`) is a comprehensive dialog with:
- Three-panel layout (directory tree, sequence list, preview)
- Full navigation controls (back/forward, breadcrumbs, favorites)
- Thumbnail generation and caching
- Metadata extraction and display
- Keyboard shortcuts and accessibility features

**Key Issues Identified:**
1. **Overwhelming Interface**: Too many UI elements visible simultaneously
2. **Poor Default Behavior**: Doesn't start in the most logical location
3. **Slow Feedback**: Thumbnail generation blocks user interaction
4. **Complex Navigation**: Multiple ways to do the same thing creates confusion
5. **Inconsistent State**: Settings and preferences not properly persisted

### Proposed Architecture Improvements

#### 1. Progressive Disclosure UI Pattern
Instead of showing all features at once, implement a progressive disclosure pattern:
- **Simple Mode**: Streamlined interface for common use cases
- **Advanced Mode**: Full feature set for power users
- **Smart Defaults**: Automatically choose the best mode based on context

#### 2. Enhanced State Management
Extend the existing state management to include:
- User interface preferences (simple vs advanced mode)
- Recent directory history with project context
- Thumbnail cache persistence
- Sort and filter preferences

#### 3. Improved Performance Architecture
- **Asynchronous Operations**: All file system operations run in background threads
- **Progressive Loading**: Show results as they become available
- **Smart Caching**: Persist thumbnails and metadata across sessions
- **Cancellable Operations**: Allow users to cancel long-running operations

## Components and Interfaces

### 1. Enhanced ImageSequenceBrowserDialog

#### New Interface Modes

**Simple Mode (Default)**:
```
┌─────────────────────────────────────────────────────────────┐
│ Load Image Sequence                                    [×]  │
├─────────────────────────────────────────────────────────────┤
│ Recent Locations: [Dropdown ▼] [Browse...] [Advanced >>]   │
├─────────────────────────────────────────────────────────────┤
│ ┌─ Image Sequences ─────────────────────────────────────┐   │
│ │ render_v001_####.exr [1-100] (100 frames) 2K        │   │
│ │ comp_final_####.jpg [1-50] (50 frames) HD           │   │
│ │ bg_plate_####.dpx [1-75] (75 frames) 4K             │   │
│ └─────────────────────────────────────────────────────────┘   │
│ ┌─ Preview ─────────────────────────────────────────────┐   │
│ │ [Thumbnail] [Thumbnail] [Thumbnail] [Thumbnail]      │   │
│ │ Frame 1     Frame 25    Frame 50    Frame 75        │   │
│ └─────────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│                                    [Cancel] [Load Sequence] │
└─────────────────────────────────────────────────────────────┘
```

**Advanced Mode**:
- Expands to show the current three-panel layout
- Maintains all existing functionality
- Adds new features like project-aware recent directories

#### New Components

**SmartLocationSelector**:
- Combines recent directories, favorites, and quick access
- Project-aware directory suggestions
- Intelligent path completion

**SequencePreviewWidget**:
- Optimized thumbnail loading with progress indication
- Lazy loading with viewport culling
- Metadata overlay on hover

**ProgressiveDisclosureController**:
- Manages transition between simple and advanced modes
- Preserves user preferences
- Handles layout animations

### 2. Enhanced State Management

#### ProjectAwareStateManager
```python
class ProjectAwareStateManager:
    def get_recent_directories(self, project_context: str | None = None) -> list[str]
    def add_recent_directory(self, path: str, project_context: str | None = None) -> None
    def get_user_preferences(self) -> UserPreferences
    def save_user_preferences(self, prefs: UserPreferences) -> None
```

#### UserPreferences
```python
@dataclass
class UserPreferences:
    interface_mode: Literal["simple", "advanced"] = "simple"
    default_sort_order: str = "name"
    show_thumbnails: bool = True
    thumbnail_size: int = 150
    auto_detect_project_context: bool = True
    remember_window_size: bool = True
```

### 3. Performance Optimizations

#### AsyncThumbnailGenerator
- Background thumbnail generation with priority queue
- Cancellable operations
- Progress reporting
- Disk cache with LRU eviction

#### SmartDirectoryScanner
- Incremental scanning with early results
- File system change monitoring
- Optimized pattern matching for sequence detection

## Data Models

### Enhanced ImageSequence Model
```python
@dataclass
class ImageSequence:
    # Existing fields...
    
    # New fields for improved UX
    project_context: str | None = None
    last_accessed: datetime | None = None
    thumbnail_paths: list[str] = field(default_factory=list)
    metadata_cached: bool = False
    user_rating: int = 0  # For favorites/bookmarking
    
    @property
    def display_priority(self) -> int:
        """Calculate display priority based on recency, rating, etc."""
        
    @property
    def smart_display_name(self) -> str:
        """Generate context-aware display name."""
```

### DirectoryContext Model
```python
@dataclass
class DirectoryContext:
    path: str
    project_name: str | None = None
    sequence_count: int = 0
    last_visited: datetime | None = None
    is_favorite: bool = False
    access_frequency: int = 0
```

## Error Handling

### Graceful Degradation Strategy

1. **Network/Permission Issues**:
   - Show user-friendly error messages
   - Provide alternative access methods
   - Cache last successful state

2. **Performance Issues**:
   - Implement timeout handling
   - Show progress indicators
   - Allow operation cancellation

3. **File System Issues**:
   - Handle missing directories gracefully
   - Provide path correction suggestions
   - Maintain working fallback locations

### Error Recovery Patterns

```python
class ErrorRecoveryManager:
    def handle_directory_access_error(self, path: str, error: Exception) -> RecoveryAction
    def suggest_alternative_paths(self, failed_path: str) -> list[str]
    def provide_user_guidance(self, error_type: ErrorType) -> str
```

## Testing Strategy

### User Experience Testing
1. **Task-Based Testing**: Time users completing common workflows
2. **A/B Testing**: Compare simple vs advanced mode adoption
3. **Accessibility Testing**: Verify keyboard navigation and screen reader support
4. **Performance Testing**: Measure load times with various directory sizes

### Automated Testing
1. **Unit Tests**: Individual component functionality
2. **Integration Tests**: Cross-component interactions
3. **Performance Tests**: Thumbnail generation and caching
4. **Regression Tests**: Ensure existing functionality remains intact

### Test Scenarios
- Loading sequences from network drives
- Handling directories with thousands of files
- Managing favorites and recent directories
- Switching between interface modes
- Cancelling long-running operations

## Implementation Phases

### Phase 1: Core UX Improvements
- Implement simple mode interface
- Add smart location selector
- Enhance state management
- Improve default behaviors

### Phase 2: Performance Optimizations
- Implement async thumbnail generation
- Add progressive loading
- Optimize directory scanning
- Implement smart caching

### Phase 3: Advanced Features
- Add project context awareness
- Implement user preferences system
- Add advanced filtering and sorting
- Enhance accessibility features

### Phase 4: Polish and Optimization
- Performance tuning
- UI animations and transitions
- Advanced error handling
- Comprehensive testing

## Migration Strategy

### Backward Compatibility
- Maintain existing API for `ImageSequenceBrowserDialog`
- Preserve all current functionality in advanced mode
- Ensure existing shortcuts and workflows continue to work

### User Transition
- Default to simple mode for new users
- Provide easy discovery of advanced features
- Maintain user's mode preference across sessions
- Offer guided tour for new features

## Success Metrics

### Quantitative Metrics
- Reduce average time to load sequence by 50%
- Decrease user error rate by 40%
- Improve task completion rate to >95%
- Reduce support requests related to image loading by 60%

### Qualitative Metrics
- User satisfaction scores
- Ease of use ratings
- Feature discoverability
- Overall workflow efficiency

This design maintains the powerful functionality of the existing image sequence browser while dramatically improving the user experience through progressive disclosure, better defaults, and performance optimizations.
# CurveEditor Performance Guide

## Performance Targets

CurveEditor is designed for high-performance curve editing with these targets:

- **Handle 10,000+ points smoothly**
- **60 FPS rendering on modern hardware**
- **Sub-millisecond coordinate transformations**
- **Memory efficient with large datasets**

## Rendering Optimizations

### Viewport Culling

Only render points visible in the current view:

```python
class CurveRenderer:
    def render_points(self, points: list[CurvePoint], viewport: QRectF) -> None:
        """Render only visible points for performance."""
        transform_service = get_transform_service()
        
        # Cull points outside viewport
        visible_points = []
        for point in points:
            screen_pos = transform_service.data_to_screen(point.position)
            if viewport.contains(screen_pos):
                visible_points.append((point, screen_pos))
        
        # Render only visible points
        self._render_point_batch(visible_points)
```

### Batch Rendering

Render points in batches to minimize QPainter state changes:

```python
def _render_point_batch(self, points_with_positions: list[tuple[CurvePoint, QPointF]]) -> None:
    """Batch render points by status for efficiency."""
    # Group by rendering properties
    selected_points = []
    normal_points = []
    
    for point, screen_pos in points_with_positions:
        if point.status == PointStatus.SELECTED:
            selected_points.append(screen_pos)
        else:
            normal_points.append(screen_pos)
    
    # Batch render each group
    if normal_points:
        painter.setPen(self.normal_pen)
        painter.setBrush(self.normal_brush)
        for pos in normal_points:
            painter.drawEllipse(pos, self.point_radius, self.point_radius)
    
    if selected_points:
        painter.setPen(self.selected_pen)
        painter.setBrush(self.selected_brush)
        for pos in selected_points:
            painter.drawEllipse(pos, self.point_radius, self.point_radius)
```

### Dirty Flag System

Only redraw when necessary using dirty flags:

```python
class CurveViewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._render_dirty = True
        self._cached_image: QImage | None = None
    
    def invalidate_render(self) -> None:
        """Mark rendering cache as dirty."""
        self._render_dirty = True
        self.update()  # Schedule repaint
    
    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint with caching for performance."""
        if self._render_dirty or self._cached_image is None:
            self._rebuild_render_cache()
            self._render_dirty = False
        
        # Fast blit from cache
        painter = QPainter(self)
        painter.drawImage(0, 0, self._cached_image)
```

### Transform Caching

Cache expensive coordinate transformations:

```python
class TransformService:
    def __init__(self):
        self._transform_matrix: QTransform | None = None
        self._matrix_dirty = True
        self._screen_points_cache: dict[str, list[QPointF]] = {}
    
    def data_to_screen(self, data_point: tuple[float, float]) -> QPointF:
        """Fast coordinate transformation with caching."""
        if self._matrix_dirty or self._transform_matrix is None:
            self._rebuild_transform_matrix()
        
        return self._transform_matrix.map(QPointF(*data_point))
    
    def invalidate_transform_cache(self) -> None:
        """Invalidate cached transforms when view changes."""
        self._matrix_dirty = True
        self._screen_points_cache.clear()
```

## Memory Management

### Efficient Data Structures

Use appropriate data structures for large datasets:

```python
class SpatialIndex:
    """Efficient spatial indexing for large point sets."""
    
    def __init__(self, grid_size: float = 50.0):
        self._grid_size = grid_size
        self._grid: dict[tuple[int, int], list[int]] = {}
        self._points: list[CurvePoint] = []
    
    def add_point(self, point_index: int, position: tuple[float, float]) -> None:
        """Add point to spatial grid."""
        grid_x = int(position[0] // self._grid_size)
        grid_y = int(position[1] // self._grid_size)
        grid_key = (grid_x, grid_y)
        
        if grid_key not in self._grid:
            self._grid[grid_key] = []
        self._grid[grid_key].append(point_index)
    
    def find_points_near(self, position: tuple[float, float], radius: float) -> list[int]:
        """Efficiently find points within radius."""
        # Check only relevant grid cells
        grid_radius = int(radius // self._grid_size) + 1
        center_x = int(position[0] // self._grid_size)
        center_y = int(position[1] // self._grid_size)
        
        candidates = []
        for dx in range(-grid_radius, grid_radius + 1):
            for dy in range(-grid_radius, grid_radius + 1):
                grid_key = (center_x + dx, center_y + dy)
                if grid_key in self._grid:
                    candidates.extend(self._grid[grid_key])
        
        # Filter by actual distance
        return [idx for idx in candidates 
                if self._distance(position, self._points[idx].position) <= radius]
```

### Memory Pool Pattern

Reuse objects to reduce garbage collection:

```python
class PointPool:
    """Object pool for CurvePoint instances."""
    
    def __init__(self, initial_size: int = 1000):
        self._available: list[CurvePoint] = []
        self._in_use: set[CurvePoint] = set()
        
        # Pre-allocate points
        for _ in range(initial_size):
            self._available.append(CurvePoint(0, 0.0, 0.0))
    
    def acquire(self, frame: int, x: float, y: float) -> CurvePoint:
        """Get a point from the pool."""
        if self._available:
            point = self._available.pop()
            point.frame = frame
            point.x = x
            point.y = y
        else:
            point = CurvePoint(frame, x, y)
        
        self._in_use.add(point)
        return point
    
    def release(self, point: CurvePoint) -> None:
        """Return a point to the pool."""
        if point in self._in_use:
            self._in_use.remove(point)
            self._available.append(point)
```

### Lazy Loading

Load data only when needed:

```python
class CurveDataManager:
    def __init__(self):
        self._curve_files: dict[str, Path] = {}
        self._loaded_curves: dict[str, list[CurvePoint]] = {}
    
    def register_curve_file(self, curve_name: str, file_path: Path) -> None:
        """Register curve file without loading."""
        self._curve_files[curve_name] = file_path
    
    def get_curve_data(self, curve_name: str) -> list[CurvePoint] | None:
        """Load curve data on first access."""
        if curve_name in self._loaded_curves:
            return self._loaded_curves[curve_name]
        
        if curve_name in self._curve_files:
            # Lazy load
            file_path = self._curve_files[curve_name]
            points = self._load_curve_file(file_path)
            self._loaded_curves[curve_name] = points
            return points
        
        return None
```

## Algorithm Optimizations

### Fast Point Selection

Use spatial indexing for efficient point picking:

```python
class InteractionService:
    def __init__(self):
        self._spatial_index = SpatialIndex()
        self._selection_radius = 10.0  # pixels
    
    def find_point_at_position(self, screen_pos: QPointF) -> int | None:
        """Fast point lookup using spatial index."""
        transform_service = get_transform_service()
        
        # Convert to data coordinates
        data_pos = transform_service.screen_to_data(screen_pos)
        
        # Convert selection radius to data space
        data_radius = self._selection_radius / transform_service.get_zoom_factor()
        
        # Use spatial index for fast lookup
        candidates = self._spatial_index.find_points_near(data_pos, data_radius)
        
        if not candidates:
            return None
        
        # Find closest candidate
        min_distance = float('inf')
        closest_point = None
        
        for point_idx in candidates:
            point_pos = self._get_point_position(point_idx)
            distance = self._distance(data_pos, point_pos)
            if distance < min_distance:
                min_distance = distance
                closest_point = point_idx
        
        return closest_point
```

### Efficient Curve Smoothing

Use optimized algorithms for curve operations:

```python
def smooth_curve_points(points: list[CurvePoint], window_size: int = 5) -> list[CurvePoint]:
    """Fast curve smoothing using moving average."""
    if len(points) < window_size:
        return points.copy()
    
    smoothed = []
    half_window = window_size // 2
    
    # Pre-calculate weights for efficiency
    weights = [1.0 / window_size] * window_size
    
    for i in range(len(points)):
        # Determine window bounds
        start = max(0, i - half_window)
        end = min(len(points), i + half_window + 1)
        
        # Calculate weighted average
        sum_x = sum_y = 0.0
        count = 0
        
        for j in range(start, end):
            sum_x += points[j].x
            sum_y += points[j].y
            count += 1
        
        # Create smoothed point
        smoothed_point = CurvePoint(
            points[i].frame,
            sum_x / count,
            sum_y / count
        )
        smoothed.append(smoothed_point)
    
    return smoothed
```

## Threading and Concurrency

### Background Processing

Use worker threads for expensive operations:

```python
class CurveAnalysisWorker(QThread):
    """Background thread for curve analysis."""
    
    analysis_complete = Signal(dict)
    
    def __init__(self, curve_data: list[CurvePoint]):
        super().__init__()
        self._curve_data = curve_data.copy()  # Thread-safe copy
    
    def run(self) -> None:
        """Perform analysis in background thread."""
        try:
            # Expensive analysis operations
            stats = self._calculate_statistics()
            velocity_data = self._calculate_velocities()
            
            results = {
                'statistics': stats,
                'velocities': velocity_data
            }
            
            self.analysis_complete.emit(results)
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")

# Usage
def start_background_analysis(self, curve_data: list[CurvePoint]) -> None:
    """Start analysis in background thread."""
    self._analysis_worker = CurveAnalysisWorker(curve_data)
    self._analysis_worker.analysis_complete.connect(self._on_analysis_complete)
    self._analysis_worker.start()
```

### Thread-Safe Caching

Use locks for thread-safe cache operations:

```python
class ThreadSafeCache:
    """Thread-safe cache for expensive computations."""
    
    def __init__(self, max_size: int = 100):
        self._cache: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._max_size = max_size
        self._access_order: list[str] = []
    
    def get(self, key: str, compute_func: Callable[[], Any]) -> Any:
        """Get cached value or compute if missing."""
        with self._lock:
            if key in self._cache:
                # Move to end (most recently used)
                self._access_order.remove(key)
                self._access_order.append(key)
                return self._cache[key]
            
            # Compute new value
            value = compute_func()
            
            # Add to cache with LRU eviction
            if len(self._cache) >= self._max_size:
                oldest_key = self._access_order.pop(0)
                del self._cache[oldest_key]
            
            self._cache[key] = value
            self._access_order.append(key)
            return value
```

## Profiling and Benchmarking

### Performance Measurement

Use decorators to measure performance:

```python
import time
import functools
from typing import Callable, Any

def profile_performance(func: Callable) -> Callable:
    """Decorator to measure function execution time."""
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            end_time = time.perf_counter()
            duration = (end_time - start_time) * 1000  # Convert to milliseconds
            logger.debug(f"{func.__name__} took {duration:.2f}ms")
    return wrapper

# Usage
class CurveRenderer:
    @profile_performance
    def render_curve(self, points: list[CurvePoint]) -> QImage:
        """Render curve with performance measurement."""
        # Rendering implementation
        pass
```

### Memory Profiling

Monitor memory usage for large datasets:

```python
import psutil
import os

class MemoryMonitor:
    """Monitor memory usage for performance analysis."""
    
    def __init__(self):
        self._process = psutil.Process(os.getpid())
        self._baseline_memory = self._get_memory_usage()
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB."""
        return self._process.memory_info().rss / 1024 / 1024
    
    def log_memory_usage(self, operation: str) -> None:
        """Log current memory usage."""
        current_memory = self._get_memory_usage()
        delta = current_memory - self._baseline_memory
        logger.info(f"{operation}: {current_memory:.1f}MB (+{delta:.1f}MB)")
    
    def reset_baseline(self) -> None:
        """Reset memory baseline."""
        self._baseline_memory = self._get_memory_usage()

# Usage
memory_monitor = MemoryMonitor()
memory_monitor.log_memory_usage("Before loading curve data")
# ... load large dataset ...
memory_monitor.log_memory_usage("After loading curve data")
```

## Performance Testing

### Benchmark Tests

Create performance tests for critical operations:

```python
import pytest
import time

@pytest.mark.performance
def test_point_selection_performance():
    """Test point selection performance with large dataset."""
    # Create large dataset
    points = [CurvePoint(i, float(i), float(i)) for i in range(10000)]
    
    interaction_service = get_interaction_service()
    interaction_service.add_curve_data("test", points)
    
    # Measure selection performance
    start_time = time.perf_counter()
    
    for _ in range(100):  # 100 selections
        point_idx = interaction_service.find_point_at_position(QPointF(500, 500))
    
    end_time = time.perf_counter()
    avg_time = (end_time - start_time) / 100 * 1000  # ms per selection
    
    # Assert performance target (sub-millisecond)
    assert avg_time < 1.0, f"Point selection too slow: {avg_time:.2f}ms"

@pytest.mark.performance
def test_rendering_performance():
    """Test rendering performance with target framerate."""
    widget = CurveViewWidget()
    points = [CurvePoint(i, float(i), float(i)) for i in range(10000)]
    widget.set_curve_data(points)
    
    # Measure rendering time
    start_time = time.perf_counter()
    
    for _ in range(60):  # Simulate 60 frames
        widget.render_to_image()
    
    end_time = time.perf_counter()
    total_time = end_time - start_time
    fps = 60 / total_time
    
    # Assert 60 FPS target
    assert fps >= 60.0, f"Rendering too slow: {fps:.1f} FPS"
```

## Performance Best Practices

### Do's

- ✅ Use viewport culling for large datasets
- ✅ Batch similar rendering operations
- ✅ Cache expensive computations
- ✅ Use spatial indexing for point queries
- ✅ Profile performance-critical code
- ✅ Use appropriate data structures (spatial grids, object pools)
- ✅ Minimize QPainter state changes
- ✅ Use dirty flags to avoid unnecessary redraws

### Don'ts

- ❌ Don't render all points when only some are visible
- ❌ Don't recalculate transforms on every frame
- ❌ Don't use linear search for point selection
- ❌ Don't create new objects in tight loops
- ❌ Don't ignore memory usage with large datasets
- ❌ Don't block the UI thread with expensive operations
- ❌ Don't assume performance without measurement

Following these performance guidelines will help maintain CurveEditor's high-performance targets even with large datasets and complex operations.
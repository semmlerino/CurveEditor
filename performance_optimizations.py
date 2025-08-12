#!/usr/bin/env python
"""
Performance Optimization Implementations for CurveViewWidget.

This module provides optimized versions of key performance-critical methods
identified in the performance analysis, demonstrating how to implement
viewport culling, spatial indexing, and cache optimizations.
"""

import math
import time
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen


@dataclass
class ViewportBounds:
    """Represents the visible viewport bounds."""
    left: float
    right: float
    top: float
    bottom: float
    
    def contains_point(self, x: float, y: float) -> bool:
        """Check if a point is within the viewport bounds."""
        return (self.left <= x <= self.right and 
                self.top <= y <= self.bottom)
    
    def intersects_circle(self, center_x: float, center_y: float, radius: float) -> bool:
        """Check if a circle intersects with the viewport."""
        # Expand bounds by radius for circle intersection
        return (self.left - radius <= center_x <= self.right + radius and
                self.top - radius <= center_y <= self.bottom + radius)


class QuadTreeNode:
    """
    QuadTree node for spatial indexing of curve points.
    
    Provides O(log n) point selection instead of O(n) linear search.
    """
    
    def __init__(self, bounds: QRectF, max_points: int = 10, max_depth: int = 8):
        self.bounds = bounds
        self.max_points = max_points
        self.max_depth = max_depth
        self.points: List[Tuple[int, float, float]] = []  # (index, x, y)
        self.children: List[Optional['QuadTreeNode']] = [None, None, None, None]
        self.is_divided = False
    
    def insert(self, index: int, x: float, y: float) -> bool:
        """Insert a point into the quadtree."""
        # Check if point is in bounds
        if not self.bounds.contains(QPointF(x, y)):
            return False
        
        # If we have space and no children, add point here
        if len(self.points) < self.max_points and not self.is_divided:
            self.points.append((index, x, y))
            return True
        
        # Otherwise, subdivide if needed
        if not self.is_divided:
            self._subdivide()
        
        # Try to insert in children
        for child in self.children:
            if child and child.insert(index, x, y):
                return True
        
        # If we couldn't insert in children, add to this node
        self.points.append((index, x, y))
        return True
    
    def _subdivide(self):
        """Subdivide this node into four quadrants."""
        if self.max_depth <= 0:
            return
        
        x = self.bounds.x()
        y = self.bounds.y()
        w = self.bounds.width() / 2
        h = self.bounds.height() / 2
        
        # Create four child quadrants
        self.children[0] = QuadTreeNode(QRectF(x, y, w, h), 
                                       self.max_points, self.max_depth - 1)  # NW
        self.children[1] = QuadTreeNode(QRectF(x + w, y, w, h), 
                                       self.max_points, self.max_depth - 1)  # NE
        self.children[2] = QuadTreeNode(QRectF(x, y + h, w, h), 
                                       self.max_points, self.max_depth - 1)  # SW
        self.children[3] = QuadTreeNode(QRectF(x + w, y + h, w, h), 
                                       self.max_points, self.max_depth - 1)  # SE
        
        self.is_divided = True
        
        # Redistribute existing points to children
        for point in self.points:
            index, px, py = point
            for child in self.children:
                if child and child.bounds.contains(QPointF(px, py)):
                    child.insert(index, px, py)
                    break
        
        self.points.clear()
    
    def query_range(self, range_bounds: QRectF) -> List[Tuple[int, float, float]]:
        """Query all points within a given range."""
        result = []
        
        # If bounds don't intersect, return empty
        if not self.bounds.intersects(range_bounds):
            return result
        
        # Add points from this node that are in range
        for point in self.points:
            index, px, py = point
            if range_bounds.contains(QPointF(px, py)):
                result.append(point)
        
        # Query children if divided
        if self.is_divided:
            for child in self.children:
                if child:
                    result.extend(child.query_range(range_bounds))
        
        return result
    
    def find_nearest(self, x: float, y: float, max_distance: float = float('inf')) -> Optional[Tuple[int, float, float, float]]:
        """Find the nearest point within max_distance."""
        candidates = self._get_candidates_for_nearest(x, y, max_distance)
        
        if not candidates:
            return None
        
        # Find closest candidate
        best_point = None
        best_distance = max_distance
        
        for index, px, py in candidates:
            distance = math.sqrt((x - px)**2 + (y - py)**2)
            if distance < best_distance:
                best_distance = distance
                best_point = (index, px, py, distance)
        
        return best_point
    
    def _get_candidates_for_nearest(self, x: float, y: float, max_distance: float) -> List[Tuple[int, float, float]]:
        """Get candidate points for nearest neighbor search."""
        # Create search rectangle
        search_rect = QRectF(
            x - max_distance, y - max_distance,
            2 * max_distance, 2 * max_distance
        )
        
        return self.query_range(search_rect)


class OptimizedCache:
    """
    LRU cache with size limits to prevent memory leaks.
    """
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache: Dict = {}
        self.access_order: List = []
        self.size = 0
    
    def get(self, key, default=None):
        """Get value from cache, updating access order."""
        if key in self.cache:
            # Move to end (most recently used)
            self.access_order.remove(key)
            self.access_order.append(key)
            return self.cache[key]
        return default
    
    def set(self, key, value):
        """Set value in cache with LRU eviction."""
        if key in self.cache:
            # Update existing key
            self.cache[key] = value
            self.access_order.remove(key)
            self.access_order.append(key)
        else:
            # Add new key
            if self.size >= self.max_size:
                # Evict least recently used
                lru_key = self.access_order.pop(0)
                del self.cache[lru_key]
                self.size -= 1
            
            self.cache[key] = value
            self.access_order.append(key)
            self.size += 1
    
    def clear(self):
        """Clear all cache entries."""
        self.cache.clear()
        self.access_order.clear()
        self.size = 0
    
    def get_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "size": self.size,
            "max_size": self.max_size,
            "utilization": self.size / self.max_size if self.max_size > 0 else 0
        }


class PerformanceOptimizedCurveView:
    """
    Performance-optimized version of CurveViewWidget methods.
    
    Demonstrates implementation of key optimizations:
    - Viewport culling
    - Spatial indexing for point selection  
    - LRU cache management
    - Efficient coordinate transformations
    """
    
    def __init__(self):
        # Spatial index for fast point lookup
        self.spatial_index: Optional[QuadTreeNode] = None
        self.spatial_index_dirty = True
        
        # Optimized caches with LRU eviction
        self.screen_points_cache = OptimizedCache(max_size=20000)
        self.visible_indices_cache = OptimizedCache(max_size=100)
        self.transform_cache = OptimizedCache(max_size=10)
        
        # Viewport culling
        self.viewport_bounds: Optional[ViewportBounds] = None
        self.viewport_margin = 50  # Extra pixels around viewport
        
        # Performance tracking
        self.paint_time_samples = []
        self.selection_time_samples = []
        
        # Mock data for demonstration
        self.curve_data = []
        self.selected_indices: Set[int] = set()
        self.point_radius = 5
    
    def optimized_paint_points(self, painter: QPainter, viewport_rect: QRectF) -> None:
        """
        Optimized point painting with viewport culling.
        
        This method demonstrates the primary optimization: only render points
        that are actually visible in the current viewport.
        """
        if not self.curve_data:
            return
        
        start_time = time.perf_counter()
        
        # Update viewport bounds for culling
        self._update_viewport_bounds(viewport_rect)
        
        # Get visible indices using spatial index
        visible_indices = self._get_visible_point_indices()
        
        # Count points before and after culling for statistics
        total_points = len(self.curve_data)
        visible_points = len(visible_indices)
        
        painter.save()
        
        # Batch drawing operations by color to minimize state changes
        color_batches = self._batch_points_by_color(visible_indices)
        
        for color, indices in color_batches.items():
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(Qt.PenStyle.NoPen))
            
            for idx in indices:
                screen_pos = self._get_screen_position_cached(idx)
                if screen_pos:
                    painter.drawEllipse(screen_pos, self.point_radius, self.point_radius)
        
        painter.restore()
        
        # Track performance
        paint_time = (time.perf_counter() - start_time) * 1000.0
        self.paint_time_samples.append(paint_time)
        if len(self.paint_time_samples) > 100:
            self.paint_time_samples.pop(0)
        
        # Log culling efficiency periodically
        if len(self.paint_time_samples) % 60 == 0:  # Every 60 frames
            culling_efficiency = ((total_points - visible_points) / total_points) * 100
            avg_paint_time = sum(self.paint_time_samples[-10:]) / 10
            print(f"Culling: {culling_efficiency:.1f}% points skipped, "
                  f"Paint time: {avg_paint_time:.2f}ms")
    
    def optimized_find_point_at(self, x: float, y: float, max_distance: float = 20.0) -> int:
        """
        Optimized point selection using spatial indexing.
        
        Replaces O(n) linear search with O(log n) spatial query.
        """
        start_time = time.perf_counter()
        
        # Rebuild spatial index if needed
        if self.spatial_index_dirty:
            self._rebuild_spatial_index()
        
        result_index = -1
        
        if self.spatial_index:
            nearest = self.spatial_index.find_nearest(x, y, max_distance)
            if nearest:
                result_index = nearest[0]  # Return point index
        
        # Track performance
        selection_time = (time.perf_counter() - start_time) * 1000.0
        self.selection_time_samples.append(selection_time)
        if len(self.selection_time_samples) > 50:
            self.selection_time_samples.pop(0)
        
        return result_index
    
    def optimized_invalidate_caches(self, invalidate_transform: bool = True) -> None:
        """
        Smarter cache invalidation that only clears what's needed.
        
        Instead of clearing all caches, selectively invalidate based on what changed.
        """
        if invalidate_transform:
            # Transform changed, need to recalculate screen positions
            self.screen_points_cache.clear()
            self.visible_indices_cache.clear()
            self.transform_cache.clear()
        else:
            # Only data changed, transform cache can be preserved
            self.visible_indices_cache.clear()
            # Screen points cache may still be valid if only selection changed
    
    def optimized_batch_update_points(self, point_updates: List[Tuple[int, float, float]]) -> None:
        """
        Batch point updates to minimize cache invalidation.
        
        Instead of invalidating caches for each point update, batch them
        and invalidate once at the end.
        """
        # Store original cache state
        cache_keys_to_update = set()
        
        # Apply all updates
        for index, new_x, new_y in point_updates:
            if 0 <= index < len(self.curve_data):
                # Update data
                old_point = self.curve_data[index]
                self.curve_data[index] = (old_point[0], new_x, new_y, *old_point[3:])
                
                # Track what needs cache updates
                cache_keys_to_update.add(index)
        
        # Invalidate only affected cache entries
        for index in cache_keys_to_update:
            self.screen_points_cache.cache.pop(index, None)
        
        # Mark spatial index as dirty
        self.spatial_index_dirty = True
    
    def _update_viewport_bounds(self, viewport_rect: QRectF) -> None:
        """Update viewport bounds for culling calculations."""
        margin = self.viewport_margin
        
        self.viewport_bounds = ViewportBounds(
            left=viewport_rect.left() - margin,
            right=viewport_rect.right() + margin,
            top=viewport_rect.top() - margin,
            bottom=viewport_rect.bottom() + margin
        )
    
    def _get_visible_point_indices(self) -> List[int]:
        """Get indices of points visible in current viewport."""
        if not self.viewport_bounds:
            return list(range(len(self.curve_data)))
        
        # Use cache key based on viewport bounds
        cache_key = f"{self.viewport_bounds.left}_{self.viewport_bounds.right}_{self.viewport_bounds.top}_{self.viewport_bounds.bottom}"
        
        cached_indices = self.visible_indices_cache.get(cache_key)
        if cached_indices is not None:
            return cached_indices
        
        visible_indices = []
        
        if self.spatial_index:
            # Use spatial index for efficient viewport query
            query_rect = QRectF(
                self.viewport_bounds.left, self.viewport_bounds.top,
                self.viewport_bounds.right - self.viewport_bounds.left,
                self.viewport_bounds.bottom - self.viewport_bounds.top
            )
            
            spatial_results = self.spatial_index.query_range(query_rect)
            visible_indices = [idx for idx, _, _ in spatial_results]
        else:
            # Fallback to linear search with culling
            for idx, point in enumerate(self.curve_data):
                _, x, y = point[:3]
                screen_pos = self._get_screen_position_cached(idx)
                if screen_pos and self.viewport_bounds.contains_point(screen_pos.x(), screen_pos.y()):
                    visible_indices.append(idx)
        
        # Cache the result
        self.visible_indices_cache.set(cache_key, visible_indices)
        return visible_indices
    
    def _batch_points_by_color(self, point_indices: List[int]) -> Dict[QColor, List[int]]:
        """Batch points by color to minimize painter state changes."""
        color_batches = defaultdict(list)
        
        for idx in point_indices:
            if idx < len(self.curve_data):
                # Determine point color based on selection and status
                if idx in self.selected_indices:
                    color = QColor(255, 255, 0)  # Yellow for selected
                else:
                    # Determine by status
                    point = self.curve_data[idx]
                    status = point[3] if len(point) > 3 else "tracked"
                    
                    if status == "keyframe":
                        color = QColor(0, 255, 0)
                    elif status == "interpolated":
                        color = QColor(100, 150, 255)
                    else:
                        color = QColor(255, 100, 100)
                
                color_batches[color].append(idx)
        
        return dict(color_batches)
    
    def _get_screen_position_cached(self, index: int) -> Optional[QPointF]:
        """Get screen position for point with caching."""
        cached_pos = self.screen_points_cache.get(index)
        if cached_pos is not None:
            return cached_pos
        
        if 0 <= index < len(self.curve_data):
            point = self.curve_data[index]
            _, x, y = point[:3]
            
            # This would call the actual transformation method
            # For demo purposes, use simple transformation
            screen_pos = QPointF(x, y)  # Simplified
            
            self.screen_points_cache.set(index, screen_pos)
            return screen_pos
        
        return None
    
    def _rebuild_spatial_index(self) -> None:
        """Rebuild the spatial index from current curve data."""
        if not self.curve_data:
            self.spatial_index = None
            self.spatial_index_dirty = False
            return
        
        # Calculate bounds of all points
        min_x = min_y = float('inf')
        max_x = max_y = float('-inf')
        
        for point in self.curve_data:
            _, x, y = point[:3]
            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
        
        # Add some padding
        padding = 100
        bounds = QRectF(
            min_x - padding, min_y - padding,
            (max_x - min_x) + 2 * padding,
            (max_y - min_y) + 2 * padding
        )
        
        # Create new spatial index
        self.spatial_index = QuadTreeNode(bounds, max_points=10, max_depth=8)
        
        # Insert all points
        for idx, point in enumerate(self.curve_data):
            _, x, y = point[:3]
            self.spatial_index.insert(idx, x, y)
        
        self.spatial_index_dirty = False
        
        print(f"Rebuilt spatial index with {len(self.curve_data)} points")
    
    def get_performance_stats(self) -> Dict[str, Union[float, int, str]]:
        """Get current performance statistics."""
        stats = {}
        
        # Paint performance
        if self.paint_time_samples:
            avg_paint_time = sum(self.paint_time_samples[-10:]) / min(10, len(self.paint_time_samples))
            estimated_fps = 1000.0 / avg_paint_time if avg_paint_time > 0 else 0
            
            stats["avg_paint_time_ms"] = round(avg_paint_time, 2)
            stats["estimated_fps"] = round(estimated_fps, 1)
            stats["paint_samples_count"] = len(self.paint_time_samples)
        
        # Selection performance
        if self.selection_time_samples:
            avg_selection_time = sum(self.selection_time_samples[-10:]) / min(10, len(self.selection_time_samples))
            stats["avg_selection_time_ms"] = round(avg_selection_time, 3)
            stats["selection_samples_count"] = len(self.selection_time_samples)
        
        # Cache statistics
        stats["screen_cache"] = self.screen_points_cache.get_stats()
        stats["visible_cache"] = self.visible_indices_cache.get_stats()
        stats["transform_cache"] = self.transform_cache.get_stats()
        
        # Spatial index
        stats["spatial_index_enabled"] = self.spatial_index is not None
        stats["spatial_index_dirty"] = self.spatial_index_dirty
        
        return stats


# Example usage and performance comparison
def performance_comparison_demo():
    """
    Demonstrate performance improvements with optimized vs unoptimized methods.
    """
    print("Performance Optimization Demo")
    print("=" * 50)
    
    # Create optimized curve view
    optimized_view = PerformanceOptimizedCurveView()
    
    # Generate test data
    test_data = []
    for i in range(10000):
        frame = i
        x = 100 + (i % 1920)
        y = 540 + 200 * math.sin(i * 0.01)
        status = "keyframe" if i % 100 == 0 else "tracked"
        test_data.append((frame, x, y, status))
    
    optimized_view.curve_data = test_data
    
    # Test point selection performance
    print("\nPoint Selection Performance:")
    print("-" * 30)
    
    # Test multiple selections
    test_positions = [(500, 600), (1000, 400), (1500, 700), (300, 500), (800, 300)]
    
    for pos_x, pos_y in test_positions:
        found_idx = optimized_view.optimized_find_point_at(pos_x, pos_y)
        if optimized_view.selection_time_samples:
            selection_time = optimized_view.selection_time_samples[-1]
            print(f"  Position ({pos_x}, {pos_y}): Found index {found_idx} in {selection_time:.3f}ms")
    
    # Show performance stats
    stats = optimized_view.get_performance_stats()
    print(f"\nPerformance Statistics:")
    print(f"  Average selection time: {stats.get('avg_selection_time_ms', 'N/A')} ms")
    print(f"  Screen cache utilization: {stats['screen_cache']['utilization']:.1%}")
    print(f"  Spatial index enabled: {stats['spatial_index_enabled']}")
    
    print("\nOptimization Benefits:")
    print("  ✅ Point selection: O(log n) instead of O(n)")
    print("  ✅ Viewport culling: Only render visible points")  
    print("  ✅ LRU caches: Prevent memory leaks")
    print("  ✅ Batch rendering: Minimize painter state changes")
    print("  ✅ Smart invalidation: Reduce unnecessary recalculation")


if __name__ == "__main__":
    performance_comparison_demo()
#!/usr/bin/env python
"""
Performance Testing Suite for CurveEditor Application.

This script provides comprehensive performance testing for the CurveViewWidget,
focusing on rendering performance, memory usage, interaction responsiveness,
and data operations with various dataset sizes.
"""

import gc
import json
import logging
import os
import random
import sys
import time
from pathlib import Path
from typing import List, Tuple

from PySide6.QtCore import QPointF, QTimer, Qt
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtWidgets import QApplication, QMainWindow

# Import CurveEditor components
from ui.curve_view_widget import CurveViewWidget
from ui.main_window import MainWindow
from performance_profiler import create_performance_profiler, profile_curve_view_widget
from core.models import CurvePoint

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PerformanceTestSuite:
    """Comprehensive performance test suite for CurveEditor."""
    
    def __init__(self):
        self.app = QApplication.instance() or QApplication([])
        self.profiler = create_performance_profiler()
        self.test_results = {}
        self.test_data_sets = {}
        
        # Create main window and curve widget for testing
        self.main_window = MainWindow()
        self.curve_widget = self.main_window.findChild(CurveViewWidget) or CurveViewWidget()
        
        # Apply profiling to the widget
        self.widget_profiler = profile_curve_view_widget(self.curve_widget)
        
        logger.info("Performance test suite initialized")
    
    def generate_test_datasets(self) -> None:
        """Generate various test datasets for performance testing."""
        logger.info("Generating test datasets...")
        
        # Small dataset (100 points) - typical usage
        self.test_data_sets["small"] = self._generate_curve_data(
            count=100, 
            x_range=(0, 1920), 
            y_range=(0, 1080),
            pattern="smooth"
        )
        
        # Medium dataset (1,000 points) - heavy usage
        self.test_data_sets["medium"] = self._generate_curve_data(
            count=1000,
            x_range=(0, 1920),
            y_range=(0, 1080), 
            pattern="complex"
        )
        
        # Large dataset (10,000 points) - stress test
        self.test_data_sets["large"] = self._generate_curve_data(
            count=10000,
            x_range=(0, 1920),
            y_range=(0, 1080),
            pattern="random"
        )
        
        # Dense dataset (5,000 points in small area) - viewport culling test
        self.test_data_sets["dense"] = self._generate_curve_data(
            count=5000,
            x_range=(500, 700),
            y_range=(400, 600),
            pattern="dense_cluster"
        )
        
        logger.info(f"Generated {len(self.test_data_sets)} test datasets")
    
    def _generate_curve_data(self, count: int, x_range: Tuple[int, int], 
                           y_range: Tuple[int, int], pattern: str) -> List[Tuple]:
        """Generate curve data with specified pattern."""
        data = []
        x_min, x_max = x_range
        y_min, y_max = y_range
        
        for i in range(count):
            frame = i
            
            if pattern == "smooth":
                # Smooth sine wave pattern
                t = i / count * 4 * 3.14159
                x = x_min + (x_max - x_min) * (i / count)
                y = y_min + (y_max - y_min) * (0.5 + 0.3 * math.sin(t))
                
            elif pattern == "complex":
                # Multiple overlapping patterns
                t = i / count * 8 * 3.14159
                x = x_min + (x_max - x_min) * (i / count)
                y = (y_min + (y_max - y_min) * (
                    0.5 + 0.2 * math.sin(t) + 
                    0.1 * math.sin(t * 3) + 
                    0.05 * random.random()
                ))
                
            elif pattern == "random":
                # Random distribution
                x = random.uniform(x_min, x_max)
                y = random.uniform(y_min, y_max)
                
            elif pattern == "dense_cluster":
                # Dense clustering with some outliers
                if random.random() < 0.9:
                    # Clustered points
                    center_x = (x_min + x_max) / 2
                    center_y = (y_min + y_max) / 2
                    radius = min(x_max - x_min, y_max - y_min) / 4
                    
                    angle = random.uniform(0, 2 * 3.14159)
                    r = random.uniform(0, radius)
                    x = center_x + r * math.cos(angle)
                    y = center_y + r * math.sin(angle)
                else:
                    # Outliers
                    x = random.uniform(x_min, x_max)
                    y = random.uniform(y_min, y_max)
            
            # Assign status randomly
            status = random.choice(["tracked", "keyframe", "interpolated"])
            data.append((frame, x, y, status))
        
        return data
    
    def test_rendering_performance(self) -> None:
        """Test rendering performance with different dataset sizes."""
        logger.info("Starting rendering performance tests...")
        
        results = {}
        
        for dataset_name, data in self.test_data_sets.items():
            logger.info(f"Testing rendering with {dataset_name} dataset ({len(data)} points)")
            
            # Set test data
            self.curve_widget.set_curve_data(data)
            
            # Force initial update
            self.curve_widget.update()
            self.app.processEvents()
            
            # Measure paint times
            paint_times = []
            frame_count = 50  # Measure 50 frames
            
            start_time = time.time()
            for i in range(frame_count):
                self.curve_widget.update()
                self.app.processEvents()
                time.sleep(0.001)  # Small delay to avoid overwhelming
            
            total_time = time.time() - start_time
            
            # Get metrics from profiler
            paint_metrics = [m for name, m in self.widget_profiler.metrics.items() 
                           if "paint_event" in name]
            
            if paint_metrics:
                avg_paint_time = sum(m.avg_time for m in paint_metrics) / len(paint_metrics)
                max_paint_time = max(m.max_time for m in paint_metrics)
                estimated_fps = sum(m.fps_estimate for m in paint_metrics) / len(paint_metrics)
            else:
                # Fallback calculation
                avg_paint_time = (total_time * 1000) / frame_count
                max_paint_time = avg_paint_time * 2  # Estimate
                estimated_fps = 1000 / avg_paint_time if avg_paint_time > 0 else 0
            
            results[dataset_name] = {
                "point_count": len(data),
                "avg_paint_time_ms": avg_paint_time,
                "max_paint_time_ms": max_paint_time,
                "estimated_fps": estimated_fps,
                "total_test_time_s": total_time,
                "meets_60fps": estimated_fps >= 60.0,
                "meets_30fps": estimated_fps >= 30.0
            }
            
            logger.info(f"  Average paint time: {avg_paint_time:.2f}ms")
            logger.info(f"  Estimated FPS: {estimated_fps:.1f}")
        
        self.test_results["rendering"] = results
    
    def test_memory_usage(self) -> None:
        """Test memory usage with different dataset sizes."""
        logger.info("Starting memory usage tests...")
        
        results = {}
        
        # Get baseline memory usage
        gc.collect()
        baseline_memory = self.widget_profiler.process.memory_info().rss / 1024 / 1024
        
        for dataset_name, data in self.test_data_sets.items():
            logger.info(f"Testing memory with {dataset_name} dataset ({len(data)} points)")
            
            # Clear any existing data
            self.curve_widget.set_curve_data([])
            gc.collect()
            
            # Measure memory before loading
            memory_before = self.widget_profiler.process.memory_info().rss / 1024 / 1024
            
            # Load test data
            self.curve_widget.set_curve_data(data)
            self.curve_widget.update()
            self.app.processEvents()
            
            # Measure memory after loading
            memory_after = self.widget_profiler.process.memory_info().rss / 1024 / 1024
            memory_increase = memory_after - memory_before
            
            # Calculate memory per point
            memory_per_point_kb = (memory_increase * 1024) / len(data) if len(data) > 0 else 0
            
            # Test memory leak by reloading same data multiple times
            leak_test_iterations = 5
            memory_samples = []
            
            for i in range(leak_test_iterations):
                self.curve_widget.set_curve_data([])  # Clear
                self.curve_widget.set_curve_data(data)  # Reload
                self.app.processEvents()
                gc.collect()
                
                memory_sample = self.widget_profiler.process.memory_info().rss / 1024 / 1024
                memory_samples.append(memory_sample)
                time.sleep(0.1)  # Brief pause
            
            # Analyze memory leak
            memory_growth = memory_samples[-1] - memory_samples[0]
            has_potential_leak = memory_growth > 5.0  # Growing > 5MB over test
            
            results[dataset_name] = {
                "point_count": len(data),
                "baseline_memory_mb": baseline_memory,
                "memory_before_mb": memory_before,
                "memory_after_mb": memory_after,
                "memory_increase_mb": memory_increase,
                "memory_per_point_kb": memory_per_point_kb,
                "memory_samples": memory_samples,
                "memory_growth_mb": memory_growth,
                "potential_leak": has_potential_leak
            }
            
            logger.info(f"  Memory increase: {memory_increase:.1f}MB")
            logger.info(f"  Memory per point: {memory_per_point_kb:.2f}KB")
            
            if has_potential_leak:
                logger.warning(f"  Potential memory leak detected: {memory_growth:.1f}MB growth")
        
        self.test_results["memory"] = results
    
    def test_interaction_responsiveness(self) -> None:
        """Test mouse interaction responsiveness."""
        logger.info("Starting interaction responsiveness tests...")
        
        results = {}
        
        for dataset_name, data in self.test_data_sets.items():
            logger.info(f"Testing interaction with {dataset_name} dataset ({len(data)} points)")
            
            # Set test data
            self.curve_widget.set_curve_data(data)
            self.app.processEvents()
            
            # Simulate mouse interactions
            widget_center = QPointF(
                self.curve_widget.width() / 2,
                self.curve_widget.height() / 2
            )
            
            # Test point selection
            selection_times = []
            for i in range(20):  # 20 selection tests
                with self.profiler.profile_operation("point_selection_test"):
                    # Simulate finding a point near center
                    idx = self.curve_widget._find_point_at(widget_center)
                
                if "point_selection_test" in self.profiler.metrics:
                    selection_times.append(
                        self.profiler.metrics["point_selection_test"].recent_times[-1]
                    )
            
            # Test dragging simulation
            drag_times = []
            for i in range(10):  # 10 drag tests
                start_pos = QPointF(
                    widget_center.x() + random.uniform(-100, 100),
                    widget_center.y() + random.uniform(-100, 100)
                )
                
                end_pos = QPointF(
                    start_pos.x() + random.uniform(-50, 50),
                    start_pos.y() + random.uniform(-50, 50)
                )
                
                with self.profiler.profile_operation("drag_test"):
                    # Simulate drag operation
                    delta = end_pos - start_pos
                    self.curve_widget._drag_point(0, delta)  # Drag first point
                
                if "drag_test" in self.profiler.metrics:
                    drag_times.append(
                        self.profiler.metrics["drag_test"].recent_times[-1]
                    )
            
            # Calculate statistics
            avg_selection_time = sum(selection_times) / len(selection_times) if selection_times else 0
            avg_drag_time = sum(drag_times) / len(drag_times) if drag_times else 0
            
            results[dataset_name] = {
                "point_count": len(data),
                "avg_selection_time_ms": avg_selection_time,
                "avg_drag_time_ms": avg_drag_time,
                "selection_responsive": avg_selection_time < 50.0,  # < 50ms
                "drag_responsive": avg_drag_time < 10.0,  # < 10ms
                "selection_times": selection_times,
                "drag_times": drag_times
            }
            
            logger.info(f"  Selection time: {avg_selection_time:.2f}ms")
            logger.info(f"  Drag time: {avg_drag_time:.2f}ms")
        
        self.test_results["interaction"] = results
    
    def test_data_operations(self) -> None:
        """Test data operation performance (loading, saving, transformations)."""
        logger.info("Starting data operation tests...")
        
        results = {}
        
        for dataset_name, data in self.test_data_sets.items():
            logger.info(f"Testing data operations with {dataset_name} dataset ({len(data)} points)")
            
            # Test data loading
            load_times = []
            for i in range(5):
                with self.profiler.profile_operation("data_load_test"):
                    self.curve_widget.set_curve_data(data)
                
                if "data_load_test" in self.profiler.metrics:
                    load_times.append(
                        self.profiler.metrics["data_load_test"].recent_times[-1]
                    )
            
            # Test coordinate transformations
            transform_times = []
            for i in range(100):  # Many transform operations
                with self.profiler.profile_operation("coordinate_transform_test"):
                    # Transform random data coordinate to screen
                    if data:
                        point = random.choice(data)
                        screen_pos = self.curve_widget.data_to_screen(point[1], point[2])
                        data_pos = self.curve_widget.screen_to_data(screen_pos)
                
                if "coordinate_transform_test" in self.profiler.metrics:
                    transform_times.append(
                        self.profiler.metrics["coordinate_transform_test"].recent_times[-1]
                    )
            
            # Test cache operations
            cache_times = []
            for i in range(10):
                with self.profiler.profile_operation("cache_update_test"):
                    self.curve_widget._invalidate_caches()
                    self.curve_widget._update_screen_points_cache()
                
                if "cache_update_test" in self.profiler.metrics:
                    cache_times.append(
                        self.profiler.metrics["cache_update_test"].recent_times[-1]
                    )
            
            # Calculate statistics
            avg_load_time = sum(load_times) / len(load_times) if load_times else 0
            avg_transform_time = sum(transform_times) / len(transform_times) if transform_times else 0
            avg_cache_time = sum(cache_times) / len(cache_times) if cache_times else 0
            
            results[dataset_name] = {
                "point_count": len(data),
                "avg_load_time_ms": avg_load_time,
                "avg_transform_time_ms": avg_transform_time,
                "avg_cache_time_ms": avg_cache_time,
                "load_efficient": avg_load_time < 100.0,  # < 100ms
                "transform_efficient": avg_transform_time < 1.0,  # < 1ms
                "cache_efficient": avg_cache_time < 50.0  # < 50ms
            }
            
            logger.info(f"  Load time: {avg_load_time:.2f}ms")
            logger.info(f"  Transform time: {avg_transform_time:.3f}ms")
            logger.info(f"  Cache time: {avg_cache_time:.2f}ms")
        
        self.test_results["data_operations"] = results
    
    def test_zoom_pan_performance(self) -> None:
        """Test zoom and pan operations performance."""
        logger.info("Starting zoom/pan performance tests...")
        
        results = {}
        
        for dataset_name, data in self.test_data_sets.items():
            logger.info(f"Testing zoom/pan with {dataset_name} dataset ({len(data)} points)")
            
            # Set test data
            self.curve_widget.set_curve_data(data)
            self.app.processEvents()
            
            # Test zoom operations
            zoom_times = []
            original_zoom = self.curve_widget.zoom_factor
            
            for i in range(20):  # Test multiple zoom levels
                zoom_factor = 0.5 + (i / 20.0) * 4.0  # 0.5x to 4.5x zoom
                
                with self.profiler.profile_operation("zoom_test"):
                    self.curve_widget.zoom_factor = zoom_factor
                    self.curve_widget._invalidate_caches()
                    self.curve_widget.update()
                    self.app.processEvents()
                
                if "zoom_test" in self.profiler.metrics:
                    zoom_times.append(
                        self.profiler.metrics["zoom_test"].recent_times[-1]
                    )
            
            # Reset zoom
            self.curve_widget.zoom_factor = original_zoom
            
            # Test pan operations
            pan_times = []
            original_pan_x = self.curve_widget.pan_offset_x
            original_pan_y = self.curve_widget.pan_offset_y
            
            for i in range(20):  # Test multiple pan positions
                pan_x = random.uniform(-200, 200)
                pan_y = random.uniform(-200, 200)
                
                with self.profiler.profile_operation("pan_test"):
                    self.curve_widget.pan_offset_x = pan_x
                    self.curve_widget.pan_offset_y = pan_y
                    self.curve_widget._invalidate_caches()
                    self.curve_widget.update()
                    self.app.processEvents()
                
                if "pan_test" in self.profiler.metrics:
                    pan_times.append(
                        self.profiler.metrics["pan_test"].recent_times[-1]
                    )
            
            # Reset pan
            self.curve_widget.pan_offset_x = original_pan_x
            self.curve_widget.pan_offset_y = original_pan_y
            
            # Calculate statistics
            avg_zoom_time = sum(zoom_times) / len(zoom_times) if zoom_times else 0
            avg_pan_time = sum(pan_times) / len(pan_times) if pan_times else 0
            
            results[dataset_name] = {
                "point_count": len(data),
                "avg_zoom_time_ms": avg_zoom_time,
                "avg_pan_time_ms": avg_pan_time,
                "zoom_responsive": avg_zoom_time < 50.0,  # < 50ms
                "pan_responsive": avg_pan_time < 50.0,  # < 50ms
                "zoom_times": zoom_times,
                "pan_times": pan_times
            }
            
            logger.info(f"  Zoom time: {avg_zoom_time:.2f}ms")
            logger.info(f"  Pan time: {avg_pan_time:.2f}ms")
        
        self.test_results["zoom_pan"] = results
    
    def run_full_test_suite(self) -> dict:
        """Run the complete performance test suite."""
        logger.info("Starting comprehensive performance test suite...")
        
        start_time = time.time()
        
        # Generate test datasets
        self.generate_test_datasets()
        
        # Run all tests
        self.test_rendering_performance()
        self.test_memory_usage()
        self.test_interaction_responsiveness()
        self.test_data_operations()
        self.test_zoom_pan_performance()
        
        total_time = time.time() - start_time
        
        # Add summary information
        self.test_results["meta"] = {
            "total_test_time_s": total_time,
            "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "datasets_tested": list(self.test_data_sets.keys()),
            "tests_completed": list(self.test_results.keys())
        }
        
        logger.info(f"Performance test suite completed in {total_time:.1f} seconds")
        
        return self.test_results
    
    def generate_performance_report(self) -> str:
        """Generate comprehensive performance analysis report."""
        if not self.test_results:
            return "No test results available. Run test suite first."
        
        report = []
        report.append("=" * 80)
        report.append("CURVEEDITOR PERFORMANCE TEST REPORT")
        report.append("=" * 80)
        report.append(f"Generated: {self.test_results.get('meta', {}).get('test_timestamp', 'Unknown')}")
        report.append(f"Total test time: {self.test_results.get('meta', {}).get('total_test_time_s', 0):.1f}s")
        report.append("")
        
        # Rendering Performance
        if "rendering" in self.test_results:
            report.append("RENDERING PERFORMANCE")
            report.append("-" * 40)
            
            for dataset, results in self.test_results["rendering"].items():
                fps_status = "✅ EXCELLENT" if results["estimated_fps"] >= 60 else \
                           "⚡ GOOD" if results["estimated_fps"] >= 30 else \
                           "⚠️  POOR"
                
                report.append(f"{dataset.upper()} ({results['point_count']:,} points):")
                report.append(f"  Average paint time: {results['avg_paint_time_ms']:.2f}ms")
                report.append(f"  Estimated FPS: {results['estimated_fps']:.1f} {fps_status}")
                report.append(f"  60 FPS target: {'✅' if results['meets_60fps'] else '❌'}")
                report.append("")
        
        # Memory Usage
        if "memory" in self.test_results:
            report.append("MEMORY USAGE ANALYSIS")
            report.append("-" * 40)
            
            for dataset, results in self.test_results["memory"].items():
                leak_status = "⚠️  POTENTIAL LEAK" if results["potential_leak"] else "✅ STABLE"
                
                report.append(f"{dataset.upper()} ({results['point_count']:,} points):")
                report.append(f"  Memory per point: {results['memory_per_point_kb']:.2f}KB")
                report.append(f"  Total increase: {results['memory_increase_mb']:.1f}MB")
                report.append(f"  Memory stability: {leak_status}")
                
                if results["potential_leak"]:
                    report.append(f"  Growth detected: {results['memory_growth_mb']:.1f}MB")
                report.append("")
        
        # Interaction Responsiveness
        if "interaction" in self.test_results:
            report.append("INTERACTION RESPONSIVENESS")
            report.append("-" * 40)
            
            for dataset, results in self.test_results["interaction"].items():
                selection_status = "✅ RESPONSIVE" if results["selection_responsive"] else "⚠️  SLOW"
                drag_status = "✅ RESPONSIVE" if results["drag_responsive"] else "⚠️  SLOW"
                
                report.append(f"{dataset.upper()} ({results['point_count']:,} points):")
                report.append(f"  Point selection: {results['avg_selection_time_ms']:.2f}ms {selection_status}")
                report.append(f"  Drag operations: {results['avg_drag_time_ms']:.2f}ms {drag_status}")
                report.append("")
        
        # Data Operations
        if "data_operations" in self.test_results:
            report.append("DATA OPERATIONS PERFORMANCE")
            report.append("-" * 40)
            
            for dataset, results in self.test_results["data_operations"].items():
                load_status = "✅ FAST" if results["load_efficient"] else "⚠️  SLOW"
                transform_status = "✅ FAST" if results["transform_efficient"] else "⚠️  SLOW"
                cache_status = "✅ FAST" if results["cache_efficient"] else "⚠️  SLOW"
                
                report.append(f"{dataset.upper()} ({results['point_count']:,} points):")
                report.append(f"  Data loading: {results['avg_load_time_ms']:.2f}ms {load_status}")
                report.append(f"  Coordinate transform: {results['avg_transform_time_ms']:.3f}ms {transform_status}")
                report.append(f"  Cache updates: {results['avg_cache_time_ms']:.2f}ms {cache_status}")
                report.append("")
        
        # Zoom/Pan Performance
        if "zoom_pan" in self.test_results:
            report.append("ZOOM/PAN PERFORMANCE")
            report.append("-" * 40)
            
            for dataset, results in self.test_results["zoom_pan"].items():
                zoom_status = "✅ RESPONSIVE" if results["zoom_responsive"] else "⚠️  SLOW"
                pan_status = "✅ RESPONSIVE" if results["pan_responsive"] else "⚠️  SLOW"
                
                report.append(f"{dataset.upper()} ({results['point_count']:,} points):")
                report.append(f"  Zoom operations: {results['avg_zoom_time_ms']:.2f}ms {zoom_status}")
                report.append(f"  Pan operations: {results['avg_pan_time_ms']:.2f}ms {pan_status}")
                report.append("")
        
        # Optimization Recommendations
        report.append("OPTIMIZATION RECOMMENDATIONS")
        report.append("-" * 40)
        report.extend(self._generate_optimization_recommendations())
        
        return "\n".join(report)
    
    def _generate_optimization_recommendations(self) -> List[str]:
        """Generate specific optimization recommendations based on test results."""
        recommendations = []
        
        # Check rendering performance issues
        if "rendering" in self.test_results:
            poor_rendering = [
                (name, results) for name, results in self.test_results["rendering"].items()
                if not results["meets_30fps"]
            ]
            
            if poor_rendering:
                recommendations.append("🔴 CRITICAL: Poor rendering performance detected")
                recommendations.append("   Immediate actions:")
                recommendations.append("   - Implement viewport culling to skip off-screen points")
                recommendations.append("   - Add level-of-detail rendering (reduce detail when zoomed out)")
                recommendations.append("   - Cache screen coordinates between frames")
                recommendations.append("   - Consider QOpenGLWidget for hardware acceleration")
                recommendations.append("")
        
        # Check memory issues
        if "memory" in self.test_results:
            memory_leaks = [
                (name, results) for name, results in self.test_results["memory"].items()
                if results["potential_leak"]
            ]
            
            if memory_leaks:
                recommendations.append("🟡 WARNING: Potential memory leaks detected")
                recommendations.append("   Actions:")
                recommendations.append("   - Clear screen coordinate caches periodically")
                recommendations.append("   - Implement object pooling for point rendering")
                recommendations.append("   - Check for circular references in data structures")
                recommendations.append("   - Use weak references for signal connections")
                recommendations.append("")
            
            # Check memory efficiency
            high_memory = [
                (name, results) for name, results in self.test_results["memory"].items()
                if results["memory_per_point_kb"] > 1.0  # > 1KB per point
            ]
            
            if high_memory:
                recommendations.append("🟡 NOTICE: High memory usage per point")
                recommendations.append("   Optimizations:")
                recommendations.append("   - Use more compact data structures")
                recommendations.append("   - Lazy-load point details (status, metadata)")
                recommendations.append("   - Implement data compression for large datasets")
                recommendations.append("")
        
        # Check interaction responsiveness
        if "interaction" in self.test_results:
            slow_interactions = [
                (name, results) for name, results in self.test_results["interaction"].items()
                if not results["selection_responsive"] or not results["drag_responsive"]
            ]
            
            if slow_interactions:
                recommendations.append("🟡 WARNING: Slow interaction performance")
                recommendations.append("   Improvements:")
                recommendations.append("   - Use spatial indexing (quadtree) for point lookup")
                recommendations.append("   - Defer expensive operations until mouse release")
                recommendations.append("   - Batch update operations during drag")
                recommendations.append("   - Implement progressive selection for large datasets")
                recommendations.append("")
        
        # Overall architectural recommendations
        if not recommendations:
            recommendations.append("✅ Performance is within acceptable ranges!")
            recommendations.append("")
            
        recommendations.append("GENERAL OPTIMIZATIONS:")
        recommendations.append("• Consider implementing:")
        recommendations.append("  - Viewport-based culling system")
        recommendations.append("  - Multi-threaded rendering pipeline")
        recommendations.append("  - GPU-accelerated point rendering")
        recommendations.append("  - Smart caching with LRU eviction")
        recommendations.append("  - Progressive loading for large files")
        
        return recommendations
    
    def save_results(self, filename: str) -> None:
        """Save test results to JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.test_results, f, indent=2)
        
        logger.info(f"Test results saved to {filename}")
    
    def cleanup(self) -> None:
        """Clean up test resources."""
        if hasattr(self, 'widget_profiler'):
            self.widget_profiler.stop_monitoring()
        
        if hasattr(self, 'main_window'):
            self.main_window.close()


def main():
    """Run the performance test suite."""
    import math  # Add missing import
    
    # Create test suite
    test_suite = PerformanceTestSuite()
    
    try:
        # Run all tests
        results = test_suite.run_full_test_suite()
        
        # Generate and save report
        report = test_suite.generate_performance_report()
        print(report)
        
        # Save detailed results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        results_file = f"performance_results_{timestamp}.json"
        test_suite.save_results(results_file)
        
        # Save report
        report_file = f"performance_report_{timestamp}.txt"
        with open(report_file, 'w') as f:
            f.write(report)
        
        print(f"\nDetailed results saved to: {results_file}")
        print(f"Performance report saved to: {report_file}")
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up
        test_suite.cleanup()


if __name__ == "__main__":
    main()
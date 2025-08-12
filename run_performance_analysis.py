#!/usr/bin/env python
"""
Comprehensive Performance Analysis Script for CurveEditor.

This script runs a complete performance analysis of the CurveViewWidget
including rendering, memory, interaction, and data operation profiling
as requested in the task specification.
"""

import json
import logging
import math
import os
import sys
import time
from pathlib import Path

# Ensure the CurveEditor modules are in the path
sys.path.insert(0, str(Path(__file__).parent))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap

# Import CurveEditor components
try:
    from ui.main_window import MainWindow
    from ui.curve_view_widget import CurveViewWidget
    from performance_profiler import create_performance_profiler, profile_curve_view_widget
    from performance_monitor import PerformanceMonitorWidget
    from test_performance import PerformanceTestSuite
except ImportError as e:
    print(f"Error importing CurveEditor components: {e}")
    print("Make sure you're running this script from the CurveEditor directory")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('performance_analysis.log')
    ]
)
logger = logging.getLogger(__name__)


class CurveEditorPerformanceAnalyzer:
    """Comprehensive performance analyzer for CurveEditor application."""
    
    def __init__(self):
        self.app = QApplication.instance() or QApplication([])
        self.results = {}
        self.start_time = time.time()
        
        # Initialize application components
        self.main_window = None
        self.curve_widget = None
        self.profiler = None
        
        logger.info("Performance analyzer initialized")
    
    def setup_application(self):
        """Setup the CurveEditor application for testing."""
        logger.info("Setting up CurveEditor application...")
        
        try:
            # Create main window
            self.main_window = MainWindow()
            
            # Find or create curve widget
            self.curve_widget = self.main_window.findChild(CurveViewWidget)
            if not self.curve_widget:
                # If not found, create one manually
                self.curve_widget = CurveViewWidget(self.main_window)
                self.curve_widget.set_main_window(self.main_window)
            
            # Apply performance profiling
            self.profiler = profile_curve_view_widget(self.curve_widget)
            
            # Show window (required for proper rendering)
            self.main_window.show()
            self.app.processEvents()
            
            logger.info("Application setup complete")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup application: {e}")
            return False
    
    def test_rendering_performance(self):
        """Test 1: Rendering Performance Analysis"""
        logger.info("=" * 60)
        logger.info("TESTING RENDERING PERFORMANCE")
        logger.info("=" * 60)
        
        results = {}
        
        # Define test datasets
        test_datasets = {
            "small_100": self._generate_smooth_curve(100),
            "medium_1000": self._generate_smooth_curve(1000),
            "large_10000": self._generate_smooth_curve(10000),
            "dense_cluster": self._generate_dense_cluster(2000),
        }
        
        for dataset_name, data in test_datasets.items():
            logger.info(f"Testing rendering with {dataset_name} ({len(data)} points)")
            
            # Clear existing data
            self.curve_widget.set_curve_data([])
            self.app.processEvents()
            
            # Load test data
            self.curve_widget.set_curve_data(data)
            self.app.processEvents()
            
            # Measure paint performance
            paint_times = []
            frame_count = 60  # Measure 60 frames for accurate FPS
            
            start_test = time.perf_counter()
            
            for frame in range(frame_count):
                # Force a repaint
                frame_start = time.perf_counter()
                self.curve_widget.update()
                self.app.processEvents()
                frame_time = (time.perf_counter() - frame_start) * 1000.0
                paint_times.append(frame_time)
                
                # Small delay to prevent overwhelming
                time.sleep(0.005)
            
            total_test_time = time.perf_counter() - start_test
            
            # Calculate statistics
            avg_paint_time = sum(paint_times) / len(paint_times)
            min_paint_time = min(paint_times)
            max_paint_time = max(paint_times)
            estimated_fps = 1000.0 / avg_paint_time if avg_paint_time > 0 else 0
            
            # Performance assessment
            performance_rating = "EXCELLENT" if estimated_fps >= 60 else \
                               "GOOD" if estimated_fps >= 30 else \
                               "POOR"
            
            results[dataset_name] = {
                "point_count": len(data),
                "avg_paint_time_ms": round(avg_paint_time, 2),
                "min_paint_time_ms": round(min_paint_time, 2),
                "max_paint_time_ms": round(max_paint_time, 2),
                "estimated_fps": round(estimated_fps, 1),
                "performance_rating": performance_rating,
                "total_test_time_s": round(total_test_time, 2),
                "paint_times_sample": paint_times[:10],  # First 10 samples
                "meets_60fps_target": estimated_fps >= 60,
                "meets_30fps_target": estimated_fps >= 30
            }
            
            logger.info(f"  Average paint time: {avg_paint_time:.2f}ms")
            logger.info(f"  Estimated FPS: {estimated_fps:.1f} ({performance_rating})")
            logger.info(f"  Paint time range: {min_paint_time:.1f} - {max_paint_time:.1f}ms")
        
        self.results["rendering_performance"] = results
        return results
    
    def test_memory_usage(self):
        """Test 2: Memory Usage Analysis"""
        logger.info("=" * 60)
        logger.info("TESTING MEMORY USAGE")
        logger.info("=" * 60)
        
        import gc
        import psutil
        
        process = psutil.Process()
        results = {}
        
        # Get baseline memory
        gc.collect()
        baseline_memory = process.memory_info().rss / 1024 / 1024
        
        test_datasets = {
            "small_100": self._generate_smooth_curve(100),
            "medium_1000": self._generate_smooth_curve(1000),
            "large_10000": self._generate_smooth_curve(10000),
            "extra_large_50000": self._generate_smooth_curve(50000),
        }
        
        for dataset_name, data in test_datasets.items():
            logger.info(f"Testing memory with {dataset_name} ({len(data)} points)")
            
            # Clear and collect garbage
            self.curve_widget.set_curve_data([])
            gc.collect()
            
            # Measure memory before loading
            memory_before = process.memory_info().rss / 1024 / 1024
            
            # Load data
            self.curve_widget.set_curve_data(data)
            self.curve_widget.update()
            self.app.processEvents()
            
            # Force cache population
            self.curve_widget._update_screen_points_cache()
            
            # Measure memory after loading
            memory_after = process.memory_info().rss / 1024 / 1024
            memory_increase = memory_after - memory_before
            memory_per_point = (memory_increase * 1024) / len(data) if len(data) > 0 else 0
            
            # Test for memory leaks by reloading
            leak_test_samples = []
            for i in range(10):
                self.curve_widget.set_curve_data([])
                gc.collect()
                self.curve_widget.set_curve_data(data)
                self.app.processEvents()
                
                current_memory = process.memory_info().rss / 1024 / 1024
                leak_test_samples.append(current_memory)
                time.sleep(0.1)
            
            # Analyze leak pattern
            memory_growth = leak_test_samples[-1] - leak_test_samples[0]
            has_potential_leak = memory_growth > 2.0  # Growing > 2MB
            
            results[dataset_name] = {
                "point_count": len(data),
                "baseline_memory_mb": round(baseline_memory, 1),
                "memory_before_mb": round(memory_before, 1),
                "memory_after_mb": round(memory_after, 1),
                "memory_increase_mb": round(memory_increase, 1),
                "memory_per_point_kb": round(memory_per_point, 2),
                "leak_test_samples": [round(s, 1) for s in leak_test_samples],
                "memory_growth_mb": round(memory_growth, 1),
                "potential_leak_detected": has_potential_leak,
                "memory_efficiency_rating": "GOOD" if memory_per_point < 0.5 else "POOR"
            }
            
            logger.info(f"  Memory increase: {memory_increase:.1f}MB")
            logger.info(f"  Per point: {memory_per_point:.2f}KB")
            if has_potential_leak:
                logger.warning(f"  Potential leak detected: {memory_growth:.1f}MB growth")
        
        self.results["memory_usage"] = results
        return results
    
    def test_interaction_responsiveness(self):
        """Test 3: Interaction Responsiveness"""
        logger.info("=" * 60)
        logger.info("TESTING INTERACTION RESPONSIVENESS")
        logger.info("=" * 60)
        
        from PySide6.QtCore import QPointF
        import random
        
        results = {}
        
        test_datasets = {
            "small_100": self._generate_smooth_curve(100),
            "medium_1000": self._generate_smooth_curve(1000),
            "large_10000": self._generate_smooth_curve(10000),
        }
        
        for dataset_name, data in test_datasets.items():
            logger.info(f"Testing interaction with {dataset_name} ({len(data)} points)")
            
            # Load test data
            self.curve_widget.set_curve_data(data)
            self.app.processEvents()
            
            # Test point selection performance
            selection_times = []
            widget_center = QPointF(
                self.curve_widget.width() / 2,
                self.curve_widget.height() / 2
            )
            
            for i in range(50):  # 50 selection tests
                test_pos = QPointF(
                    widget_center.x() + random.uniform(-200, 200),
                    widget_center.y() + random.uniform(-200, 200)
                )
                
                start_time = time.perf_counter()
                found_idx = self.curve_widget._find_point_at(test_pos)
                selection_time = (time.perf_counter() - start_time) * 1000.0
                selection_times.append(selection_time)
            
            # Test drag performance
            drag_times = []
            for i in range(30):  # 30 drag tests
                if data:  # Only test if we have data
                    start_time = time.perf_counter()
                    
                    # Simulate drag operation
                    delta = QPointF(random.uniform(-10, 10), random.uniform(-10, 10))
                    self.curve_widget._drag_point(0, delta)
                    self.app.processEvents()
                    
                    drag_time = (time.perf_counter() - start_time) * 1000.0
                    drag_times.append(drag_time)
            
            # Calculate statistics
            avg_selection_time = sum(selection_times) / len(selection_times)
            max_selection_time = max(selection_times)
            avg_drag_time = sum(drag_times) / len(drag_times) if drag_times else 0
            max_drag_time = max(drag_times) if drag_times else 0
            
            # Responsiveness ratings
            selection_responsive = avg_selection_time < 5.0  # < 5ms
            drag_responsive = avg_drag_time < 10.0  # < 10ms
            
            results[dataset_name] = {
                "point_count": len(data),
                "avg_selection_time_ms": round(avg_selection_time, 3),
                "max_selection_time_ms": round(max_selection_time, 3),
                "avg_drag_time_ms": round(avg_drag_time, 3),
                "max_drag_time_ms": round(max_drag_time, 3),
                "selection_responsive": selection_responsive,
                "drag_responsive": drag_responsive,
                "interaction_rating": "EXCELLENT" if selection_responsive and drag_responsive else "GOOD" if selection_responsive else "POOR"
            }
            
            logger.info(f"  Selection: {avg_selection_time:.3f}ms avg, {max_selection_time:.3f}ms max")
            logger.info(f"  Drag: {avg_drag_time:.3f}ms avg, {max_drag_time:.3f}ms max")
        
        self.results["interaction_responsiveness"] = results
        return results
    
    def test_data_operations(self):
        """Test 4: Data Operations Performance"""
        logger.info("=" * 60)
        logger.info("TESTING DATA OPERATIONS")
        logger.info("=" * 60)
        
        results = {}
        
        test_datasets = {
            "small_100": self._generate_smooth_curve(100),
            "medium_1000": self._generate_smooth_curve(1000),
            "large_10000": self._generate_smooth_curve(10000),
        }
        
        for dataset_name, data in test_datasets.items():
            logger.info(f"Testing data operations with {dataset_name} ({len(data)} points)")
            
            # Test data loading performance
            load_times = []
            for i in range(10):
                self.curve_widget.set_curve_data([])  # Clear first
                
                start_time = time.perf_counter()
                self.curve_widget.set_curve_data(data)
                load_time = (time.perf_counter() - start_time) * 1000.0
                load_times.append(load_time)
                
                self.app.processEvents()
            
            # Test coordinate transformation performance
            transform_times = []
            if data:
                for i in range(1000):  # Many transform tests
                    point = random.choice(data)
                    
                    start_time = time.perf_counter()
                    screen_pos = self.curve_widget.data_to_screen(point[1], point[2])
                    data_pos = self.curve_widget.screen_to_data(screen_pos)
                    transform_time = (time.perf_counter() - start_time) * 1000.0
                    transform_times.append(transform_time)
            
            # Test cache update performance
            cache_times = []
            for i in range(20):
                start_time = time.perf_counter()
                self.curve_widget._invalidate_caches()
                self.curve_widget._update_screen_points_cache()
                cache_time = (time.perf_counter() - start_time) * 1000.0
                cache_times.append(cache_time)
            
            # Calculate statistics
            avg_load_time = sum(load_times) / len(load_times)
            avg_transform_time = sum(transform_times) / len(transform_times) if transform_times else 0
            avg_cache_time = sum(cache_times) / len(cache_times)
            
            results[dataset_name] = {
                "point_count": len(data),
                "avg_load_time_ms": round(avg_load_time, 2),
                "max_load_time_ms": round(max(load_times), 2),
                "avg_transform_time_ms": round(avg_transform_time, 4),
                "max_transform_time_ms": round(max(transform_times), 4) if transform_times else 0,
                "avg_cache_time_ms": round(avg_cache_time, 2),
                "max_cache_time_ms": round(max(cache_times), 2),
                "load_efficient": avg_load_time < 50.0,
                "transform_efficient": avg_transform_time < 0.1,
                "cache_efficient": avg_cache_time < 100.0
            }
            
            logger.info(f"  Load: {avg_load_time:.2f}ms avg")
            logger.info(f"  Transform: {avg_transform_time:.4f}ms avg")
            logger.info(f"  Cache: {avg_cache_time:.2f}ms avg")
        
        self.results["data_operations"] = results
        return results
    
    def test_zoom_pan_performance(self):
        """Test 5: Zoom and Pan Operations"""
        logger.info("=" * 60)
        logger.info("TESTING ZOOM/PAN PERFORMANCE")
        logger.info("=" * 60)
        
        results = {}
        
        test_datasets = {
            "medium_1000": self._generate_smooth_curve(1000),
            "large_10000": self._generate_smooth_curve(10000),
        }
        
        for dataset_name, data in test_datasets.items():
            logger.info(f"Testing zoom/pan with {dataset_name} ({len(data)} points)")
            
            # Load test data
            self.curve_widget.set_curve_data(data)
            self.app.processEvents()
            
            # Store original state
            original_zoom = self.curve_widget.zoom_factor
            original_pan_x = self.curve_widget.pan_offset_x
            original_pan_y = self.curve_widget.pan_offset_y
            
            # Test zoom performance
            zoom_times = []
            zoom_levels = [0.1, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
            
            for zoom in zoom_levels:
                start_time = time.perf_counter()
                
                self.curve_widget.zoom_factor = zoom
                self.curve_widget._invalidate_caches()
                self.curve_widget.update()
                self.app.processEvents()
                
                zoom_time = (time.perf_counter() - start_time) * 1000.0
                zoom_times.append(zoom_time)
            
            # Test pan performance
            pan_times = []
            pan_offsets = [(-100, -100), (0, -100), (100, -100), 
                          (-100, 0), (0, 0), (100, 0),
                          (-100, 100), (0, 100), (100, 100)]
            
            for pan_x, pan_y in pan_offsets:
                start_time = time.perf_counter()
                
                self.curve_widget.pan_offset_x = pan_x
                self.curve_widget.pan_offset_y = pan_y
                self.curve_widget._invalidate_caches()
                self.curve_widget.update()
                self.app.processEvents()
                
                pan_time = (time.perf_counter() - start_time) * 1000.0
                pan_times.append(pan_time)
            
            # Restore original state
            self.curve_widget.zoom_factor = original_zoom
            self.curve_widget.pan_offset_x = original_pan_x
            self.curve_widget.pan_offset_y = original_pan_y
            self.curve_widget._invalidate_caches()
            
            # Calculate statistics
            avg_zoom_time = sum(zoom_times) / len(zoom_times)
            avg_pan_time = sum(pan_times) / len(pan_times)
            
            results[dataset_name] = {
                "point_count": len(data),
                "avg_zoom_time_ms": round(avg_zoom_time, 2),
                "max_zoom_time_ms": round(max(zoom_times), 2),
                "avg_pan_time_ms": round(avg_pan_time, 2),
                "max_pan_time_ms": round(max(pan_times), 2),
                "zoom_responsive": avg_zoom_time < 50.0,
                "pan_responsive": avg_pan_time < 50.0,
                "zoom_levels_tested": zoom_levels,
                "zoom_times": [round(t, 2) for t in zoom_times],
                "pan_times": [round(t, 2) for t in pan_times]
            }
            
            logger.info(f"  Zoom: {avg_zoom_time:.2f}ms avg ({max(zoom_times):.2f}ms max)")
            logger.info(f"  Pan: {avg_pan_time:.2f}ms avg ({max(pan_times):.2f}ms max)")
        
        self.results["zoom_pan_performance"] = results
        return results
    
    def generate_optimization_recommendations(self):
        """Generate specific optimization recommendations."""
        logger.info("=" * 60)
        logger.info("GENERATING OPTIMIZATION RECOMMENDATIONS")
        logger.info("=" * 60)
        
        recommendations = []
        
        # Analyze rendering performance
        if "rendering_performance" in self.results:
            poor_fps_datasets = [
                (name, data) for name, data in self.results["rendering_performance"].items()
                if not data["meets_30fps_target"]
            ]
            
            if poor_fps_datasets:
                recommendations.append({
                    "category": "CRITICAL - Rendering Performance",
                    "issue": f"Poor FPS detected on {len(poor_fps_datasets)} dataset(s)",
                    "recommendations": [
                        "Implement viewport culling to skip rendering off-screen points",
                        "Add level-of-detail (LOD) system for distant/small points", 
                        "Cache screen coordinates and invalidate only when transform changes",
                        "Consider using QOpenGLWidget for GPU-accelerated rendering",
                        "Implement point clustering for dense datasets"
                    ]
                })
        
        # Analyze memory usage
        if "memory_usage" in self.results:
            memory_issues = [
                (name, data) for name, data in self.results["memory_usage"].items()
                if data["potential_leak_detected"] or data["memory_per_point_kb"] > 1.0
            ]
            
            if memory_issues:
                recommendations.append({
                    "category": "WARNING - Memory Efficiency", 
                    "issue": f"Memory issues detected on {len(memory_issues)} dataset(s)",
                    "recommendations": [
                        "Implement periodic cache clearing to prevent memory accumulation",
                        "Use object pooling for frequently allocated/deallocated objects",
                        "Optimize data structures - consider using numpy arrays for coordinates",
                        "Implement lazy loading for point metadata (status, labels)",
                        "Add memory usage monitoring and automatic cleanup thresholds"
                    ]
                })
        
        # Analyze interaction responsiveness
        if "interaction_responsiveness" in self.results:
            slow_interactions = [
                (name, data) for name, data in self.results["interaction_responsiveness"].items()
                if not data["selection_responsive"] or not data["drag_responsive"]
            ]
            
            if slow_interactions:
                recommendations.append({
                    "category": "WARNING - Interaction Performance",
                    "issue": f"Slow interactions detected on {len(slow_interactions)} dataset(s)",
                    "recommendations": [
                        "Implement spatial indexing (QuadTree/KD-Tree) for fast point lookup",
                        "Use progressive selection updates for large datasets",
                        "Defer expensive operations until mouse release events",
                        "Implement mouse interaction throttling/debouncing",
                        "Cache frequently accessed point data structures"
                    ]
                })
        
        # General architectural recommendations
        recommendations.append({
            "category": "ENHANCEMENT - Architecture",
            "issue": "General optimization opportunities",
            "recommendations": [
                "Consider implementing multi-threaded rendering pipeline",
                "Add progressive loading system for very large datasets",
                "Implement smart caching with LRU eviction policy",
                "Add performance monitoring dashboard for end users",
                "Consider WebGL/OpenGL rendering for ultimate performance"
            ]
        })
        
        self.results["optimization_recommendations"] = recommendations
        return recommendations
    
    def generate_comprehensive_report(self):
        """Generate the final comprehensive performance report."""
        total_time = time.time() - self.start_time
        
        report = []
        report.append("=" * 80)
        report.append("CURVEEDITOR COMPREHENSIVE PERFORMANCE ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Analysis completed: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total analysis time: {total_time:.1f} seconds")
        report.append("")
        
        # Executive Summary
        report.append("EXECUTIVE SUMMARY")
        report.append("-" * 40)
        
        summary_items = []
        
        # Rendering summary
        if "rendering_performance" in self.results:
            good_fps_count = sum(1 for data in self.results["rendering_performance"].values() 
                               if data["meets_60fps_target"])
            total_datasets = len(self.results["rendering_performance"])
            summary_items.append(f"Rendering: {good_fps_count}/{total_datasets} datasets meet 60 FPS target")
        
        # Memory summary  
        if "memory_usage" in self.results:
            leak_count = sum(1 for data in self.results["memory_usage"].values() 
                           if data["potential_leak_detected"])
            total_datasets = len(self.results["memory_usage"])
            summary_items.append(f"Memory: {leak_count}/{total_datasets} datasets show potential leaks")
        
        for item in summary_items:
            report.append(f"• {item}")
        
        report.append("")
        
        # Detailed Results
        for section_name, section_data in self.results.items():
            if section_name == "optimization_recommendations":
                continue  # Handle separately
                
            report.append(f"{section_name.upper().replace('_', ' ')}")
            report.append("-" * 50)
            
            if isinstance(section_data, dict):
                for dataset_name, dataset_results in section_data.items():
                    report.append(f"\n{dataset_name.upper()}:")
                    
                    # Format results nicely
                    for key, value in dataset_results.items():
                        if isinstance(value, (int, float)):
                            if "time" in key.lower() and "ms" not in str(value):
                                report.append(f"  {key}: {value:.3f}")
                            else:
                                report.append(f"  {key}: {value}")
                        elif isinstance(value, bool):
                            status = "✅ YES" if value else "❌ NO"  
                            report.append(f"  {key}: {status}")
                        elif isinstance(value, str):
                            report.append(f"  {key}: {value}")
                        elif isinstance(value, list) and len(value) <= 10:
                            report.append(f"  {key}: {value}")
            
            report.append("")
        
        # Optimization Recommendations
        if "optimization_recommendations" in self.results:
            report.append("OPTIMIZATION RECOMMENDATIONS")
            report.append("-" * 50)
            
            for rec in self.results["optimization_recommendations"]:
                report.append(f"\n{rec['category']}")
                report.append(f"Issue: {rec['issue']}")
                report.append("Recommended actions:")
                for action in rec['recommendations']:
                    report.append(f"  • {action}")
        
        return "\n".join(report)
    
    def _generate_smooth_curve(self, point_count: int):
        """Generate a smooth curve for testing."""
        data = []
        for i in range(point_count):
            frame = i
            t = i / point_count * 4 * math.pi
            x = 100 + (1820 * i / point_count)  # Spread across screen width
            y = 540 + 200 * math.sin(t)  # Sine wave
            status = "tracked" if i % 10 != 0 else "keyframe"
            data.append((frame, x, y, status))
        return data
    
    def _generate_dense_cluster(self, point_count: int):
        """Generate a dense cluster of points for testing."""
        import random
        data = []
        center_x, center_y = 960, 540
        
        for i in range(point_count):
            # Most points clustered near center
            if random.random() < 0.8:
                radius = random.uniform(0, 50)
                angle = random.uniform(0, 2 * math.pi)
                x = center_x + radius * math.cos(angle)
                y = center_y + radius * math.sin(angle)
            else:
                # Some scattered outliers
                x = random.uniform(100, 1820)
                y = random.uniform(100, 980)
            
            status = random.choice(["tracked", "keyframe", "interpolated"])
            data.append((i, x, y, status))
        
        return data
    
    def save_results(self, filename: str):
        """Save results to JSON file."""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2, default=str)
        
        logger.info(f"Results saved to {filename}")
    
    def cleanup(self):
        """Clean up resources."""
        if self.profiler:
            self.profiler.stop_monitoring()
        
        if self.main_window:
            self.main_window.close()


def main():
    """Run the comprehensive performance analysis."""
    logger.info("Starting CurveEditor Performance Analysis")
    
    # Create analyzer
    analyzer = CurveEditorPerformanceAnalyzer()
    
    try:
        # Setup application
        if not analyzer.setup_application():
            logger.error("Failed to setup application")
            return
        
        # Run all performance tests
        logger.info("Running comprehensive performance test suite...")
        
        # Test 1: Rendering Performance
        analyzer.test_rendering_performance()
        
        # Test 2: Memory Usage  
        analyzer.test_memory_usage()
        
        # Test 3: Interaction Responsiveness
        analyzer.test_interaction_responsiveness()
        
        # Test 4: Data Operations
        analyzer.test_data_operations()
        
        # Test 5: Zoom/Pan Performance
        analyzer.test_zoom_pan_performance()
        
        # Generate optimization recommendations
        analyzer.generate_optimization_recommendations()
        
        # Generate comprehensive report
        report = analyzer.generate_comprehensive_report()
        
        # Save results
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        # Save JSON results
        json_filename = f"performance_analysis_{timestamp}.json"
        analyzer.save_results(json_filename)
        
        # Save text report
        report_filename = f"performance_report_{timestamp}.txt"
        with open(report_filename, 'w') as f:
            f.write(report)
        
        # Print report to console
        print("\n")
        print(report)
        
        print(f"\nAnalysis complete!")
        print(f"Detailed results: {json_filename}")
        print(f"Summary report: {report_filename}")
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Cleanup
        analyzer.cleanup()


if __name__ == "__main__":
    main()
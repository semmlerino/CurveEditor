#!/usr/bin/env python
"""
Comprehensive Performance Profiler for CurveEditor Application.

This module provides detailed profiling capabilities for the CurveViewWidget
and related rendering systems, focusing on CPU, memory, and I/O performance.

Key Features:
    - Paint event profiling with timing analysis
    - Memory usage tracking with leak detection
    - Mouse interaction responsiveness measurement
    - Data operation performance analysis
    - Service call overhead measurement
    - Optimization recommendations
"""

import cProfile
import gc
import io
import logging
import math
import os
import psutil
import pstats
import statistics
import sys
import time
import tracemalloc
from collections import defaultdict, deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple

from PySide6.QtCore import QElapsedTimer, QObject, QTimer, Signal, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

# Profile data classes
@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    name: str
    total_time: float = 0.0
    call_count: int = 0
    min_time: float = float('inf')
    max_time: float = 0.0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=100))
    memory_usage: List[float] = field(default_factory=list)
    
    @property
    def avg_time(self) -> float:
        """Average execution time."""
        return self.total_time / max(1, self.call_count)
    
    @property
    def recent_avg(self) -> float:
        """Average of recent calls."""
        return statistics.mean(self.recent_times) if self.recent_times else 0.0
    
    @property
    def fps_estimate(self) -> float:
        """Estimated FPS if this is a paint operation."""
        if self.recent_avg > 0:
            return 1000.0 / self.recent_avg  # Convert ms to FPS
        return 0.0


@dataclass
class MemorySnapshot:
    """Memory usage snapshot."""
    timestamp: float
    rss_mb: float  # Resident set size
    vms_mb: float  # Virtual memory size
    heap_mb: float  # Python heap size
    objects_count: int
    tracemalloc_top: List[Tuple[str, int]] = field(default_factory=list)


class PerformanceProfiler(QObject):
    """
    Advanced performance profiler for CurveEditor application.
    
    Provides comprehensive profiling including:
    - Paint event timing with frame rate analysis
    - Memory usage tracking and leak detection
    - Mouse interaction responsiveness
    - Data operation performance
    - Service call overhead analysis
    """
    
    # Signals for real-time monitoring
    paint_time_measured = Signal(float)  # Paint time in ms
    memory_usage_updated = Signal(float, float)  # RSS MB, VMS MB
    performance_warning = Signal(str, float)  # Warning message, metric value
    
    def __init__(self):
        super().__init__()
        self.metrics: Dict[str, PerformanceMetrics] = {}
        self.memory_snapshots: List[MemorySnapshot] = []
        self.process = psutil.Process()
        self.start_time = time.time()
        
        # Profiling state
        self.profiling_enabled = True
        self.memory_tracking_enabled = True
        self.detailed_memory_tracking = False
        
        # Performance thresholds
        self.paint_time_warning_ms = 16.67  # 60 FPS threshold
        self.memory_growth_warning_mb = 50.0  # Memory growth warning
        self.interaction_delay_warning_ms = 100.0  # UI responsiveness
        
        # Setup timers for periodic monitoring
        self.memory_timer = QTimer()
        self.memory_timer.timeout.connect(self._collect_memory_sample)
        
        # Initialize tracemalloc if detailed tracking enabled
        if self.detailed_memory_tracking:
            tracemalloc.start(10)
            logging.info("Detailed memory tracking enabled with tracemalloc")
        
        logging.info("Performance profiler initialized")
    
    def enable_profiling(self, enabled: bool = True) -> None:
        """Enable or disable performance profiling."""
        self.profiling_enabled = enabled
        if enabled:
            self.start_monitoring()
        else:
            self.stop_monitoring()
        
        logging.info(f"Performance profiling {'enabled' if enabled else 'disabled'}")
    
    def start_monitoring(self) -> None:
        """Start continuous performance monitoring."""
        if not self.profiling_enabled:
            return
            
        # Start memory monitoring every 5 seconds
        self.memory_timer.start(5000)
        self._collect_memory_sample()  # Initial sample
        
        logging.info("Performance monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop continuous monitoring."""
        self.memory_timer.stop()
        logging.info("Performance monitoring stopped")
    
    @contextmanager
    def profile_operation(self, operation_name: str):
        """Context manager for profiling any operation."""
        if not self.profiling_enabled:
            yield
            return
        
        start_time = time.perf_counter()
        start_memory = None
        
        if self.memory_tracking_enabled:
            start_memory = self.process.memory_info().rss / 1024 / 1024
        
        try:
            yield
        finally:
            end_time = time.perf_counter()
            elapsed_ms = (end_time - start_time) * 1000.0
            
            # Update metrics
            if operation_name not in self.metrics:
                self.metrics[operation_name] = PerformanceMetrics(operation_name)
            
            metric = self.metrics[operation_name]
            metric.total_time += elapsed_ms
            metric.call_count += 1
            metric.min_time = min(metric.min_time, elapsed_ms)
            metric.max_time = max(metric.max_time, elapsed_ms)
            metric.recent_times.append(elapsed_ms)
            
            if self.memory_tracking_enabled and start_memory is not None:
                end_memory = self.process.memory_info().rss / 1024 / 1024
                metric.memory_usage.append(end_memory - start_memory)
            
            # Check thresholds and emit warnings
            self._check_performance_thresholds(operation_name, elapsed_ms)
    
    def profile_paint_event(self) -> Callable:
        """Decorator for profiling paint events specifically."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.profiling_enabled:
                    return func(*args, **kwargs)
                
                with self.profile_operation(f"paint_event_{func.__name__}"):
                    result = func(*args, **kwargs)
                
                # Emit paint-specific signal
                paint_metric = self.metrics.get(f"paint_event_{func.__name__}")
                if paint_metric and paint_metric.recent_times:
                    recent_time = paint_metric.recent_times[-1]
                    self.paint_time_measured.emit(recent_time)
                
                return result
            return wrapper
        return decorator
    
    def profile_mouse_event(self) -> Callable:
        """Decorator for profiling mouse interaction events."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.profiling_enabled:
                    return func(*args, **kwargs)
                
                with self.profile_operation(f"mouse_event_{func.__name__}"):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def profile_data_operation(self) -> Callable:
        """Decorator for profiling data operations (file I/O, processing)."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.profiling_enabled:
                    return func(*args, **kwargs)
                
                with self.profile_operation(f"data_op_{func.__name__}"):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def profile_service_call(self) -> Callable:
        """Decorator for profiling service method calls."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.profiling_enabled:
                    return func(*args, **kwargs)
                
                with self.profile_operation(f"service_{func.__name__}"):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    @Slot()
    def _collect_memory_sample(self) -> None:
        """Collect memory usage sample."""
        if not self.memory_tracking_enabled:
            return
        
        try:
            # Get process memory info
            memory_info = self.process.memory_info()
            rss_mb = memory_info.rss / 1024 / 1024
            vms_mb = memory_info.vms / 1024 / 1024
            
            # Get Python object count
            objects_count = len(gc.get_objects())
            
            # Get heap size estimate
            heap_mb = sys.getsizeof(gc.get_objects()) / 1024 / 1024
            
            # Collect tracemalloc info if available
            tracemalloc_top = []
            if self.detailed_memory_tracking and tracemalloc.is_tracing():
                snapshot = tracemalloc.take_snapshot()
                top_stats = snapshot.statistics('lineno')[:10]
                tracemalloc_top = [(str(stat.traceback), stat.size // 1024) 
                                  for stat in top_stats]
            
            # Create snapshot
            snapshot = MemorySnapshot(
                timestamp=time.time(),
                rss_mb=rss_mb,
                vms_mb=vms_mb,
                heap_mb=heap_mb,
                objects_count=objects_count,
                tracemalloc_top=tracemalloc_top
            )
            
            self.memory_snapshots.append(snapshot)
            
            # Keep only recent samples (last hour at 5-second intervals = 720 samples)
            if len(self.memory_snapshots) > 720:
                self.memory_snapshots = self.memory_snapshots[-720:]
            
            # Emit signal for real-time monitoring
            self.memory_usage_updated.emit(rss_mb, vms_mb)
            
            # Check for memory growth warnings
            if len(self.memory_snapshots) >= 2:
                growth = rss_mb - self.memory_snapshots[0].rss_mb
                if growth > self.memory_growth_warning_mb:
                    self.performance_warning.emit(
                        f"Memory growth: {growth:.1f} MB since start", growth
                    )
        
        except Exception as e:
            logging.warning(f"Failed to collect memory sample: {e}")
    
    def _check_performance_thresholds(self, operation_name: str, elapsed_ms: float) -> None:
        """Check performance thresholds and emit warnings."""
        # Paint event threshold
        if "paint_event" in operation_name and elapsed_ms > self.paint_time_warning_ms:
            self.performance_warning.emit(
                f"Slow paint event: {operation_name} took {elapsed_ms:.1f}ms "
                f"(>{self.paint_time_warning_ms:.1f}ms threshold)",
                elapsed_ms
            )
        
        # Mouse interaction threshold
        elif "mouse_event" in operation_name and elapsed_ms > self.interaction_delay_warning_ms:
            self.performance_warning.emit(
                f"Slow interaction: {operation_name} took {elapsed_ms:.1f}ms "
                f"(>{self.interaction_delay_warning_ms:.1f}ms threshold)",
                elapsed_ms
            )
    
    def generate_performance_report(self) -> str:
        """Generate comprehensive performance report."""
        report = []
        report.append("=" * 80)
        report.append("CURVEEDITOR PERFORMANCE ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Report generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Profiling duration: {time.time() - self.start_time:.1f} seconds")
        report.append("")
        
        # Overall metrics summary
        if self.metrics:
            report.append("PERFORMANCE METRICS SUMMARY")
            report.append("-" * 40)
            
            # Sort by average time (slowest first)
            sorted_metrics = sorted(
                self.metrics.values(), 
                key=lambda m: m.avg_time, 
                reverse=True
            )
            
            for metric in sorted_metrics[:10]:  # Top 10 slowest operations
                fps = f" ({metric.fps_estimate:.1f} FPS)" if "paint" in metric.name else ""
                report.append(
                    f"{metric.name:30s}: "
                    f"avg={metric.avg_time:6.2f}ms, "
                    f"calls={metric.call_count:5d}, "
                    f"min={metric.min_time:6.2f}ms, "
                    f"max={metric.max_time:6.2f}ms{fps}"
                )
            
            report.append("")
        
        # Paint event analysis
        paint_metrics = {name: metric for name, metric in self.metrics.items() 
                        if "paint_event" in name}
        
        if paint_metrics:
            report.append("RENDERING PERFORMANCE ANALYSIS")
            report.append("-" * 40)
            
            for name, metric in paint_metrics.items():
                fps = metric.fps_estimate
                fps_status = "EXCELLENT" if fps >= 60 else "GOOD" if fps >= 30 else "POOR"
                
                report.append(f"{name}:")
                report.append(f"  Average frame time: {metric.avg_time:.2f}ms")
                report.append(f"  Estimated FPS: {fps:.1f} ({fps_status})")
                report.append(f"  Frame time range: {metric.min_time:.2f}ms - {metric.max_time:.2f}ms")
                
                if metric.recent_times:
                    recent_fps = 1000.0 / statistics.mean(metric.recent_times)
                    report.append(f"  Recent FPS: {recent_fps:.1f}")
                
                report.append("")
        
        # Mouse interaction analysis
        mouse_metrics = {name: metric for name, metric in self.metrics.items() 
                        if "mouse_event" in name}
        
        if mouse_metrics:
            report.append("INTERACTION RESPONSIVENESS ANALYSIS")
            report.append("-" * 40)
            
            for name, metric in mouse_metrics.items():
                responsiveness = "EXCELLENT" if metric.avg_time < 10 else \
                               "GOOD" if metric.avg_time < 50 else "POOR"
                
                report.append(f"{name}: {metric.avg_time:.2f}ms avg ({responsiveness})")
        
        # Memory analysis
        if self.memory_snapshots:
            report.append("MEMORY USAGE ANALYSIS")
            report.append("-" * 40)
            
            first_snapshot = self.memory_snapshots[0]
            last_snapshot = self.memory_snapshots[-1]
            
            rss_growth = last_snapshot.rss_mb - first_snapshot.rss_mb
            vms_growth = last_snapshot.vms_mb - first_snapshot.vms_mb
            
            report.append(f"Initial memory (RSS): {first_snapshot.rss_mb:.1f} MB")
            report.append(f"Current memory (RSS): {last_snapshot.rss_mb:.1f} MB")
            report.append(f"Memory growth: {rss_growth:+.1f} MB")
            report.append(f"Virtual memory growth: {vms_growth:+.1f} MB")
            report.append(f"Python objects: {last_snapshot.objects_count:,}")
            report.append("")
            
            # Memory growth analysis
            if len(self.memory_snapshots) >= 10:
                recent_snapshots = self.memory_snapshots[-10:]
                growth_rates = []
                for i in range(1, len(recent_snapshots)):
                    time_diff = recent_snapshots[i].timestamp - recent_snapshots[i-1].timestamp
                    mem_diff = recent_snapshots[i].rss_mb - recent_snapshots[i-1].rss_mb
                    if time_diff > 0:
                        growth_rates.append(mem_diff / time_diff)  # MB/second
                
                if growth_rates:
                    avg_growth_rate = statistics.mean(growth_rates)
                    report.append(f"Recent memory growth rate: {avg_growth_rate:.3f} MB/sec")
                    
                    if avg_growth_rate > 0.1:  # Growing > 0.1 MB/sec
                        report.append("WARNING: Potential memory leak detected!")
                    report.append("")
        
        # Data operation analysis
        data_metrics = {name: metric for name, metric in self.metrics.items() 
                       if "data_op" in name}
        
        if data_metrics:
            report.append("DATA OPERATION PERFORMANCE")
            report.append("-" * 40)
            
            for name, metric in data_metrics.items():
                report.append(f"{name}: {metric.avg_time:.2f}ms avg, {metric.call_count} calls")
        
        # Service call analysis
        service_metrics = {name: metric for name, metric in self.metrics.items() 
                          if "service" in name}
        
        if service_metrics:
            report.append("SERVICE CALL OVERHEAD")
            report.append("-" * 40)
            
            total_service_time = sum(m.total_time for m in service_metrics.values())
            
            for name, metric in service_metrics.items():
                percentage = (metric.total_time / total_service_time) * 100 if total_service_time > 0 else 0
                report.append(f"{name}: {metric.avg_time:.2f}ms avg ({percentage:.1f}% of total)")
        
        # Generate optimization recommendations
        report.append("")
        report.extend(self._generate_optimization_recommendations())
        
        return "\n".join(report)
    
    def _generate_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on profiling data."""
        recommendations = []
        recommendations.append("OPTIMIZATION RECOMMENDATIONS")
        recommendations.append("-" * 40)
        
        # Check paint performance
        paint_metrics = {name: metric for name, metric in self.metrics.items() 
                        if "paint_event" in name}
        
        for name, metric in paint_metrics.items():
            if metric.avg_time > self.paint_time_warning_ms:
                recommendations.append(
                    f"🔴 CRITICAL: {name} averaging {metric.avg_time:.1f}ms "
                    f"(target: <{self.paint_time_warning_ms:.1f}ms)"
                )
                recommendations.append("   Recommendations:")
                recommendations.append("   - Implement viewport culling for off-screen points")
                recommendations.append("   - Cache screen coordinates between frames")
                recommendations.append("   - Use level-of-detail for distant points")
                recommendations.append("   - Consider using QOpenGLWidget for GPU acceleration")
                recommendations.append("")
        
        # Check memory growth
        if self.memory_snapshots and len(self.memory_snapshots) >= 2:
            growth = (self.memory_snapshots[-1].rss_mb - 
                     self.memory_snapshots[0].rss_mb)
            
            if growth > self.memory_growth_warning_mb:
                recommendations.append(f"🟡 WARNING: Memory grew {growth:.1f} MB")
                recommendations.append("   Recommendations:")
                recommendations.append("   - Clear caches periodically")
                recommendations.append("   - Implement object pooling for frequent allocations")
                recommendations.append("   - Check for circular references in data structures")
                recommendations.append("   - Use weak references for temporary connections")
                recommendations.append("")
        
        # Check interaction responsiveness
        mouse_metrics = {name: metric for name, metric in self.metrics.items() 
                        if "mouse_event" in name}
        
        slow_interactions = [
            (name, metric) for name, metric in mouse_metrics.items()
            if metric.avg_time > self.interaction_delay_warning_ms
        ]
        
        if slow_interactions:
            recommendations.append("🟡 WARNING: Slow mouse interactions detected")
            recommendations.append("   Recommendations:")
            recommendations.append("   - Defer expensive operations until mouse release")
            recommendations.append("   - Use QTimer.singleShot for delayed updates")
            recommendations.append("   - Implement progressive updates for large datasets")
            recommendations.append("")
        
        # Service overhead analysis
        service_metrics = {name: metric for name, metric in self.metrics.items() 
                          if "service" in name}
        
        if service_metrics:
            total_service_time = sum(m.total_time for m in service_metrics.values())
            avg_service_time = total_service_time / sum(m.call_count for m in service_metrics.values())
            
            if avg_service_time > 1.0:  # > 1ms average
                recommendations.append("🟡 NOTICE: High service call overhead detected")
                recommendations.append("   Recommendations:")
                recommendations.append("   - Batch service calls where possible")
                recommendations.append("   - Cache frequently accessed data")
                recommendations.append("   - Consider direct method calls for hot paths")
                recommendations.append("")
        
        if not any("🔴" in r or "🟡" in r for r in recommendations[2:]):
            recommendations.append("✅ Performance looks good! No critical issues detected.")
        
        return recommendations
    
    def generate_detailed_memory_report(self) -> str:
        """Generate detailed memory usage report with tracemalloc data."""
        if not self.detailed_memory_tracking or not tracemalloc.is_tracing():
            return "Detailed memory tracking not enabled. Call profiler.detailed_memory_tracking = True"
        
        report = []
        report.append("DETAILED MEMORY ALLOCATION REPORT")
        report.append("=" * 50)
        
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        
        report.append("TOP MEMORY ALLOCATIONS:")
        for index, stat in enumerate(top_stats[:20], 1):
            report.append(f"{index:2d}. {stat}")
        
        return "\n".join(report)
    
    def export_metrics_csv(self, filename: str) -> None:
        """Export performance metrics to CSV file."""
        import csv
        
        with open(filename, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow([
                'Operation', 'Total_Time_ms', 'Call_Count', 'Avg_Time_ms',
                'Min_Time_ms', 'Max_Time_ms', 'Recent_Avg_ms', 'Estimated_FPS'
            ])
            
            # Write metrics data
            for metric in self.metrics.values():
                writer.writerow([
                    metric.name,
                    f"{metric.total_time:.3f}",
                    metric.call_count,
                    f"{metric.avg_time:.3f}",
                    f"{metric.min_time:.3f}",
                    f"{metric.max_time:.3f}",
                    f"{metric.recent_avg:.3f}",
                    f"{metric.fps_estimate:.1f}"
                ])
        
        logging.info(f"Performance metrics exported to {filename}")
    
    def run_cpu_profile(self, duration_seconds: int = 30) -> str:
        """Run detailed CPU profiling for specified duration."""
        profiler = cProfile.Profile()
        
        logging.info(f"Starting CPU profiling for {duration_seconds} seconds...")
        
        profiler.enable()
        
        # Let the profiler run
        start_time = time.time()
        while time.time() - start_time < duration_seconds:
            QApplication.processEvents()
            time.sleep(0.01)
        
        profiler.disable()
        
        # Analyze results
        s = io.StringIO()
        stats = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
        stats.print_stats(50)  # Top 50 functions
        
        return s.getvalue()


# Convenience functions for easy integration

def create_performance_profiler() -> PerformanceProfiler:
    """Create and configure a performance profiler instance."""
    profiler = PerformanceProfiler()
    profiler.detailed_memory_tracking = True
    return profiler


def profile_curve_view_widget(curve_widget) -> PerformanceProfiler:
    """Apply performance profiling to a CurveViewWidget instance."""
    profiler = create_performance_profiler()
    
    # Wrap paint event
    original_paint_event = curve_widget.paintEvent
    @profiler.profile_paint_event()
    def profiled_paint_event(event):
        return original_paint_event(event)
    curve_widget.paintEvent = profiled_paint_event
    
    # Wrap mouse events
    for event_method in ['mousePressEvent', 'mouseMoveEvent', 'mouseReleaseEvent']:
        if hasattr(curve_widget, event_method):
            original_method = getattr(curve_widget, event_method)
            profiled_method = profiler.profile_mouse_event()(original_method)
            setattr(curve_widget, event_method, profiled_method)
    
    # Start monitoring
    profiler.start_monitoring()
    
    return profiler


# Example usage and testing
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
    
    # Create application
    app = QApplication(sys.argv)
    
    # Create profiler
    profiler = create_performance_profiler()
    
    # Test profiling functionality
    with profiler.profile_operation("test_operation"):
        time.sleep(0.01)  # Simulate work
    
    # Generate report
    report = profiler.generate_performance_report()
    print(report)
    
    app.quit()
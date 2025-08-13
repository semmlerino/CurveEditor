#!/usr/bin/env python3
"""
Performance profiler for CurveEditor application.
Identifies bottlenecks and generates optimization recommendations.
"""

import cProfile
import io
import pstats
import time
import tracemalloc
from pathlib import Path
from typing import Any, Callable

import psutil


class PerformanceProfiler:
    """Comprehensive performance profiling for CurveEditor."""

    def __init__(self):
        self.results = {}
        self.process = psutil.Process()

    def profile_startup(self) -> dict:
        """Profile application startup time."""
        print("Profiling application startup...")
        
        start_time = time.perf_counter()
        start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        
        try:
            # Import main components
            import_start = time.perf_counter()
            from services import (
                get_data_service,
                get_interaction_service,
                get_transform_service,
                get_ui_service,
            )
            import_time = time.perf_counter() - import_start
            
            # Initialize services
            init_start = time.perf_counter()
            data_service = get_data_service()
            transform_service = get_transform_service()
            interaction_service = get_interaction_service()
            ui_service = get_ui_service()
            init_time = time.perf_counter() - init_start
            
            # Create main window (without showing)
            window_start = time.perf_counter()
            from ui.main_window import MainWindow
            from PySide6.QtWidgets import QApplication
            import sys
            
            app = QApplication.instance()
            if not app:
                app = QApplication(sys.argv)
            
            window = MainWindow()
            window_time = time.perf_counter() - window_start
            
            total_time = time.perf_counter() - start_time
            end_memory = self.process.memory_info().rss / 1024 / 1024
            
            return {
                "total_time": total_time * 1000,  # ms
                "import_time": import_time * 1000,
                "service_init_time": init_time * 1000,
                "window_creation_time": window_time * 1000,
                "memory_used": end_memory - start_memory,
                "final_memory": end_memory,
            }
            
        except Exception as e:
            return {"error": str(e)}

    def profile_transforms(self, num_points: int = 1000) -> dict:
        """Profile coordinate transformation performance."""
        print(f"Profiling transform operations with {num_points} points...")
        
        from services import get_transform_service
        from services.transform_service import ViewState
        
        transform_service = get_transform_service()
        
        # Create test data
        test_points = [(i, float(i * 10), float(i * 20)) for i in range(num_points)]
        
        # Create view state
        view_state = ViewState(
            display_width=1920,
            display_height=1080,
            widget_width=1920,
            widget_height=1080,
            zoom_factor=2.0,
            offset_x=100,
            offset_y=50,
            flip_y_axis=False,
        )
        
        # Profile transform creation
        create_start = time.perf_counter()
        transform = transform_service.create_transform(view_state)
        create_time = time.perf_counter() - create_start
        
        # Profile data to screen transformations
        to_screen_start = time.perf_counter()
        screen_points = []
        for _, x, y in test_points:
            sx, sy = transform.data_to_screen(x, y)
            screen_points.append((sx, sy))
        to_screen_time = time.perf_counter() - to_screen_start
        
        # Profile screen to data transformations
        to_data_start = time.perf_counter()
        data_points = []
        for sx, sy in screen_points:
            dx, dy = transform.screen_to_data(sx, sy)
            data_points.append((dx, dy))
        to_data_time = time.perf_counter() - to_data_start
        
        return {
            "num_points": num_points,
            "transform_creation": create_time * 1000,
            "total_to_screen": to_screen_time * 1000,
            "per_point_to_screen": (to_screen_time / num_points) * 1000,
            "total_to_data": to_data_time * 1000,
            "per_point_to_data": (to_data_time / num_points) * 1000,
        }

    def profile_file_io(self) -> dict:
        """Profile file I/O operations."""
        print("Profiling file I/O operations...")
        
        import tempfile
        import json
        from services import get_data_service
        
        data_service = get_data_service()
        
        # Create test data of various sizes
        sizes = [100, 1000, 10000]
        results = {}
        
        for size in sizes:
            test_data = [
                (i, float(i * 10), float(i * 20), "keyframe" if i % 10 == 0 else "interpolated")
                for i in range(size)
            ]
            
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
                temp_path = f.name
            
            try:
                # Profile save
                save_start = time.perf_counter()
                data_service._save_json(temp_path, test_data, "Test", "#FF0000")
                save_time = time.perf_counter() - save_start
                
                # Get file size
                file_size = Path(temp_path).stat().st_size / 1024  # KB
                
                # Profile load
                load_start = time.perf_counter()
                loaded_data = data_service._load_json(temp_path)
                load_time = time.perf_counter() - load_start
                
                results[f"{size}_points"] = {
                    "save_time": save_time * 1000,
                    "load_time": load_time * 1000,
                    "file_size_kb": file_size,
                    "points_verified": len(loaded_data) == size,
                }
                
            finally:
                Path(temp_path).unlink(missing_ok=True)
        
        return results

    def profile_rendering(self) -> dict:
        """Profile rendering performance."""
        print("Profiling rendering performance...")
        
        try:
            from ui.curve_view_widget import CurveViewWidget
            from PySide6.QtWidgets import QApplication
            from PySide6.QtGui import QPainter, QPixmap
            import sys
            
            app = QApplication.instance()
            if not app:
                app = QApplication(sys.argv)
            
            # Create widget
            widget = CurveViewWidget()
            
            # Test with different data sizes
            sizes = [100, 500, 1000]
            results = {}
            
            for size in sizes:
                test_data = [
                    (i, float(i * 10), float(i * 20), "keyframe")
                    for i in range(size)
                ]
                
                widget.set_curve_data(test_data)
                
                # Create pixmap for offscreen rendering
                pixmap = QPixmap(1920, 1080)
                painter = QPainter(pixmap)
                
                # Time the paint event
                paint_start = time.perf_counter()
                widget.render(painter)
                paint_time = time.perf_counter() - paint_start
                
                painter.end()
                
                results[f"{size}_points"] = {
                    "render_time": paint_time * 1000,
                    "fps_potential": 1000 / (paint_time * 1000) if paint_time > 0 else float('inf'),
                }
            
            return results
            
        except Exception as e:
            return {"error": str(e)}

    def profile_memory(self) -> dict:
        """Profile memory usage patterns."""
        print("Profiling memory usage...")
        
        tracemalloc.start()
        
        # Create large dataset
        from services import get_data_service, get_interaction_service
        
        data_service = get_data_service()
        interaction_service = get_interaction_service()
        
        # Track memory for different operations
        results = {}
        
        # Baseline
        snapshot1 = tracemalloc.take_snapshot()
        
        # Create large dataset
        large_data = [
            (i, float(i * 10), float(i * 20), "keyframe")
            for i in range(10000)
        ]
        
        snapshot2 = tracemalloc.take_snapshot()
        
        # Calculate memory difference
        top_stats = snapshot2.compare_to(snapshot1, 'lineno')
        
        total_memory = sum(stat.size_diff for stat in top_stats) / 1024 / 1024  # MB
        
        # Get top memory consumers
        top_consumers = []
        for stat in top_stats[:10]:
            if stat.size_diff > 0:
                top_consumers.append({
                    "file": stat.traceback.format()[0] if stat.traceback else "unknown",
                    "size_mb": stat.size_diff / 1024 / 1024,
                })
        
        tracemalloc.stop()
        
        return {
            "large_dataset_memory": total_memory,
            "top_consumers": top_consumers,
            "process_memory": self.process.memory_info().rss / 1024 / 1024,
        }

    def run_cpu_profile(self, func: Callable, *args, **kwargs) -> tuple[Any, pstats.Stats]:
        """Run CPU profiling on a function."""
        profiler = cProfile.Profile()
        profiler.enable()
        
        result = func(*args, **kwargs)
        
        profiler.disable()
        
        # Get stats
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats(pstats.SortKey.CUMULATIVE)
        
        return result, stats

    def generate_report(self) -> str:
        """Generate comprehensive performance report."""
        report = []
        report.append("=" * 60)
        report.append("CURVEEDITOR PERFORMANCE PROFILE REPORT")
        report.append("=" * 60)
        report.append("")
        
        # Run all profiles
        startup = self.profile_startup()
        transforms = self.profile_transforms()
        file_io = self.profile_file_io()
        rendering = self.profile_rendering()
        memory = self.profile_memory()
        
        # Startup Performance
        report.append("## STARTUP PERFORMANCE")
        report.append("-" * 40)
        if "error" not in startup:
            report.append(f"Total Startup Time: {startup['total_time']:.2f}ms")
            report.append(f"  - Import Time: {startup['import_time']:.2f}ms")
            report.append(f"  - Service Init: {startup['service_init_time']:.2f}ms")
            report.append(f"  - Window Creation: {startup['window_creation_time']:.2f}ms")
            report.append(f"Memory Used: {startup['memory_used']:.2f}MB")
            report.append(f"Final Memory: {startup['final_memory']:.2f}MB")
            
            # Assessment
            if startup['total_time'] < 500:
                report.append("✅ Startup time is EXCELLENT (<500ms)")
            elif startup['total_time'] < 1000:
                report.append("⚠️ Startup time is ACCEPTABLE (500-1000ms)")
            else:
                report.append("❌ Startup time NEEDS OPTIMIZATION (>1000ms)")
        else:
            report.append(f"Error: {startup['error']}")
        report.append("")
        
        # Transform Performance
        report.append("## TRANSFORM PERFORMANCE")
        report.append("-" * 40)
        report.append(f"Points Tested: {transforms['num_points']}")
        report.append(f"Transform Creation: {transforms['transform_creation']:.3f}ms")
        report.append(f"Data→Screen Total: {transforms['total_to_screen']:.2f}ms")
        report.append(f"Data→Screen Per Point: {transforms['per_point_to_screen']:.4f}ms")
        report.append(f"Screen→Data Total: {transforms['total_to_data']:.2f}ms")
        report.append(f"Screen→Data Per Point: {transforms['per_point_to_data']:.4f}ms")
        
        # Assessment
        if transforms['total_to_screen'] < 10:
            report.append("✅ Transform performance is EXCELLENT (<10ms for 1000 points)")
        elif transforms['total_to_screen'] < 20:
            report.append("⚠️ Transform performance is ACCEPTABLE (10-20ms)")
        else:
            report.append("❌ Transform performance NEEDS OPTIMIZATION (>20ms)")
        report.append("")
        
        # File I/O Performance
        report.append("## FILE I/O PERFORMANCE")
        report.append("-" * 40)
        for size_key, metrics in file_io.items():
            points = size_key.split('_')[0]
            report.append(f"\n{points} Points:")
            report.append(f"  Save Time: {metrics['save_time']:.2f}ms")
            report.append(f"  Load Time: {metrics['load_time']:.2f}ms")
            report.append(f"  File Size: {metrics['file_size_kb']:.1f}KB")
            report.append(f"  Verified: {metrics['points_verified']}")
        
        # Assessment for 10k points
        if "10000_points" in file_io:
            load_time = file_io["10000_points"]["load_time"]
            if load_time < 1000:
                report.append("\n✅ File I/O is EXCELLENT (<1s for 10k points)")
            elif load_time < 2000:
                report.append("\n⚠️ File I/O is ACCEPTABLE (1-2s)")
            else:
                report.append("\n❌ File I/O NEEDS OPTIMIZATION (>2s)")
        report.append("")
        
        # Rendering Performance
        report.append("## RENDERING PERFORMANCE")
        report.append("-" * 40)
        if "error" not in rendering:
            for size_key, metrics in rendering.items():
                points = size_key.split('_')[0]
                report.append(f"\n{points} Points:")
                report.append(f"  Render Time: {metrics['render_time']:.2f}ms")
                report.append(f"  FPS Potential: {metrics['fps_potential']:.1f}")
            
            # Assessment for 1000 points
            if "1000_points" in rendering:
                fps = rendering["1000_points"]["fps_potential"]
                if fps >= 60:
                    report.append("\n✅ Rendering is EXCELLENT (60+ FPS)")
                elif fps >= 30:
                    report.append("\n⚠️ Rendering is ACCEPTABLE (30-60 FPS)")
                else:
                    report.append("\n❌ Rendering NEEDS OPTIMIZATION (<30 FPS)")
        else:
            report.append(f"Error: {rendering['error']}")
        report.append("")
        
        # Memory Usage
        report.append("## MEMORY USAGE")
        report.append("-" * 40)
        report.append(f"Large Dataset (10k points): {memory['large_dataset_memory']:.2f}MB")
        report.append(f"Process Total Memory: {memory['process_memory']:.2f}MB")
        
        if memory['top_consumers']:
            report.append("\nTop Memory Consumers:")
            for consumer in memory['top_consumers'][:5]:
                report.append(f"  {consumer['size_mb']:.2f}MB - {consumer['file']}")
        
        # Assessment
        if memory['process_memory'] < 100:
            report.append("\n✅ Memory usage is EXCELLENT (<100MB)")
        elif memory['process_memory'] < 200:
            report.append("\n⚠️ Memory usage is ACCEPTABLE (100-200MB)")
        else:
            report.append("\n❌ Memory usage NEEDS OPTIMIZATION (>200MB)")
        report.append("")
        
        # Bottlenecks and Recommendations
        report.append("## BOTTLENECK ANALYSIS")
        report.append("-" * 40)
        
        bottlenecks = []
        
        # Check each metric
        if "error" not in startup and startup['total_time'] > 1000:
            bottlenecks.append(("Startup", startup['total_time'], "ms"))
        
        if transforms['total_to_screen'] > 20:
            bottlenecks.append(("Transforms", transforms['total_to_screen'], "ms"))
        
        if "10000_points" in file_io and file_io["10000_points"]["load_time"] > 2000:
            bottlenecks.append(("File I/O", file_io["10000_points"]["load_time"], "ms"))
        
        if "1000_points" in rendering and rendering["1000_points"]["fps_potential"] < 30:
            bottlenecks.append(("Rendering", rendering["1000_points"]["render_time"], "ms"))
        
        if memory['process_memory'] > 200:
            bottlenecks.append(("Memory", memory['process_memory'], "MB"))
        
        if bottlenecks:
            report.append("Priority Optimization Targets:")
            for name, value, unit in sorted(bottlenecks, key=lambda x: x[1], reverse=True):
                report.append(f"  1. {name}: {value:.1f}{unit}")
        else:
            report.append("✅ No major bottlenecks detected!")
        
        report.append("")
        report.append("## OPTIMIZATION RECOMMENDATIONS")
        report.append("-" * 40)
        
        recommendations = []
        
        if "error" not in startup and startup['import_time'] > 200:
            recommendations.append("- Use lazy imports to reduce startup time")
        
        if transforms['per_point_to_screen'] > 0.01:
            recommendations.append("- Implement transform caching for repeated operations")
            recommendations.append("- Consider vectorized operations for batch transforms")
        
        if "10000_points" in file_io and file_io["10000_points"]["load_time"] > 1000:
            recommendations.append("- Implement streaming/chunked file loading")
            recommendations.append("- Consider binary format for large datasets")
        
        if "1000_points" in rendering and rendering["1000_points"]["render_time"] > 16:
            recommendations.append("- Implement render caching for static elements")
            recommendations.append("- Use level-of-detail (LOD) for large datasets")
            recommendations.append("- Consider GPU acceleration via OpenGL")
        
        if memory['large_dataset_memory'] > 50:
            recommendations.append("- Implement data structure optimization")
            recommendations.append("- Use memory-mapped files for large datasets")
        
        if recommendations:
            for rec in recommendations:
                report.append(rec)
        else:
            report.append("Performance is already optimized!")
        
        report.append("")
        report.append("=" * 60)
        report.append("END OF PERFORMANCE REPORT")
        report.append("=" * 60)
        
        return "\n".join(report)


def main():
    """Run performance profiling and generate report."""
    profiler = PerformanceProfiler()
    report = profiler.generate_report()
    
    # Save report
    report_path = Path("PERFORMANCE_BASELINE_REPORT.md")
    report_path.write_text(report)
    
    print("\n" + report)
    print(f"\nReport saved to: {report_path}")


if __name__ == "__main__":
    main()
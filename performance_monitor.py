#!/usr/bin/env python
"""
Real-time Performance Monitor for CurveEditor Application.

This module provides a real-time performance monitoring widget that can be
embedded in the main application to continuously track rendering performance,
memory usage, and interaction responsiveness.
"""

import logging
import statistics
import time
from collections import deque
from typing import Dict, List, Optional

from PySide6.QtCore import QTimer, Signal, Slot, Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen, QBrush
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QSizePolicy

from performance_profiler import PerformanceProfiler


class PerformanceGraph(QWidget):
    """
    Real-time performance graph widget.
    
    Displays performance metrics as a scrolling graph with configurable
    metrics, colors, and thresholds.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Graph configuration
        self.max_samples = 100  # Keep last 100 samples
        self.samples: deque = deque(maxlen=self.max_samples)
        self.metric_name = "Performance"
        self.unit = "ms"
        self.warning_threshold = 16.67  # 60 FPS threshold
        self.critical_threshold = 33.33  # 30 FPS threshold
        
        # Colors
        self.background_color = QColor(20, 20, 20)
        self.grid_color = QColor(60, 60, 60)
        self.line_color = QColor(0, 150, 255)
        self.warning_color = QColor(255, 165, 0)
        self.critical_color = QColor(255, 50, 50)
        self.text_color = QColor(255, 255, 255)
        
        # Graph state
        self.auto_scale = True
        self.min_value = 0.0
        self.max_value = 50.0
        
        # Widget setup
        self.setMinimumSize(300, 100)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    
    def add_sample(self, value: float) -> None:
        """Add a new performance sample."""
        self.samples.append(value)
        
        # Auto-scale if enabled
        if self.auto_scale and self.samples:
            self.max_value = max(max(self.samples) * 1.1, self.critical_threshold)
        
        self.update()
    
    def set_metric_name(self, name: str, unit: str = "ms") -> None:
        """Set the metric name and unit."""
        self.metric_name = name
        self.unit = unit
        self.update()
    
    def set_thresholds(self, warning: float, critical: float) -> None:
        """Set warning and critical thresholds."""
        self.warning_threshold = warning
        self.critical_threshold = critical
        self.update()
    
    def paintEvent(self, event):
        """Paint the performance graph."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        
        # Draw background
        painter.fillRect(rect, self.background_color)
        
        # Draw grid
        self._draw_grid(painter, rect)
        
        # Draw threshold lines
        self._draw_thresholds(painter, rect)
        
        # Draw performance line
        self._draw_performance_line(painter, rect)
        
        # Draw labels and current value
        self._draw_labels(painter, rect)
    
    def _draw_grid(self, painter: QPainter, rect):
        """Draw background grid."""
        painter.setPen(QPen(self.grid_color, 1))
        
        # Vertical grid lines (time)
        grid_count = 10
        for i in range(grid_count + 1):
            x = rect.left() + (i * rect.width()) // grid_count
            painter.drawLine(x, rect.top(), x, rect.bottom())
        
        # Horizontal grid lines (values)
        for i in range(5):
            y = rect.top() + (i * rect.height()) // 4
            painter.drawLine(rect.left(), y, rect.right(), y)
    
    def _draw_thresholds(self, painter: QPainter, rect):
        """Draw warning and critical threshold lines."""
        if not self.samples:
            return
        
        height = rect.height()
        value_range = self.max_value - self.min_value
        
        # Warning threshold
        if self.min_value <= self.warning_threshold <= self.max_value:
            warning_y = rect.bottom() - int(
                (self.warning_threshold - self.min_value) / value_range * height
            )
            
            painter.setPen(QPen(self.warning_color, 2, Qt.DashLine))
            painter.drawLine(rect.left(), warning_y, rect.right(), warning_y)
        
        # Critical threshold
        if self.min_value <= self.critical_threshold <= self.max_value:
            critical_y = rect.bottom() - int(
                (self.critical_threshold - self.min_value) / value_range * height
            )
            
            painter.setPen(QPen(self.critical_color, 2, Qt.DashLine))
            painter.drawLine(rect.left(), critical_y, rect.right(), critical_y)
    
    def _draw_performance_line(self, painter: QPainter, rect):
        """Draw the main performance line."""
        if len(self.samples) < 2:
            return
        
        width = rect.width()
        height = rect.height()
        value_range = self.max_value - self.min_value
        
        # Calculate points
        points = []
        samples_list = list(self.samples)
        
        for i, value in enumerate(samples_list):
            x = rect.left() + int((i * width) / (len(samples_list) - 1))
            y = rect.bottom() - int((value - self.min_value) / value_range * height)
            points.append((x, y))
        
        # Draw line segments with color coding
        for i in range(len(points) - 1):
            x1, y1 = points[i]
            x2, y2 = points[i + 1]
            
            # Choose color based on value
            value = samples_list[i + 1]
            if value >= self.critical_threshold:
                color = self.critical_color
                width_pen = 3
            elif value >= self.warning_threshold:
                color = self.warning_color
                width_pen = 2
            else:
                color = self.line_color
                width_pen = 2
            
            painter.setPen(QPen(color, width_pen))
            painter.drawLine(x1, y1, x2, y2)
        
        # Draw current value point
        if points:
            last_x, last_y = points[-1]
            current_value = samples_list[-1]
            
            if current_value >= self.critical_threshold:
                color = self.critical_color
            elif current_value >= self.warning_threshold:
                color = self.warning_color
            else:
                color = self.line_color
            
            painter.setBrush(QBrush(color))
            painter.setPen(QPen(color, 2))
            painter.drawEllipse(last_x - 3, last_y - 3, 6, 6)
    
    def _draw_labels(self, painter: QPainter, rect):
        """Draw metric labels and current value."""
        font = QFont("Arial", 9)
        painter.setFont(font)
        painter.setPen(QPen(self.text_color))
        
        metrics = QFontMetrics(font)
        
        if self.samples:
            current_value = self.samples[-1]
            avg_value = sum(self.samples) / len(self.samples)
            max_value = max(self.samples)
            
            # Status indicator
            if current_value >= self.critical_threshold:
                status = "CRITICAL"
                status_color = self.critical_color
            elif current_value >= self.warning_threshold:
                status = "WARNING"
                status_color = self.warning_color
            else:
                status = "GOOD"
                status_color = self.line_color
            
            # Draw metric name and status
            title_text = f"{self.metric_name}: {current_value:.1f}{self.unit} ({status})"
            painter.drawText(rect.left() + 5, rect.top() + 15, title_text)
            
            # Draw statistics
            stats_text = f"Avg: {avg_value:.1f}{self.unit}  Max: {max_value:.1f}{self.unit}"
            painter.drawText(rect.left() + 5, rect.bottom() - 5, stats_text)
            
            # Draw scale labels
            painter.drawText(rect.right() - 50, rect.top() + 15, f"{self.max_value:.0f}{self.unit}")
            painter.drawText(rect.right() - 50, rect.bottom() - 5, f"{self.min_value:.0f}{self.unit}")


class PerformanceStatsWidget(QWidget):
    """Widget displaying performance statistics in text form."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Create labels for different metrics
        self.fps_label = QLabel("FPS: --")
        self.paint_time_label = QLabel("Paint: --")
        self.memory_label = QLabel("Memory: --")
        self.points_label = QLabel("Points: --")
        self.interaction_label = QLabel("Interaction: --")
        
        # Style labels
        font = QFont("Consolas", 9)
        for label in [self.fps_label, self.paint_time_label, 
                     self.memory_label, self.points_label, self.interaction_label]:
            label.setFont(font)
            label.setStyleSheet("""
                QLabel {
                    color: #ffffff;
                    background-color: rgba(0, 0, 0, 100);
                    padding: 2px 5px;
                    border: 1px solid #444444;
                }
            """)
            layout.addWidget(label)
        
        layout.addStretch()
        
        self.setMaximumWidth(150)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    
    def update_fps(self, fps: float) -> None:
        """Update FPS display."""
        color = "#00ff00" if fps >= 60 else "#ffaa00" if fps >= 30 else "#ff0000"
        self.fps_label.setText(f"FPS: {fps:.1f}")
        self.fps_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background-color: rgba(0, 0, 0, 100);
                padding: 2px 5px;
                border: 1px solid #444444;
            }}
        """)
    
    def update_paint_time(self, time_ms: float) -> None:
        """Update paint time display."""
        color = "#00ff00" if time_ms < 16.67 else "#ffaa00" if time_ms < 33.33 else "#ff0000"
        self.paint_time_label.setText(f"Paint: {time_ms:.1f}ms")
        self.paint_time_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background-color: rgba(0, 0, 0, 100);
                padding: 2px 5px;
                border: 1px solid #444444;
            }}
        """)
    
    def update_memory(self, memory_mb: float) -> None:
        """Update memory usage display."""
        color = "#00ff00" if memory_mb < 100 else "#ffaa00" if memory_mb < 500 else "#ff0000"
        self.memory_label.setText(f"Memory: {memory_mb:.0f}MB")
        self.memory_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background-color: rgba(0, 0, 0, 100);
                padding: 2px 5px;
                border: 1px solid #444444;
            }}
        """)
    
    def update_points(self, count: int) -> None:
        """Update point count display."""
        color = "#00ff00" if count < 1000 else "#ffaa00" if count < 10000 else "#ff0000"
        self.points_label.setText(f"Points: {count:,}")
        self.points_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background-color: rgba(0, 0, 0, 100);
                padding: 2px 5px;
                border: 1px solid #444444;
            }}
        """)
    
    def update_interaction(self, time_ms: float) -> None:
        """Update interaction time display."""
        color = "#00ff00" if time_ms < 10 else "#ffaa00" if time_ms < 50 else "#ff0000"
        self.interaction_label.setText(f"Interact: {time_ms:.1f}ms")
        self.interaction_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                background-color: rgba(0, 0, 0, 100);
                padding: 2px 5px;
                border: 1px solid #444444;
            }}
        """)


class PerformanceMonitorWidget(QFrame):
    """
    Complete performance monitoring widget.
    
    Combines real-time graphs and statistics to provide comprehensive
    performance monitoring that can be embedded in the main application.
    """
    
    # Signals
    performance_alert = Signal(str, float)  # Alert message, value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.profiler = PerformanceProfiler()
        
        # Create UI
        self._setup_ui()
        
        # Setup monitoring
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_displays)
        self.update_timer.start(100)  # Update every 100ms
        
        # Performance tracking
        self.paint_times = deque(maxlen=60)  # Last 60 samples for FPS calculation
        self.interaction_times = deque(maxlen=20)  # Last 20 interaction times
        
        # Connect to profiler signals
        self.profiler.paint_time_measured.connect(self._on_paint_time)
        self.profiler.memory_usage_updated.connect(self._on_memory_update)
        self.profiler.performance_warning.connect(self._on_performance_warning)
        
        # Start monitoring
        self.profiler.start_monitoring()
        
        logging.info("Performance monitor widget initialized")
    
    def _setup_ui(self) -> None:
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Title
        title_label = QLabel("Performance Monitor")
        title_label.setFont(QFont("Arial", 10, QFont.Bold))
        title_label.setStyleSheet("color: #ffffff; padding: 2px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Create graphs
        self.fps_graph = PerformanceGraph()
        self.fps_graph.set_metric_name("FPS", "fps")
        self.fps_graph.set_thresholds(30, 60)  # Warning at 30, good at 60+
        self.fps_graph.setFixedHeight(80)
        layout.addWidget(self.fps_graph)
        
        self.paint_time_graph = PerformanceGraph()
        self.paint_time_graph.set_metric_name("Paint Time", "ms")
        self.paint_time_graph.set_thresholds(16.67, 33.33)  # 60fps/30fps thresholds
        self.paint_time_graph.setFixedHeight(80)
        layout.addWidget(self.paint_time_graph)
        
        self.memory_graph = PerformanceGraph()
        self.memory_graph.set_metric_name("Memory Usage", "MB")
        self.memory_graph.set_thresholds(200, 500)  # Warning thresholds
        self.memory_graph.auto_scale = True
        self.memory_graph.setFixedHeight(80)
        layout.addWidget(self.memory_graph)
        
        # Statistics widget
        self.stats_widget = PerformanceStatsWidget()
        layout.addWidget(self.stats_widget)
        
        # Style the frame
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(30, 30, 30, 200);
                border: 1px solid #555555;
                border-radius: 5px;
            }
        """)
        
        self.setFixedWidth(320)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
    
    @Slot(float)
    def _on_paint_time(self, time_ms: float) -> None:
        """Handle paint time measurement."""
        self.paint_times.append(time_ms)
        
        # Update paint time graph
        self.paint_time_graph.add_sample(time_ms)
        
        # Calculate and update FPS
        if len(self.paint_times) >= 10:  # Need some samples for stable FPS
            avg_paint_time = statistics.mean(self.paint_times)
            fps = 1000.0 / avg_paint_time if avg_paint_time > 0 else 0.0
            self.fps_graph.add_sample(fps)
        
        # Update statistics
        self.stats_widget.update_paint_time(time_ms)
        if len(self.paint_times) >= 5:
            fps = 1000.0 / statistics.mean(list(self.paint_times)[-5:])
            self.stats_widget.update_fps(fps)
    
    @Slot(float, float)
    def _on_memory_update(self, rss_mb: float, vms_mb: float) -> None:
        """Handle memory usage update."""
        self.memory_graph.add_sample(rss_mb)
        self.stats_widget.update_memory(rss_mb)
    
    @Slot(str, float)
    def _on_performance_warning(self, message: str, value: float) -> None:
        """Handle performance warnings."""
        logging.warning(f"Performance warning: {message}")
        self.performance_alert.emit(message, value)
    
    @Slot()
    def _update_displays(self) -> None:
        """Update display elements periodically."""
        # Update interaction time from profiler if available
        mouse_metrics = [
            metric for name, metric in self.profiler.metrics.items()
            if "mouse_event" in name and metric.recent_times
        ]
        
        if mouse_metrics:
            # Get most recent interaction time
            recent_times = []
            for metric in mouse_metrics:
                recent_times.extend(list(metric.recent_times)[-5:])  # Last 5 samples
            
            if recent_times:
                avg_interaction_time = statistics.mean(recent_times)
                self.stats_widget.update_interaction(avg_interaction_time)
    
    def set_point_count(self, count: int) -> None:
        """Update the point count display."""
        self.stats_widget.update_points(count)
    
    def add_interaction_time(self, time_ms: float) -> None:
        """Add an interaction time measurement."""
        self.interaction_times.append(time_ms)
        
        if len(self.interaction_times) >= 5:
            avg_time = statistics.mean(list(self.interaction_times)[-5:])
            self.stats_widget.update_interaction(avg_time)
    
    def get_current_metrics(self) -> Dict[str, float]:
        """Get current performance metrics."""
        metrics = {}
        
        if self.paint_times:
            avg_paint_time = statistics.mean(self.paint_times)
            metrics["fps"] = 1000.0 / avg_paint_time if avg_paint_time > 0 else 0.0
            metrics["paint_time_ms"] = avg_paint_time
        
        if self.profiler.memory_snapshots:
            metrics["memory_mb"] = self.profiler.memory_snapshots[-1].rss_mb
        
        if self.interaction_times:
            metrics["interaction_time_ms"] = statistics.mean(self.interaction_times)
        
        return metrics
    
    def reset_metrics(self) -> None:
        """Reset all performance metrics."""
        self.paint_times.clear()
        self.interaction_times.clear()
        self.profiler.metrics.clear()
        self.profiler.memory_snapshots.clear()
        
        logging.info("Performance metrics reset")
    
    def generate_performance_snapshot(self) -> Dict:
        """Generate a performance snapshot for reporting."""
        metrics = self.get_current_metrics()
        
        snapshot = {
            "timestamp": time.time(),
            "metrics": metrics,
            "profiler_data": {
                name: {
                    "avg_time": metric.avg_time,
                    "call_count": metric.call_count,
                    "recent_avg": metric.recent_avg
                }
                for name, metric in self.profiler.metrics.items()
            }
        }
        
        return snapshot
    
    def set_visible(self, visible: bool) -> None:
        """Control visibility and resource usage."""
        super().setVisible(visible)
        
        if visible:
            self.update_timer.start(100)
            self.profiler.start_monitoring()
        else:
            self.update_timer.stop()
            self.profiler.stop_monitoring()


# Integration helper function
def integrate_performance_monitor(main_window) -> PerformanceMonitorWidget:
    """
    Integrate performance monitor into main window.
    
    Args:
        main_window: MainWindow instance
        
    Returns:
        PerformanceMonitorWidget instance
    """
    monitor = PerformanceMonitorWidget(main_window)
    
    # Connect to curve widget if available
    curve_widget = getattr(main_window, 'curve_view_widget', None)
    if curve_widget:
        # Monitor point count changes
        if hasattr(curve_widget, 'curve_data'):
            monitor.set_point_count(len(curve_widget.curve_data))
        
        # Wrap paint events for monitoring
        original_paint_event = curve_widget.paintEvent
        
        def monitored_paint_event(event):
            start_time = time.perf_counter()
            result = original_paint_event(event)
            paint_time = (time.perf_counter() - start_time) * 1000.0
            monitor._on_paint_time(paint_time)
            return result
        
        curve_widget.paintEvent = monitored_paint_event
        
        # Monitor mouse interactions
        for event_name in ['mousePressEvent', 'mouseMoveEvent', 'mouseReleaseEvent']:
            if hasattr(curve_widget, event_name):
                original_method = getattr(curve_widget, event_name)
                
                def create_monitored_method(original):
                    def monitored_method(event):
                        start_time = time.perf_counter()
                        result = original(event)
                        interaction_time = (time.perf_counter() - start_time) * 1000.0
                        monitor.add_interaction_time(interaction_time)
                        return result
                    return monitored_method
                
                setattr(curve_widget, event_name, create_monitored_method(original_method))
    
    return monitor


# Example usage
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QWidget
    
    app = QApplication(sys.argv)
    
    # Create main window
    main_window = QMainWindow()
    main_window.setWindowTitle("Performance Monitor Test")
    main_window.resize(800, 600)
    
    # Create central widget
    central_widget = QWidget()
    layout = QHBoxLayout(central_widget)
    
    # Create performance monitor
    monitor = PerformanceMonitorWidget()
    layout.addWidget(monitor)
    
    # Add some space
    layout.addStretch()
    
    main_window.setCentralWidget(central_widget)
    
    # Simulate some performance data
    import random
    
    def simulate_performance():
        # Simulate paint times
        paint_time = 10 + random.uniform(-5, 20)  # 5-30ms range
        monitor._on_paint_time(paint_time)
        
        # Simulate memory usage
        memory = 50 + random.uniform(0, 10)  # Growing memory
        monitor._on_memory_update(memory, memory * 1.5)
    
    # Setup timer to simulate data
    timer = QTimer()
    timer.timeout.connect(simulate_performance)
    timer.start(50)  # Every 50ms
    
    main_window.show()
    sys.exit(app.exec())
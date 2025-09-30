#!/usr/bin/env python3
"""Simple monitoring utilities for CurveEditor performance tracking.

Provides lightweight in-memory metrics collection when feature flags enable monitoring.
Single-user application - no need for complex distributed metrics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class CacheMetrics:
    """Track cache performance metrics when cache_monitoring flag is enabled.

    Simple in-memory counters for cache hit/miss tracking.
    """

    hits: int = 0
    misses: int = 0
    reset_time: float = field(default_factory=time.time)

    def record_hit(self) -> None:
        """Record a cache hit."""
        self.hits += 1

    def record_miss(self) -> None:
        """Record a cache miss."""
        self.misses += 1

    @property
    def total(self) -> int:
        """Total number of cache accesses."""
        return self.hits + self.misses

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage.

        Returns:
            Hit rate from 0.0 to 100.0, or 0.0 if no accesses
        """
        if self.total == 0:
            return 0.0
        return (self.hits / self.total) * 100.0

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate as percentage.

        Returns:
            Miss rate from 0.0 to 100.0, or 0.0 if no accesses
        """
        if self.total == 0:
            return 0.0
        return (self.misses / self.total) * 100.0

    @property
    def uptime_seconds(self) -> float:
        """Time since metrics were reset."""
        return time.time() - self.reset_time

    def reset(self) -> None:
        """Reset all metrics."""
        self.hits = 0
        self.misses = 0
        self.reset_time = time.time()

    def summary(self) -> str:
        """Get human-readable summary of cache metrics.

        Returns:
            Multi-line string with cache statistics
        """
        uptime_mins = self.uptime_seconds / 60

        lines = [
            "Cache Metrics:",
            f"  Hits:      {self.hits:,}",
            f"  Misses:    {self.misses:,}",
            f"  Total:     {self.total:,}",
            f"  Hit Rate:  {self.hit_rate:.1f}%",
            f"  Miss Rate: {self.miss_rate:.1f}%",
            f"  Uptime:    {uptime_mins:.1f} minutes",
        ]

        if self.total > 0:
            avg_per_min = self.total / max(uptime_mins, 0.001)
            lines.append(f"  Avg/min:   {avg_per_min:.1f}")

        return "\n".join(lines)


@dataclass
class TransformMetrics:
    """Track transform performance metrics when debug_metrics flag is enabled.

    Tracks timing and count statistics for transform operations.
    """

    create_count: int = 0
    create_total_time: float = 0.0
    create_min_time: float = float("inf")
    create_max_time: float = 0.0

    data_to_screen_count: int = 0
    data_to_screen_total_time: float = 0.0

    screen_to_data_count: int = 0
    screen_to_data_total_time: float = 0.0

    reset_time: float = field(default_factory=time.time)

    def record_create(self, elapsed: float) -> None:
        """Record a transform creation timing.

        Args:
            elapsed: Time taken in seconds
        """
        self.create_count += 1
        self.create_total_time += elapsed
        self.create_min_time = min(self.create_min_time, elapsed)
        self.create_max_time = max(self.create_max_time, elapsed)

    def record_data_to_screen(self, elapsed: float) -> None:
        """Record a data-to-screen transform timing.

        Args:
            elapsed: Time taken in seconds
        """
        self.data_to_screen_count += 1
        self.data_to_screen_total_time += elapsed

    def record_screen_to_data(self, elapsed: float) -> None:
        """Record a screen-to-data transform timing.

        Args:
            elapsed: Time taken in seconds
        """
        self.screen_to_data_count += 1
        self.screen_to_data_total_time += elapsed

    @property
    def create_avg_time(self) -> float:
        """Average time for transform creation in seconds."""
        if self.create_count == 0:
            return 0.0
        return self.create_total_time / self.create_count

    @property
    def data_to_screen_avg_time(self) -> float:
        """Average time for data-to-screen transform in seconds."""
        if self.data_to_screen_count == 0:
            return 0.0
        return self.data_to_screen_total_time / self.data_to_screen_count

    @property
    def screen_to_data_avg_time(self) -> float:
        """Average time for screen-to-data transform in seconds."""
        if self.screen_to_data_count == 0:
            return 0.0
        return self.screen_to_data_total_time / self.screen_to_data_count

    @property
    def uptime_seconds(self) -> float:
        """Time since metrics were reset."""
        return time.time() - self.reset_time

    def reset(self) -> None:
        """Reset all metrics."""
        self.create_count = 0
        self.create_total_time = 0.0
        self.create_min_time = float("inf")
        self.create_max_time = 0.0
        self.data_to_screen_count = 0
        self.data_to_screen_total_time = 0.0
        self.screen_to_data_count = 0
        self.screen_to_data_total_time = 0.0
        self.reset_time = time.time()

    def summary(self) -> str:
        """Get human-readable summary of transform metrics.

        Returns:
            Multi-line string with transform statistics
        """
        uptime_mins = self.uptime_seconds / 60

        lines = [
            "Transform Metrics:",
            "  Create Operations:",
            f"    Count:    {self.create_count:,}",
            f"    Avg Time: {self.create_avg_time * 1000:.3f}ms",
        ]

        if self.create_count > 0:
            lines.extend(
                [
                    f"    Min Time: {self.create_min_time * 1000:.3f}ms",
                    f"    Max Time: {self.create_max_time * 1000:.3f}ms",
                ]
            )

        lines.extend(
            [
                "  Data→Screen:",
                f"    Count:    {self.data_to_screen_count:,}",
                f"    Avg Time: {self.data_to_screen_avg_time * 1000000:.1f}µs",
                "  Screen→Data:",
                f"    Count:    {self.screen_to_data_count:,}",
                f"    Avg Time: {self.screen_to_data_avg_time * 1000000:.1f}µs",
                f"  Uptime:     {uptime_mins:.1f} minutes",
            ]
        )

        return "\n".join(lines)


class MetricsCollector:
    """Central metrics collector for all monitored subsystems.

    Singleton that aggregates metrics from different components.
    Only active when monitoring feature flags are enabled.
    """

    _instance: MetricsCollector | None = None

    def __new__(cls) -> MetricsCollector:
        """Ensure singleton instance."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        """Initialize metrics collector (only once)."""
        if self._initialized:
            return

        self.cache_metrics = CacheMetrics()
        self.transform_metrics = TransformMetrics()
        self.custom_metrics: dict[str, float] = {}
        self._initialized = True

    def record_custom(self, name: str, value: float) -> None:
        """Record a custom metric value.

        Args:
            name: Metric name
            value: Metric value
        """
        self.custom_metrics[name] = value

    def reset_all(self) -> None:
        """Reset all metrics."""
        self.cache_metrics.reset()
        self.transform_metrics.reset()
        self.custom_metrics.clear()

    def summary(self) -> str:
        """Get complete metrics summary.

        Returns:
            Multi-line string with all metrics
        """
        sections = [
            "=" * 50,
            "Performance Metrics Summary",
            "=" * 50,
            "",
            self.cache_metrics.summary(),
            "",
            self.transform_metrics.summary(),
        ]

        if self.custom_metrics:
            sections.extend(
                [
                    "",
                    "Custom Metrics:",
                ]
            )
            for name, value in sorted(self.custom_metrics.items()):
                sections.append(f"  {name}: {value:.3f}")

        sections.append("=" * 50)
        return "\n".join(sections)

    @classmethod
    def get_instance(cls) -> MetricsCollector:
        """Get the singleton metrics collector instance.

        Returns:
            The global MetricsCollector instance
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance.

    Returns:
        The singleton MetricsCollector
    """
    return MetricsCollector.get_instance()


if __name__ == "__main__":
    # Demo/testing
    print("Testing monitoring utilities...")

    # Test cache metrics
    cache = CacheMetrics()
    for _ in range(75):
        cache.record_hit()
    for _ in range(25):
        cache.record_miss()

    print(cache.summary())
    print()

    # Test transform metrics
    import random

    transform = TransformMetrics()
    for _ in range(100):
        transform.record_create(random.uniform(0.001, 0.010))
        transform.record_data_to_screen(random.uniform(0.000001, 0.000010))
        transform.record_screen_to_data(random.uniform(0.000001, 0.000010))

    print(transform.summary())
    print()

    # Test collector
    collector = get_metrics_collector()
    collector.record_custom("fps", 60.0)
    collector.record_custom("memory_mb", 245.3)
    print(collector.summary())

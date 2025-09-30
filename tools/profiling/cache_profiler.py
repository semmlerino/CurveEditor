#!/usr/bin/env python
"""
CacheProfiler - Advanced profiling for CurveEditor zoom transformation caching.

This profiler instruments the caching layers to identify performance bottlenecks
and stale cache issues that cause the zoom floating bug.

Key Analysis Areas:
1. Cache hit/miss rates during zoom operations
2. ViewState cache key precision and quantization effects
3. Multiple cache layer interactions (_transform_cache vs LRU caches)
4. Cache invalidation timing and frequency
5. Transform stability and precision loss
"""

import contextlib
import hashlib
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

# Thread-safe profiling data
_profiling_lock = threading.RLock()


@dataclass
class CacheOperation:
    """Single cache operation record."""

    timestamp: float
    operation: str  # 'hit', 'miss', 'create', 'invalidate'
    cache_name: str
    key_hash: str
    zoom_factor: float | None = None
    base_scale: float | None = None
    total_scale: float | None = None
    precision_loss: float | None = None
    transform_hash: str | None = None
    stack_trace: str | None = None


@dataclass
class ZoomSession:
    """Zoom operation session tracking."""

    start_time: float
    operations: list[CacheOperation] = field(default_factory=list)
    zoom_start: float | None = None
    zoom_end: float | None = None
    cache_hits: int = 0
    cache_misses: int = 0
    invalidations: int = 0
    floating_detected: bool = False


class CacheProfiler:
    """Advanced cache profiler for zoom operations."""

    def __init__(self):
        self.enabled = False
        self.operations: list[CacheOperation] = []
        self.zoom_sessions: list[ZoomSession] = []
        self.current_session: ZoomSession | None = None
        self.cache_stats: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        # Performance tracking
        self.transform_creation_times: list[float] = []
        self.cache_lookup_times: list[float] = []

        # Precision analysis
        self.quantization_errors: list[tuple[float, float, str]] = []
        self.transform_stability: dict[str, list[str]] = defaultdict(list)

    def enable(self):
        """Enable cache profiling with instrumentation."""
        with _profiling_lock:
            if self.enabled:
                return

            self.enabled = True
            self.operations.clear()
            self.zoom_sessions.clear()
            self.current_session = None

            # Install instrumentation
            self._patch_transform_service()
            self._patch_curve_view_widget()

            logging.getLogger("cache_profiler").info("Cache profiling enabled")

    def disable(self):
        """Disable cache profiling."""
        with _profiling_lock:
            self.enabled = False
            logging.getLogger("cache_profiler").info("Cache profiling disabled")

    def start_zoom_session(self, initial_zoom: float):
        """Start tracking a zoom operation session."""
        if not self.enabled:
            return

        with _profiling_lock:
            self.current_session = ZoomSession(start_time=time.time(), zoom_start=initial_zoom)

    def end_zoom_session(self, final_zoom: float):
        """End current zoom session and analyze results."""
        if not self.enabled or not self.current_session:
            return

        with _profiling_lock:
            self.current_session.zoom_end = final_zoom
            self.zoom_sessions.append(self.current_session)

            # Analyze session for floating behavior
            self._analyze_zoom_session(self.current_session)
            self.current_session = None

    def record_cache_operation(
        self, operation: str, cache_name: str, cache_key: Any = None, additional_data: dict[str, Any] = None
    ):
        """Record a cache operation with detailed context."""
        if not self.enabled:
            return

        with _profiling_lock:
            # Generate consistent hash for cache key
            key_hash = self._hash_cache_key(cache_key) if cache_key else "unknown"

            # Extract additional data
            extra = additional_data or {}

            op = CacheOperation(
                timestamp=time.time(),
                operation=operation,
                cache_name=cache_name,
                key_hash=key_hash,
                zoom_factor=extra.get("zoom_factor"),
                base_scale=extra.get("base_scale"),
                total_scale=extra.get("total_scale"),
                precision_loss=extra.get("precision_loss"),
                transform_hash=extra.get("transform_hash"),
            )

            self.operations.append(op)

            # Update current session
            if self.current_session:
                self.current_session.operations.append(op)
                if operation == "hit":
                    self.current_session.cache_hits += 1
                elif operation == "miss":
                    self.current_session.cache_misses += 1
                elif operation == "invalidate":
                    self.current_session.invalidations += 1

            # Update cache stats
            self.cache_stats[cache_name][operation] += 1

    def analyze_precision_loss(self, original_value: float, quantized_value: float, parameter_name: str):
        """Analyze precision loss from quantization."""
        if not self.enabled:
            return

        loss = abs(original_value - quantized_value)
        if loss > 0:
            with _profiling_lock:
                self.quantization_errors.append((original_value, quantized_value, parameter_name))

    def track_transform_stability(self, transform_hash: str, view_state_info: str):
        """Track transform stability across operations."""
        if not self.enabled:
            return

        with _profiling_lock:
            self.transform_stability[transform_hash].append(view_state_info)

    def _hash_cache_key(self, key: Any) -> str:
        """Generate consistent hash for cache key."""
        try:
            if hasattr(key, "__dict__"):
                # For ViewState objects
                key_str = "|".join(
                    f"{k}:{v}"
                    for k, v in sorted(key.__dict__.items())
                    if not k.startswith("_") and k != "background_image"
                )
            else:
                key_str = str(key)

            return hashlib.md5(key_str.encode()).hexdigest()[:12]
        except Exception:
            return "hash_error"

    def _analyze_zoom_session(self, session: ZoomSession):
        """Analyze a zoom session for floating behavior indicators."""
        if not session.operations:
            return

        # Check for high cache miss rate during zoom
        total_ops = session.cache_hits + session.cache_misses
        if total_ops > 0:
            miss_rate = session.cache_misses / total_ops
            if miss_rate > 0.1:  # More than 10% misses
                session.floating_detected = True

        # Check for frequent invalidations
        if session.invalidations > len(session.operations) * 0.2:  # More than 20%
            session.floating_detected = True

        # Check for transform instability
        transform_hashes = set()
        for op in session.operations:
            if op.transform_hash:
                transform_hashes.add(op.transform_hash)

        if len(transform_hashes) > 3:  # Too many different transforms for one zoom
            session.floating_detected = True

    def _patch_transform_service(self):
        """Install instrumentation on TransformService methods."""
        try:
            from services import get_transform_service

            transform_service = get_transform_service()

            # Patch create_transform_from_view_state
            original_create = transform_service.create_transform_from_view_state

            def instrumented_create(view_state):
                start_time = time.time()

                # Analyze quantization effects
                if hasattr(view_state, "quantized_for_cache"):
                    quantized = view_state.quantized_for_cache()

                    # Check for precision loss
                    abs(view_state.zoom_factor - quantized.zoom_factor)
                    self.analyze_precision_loss(view_state.zoom_factor, quantized.zoom_factor, "zoom_factor")

                    abs(view_state.offset_x - quantized.offset_x)
                    self.analyze_precision_loss(view_state.offset_x, quantized.offset_x, "offset_x")

                # Check cache before calling
                cache_info_before = None
                if hasattr(transform_service, "_create_transform_cached"):
                    cache_info_before = transform_service._create_transform_cached.cache_info()

                result = original_create(view_state)

                # Check cache after calling
                cache_hit = False
                if cache_info_before and hasattr(transform_service, "_create_transform_cached"):
                    cache_info_after = transform_service._create_transform_cached.cache_info()
                    cache_hit = cache_info_after.hits > cache_info_before.hits

                # Record operation
                elapsed = time.time() - start_time
                self.cache_lookup_times.append(elapsed)

                operation = "hit" if cache_hit else "miss"
                self.record_cache_operation(
                    operation,
                    "TransformService",
                    cache_key=view_state,
                    additional_data={
                        "zoom_factor": getattr(view_state, "zoom_factor", None),
                        "base_scale": getattr(view_state, "base_scale", None),
                        "total_scale": getattr(view_state, "zoom_factor", 1.0) * getattr(view_state, "base_scale", 1.0),
                        "transform_hash": result.stability_hash if hasattr(result, "stability_hash") else None,
                    },
                )

                return result

            transform_service.create_transform_from_view_state = instrumented_create

        except Exception as e:
            logging.getLogger("cache_profiler").warning(f"Failed to patch TransformService: {e}")

    def _patch_curve_view_widget(self):
        """Install instrumentation on CurveViewWidget cache methods."""
        try:
            # This would require importing the widget class, which might cause circular imports
            # For now, we'll instrument via monkey patching in the test
            pass
        except Exception as e:
            logging.getLogger("cache_profiler").warning(f"Failed to patch CurveViewWidget: {e}")

    def generate_report(self) -> str:
        """Generate comprehensive cache profiling report."""
        with _profiling_lock:
            report = []
            report.append("=" * 80)
            report.append("CURVEEDITOR CACHE PROFILING REPORT")
            report.append("=" * 80)

            # Overall statistics
            total_ops = len(self.operations)
            report.append(f"\nTotal Operations: {total_ops}")
            report.append(f"Zoom Sessions: {len(self.zoom_sessions)}")

            if total_ops > 0:
                # Cache statistics by type
                report.append("\nCACHE STATISTICS:")
                for cache_name, stats in self.cache_stats.items():
                    sum(stats.values())
                    hits = stats.get("hit", 0)
                    misses = stats.get("miss", 0)
                    hit_rate = hits / (hits + misses) if (hits + misses) > 0 else 0

                    report.append(f"  {cache_name}:")
                    report.append(f"    Hit Rate: {hit_rate:.1%} ({hits}/{hits+misses})")
                    report.append(f"    Invalidations: {stats.get('invalidate', 0)}")
                    report.append(f"    Creates: {stats.get('create', 0)}")

            # Zoom session analysis
            floating_sessions = sum(1 for s in self.zoom_sessions if s.floating_detected)
            if self.zoom_sessions:
                report.append("\nZOOM SESSION ANALYSIS:")
                report.append(f"  Total Sessions: {len(self.zoom_sessions)}")
                report.append(
                    f"  Floating Detected: {floating_sessions} ({floating_sessions/len(self.zoom_sessions):.1%})"
                )

                avg_hit_rate = sum(
                    s.cache_hits / (s.cache_hits + s.cache_misses) if (s.cache_hits + s.cache_misses) > 0 else 0
                    for s in self.zoom_sessions
                ) / len(self.zoom_sessions)
                report.append(f"  Average Hit Rate: {avg_hit_rate:.1%}")

                avg_invalidations = sum(s.invalidations for s in self.zoom_sessions) / len(self.zoom_sessions)
                report.append(f"  Average Invalidations per Session: {avg_invalidations:.1f}")

            # Precision analysis
            if self.quantization_errors:
                report.append("\nPRECISION ANALYSIS:")
                report.append(f"  Quantization Errors: {len(self.quantization_errors)}")

                by_param = defaultdict(list)
                for orig, quant, param in self.quantization_errors:
                    by_param[param].append(abs(orig - quant))

                for param, errors in by_param.items():
                    avg_error = sum(errors) / len(errors)
                    max_error = max(errors)
                    report.append(f"    {param}: avg_error={avg_error:.6f}, max_error={max_error:.6f}")

            # Performance metrics
            if self.cache_lookup_times:
                avg_lookup = sum(self.cache_lookup_times) / len(self.cache_lookup_times)
                max_lookup = max(self.cache_lookup_times)
                report.append("\nPERFORMANCE METRICS:")
                report.append(f"  Average Lookup Time: {avg_lookup*1000:.3f}ms")
                report.append(f"  Max Lookup Time: {max_lookup*1000:.3f}ms")
                report.append(f"  Total Lookup Operations: {len(self.cache_lookup_times)}")

            # Transform stability
            unstable_transforms = sum(1 for hashes in self.transform_stability.values() if len(hashes) > 1)
            if self.transform_stability:
                report.append("\nTRANSFORM STABILITY:")
                report.append(f"  Unique Transforms: {len(self.transform_stability)}")
                report.append(f"  Unstable Transforms: {unstable_transforms}")

            # Recommendations
            report.append("\nRECOMMENDATIONS:")

            # Cache hit rate issues
            overall_hit_rate = 0
            total_cache_ops = 0
            for stats in self.cache_stats.values():
                hits = stats.get("hit", 0)
                misses = stats.get("miss", 0)
                overall_hit_rate += hits
                total_cache_ops += hits + misses

            if total_cache_ops > 0:
                overall_hit_rate /= total_cache_ops
                if overall_hit_rate < 0.95:  # Less than 95%
                    report.append(f"  ⚠ LOW CACHE HIT RATE ({overall_hit_rate:.1%})")
                    report.append("    - Consider adjusting quantization precision")
                    report.append("    - Check if cache keys include all relevant state")

            # Floating detection
            if floating_sessions > 0:
                report.append(f"  🐛 FLOATING BUG DETECTED in {floating_sessions} sessions")
                report.append("    - High cache miss rates during zoom operations")
                report.append("    - Excessive cache invalidations")
                report.append("    - Transform instability")

            # Precision issues
            zoom_errors = [
                err
                for orig, quant, param in self.quantization_errors
                if param == "zoom_factor"
                for err in [abs(orig - quant)]
            ]
            if zoom_errors and max(zoom_errors) > 0.001:
                report.append("  📐 PRECISION ISSUES with zoom quantization")
                report.append(f"    - Max zoom error: {max(zoom_errors):.6f}")
                report.append("    - Consider reducing quantization precision for zoom")

            report.append("\n" + "=" * 80)

            return "\n".join(report)


# Global profiler instance
cache_profiler = CacheProfiler()


# Convenience functions
def enable_cache_profiling():
    """Enable cache profiling."""
    cache_profiler.enable()


def disable_cache_profiling():
    """Disable cache profiling."""
    cache_profiler.disable()


def get_cache_report() -> str:
    """Get cache profiling report."""
    return cache_profiler.generate_report()


# Context manager for profiling zoom operations
@contextlib.contextmanager
def profile_zoom_operation(initial_zoom: float, final_zoom: float):
    """Context manager for profiling zoom operations."""
    cache_profiler.start_zoom_session(initial_zoom)
    try:
        yield cache_profiler
    finally:
        cache_profiler.end_zoom_session(final_zoom)

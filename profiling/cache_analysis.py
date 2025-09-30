#!/usr/bin/env python
"""
Static analysis of CurveEditor zoom cache implementation.

This script analyzes the cache structure and identifies potential issues
without running the full application.
"""

import re
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class CacheAnalyzer:
    """Analyzes cache implementation for potential issues."""

    def __init__(self):
        self.issues: list[str] = []
        self.warnings: list[str] = []
        self.recommendations: list[str] = []

    def analyze_transform_service(self, file_path: str):
        """Analyze TransformService caching implementation."""
        print(f"Analyzing {file_path}...")

        with open(file_path) as f:
            content = f.read()

        # Check for LRU cache usage
        lru_cache_matches = re.findall(r"@lru_cache\(maxsize=(\d+)\)", content)
        print(f"Found {len(lru_cache_matches)} LRU cache decorators with sizes: {lru_cache_matches}")

        # Check quantization precision
        quantization_matches = re.findall(r"precision\s*=\s*([\d.]+)", content)
        print(f"Quantization precisions found: {quantization_matches}")

        # Look for cache key issues
        if "background_image" in content and "hash=False" in content:
            print("✓ Background image excluded from hash (good)")

        # Check for base_scale usage
        base_scale_count = content.count("base_scale")
        print(f"base_scale mentioned {base_scale_count} times")

        # Look for zoom_factor vs total_scale usage
        zoom_factor_count = content.count("zoom_factor")
        total_scale_count = content.count("total_scale")
        print(f"zoom_factor: {zoom_factor_count}, total_scale: {total_scale_count}")

        # Check for cache invalidation logic
        cache_clear_count = content.count("cache_clear")
        print(f"Cache clear operations: {cache_clear_count}")

        # Check ViewState quantization method
        quantize_method_match = re.search(r"def quantized_for_cache\(self.*?\):", content, re.DOTALL)
        if quantize_method_match:
            print("✓ ViewState quantization method found")
            # Extract the method
            quantize_start = quantize_method_match.start()
            # Find the end of the method (next 'def' or 'class' at same indentation)
            method_content = content[quantize_start : quantize_start + 2000]  # Reasonable limit

            # Check zoom precision
            if "zoom_precision = precision / 10" in method_content:
                print("✓ Separate zoom precision (precision/10)")

            # Check for minimum value handling
            if "min_value" in method_content:
                print("✓ Minimum value handling in quantization")

        # Analyze cache key composition
        viewstate_fields = re.findall(r"(\w+):\s*(?:int|float|bool)", content)
        print(f"ViewState fields: {len(set(viewstate_fields))}")

        # Check for cache bypass conditions
        if "validation_config.enable_full_validation != env_config.enable_full_validation" in content:
            print("⚠ Cache bypass for different validation configs")

        return self._analyze_cache_structure(content)

    def analyze_curve_view_widget(self, file_path: str):
        """Analyze CurveViewWidget caching implementation."""
        print(f"\nAnalyzing {file_path}...")

        with open(file_path) as f:
            content = f.read()

        # Check transform cache usage
        transform_cache_count = content.count("_transform_cache")
        print(f"_transform_cache references: {transform_cache_count}")

        # Check invalidation frequency
        invalidate_count = content.count("_invalidate_caches")
        print(f"_invalidate_caches calls: {invalidate_count}")

        # Find all invalidation call sites
        invalidate_lines = []
        for i, line in enumerate(content.split("\n"), 1):
            if "_invalidate_caches()" in line:
                invalidate_lines.append((i, line.strip()))

        print("Cache invalidation call sites:")
        for line_num, line in invalidate_lines[:10]:  # Show first 10
            print(f"  Line {line_num}: {line}")

        if len(invalidate_lines) > 10:
            print(f"  ... and {len(invalidate_lines) - 10} more")

        # Check for base_scale calculation
        base_scale_calc = re.search(r"base_scale\s*=.*?min\(scale_x,\s*scale_y\)", content, re.DOTALL)
        if base_scale_calc:
            print("✓ Base scale calculation found")

        # Check total_scale calculation
        total_scale_calc = re.search(r"total_scale\s*=\s*base_scale\s*\*\s*self\.zoom_factor", content)
        if total_scale_calc:
            print("✓ Total scale calculation found")

        # Check zoom_factor vs total_scale in ViewState
        viewstate_creation = re.search(r"ViewState\((.*?)\)", content, re.DOTALL)
        if viewstate_creation:
            viewstate_args = viewstate_creation.group(1)
            if "zoom_factor=total_scale" in viewstate_args:
                print("⚠ ViewState uses total_scale as zoom_factor")
            if "base_scale=base_scale" in viewstate_args:
                print("✓ ViewState includes separate base_scale")

        return self._analyze_invalidation_patterns(content)

    def _analyze_cache_structure(self, content: str) -> dict[str, any]:
        """Analyze cache structure for potential issues."""
        analysis = {}

        # Check for cache key conflicts
        # ViewState fields that could cause cache misses
        precision_sensitive_fields = ["zoom_factor", "offset_x", "offset_y"]

        for field in precision_sensitive_fields:
            if field in content:
                # Check if field is quantized
                if f"quantize(self.{field}" in content:
                    analysis[f"{field}_quantized"] = True
                else:
                    analysis[f"{field}_quantized"] = False
                    self.issues.append(f"Field {field} may not be quantized properly")

        # Check cache size appropriateness
        cache_sizes = re.findall(r"maxsize=(\d+)", content)
        for size in cache_sizes:
            size_int = int(size)
            if size_int < 64:
                self.warnings.append(f"Cache size {size_int} may be too small")
            elif size_int > 1024:
                self.warnings.append(f"Cache size {size_int} may be too large")

        return analysis

    def _analyze_invalidation_patterns(self, content: str) -> dict[str, any]:
        """Analyze cache invalidation patterns."""
        analysis = {}

        # Find methods that call invalidate
        invalidation_methods = set()
        lines = content.split("\n")

        current_method = None
        for line in lines:
            # Track current method
            method_match = re.match(r"\s*def\s+(\w+)", line)
            if method_match:
                current_method = method_match.group(1)

            # Check for invalidation calls
            if "_invalidate_caches()" in line and current_method:
                invalidation_methods.add(current_method)

        analysis["invalidation_methods"] = invalidation_methods
        print(f"Methods that invalidate cache: {len(invalidation_methods)}")

        # Check for excessive invalidation
        if len(invalidation_methods) > 10:
            self.warnings.append(f"High number of invalidation points: {len(invalidation_methods)}")

        # Check for zoom-related invalidations
        zoom_methods = [m for m in invalidation_methods if "zoom" in m.lower()]
        if zoom_methods:
            analysis["zoom_invalidations"] = zoom_methods
            print(f"Zoom-related invalidation methods: {zoom_methods}")

        return analysis

    def check_cache_key_precision(self):
        """Check cache key precision issues."""
        print("\nAnalyzing cache key precision...")

        # Simulate quantization effects
        test_values = [1.0, 1.001, 1.002, 1.01, 1.05, 1.1]
        precision = 0.1
        zoom_precision = precision / 10  # 0.01

        print(f"Standard precision: {precision}")
        print(f"Zoom precision: {zoom_precision}")

        print("Quantization effects:")
        for value in test_values:
            quantized = round(value / zoom_precision) * zoom_precision
            print(f"  {value:.3f} -> {quantized:.3f} (diff: {abs(value-quantized):.6f})")

        # Check for potential collisions
        quantized_values = [round(v / zoom_precision) * zoom_precision for v in test_values]
        unique_quantized = set(quantized_values)

        if len(unique_quantized) < len(test_values):
            collision_count = len(test_values) - len(unique_quantized)
            self.issues.append(f"Quantization causes {collision_count} cache key collisions")
            print(f"⚠ {collision_count} cache key collisions detected!")

    def analyze_floating_causes(self):
        """Analyze potential causes of floating behavior."""
        print("\nAnalyzing potential floating causes...")

        potential_causes = [
            "Cache key doesn't include all relevant state",
            "Quantization precision too coarse for smooth zoom",
            "base_scale vs zoom_factor inconsistency in cache key",
            "Excessive cache invalidation during zoom",
            "Transform precision loss in calculations",
            "Multiple transform instances with different configs",
            "Race conditions in cache updates",
        ]

        print("Potential floating causes:")
        for i, cause in enumerate(potential_causes, 1):
            print(f"  {i}. {cause}")

        # Based on analysis, identify most likely causes
        likely_causes = []

        if len(self.issues) > 0:
            likely_causes.append("Cache key precision issues detected")

        if len(self.warnings) > 0:
            likely_causes.append("Cache configuration warnings found")

        return likely_causes

    def generate_recommendations(self):
        """Generate recommendations based on analysis."""
        print("\nGenerating recommendations...")

        recommendations = []

        # Cache key recommendations
        recommendations.append("1. Verify cache key includes base_scale separately from zoom_factor")
        recommendations.append("2. Consider reducing zoom quantization precision (e.g., 0.001 instead of 0.01)")
        recommendations.append("3. Add cache key debugging to log collisions")

        # Performance recommendations
        recommendations.append("4. Monitor cache hit rate in production (target >95%)")
        recommendations.append("5. Consider cache warming for common zoom levels")

        # Debugging recommendations
        recommendations.append("6. Add transform stability hash logging")
        recommendations.append("7. Implement cache operation profiling")
        recommendations.append("8. Test with cache temporarily disabled to confirm floating is cache-related")

        return recommendations

    def run_analysis(self):
        """Run complete cache analysis."""
        print("CurveEditor Cache Analysis")
        print("=" * 50)

        # Analyze main files
        base_path = Path(__file__).parent.parent
        transform_service_path = base_path / "services" / "transform_service.py"
        curve_view_path = base_path / "ui" / "curve_view_widget.py"

        transform_analysis = self.analyze_transform_service(str(transform_service_path))
        curve_view_analysis = self.analyze_curve_view_widget(str(curve_view_path))

        # Additional analysis
        self.check_cache_key_precision()
        floating_causes = self.analyze_floating_causes()
        recommendations = self.generate_recommendations()

        # Summary
        print("\n" + "=" * 50)
        print("ANALYSIS SUMMARY")
        print("=" * 50)

        if self.issues:
            print(f"\n🐛 ISSUES FOUND ({len(self.issues)}):")
            for issue in self.issues:
                print(f"  - {issue}")

        if self.warnings:
            print(f"\n⚠ WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")

        if floating_causes:
            print("\n🎯 LIKELY FLOATING CAUSES:")
            for cause in floating_causes:
                print(f"  - {cause}")

        print("\n💡 RECOMMENDATIONS:")
        for rec in recommendations:
            print(f"  {rec}")

        return {
            "issues": self.issues,
            "warnings": self.warnings,
            "recommendations": recommendations,
            "transform_analysis": transform_analysis,
            "curve_view_analysis": curve_view_analysis,
        }


if __name__ == "__main__":
    analyzer = CacheAnalyzer()
    results = analyzer.run_analysis()

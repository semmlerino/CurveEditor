#!/usr/bin/env python
"""Quick check that our optimizations are loaded."""

import sys

from PySide6.QtWidgets import QApplication

from rendering.optimized_curve_renderer import OptimizedCurveRenderer
from ui.curve_view_widget import CurveViewWidget


def main():
    """Main function to run the optimization checks."""
    app = QApplication(sys.argv)  # noqa: F841

    w = CurveViewWidget()

    # Check new attributes exist
    attrs_to_check = [
        "_is_interacting",
        "_interaction_start_time",
        "_pending_full_redraw",
        "_dirty_region",
        "_last_paint_time",
        "_target_fps",
        "_frame_time",
        "_last_valid_transform",
        "_cache_monitor",
        "_pre_calculate_transform",
        "_get_cached_transform_for_paint",
        "_render_with_quality",
        "_mark_dirty_region",
        "_log_paint_performance",
    ]

    for attr in attrs_to_check:
        has_attr = hasattr(w, attr)
        print(f"{attr}: {has_attr}")
        if not has_attr:
            print(f"  ERROR: Missing attribute {attr}")

    # Check if render_draft exists in renderer
    renderer = OptimizedCurveRenderer()
    print(f"\nrender_draft method: {hasattr(renderer, 'render_draft')}")

    print("\nAll checks passed!" if all(hasattr(w, attr) for attr in attrs_to_check) else "\nSome attributes missing!")


if __name__ == "__main__":
    main()

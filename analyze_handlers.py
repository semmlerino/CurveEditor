#!/usr/bin/env python3
"""Analyze event handlers in MainWindow to identify thin wrappers."""

import re
from pathlib import Path


def analyze_handlers():
    """Analyze all _on_* methods in MainWindow."""

    main_window_path = Path("ui/main_window.py")
    content = main_window_path.read_text()

    # Find all _on_* methods with their bodies
    pattern = r"(    def _on_\w+\([^)]*\)[^:]*:\n(?:.*\n)*?(?=\n    def |\n    @|\n\n|\Z))"
    methods = re.findall(pattern, content)

    handlers = {}

    for method in methods:
        lines = method.strip().split("\n")

        # Extract method name
        method_name_match = re.search(r"def (_on_\w+)", lines[0])
        if not method_name_match:
            continue

        method_name = method_name_match.group(1)

        # Count actual code lines (exclude decorators, docstrings, pass)
        code_lines = []
        in_docstring = False

        for line in lines[1:]:  # Skip def line
            stripped = line.strip()

            # Skip empty lines
            if not stripped:
                continue

            # Handle docstrings
            if '"""' in stripped:
                if stripped.count('"""') == 2:
                    # Single line docstring
                    continue
                else:
                    in_docstring = not in_docstring
                    continue

            if in_docstring:
                continue

            # Skip decorators
            if stripped.startswith("@"):
                continue

            # This is actual code
            code_lines.append(line)

        # Analyze delegation pattern
        delegates_to = None
        is_thin_wrapper = False

        if len(code_lines) == 1:
            # Single line - likely a delegation
            code = code_lines[0].strip()

            # Check for controller delegation patterns
            if "self.event_coordinator." in code:
                delegates_to = "event_coordinator"
                is_thin_wrapper = True
            elif "self.playback_controller." in code:
                delegates_to = "playback_controller"
                is_thin_wrapper = True
            elif "self.frame_navigation_controller." in code:
                delegates_to = "frame_navigation_controller"
                is_thin_wrapper = True
            elif "self.zoom_controller." in code:
                delegates_to = "zoom_controller"
                is_thin_wrapper = True
            elif "self.point_edit_controller." in code:
                delegates_to = "point_edit_controller"
                is_thin_wrapper = True
            elif "self.tracking_panel_controller." in code:
                delegates_to = "tracking_panel_controller"
                is_thin_wrapper = True
            elif "self.file_operations_manager." in code:
                delegates_to = "file_operations_manager"
                is_thin_wrapper = True
            elif "self.view_update_manager." in code:
                delegates_to = "view_update_manager"
                is_thin_wrapper = True

        handlers[method_name] = {
            "lines": len(lines),
            "code_lines": len(code_lines),
            "delegates_to": delegates_to,
            "is_thin_wrapper": is_thin_wrapper,
            "code": code_lines[0] if code_lines else None,
        }

    return handlers


def main():
    """Main analysis."""
    handlers = analyze_handlers()

    # Group by controller
    by_controller = {}
    complex_handlers = []

    for name, info in handlers.items():
        if info["is_thin_wrapper"]:
            controller = info["delegates_to"]
            if controller not in by_controller:
                by_controller[controller] = []
            by_controller[controller].append(name)
        else:
            complex_handlers.append(name)

    print("=== THIN WRAPPER HANDLERS (can be removed) ===\n")

    total_wrapper_lines = 0
    for controller, methods in sorted(by_controller.items()):
        print(f"{controller}: ({len(methods)} methods)")
        for method in sorted(methods):
            info = handlers[method]
            print(f"  - {method} ({info['lines']} lines)")
            total_wrapper_lines += info["lines"]
        print()

    print(f"Total thin wrappers: {sum(len(m) for m in by_controller.values())}")
    print(f"Total lines to save: ~{total_wrapper_lines}\n")

    print("=== COMPLEX HANDLERS (need analysis) ===\n")
    for name in sorted(complex_handlers):
        info = handlers[name]
        print(f"  - {name} ({info['code_lines']} code lines)")

    print(f"\nTotal complex handlers: {len(complex_handlers)}")


if __name__ == "__main__":
    main()

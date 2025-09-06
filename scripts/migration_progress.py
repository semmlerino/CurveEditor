#!/usr/bin/env python3
"""Track hasattr() migration progress for Phase 2 type safety improvements."""

import subprocess

# Color codes for terminal output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


def count_hasattr_occurrences() -> dict[str, int]:
    """Count hasattr() calls in each Python file."""
    cmd = ["rg", "hasattr\\(", "--count-matches", "--type", "python"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        occurrences = {}
        for line in result.stdout.strip().split("\n"):
            if ":" in line:
                file_path, count = line.rsplit(":", 1)
                # Exclude test files from production count
                if not file_path.startswith("tests/"):
                    occurrences[file_path] = int(count)
        return occurrences
    except subprocess.CalledProcessError:
        return {}


def categorize_files(occurrences: dict[str, int]) -> dict[str, list[tuple[str, int]]]:
    """Categorize files by component type."""
    categories = {"Core": [], "Data": [], "Rendering": [], "Services": [], "UI": [], "Other": []}

    for file_path, count in occurrences.items():
        if file_path.startswith("core/"):
            categories["Core"].append((file_path, count))
        elif file_path.startswith("data/"):
            categories["Data"].append((file_path, count))
        elif file_path.startswith("rendering/"):
            categories["Rendering"].append((file_path, count))
        elif file_path.startswith("services/"):
            categories["Services"].append((file_path, count))
        elif file_path.startswith("ui/"):
            categories["UI"].append((file_path, count))
        else:
            categories["Other"].append((file_path, count))

    # Sort each category by count (highest first)
    for category in categories:
        categories[category].sort(key=lambda x: x[1], reverse=True)

    return categories


def get_basedpyright_stats() -> tuple[int, int]:
    """Get current basedpyright error and warning counts."""
    try:
        result = subprocess.run(["./bpr"], capture_output=True, text=True)
        output = result.stdout + result.stderr

        errors = 0
        warnings = 0

        # Parse the summary line
        for line in output.split("\n"):
            if "error" in line.lower() and "warning" in line.lower():
                parts = line.split(",")
                for part in parts:
                    if "error" in part:
                        errors = int("".join(filter(str.isdigit, part)) or 0)
                    elif "warning" in part:
                        warnings = int("".join(filter(str.isdigit, part)) or 0)

        return errors, warnings
    except Exception:
        return -1, -1


def print_progress_report():
    """Print a formatted progress report."""
    print(f"\n{BOLD}{'='*60}")
    print("   Phase 2: Type Safety Migration Progress Report")
    print(f"{'='*60}{RESET}\n")

    # Count hasattr occurrences
    occurrences = count_hasattr_occurrences()
    total_hasattr = sum(occurrences.values())

    # Get basedpyright stats
    errors, warnings = get_basedpyright_stats()

    # Print summary metrics
    print(f"{BOLD}Summary Metrics:{RESET}")
    print(
        f"  Total hasattr() calls: {RED if total_hasattr > 50 else YELLOW if total_hasattr > 25 else GREEN}{total_hasattr}{RESET}"
    )
    print(f"  Files with hasattr(): {len(occurrences)}")
    if errors >= 0:
        print(f"  Basedpyright errors: {RED if errors > 300 else YELLOW if errors > 200 else GREEN}{errors}{RESET}")
        print(f"  Basedpyright warnings: {warnings}")
    print()

    # Progress against goals
    print(f"{BOLD}Progress Against Goals:{RESET}")
    hasattr_progress = max(0, (97 - total_hasattr) / 97 * 100)
    print(
        f"  hasattr reduction: {GREEN if hasattr_progress >= 50 else YELLOW if hasattr_progress >= 25 else RED}{hasattr_progress:.1f}%{RESET} (Goal: 50%)"
    )

    if errors >= 0:
        error_progress = max(0, (556 - errors) / (556 - 300) * 100)
        print(
            f"  Type error reduction: {GREEN if error_progress >= 75 else YELLOW if error_progress >= 50 else RED}{error_progress:.1f}%{RESET} (Goal: <300 errors)"
        )
    print()

    # Categorized file list
    categories = categorize_files(occurrences)

    print(f"{BOLD}Files by Category:{RESET}")
    for category, files in categories.items():
        if files:
            total_in_category = sum(count for _, count in files)
            print(f"\n  {BLUE}{category}{RESET} ({total_in_category} total):")
            for file_path, count in files[:5]:  # Show top 5 in each category
                status = f"{RED}High" if count >= 8 else f"{YELLOW}Medium" if count >= 4 else f"{GREEN}Low"
                print(f"    {count:2d} - {file_path} [{status}{RESET}]")
            if len(files) > 5:
                print(f"    ... and {len(files) - 5} more files")

    # Priority files for next sprint
    print(f"\n{BOLD}Priority Files for Refactoring:{RESET}")
    sorted_files = sorted(occurrences.items(), key=lambda x: x[1], reverse=True)[:5]
    for i, (file_path, count) in enumerate(sorted_files, 1):
        print(f"  {i}. {file_path}: {RED}{count}{RESET} hasattr() calls")

    # Week tracking
    print(f"\n{BOLD}Weekly Sprint Status:{RESET}")
    week_goals = {
        1: "Protocol Interfaces",
        2: "High-Frequency Paths (28 calls)",
        3: "Core Components",
        4: "Testing & Documentation",
    }

    # Determine current week (manual update or could be calculated from start date)
    current_week = 1  # Update this as weeks progress

    for week, goal in week_goals.items():
        if week < current_week:
            status = f"{GREEN}✓ Complete{RESET}"
        elif week == current_week:
            status = f"{YELLOW}→ In Progress{RESET}"
        else:
            status = "  Pending"
        print(f"  Week {week}: {goal} {status}")

    print(f"\n{BOLD}{'='*60}{RESET}\n")


def main():
    """Main entry point."""
    print_progress_report()

    # Check if we've met Phase 2 goals
    occurrences = count_hasattr_occurrences()
    total_hasattr = sum(occurrences.values())

    if total_hasattr <= 50:
        print(f"{GREEN}{BOLD}🎉 Phase 2 Goal Achieved! hasattr() calls reduced by >50%{RESET}")
    else:
        remaining = total_hasattr - 50
        print(f"📊 {remaining} more hasattr() calls to remove to reach Phase 2 goal")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Count mock definitions in test files.

Counts actual mock instantiations and patches, not just lines mentioning "Mock".
"""

import re
from pathlib import Path


def count_mock_definitions(file_path: Path) -> dict[str, int]:
    """Count different types of mock definitions in a file."""
    content = file_path.read_text()

    counts = {
        "Mock()": len(re.findall(r"\bMock\(", content)),
        "MagicMock()": len(re.findall(r"\bMagicMock\(", content)),
        "@patch": len(re.findall(r"@patch\(", content)),
        "patch()": len(re.findall(r"\bpatch\(", content)),
        "mock.Mock()": len(re.findall(r"mock\.Mock\(", content)),
        "mock.MagicMock()": len(re.findall(r"mock\.MagicMock\(", content)),
    }

    # Avoid double-counting @patch and patch()
    # @patch creates a mock via decorator, patch() is context manager
    # They're different uses, but @patch includes the string "patch("
    # So subtract @patch from patch() count
    counts["patch()"] = max(0, counts["patch()"] - counts["@patch"])

    return counts


def main():
    """Count mocks across all test files."""
    test_dir = Path("tests")
    test_files = sorted(test_dir.glob("test_*.py"))

    total_counts = {
        "Mock()": 0,
        "MagicMock()": 0,
        "@patch": 0,
        "patch()": 0,
        "mock.Mock()": 0,
        "mock.MagicMock()": 0,
    }

    file_totals = []

    for test_file in test_files:
        counts = count_mock_definitions(test_file)
        file_total = sum(counts.values())

        if file_total > 0:
            file_totals.append((file_total, test_file.name, counts))

            for key, value in counts.items():
                total_counts[key] += value

    # Sort by total count descending
    file_totals.sort(reverse=True)

    # Print results
    print("Mock Definition Counts by File")
    print("=" * 80)
    print()

    for file_total, filename, counts in file_totals[:20]:
        print(f"{filename}: {file_total} mocks")
        if file_total > 20:  # Show breakdown for high-count files
            breakdown = ", ".join(f"{k}: {v}" for k, v in counts.items() if v > 0)
            print(f"  ({breakdown})")

    print()
    print("=" * 80)
    print("TOTAL MOCK DEFINITIONS:", sum(total_counts.values()))
    print()
    print("Breakdown:")
    for key, value in total_counts.items():
        if value > 0:
            print(f"  {key}: {value}")
    print()
    print(f"Files with mocks: {len(file_totals)}")


if __name__ == "__main__":
    main()

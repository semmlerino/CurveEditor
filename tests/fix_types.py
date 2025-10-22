"""
Simple script to fix type compatibility issues in the test files
"""

# Per-file type checking relaxations for test code
# Tests use mocks, fixtures, and Qt objects with incomplete type stubs
# pyright: reportAttributeAccessIssue=none
# pyright: reportArgumentType=none
# pyright: reportAny=none
# pyright: reportUnknownMemberType=none
# pyright: reportUnknownParameterType=none
# pyright: reportUnknownVariableType=none
# pyright: reportMissingParameterType=none
# pyright: reportPrivateUsage=none
# pyright: reportUnusedParameter=none
# pyright: reportUnusedCallResult=none

import re


def fix_visualization_test_file():
    file_path = "test_visualization_service.py"

    # Read the file
    with open(file_path) as file:
        content = file.read()

    # Replace integer coordinate tuples with float coordinates
    # This regex finds tuples like (10, 300, 400) and replaces with (10, 300.0, 400.0)
    pattern = r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)"
    replacement = r"(\1, \2.0, \3.0)"

    # Apply the replacement
    updated_content = re.sub(pattern, replacement, content)

    # Write back to the file
    with open(file_path, "w") as file:
        file.write(updated_content)

    print(f"Updated {file_path} with float coordinates")


if __name__ == "__main__":
    fix_visualization_test_file()

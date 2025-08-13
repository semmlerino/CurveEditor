"""
Simplified conftest.py that imports fixtures from organized modules.

This file maintains backward compatibility while delegating to domain-specific
fixture modules for better organization.
"""

import os
import sys
import warnings
from pathlib import Path

import pytest

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure Qt for headless testing
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Suppress Qt accessibility warnings
warnings.filterwarnings("ignore", category=UserWarning, message=".*accessibility.*")

# =============================================================================
# Import fixtures from organized modules
# =============================================================================

# Import all fixtures to make them available to tests


# =============================================================================
# Pytest Configuration
# =============================================================================


def pytest_configure(config: pytest.Config) -> None:
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "unit: marks unit tests")
    config.addinivalue_line("markers", "performance: marks performance tests")
    config.addinivalue_line("markers", "qt: marks tests requiring Qt")
    config.addinivalue_line("markers", "threading: marks threading tests")
    config.addinivalue_line("markers", "skip_ci: skip in CI environment")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Modify test collection to handle special cases."""
    for item in items:
        # Auto-mark Qt tests
        if "qapp" in item.fixturenames or "curve_view" in item.fixturenames:
            item.add_marker(pytest.mark.qt)

        # Auto-mark slow tests
        if "large_sample_points" in item.fixturenames or "performance_test_data" in item.fixturenames:
            item.add_marker(pytest.mark.slow)

        # Skip certain tests in CI
        if os.environ.get("CI") and "skip_ci" in item.keywords:
            item.add_marker(pytest.mark.skip(reason="Skipped in CI"))


# =============================================================================
# Test Configuration
# =============================================================================

# Configure test paths
TEST_DATA_DIR = project_root / "tests" / "test_data"
TEST_OUTPUT_DIR = project_root / "tests" / "test_output"

# Create directories if they don't exist
TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
TEST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# Clean test output directory before test run
def pytest_sessionstart(session):
    """Clean up test output directory at start of test session."""
    import shutil

    if TEST_OUTPUT_DIR.exists():
        for item in TEST_OUTPUT_DIR.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)


# =============================================================================
# Export configuration for tests
# =============================================================================


def get_test_data_path(filename: str) -> Path:
    """Get path to test data file.

    Args:
        filename: Name of test data file

    Returns:
        Path: Full path to test data file
    """
    return TEST_DATA_DIR / filename


def get_test_output_path(filename: str) -> Path:
    """Get path for test output file.

    Args:
        filename: Name of output file

    Returns:
        Path: Full path for output file
    """
    return TEST_OUTPUT_DIR / filename

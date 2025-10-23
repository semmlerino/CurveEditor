"""
Service layer test fixtures.

Contains fixtures for testing service components and managing service state.
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

import gc
import threading
from collections.abc import Generator
from types import SimpleNamespace
from typing import Any

import pytest

# Import service modules
import services


@pytest.fixture
def isolated_services() -> Generator[None, None, None]:
    """Provide isolated service instances for testing.

    This fixture ensures services are reset between tests to prevent
    state leakage.

    Yields:
        None: Services are available globally after reset
    """
    # Store original service instances
    original_services = {}

    # Get all service attributes that are instances
    for attr_name in dir(services):
        if attr_name.startswith("_") and "_service" in attr_name:
            original_services[attr_name] = getattr(services, attr_name)
            setattr(services, attr_name, None)

    # Reset service lock
    if hasattr(services, "_service_lock"):
        services._service_lock = threading.RLock()

    yield

    # Restore original services
    for attr_name, value in original_services.items():
        setattr(services, attr_name, value)


@pytest.fixture
def all_services() -> Generator[SimpleNamespace, None, None]:
    """Provide all service instances in a convenient namespace.

    This fixture consolidates the common pattern of initializing all services
    at the start of a test, reducing duplication across test files.

    Yields:
        SimpleNamespace: Object with data_service, transform_service,
                        interaction_service, and ui_service attributes
    """
    from services import get_data_service, get_interaction_service, get_transform_service, get_ui_service

    # Create namespace with all services
    services_ns = SimpleNamespace(
        data=get_data_service(),
        transform=get_transform_service(),
        interaction=get_interaction_service(),
        ui=get_ui_service(),
    )

    yield services_ns

    # Services are singletons, no cleanup needed


@pytest.fixture
def memory_monitor() -> Generator[Any, None, None]:
    """Monitor memory usage during tests.

    Useful for detecting memory leaks in service operations.

    Yields:
        MemoryMonitor: Object with methods to check memory usage
    """
    import os

    import psutil

    class MemoryMonitor:
        process: psutil.Process
        initial_memory: float

        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.initial_memory = self.get_memory_usage()

        def get_memory_usage(self):
            """Get current memory usage in MB."""
            return self.process.memory_info().rss / 1024 / 1024

        def get_memory_increase(self):
            """Get memory increase since initialization in MB."""
            return self.get_memory_usage() - self.initial_memory

        def assert_memory_usage(self, max_increase_mb: float = 50) -> None:
            """Assert memory usage hasn't increased too much."""
            increase = self.get_memory_increase()
            assert increase < max_increase_mb, f"Memory increased by {increase:.2f} MB"

        def force_gc(self):
            """Force garbage collection."""
            gc.collect()
            return self.get_memory_usage()

    monitor = MemoryMonitor()
    yield monitor

    # Force cleanup after test
    gc.collect()


@pytest.fixture
def app_state() -> Generator[Any, None, None]:
    """Provide clean ApplicationState for each test.

    This fixture ensures ApplicationState is reset between tests to prevent
    state leakage. It's the recommended way to access ApplicationState in tests.

    Yields:
        ApplicationState: Fresh application state instance

    Example:
        def test_curve_data(app_state):
            app_state.set_curve_data("test", test_data)
            assert app_state.get_curve_data("test") == test_data
    """
    from stores.application_state import get_application_state, reset_application_state

    # Reset to ensure clean state
    reset_application_state()
    state = get_application_state()

    yield state

    # Cleanup after test
    reset_application_state()


@pytest.fixture
def curve_with_data(app_state) -> Generator[Any, None, None]:
    """Provide ApplicationState with test curve data pre-loaded.

    Convenience fixture that sets up a test curve with sample data and
    sets it as the active curve. Useful for tests that need data to work with.

    Args:
        app_state: ApplicationState fixture (automatically injected)

    Yields:
        ApplicationState: State with "test_curve" loaded and active

    Example:
        def test_point_manipulation(curve_with_data):
            # Test curve already loaded with 10 points
            data = curve_with_data.get_curve_data()
            assert len(data) == 10
    """
    # Create test data: 10 points with frame, x, y, status
    test_data = [(i, float(i), float(i * 2), "normal") for i in range(10)]

    # Load into ApplicationState
    app_state.set_curve_data("test_curve", test_data)
    app_state.set_active_curve("test_curve")

    yield app_state

    # Cleanup happens in app_state fixture

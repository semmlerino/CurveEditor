"""
Service layer test fixtures.

Contains fixtures for testing service components and managing service state.
"""

import gc
import threading

import pytest

# Import service modules
import services


@pytest.fixture
def isolated_services():
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
def all_services():
    """Provide all service instances in a convenient namespace.

    This fixture consolidates the common pattern of initializing all services
    at the start of a test, reducing duplication across test files.

    Yields:
        SimpleNamespace: Object with data_service, transform_service,
                        interaction_service, and ui_service attributes
    """
    from types import SimpleNamespace

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
def memory_monitor():
    """Monitor memory usage during tests.

    Useful for detecting memory leaks in service operations.

    Yields:
        MemoryMonitor: Object with methods to check memory usage
    """
    import os

    import psutil

    class MemoryMonitor:
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

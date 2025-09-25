"""
Service layer test fixtures.

Contains fixtures for testing service components and managing service state.
"""

import gc
import threading
from unittest.mock import MagicMock, patch

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


@pytest.fixture
def mock_service_factory():
    """Factory for creating mock services with common patterns.

    Returns:
        ServiceFactory: Factory object for creating mock services
    """

    class ServiceFactory:
        @staticmethod
        def create_data_service(with_data: bool = False) -> MagicMock:
            """Create a mock data service."""
            from unittest.mock import MagicMock

            service = MagicMock()
            if with_data:
                service.get_curve_data.return_value = [
                    (1, 100.0, 200.0),
                    (2, 150.0, 250.0),
                    (3, 200.0, 300.0),
                ]
            else:
                service.get_curve_data.return_value = []

            service.is_modified = False
            service.current_file = None
            return service

        @staticmethod
        def create_transform_service(scale: float = 1.0, offset_x: float = 0, offset_y: float = 0) -> MagicMock:
            """Create a mock transform service."""
            from unittest.mock import MagicMock

            service = MagicMock()
            transform = MagicMock()
            transform.scale = scale
            transform.offset_x = offset_x
            transform.offset_y = offset_y
            transform.data_to_screen = lambda x, y: (x * scale + offset_x, y * scale + offset_y)
            transform.screen_to_data = lambda x, y: ((x - offset_x) / scale, (y - offset_y) / scale)

            service.get_transform.return_value = transform
            return service

        @staticmethod
        def create_interaction_service(selected_indices: list[int] | None = None) -> MagicMock:
            """Create a mock interaction service."""
            from unittest.mock import MagicMock

            service = MagicMock()
            service.selected_indices = selected_indices or set()
            service.is_dragging = False
            service.drag_start_pos = None
            return service

        @staticmethod
        def create_ui_service():
            """Create a mock UI service."""
            from unittest.mock import MagicMock

            service = MagicMock()
            service.status_message = ""
            service.progress_value = 0
            service.is_busy = False
            return service

    return ServiceFactory()


@pytest.fixture
def service_patch():
    """Patch service getters for testing.

    Yields:
        ServicePatcher: Object with methods to patch services
    """

    class ServicePatcher:
        def __init__(self):
            self.patches = []

        def patch_data_service(self, mock_service):
            """Patch the data service getter."""
            p = patch("services.get_data_service", return_value=mock_service)
            self.patches.append(p)
            return p.start()

        def patch_transform_service(self, mock_service):
            """Patch the transform service getter."""
            p = patch("services.get_transform_service", return_value=mock_service)
            self.patches.append(p)
            return p.start()

        def patch_interaction_service(self, mock_service):
            """Patch the interaction service getter."""
            p = patch("services.get_interaction_service", return_value=mock_service)
            self.patches.append(p)
            return p.start()

        def patch_ui_service(self, mock_service):
            """Patch the UI service getter."""
            p = patch("services.get_ui_service", return_value=mock_service)
            self.patches.append(p)
            return p.start()

        def stop_all(self):
            """Stop all patches."""
            for p in self.patches:
                p.stop()
            self.patches.clear()

    patcher = ServicePatcher()
    yield patcher
    patcher.stop_all()


@pytest.fixture
def thread_safe_service_test():
    """Ensure thread-safe testing of services.

    This fixture sets up proper locking for service tests.

    Yields:
        ThreadSafetyChecker: Object for checking thread safety
    """
    from concurrent.futures import ThreadPoolExecutor

    class ThreadSafetyChecker:
        def __init__(self):
            self.errors: list[str] = []
            self.lock = threading.Lock()

        def run_concurrent(self, func, num_threads=10, num_iterations=100):
            """Run a function concurrently in multiple threads."""

            def worker():
                try:
                    for _ in range(num_iterations):
                        func()
                except Exception as e:
                    with self.lock:
                        self.errors.append(str(e))

            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(worker) for _ in range(num_threads)]
                for future in futures:
                    future.result()

            assert not self.errors, f"Thread safety errors: {self.errors}"

        def check_singleton(self, getter_func):
            """Check that a service getter returns singleton."""
            instances = set()

            def collect_instance():
                instances.add(id(getter_func()))

            self.run_concurrent(collect_instance, num_threads=20, num_iterations=10)
            assert len(instances) == 1, "Service is not a singleton"

    return ThreadSafetyChecker()

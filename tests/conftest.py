#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for all tests.

This module imports fixtures from the organized fixtures package
to make them available to all tests.
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

from collections.abc import Generator

import pytest

# import services  # Temporarily disabled to debug import issue
from core.config import reset_config

# Import all fixtures from the fixtures package
from tests.fixtures import (
    all_services,
    curve_view_widget,
    file_load_signals,
    file_load_worker,
    # Service fixtures
    isolated_services,
    keyframe_curve_data,
    large_sample_points,
    lazy_mock_main_window,
    memory_monitor,
    # Mock fixtures
    mock_curve_view,
    mock_curve_view_with_selection,
    mock_main_window,
    mock_main_window_with_data,
    # Production fixtures
    production_widget_factory,
    protocol_compliant_mock_curve_view,
    protocol_compliant_mock_main_window,
    # Qt fixtures
    qapp,
    qt_cleanup,
    safe_test_data_factory,
    # Data fixtures
    sample_curve_data,
    sample_points,
    ui_file_load_signals,
    ui_file_load_worker,
    user_interaction,
)


# Comprehensive service reset fixture
@pytest.fixture(autouse=True)
def reset_all_services() -> Generator[None, None, None]:
    """Reset ALL service state between tests to ensure complete isolation.

    This fixture is auto-used for all tests to prevent state leakage,
    especially for Y-flip tests that fail due to service singleton persistence.

    Also sets a default _total_frames to allow frame navigation in tests.
    """
    # BEFORE test: Set default total frames for frame navigation
    from stores.application_state import get_application_state
    app_state = get_application_state()
    # Set generous default that allows most tests to navigate freely
    app_state.set_image_files(["dummy.png"] * 10000)

    yield  # Run the test

    # After test completes, reset everything
    try:
        # Import services lazily to avoid startup issues
        import services

        # 1. FIRST clear service caches while they still exist
        if hasattr(services, "_transform_service") and services._transform_service is not None:
            clear_cache_method = getattr(services._transform_service, "clear_cache", None)
            if clear_cache_method is not None:
                clear_cache_method()

        if hasattr(services, "_data_service") and services._data_service is not None:
            clear_cache_method = getattr(services._data_service, "clear_cache", None)
            if clear_cache_method is not None:
                clear_cache_method()
            # CRITICAL: Stop SafeImageCacheManager preload worker thread before service reset
            # Without cleanup(), the QThread worker remains running and causes Fatal Python abort
            # during thread.join() in background thread cleanup
            if hasattr(services._data_service, "_safe_image_cache") and services._data_service._safe_image_cache is not None:
                cleanup_method = getattr(services._data_service._safe_image_cache, "cleanup", None)
                if cleanup_method is not None:
                    cleanup_method()

        if hasattr(services, "_interaction_service") and services._interaction_service is not None:
            clear_cache_method = getattr(services._interaction_service, "clear_cache", None)
            if clear_cache_method is not None:
                clear_cache_method()

        # 2. THEN clear all service singletons
        if hasattr(services, "_data_service"):
            services._data_service = None
        if hasattr(services, "_interaction_service"):
            services._interaction_service = None
        if hasattr(services, "_transform_service"):
            services._transform_service = None
        if hasattr(services, "_ui_service"):
            services._ui_service = None

        # 2.3. CRITICAL: Reset ApplicationState singleton before StoreManager
        # ApplicationState must be reset before StoreManager to ensure clean state
        try:
            from stores.application_state import reset_application_state

            reset_application_state()
        except Exception:
            pass  # ApplicationState might not be initialized

        # 2.5. CRITICAL: Reset StoreManager singleton to prevent QObject accumulation
        # StoreManager creates orphaned QObjects (CurveDataStore, FrameStore) that
        # accumulate in session-scope QApplication causing segfaults after 850+ tests
        try:
            from stores.store_manager import StoreManager

            StoreManager.reset()
        except Exception:
            pass  # Store manager might not be initialized

        # 3. Reset global config
        reset_config()

        # 4. Clear any cached imports for coordinate systems
        import sys

        modules_to_clear = ["core.coordinate_system", "core.curve_data", "core.coordinate_detector"]
        for module in modules_to_clear:
            if module in sys.modules:
                # Clear module-level caches if they exist
                mod = sys.modules[module]
                coordinate_systems = getattr(mod, "COORDINATE_SYSTEMS", None)
                if coordinate_systems is not None:
                    # Re-initialize coordinate systems to defaults
                    from core.coordinate_system import COORDINATE_SYSTEMS

                    COORDINATE_SYSTEMS.clear()
                    COORDINATE_SYSTEMS.update(
                        {
                            "qt": mod.CoordinateMetadata(
                                system=mod.CoordinateSystem.QT_SCREEN,
                                origin=mod.CoordinateOrigin.TOP_LEFT,
                                width=1920,
                                height=1080,
                            ),
                            "3de_720p": mod.CoordinateMetadata(
                                system=mod.CoordinateSystem.THREE_DE_EQUALIZER,
                                origin=mod.CoordinateOrigin.BOTTOM_LEFT,
                                width=1280,
                                height=720,
                            ),
                            "3de_1080p": mod.CoordinateMetadata(
                                system=mod.CoordinateSystem.THREE_DE_EQUALIZER,
                                origin=mod.CoordinateOrigin.BOTTOM_LEFT,
                                width=1920,
                                height=1080,
                            ),
                            "nuke_hd": mod.CoordinateMetadata(
                                system=mod.CoordinateSystem.NUKE,
                                origin=mod.CoordinateOrigin.BOTTOM_LEFT,
                                width=1920,
                                height=1080,
                            ),
                            "internal": mod.CoordinateMetadata(
                                system=mod.CoordinateSystem.CURVE_EDITOR_INTERNAL,
                                origin=mod.CoordinateOrigin.TOP_LEFT,
                                width=1920,
                                height=1080,
                            ),
                        }
                    )

        # 5. CRITICAL: Check for background threads before processEvents to prevent deadlock
        # Only log warnings - don't block test execution with join()
        try:
            import logging
            import threading

            # Get all active threads (excluding main thread and daemon threads)
            active_threads = [
                t for t in threading.enumerate() if t != threading.main_thread() and not t.daemon and t.is_alive()
            ]

            if active_threads:
                logger = logging.getLogger(__name__)
                # Try very brief join (0.01s = 10ms) but don't block if thread won't stop
                for thread in active_threads:
                    thread.join(timeout=0.01)

                # Log remaining threads for debugging but continue
                still_alive = [t for t in active_threads if t.is_alive()]
                if still_alive:
                    logger.debug(f"Background threads still running: {[t.name for t in still_alive]}")
        except Exception:
            pass

        # 6. Process pending Qt events to clean up QObjects
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                # Process deleteLater() calls
                app.processEvents()
                # Additional event processing for nested deletions
                app.processEvents()
        except Exception:
            pass

        # 7. Force Python garbage collection to trigger __del__ for MainWindow cleanup
        # CRITICAL: MainWindow.__del__ removes global event filters.
        # Without gc.collect(), event filters accumulate causing timeout after 1580+ tests.
        import gc

        gc.collect()  # Force garbage collection to call __del__
        # Process events again after gc to handle any Qt cleanup from __del__
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                app.processEvents()
        except Exception:
            pass

    except Exception as e:
        # Log but don't fail test due to cleanup issues
        import logging

        logging.warning(f"Service reset warning: {e}")


def pytest_collection_modifyitems(items):
    """Auto-tag tests based on fixtures used.

    Implements pytest collection hook to automatically mark tests:
    - 'production': Tests using production workflow fixtures
    - 'unit': Tests without Qt dependencies (fast unit tests)

    This enables filtering tests by type without manual markers.
    """
    for item in items:
        # Auto-tag production workflow tests
        production_fixtures = {"production_widget_factory", "user_interaction"}
        if any(f in item.fixturenames for f in production_fixtures):
            item.add_marker(pytest.mark.production)

        # Auto-tag unit tests (no Qt widgets)
        elif "qtbot" not in item.fixturenames and "qapp" not in item.fixturenames:
            item.add_marker(pytest.mark.unit)


# Re-export all fixtures so pytest can find them
__all__ = [
    "all_services",
    "curve_view_widget",
    "file_load_signals",
    "file_load_worker",
    "isolated_services",
    "keyframe_curve_data",
    "large_sample_points",
    "lazy_mock_main_window",
    "memory_monitor",
    "mock_curve_view",
    "mock_curve_view_with_selection",
    "mock_main_window",
    "mock_main_window_with_data",
    "production_widget_factory",
    "protocol_compliant_mock_curve_view",
    "protocol_compliant_mock_main_window",
    "qapp",
    "qt_cleanup",
    "safe_test_data_factory",
    "sample_curve_data",
    "sample_points",
    "ui_file_load_signals",
    "ui_file_load_worker",
    "user_interaction",
]

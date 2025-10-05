#!/usr/bin/env python3
"""
Pytest configuration and shared fixtures for all tests.

This module imports fixtures from the organized fixtures package
to make them available to all tests.
"""

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
    protocol_compliant_mock_curve_view,
    protocol_compliant_mock_main_window,
    # Qt fixtures
    qapp,
    qt_cleanup,
    # Data fixtures
    sample_curve_data,
    sample_points,
    ui_file_load_signals,
    ui_file_load_worker,
)


# Comprehensive service reset fixture
@pytest.fixture(autouse=True)
def reset_all_services() -> Generator[None, None, None]:
    """Reset ALL service state between tests to ensure complete isolation.

    This fixture is auto-used for all tests to prevent state leakage,
    especially for Y-flip tests that fail due to service singleton persistence.
    """
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

        # 5. Process pending Qt events to clean up QObjects
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

        # 6. Force Python garbage collection to trigger __del__ for MainWindow cleanup
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


# Re-export all fixtures so pytest can find them
__all__ = [
    # Data fixtures
    "sample_curve_data",
    "keyframe_curve_data",
    "sample_points",
    "large_sample_points",
    # Mock fixtures
    "mock_curve_view",
    "mock_curve_view_with_selection",
    "mock_main_window",
    "mock_main_window_with_data",
    "protocol_compliant_mock_curve_view",
    "protocol_compliant_mock_main_window",
    "lazy_mock_main_window",
    # Qt fixtures
    "qapp",
    "qt_cleanup",
    "curve_view_widget",
    "file_load_signals",
    "file_load_worker",
    "ui_file_load_signals",
    "ui_file_load_worker",
    # Service fixtures
    "all_services",
    "isolated_services",
    "memory_monitor",
]

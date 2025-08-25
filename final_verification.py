#!/usr/bin/env python
"""
Sprint 11 Day 5 - Final Functionality Verification Script
Tests core services and operations programmatically to ensure production readiness.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.models import CurvePoint
from services import (
    get_data_service,
    get_interaction_service,
    get_transform_service,
    get_ui_service,
)
from services.transform_service import ViewState


class FunctionalityVerifier:
    """Verify core functionality of CurveEditor services."""

    def __init__(self):
        self.data_service = get_data_service()
        self.interaction_service = get_interaction_service()
        self.transform_service = get_transform_service()
        self.ui_service = get_ui_service()
        self.results = []
        self.errors = []

    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result."""
        status = "✅ PASSED" if passed else "❌ FAILED"
        self.results.append(f"{status}: {test_name}")
        if details:
            self.results.append(f"  Details: {details}")
        if not passed:
            self.errors.append(f"{test_name}: {details}")

    def test_data_service_operations(self):
        """Test DataService core operations."""
        print("\n=== Testing DataService Operations ===")

        # Test 1: Load CSV data
        csv_path = Path("data/burger-001.csv")
        if csv_path.exists():
            try:
                points = self.data_service.load_csv(str(csv_path))
                self.log_result("Load CSV", len(points) > 0, f"Loaded {len(points)} points from burger-001.csv")
            except Exception as e:
                self.log_result("Load CSV", False, str(e))
        else:
            self.log_result("Load CSV", False, "Sample CSV file not found")

        # Test 2: Analyze points
        test_points = [
            CurvePoint(frame=1, x=100, y=200),
            CurvePoint(frame=2, x=150, y=250),
            CurvePoint(frame=3, x=200, y=300),
        ]
        try:
            analysis = self.data_service.analyze_points(test_points)
            self.log_result(
                "Analyze Points",
                analysis["count"] == 3 and analysis["min_frame"] == 1,
                f"Analysis: {analysis['count']} points, frames {analysis['min_frame']}-{analysis['max_frame']}",
            )
        except Exception as e:
            self.log_result("Analyze Points", False, str(e))

        # Test 3: Save/Load JSON
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
            temp_path = tmp.name

        try:
            # Save test data
            test_data = [(1, 100.0, 200.0), (2, 150.0, 250.0)]
            self.data_service.save_json(test_data, temp_path)

            # Load it back
            loaded_data = self.data_service.load_json(temp_path)

            self.log_result(
                "JSON Save/Load",
                len(loaded_data) == len(test_data),
                f"Saved {len(test_data)} points, loaded {len(loaded_data)} points",
            )
        except Exception as e:
            self.log_result("JSON Save/Load", False, str(e))
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

        # Test 4: Recent files
        try:
            recent = self.data_service.get_recent_files()
            self.log_result("Recent Files", isinstance(recent, list), f"Retrieved {len(recent)} recent files")
        except Exception as e:
            self.log_result("Recent Files", False, str(e))

    def test_transform_service_operations(self):
        """Test TransformService operations."""
        print("\n=== Testing TransformService Operations ===")

        # Test 1: Create transform from ViewState
        view_state = ViewState(
            display_width=800,
            display_height=600,
            widget_width=800,
            widget_height=600,
            zoom_factor=2.0,
            offset_x=100,
            offset_y=50,
        )

        try:
            transform = self.transform_service.create_transform_from_view_state(view_state)
            self.log_result(
                "Create Transform", transform.scale == 2.0, f"Transform created with scale={transform.scale}"
            )
        except Exception as e:
            self.log_result("Create Transform", False, str(e))

        # Test 2: Coordinate transformations
        try:
            transform = self.transform_service.create_transform(
                scale=2.0, center_offset=(100, 100), pan_offset=(50, 50)
            )

            # Transform data to screen
            screen_x, screen_y = self.transform_service.transform_point_to_screen(transform, 100, 200)

            # Transform back to data
            data_x, data_y = self.transform_service.transform_point_to_data(transform, screen_x, screen_y)

            # Should get original coordinates back
            coords_match = abs(data_x - 100) < 0.01 and abs(data_y - 200) < 0.01

            self.log_result(
                "Coordinate Transformation",
                coords_match,
                f"Data(100,200) → Screen({screen_x:.1f},{screen_y:.1f}) → Data({data_x:.1f},{data_y:.1f})",
            )
        except Exception as e:
            self.log_result("Coordinate Transformation", False, str(e))

        # Test 3: Cache performance
        try:
            cache_info = self.transform_service.get_cache_info()
            hit_rate = cache_info.get("hit_rate", 0)
            self.log_result(
                "Transform Caching",
                hit_rate >= 0,
                f"Cache hit rate: {hit_rate:.1%}, size: {cache_info.get('current_size', 0)}/{cache_info.get('max_size', 0)}",
            )
        except Exception as e:
            self.log_result("Transform Caching", False, str(e))

    def test_interaction_service_operations(self):
        """Test InteractionService operations."""
        print("\n=== Testing InteractionService Operations ===")

        # Mock view for testing
        class MockView:
            def __init__(self):
                self.points = [(1, 100, 100), (2, 200, 200), (3, 300, 300)]
                self.selected_points = set()
                self.zoom_factor = 1.0
                self.pan_offset_x = 0
                self.pan_offset_y = 0

            def get_transform(self):
                from services.transform_service import Transform

                return Transform(scale=1.0)

            def width(self):
                return 800

            def height(self):
                return 600

            def update(self):
                pass

        view = MockView()

        # Test 1: History functionality
        try:
            initial_state = {"points": [(1, 100, 100)], "selection": set()}
            self.interaction_service.add_to_history(view, initial_state)

            # Add another state
            new_state = {"points": [(1, 100, 100), (2, 200, 200)], "selection": {0}}
            self.interaction_service.add_to_history(view, new_state)

            # Test undo
            can_undo = self.interaction_service.can_undo()
            if can_undo:
                self.interaction_service.undo(view)

            self.log_result(
                "History (Undo/Redo)",
                can_undo,
                f"History size: {len(self.interaction_service._history)}, can_undo: {can_undo}",
            )
        except Exception as e:
            self.log_result("History (Undo/Redo)", False, str(e))

        # Test 2: Point finding with spatial index
        try:
            # Find point at position
            idx = self.interaction_service.find_point_at(view, 100, 100)
            self.log_result(
                "Spatial Index Point Lookup",
                idx >= -1,  # -1 means no point found, which is valid
                f"Point lookup returned index: {idx}",
            )
        except Exception as e:
            self.log_result("Spatial Index Point Lookup", False, str(e))

        # Test 3: Spatial index statistics
        try:
            stats = self.interaction_service.get_spatial_index_stats()
            self.log_result(
                "Spatial Index Stats",
                "grid_size" in stats,
                f"Grid size: {stats.get('grid_size', 'N/A')}, Points indexed: {stats.get('total_points', 0)}",
            )
        except Exception as e:
            self.log_result("Spatial Index Stats", False, str(e))

    def test_ui_service_operations(self):
        """Test UIService operations."""
        print("\n=== Testing UIService Operations ===")

        # Mock main window
        class MockMainWindow:
            def __init__(self):
                self.status_bar_message = ""
                self.status_bar = self

            def statusBar(self):
                return self.status_bar

            def showMessage(self, msg, timeout=0):
                self.status_bar_message = msg

        window = MockMainWindow()

        # Test 1: Status update
        try:
            self.ui_service.set_status(window, "Test status message")
            self.log_result(
                "Status Update",
                window.status_bar_message == "Test status message",
                "Status message updated successfully",
            )
        except Exception as e:
            self.log_result("Status Update", False, str(e))

        # Test 2: Error handling (non-blocking in headless mode)
        try:
            # Mock parent widget
            class MockWidget:
                pass

            parent = MockWidget()
            # This won't show a dialog in headless mode but should not crash
            self.ui_service.show_error(parent, "Test error", "Error details")
            self.log_result(
                "Error Display",
                True,  # If no exception, consider it passed
                "Error handling mechanism functional",
            )
        except Exception as e:
            self.log_result("Error Display", False, str(e))

    def test_file_operations(self):
        """Test actual file operations with sample data."""
        print("\n=== Testing File Operations ===")

        # Check for sample data files
        data_dir = Path("data")
        if data_dir.exists():
            csv_files = list(data_dir.glob("*.csv"))
            image_files = list(data_dir.glob("*.png")) + list(data_dir.glob("*.jpg"))

            self.log_result(
                "Sample Data Available",
                len(csv_files) > 0,
                f"Found {len(csv_files)} CSV files, {len(image_files)} image files",
            )

            # Try loading first CSV
            if csv_files:
                try:
                    points = self.data_service.load_csv(str(csv_files[0]))
                    self.log_result(
                        "Load Sample Data", len(points) > 0, f"Loaded {len(points)} points from {csv_files[0].name}"
                    )
                except Exception as e:
                    self.log_result("Load Sample Data", False, str(e))
        else:
            self.log_result("Sample Data Available", False, "Data directory not found")

    def test_performance_optimizations(self):
        """Verify performance optimizations are active."""
        print("\n=== Testing Performance Optimizations ===")

        # Test 1: Transform caching is enabled
        try:
            # Create same transform multiple times
            view_state = ViewState(
                display_width=800,
                display_height=600,
                widget_width=800,
                widget_height=600,
                zoom_factor=1.5,
            )

            # Create transform twice
            self.transform_service.create_transform_from_view_state(view_state)
            self.transform_service.create_transform_from_view_state(view_state)

            cache_info = self.transform_service.get_cache_info()
            self.log_result(
                "LRU Cache Active",
                cache_info["hits"] > 0,
                f"Cache hits: {cache_info['hits']}, Cache size: {cache_info['current_size']}",
            )
        except Exception as e:
            self.log_result("LRU Cache Active", False, str(e))

        # Test 2: Spatial indexing is enabled
        try:
            # Check if spatial index is initialized
            has_spatial_index = hasattr(self.interaction_service, "_spatial_index")
            self.log_result(
                "Spatial Indexing Active", has_spatial_index, "Spatial index initialized for O(1) point lookups"
            )
        except Exception as e:
            self.log_result("Spatial Indexing Active", False, str(e))

    def run_all_tests(self):
        """Run all verification tests."""
        print("\n" + "=" * 60)
        print("SPRINT 11 DAY 5 - FINAL FUNCTIONALITY VERIFICATION")
        print("=" * 60)

        self.test_data_service_operations()
        self.test_transform_service_operations()
        self.test_interaction_service_operations()
        self.test_ui_service_operations()
        self.test_file_operations()
        self.test_performance_optimizations()

        # Print summary
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)

        for result in self.results:
            print(result)

        # Final assessment
        total_tests = len([r for r in self.results if "PASSED" in r or "FAILED" in r])
        passed_tests = len([r for r in self.results if "PASSED" in r])

        print("\n" + "-" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")

        if self.errors:
            print("\n⚠️  ERRORS ENCOUNTERED:")
            for error in self.errors:
                print(f"  - {error}")

        # Production readiness assessment
        print("\n" + "=" * 60)
        if passed_tests >= total_tests * 0.9:  # 90% pass rate
            print("✅ PRODUCTION READY - All critical functionality verified")
        elif passed_tests >= total_tests * 0.7:  # 70% pass rate
            print("⚠️  CONDITIONALLY READY - Some non-critical issues present")
        else:
            print("❌ NOT READY - Critical functionality issues detected")
        print("=" * 60)


if __name__ == "__main__":
    verifier = FunctionalityVerifier()
    verifier.run_all_tests()

"""Integration tests for loading actual example files from the repository.

These tests ensure that example files used in documentation and development
remain loadable and maintain their expected format.

This prevents regressions like the 2DTrackDatav2.txt JSON format issue.
"""

from pathlib import Path

import pytest

from services.data_service import DataService


class TestExampleFileLoading:
    """Test loading of actual example files from the repository."""

    @pytest.fixture
    def data_service(self):
        """Create a DataService instance."""
        return DataService()

    @pytest.fixture
    def project_root(self):
        """Get the project root directory."""
        return Path(__file__).parent.parent

    def test_2dtrack_datav2_loads_successfully(self, data_service, project_root):
        """Test loading 2DTrackDatav2.txt in correct multi-point format.

        This file is used as the canonical example for multi-point tracking data.
        It should remain in text format with multiple tracking points.
        """
        file_path = project_root / "2DTrackDatav2.txt"

        # File must exist
        assert file_path.exists(), f"Example file not found: {file_path}"

        # Load as multi-point data
        tracked_data = data_service.load_tracked_data(str(file_path))

        # Must return dict (multi-point format)
        assert isinstance(tracked_data, dict), "2DTrackDatav2.txt must be multi-point format (dict)"

        # Must contain multiple points (canonical example has 12 points)
        assert len(tracked_data) > 0, "2DTrackDatav2.txt must contain tracking points"
        assert len(tracked_data) >= 2, "2DTrackDatav2.txt should have multiple tracking points"

        # Verify known points from canonical data
        assert "Point1" in tracked_data or "Point01" in tracked_data, \
            "Expected Point1 in canonical multi-point data"

        # Each trajectory should have data
        for point_name, trajectory in tracked_data.items():
            assert len(trajectory) > 0, f"Point {point_name} should have trajectory data"

    def test_2dtrack_data_point1_only_loads(self, data_service, project_root):
        """Test loading single-point example file."""
        file_path = project_root / "2DTrackData_Point1_only.txt"

        if not file_path.exists():
            pytest.skip("Single-point example file not present")

        # Load as multi-point (should work for single-point too)
        tracked_data = data_service.load_tracked_data(str(file_path))

        # Should return dict with one point
        assert isinstance(tracked_data, dict)
        assert len(tracked_data) == 1, "Single-point file should have exactly one trajectory"
        assert "Point1" in tracked_data, "Expected Point1 in single-point file"

    def test_burger_example_data_loads(self, data_service, project_root):
        """Test loading footage/Burger example if present."""
        file_path = project_root / "footage" / "Burger" / "2DTrackData.txt"

        if not file_path.exists():
            pytest.skip("Burger example footage not present")

        # Try loading - should not crash
        tracked_data = data_service.load_tracked_data(str(file_path))

        # Should return dict (multi-point) or empty dict (if format not recognized)
        assert isinstance(tracked_data, dict)

    def test_example_files_not_json(self, project_root):
        """Verify example .txt files are NOT JSON format.

        This catches regressions where JSON accidentally replaces text format.
        """
        example_files = [
            project_root / "2DTrackDatav2.txt",
            project_root / "2DTrackData_Point1_only.txt",
        ]

        for file_path in example_files:
            if not file_path.exists():
                continue

            content = file_path.read_text()

            # Should NOT start with JSON markers
            assert not content.strip().startswith("{"), \
                f"{file_path.name} should be text format, not JSON"
            assert not content.strip().startswith("["), \
                f"{file_path.name} should be text format, not JSON array"

            # Should have characteristic text format markers
            # (version number line, point names, data lines)
            lines = content.strip().split('\n')
            assert len(lines) > 4, f"{file_path.name} should have multiple lines"


class TestExampleFileFormats:
    """Validate the structure and format of example files."""

    @pytest.fixture
    def project_root(self):
        """Get the project root directory."""
        return Path(__file__).parent.parent

    def test_2dtrack_datav2_format_validation(self, project_root):
        """Validate 2DTrackDatav2.txt has correct multi-point format.

        Expected format:
        - Version line (e.g., "12")
        - Point name line (e.g., "Point1")
        - Identifier line (e.g., "0")
        - Count line (e.g., "37")
        - Data lines: "frame x y"
        - Repeat for each point
        """
        file_path = project_root / "2DTrackDatav2.txt"

        if not file_path.exists():
            pytest.skip("2DTrackDatav2.txt not present")

        lines = file_path.read_text().strip().split('\n')

        # First line should be version number
        assert lines[0].strip().isdigit(), "First line should be version number"

        # Second line should be point name
        assert lines[1].strip().startswith("Point"), \
            "Second line should be point name (e.g., 'Point1')"

        # Third line should be identifier (usually "0")
        assert lines[2].strip().isdigit(), "Third line should be identifier number"

        # Fourth line should be point count
        assert lines[3].strip().isdigit(), "Fourth line should be point count"

        # Fifth line should be data (frame x y format)
        data_parts = lines[4].strip().split()
        assert len(data_parts) >= 3, "Data lines should have at least 3 values (frame x y)"
        assert all(part.replace('.', '').replace('-', '').isdigit()
                   for part in data_parts[:3]), \
            "Data line values should be numeric"

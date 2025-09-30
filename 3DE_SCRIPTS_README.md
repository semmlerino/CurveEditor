# 3DEqualizer Python Scripts

These scripts are designed to run **inside** 3DEqualizer's Python console to analyze tracking data and coordinate systems.

## Scripts

1. **3de_tracking_analyzer.py** - Analyzes your tracking project
   - Cameras, point groups, tracking points
   - Coordinate system details
   - Export options

2. **3de_coordinate_test.py** - Creates test points
   - Places points at known positions
   - Tests coordinate conversions
   - Demonstrates multi-frame tracking

3. **3de_export_formats.py** - Export format demonstrations
   - Custom 2D track format
   - JSON export
   - Nuke/After Effects comparisons

## Usage

1. Open your tracked project in 3DEqualizer
2. Open Python console (Window → Python Console)
3. Copy and paste script content OR use File → Run Script File
4. Review output in console
5. **Output files are automatically saved** with timestamps:
   - Saved to project directory if available
   - Otherwise saved to system temp directory (e.g., `C:\Users\Username\AppData\Local\Temp\` on Windows)
   - Files named: `3de_tracking_analysis_YYYYMMDD_HHMMSS.txt`
   - Both console and file output provided

## Requirements

- 3DEqualizer4 R3b4 or later (Python support)
- Python 2.x (3DE uses Python 2, not Python 3)

## API Notes

Based on 3DEqualizer4 Release 8.0 Python API (py_doc_r8.0.txt):

**Verified functions that exist:**
- Point groups: `tde4.getPGroupList(0)` where 0=all, 1=selected
- Points: `tde4.getPointList(pg, 0)` where 0=all, 1=selected
- Cameras: `tde4.getCameraList(0)` where 0=all, 1=selected
- Point validity: `tde4.isPointPos2DValid(pg, point, cam, frame)` returns 0 or 1
- Point status: `tde4.setPointStatus2D(pg, point, cam, frame, status)`
  - Status values: "POINT_TRACKED", "POINT_KEYFRAME", "POINT_INTERPOLATED", "POINT_OBSOLETE"
- Colors: `tde4.getPointColor2D(pg, point)` and `tde4.setPointColor2D(pg, point, color_index)`
  - Use color indices (0-7) not RGB values
- Lens info: `tde4.getLensFBackWidth(lens_id)` and `tde4.getLensFBackHeight(lens_id)`

**Functions that DON'T exist in R8.0:**
- ~~`tde4.getCameraFilmbackWidth()`~~ - Use `getLensFBackWidth()` with lens_id
- ~~`tde4.getCameraFilmbackHeight()`~~ - Use `getLensFBackHeight()` with lens_id
- ~~`tde4.getPointPosition2DRaw()`~~ - Does not exist
- ~~`tde4.getProjectUnit()`~~ - Does not exist
- ~~`tde4.setPointCalcMode2D()`~~ - Use `setPointCalcMode()` without "2D"

## Output Files

Each script creates a timestamped output file containing all analysis results:

- **3de_tracking_analyzer.py** → `3de_tracking_analysis_YYYYMMDD_HHMMSS.txt`
  - Complete project analysis
  - Camera settings, point groups, tracking points
  - Export format documentation

- **3de_coordinate_test.py** → `3de_coordinate_test_YYYYMMDD_HHMMSS.txt`
  - Test point creation results
  - Coordinate conversion tests
  - Multi-frame tracking data

- **3de_export_formats.py** → `3de_export_analysis_YYYYMMDD_HHMMSS.txt`
  - Export format comparisons
  - Sample data in different formats
  - Format conversion formulas

Files are saved to:
1. Project directory (if available)
2. System temp directory (fallback)
   - Windows: `%TEMP%` (e.g., `C:\Users\Username\AppData\Local\Temp\`)
   - Linux: `/tmp/`
   - macOS: `/var/folders/.../`

## Coordinate System

3DEqualizer uses:
- Origin: Bottom-left (0,0)
- Y-axis: Increases upward
- Units: Pixels
- To convert to Qt/screen: `y_screen = height - y_3de`

#!/usr/bin/env python
"""CSV and Excel export functionality for curve data.

This module provides functions to export curve tracking data to CSV and Excel formats.
The Excel export functionality requires the optional xlsxwriter dependency.
"""

from core.logger_utils import get_logger
from core.path_security import PathSecurityError, validate_file_path

logger = get_logger("csv_export")


def export_to_csv(
    file_path: str, curve_data: list[tuple[int, float, float]], include_header: bool = True, delimiter: str = ","
) -> bool:
    """Export tracking data to CSV format.

    Args:
        file_path: Path to save the CSV file
        curve_data: list of (frame, x, y) tuples
        include_header: Whether to include a header row
        delimiter: CSV delimiter character

    Returns:
        True if export was successful, False otherwise
    """
    # Validate file path for security
    try:
        validated_path = validate_file_path(
            file_path, operation_type="export_files", allow_create=True, require_exists=False
        )
        file_path = str(validated_path)
    except PathSecurityError as e:
        logger.error(f"Security violation: {e}")
        return False

    if not curve_data:
        logger.warning("No curve data to export")
        return False

    try:
        with open(file_path, "w") as f:
            # Write header
            if include_header:
                _ = f.write(f"Frame{delimiter}X{delimiter}Y\n")

            # Write data
            for frame, x, y in sorted(curve_data, key=lambda p: p[0]):
                _ = f.write(f"{frame}{delimiter}{x}{delimiter}{y}\n")

        logger.info(f"Successfully exported {len(curve_data)} points to CSV: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error exporting to CSV: {str(e)}")
        return False


def export_to_excel(file_path: str, curve_data: list[tuple[int, float, float]], sheet_name: str = "Track Data") -> bool:
    """Export tracking data to Excel format.

    Note: This function requires the xlsxwriter module to be installed.
    If xlsxwriter is not available, the function will return False with an error message.

    Args:
        file_path: Path to save the Excel file
        curve_data: list of (frame, x, y) tuples
        sheet_name: Name of the worksheet

    Returns:
        True if export was successful, False otherwise
    """
    # Validate file path for security
    try:
        validated_path = validate_file_path(
            file_path, operation_type="export_files", allow_create=True, require_exists=False
        )
        file_path = str(validated_path)
    except PathSecurityError as e:
        logger.error(f"Security violation: {e}")
        return False

    if not curve_data:
        logger.warning("No curve data to export")
        return False

    try:
        import xlsxwriter  # type: ignore[import-untyped,import-not-found] # pyright: ignore[reportMissingImports]
    except ImportError:
        logger.warning("xlsxwriter module not found. Excel export functionality is disabled.")
        logger.info("To enable Excel export, install xlsxwriter: pip install xlsxwriter")
        return False

    try:
        workbook = xlsxwriter.Workbook(file_path)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]
        worksheet = workbook.add_worksheet(sheet_name)  # pyright: ignore[reportUnknownMemberType,reportUnknownVariableType]

        # Add header
        worksheet.write(0, 0, "Frame")  # pyright: ignore[reportUnknownMemberType]
        worksheet.write(0, 1, "X")  # pyright: ignore[reportUnknownMemberType]
        worksheet.write(0, 2, "Y")  # pyright: ignore[reportUnknownMemberType]

        # Add data
        sorted_data = sorted(curve_data, key=lambda p: p[0])
        for i, (frame, x, y) in enumerate(sorted_data):
            worksheet.write(i + 1, 0, frame)  # pyright: ignore[reportUnknownMemberType]
            worksheet.write(i + 1, 1, x)  # pyright: ignore[reportUnknownMemberType]
            worksheet.write(i + 1, 2, y)  # pyright: ignore[reportUnknownMemberType]

        workbook.close()  # pyright: ignore[reportUnknownMemberType]
        logger.info(f"Successfully exported {len(curve_data)} points to Excel: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        return False

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CSV and Excel export functionality for curve data.

This module provides functions to export curve tracking data to CSV and Excel formats.
The Excel export functionality requires the optional xlsxwriter dependency.
"""

from typing import List, Tuple
from services.logging_service import LoggingService

logger = LoggingService.get_logger("csv_export")


def export_to_csv(file_path: str, curve_data: List[Tuple[int, float, float]], include_header: bool = True, delimiter: str = ',') -> bool:
    """Export tracking data to CSV format.

    Args:
        file_path: Path to save the CSV file
        curve_data: List of (frame, x, y) tuples
        include_header: Whether to include a header row
        delimiter: CSV delimiter character

    Returns:
        True if export was successful, False otherwise
    """
    if not curve_data:
        logger.warning("No curve data to export")
        return False

    try:
        with open(file_path, 'w') as f:
            # Write header
            if include_header:
                f.write(f"Frame{delimiter}X{delimiter}Y\n")

            # Write data
            for frame, x, y in sorted(curve_data, key=lambda p: p[0]):
                f.write(f"{frame}{delimiter}{x}{delimiter}{y}\n")

        logger.info(f"Successfully exported {len(curve_data)} points to CSV: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error exporting to CSV: {str(e)}")
        return False


def export_to_excel(file_path: str, curve_data: List[Tuple[int, float, float]], sheet_name: str = "Track Data") -> bool:
    """Export tracking data to Excel format.

    Note: This function requires the xlsxwriter module to be installed.
    If xlsxwriter is not available, the function will return False with an error message.

    Args:
        file_path: Path to save the Excel file
        curve_data: List of (frame, x, y) tuples
        sheet_name: Name of the worksheet

    Returns:
        True if export was successful, False otherwise
    """
    if not curve_data:
        logger.warning("No curve data to export")
        return False

    try:
        import xlsxwriter  # type: ignore
    except ImportError:
        logger.warning("xlsxwriter module not found. Excel export functionality is disabled.")
        logger.info("To enable Excel export, install xlsxwriter: pip install xlsxwriter")
        return False

    try:
        workbook = xlsxwriter.Workbook(file_path)  # type: ignore
        worksheet = workbook.add_worksheet(sheet_name)  # type: ignore

        # Add header
        worksheet.write(0, 0, "Frame")  # type: ignore
        worksheet.write(0, 1, "X")  # type: ignore
        worksheet.write(0, 2, "Y")  # type: ignore

        # Add data
        sorted_data = sorted(curve_data, key=lambda p: p[0])
        for i, (frame, x, y) in enumerate(sorted_data):
            worksheet.write(i + 1, 0, frame)  # type: ignore
            worksheet.write(i + 1, 1, x)  # type: ignore
            worksheet.write(i + 1, 2, y)  # type: ignore

        workbook.close()  # type: ignore
        logger.info(f"Successfully exported {len(curve_data)} points to Excel: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error exporting to Excel: {str(e)}")
        return False

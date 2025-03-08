#!/usr/bin/env python
# -*- coding: utf-8 -*-

def export_to_csv(file_path, curve_data, include_header=True, delimiter=','):
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
        return False
        
    try:
        with open(file_path, 'w') as f:
            # Write header
            if include_header:
                f.write(f"Frame{delimiter}X{delimiter}Y\n")
                
            # Write data
            for frame, x, y in sorted(curve_data, key=lambda p: p[0]):
                f.write(f"{frame}{delimiter}{x}{delimiter}{y}\n")
                
        return True
    except Exception as e:
        print(f"Error exporting to CSV: {str(e)}")
        return False

def export_to_excel(file_path, curve_data, sheet_name="Track Data"):
    """Export tracking data to Excel format.
    
    Args:
        file_path: Path to save the Excel file
        curve_data: List of (frame, x, y) tuples
        sheet_name: Name of the worksheet
        
    Returns:
        True if export was successful, False otherwise
    """
    try:
        import xlsxwriter
    except ImportError:
        print("xlsxwriter module not found. Please install it using 'pip install xlsxwriter'")
        return False
        
    if not curve_data:
        return False
        
    try:
        workbook = xlsxwriter.Workbook(file_path)
        worksheet = workbook.add_worksheet(sheet_name)
        
        # Add header
        worksheet.write(0, 0, "Frame")
        worksheet.write(0, 1, "X")
        worksheet.write(0, 2, "Y")
        
        # Add data
        sorted_data = sorted(curve_data, key=lambda p: p[0])
        for i, (frame, x, y) in enumerate(sorted_data):
            worksheet.write(i + 1, 0, frame)
            worksheet.write(i + 1, 1, x)
            worksheet.write(i + 1, 2, y)
            
        workbook.close()
        return True
    except Exception as e:
        print(f"Error exporting to Excel: {str(e)}")
        return False
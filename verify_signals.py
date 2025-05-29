#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Signal connection verification utility for 3DE4 Curve Editor.

This script can be used to verify that all expected signals are properly connected
in the application. It checks for common UI elements and their signals, reporting
any that are missing or improperly connected.

Usage:
    Run this script from within the main window to verify signal connections.
"""


from PySide6.QtCore import Signal

def verify_signal_connections(main_window):
    """Verify that all expected signals are properly connected.
    
    Args:
        main_window: The main application window instance
        
    Returns:
        tuple: (success, report) where success is a boolean indicating all checks passed,
               and report is a string with details
    """
    report_lines = []
    report_lines.append("\n" + "="*80)
    report_lines.append("SIGNAL CONNECTION VERIFICATION REPORT")
    report_lines.append("="*80 + "\n")
    
    # Check if connection tracking is initialized
    if not hasattr(main_window, '_connected_signals'):
        report_lines.append("❌ ERROR: No '_connected_signals' tracking set found.")
        report_lines.append("   Signal connections may not have been made using SignalRegistry.")
        return False, "\n".join(report_lines)
    
    report_lines.append(f"✓ Found {len(main_window._connected_signals)} tracked signal connections.")
    
    # Define expected UI elements with signals that should be connected
    essential_elements = [
        'curve_view',
        'load_button',
        'save_button',
        'timeline_slider',
    ]
    
    # Check that essential elements exist and have signals connected
    for element_name in essential_elements:
        if not hasattr(main_window, element_name):
            report_lines.append(f"❌ Essential UI element '{element_name}' not found.")
            continue
            
        # Element exists but we don't need to store it in a variable
        # element = getattr(main_window, element_name)
        
        # For each element, check that expected signals are in the tracking set
        # This is a simplified check since we don't have the actual signal object
        signal_found = False
        for conn_id in main_window._connected_signals:
            if element_name in conn_id:
                signal_found = True
                break
                
        if signal_found:
            report_lines.append(f"✓ Element '{element_name}' has connected signals.")
        else:
            report_lines.append(f"❌ No signals connected for '{element_name}'.")
    
    # Check curve_view signals specifically
    if hasattr(main_window, 'curve_view'):
        cv = main_window.curve_view
        
        # Get signals from the curve view
        signals = []
        for name in dir(cv):
            attr = getattr(cv, name)
            if isinstance(attr, Signal):
                signals.append(name)
                
        report_lines.append(f"\nFound {len(signals)} signals in curve_view:")
        
        # Check each signal for connections
        for signal_name in signals:
            signal_found = False
            for conn_id in main_window._connected_signals:
                if f"curve_view.{signal_name}" in conn_id:
                    signal_found = True
                    break
                    
            if signal_found:
                report_lines.append(f"✓ Signal 'curve_view.{signal_name}' is connected.")
            else:
                report_lines.append(f"❌ Signal 'curve_view.{signal_name}' is NOT connected.")
    
    # Check keyboard shortcuts
    if hasattr(main_window, 'shortcuts') and main_window.shortcuts:
        shortcut_count = len(main_window.shortcuts)
        report_lines.append(f"\nFound {shortcut_count} keyboard shortcuts defined.")
        
        # We can't easily check if the shortcuts are connected, but we can check if they exist
        from keyboard_shortcuts import ShortcutManager
        missing_shortcuts = []
        
        for shortcut_id in ShortcutManager.SHORTCUTS:
            if shortcut_id not in main_window.shortcuts:
                missing_shortcuts.append(shortcut_id)
                
        if missing_shortcuts:
            report_lines.append(f"❌ Missing {len(missing_shortcuts)} shortcuts: {missing_shortcuts}")
        else:
            report_lines.append("✓ All defined shortcuts are present.")
    else:
        report_lines.append("❌ No keyboard shortcuts found.")
    
    # Overall verdict
    if "❌" in "\n".join(report_lines):
        report_lines.append("\n❌ Some signal connection checks FAILED.")
        success = False
    else:
        report_lines.append("\n✓ All signal connection checks PASSED.")
        success = True
        
    report_lines.append("="*80)
    
    return success, "\n".join(report_lines)

if __name__ == "__main__":
    # This can be used to test the verification function directly
    # It should be run from inside the application, e.g., from console
    print("Run this from within the application to verify signal connections.")
    print("Example usage:")
    print("    from verify_signals import verify_signal_connections")
    print("    success, report = verify_signal_connections(self)")
    print("    print(report)")

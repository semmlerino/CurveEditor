#!/usr/bin/env python3
"""
Test Coverage Analysis Script

This script runs pytest with coverage and generates a detailed report of the results.
It identifies modules with low coverage and suggests areas for improvement.
"""

import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

def run_coverage_analysis():
    """Run pytest with coverage and generate a coverage XML report."""
    print("Running pytest with coverage analysis...")
    subprocess.run(
        ["pytest", "--cov=services", "--cov-report=xml:coverage.xml"],
        check=True
    )

def parse_coverage_report():
    """Parse the coverage XML report and return coverage data."""
    if not os.path.exists("coverage.xml"):
        print("Error: coverage.xml not found. Coverage analysis may have failed.")
        return None
    
    tree = ET.parse("coverage.xml")
    root = tree.getroot()
    
    # Extract project-level coverage
    project_coverage = float(root.get("line-rate", "0")) * 100
    
    # Extract package and class level coverage
    packages = []
    for package in root.findall(".//package"):
        package_name = package.get("name", "unknown")
        package_coverage = float(package.get("line-rate", "0")) * 100
        
        classes = []
        for cls in package.findall(".//class"):
            class_name = cls.get("name", "unknown")
            class_coverage = float(cls.get("line-rate", "0")) * 100
            
            classes.append({
                "name": class_name,
                "coverage": class_coverage
            })
        
        packages.append({
            "name": package_name,
            "coverage": package_coverage,
            "classes": classes
        })
    
    return {
        "project_coverage": project_coverage,
        "packages": packages
    }

def generate_report(coverage_data):
    """Generate a human-readable coverage report."""
    if not coverage_data:
        return "No coverage data available."
    
    lines = []
    lines.append("# Test Coverage Report")
    lines.append("")
    lines.append(f"Overall project coverage: {coverage_data['project_coverage']:.2f}%")
    lines.append("")
    lines.append("## Package Coverage")
    lines.append("")
    
    # Sort packages by coverage (ascending)
    packages = sorted(coverage_data['packages'], key=lambda x: x['coverage'])
    
    for package in packages:
        lines.append(f"### {package['name']}: {package['coverage']:.2f}%")
        
        # Sort classes by coverage (ascending)
        classes = sorted(package['classes'], key=lambda x: x['coverage'])
        
        lines.append("| Module | Coverage |")
        lines.append("|--------|----------|")
        for cls in classes:
            coverage_str = f"{cls['coverage']:.2f}%"
            # Highlight low coverage
            if cls['coverage'] < 50:
                coverage_str = f"**{coverage_str}** 🔴"
            elif cls['coverage'] < 80:
                coverage_str = f"*{coverage_str}* 🟡"
            lines.append(f"| {cls['name']} | {coverage_str} |")
        
        lines.append("")
    
    # Add recommendations
    lines.append("## Recommendations")
    lines.append("")
    lines.append("Modules with coverage below 50% (🔴) should be prioritized for additional tests.")
    lines.append("Modules with coverage between 50% and 80% (🟡) need moderate improvement.")
    
    # Find modules with lowest coverage
    all_classes = []
    for package in packages:
        for cls in package['classes']:
            all_classes.append((f"{package['name']}.{cls['name']}", cls['coverage']))
    
    all_classes.sort(key=lambda x: x[1])
    
    if all_classes:
        lines.append("")
        lines.append("### Top Priority Modules")
        lines.append("")
        for module, coverage in all_classes[:5]:
            if coverage < 80:
                lines.append(f"- {module}: {coverage:.2f}%")
    
    return "\n".join(lines)

def main():
    """Run the coverage analysis and generate reports."""
    try:
        run_coverage_analysis()
        coverage_data = parse_coverage_report()
        report = generate_report(coverage_data)
        
        # Save report to a file
        report_path = Path("docs") / "coverage_report.md"
        os.makedirs(report_path.parent, exist_ok=True)
        
        with open(report_path, "w") as f:
            f.write(report)
        
        print(f"Coverage report generated at {report_path}")
        print("\nSummary:")
        if coverage_data:
            print(f"Overall coverage: {coverage_data['project_coverage']:.2f}%")
            
            # Count modules by coverage category
            low = 0
            medium = 0
            high = 0
            
            for package in coverage_data['packages']:
                for cls in package['classes']:
                    if cls['coverage'] < 50:
                        low += 1
                    elif cls['coverage'] < 80:
                        medium += 1
                    else:
                        high += 1
            
            print(f"Modules with low coverage (<50%): {low}")
            print(f"Modules with medium coverage (50-80%): {medium}")
            print(f"Modules with good coverage (>80%): {high}")
        
    except Exception as e:
        print(f"Error running coverage analysis: {e}")

if __name__ == "__main__":
    main()

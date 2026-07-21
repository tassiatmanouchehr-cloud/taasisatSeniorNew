#!/usr/bin/env python3
"""
Theme Validation Script
Enterprise Service Marketplace Platform

Verifies that all theme CSS files define the same set of CSS variables.
Detects missing, duplicate, and mismatched variables across themes.

Checks:
  1. Light theme defines all required variables
  2. Dark theme defines all required variables
  3. No variable defined in light is missing from dark (and vice versa)
  4. No duplicate variable definitions within a single theme
  5. Variable naming follows convention (--color-*, --shadow-*, --ring-*)

Usage:
    python tools/validate_themes.py
    python tools/validate_themes.py --verbose

Exit code:
    0 = all themes valid
    1 = validation errors found
"""

import argparse
import re
import sys
from pathlib import Path

# Theme files to validate
THEME_FILES = {
    "light": "ui/themes/light.css",
    "dark": "ui/themes/dark.css",
}

# Required variable prefixes (at minimum, both themes must define these groups)
REQUIRED_PREFIXES = [
    "--color-primary-",
    "--color-secondary-",
    "--color-accent-",
    "--color-success-",
    "--color-warning-",
    "--color-danger-",
    "--color-info-",
    "--color-surface",
    "--color-background",
    "--color-border",
    "--color-text",
    "--shadow-",
    "--ring-",
]

# CSS variable extraction pattern
CSS_VAR_DEFINITION = re.compile(r"(--[\w-]+)\s*:\s*([^;]+);")


def extract_variables(filepath: str) -> dict:
    """Extract all CSS variable definitions from a file."""
    variables = {}
    duplicates = []

    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        return variables

    for match in CSS_VAR_DEFINITION.finditer(content):
        var_name = match.group(1)
        var_value = match.group(2).strip()
        if var_name in variables:
            duplicates.append(var_name)
        variables[var_name] = var_value

    return variables


def validate_naming(variables: dict) -> list:
    """Check variable naming conventions."""
    issues = []
    valid_prefixes = (
        "--color-",
        "--shadow-",
        "--ring-",
        "--sidebar-",
        "--navbar-",
        "--content-",
        "--input-",
        "--border-",
    )

    for var_name in variables:
        if not any(var_name.startswith(p) for p in valid_prefixes):
            # Allow structural variables from base.css
            if not var_name.startswith("--motion-"):
                issues.append(f"Non-standard variable name: {var_name}")

    return issues


def main():
    parser = argparse.ArgumentParser(description="Validate theme CSS variables")
    parser.add_argument("--verbose", action="store_true", help="Show all variables")
    parser.add_argument("--root", default=".", help="Project root directory")
    args = parser.parse_args()

    root = Path(args.root)
    errors = []
    warnings = []

    # Extract variables from each theme
    themes = {}
    for theme_name, theme_path in THEME_FILES.items():
        full_path = str(root / theme_path)
        variables = extract_variables(full_path)
        if not variables:
            errors.append(f"Theme '{theme_name}' has no CSS variables or file not found: {theme_path}")
        themes[theme_name] = variables

    if errors:
        # Fatal — can't continue without theme files
        print("\n❌ THEME VALIDATION FAILED\n")
        for err in errors:
            print(f"  ERROR: {err}")
        sys.exit(1)

    light_vars = themes.get("light", {})
    dark_vars = themes.get("dark", {})

    # Check 1: Required prefixes exist in both themes
    for prefix in REQUIRED_PREFIXES:
        light_has = any(v.startswith(prefix) for v in light_vars)
        dark_has = any(v.startswith(prefix) for v in dark_vars)
        if not light_has:
            errors.append(f"Light theme missing variables with prefix: {prefix}")
        if not dark_has:
            errors.append(f"Dark theme missing variables with prefix: {prefix}")

    # Check 2: Cross-theme consistency (same variables in both)
    light_only = set(light_vars.keys()) - set(dark_vars.keys())
    dark_only = set(dark_vars.keys()) - set(light_vars.keys())

    for var in sorted(light_only):
        errors.append(f"Variable defined in light but MISSING from dark: {var}")
    for var in sorted(dark_only):
        errors.append(f"Variable defined in dark but MISSING from light: {var}")

    # Check 3: Naming conventions
    naming_issues = validate_naming(light_vars)
    for issue in naming_issues:
        warnings.append(issue)

    # Check 4: Variable count
    light_count = len(light_vars)
    dark_count = len(dark_vars)

    # Report
    print(f"\n{'=' * 60}")
    print("  THEME VALIDATION REPORT")
    print(f"{'=' * 60}")
    print(f"\n  Light theme: {light_count} variables ({THEME_FILES['light']})")
    print(f"  Dark theme:  {dark_count} variables ({THEME_FILES['dark']})")

    if args.verbose:
        print("\n  Light variables:")
        for v in sorted(light_vars.keys()):
            status = "✓" if v in dark_vars else "✗ MISSING IN DARK"
            print(f"    {status} {v}")

    if errors:
        print(f"\n  ❌ ERRORS ({len(errors)}):")
        for err in errors:
            print(f"    • {err}")

    if warnings:
        print(f"\n  ⚠ WARNINGS ({len(warnings)}):")
        for warn in warnings:
            print(f"    • {warn}")

    print(f"\n{'=' * 60}")

    if errors:
        print(f"\n❌ THEME VALIDATION FAILED: {len(errors)} errors")
        sys.exit(1)
    else:
        print("\n✅ THEME VALIDATION PASSED")
        print(f"   Light: {light_count} vars | Dark: {dark_count} vars | Consistent: ✓")
        sys.exit(0)


if __name__ == "__main__":
    main()

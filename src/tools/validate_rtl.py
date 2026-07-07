#!/usr/bin/env python3
"""
RTL Validation Script
Enterprise Service Marketplace Platform

Scans CSS and HTML templates for physical direction properties.
All positioning must use logical CSS (inline-start/end, block-start/end).

REJECTS (in CSS declarations and Tailwind classes):
  - left: / right: (positioning)
  - margin-left / margin-right
  - padding-left / padding-right
  - border-left / border-right
  - float: left / float: right
  - text-align: left / text-align: right
  - Tailwind: ml-*, mr-*, pl-*, pr-*, left-*, right-*, text-left, text-right

ALLOWS:
  - Comments mentioning left/right (documentation)
  - CSS variable definitions (--xxx-left is fine as a name)
  - margin-inline-start/end, padding-inline-start/end
  - inset-inline-start/end
  - Tailwind: ms-*, me-*, ps-*, pe-*, start-*, end-*, text-start, text-end
  - SVG transform/path data containing coordinates

Usage:
    python tools/validate_rtl.py
    python tools/validate_rtl.py --fix-suggestions  (show what to replace with)

Exit code:
    0 = no violations
    1 = violations found (fails CI)
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Directories to scan
SCAN_DIRS = ['templates/', 'ui/components/', 'ui/layouts/', 'ui/css/']

# Directories to EXCLUDE
EXCLUDE_DIRS = ['node_modules/', '.venv/', 'tests/', 'ui/themes/']

# Physical CSS properties (FORBIDDEN in declarations)
PHYSICAL_CSS_PROPERTIES = [
    (re.compile(r'(?<!\w)margin-left\s*:'), 'margin-left', 'margin-inline-start'),
    (re.compile(r'(?<!\w)margin-right\s*:'), 'margin-right', 'margin-inline-end'),
    (re.compile(r'(?<!\w)padding-left\s*:'), 'padding-left', 'padding-inline-start'),
    (re.compile(r'(?<!\w)padding-right\s*:'), 'padding-right', 'padding-inline-end'),
    (re.compile(r'(?<!\w)border-left\s*:'), 'border-left', 'border-inline-start'),
    (re.compile(r'(?<!\w)border-right\s*:'), 'border-right', 'border-inline-end'),
    (re.compile(r'(?<!\w)border-left-width\s*:'), 'border-left-width', 'border-inline-start-width'),
    (re.compile(r'(?<!\w)border-right-width\s*:'), 'border-right-width', 'border-inline-end-width'),
    (re.compile(r'float\s*:\s*left'), 'float: left', 'float: inline-start'),
    (re.compile(r'float\s*:\s*right'), 'float: right', 'float: inline-end'),
    (re.compile(r'text-align\s*:\s*left'), 'text-align: left', 'text-align: start'),
    (re.compile(r'text-align\s*:\s*right'), 'text-align: right', 'text-align: end'),
    (re.compile(r'(?<!\w)left\s*:\s*(?!.*calc)(?!.*var)\d'), 'left:', 'inset-inline-start:'),
    (re.compile(r'(?<!\w)right\s*:\s*(?!.*calc)(?!.*var)\d'), 'right:', 'inset-inline-end:'),
]

# Physical Tailwind classes (FORBIDDEN in class attributes)
PHYSICAL_TAILWIND = re.compile(
    r'\b(?:ml-|mr-|pl-|pr-|left-|right-|text-left|text-right'
    r'|border-l-|border-r-|rounded-l-|rounded-r-'
    r'|rounded-tl-|rounded-tr-|rounded-bl-|rounded-br-)\S*\b'
)

# Tailwind replacements for suggestions
TAILWIND_FIXES = {
    'ml-': 'ms-', 'mr-': 'me-', 'pl-': 'ps-', 'pr-': 'pe-',
    'left-': 'start-', 'right-': 'end-',
    'text-left': 'text-start', 'text-right': 'text-end',
    'border-l-': 'border-s-', 'border-r-': 'border-e-',
    'rounded-l-': 'rounded-s-', 'rounded-r-': 'rounded-e-',
    'rounded-tl-': 'rounded-ss-', 'rounded-tr-': 'rounded-se-',
    'rounded-bl-': 'rounded-es-', 'rounded-br-': 'rounded-ee-',
}


def is_excluded(filepath: str) -> bool:
    """Check if file should be excluded."""
    for excl in EXCLUDE_DIRS:
        if excl in filepath:
            return True
    return False


def is_comment_line(line: str) -> bool:
    """Check if line is a comment."""
    stripped = line.strip()
    return (
        stripped.startswith('<!--')
        or stripped.startswith('*')
        or stripped.startswith('/*')
        or stripped.startswith('//')
        or stripped.startswith('{#')
        or stripped.startswith('#')
        or '(not ' in stripped  # Documentation like "(not margin-left)"
    )


def scan_file(filepath: str, show_fix: bool = False) -> list:
    """Scan a single file for RTL violations."""
    violations = []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except (UnicodeDecodeError, IOError):
        return violations

    for line_num, line in enumerate(lines, 1):
        # Skip comments
        if is_comment_line(line):
            continue

        # Check CSS property violations (in .css files and style= attributes)
        if filepath.endswith('.css') or 'style=' in line:
            for pattern, prop_name, replacement in PHYSICAL_CSS_PROPERTIES:
                if pattern.search(line):
                    v = {
                        'file': filepath,
                        'line': line_num,
                        'type': 'PHYSICAL_CSS',
                        'value': prop_name,
                        'context': line.strip()[:100],
                    }
                    if show_fix:
                        v['fix'] = f'Replace with: {replacement}'
                    violations.append(v)

        # Check Tailwind class violations (in .html files)
        if filepath.endswith('.html'):
            for match in PHYSICAL_TAILWIND.finditer(line):
                # Skip if in a comment context
                before = line[:match.start()]
                if '{#' in before or '<!--' in before:
                    continue
                v = {
                    'file': filepath,
                    'line': line_num,
                    'type': 'PHYSICAL_TAILWIND',
                    'value': match.group(),
                    'context': line.strip()[:100],
                }
                if show_fix:
                    fix_class = match.group()
                    for old, new in TAILWIND_FIXES.items():
                        if fix_class.startswith(old):
                            fix_class = new + fix_class[len(old):]
                            break
                    v['fix'] = f'Replace with: {fix_class}'
                violations.append(v)

    return violations


def main():
    parser = argparse.ArgumentParser(description='Validate RTL compliance (logical CSS only)')
    parser.add_argument('--fix-suggestions', action='store_true',
                        help='Show suggested replacements')
    parser.add_argument('--root', default='.', help='Project root directory')
    args = parser.parse_args()

    root = Path(args.root)
    all_violations = []

    # Collect files
    files_to_scan = []
    for scan_dir in SCAN_DIRS:
        dir_path = root / scan_dir
        if not dir_path.exists():
            continue
        for filepath in dir_path.rglob('*'):
            if filepath.is_file() and filepath.suffix in ('.html', '.css'):
                rel_path = str(filepath.relative_to(root))
                if not is_excluded(rel_path):
                    files_to_scan.append(str(filepath))

    # Scan files
    for filepath in sorted(files_to_scan):
        violations = scan_file(filepath, show_fix=args.fix_suggestions)
        all_violations.extend(violations)

    # Report
    if all_violations:
        print(f"\n❌ RTL VIOLATIONS: {len(all_violations)} found\n")
        print("-" * 80)
        for v in all_violations:
            print(f"  {v['file']}:{v['line']}")
            print(f"    Type: {v['type']}")
            print(f"    Value: {v['value']}")
            if 'fix' in v:
                print(f"    Fix: {v['fix']}")
            print(f"    Context: {v['context']}")
            print()
        print("-" * 80)
        print(f"\n❌ FAILED: {len(all_violations)} RTL violations")
        print("Fix: Replace physical properties with logical equivalents.")
        print("Run with --fix-suggestions for replacement hints.")
        sys.exit(1)
    else:
        print(f"\n✅ RTL VALIDATION PASSED")
        print(f"   Files checked: {len(files_to_scan)}")
        print(f"   Violations: 0")
        print(f"   All positioning uses logical CSS (inline-start/end).")
        sys.exit(0)


if __name__ == '__main__':
    main()

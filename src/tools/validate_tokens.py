#!/usr/bin/env python3
"""
Design Token Validation Script
Enterprise Service Marketplace Platform

Scans all HTML templates and CSS files for hardcoded values that should
come from Design Tokens (CSS variables or Tailwind classes).

REJECTS:
  - Hardcoded HEX colors (#fff, #a1b2c3, etc.)
  - Hardcoded RGB/RGBA (rgb(x,x,x), rgba(...))
  - Hardcoded HSL/HSLA (hsl(...), hsla(...))
  - Hardcoded pixel spacing in style attributes (margin: 10px, padding: 20px)
  - Hardcoded border-radius in style attributes
  - Hardcoded box-shadow in style attributes
  - Hardcoded z-index in style attributes

ALLOWS:
  - CSS variable references: var(--color-*)
  - Tailwind classes: bg-primary, text-text, p-4, rounded-lg, shadow-md, z-modal
  - Colors inside theme CSS files (themes/*.css) — those DEFINE the tokens
  - Colors inside design_tokens/*.js — those DEFINE the tokens
  - SVG path data (d="M..." attributes)
  - stroke-width, viewBox numbers in SVGs

Usage:
    python tools/validate_tokens.py
    python tools/validate_tokens.py --strict  (also checks CSS files)

Exit code:
    0 = no violations
    1 = violations found (fails CI)
"""

import argparse
import re
import sys
from pathlib import Path

# Directories to scan
TEMPLATE_DIRS = ["templates/", "ui/components/", "ui/layouts/"]
CSS_DIRS = ["ui/css/"]

# Directories to EXCLUDE (these define tokens, not consume them)
EXCLUDE_DIRS = ["ui/themes/", "ui/design_tokens/", "node_modules/", ".venv/", "tests/"]
EXCLUDE_FILES = ["tailwind.config.js", "postcss.config.js"]

# Patterns that indicate hardcoded values (violations)
HEX_COLOR = re.compile(r"(?<![\w-])#(?:[0-9a-fA-F]{3}){1,2}(?![0-9a-fA-F])")
RGB_COLOR = re.compile(r"rgba?\s*\(\s*\d+", re.IGNORECASE)
HSL_COLOR = re.compile(r"hsla?\s*\(\s*\d+", re.IGNORECASE)

# Inline style patterns with hardcoded values
INLINE_STYLE_SPACING = re.compile(
    r'style\s*=\s*["\'][^"\']*(?:margin|padding|gap|top|bottom|left|right|width|height)\s*:\s*\d+px', re.IGNORECASE
)
INLINE_STYLE_RADIUS = re.compile(r'style\s*=\s*["\'][^"\']*border-radius\s*:\s*\d+', re.IGNORECASE)
INLINE_STYLE_SHADOW = re.compile(r'style\s*=\s*["\'][^"\']*box-shadow\s*:', re.IGNORECASE)
INLINE_STYLE_ZINDEX = re.compile(r'style\s*=\s*["\'][^"\']*z-index\s*:\s*\d+', re.IGNORECASE)

# Exceptions: contexts where colors ARE allowed
SVG_PATH_DATA = re.compile(r'd\s*=\s*"[^"]*"')  # SVG path data
SVG_VIEWBOX = re.compile(r'viewBox\s*=\s*"[^"]*"')
STROKE_WIDTH = re.compile(r'stroke-width\s*=\s*"[^"]*"')
CSS_VAR_REF = re.compile(r"var\s*\(\s*--")  # var(--color-xxx) is allowed
TAILWIND_CLASS_CONTEXT = re.compile(r'class\s*=\s*"[^"]*"')


def is_excluded(filepath: str) -> bool:
    """Check if file should be excluded from scanning."""
    for excl in EXCLUDE_DIRS:
        if excl in filepath:
            return True
    for excl in EXCLUDE_FILES:
        if filepath.endswith(excl):
            return True
    return False


def is_in_svg_context(line: str, match_start: int) -> bool:
    """Check if a match is inside an SVG d= attribute or viewBox."""
    # Check if the hex color is part of SVG path data
    before = line[:match_start]
    if 'd="' in before and '"' not in before[before.rfind('d="') + 3 :]:
        return True
    return False


def is_in_comment(line: str) -> bool:
    """Check if the line is a comment."""
    stripped = line.strip()
    return (
        stripped.startswith("<!--")
        or stripped.startswith("*")
        or stripped.startswith("/*")
        or stripped.startswith("//")
        or stripped.startswith("{#")
        or stripped.startswith("#")
    )


def scan_file(filepath: str, strict: bool = False) -> list:
    """Scan a single file for design token violations."""
    violations = []

    try:
        with open(filepath, encoding="utf-8") as f:
            lines = f.readlines()
    except (OSError, UnicodeDecodeError):
        return violations

    for line_num, line in enumerate(lines, 1):
        # Skip comments
        if is_in_comment(line):
            continue

        # Skip lines that are CSS variable definitions (in theme files)
        if "--color-" in line or "--shadow-" in line or "--ring-" in line:
            continue

        # Check HEX colors
        for match in HEX_COLOR.finditer(line):
            # Skip if inside SVG path data
            if is_in_svg_context(line, match.start()):
                continue
            # Skip if it's a CSS variable value (defining tokens)
            if "var(" in line[max(0, match.start() - 20) : match.start()]:
                continue
            violations.append(
                {
                    "file": filepath,
                    "line": line_num,
                    "type": "HARDCODED_HEX",
                    "value": match.group(),
                    "context": line.strip()[:100],
                }
            )

        # Check RGB/RGBA (but not in var() context or CSS variable definitions)
        for match in RGB_COLOR.finditer(line):
            if CSS_VAR_REF.search(line[max(0, match.start() - 10) : match.start()]):
                continue
            violations.append(
                {
                    "file": filepath,
                    "line": line_num,
                    "type": "HARDCODED_RGB",
                    "value": match.group()[:30],
                    "context": line.strip()[:100],
                }
            )

        # Check HSL/HSLA
        for match in HSL_COLOR.finditer(line):
            if CSS_VAR_REF.search(line[max(0, match.start() - 10) : match.start()]):
                continue
            violations.append(
                {
                    "file": filepath,
                    "line": line_num,
                    "type": "HARDCODED_HSL",
                    "value": match.group()[:30],
                    "context": line.strip()[:100],
                }
            )

        # Check inline style violations (only in HTML templates)
        if filepath.endswith(".html"):
            if INLINE_STYLE_SPACING.search(line):
                violations.append(
                    {
                        "file": filepath,
                        "line": line_num,
                        "type": "INLINE_SPACING",
                        "value": "hardcoded px value in style attribute",
                        "context": line.strip()[:100],
                    }
                )
            if INLINE_STYLE_RADIUS.search(line):
                violations.append(
                    {
                        "file": filepath,
                        "line": line_num,
                        "type": "INLINE_RADIUS",
                        "value": "hardcoded border-radius in style",
                        "context": line.strip()[:100],
                    }
                )
            if INLINE_STYLE_SHADOW.search(line):
                violations.append(
                    {
                        "file": filepath,
                        "line": line_num,
                        "type": "INLINE_SHADOW",
                        "value": "hardcoded box-shadow in style",
                        "context": line.strip()[:100],
                    }
                )
            if INLINE_STYLE_ZINDEX.search(line):
                violations.append(
                    {
                        "file": filepath,
                        "line": line_num,
                        "type": "INLINE_ZINDEX",
                        "value": "hardcoded z-index in style",
                        "context": line.strip()[:100],
                    }
                )

    return violations


def main():
    parser = argparse.ArgumentParser(description="Validate Design Token usage")
    parser.add_argument("--strict", action="store_true", help="Also scan CSS files (not just templates)")
    parser.add_argument("--root", default=".", help="Project root directory")
    args = parser.parse_args()

    root = Path(args.root)
    all_violations = []

    # Determine directories to scan
    scan_dirs = TEMPLATE_DIRS.copy()
    if args.strict:
        scan_dirs.extend(CSS_DIRS)

    # Collect files
    files_to_scan = []
    for scan_dir in scan_dirs:
        dir_path = root / scan_dir
        if not dir_path.exists():
            continue
        for filepath in dir_path.rglob("*"):
            if filepath.is_file() and filepath.suffix in (".html", ".css"):
                rel_path = str(filepath.relative_to(root))
                if not is_excluded(rel_path):
                    files_to_scan.append(str(filepath))

    # Scan files
    for filepath in sorted(files_to_scan):
        violations = scan_file(filepath, strict=args.strict)
        all_violations.extend(violations)

    # Report
    if all_violations:
        print(f"\n❌ DESIGN TOKEN VIOLATIONS: {len(all_violations)} found\n")
        print("-" * 80)
        for v in all_violations:
            print(f"  {v['file']}:{v['line']}")
            print(f"    Type: {v['type']}")
            print(f"    Value: {v['value']}")
            print(f"    Context: {v['context']}")
            print()
        print("-" * 80)
        print(f"\n❌ FAILED: {len(all_violations)} violations in {len(set(v['file'] for v in all_violations))} files")
        print("Fix: Replace hardcoded values with Tailwind classes or CSS variables.")
        sys.exit(1)
    else:
        files_checked = len(files_to_scan)
        print("\n✅ DESIGN TOKEN VALIDATION PASSED")
        print(f"   Files checked: {files_checked}")
        print("   Violations: 0")
        print("   All values come from Design Tokens or Tailwind classes.")
        sys.exit(0)


if __name__ == "__main__":
    main()

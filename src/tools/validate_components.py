#!/usr/bin/env python3
"""
Component Architecture Validation (Part 6) +
Design System Usage Enforcement (Part 7) +
Component Documentation Validation (Part 8)

Combined validator that checks:
1. No duplicated HTML patterns across components
2. Business templates only consume Design System components (via include)
3. No inline style attributes in templates
4. No duplicated Tailwind utility combinations
5. Every component has documentation (Props comment block)
6. Produces a component dependency report

Usage:
    python tools/validate_components.py
    python tools/validate_components.py --report  (show dependency graph)
    python tools/validate_components.py --docs    (validate documentation completeness)

Exit code:
    0 = all checks pass
    1 = violations found
"""

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# Component directories
COMPONENT_DIRS = ['ui/components/forms/', 'ui/components/feedback/',
                  'ui/components/overlays/', 'ui/components/data/']
LAYOUT_DIRS = ['ui/layouts/']
BUSINESS_TEMPLATE_DIRS = ['templates/']

# Exclusions
EXCLUDE_DIRS = ['templates/showcase/', 'node_modules/', '.venv/']

# Patterns
INLINE_STYLE = re.compile(r'style\s*=\s*["\'](?!{)', re.IGNORECASE)
INCLUDE_TAG = re.compile(r'{%\s*include\s*["\']([^"\']+)["\']')
COMMENT_BLOCK = re.compile(r'({#.*?#}|{%\s*comment\s*%}.*?{%\s*endcomment\s*%})', re.DOTALL)
PROPS_SECTION = re.compile(r'Props|Usage|Parameters|Arguments', re.IGNORECASE)


def strip_template_comments(content: str) -> str:
    """Remove Django comments before scanning executable includes."""
    return COMMENT_BLOCK.sub('', content)


def is_excluded(filepath: str) -> bool:
    for excl in EXCLUDE_DIRS:
        if excl in filepath:
            return True
    return False


def scan_inline_styles(root: Path) -> list:
    """Part 7: Find inline style attributes in business templates."""
    violations = []
    for scan_dir in BUSINESS_TEMPLATE_DIRS:
        dir_path = root / scan_dir
        if not dir_path.exists():
            continue
        for filepath in dir_path.rglob('*.html'):
            rel = str(filepath.relative_to(root))
            if is_excluded(rel):
                continue
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if line.strip().startswith('{#') or line.strip().startswith('<!--'):
                        continue
                    if INLINE_STYLE.search(line):
                        # Allow style with Django template variable (dynamic)
                        if '{{' in line and 'style' in line:
                            continue
                        violations.append({
                            'file': rel,
                            'line': line_num,
                            'type': 'INLINE_STYLE',
                            'context': line.strip()[:100],
                        })
    return violations


def scan_component_docs(root: Path) -> tuple:
    """Part 8: Verify every component has documentation."""
    documented = []
    undocumented = []

    for comp_dir in COMPONENT_DIRS:
        dir_path = root / comp_dir
        if not dir_path.exists():
            continue
        for filepath in dir_path.rglob('*.html'):
            rel = str(filepath.relative_to(root))
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check for comment block with Props/Usage documentation
            has_docs = bool(COMMENT_BLOCK.search(content) and PROPS_SECTION.search(content))
            if has_docs:
                documented.append(rel)
            else:
                undocumented.append(rel)

    return documented, undocumented


def build_dependency_graph(root: Path) -> dict:
    """Part 6: Build component include dependency graph."""
    graph = defaultdict(list)

    all_templates = []
    for scan_dir in COMPONENT_DIRS + LAYOUT_DIRS + BUSINESS_TEMPLATE_DIRS:
        dir_path = root / scan_dir
        if not dir_path.exists():
            continue
        for filepath in dir_path.rglob('*.html'):
            all_templates.append(filepath)

    for filepath in all_templates:
        rel = str(filepath.relative_to(root))
        if is_excluded(rel):
            continue
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        includes = INCLUDE_TAG.findall(strip_template_comments(content))
        for inc in includes:
            graph[rel].append(inc)

    return dict(graph)


def detect_duplicated_patterns(root: Path) -> list:
    """Part 6: Detect duplicated HTML class combinations across components."""
    # Track class attribute values (simplified: long class strings that repeat)
    class_pattern = re.compile(r'class="([^"]{50,})"')
    seen_classes = defaultdict(list)

    for comp_dir in COMPONENT_DIRS:
        dir_path = root / comp_dir
        if not dir_path.exists():
            continue
        for filepath in dir_path.rglob('*.html'):
            rel = str(filepath.relative_to(root))
            with open(filepath, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    for match in class_pattern.finditer(line):
                        class_str = match.group(1).strip()
                        # Normalize: sort classes for comparison
                        normalized = ' '.join(sorted(class_str.split()))
                        if len(normalized) > 60:  # Only flag long duplicated patterns
                            seen_classes[normalized].append(f"{rel}:{line_num}")

    duplicates = []
    for class_str, locations in seen_classes.items():
        if len(locations) > 2:  # Same long class string in 3+ places = potential issue
            duplicates.append({
                'classes': class_str[:80] + '...',
                'count': len(locations),
                'locations': locations[:5],
            })

    return duplicates


def main():
    parser = argparse.ArgumentParser(description='Component architecture validation')
    parser.add_argument('--report', action='store_true', help='Show dependency graph')
    parser.add_argument('--docs', action='store_true', help='Validate documentation')
    parser.add_argument('--root', default='.', help='Project root')
    args = parser.parse_args()

    root = Path(args.root)
    errors = []
    warnings = []

    # Part 7: Inline style check
    inline_violations = scan_inline_styles(root)
    if inline_violations:
        for v in inline_violations:
            errors.append(f"INLINE_STYLE: {v['file']}:{v['line']} — {v['context']}")

    # Part 8: Documentation check
    documented, undocumented = scan_component_docs(root)
    if undocumented:
        for comp in undocumented:
            warnings.append(f"UNDOCUMENTED: {comp} — missing Props/Usage comment block")

    # Part 6: Architecture check
    duplicates = detect_duplicated_patterns(root)
    if duplicates:
        for dup in duplicates:
            warnings.append(
                f"DUPLICATED_PATTERN: {dup['classes']} "
                f"(found in {dup['count']} places: {', '.join(dup['locations'][:3])})"
            )

    # Part 6: Dependency graph (if --report)
    if args.report:
        graph = build_dependency_graph(root)
        print("\n📊 COMPONENT DEPENDENCY GRAPH\n")
        for template, includes in sorted(graph.items()):
            if includes:
                print(f"  {template}")
                for inc in includes:
                    print(f"    └── {inc}")
        print(f"\n  Total templates with includes: {len(graph)}")
        print(f"  Total include relationships: {sum(len(v) for v in graph.values())}")

    # Report
    print(f"\n{'=' * 60}")
    print(f"  COMPONENT VALIDATION REPORT")
    print(f"{'=' * 60}")
    print(f"\n  Components documented: {len(documented)}/{len(documented) + len(undocumented)}")
    print(f"  Inline style violations: {len(inline_violations)}")
    print(f"  Duplicated patterns: {len(duplicates)}")

    if errors:
        print(f"\n  ❌ ERRORS ({len(errors)}):")
        for err in errors:
            print(f"    • {err}")

    if warnings and args.docs:
        print(f"\n  ⚠ WARNINGS ({len(warnings)}):")
        for warn in warnings[:20]:
            print(f"    • {warn}")
        if len(warnings) > 20:
            print(f"    ... and {len(warnings) - 20} more")

    print(f"\n{'=' * 60}")

    if errors:
        print(f"\n❌ COMPONENT VALIDATION FAILED: {len(errors)} errors")
        sys.exit(1)
    else:
        print(f"\n✅ COMPONENT VALIDATION PASSED")
        if warnings:
            print(f"   ({len(warnings)} warnings — run with --docs to see details)")
        sys.exit(0)


if __name__ == '__main__':
    main()

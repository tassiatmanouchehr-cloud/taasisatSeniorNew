# Visual Regression Testing

## Overview

Playwright-based visual regression tests that capture baseline screenshots of the UI component showcase across multiple configurations.

## Test Matrix

| Project | Theme | Direction | Viewport |
|---------|-------|-----------|----------|
| `desktop-light-rtl` | Light | RTL | 1280×720 |
| `desktop-dark-rtl` | Dark | RTL | 1280×720 |
| `desktop-light-ltr` | Light | LTR | 1280×720 |
| `tablet-light-rtl` | Light | RTL | iPad Mini |
| `tablet-dark-rtl` | Dark | RTL | iPad Mini |
| `mobile-light-rtl` | Light | RTL | iPhone 13 |
| `mobile-dark-rtl` | Dark | RTL | iPhone 13 |

**Total configurations:** 7 projects × 14 pages = **98 baseline screenshots**

## Setup

```bash
cd tests/visual

# Install dependencies
npm install

# Install browser
npx playwright install chromium

# Ensure Django is running:
# (in another terminal) cd ../../ && python manage.py runserver
```

## Running Tests

```bash
# Run all visual tests (requires Django at localhost:8000)
npm test

# Update baselines after intentional design changes
npm run test:update

# Run with UI mode (interactive)
npm run test:ui

# View HTML report
npm run test:report

# Run specific project only
npm run test:desktop
npm run test:dark
npm run test:mobile
```

## How It Works

1. Each test navigates to a showcase page (`/ui/buttons/`, etc.)
2. Animations are disabled for deterministic screenshots
3. A full-page screenshot is captured
4. Screenshots are compared against baselines in `./baselines/`
5. Differences beyond 1% pixel ratio are flagged as failures

## Directory Structure

```
tests/visual/
├── package.json            — Dependencies + scripts
├── playwright.config.js    — Test matrix configuration
├── README.md               — This file
├── specs/
│   └── showcase.spec.js    — Test definitions
├── baselines/              — Baseline screenshots (git-tracked)
├── results/                — Test output (gitignored)
└── report/                 — HTML report (gitignored)
```

## When to Update Baselines

Update baselines (`npm run test:update`) when:
- Design tokens change (colors, spacing, typography)
- Component templates change visually
- New components are added to showcase
- Theme colors are modified
- Layout structure changes

**Never update baselines to "fix" an unintended regression — fix the code instead.**

## CI Integration

In GitHub Actions:
```yaml
- name: Visual regression tests
  run: |
    cd src/tests/visual
    npm ci
    npx playwright install chromium --with-deps
    npx playwright test
```

## Troubleshooting

- **Tests fail on different OS:** Font rendering differs across OS. Use Docker or `--ignore-snapshots-on-first-run`.
- **Animations cause flaky tests:** All animations are disabled via injected CSS before screenshots.
- **Timeout errors:** Ensure Django server is running and Tailwind CSS is compiled.

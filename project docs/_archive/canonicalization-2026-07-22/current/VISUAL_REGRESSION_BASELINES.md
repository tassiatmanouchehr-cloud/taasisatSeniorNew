# VISUAL REGRESSION BASELINES

**Created:** 2026-07-20
**Status:** Baseline generation workflow established; baseline images pending commit.

---

## Overview

Playwright visual regression tests capture screenshots of UI components across
multiple dimensions (theme, direction, viewport) and compare them against
committed baseline PNG files. When baselines are absent, the tests fail with
"A snapshot doesn't exist."

## Architecture

### Two Workflows, Distinct Purposes

| Workflow | File | Trigger | Purpose |
|----------|------|---------|---------|
| **CI** | `.github/workflows/ci.yml` | push/PR | Runs the FULL Playwright test suite (snapshots + accessibility + mobile navigation) in COMPARISON mode — fails if screenshots differ from committed baselines |
| **Generate Visual Baselines** | `.github/workflows/generate-visual-baselines.yml` | `workflow_dispatch` (manual) | Runs ONLY `snapshots.spec.js` + `showcase.spec.js` with `--update-snapshots` — generates baseline images as a downloadable artifact |

### Why They Are Separate

The normal CI workflow runs ALL spec files including accessibility (axe-core)
and mobile navigation tests — their results are valuable CI signals independent
of baseline generation.

Baseline generation intentionally runs only screenshot-producing specifications.
Accessibility, mobile-navigation, and other non-baseline-producing tests remain
part of the normal Visual & Accessibility CI workflow.

The generation workflow runs ONLY the two specs that produce baselines:
- `specs/snapshots.spec.js` — 406 baselines (16 component sections x 3 modes x 7 projects + 5 full-page x 2 modes x 7 projects)
- `specs/showcase.spec.js` — 119 baselines (14 pages x 7 projects + 3 interactive states x 7 projects)
- **Total: 525 PNG baselines**

## Baseline Generation Process

### When to regenerate

- After any UI component design change
- After Tailwind/CSS token modifications
- After Playwright or browser version upgrades
- After font changes (if fonts are ever committed)
- After CI runner OS changes (ubuntu-latest major version bump)

### How to regenerate

1. Navigate to Actions → "Generate Visual Baselines" workflow
2. Click "Run workflow" (manual dispatch)
3. Wait for completion (~20 minutes)
4. Download the `playwright-baselines` artifact
5. Verify: `find . -name "*.png" | wc -l` should equal 525
6. Verify: `find . -name "*.png" -empty | wc -l` should equal 0
7. Human-review a representative sample of screenshots
8. Replace `src/tests/visual/baselines/` contents with the verified images
9. Commit and PR the updated baselines

### Artifact verification

Every generated artifact should be verified before committing:
- Exact PNG count: 525
- Per-project count: 75 each (7 projects)
- Zero zero-byte files
- Zero corrupt files (all must be valid PNG image data)
- SHA-256 of the artifact zip recorded in the commit message

## Canonical Environment

Screenshots are generated in the GitHub Actions `ubuntu-latest` runner with:

| Factor | Value |
|--------|-------|
| OS | Ubuntu (GitHub-hosted runner, `ubuntu-latest`) |
| Python | 3.12 |
| Node | 22 |
| Playwright | ^1.44 |
| Browsers | Chromium + WebKit (Playwright-bundled) |
| Database | PostgreSQL 16 + PostGIS (for migrations/seed) |
| CSS | Tailwind compiled (`npx tailwindcss ... --minify`) |
| JS | Alpine.js built (`npm run js:build`) |
| Seed data | `python manage.py seed_tenant` |
| Server | Django development server at localhost:8000 |
| Fonts | System fallback (ubuntu-latest defaults) |

### Font stabilization (deferred)

The platform's design tokens specify IRANSansX (commercial), Vazirmatn (free),
and JetBrains Mono (free) — but none are committed to the repository. Baselines
are generated with whatever system fonts `ubuntu-latest` provides. Future font
commitment or runner-OS changes will require a baseline refresh.

## Project Matrix (7 projects, 75 baselines each)

| Project | Browser | Viewport | Color Scheme | Locale |
|---------|---------|----------|-------------|--------|
| desktop-light-rtl | Chromium | 1280x720 | light | fa-IR |
| desktop-dark-rtl | Chromium | 1280x720 | dark | fa-IR |
| desktop-light-ltr | Chromium | 1280x720 | light | en-US |
| tablet-light-rtl | WebKit (iPad Mini) | 768x1024 | light | fa-IR |
| tablet-dark-rtl | WebKit (iPad Mini) | 768x1024 | dark | fa-IR |
| mobile-light-rtl | WebKit (iPhone 13) | 375x667 | light | fa-IR |
| mobile-dark-rtl | WebKit (iPhone 13) | 375x667 | dark | fa-IR |

## Current State

- **Generation workflow:** Committed and available for manual dispatch
- **Baseline images:** NOT YET COMMITTED — pending a dedicated follow-up PR
- **First verified artifact:** Workflow run `29727417384`, artifact ID `8455309646`
  - SHA-256: `3a936b67f07733f1fae74db5e9ea962bccc643c0467a7a8de20a6b5fb12adda7`
  - 525 PNGs, all valid, zero corrupt, 16.1 MB compressed
  - Independently verified 2026-07-20

## Baseline Integration Lifecycle

1. **This PR (#29):** Establishes the generation workflow and this documentation.
2. **Follow-up PR:** Adds only the 525 verified PNG baselines + removes `.gitkeep`.
   - The follow-up PR must run normal snapshot comparison (without
     `--update-snapshots`) as part of its CI checks.
   - Snapshot comparison must pass on that PR before it is merged.
   - No application code changes are expected in the follow-up PR.
3. **After merge:** The Visual & Accessibility Tests CI job will compare future
   screenshots against the committed baselines, detecting visual regressions.

## Related CI Jobs

| CI Job | Depends on Baselines | Status Without Baselines |
|--------|---------------------|--------------------------|
| Django Test Suite | No | Passes |
| Tailwind CSS Build | No | Passes |
| Lint & Format Check | No | Fails (pre-existing lint debt) |
| UI Quality Gates | No | Fails (pre-existing RTL debt) |
| Visual & Accessibility Tests | **Yes** (snapshot comparison) | Fails ("snapshot doesn't exist") |

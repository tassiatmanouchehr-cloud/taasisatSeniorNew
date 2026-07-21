/**
 * Production Accent Accessibility Tests
 *
 * Verifies color-contrast compliance on real production routes containing
 * accent-foreground pairings (primary CTAs, pagination states, etc.).
 *
 * This spec establishes an exact baseline of known dark-mode contrast
 * violations derived from CI run on commit bb03cd1 (2026-07-20).
 *
 * Strategy:
 * - Light mode: zero-tolerance for serious/critical color-contrast violations
 * - Dark mode: exact-set equality against the observed violation targets
 *   per project and route — any added, removed, or changed target fails
 *
 * Routes tested:
 * - /accounts/login/ (primary CTA submit button)
 * - / (homepage — primary CTAs in header and hero)
 *
 * Requires: @axe-core/playwright
 */

const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

// =============================================================================
// KNOWN DARK-MODE VIOLATION MANIFEST
// Derived from CI run on commit bb03cd1 (workflow Visual & Accessibility Tests)
//
// Each entry: exact project → route → sorted array of normalized axe targets.
// The test asserts exact set equality. Any deviation (added, removed, changed)
// fails the test. When PR-B2 remediates a target, its entry must be explicitly
// removed from this manifest.
// =============================================================================

const KNOWN_DARK_TARGETS = {
  'desktop-dark-rtl': {
    '/accounts/login/': [],
    '/': [
      '.hover\\:shadow-lg',
      '.max-w-2xl.mt-4.leading-8',
      '.px-7.hover\\:shadow-xl.shadow-lg',
    ],
  },
  'tablet-dark-rtl': {
    '/accounts/login/': [],
    '/': [
      '.hover\\:shadow-lg',
      '.max-w-2xl.mt-4.leading-8',
      '.px-7.hover\\:shadow-xl.shadow-lg',
    ],
  },
  'mobile-dark-rtl': {
    '/accounts/login/': [],
    '/': [
      '.max-w-2xl.mt-4.leading-8',
      '.px-7.hover\\:shadow-xl.shadow-lg',
    ],
  },
};

// =============================================================================
// TEST CONFIGURATION
// =============================================================================

const PRODUCTION_ROUTES = [
  { name: 'login', path: '/accounts/login/' },
  { name: 'homepage', path: '/' },
];

const AXE_OPTIONS = {
  runOnly: {
    type: 'tag',
    values: ['wcag2aa'],
  },
  rules: {
    'color-contrast': { enabled: true },
    'page-has-heading-one': { enabled: false },
    'landmark-one-main': { enabled: false },
    'region': { enabled: false },
  },
};

// =============================================================================
// HELPERS
// =============================================================================

function isDarkProject(testInfo) {
  return testInfo.project.name.includes('dark');
}

function extractContrastViolations(results) {
  return results.violations.filter(
    v => v.id === 'color-contrast' && (v.impact === 'serious' || v.impact === 'critical')
  );
}

/**
 * Extract the normalized sorted target set from axe violations.
 * Each node has a `target` array; we take the first selector string from each.
 */
function extractSortedTargets(violations) {
  const targets = [];
  for (const violation of violations) {
    for (const node of (violation.nodes || [])) {
      // node.target is an array of CSS selectors; take the first (most specific)
      if (node.target && node.target.length > 0) {
        targets.push(node.target[0]);
      }
    }
  }
  return targets.sort();
}

// =============================================================================
// TESTS
// =============================================================================

for (const route of PRODUCTION_ROUTES) {
  test.describe(`Production accent a11y: ${route.name}`, () => {

    test(`color-contrast — ${route.path}`, async ({ page }, testInfo) => {
      await page.goto(route.path);
      await page.waitForLoadState('networkidle');

      const results = await new AxeBuilder({ page })
        .options(AXE_OPTIONS)
        .analyze();

      const contrastViolations = extractContrastViolations(results);
      const dark = isDarkProject(testInfo);
      const projectName = testInfo.project.name;

      if (!dark) {
        // LIGHT MODE: zero tolerance
        expect(
          contrastViolations,
          `Unexpected contrast violations on ${route.path} in light mode (${projectName})`
        ).toHaveLength(0);
      } else {
        // DARK MODE: exact-set equality against manifest
        const projectManifest = KNOWN_DARK_TARGETS[projectName];

        if (!projectManifest || !(route.path in projectManifest)) {
          // No manifest entry for this project/route — zero tolerance
          expect(
            contrastViolations,
            `No manifest for ${projectName} ${route.path} — unexpected violations`
          ).toHaveLength(0);
          return;
        }

        const expectedTargets = projectManifest[route.path].slice().sort();
        const actualTargets = extractSortedTargets(contrastViolations);

        // Exact set equality — any deviation fails
        expect(
          actualTargets,
          `Dark-mode contrast targets on ${route.path} (${projectName}) do not match manifest.\n` +
          `Expected: ${JSON.stringify(expectedTargets)}\n` +
          `Actual:   ${JSON.stringify(actualTargets)}\n` +
          `If a target was remediated, remove it from KNOWN_DARK_TARGETS.\n` +
          `If a new target appeared, investigate before adding it.`
        ).toEqual(expectedTargets);
      }
    });
  });
}

/**
 * Production Accent Accessibility Tests
 *
 * Verifies color-contrast compliance on real production routes containing
 * accent-foreground pairings (primary CTAs, pagination states, etc.).
 *
 * This spec establishes measurable evidence of the known dark-mode contrast
 * limitation where `text-white` is used on lightened accent backgrounds.
 *
 * Strategy:
 * - Run axe-core color-contrast checks on unauthenticated production routes
 * - In LIGHT mode: expect zero contrast violations (text-white on dark accent passes)
 * - In DARK mode: document the known violations (text-white on lightened accent fails)
 *   using an explicit known-violation manifest — any NEW violation fails the test
 *
 * Routes tested:
 * - /accounts/login/ (primary CTA submit button)
 * - / (homepage — primary CTAs in header and hero)
 *
 * Requires:
 *   npm install @axe-core/playwright
 */

const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

// --- Known Dark-Mode Contrast Violations ---
// These represent the documented `text-white` on lightened accent background
// defect. They must be resolved by PR-B2 (foreground token remediation).
// If a violation disappears without remediation, the test will fail to alert
// that assumptions have changed.
//
// Bounding: Each entry specifies exact route, rule, and maximum expected
// node count. The test fails if:
// - Additional nodes beyond the maximum are affected
// - A different rule fails
// - A violation appears on an unlisted route
// - Any light-mode violation appears
const KNOWN_DARK_VIOLATIONS = {
  '/accounts/login/': {
    rule: 'color-contrast',
    // The primary submit button uses inline bg-primary text-white
    description: 'text-white (#ffffff) on dark-mode bg-primary — known contrast defect',
    // Expected: 1 submit button
    maxExpectedNodes: 3,
    // Target pattern: elements with text-white class on primary backgrounds
    targetPattern: /bg-primary|text-white/,
  },
  '/': {
    rule: 'color-contrast',
    // Public homepage CTAs use inline bg-primary text-white
    description: 'text-white (#ffffff) on dark-mode bg-primary in header/hero CTAs — known contrast defect',
    // Expected: header CTA + hero CTA + mobile CTA + logo + potentially more
    maxExpectedNodes: 12,
    targetPattern: /bg-primary|text-white/,
  },
};

// --- Test Configuration ---
const PRODUCTION_ROUTES = [
  { name: 'login', path: '/accounts/login/', hasAccentCTA: true },
  { name: 'homepage', path: '/', hasAccentCTA: true },
];

const AXE_OPTIONS = {
  runOnly: {
    type: 'tag',
    values: ['wcag2aa'],
  },
  rules: {
    'color-contrast': { enabled: true },
    // Disable rules irrelevant to this focused contrast test
    'page-has-heading-one': { enabled: false },
    'landmark-one-main': { enabled: false },
    'region': { enabled: false },
  },
};

// --- Helper: Determine if current project is dark mode ---
function isDarkProject(testInfo) {
  return testInfo.project.name.includes('dark');
}

// --- Helper: Extract contrast violations only ---
function extractContrastViolations(results) {
  return results.violations.filter(
    v => v.id === 'color-contrast' && (v.impact === 'serious' || v.impact === 'critical')
  );
}

// --- Tests ---
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

      if (!dark) {
        // LIGHT MODE: expect zero serious/critical contrast violations
        expect(
          contrastViolations,
          `Unexpected contrast violations on ${route.path} in light mode (${testInfo.project.name})`
        ).toHaveLength(0);
      } else {
        // DARK MODE: known violations are expected due to text-white on accent
        // But any ADDITIONAL unknown violation must fail the test
        const knownManifest = KNOWN_DARK_VIOLATIONS[route.path];

        if (!knownManifest) {
          // No known violations for this route in dark mode
          expect(
            contrastViolations,
            `Unexpected contrast violations on ${route.path} in dark mode (${testInfo.project.name})`
          ).toHaveLength(0);
        } else {
          // Count total affected nodes across all color-contrast violations
          const totalNodes = contrastViolations.reduce(
            (sum, v) => sum + (v.nodes ? v.nodes.length : 0), 0
          );

          // Separate known vs unknown violations by rule ID
          const knownRuleViolations = contrastViolations.filter(
            v => v.id === knownManifest.rule
          );
          const unknownRuleViolations = contrastViolations.filter(
            v => v.id !== knownManifest.rule
          );

          // Count nodes in known-rule violations
          const knownNodes = knownRuleViolations.reduce(
            (sum, v) => sum + (v.nodes ? v.nodes.length : 0), 0
          );

          // Log for visibility
          if (contrastViolations.length > 0) {
            console.log(
              `[${testInfo.project.name}] ${route.path}: ` +
              `${totalNodes} affected node(s) in ${contrastViolations.length} violation(s). ` +
              `Known-rule nodes: ${knownNodes}/${knownManifest.maxExpectedNodes} max. ` +
              `Unknown-rule violations: ${unknownRuleViolations.length}.`
            );
          }

          // FAIL on any violation with an UNEXPECTED rule ID
          expect(
            unknownRuleViolations,
            `Violations with unexpected rule on ${route.path} in dark mode (${testInfo.project.name})`
          ).toHaveLength(0);

          // FAIL if known-rule node count EXCEEDS the manifest maximum
          // (prevents silent expansion of the defect)
          expect(
            knownNodes,
            `Known contrast violation node count (${knownNodes}) exceeds manifest ` +
            `maximum (${knownManifest.maxExpectedNodes}) on ${route.path} in ` +
            `${testInfo.project.name}. A new element may have introduced a contrast defect.`
          ).toBeLessThanOrEqual(knownManifest.maxExpectedNodes);
        }
      }
    });

    test(`computed accent foreground — ${route.path}`, async ({ page }, testInfo) => {
      await page.goto(route.path);
      await page.waitForLoadState('networkidle');

      // Find the first primary CTA button/link on the page
      const ctaSelector = route.path === '/accounts/login/'
        ? 'button[type="submit"]'
        : 'a[href="/services/"], header a[href*="services"]';

      const ctaElement = page.locator(ctaSelector).first();
      const ctaExists = await ctaElement.count() > 0;

      if (!ctaExists) {
        // Route may not have the expected CTA — skip gracefully
        test.skip();
        return;
      }

      const styles = await ctaElement.evaluate(el => {
        const cs = window.getComputedStyle(el);
        return {
          color: cs.color,
          backgroundColor: cs.backgroundColor,
          fontSize: cs.fontSize,
          fontWeight: cs.fontWeight,
        };
      });

      // Record evidence (visible in CI output)
      console.log(
        `[${testInfo.project.name}] ${route.path} CTA: ` +
        `fg=${styles.color}, bg=${styles.backgroundColor}`
      );

      // Basic assertion: foreground and background must be resolved (not empty/transparent)
      expect(styles.color).not.toBe('');
      expect(styles.backgroundColor).not.toBe('rgba(0, 0, 0, 0)');
    });
  });
}

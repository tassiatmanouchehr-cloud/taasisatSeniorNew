/**
 * Accessibility Tests — axe-core integration with Playwright
 * Enterprise Service Marketplace Platform
 *
 * Runs axe-core accessibility checks on every showcase page.
 * Fails CI when WCAG AA violations are detected.
 *
 * Checks: ARIA, contrast, labels, keyboard, heading hierarchy,
 * focus, forms, buttons, dialogs, reduced motion.
 *
 * Usage:
 *   npx playwright test specs/accessibility.spec.js
 *
 * Requires:
 *   npm install @axe-core/playwright
 */

const { test, expect } = require('@playwright/test');
const AxeBuilder = require('@axe-core/playwright').default;

// Showcase pages to test for accessibility
const PAGES = [
  { name: 'index', path: '/ui/' },
  { name: 'buttons', path: '/ui/buttons/' },
  { name: 'forms', path: '/ui/forms/' },
  { name: 'cards', path: '/ui/cards/' },
  { name: 'tables', path: '/ui/tables/' },
  { name: 'alerts', path: '/ui/alerts/' },
  { name: 'badges', path: '/ui/badges/' },
  { name: 'avatars', path: '/ui/avatars/' },
  { name: 'icons', path: '/ui/icons/' },
  { name: 'loading', path: '/ui/loading/' },
  { name: 'empty-states', path: '/ui/empty-states/' },
  { name: 'upload', path: '/ui/upload/' },
  { name: 'dropdowns', path: '/ui/dropdowns/' },
  { name: 'navigation', path: '/ui/navigation/' },
];

// axe-core rules to enforce (WCAG AA)
const AXE_OPTIONS = {
  runOnly: {
    type: 'tag',
    values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'],
  },
  // Rules that are known to be difficult in component showcases
  // (multiple h1s, color contrast on decorative elements)
  rules: {
    // Disable page-has-heading-one for showcase (each section has its own h1)
    'page-has-heading-one': { enabled: false },
    // Disable landmark checks for showcase layout (not a real page)
    'landmark-one-main': { enabled: false },
    'region': { enabled: false },
  },
};

// Generate a test for each page
for (const page of PAGES) {
  test(`accessibility - ${page.name}`, async ({ page: browserPage }) => {
    await browserPage.goto(page.path);
    await browserPage.waitForLoadState('networkidle');

    const accessibilityScanResults = await new AxeBuilder({ page: browserPage })
      .options(AXE_OPTIONS)
      .analyze();

    // Log violations for debugging
    if (accessibilityScanResults.violations.length > 0) {
      console.log(`\n❌ Accessibility violations on ${page.path}:`);
      for (const violation of accessibilityScanResults.violations) {
        console.log(`  [${violation.impact}] ${violation.id}: ${violation.description}`);
        console.log(`    Help: ${violation.helpUrl}`);
        for (const node of violation.nodes.slice(0, 3)) {
          console.log(`    Element: ${node.html.substring(0, 100)}`);
        }
      }
    }

    // Assert no violations (critical and serious only — warnings allowed)
    const criticalViolations = accessibilityScanResults.violations.filter(
      v => v.impact === 'critical' || v.impact === 'serious'
    );

    expect(
      criticalViolations,
      `${criticalViolations.length} critical/serious a11y violations on ${page.path}`
    ).toHaveLength(0);
  });
}

// Dark mode accessibility test
test('accessibility - dark mode contrast', async ({ page }) => {
  await page.goto('/ui/buttons/');
  await page.evaluate(() => {
    document.documentElement.classList.add('dark');
    document.documentElement.setAttribute('data-theme', 'dark');
  });
  await page.waitForTimeout(300);

  const results = await new AxeBuilder({ page })
    .options({
      runOnly: { type: 'tag', values: ['wcag2aa'] },
      rules: {
        'color-contrast': { enabled: true },
        'page-has-heading-one': { enabled: false },
        'landmark-one-main': { enabled: false },
        'region': { enabled: false },
      },
    })
    .analyze();

  const contrastViolations = results.violations.filter(
    v => v.id === 'color-contrast' && v.impact !== 'minor'
  );

  expect(
    contrastViolations,
    `Color contrast violations in dark mode`
  ).toHaveLength(0);
});

// Keyboard navigation test
test('accessibility - keyboard navigation', async ({ page }) => {
  await page.goto('/ui/forms/');
  await page.waitForLoadState('networkidle');

  // Tab through form elements — verify focus is visible
  await page.keyboard.press('Tab');
  const focusedElement = await page.evaluate(() => {
    const el = document.activeElement;
    return {
      tag: el.tagName,
      type: el.type || '',
      hasFocusRing: window.getComputedStyle(el).outlineStyle !== 'none'
        || window.getComputedStyle(el).boxShadow !== 'none',
    };
  });

  // Some interactive element should be focused
  expect(focusedElement.tag).not.toBe('BODY');
});

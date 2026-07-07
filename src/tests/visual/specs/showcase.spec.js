/**
 * Visual Regression Tests — UI Component Showcase
 *
 * Captures baseline screenshots of each showcase page.
 * Run after any design system change to detect visual regressions.
 *
 * Usage:
 *   npx playwright test                    # Run all visual tests
 *   npx playwright test --update-snapshots # Update baselines
 *   npx playwright test --grep "buttons"   # Run specific page
 */

const { test, expect } = require('@playwright/test');

// Showcase pages to test
const SHOWCASE_PAGES = [
  { name: 'index', path: '/ui/', label: 'Component Index' },
  { name: 'buttons', path: '/ui/buttons/', label: 'Buttons' },
  { name: 'forms', path: '/ui/forms/', label: 'Forms' },
  { name: 'cards', path: '/ui/cards/', label: 'Cards' },
  { name: 'tables', path: '/ui/tables/', label: 'Tables' },
  { name: 'alerts', path: '/ui/alerts/', label: 'Alerts & Feedback' },
  { name: 'badges', path: '/ui/badges/', label: 'Badges' },
  { name: 'avatars', path: '/ui/avatars/', label: 'Avatars' },
  { name: 'icons', path: '/ui/icons/', label: 'Icons' },
  { name: 'loading', path: '/ui/loading/', label: 'Loading & Skeletons' },
  { name: 'empty-states', path: '/ui/empty-states/', label: 'Empty States' },
  { name: 'upload', path: '/ui/upload/', label: 'File Upload' },
  { name: 'dropdowns', path: '/ui/dropdowns/', label: 'Dropdowns & Accordion' },
  { name: 'navigation', path: '/ui/navigation/', label: 'Navigation' },
];

// Helper: apply theme before screenshot
async function applyTheme(page, theme) {
  if (theme === 'dark') {
    await page.evaluate(() => {
      document.documentElement.classList.add('dark');
      document.documentElement.setAttribute('data-theme', 'dark');
    });
  } else {
    await page.evaluate(() => {
      document.documentElement.classList.remove('dark');
      document.documentElement.setAttribute('data-theme', 'light');
    });
  }
  // Wait for theme transition to complete
  await page.waitForTimeout(300);
}

// Helper: apply direction before screenshot
async function applyDirection(page, dir) {
  await page.evaluate((direction) => {
    document.documentElement.dir = direction;
  }, dir);
  await page.waitForTimeout(100);
}

// Helper: disable animations for consistent screenshots
async function disableAnimations(page) {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
      }
    `,
  });
}

// Generate tests for each showcase page
for (const showcasePage of SHOWCASE_PAGES) {
  test.describe(showcasePage.label, () => {
    test(`screenshot - ${showcasePage.name}`, async ({ page }) => {
      await page.goto(showcasePage.path);
      await disableAnimations(page);
      await page.waitForLoadState('networkidle');

      // Full page screenshot
      await expect(page).toHaveScreenshot(`${showcasePage.name}.png`, {
        fullPage: true,
      });
    });
  });
}

// Additional targeted tests for interactive states
test.describe('Interactive States', () => {
  test('button hover state', async ({ page }) => {
    await page.goto('/ui/buttons/');
    await disableAnimations(page);

    const primaryBtn = page.locator('button:has-text("اصلی")').first();
    await primaryBtn.hover();

    await expect(primaryBtn).toHaveScreenshot('button-primary-hover.png');
  });

  test('input focus state', async ({ page }) => {
    await page.goto('/ui/forms/');
    await disableAnimations(page);

    const input = page.locator('input[name="demo_normal"]');
    await input.focus();

    await expect(input).toHaveScreenshot('input-focus.png');
  });

  test('input error state', async ({ page }) => {
    await page.goto('/ui/forms/');
    await disableAnimations(page);

    const errorInput = page.locator('input[name="demo_error"]');
    await expect(errorInput).toHaveScreenshot('input-error.png');
  });
});

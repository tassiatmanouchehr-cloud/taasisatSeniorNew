/**
 * Component Snapshot Tests
 * Enterprise Service Marketplace Platform
 *
 * Captures snapshots of every reusable component in isolation.
 * Tests across: light/dark themes, RTL/LTR directions, desktop/tablet/mobile.
 *
 * These snapshots become the baseline for detecting visual regressions
 * in future pull requests.
 *
 * Usage:
 *   npx playwright test specs/snapshots.spec.js
 *   npx playwright test specs/snapshots.spec.js --update-snapshots
 */

const { test, expect } = require('@playwright/test');

// Helper: set theme
async function setTheme(page, theme) {
  await page.evaluate((t) => {
    if (t === 'dark') {
      document.documentElement.classList.add('dark');
      document.documentElement.setAttribute('data-theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      document.documentElement.setAttribute('data-theme', 'light');
    }
  }, theme);
  await page.waitForTimeout(200);
}

// Helper: set direction
async function setDirection(page, dir) {
  await page.evaluate((d) => { document.documentElement.dir = d; }, dir);
  await page.waitForTimeout(100);
}

// Helper: disable animations
async function disableAnimations(page) {
  await page.addStyleTag({
    content: '*, *::before, *::after { animation: none !important; transition: none !important; }',
  });
}

// Component pages with their key sections to snapshot
const COMPONENT_SECTIONS = [
  {
    page: '/ui/buttons/',
    sections: [
      { selector: 'section:nth-of-type(1)', name: 'button-variants' },
      { selector: 'section:nth-of-type(2)', name: 'button-sizes' },
      { selector: 'section:nth-of-type(3)', name: 'button-states' },
    ],
  },
  {
    page: '/ui/forms/',
    sections: [
      { selector: 'section:nth-of-type(1)', name: 'input-variants' },
      { selector: 'section:nth-of-type(4)', name: 'checkbox-radio-toggle' },
    ],
  },
  {
    page: '/ui/alerts/',
    sections: [
      { selector: 'section:nth-of-type(1)', name: 'alert-types' },
      { selector: 'section:nth-of-type(2)', name: 'badge-variants' },
      { selector: 'section:nth-of-type(4)', name: 'progress-bars' },
    ],
  },
  {
    page: '/ui/cards/',
    sections: [
      { selector: 'section:nth-of-type(1)', name: 'card-variants' },
      { selector: 'section:nth-of-type(2)', name: 'stat-cards' },
    ],
  },
  {
    page: '/ui/avatars/',
    sections: [
      { selector: 'section:nth-of-type(1)', name: 'avatar-sizes' },
      { selector: 'section:nth-of-type(2)', name: 'avatar-types' },
      { selector: 'section:nth-of-type(3)', name: 'avatar-status' },
    ],
  },
  {
    page: '/ui/loading/',
    sections: [
      { selector: 'section:nth-of-type(1)', name: 'spinners' },
      { selector: 'section:nth-of-type(2)', name: 'skeletons' },
    ],
  },
  {
    page: '/ui/empty-states/',
    sections: [
      { selector: 'section:nth-of-type(1)', name: 'empty-states-grid' },
    ],
  },
];

// Theme/direction matrix
const MODES = [
  { theme: 'light', dir: 'rtl', suffix: 'light-rtl' },
  { theme: 'dark', dir: 'rtl', suffix: 'dark-rtl' },
  { theme: 'light', dir: 'ltr', suffix: 'light-ltr' },
];

// Generate snapshot tests for each component section × mode
for (const component of COMPONENT_SECTIONS) {
  for (const section of component.sections) {
    for (const mode of MODES) {
      test(`snapshot: ${section.name} [${mode.suffix}]`, async ({ page }) => {
        await page.goto(component.page);
        await disableAnimations(page);
        await setTheme(page, mode.theme);
        await setDirection(page, mode.dir);
        await page.waitForLoadState('networkidle');

        const element = page.locator(section.selector).first();
        await expect(element).toBeVisible();

        await expect(element).toHaveScreenshot(
          `${section.name}-${mode.suffix}.png`,
          { animations: 'disabled' }
        );
      });
    }
  }
}

// Full page snapshots for key pages (desktop only)
const FULL_PAGE_SNAPSHOTS = [
  '/ui/buttons/',
  '/ui/forms/',
  '/ui/cards/',
  '/ui/alerts/',
  '/ui/avatars/',
];

for (const pagePath of FULL_PAGE_SNAPSHOTS) {
  const pageName = pagePath.replace('/ui/', '').replace('/', '');

  test(`full-page snapshot: ${pageName} [light-rtl]`, async ({ page }) => {
    await page.goto(pagePath);
    await disableAnimations(page);
    await setTheme(page, 'light');
    await setDirection(page, 'rtl');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot(`fullpage-${pageName}-light-rtl.png`, {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test(`full-page snapshot: ${pageName} [dark-rtl]`, async ({ page }) => {
    await page.goto(pagePath);
    await disableAnimations(page);
    await setTheme(page, 'dark');
    await setDirection(page, 'rtl');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot(`fullpage-${pageName}-dark-rtl.png`, {
      fullPage: true,
      animations: 'disabled',
    });
  });
}

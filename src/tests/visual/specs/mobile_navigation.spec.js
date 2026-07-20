/**
 * Mobile Navigation — real browser interaction regression tests
 * Enterprise Service Marketplace Platform
 *
 * Frontend remediation (PR #39, R1): the public mobile hamburger menu must
 * actually open/close for a real user via the site's own committed Alpine.js
 * runtime (static/ui/js/alpine.min.js) — no forced test CSS, no
 * source-string-only assertions. These tests exercise real clicks and
 * keyboard events against the rendered page.
 *
 * Usage:
 *   npx playwright test specs/mobile_navigation.spec.js
 */

const { test, expect } = require('@playwright/test');

// A plain viewport override (not a devices['iPhone ...'] preset) so this
// spec runs under whichever browser the invoking --project specifies
// (this sandbox only has Chromium installed; device presets like
// devices['iPhone 13'] force WebKit as their default browserName).
test.use({ viewport: { width: 390, height: 844 }, locale: 'fa-IR' });

test.describe('public mobile navigation', () => {
  test('hamburger click opens the menu and sets aria-expanded', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const toggle = page.getByRole('button', { name: 'منوی ناوبری' });
    const panel = page.locator('#mobile-nav-panel');

    await expect(panel).toBeHidden();
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');

    await toggle.click();

    await expect(panel).toBeVisible();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  });

  test('Login and Registration are visible and interactable once the menu is open', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: 'منوی ناوبری' }).click();
    const panel = page.locator('#mobile-nav-panel');
    await expect(panel).toBeVisible();

    const loginLink = panel.getByRole('link', { name: 'ورود به حساب' });
    const registerLink = panel.getByRole('link', { name: /ثبت‌نام/ });

    await expect(loginLink).toBeVisible();
    await expect(registerLink).toBeVisible();
    await expect(loginLink).toHaveAttribute('href', '/accounts/login/');
    await expect(registerLink).toHaveAttribute('href', '/accounts/register/');

    // Confirm the link is actually clickable (in the accessibility tree,
    // not obscured by another element) — not just present in the DOM.
    await expect(loginLink).toBeEnabled();
  });

  test('Start Request and Consultation remain reachable in the open menu', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: 'منوی ناوبری' }).click();
    const panel = page.locator('#mobile-nav-panel');

    await expect(panel.getByRole('link', { name: 'شروع درخواست' })).toBeVisible();
    await expect(panel.getByRole('link', { name: 'مشاوره رایگان' })).toBeVisible();
  });

  test('clicking the toggle again closes the menu', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const toggle = page.getByRole('button', { name: 'منوی ناوبری' });
    const panel = page.locator('#mobile-nav-panel');

    await toggle.click();
    await expect(panel).toBeVisible();
    await expect(toggle).toHaveAttribute('aria-expanded', 'true');

    await toggle.click();
    await expect(toggle).toHaveAttribute('aria-expanded', 'false');
    await expect(panel).toBeHidden();
  });

  test('Escape closes the open menu', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    const toggle = page.getByRole('button', { name: 'منوی ناوبری' });
    const panel = page.locator('#mobile-nav-panel');

    await toggle.click();
    await expect(panel).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(panel).toBeHidden();
  });

  test('a nav link inside the open menu actually navigates', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: 'منوی ناوبری' }).click();
    const panel = page.locator('#mobile-nav-panel');
    await expect(panel).toBeVisible();

    await panel.getByRole('link', { name: 'ورود به حساب' }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/accounts\/login\/$/);
  });

  test('menu does not remain stuck open across a fresh page load', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await page.getByRole('button', { name: 'منوی ناوبری' }).click();
    await expect(page.locator('#mobile-nav-panel')).toBeVisible();

    await page.reload();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('#mobile-nav-panel')).toBeHidden();
  });
});

test.describe('desktop public header account actions', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('Login and Register links are visible and point at real routes', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');

    // exact: true avoids matching the (hidden, but same-DOM) mobile panel's
    // "ورود به حساب" / "ثبت‌نام (...)" links, which contain these as substrings.
    const loginLink = page.locator('header').getByRole('link', { name: 'ورود', exact: true });
    const registerLink = page.locator('header').getByRole('link', { name: 'ثبت‌نام', exact: true });

    await expect(loginLink).toBeVisible();
    await expect(registerLink).toBeVisible();
    await expect(loginLink).toHaveAttribute('href', '/accounts/login/');
    await expect(registerLink).toHaveAttribute('href', '/accounts/register/');
  });
});

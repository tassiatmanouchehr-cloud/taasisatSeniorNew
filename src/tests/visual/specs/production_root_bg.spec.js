/**
 * Diagnostic: Verify production page root background in WebKit dark mode.
 * 
 * This test navigates to a real production page (login) and captures
 * computed styles for <html> and <body> to determine whether the
 * WebKit transparent-body issue affects production layouts.
 *
 * Temporary — remove after verification.
 */
const { test, expect } = require('@playwright/test');

test.describe('production root background verification', () => {
  test('login page computed styles in dark WebKit', async ({ page, browserName }) => {
    // Navigate to the login page (a real production route)
    await page.goto('/accounts/login/');
    await page.waitForLoadState('networkidle');

    const diagnostics = await page.evaluate(() => {
      const html = document.documentElement;
      const body = document.body;

      const htmlCS = window.getComputedStyle(html);
      const bodyCS = window.getComputedStyle(body);

      return {
        browser: navigator.userAgent.includes('WebKit') ? 'WebKit' : 'Other',
        htmlClass: html.className,
        htmlDataTheme: html.getAttribute('data-theme'),
        htmlBgColor: htmlCS.backgroundColor,
        htmlColor: htmlCS.color,
        bodyClass: body.className.substring(0, 200),
        bodyBgColor: bodyCS.backgroundColor,
        bodyColor: bodyCS.color,
        cssVars: {
          '--color-background': htmlCS.getPropertyValue('--color-background').trim(),
          '--color-text': htmlCS.getPropertyValue('--color-text').trim(),
        },
        bodyBgIsTransparent: bodyCS.backgroundColor === 'rgba(0, 0, 0, 0)' || bodyCS.backgroundColor === 'transparent',
        htmlBgIsTransparent: htmlCS.backgroundColor === 'rgba(0, 0, 0, 0)' || htmlCS.backgroundColor === 'transparent',
      };
    });

    // Log results to CI output
    console.log('\n===== PRODUCTION ROOT BG DIAGNOSTIC =====');
    console.log(`Browser engine: ${browserName} (${diagnostics.browser})`);
    console.log(`HTML class: "${diagnostics.htmlClass}"`);
    console.log(`HTML data-theme: "${diagnostics.htmlDataTheme}"`);
    console.log(`HTML background-color: ${diagnostics.htmlBgColor}`);
    console.log(`HTML color: ${diagnostics.htmlColor}`);
    console.log(`HTML bg transparent: ${diagnostics.htmlBgIsTransparent}`);
    console.log(`Body class: "${diagnostics.bodyClass}"`);
    console.log(`Body background-color: ${diagnostics.bodyBgColor}`);
    console.log(`Body color: ${diagnostics.bodyColor}`);
    console.log(`Body bg transparent: ${diagnostics.bodyBgIsTransparent}`);
    console.log(`CSS vars: --color-background=${diagnostics.cssVars['--color-background']}, --color-text=${diagnostics.cssVars['--color-text']}`);
    console.log('===== END DIAGNOSTIC =====\n');

    // The test passes regardless — it's for diagnostic output only
    expect(true).toBe(true);
  });
});

/**
 * Diagnostic test — captures computed styles for dark-mode contrast investigation.
 * This test is temporary and should be removed after the root cause is identified.
 */
const { test, expect } = require('@playwright/test');

// Only run on the affected projects
test.describe('dark-mode forms diagnostic', () => {
  test('capture computed styles on /ui/forms/ in dark mode', async ({ page, browserName }) => {
    await page.goto('/ui/forms/');
    await page.waitForLoadState('networkidle');

    const diagnostics = await page.evaluate(() => {
      const html = document.documentElement;
      const body = document.body;
      const main = document.querySelector('main');
      const h1 = document.querySelector('h1');
      const firstLabel = document.querySelector('label');

      function getStyles(el, name) {
        if (!el) return { element: name, error: 'not found' };
        const cs = window.getComputedStyle(el);
        return {
          element: name,
          tagName: el.tagName,
          className: el.className.substring(0, 200),
          computedBgColor: cs.backgroundColor,
          computedColor: cs.color,
          computedFontSize: cs.fontSize,
          computedColorScheme: cs.colorScheme,
        };
      }

      return {
        htmlHasClass: html.className,
        htmlDataTheme: html.getAttribute('data-theme'),
        htmlDir: html.dir,
        prefersDark: window.matchMedia('(prefers-color-scheme: dark)').matches,
        colorSchemeMetaContent: document.querySelector('meta[name="color-scheme"]')?.content || 'NOT PRESENT',
        elements: [
          getStyles(html, 'html'),
          getStyles(body, 'body'),
          getStyles(main, 'main'),
          getStyles(h1, 'h1'),
          getStyles(firstLabel, 'label'),
        ],
        cssVariables: {
          '--color-text': getComputedStyle(html).getPropertyValue('--color-text').trim(),
          '--color-text-muted': getComputedStyle(html).getPropertyValue('--color-text-muted').trim(),
          '--color-background': getComputedStyle(html).getPropertyValue('--color-background').trim(),
          '--color-surface': getComputedStyle(html).getPropertyValue('--color-surface').trim(),
        },
      };
    });

    // Output to CI log
    console.log('\n========== DARK MODE FORMS DIAGNOSTIC ==========');
    console.log(`Browser: ${browserName}`);
    console.log(`HTML class: "${diagnostics.htmlHasClass}"`);
    console.log(`HTML data-theme: "${diagnostics.htmlDataTheme}"`);
    console.log(`prefers-color-scheme dark: ${diagnostics.prefersDark}`);
    console.log(`color-scheme meta: ${diagnostics.colorSchemeMetaContent}`);
    console.log('\nCSS Variables:');
    for (const [k, v] of Object.entries(diagnostics.cssVariables)) {
      console.log(`  ${k}: ${v}`);
    }
    console.log('\nElements:');
    for (const el of diagnostics.elements) {
      console.log(`  ${el.element} (${el.tagName}):`);
      console.log(`    class: ${el.className}`);
      console.log(`    background-color: ${el.computedBgColor}`);
      console.log(`    color: ${el.computedColor}`);
      console.log(`    color-scheme: ${el.computedColorScheme}`);
    }
    console.log('========== END DIAGNOSTIC ==========\n');

    // This test always passes — it's for diagnostic output only
    expect(true).toBe(true);
  });
});

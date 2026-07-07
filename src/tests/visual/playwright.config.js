/**
 * Playwright Visual Regression Configuration
 * Enterprise Service Marketplace Platform
 *
 * Captures baseline screenshots for the UI component showcase
 * across multiple dimensions:
 * - Themes: light, dark
 * - Directions: RTL, LTR
 * - Viewports: desktop (1280), tablet (768), mobile (375)
 *
 * Run: npx playwright test
 * Update baselines: npx playwright test --update-snapshots
 *
 * Prerequisites:
 *   - Django runserver at http://localhost:8000
 *   - Tailwind CSS compiled (npm run css:build)
 *   - npm install @playwright/test
 */

const { defineConfig, devices } = require('@playwright/test');

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:8000';

module.exports = defineConfig({
  testDir: './specs',
  outputDir: './results',
  snapshotDir: './baselines',
  snapshotPathTemplate: '{snapshotDir}/{testFilePath}/{arg}-{projectName}{ext}',

  // Timeout per test
  timeout: 30000,
  expect: {
    timeout: 5000,
    toHaveScreenshot: {
      // Allow slight pixel differences (anti-aliasing, font rendering)
      maxDiffPixelRatio: 0.01,
      threshold: 0.2,
    },
  },

  // Run tests in parallel
  fullyParallel: true,
  workers: process.env.CI ? 1 : undefined,

  // Reporter
  reporter: [
    ['html', { outputFolder: './report' }],
    ['list'],
  ],

  // Shared settings
  use: {
    baseURL: BASE_URL,
    // Capture screenshot on failure
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
    // Disable animations for consistent screenshots
    actionTimeout: 10000,
  },

  // Project matrix: theme × direction × viewport
  projects: [
    // Desktop (1280×720)
    {
      name: 'desktop-light-rtl',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 720 },
        colorScheme: 'light',
        locale: 'fa-IR',
      },
    },
    {
      name: 'desktop-dark-rtl',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 720 },
        colorScheme: 'dark',
        locale: 'fa-IR',
      },
    },
    {
      name: 'desktop-light-ltr',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 720 },
        colorScheme: 'light',
        locale: 'en-US',
      },
    },

    // Tablet (768×1024)
    {
      name: 'tablet-light-rtl',
      use: {
        ...devices['iPad Mini'],
        colorScheme: 'light',
        locale: 'fa-IR',
      },
    },
    {
      name: 'tablet-dark-rtl',
      use: {
        ...devices['iPad Mini'],
        colorScheme: 'dark',
        locale: 'fa-IR',
      },
    },

    // Mobile (375×667)
    {
      name: 'mobile-light-rtl',
      use: {
        ...devices['iPhone 13'],
        colorScheme: 'light',
        locale: 'fa-IR',
      },
    },
    {
      name: 'mobile-dark-rtl',
      use: {
        ...devices['iPhone 13'],
        colorScheme: 'dark',
        locale: 'fa-IR',
      },
    },
  ],
});

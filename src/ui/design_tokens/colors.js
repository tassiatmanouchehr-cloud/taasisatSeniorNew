/**
 * Color Design Tokens
 *
 * All colors are defined as CSS variable references.
 * Actual values are set in theme files (light.css, dark.css).
 * This enables runtime theme switching without rebuilding CSS.
 *
 * Naming convention:
 * - Semantic names (primary, secondary, accent) not raw colors
 * - Scales from 50 (lightest) to 950 (darkest)
 * - Surface/background for layout areas
 * - State colors for feedback (success, warning, danger, info)
 */

module.exports = {
  // Brand colors — resolved from CSS variables for theme switching
  primary: {
    50: 'var(--color-primary-50)',
    100: 'var(--color-primary-100)',
    200: 'var(--color-primary-200)',
    300: 'var(--color-primary-300)',
    400: 'var(--color-primary-400)',
    500: 'var(--color-primary-500)',
    600: 'var(--color-primary-600)',
    700: 'var(--color-primary-700)',
    800: 'var(--color-primary-800)',
    900: 'var(--color-primary-900)',
    950: 'var(--color-primary-950)',
    DEFAULT: 'var(--color-primary-600)',
  },
  secondary: {
    50: 'var(--color-secondary-50)',
    100: 'var(--color-secondary-100)',
    200: 'var(--color-secondary-200)',
    300: 'var(--color-secondary-300)',
    400: 'var(--color-secondary-400)',
    500: 'var(--color-secondary-500)',
    600: 'var(--color-secondary-600)',
    700: 'var(--color-secondary-700)',
    800: 'var(--color-secondary-800)',
    900: 'var(--color-secondary-900)',
    950: 'var(--color-secondary-950)',
    DEFAULT: 'var(--color-secondary-600)',
  },
  accent: {
    50: 'var(--color-accent-50)',
    100: 'var(--color-accent-100)',
    200: 'var(--color-accent-200)',
    300: 'var(--color-accent-300)',
    400: 'var(--color-accent-400)',
    500: 'var(--color-accent-500)',
    600: 'var(--color-accent-600)',
    700: 'var(--color-accent-700)',
    800: 'var(--color-accent-800)',
    900: 'var(--color-accent-900)',
    950: 'var(--color-accent-950)',
    DEFAULT: 'var(--color-accent-500)',
  },

  // State/feedback colors
  success: {
    50: 'var(--color-success-50)',
    100: 'var(--color-success-100)',
    200: 'var(--color-success-200)',
    500: 'var(--color-success-500)',
    600: 'var(--color-success-600)',
    700: 'var(--color-success-700)',
    DEFAULT: 'var(--color-success-700)',
  },
  warning: {
    50: 'var(--color-warning-50)',
    100: 'var(--color-warning-100)',
    200: 'var(--color-warning-200)',
    500: 'var(--color-warning-500)',
    600: 'var(--color-warning-600)',
    700: 'var(--color-warning-700)',
    DEFAULT: 'var(--color-warning-700)',
  },
  danger: {
    50: 'var(--color-danger-50)',
    100: 'var(--color-danger-100)',
    200: 'var(--color-danger-200)',
    500: 'var(--color-danger-500)',
    600: 'var(--color-danger-600)',
    700: 'var(--color-danger-700)',
    DEFAULT: 'var(--color-danger-700)',
  },
  info: {
    50: 'var(--color-info-50)',
    100: 'var(--color-info-100)',
    200: 'var(--color-info-200)',
    500: 'var(--color-info-500)',
    600: 'var(--color-info-600)',
    700: 'var(--color-info-700)',
    DEFAULT: 'var(--color-info-600)',
  },

  // Surface/layout colors — adapt to light/dark theme
  surface: {
    DEFAULT: 'var(--color-surface)',
    raised: 'var(--color-surface-raised)',
    overlay: 'var(--color-surface-overlay)',
    sunken: 'var(--color-surface-sunken)',
  },
  background: {
    DEFAULT: 'var(--color-background)',
    alt: 'var(--color-background-alt)',
  },
  border: {
    DEFAULT: 'var(--color-border)',
    light: 'var(--color-border-light)',
    strong: 'var(--color-border-strong)',
  },

  // Text colors
  text: {
    DEFAULT: 'var(--color-text)',
    muted: 'var(--color-text-muted)',
    inverse: 'var(--color-text-inverse)',
    disabled: 'var(--color-text-disabled)',
    link: 'var(--color-text-link)',
  },
};

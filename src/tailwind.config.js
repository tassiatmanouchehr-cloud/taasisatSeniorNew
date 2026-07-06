/**
 * Tailwind CSS Configuration
 * Enterprise Service Marketplace Platform
 *
 * All design tokens are imported from ui/design_tokens/.
 * Colors use CSS variables for runtime theme switching.
 * Typography is Persian-optimized (IRANSansX/Vazirmatn).
 */

const tokens = require('./ui/design_tokens');

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './ui/components/**/*.html',
    './ui/layouts/**/*.html',
    './ui/js/**/*.js',
  ],
  darkMode: 'class',
  theme: {
    // Override defaults with our tokens
    screens: tokens.screens,
    fontFamily: tokens.fontFamily,
    fontSize: tokens.fontSize,
    fontWeight: tokens.fontWeight,
    lineHeight: tokens.lineHeight,
    letterSpacing: tokens.letterSpacing,
    zIndex: tokens.zIndex,
    opacity: tokens.opacity,

    extend: {
      // Colors — CSS variable based for theme switching
      colors: tokens.colors,

      // Spacing (extends default, doesn't override)
      spacing: tokens.spacing,

      // Border radius
      borderRadius: tokens.borderRadius,

      // Shadows — theme-aware via CSS variables
      boxShadow: tokens.boxShadow,

      // Containers
      maxWidth: tokens.maxWidth,

      // Animation
      transitionDuration: tokens.transitionDuration,
      transitionTimingFunction: tokens.transitionTimingFunction,
      keyframes: tokens.keyframes,
      animation: tokens.animation,
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
    require('@tailwindcss/typography'),
  ],
};

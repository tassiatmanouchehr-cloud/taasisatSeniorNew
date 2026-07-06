/**
 * Container / Layout Size Design Tokens
 *
 * Max-width values for content containers.
 * Breakpoints for responsive design.
 * Opacity scale for layering.
 */

module.exports = {
  // Container max-widths
  maxWidth: {
    none: 'none',
    xs: '20rem',      // 320px — mobile compact
    sm: '24rem',      // 384px — small widget
    md: '28rem',      // 448px — modal small
    lg: '32rem',      // 512px — modal medium
    xl: '36rem',      // 576px — modal large
    '2xl': '42rem',   // 672px — content column
    '3xl': '48rem',   // 768px — article width
    '4xl': '56rem',   // 896px — wide content
    '5xl': '64rem',   // 1024px — dashboard panel
    '6xl': '72rem',   // 1152px — wide dashboard
    '7xl': '80rem',   // 1280px — full content
    full: '100%',
    prose: '65ch',    // Optimal reading width
    screen: '100vw',
  },

  // Responsive breakpoints
  screens: {
    'xs': '475px',    // Large phones
    'sm': '640px',    // Tablets (portrait)
    'md': '768px',    // Tablets (landscape)
    'lg': '1024px',   // Desktops
    'xl': '1280px',   // Large desktops
    '2xl': '1536px',  // Ultra-wide
    '3xl': '1920px',  // Full HD+
  },

  // Opacity scale
  opacity: {
    0: '0',
    5: '0.05',
    10: '0.1',
    15: '0.15',
    20: '0.2',
    25: '0.25',
    30: '0.3',
    40: '0.4',
    50: '0.5',
    60: '0.6',
    70: '0.7',
    75: '0.75',
    80: '0.8',
    85: '0.85',
    90: '0.9',
    95: '0.95',
    100: '1',
  },
};

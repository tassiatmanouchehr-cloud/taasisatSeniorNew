/**
 * Typography Design Tokens
 *
 * Persian-optimized type system:
 * - IRANSansX as primary (if available)
 * - Vazirmatn as secondary/fallback
 * - System Persian fonts as final fallback
 * - Correct line heights for Persian text (taller than Latin)
 * - Responsive font sizes using clamp()
 *
 * The font scale follows a modular scale (1.25 ratio).
 */

module.exports = {
  fontFamily: {
    sans: [
      'IRANSansX',
      'Vazirmatn',
      'Tahoma',
      'Arial',
      'sans-serif',
    ],
    mono: [
      'JetBrains Mono',
      'Fira Code',
      'Courier New',
      'monospace',
    ],
    display: [
      'IRANSansX',
      'Vazirmatn',
      'sans-serif',
    ],
  },

  fontSize: {
    // Persian text needs slightly larger sizes and taller line heights
    'xs': ['0.75rem', { lineHeight: '1.5', letterSpacing: '0' }],      // 12px
    'sm': ['0.875rem', { lineHeight: '1.6', letterSpacing: '0' }],     // 14px
    'base': ['1rem', { lineHeight: '1.75', letterSpacing: '0' }],      // 16px
    'lg': ['1.125rem', { lineHeight: '1.75', letterSpacing: '0' }],    // 18px
    'xl': ['1.25rem', { lineHeight: '1.7', letterSpacing: '0' }],      // 20px
    '2xl': ['1.5rem', { lineHeight: '1.6', letterSpacing: '0' }],      // 24px
    '3xl': ['1.875rem', { lineHeight: '1.5', letterSpacing: '0' }],    // 30px
    '4xl': ['2.25rem', { lineHeight: '1.4', letterSpacing: '0' }],     // 36px
    '5xl': ['3rem', { lineHeight: '1.3', letterSpacing: '0' }],        // 48px
    '6xl': ['3.75rem', { lineHeight: '1.2', letterSpacing: '0' }],     // 60px
    '7xl': ['4.5rem', { lineHeight: '1.1', letterSpacing: '0' }],      // 72px
  },

  fontWeight: {
    thin: '100',
    extralight: '200',
    light: '300',
    normal: '400',
    medium: '500',
    semibold: '600',
    bold: '700',
    extrabold: '800',
    black: '900',
  },

  lineHeight: {
    none: '1',
    tight: '1.25',
    snug: '1.375',
    normal: '1.5',
    relaxed: '1.625',
    loose: '1.75',
    // Persian-specific (text needs more breathing room)
    'persian': '1.8',
    'persian-loose': '2',
  },

  letterSpacing: {
    tighter: '-0.05em',
    tight: '-0.025em',
    normal: '0',
    wide: '0.025em',
    wider: '0.05em',
    widest: '0.1em',
  },
};

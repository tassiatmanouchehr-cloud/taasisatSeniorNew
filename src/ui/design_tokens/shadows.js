/**
 * Shadow / Elevation Design Tokens
 *
 * Progressive elevation scale using CSS variables for theme adaptation.
 * Dark mode uses lighter, more subtle shadows.
 * Shadows use logical positioning (work correctly in RTL).
 */

module.exports = {
  // Box shadows — theme-aware via CSS variables
  boxShadow: {
    none: 'none',
    xs: 'var(--shadow-xs)',
    sm: 'var(--shadow-sm)',
    DEFAULT: 'var(--shadow-md)',
    md: 'var(--shadow-md)',
    lg: 'var(--shadow-lg)',
    xl: 'var(--shadow-xl)',
    '2xl': 'var(--shadow-2xl)',
    inner: 'var(--shadow-inner)',
    // Colored shadows for interactive states
    'primary': 'var(--shadow-primary)',
    'danger': 'var(--shadow-danger)',
    'success': 'var(--shadow-success)',
  },

  // Elevation tokens (numbered levels for component documentation)
  // level 0 = flat, level 5 = highest (modals, popovers)
};

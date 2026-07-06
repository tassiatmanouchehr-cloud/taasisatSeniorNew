/**
 * Border Radius Design Tokens
 *
 * Progressive scale from sharp to fully rounded.
 * Used for cards, buttons, inputs, badges, avatars.
 */

module.exports = {
  none: '0',
  xs: '0.125rem',    // 2px — subtle rounding
  sm: '0.25rem',     // 4px — inputs, small elements
  DEFAULT: '0.5rem', // 8px — cards, panels
  md: '0.625rem',    // 10px
  lg: '0.75rem',     // 12px — modals, larger cards
  xl: '1rem',        // 16px — prominent elements
  '2xl': '1.5rem',   // 24px — large containers
  '3xl': '2rem',     // 32px — hero sections
  full: '9999px',    // pill shape (buttons, badges)
};

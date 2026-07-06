/**
 * Animation / Motion Design Tokens
 *
 * Consistent timing and easing for all UI transitions.
 * Respects prefers-reduced-motion media query.
 */

module.exports = {
  transitionDuration: {
    0: '0ms',
    75: '75ms',
    100: '100ms',
    150: '150ms',
    200: '200ms',
    300: '300ms',
    500: '500ms',
    700: '700ms',
    1000: '1000ms',
    // Semantic durations
    'fast': '150ms',
    'normal': '250ms',
    'slow': '400ms',
    'slower': '700ms',
  },

  transitionTimingFunction: {
    DEFAULT: 'cubic-bezier(0.4, 0, 0.2, 1)',
    linear: 'linear',
    in: 'cubic-bezier(0.4, 0, 1, 1)',
    out: 'cubic-bezier(0, 0, 0.2, 1)',
    'in-out': 'cubic-bezier(0.4, 0, 0.2, 1)',
    // Material-inspired curves
    'ease-spring': 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
    'ease-bounce': 'cubic-bezier(0.68, -0.55, 0.265, 1.55)',
  },

  keyframes: {
    'fade-in': {
      '0%': { opacity: '0' },
      '100%': { opacity: '1' },
    },
    'fade-out': {
      '0%': { opacity: '1' },
      '100%': { opacity: '0' },
    },
    'slide-in-start': {
      '0%': { transform: 'translateX(100%)', opacity: '0' },
      '100%': { transform: 'translateX(0)', opacity: '1' },
    },
    'slide-in-end': {
      '0%': { transform: 'translateX(-100%)', opacity: '0' },
      '100%': { transform: 'translateX(0)', opacity: '1' },
    },
    'slide-up': {
      '0%': { transform: 'translateY(10px)', opacity: '0' },
      '100%': { transform: 'translateY(0)', opacity: '1' },
    },
    'slide-down': {
      '0%': { transform: 'translateY(-10px)', opacity: '0' },
      '100%': { transform: 'translateY(0)', opacity: '1' },
    },
    'scale-in': {
      '0%': { transform: 'scale(0.95)', opacity: '0' },
      '100%': { transform: 'scale(1)', opacity: '1' },
    },
    'spin': {
      '0%': { transform: 'rotate(0deg)' },
      '100%': { transform: 'rotate(360deg)' },
    },
    'pulse': {
      '0%, 100%': { opacity: '1' },
      '50%': { opacity: '0.5' },
    },
    'bounce': {
      '0%, 100%': { transform: 'translateY(-5%)', animationTimingFunction: 'cubic-bezier(0.8,0,1,1)' },
      '50%': { transform: 'translateY(0)', animationTimingFunction: 'cubic-bezier(0,0,0.2,1)' },
    },
    'shimmer': {
      '0%': { backgroundPosition: '-200% 0' },
      '100%': { backgroundPosition: '200% 0' },
    },
  },

  animation: {
    'fade-in': 'fade-in 0.2s ease-out',
    'fade-out': 'fade-out 0.15s ease-in',
    'slide-in-start': 'slide-in-start 0.3s ease-out',
    'slide-in-end': 'slide-in-end 0.3s ease-out',
    'slide-up': 'slide-up 0.2s ease-out',
    'slide-down': 'slide-down 0.2s ease-out',
    'scale-in': 'scale-in 0.2s ease-out',
    'spin': 'spin 1s linear infinite',
    'pulse': 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite',
    'bounce': 'bounce 1s infinite',
    'shimmer': 'shimmer 2s infinite linear',
  },
};

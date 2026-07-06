/**
 * Theme Engine — JavaScript Controller
 *
 * Handles theme switching between light, dark, and system (auto) modes.
 * Persists user preference in localStorage.
 * Detects system preference via matchMedia.
 * Applies theme by toggling .dark class on <html> and setting data-theme attribute.
 *
 * Usage with Alpine.js:
 *   <div x-data="themeEngine()">
 *     <button @click="setTheme('light')">Light</button>
 *     <button @click="setTheme('dark')">Dark</button>
 *     <button @click="setTheme('auto')">Auto</button>
 *   </div>
 *
 * Usage without Alpine (standalone):
 *   ThemeEngine.init();
 *   ThemeEngine.setTheme('dark');
 *   ThemeEngine.getTheme(); // 'dark'
 */

const THEME_KEY = 'marketplace-theme';
const THEMES = ['light', 'dark', 'auto'];

/**
 * Detect system color scheme preference.
 * @returns {'light' | 'dark'}
 */
function getSystemPreference() {
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'light';
}

/**
 * Get stored theme preference from localStorage.
 * @returns {'light' | 'dark' | 'auto'}
 */
function getStoredTheme() {
  const stored = localStorage.getItem(THEME_KEY);
  if (stored && THEMES.includes(stored)) {
    return stored;
  }
  return 'auto';
}

/**
 * Resolve the effective theme (handles 'auto' by checking system preference).
 * @param {'light' | 'dark' | 'auto'} theme
 * @returns {'light' | 'dark'}
 */
function resolveTheme(theme) {
  if (theme === 'auto') {
    return getSystemPreference();
  }
  return theme;
}

/**
 * Apply theme to the document.
 * - Sets .dark class on <html> for Tailwind darkMode: 'class'
 * - Sets data-theme attribute for CSS variable selectors
 * @param {'light' | 'dark'} effectiveTheme
 */
function applyTheme(effectiveTheme) {
  const html = document.documentElement;

  if (effectiveTheme === 'dark') {
    html.classList.add('dark');
    html.setAttribute('data-theme', 'dark');
  } else {
    html.classList.remove('dark');
    html.setAttribute('data-theme', 'light');
  }
}

/**
 * ThemeEngine — Standalone API (no framework dependency)
 */
const ThemeEngine = {
  /**
   * Initialize the theme engine.
   * Reads stored preference, applies it, listens for system changes.
   */
  init() {
    const preference = getStoredTheme();
    const effective = resolveTheme(preference);
    applyTheme(effective);

    // Listen for system preference changes (only matters when theme is 'auto')
    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
        const current = getStoredTheme();
        if (current === 'auto') {
          applyTheme(e.matches ? 'dark' : 'light');
        }
      });
    }
  },

  /**
   * Set the theme preference.
   * @param {'light' | 'dark' | 'auto'} theme
   */
  setTheme(theme) {
    if (!THEMES.includes(theme)) {
      console.warn(`Invalid theme: ${theme}. Use 'light', 'dark', or 'auto'.`);
      return;
    }
    localStorage.setItem(THEME_KEY, theme);
    const effective = resolveTheme(theme);
    applyTheme(effective);
  },

  /**
   * Get the current theme preference (not effective — may be 'auto').
   * @returns {'light' | 'dark' | 'auto'}
   */
  getTheme() {
    return getStoredTheme();
  },

  /**
   * Get the effective applied theme.
   * @returns {'light' | 'dark'}
   */
  getEffectiveTheme() {
    return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
  },

  /**
   * Toggle between light and dark (ignores auto).
   */
  toggle() {
    const current = this.getEffectiveTheme();
    this.setTheme(current === 'dark' ? 'light' : 'dark');
  },
};

/**
 * Alpine.js component for theme switching.
 * Use: <div x-data="themeEngine()">
 */
function themeEngine() {
  return {
    theme: getStoredTheme(),
    effectiveTheme: resolveTheme(getStoredTheme()),

    init() {
      // Apply on component mount
      applyTheme(this.effectiveTheme);

      // Watch for system changes
      if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
          if (this.theme === 'auto') {
            this.effectiveTheme = e.matches ? 'dark' : 'light';
            applyTheme(this.effectiveTheme);
          }
        });
      }
    },

    setTheme(newTheme) {
      if (!THEMES.includes(newTheme)) return;
      this.theme = newTheme;
      this.effectiveTheme = resolveTheme(newTheme);
      localStorage.setItem(THEME_KEY, newTheme);
      applyTheme(this.effectiveTheme);
    },

    isLight() { return this.effectiveTheme === 'light'; },
    isDark() { return this.effectiveTheme === 'dark'; },
    isAuto() { return this.theme === 'auto'; },

    toggle() {
      this.setTheme(this.effectiveTheme === 'dark' ? 'light' : 'dark');
    },
  };
}

// Auto-initialize on page load (before Alpine mounts)
if (typeof document !== 'undefined') {
  // Apply theme immediately to prevent flash of wrong theme
  const preference = getStoredTheme();
  const effective = resolveTheme(preference);
  applyTheme(effective);
}

// Export for module systems (optional)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { ThemeEngine, themeEngine };
}

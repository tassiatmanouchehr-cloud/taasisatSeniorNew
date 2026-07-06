# Theme Engine

## How Theming Works

1. **Design tokens** (JS) define color names as CSS variable references
2. **Theme files** (CSS) set the actual CSS variable values
3. **Components** use Tailwind classes that resolve to theme variables
4. **Theme switcher** (JS) toggles `.dark` class on `<html>`

Changing a theme = changing one CSS file. Zero template changes.

## Theme Files

| File | Applies When | Variables |
|------|-------------|-----------|
| `themes/base.css` | Always | Structural vars (widths, heights, borders) |
| `themes/light.css` | `:root` / `[data-theme="light"]` | 71 color + shadow variables |
| `themes/dark.css` | `.dark` / `[data-theme="dark"]` | 71 color + shadow variables (inverted) |

## CSS Variable Categories

```
--color-primary-{50-950}   Brand primary (11 steps)
--color-secondary-{50-950} Brand secondary (11 steps)
--color-accent-{50-950}    Brand accent (11 steps)
--color-success-{50,100,200,500,600,700}
--color-warning-{...}
--color-danger-{...}
--color-info-{...}
--color-surface            Card/panel background
--color-surface-raised     Elevated surface
--color-surface-overlay    Modal/drawer backdrop
--color-surface-sunken     Recessed area
--color-background         Page background
--color-background-alt     Alternating rows
--color-border             Default border
--color-border-light       Subtle border
--color-border-strong      Emphasized border
--color-text               Primary text
--color-text-muted         Secondary text
--color-text-inverse       Text on primary/dark bg
--color-text-disabled      Disabled text
--color-text-link          Link color
--shadow-{xs,sm,md,lg,xl,2xl,inner}
--shadow-primary           Primary-colored shadow
--ring-color               Focus ring color
--ring-offset-color        Focus ring offset
```

## Theme Switching

### JavaScript API

```javascript
// Standalone
ThemeEngine.setTheme('dark');  // 'light' | 'dark' | 'auto'
ThemeEngine.toggle();
ThemeEngine.getEffectiveTheme(); // 'light' or 'dark'

// Alpine.js component
<div x-data="themeEngine()">
  <button @click="setTheme('dark')">تاریک</button>
  <button @click="setTheme('light')">روشن</button>
  <button @click="setTheme('auto')">خودکار</button>
</div>
```

### Persistence

- Stored in `localStorage` key: `marketplace-theme`
- Auto-detects system preference via `matchMedia('prefers-color-scheme: dark')`
- `auto` mode follows system and updates on change

### Flash Prevention

`theme.js` is loaded in `<head>` (not deferred) to apply theme BEFORE page renders.

## Creating a Custom Theme

1. Copy `themes/light.css`
2. Change the CSS variable values
3. Add a selector: `[data-theme="brand-name"] { ... }`
4. Register in ThemeEngine (add to THEMES array)

## White-Label Support

For tenant-specific branding, override variables at runtime:
```html
<style>
  :root {
    --color-primary-500: #your-brand-color;
    --color-primary-600: #your-brand-darker;
  }
</style>
```

# Design System

## Token Architecture

All visual decisions are encoded as **design tokens** — single-source-of-truth values consumed by Tailwind CSS.

### Token Files

| File | Contains |
|------|----------|
| `colors.js` | Semantic colors via CSS variables (primary, secondary, accent, states, surfaces) |
| `spacing.js` | 4px base unit, 40+ values (0–96) |
| `radius.js` | none → xs → sm → md → lg → xl → 2xl → 3xl → full |
| `shadows.js` | Elevation scale via CSS variables (xs–2xl + colored) |
| `z_index.js` | Named layers (base < dropdown < sticky < overlay < modal < toast < tooltip) |
| `typography.js` | Font families, sizes (xs–7xl), weights, line heights, letter spacing |
| `animation.js` | Durations, easings, keyframes, named animations |
| `containers.js` | Max-widths, breakpoints (xs–3xl), opacity scale |

### Color System

Colors use **CSS variables** — never hardcoded hex values in Tailwind config.

```
Token (JS)              → CSS Variable              → Resolved by Theme
colors.primary.500     → var(--color-primary-500)  → #3b82f6 (light) / #3b82f6 (dark)
colors.text.DEFAULT    → var(--color-text)         → #1e293b (light) / #f1f5f9 (dark)
```

Changing `themes/light.css` or `themes/dark.css` changes ALL colors instantly.

### Spacing

Base: 4px (0.25rem). Scale: `0, 0.5, 1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10, 12, 14, 16, 20, 24, 32, 40, 48, 56, 64, 72, 80, 96`

### Breakpoints

| Name | Width | Use Case |
|------|-------|----------|
| xs | 475px | Large phones |
| sm | 640px | Tablets portrait |
| md | 768px | Tablets landscape |
| lg | 1024px | Desktops |
| xl | 1280px | Large desktops |
| 2xl | 1536px | Ultra-wide |
| 3xl | 1920px | Full HD+ |

## Component Categories

| Category | Components | Count |
|----------|-----------|-------|
| Forms | button, input, textarea, select, checkbox, radio, toggle | 7 |
| Feedback | badge, chip, alert, toast, loader, skeleton, progress | 7 |
| Overlays | modal, drawer, dropdown, dropdown_item, tooltip, accordion, tabs | 7 |
| Data | table, pagination, card, stat_card, timeline, empty_state, avatar, breadcrumb | 8 |
| **Total** | | **29** |

## Component API Pattern

Every component uses Django `{% include %}` with `with` keyword for props:

```html
{% include "ui/components/forms/input.html" with
    name="email"
    label="ایمیل"
    type="email"
    placeholder="email@example.com"
    required=True
    error=form.email.errors.0
%}
```

## Quality Checklist (Every Component)

- [x] RTL (logical CSS, no left/right)
- [x] Dark mode (theme CSS variables)
- [x] Light mode
- [x] Accessible (aria, role, label, keyboard)
- [x] Responsive (works xs through 3xl)
- [x] HTMX compatible (standard HTML)
- [x] Alpine compatible (x-data, x-show, x-model)

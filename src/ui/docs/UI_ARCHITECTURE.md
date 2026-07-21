# UI Architecture

## Overview

The UI layer is a **standalone, reusable Enterprise Design System** separated from business modules. It provides the visual foundation for hundreds of future pages without any business logic coupling.

## Stack

| Technology | Role |
|-----------|------|
| Tailwind CSS 3.4 | Utility-first styling, design tokens |
| HTMX | Server-driven partial updates |
| Alpine.js | Client-side reactivity, component state |
| Django Templates | Server-side rendering, includes/blocks |
| PostCSS | CSS build pipeline |

## Directory Structure

```
src/ui/
├── design_tokens/     — Color, spacing, typography JS modules (→ Tailwind)
├── themes/            — CSS variable theme files (light, dark, custom)
├── css/
│   ├── main.css       — Tailwind entry + imports
│   ├── typography.css — @font-face + type system
│   ├── rtl.css        — Logical CSS + RTL utilities
│   └── accessibility.css — Focus, screen reader, contrast
├── js/
│   ├── theme.js       — Theme switcher (standalone + Alpine)
│   └── jalali.js      — Jalali date display (no deps)
├── components/
│   ├── forms/         — button, input, textarea, select, checkbox, radio, toggle
│   ├── feedback/      — badge, chip, alert, toast, loader, skeleton, progress
│   ├── overlays/      — modal, drawer, dropdown, tooltip, accordion, tabs
│   └── data/          — table, pagination, card, stat-card, timeline, empty-state, avatar, breadcrumb
├── layouts/           — base, public, portal, dashboard, admin, auth, error
├── fonts/             — IRANSansX, Vazirmatn, JetBrains Mono
├── icons/             — SVG icon system (future)
└── docs/              — This documentation
```

## Principles

1. **Theme-driven** — Changing one CSS file changes the entire platform appearance
2. **RTL-first** — All CSS uses logical properties; no left/right physical values
3. **Component-based** — Django `{% include %}` for reusable UI parts
4. **Dark-mode ready** — Every component adapts via CSS variables
5. **Accessible** — WCAG AA, keyboard navigable, screen reader compatible
6. **Responsive** — Mobile-first, 7 breakpoints (xs through 3xl)
7. **No business logic** — UI layer has zero domain knowledge

## Build

```bash
npm install                          # Install Tailwind + plugins
npx tailwindcss -i ui/css/main.css -o static/css/output.css --watch
```

## Import Order (main.css)

```
@tailwind base
themes/base.css       → structural variables
themes/light.css      → default color variables
themes/dark.css       → dark mode overrides
css/typography.css    → @font-face + type system
css/rtl.css           → logical CSS + utilities
css/accessibility.css → focus, a11y utilities
@tailwind components
@tailwind utilities
Custom @layer base    → HTML/body defaults
Custom @layer components
Custom @layer utilities → digits-fa, ltr-nums, scrollbar-hide
```

## Component Usage (Django Templates)

```html
{% include "ui/components/forms/button.html" with label="ذخیره" variant="primary" %}
{% include "ui/components/feedback/alert.html" with type="success" message="انجام شد" %}
{% include "ui/components/data/pagination.html" with current=3 total_pages=10 %}
```

## Layout Inheritance

```
base.html
├── public.html    (marketing, catalog)
├── portal.html    (authenticated users)
│   ├── dashboard.html
│   └── admin.html
├── auth.html      (login, register)
└── error.html     (404, 500)
```



## Semantic Token Decisions (PR #34, July 2026)

The following token values were adjusted for WCAG 2.2 AA color contrast compliance.

### Light Theme Token Changes

| Token | Previous Value | Current Value | Rationale |
|-------|---------------|---------------|-----------|
| `--color-text-muted` | `#64748b` | `#536170` | Previous value (4.34:1 on `bg-background`) failed 4.5:1 minimum. New value: 5.79:1 on `bg-background`, 5.14:1 on `bg-background-alt`, 6.34:1 on `bg-surface`. |

### Design Token DEFAULT Shifts

| Token Group | Previous DEFAULT | Current DEFAULT | Rationale |
|-------------|-----------------|-----------------|-----------|
| `success` | `-600` (`#16a34a`) | `-700` (`#15803d`) | Previous value 3.30:1 on white — failed AA. New value 5.02:1. |
| `danger` | `-600` (`#dc2626`) | `-700` (`#b91c1c`) | Previous value 4.41:1 on `bg-background` — failed AA. New value 5.91:1. |
| `warning` | `-600` (`#d97706`) | `-700` (`#b45309`) | Previous value 2.91:1 on `bg-background` — failed AA. New value 4.58:1. |

These changes affect all usages of `text-success`, `text-danger`, `text-warning`, `bg-success`, `bg-danger`, `bg-warning` (the DEFAULT shade). Dark-mode tokens were not changed.

## Known Limitations

### Dark-Mode Contrast: Raw `text-white` on Semantic Backgrounds

Several components and page templates use `text-white` (hardcoded `#ffffff`) on `bg-primary`, `bg-success`, or `bg-danger`. In dark mode, these semantic backgrounds resolve to lighter shades (e.g., `bg-primary` → `#60a5fa`), producing insufficient contrast:

| Pairing | Dark-Mode Contrast | AA Requirement |
|---------|-------------------|----------------|
| `text-white` on `bg-primary` (dark: `#60a5fa`) | 2.54:1 | 4.5:1 |
| `text-white` on `bg-success` (dark: `#86efac`) | 1.40:1 | 4.5:1 |
| `text-white` on `bg-danger` (dark: `#fca5a5`) | 1.90:1 | 4.5:1 |

The canonical `button.html` component uses `text-text-inverse` which resolves correctly in both themes (light: `#ffffff`, dark: `#0f172a`). However, ~55 page templates and 8 public-site components bypass the button component and use inline `bg-primary text-white` markup.

**Replacing `text-white` with `text-text-inverse` is not a drop-in substitution.** It changes the visual appearance of primary buttons in dark mode from white-on-blue to dark-on-blue. Each context requires individual design review to confirm the replacement is acceptable.

This is documented as known accessibility debt pending design review.

### Showcase-Specific WebKit Root Background Workaround

In `templates/showcase/base.html`, the `<html>` element has `class="bg-background"` added during PR #34 accessibility remediation. This was required because WebKit (tablet and mobile viewport projects) computed `<body>` `background-color` as `transparent` on the showcase pages, causing axe-core to treat the page background as white.

This issue did NOT reproduce on the tested production route (`/accounts/login/`) using `ui/layouts/base.html`. Direct CI verification (PR #35, closed without merge) confirmed that production `<body>` correctly receives `background-color: rgb(15, 23, 42)` in WebKit dark mode.

The exact root cause of the showcase-specific behavior remains unproven. Hypotheses include Alpine.js `x-data` on `<html>`, CDN Alpine loading timing, or interaction with the since-removed `color-scheme` meta tag. Current evidence does not justify modifying the shared production root layout (`ui/layouts/base.html`).

### Typography Layer and Tailwind Utility Interaction

The `ui/css/typography.css` layer defines heading sizes using `clamp()`:

```css
h2 { font-size: clamp(1.5rem, 3vw, 2.25rem); }
h3 { font-size: clamp(1.25rem, 2.5vw, 1.875rem); }
```

These rules have higher specificity than Tailwind's preflight reset (`h1,...,h6 { font-size: inherit }`) but lower specificity than Tailwind utility classes (e.g., `text-base`, `text-lg`). When a heading element has NO explicit Tailwind text-size class, the typography layer's `clamp()` values apply.

This means:
- Changing a heading level (e.g., `<h3>` → `<h2>`) changes its rendered size even if both have identical Tailwind classes.
- The showcase index page uses `<h3>` for card headings with a visually-hidden `<h2>` for heading hierarchy compliance, specifically to avoid this size interaction.

## Ruff Configuration (PR #34)

PR #34 added per-file-ignores and rule ignores to `pyproject.toml` to achieve a passing `ruff check .` and `ruff format --check .` in CI. These represent pre-existing codebase patterns that were never compliant, not newly introduced violations:

- `T201` (print): Ignored for CLI tools, management commands, scripts, and celery debug tasks
- `F401` (unused import): Ignored for `__init__.py` re-exports
- Pattern rules (`B904`, `SIM105`, `SIM117`, `E402`, etc.): Ignored where the codebase systematically uses alternative patterns

The CI Lint & Format Check job had never been green on `main` before PR #34.

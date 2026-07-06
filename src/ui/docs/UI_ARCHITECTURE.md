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

# Illustration System

## Architecture

All illustrations in this platform are **inline SVG** rendered via Django template includes. They are NOT external image files. This ensures:

1. **Theme-aware** — Colors use CSS classes that resolve to theme variables
2. **Dark mode** — Automatically adapts (no separate dark illustrations needed)
3. **RTL-compatible** — SVGs don't need mirroring (abstract/symmetric designs)
4. **No external requests** — Zero network overhead, instant render
5. **Accessible** — `aria-hidden="true"` (decorative), meaningful alt via parent

## Directory Structure

```
ui/components/illustrations/
├── README.md              ← This file
├── empty_state_svg.html   ← Empty state illustrations (10 variants)
├── status_svg.html        ← Status/feedback illustrations (future)
├── onboarding_svg.html    ← Onboarding/tutorial illustrations (future)
└── hero_svg.html          ← Hero/marketing illustrations (future)
```

## Color Strategy

Illustrations use **Tailwind CSS classes** for colors, NOT hardcoded hex values:

| Purpose | Light Class | Dark Class | Resolves To |
|---------|------------|------------|-------------|
| Background shape | `fill-background-alt` | auto (theme var) | Light gray / Dark slate |
| Borders/outlines | `stroke-border` | auto | Gray border color |
| Primary accent | `fill-primary` | auto | Brand blue |
| Success | `fill-success` | auto | Green |
| Warning | `fill-warning` | auto | Amber |
| Danger | `fill-danger` | auto | Red |
| Muted elements | `fill-border` | auto | Subtle gray |
| Opacity layers | `opacity-60`, `opacity-40` | auto | Reduced visibility |

## How to Add a New Illustration

1. Create SVG with 120×120 viewBox (standard size)
2. Use only CSS classes for colors (no `fill="#hex"` or `stroke="#hex"`)
3. Keep shapes abstract/geometric (avoids cultural bias)
4. Ensure it reads correctly in both LTR and RTL (prefer symmetric)
5. Add as a new `{% if variant == "your_name" %}` block in the appropriate file
6. Test in both light and dark themes

### Template Pattern

```html
{% if variant == "your_name" %}
<rect x="..." y="..." width="..." height="..." rx="..." 
      class="fill-background-alt stroke-border" stroke-width="2"/>
<circle cx="..." cy="..." r="..." class="fill-primary"/>
{% endif %}
```

## Size System

Illustrations support 3 sizes via the `size` prop:

| Size | Dimensions | Use Case |
|------|-----------|----------|
| `sm` | w-24 h-24 (96px) | Inline/compact empty states |
| `md` | w-32 h-32 (128px) | Standard empty states (default) |
| `lg` | w-40 h-40 (160px) | Full-page empty states, hero areas |

## Available Illustrations

### Empty States (`empty_state_svg.html`)

| Variant | Description | Use Case |
|---------|-------------|----------|
| `no_data` | Empty document/table | Lists, tables with no records |
| `no_search` | Magnifying glass with X | Search results empty |
| `permission` | Lock/shield | Access denied pages |
| `offline` | Cloud with slash | Network disconnected |
| `maintenance` | Gear + wrench | System under maintenance |
| `no_notifications` | Bell with Z's | Notification center empty |
| `no_orders` | Empty clipboard | Order list empty |
| `no_messages` | Empty chat bubble | Inbox/messages empty |
| `error` | Warning triangle | Error pages |
| `success` | Checkmark circle | Success confirmation |

## Design Guidelines

1. **Keep it simple** — max 8-10 SVG elements per illustration
2. **Abstract over literal** — geometric shapes, not realistic drawings
3. **Single focal point** — one main element, supporting elements subtle
4. **Consistent line weight** — `stroke-width="2"` for outlines
5. **No text in SVGs** — text comes from the component props (i18n-safe)
6. **No directional bias** — arrows/chevrons should be avoided in illustrations
7. **Rounded corners** — use `rx` on rects for softness (matches design tokens)

## Future Additions (Planned)

- Onboarding step illustrations
- Error type illustrations (404, 500, 403)
- Success/celebration animations (confetti SVG)
- Feature tour spot illustrations
- Marketing hero illustrations (abstract patterns)

These will be added as business modules require them, following the same pattern.

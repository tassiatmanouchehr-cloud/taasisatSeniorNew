# RTL Guide

## Core Rule

**This platform uses ONLY logical CSS properties.** No `left`, `right`, `margin-left`, `padding-right`, `text-align: right`, `float: left` — ever.

## Logical Property Mapping

| Physical (FORBIDDEN) | Logical (REQUIRED) | Tailwind |
|---------------------|-------------------|----------|
| `margin-left` | `margin-inline-start` | `ms-*` |
| `margin-right` | `margin-inline-end` | `me-*` |
| `padding-left` | `padding-inline-start` | `ps-*` |
| `padding-right` | `padding-inline-end` | `pe-*` |
| `left` | `inset-inline-start` | `start-*` |
| `right` | `inset-inline-end` | `end-*` |
| `border-left` | `border-inline-start` | `border-s-*` |
| `border-right` | `border-inline-end` | `border-e-*` |
| `text-align: left` | `text-align: start` | `text-start` |
| `text-align: right` | `text-align: end` | `text-end` |
| `float: left` | `float: inline-start` | `float-start` |
| `float: right` | `float: inline-end` | `float-end` |

## RTL Utility Classes

| Class | Purpose |
|-------|---------|
| `.icon-mirror` | Flip icon horizontally (for directional icons) |
| `.icon-directional` | Auto-mirrors based on document direction |
| `.embed-ltr` | Embed LTR content (code, URLs) in RTL text |
| `.isolate-ltr` | Isolate LTR without affecting surroundings |
| `.force-rtl` | Force RTL on wrongly-inherited elements |
| `.ltr-value` | Phone numbers, prices — always LTR |
| `.mixed-bidi` | Plaintext BiDi for mixed content |
| `.border-s` / `.border-e` | Logical border (inline-start/end) |
| `.rounded-s` / `.rounded-e` | Logical radius (start/end side) |
| `.scroll-rtl` | RTL-aware horizontal scrolling |

## When to Use LTR

Some content MUST be LTR even in an RTL page:

| Content | How |
|---------|-----|
| Phone numbers | `<span class="ltr-value">+98 912 345 6789</span>` |
| Email addresses | `<span class="embed-ltr">user@domain.com</span>` |
| Code blocks | `<code class="embed-ltr">const x = 1;</code>` |
| URLs | `<span class="isolate-ltr">https://...</span>` |
| Latin numbers in text | `<span class="ltr-value">12,345</span>` |

## Icon Mirroring

Directional icons (arrows, chevrons, forward/back) must mirror in RTL:

```html
<!-- Auto-mirrors based on dir attribute -->
<svg class="icon-directional">...</svg>

<!-- Force mirror -->
<svg class="icon-mirror">...</svg>
```

Icons that should NOT mirror: checkmarks, plus/minus, search, settings, user, home.

## Sidebar Position

In RTL, the sidebar is on the **inline-start** side (which renders on the RIGHT):

```html
<aside class="fixed inset-inline-start-0">...</aside>
<main class="ps-64">...</main>
```

## Testing RTL

1. Verify sidebar appears on the right
2. Verify text aligns to the right
3. Verify form labels are on the right
4. Verify breadcrumbs flow right-to-left
5. Verify directional icons are mirrored
6. Verify progress bars fill from right
7. Verify pagination arrows point correctly

# Component Guide

## Usage Pattern

All components are Django template includes with props via `with`:

```html
{% include "ui/components/{category}/{name}.html" with prop1=value prop2=value %}
```

## Form Components (`ui/components/forms/`)

### Button
```html
{% include "ui/components/forms/button.html" with label="ذخیره" variant="primary" size="md" %}
{% include "ui/components/forms/button.html" with label="حذف" variant="danger" loading=True %}
{% include "ui/components/forms/button.html" with label="بیشتر" href="/more/" variant="ghost" %}
```
Variants: `primary` | `secondary` | `danger` | `success` | `ghost` | `outline`
Sizes: `xs` | `sm` | `md` | `lg` | `xl`

### Input
```html
{% include "ui/components/forms/input.html" with name="email" label="ایمیل" type="email" required=True %}
{% include "ui/components/forms/input.html" with name="phone" label="تلفن" dir="ltr" hint="با ۰۹ شروع شود" %}
```

### Textarea
```html
{% include "ui/components/forms/textarea.html" with name="bio" label="درباره من" rows="4" maxlength="500" %}
```

### Select
```html
{% include "ui/components/forms/select.html" with name="city" label="شهر" options=cities placeholder="انتخاب کنید" %}
```

### Checkbox / Radio / Toggle
```html
{% include "ui/components/forms/checkbox.html" with name="terms" label="قوانین را می‌پذیرم" required=True %}
{% include "ui/components/forms/radio.html" with name="type" value="provider" label="ارائه‌دهنده" %}
{% include "ui/components/forms/toggle.html" with name="notifications" label="اعلان‌ها" checked=True %}
```

## Feedback Components (`ui/components/feedback/`)

### Alert
```html
{% include "ui/components/feedback/alert.html" with type="success" title="موفق" message="ذخیره شد." dismissible=True %}
```
Types: `success` | `warning` | `danger` | `info`

### Badge / Chip
```html
{% include "ui/components/feedback/badge.html" with label="جدید" variant="primary" pill=True %}
{% include "ui/components/feedback/chip.html" with label="تهران" removable=True %}
```

### Loader / Skeleton / Progress
```html
{% include "ui/components/feedback/loader.html" with size="lg" %}
{% include "ui/components/feedback/skeleton.html" with type="card" %}
{% include "ui/components/feedback/progress.html" with value=75 variant="success" show_value=True %}
```

## Overlay Components (`ui/components/overlays/`)

### Modal
```html
<div x-data="{ open: false }">
  <button @click="open = true">باز</button>
  {% include "ui/components/overlays/modal.html" with title="تأیید" size="md" %}
</div>
```

### Tabs
```html
<div x-data="{ tab: 'info' }">
  {% include "ui/components/overlays/tabs.html" with tabs=tab_list active_model="tab" variant="underline" %}
</div>
```
Variants: `underline` | `pills` | `enclosed`

### Accordion
```html
<div x-data="{ active: null }">
  {% include "ui/components/overlays/accordion.html" with id="q1" title="سوال اول" content="پاسخ..." %}
</div>
```

## Data Components (`ui/components/data/`)

### Table
```html
{% include "ui/components/data/table.html" with columns=cols rows=rows striped="true" hoverable="true" %}
```

### Stat Card
```html
{% include "ui/components/data/stat_card.html" with label="سفارشات" value="۱,۲۳۴" change="+۱۲%" trend="up" %}
```

### Avatar / Breadcrumb / Timeline
```html
{% include "ui/components/data/avatar.html" with name="علی" size="lg" status="online" %}
{% include "ui/components/data/breadcrumb.html" with items=crumbs %}
{% include "ui/components/data/timeline.html" with items=events %}
```

## Jalali Dates

```html
<time data-jalali="2026-07-06T14:30:00Z"></time>          → ۱۴۰۵/۰۴/۱۶
<time data-jalali-datetime="2026-07-06T14:30:00Z"></time>  → ۱۴۰۵/۰۴/۱۶ ۱۴:۳۰
<span data-jalali-relative="2026-07-06T14:30:00Z"></span>  → ۵ دقیقه پیش
<span data-persian-digits>12345</span>                      → ۱۲۳۴۵
```

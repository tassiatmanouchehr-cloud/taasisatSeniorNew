# Font Files

This directory contains web fonts used by the platform.

## Required Fonts

### IRANSansX (Primary — Persian)
- **Source:** https://fontiran.com (commercial license)
- **Format:** Variable weight WOFF2
- **Place in:** `iransansx/IRANSansX-Variable.woff2`
- **Weights:** 100–900 (variable)

### Vazirmatn (Secondary/Fallback — Persian, Free)
- **Source:** https://github.com/rastikerdar/vazirmatn
- **Format:** Variable weight WOFF2
- **Place in:** `vazirmatn/Vazirmatn-Variable.woff2`
- **Weights:** 100–900 (variable)
- **License:** Open Font License (OFL)

### JetBrains Mono (Monospace — Code)
- **Source:** https://www.jetbrains.com/lp/mono/
- **Format:** Variable weight WOFF2
- **Place in:** `jetbrains-mono/JetBrainsMono-Variable.woff2`
- **License:** OFL

## Installation

```bash
# Vazirmatn (free — download from GitHub releases)
mkdir -p vazirmatn
curl -L -o vazirmatn/Vazirmatn-Variable.woff2 \
  https://github.com/rastikerdar/vazirmatn/raw/main/fonts/webfonts/Vazirmatn-Variable.woff2

# JetBrains Mono (free)
mkdir -p jetbrains-mono
# Download from https://www.jetbrains.com/lp/mono/

# IRANSansX (commercial — purchase from fontiran.com)
mkdir -p iransansx
# Place IRANSansX-Variable.woff2 after purchase
```

## Fallback Behavior

If font files are not present:
- CSS `font-display: swap` ensures text renders immediately with system fonts
- Tahoma → Arial → sans-serif fallback chain covers most systems
- Platform remains fully functional without custom fonts (just less polished)

## .gitignore Note

Font files (*.woff2) should be either:
- Committed to the repo (if license permits — Vazirmatn/JetBrains yes)
- Downloaded during build/setup (if commercial — IRANSansX)

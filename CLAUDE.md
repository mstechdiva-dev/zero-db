# Claude Code Instructions

## Deployment Rules

### Vercel
- **Never merge a PR if there are active Vercel build errors.**
- Resolve all build errors first, push the fix, confirm the build passes, then merge.
- Check Vercel deployment logs before suggesting or performing a merge.

## Design Rules

### HTML Mockups Required for New Pages
- **Before building any new page or significant UI section, create an HTML mockup first.**
- Mockups live in `docs/` and are named descriptively (e.g., `admin-mockup.html`, `billing-mockup.html`).
- A single HTML file may use tabs to cover multiple related views (e.g., overview + detail + sub-page).
- Mockups must match the SchemaZero design system exactly:
  - Background: `#0a0a0a` (page), `#111111` (cards), `#141414` (nested elements)
  - Accent green: `#00e87a`
  - Fonts: DM Sans (body), Space Mono (mono/code elements)
  - Use the CSS variables defined in `docs/schemazero-3.html` as the reference
- Get mockup sign-off before writing the Next.js/React implementation.
- This prevents builds that don't match the intended design and avoids rework.

### Existing Design Reference
- `docs/schemazero-3.html` — landing page reference. All new mockups must be visually consistent with this file.

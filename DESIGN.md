# Design System & Visual Architecture — ConfigStream

> **Status: target-state specification.** This document defines the intended
> visual system; it does not describe the currently deployed frontend. Current
> release status remains authoritative in `docs/readiness.json`. Each target
> below requires implementation and browser-backed verification before it may
> be marked complete.

## 1. Global Vision
ConfigStream is a utilitarian, censorship-resistant proxy intelligence platform. Its visual language balances **Cold Luxury** and **High-Trust Cyberpunk Infrastructure**: deep space backdrops (`#0a0e17`), precision glassmorphic elevations (`rgba(17, 24, 39, 0.75)`), thin laser borders (`rgba(255, 255, 255, 0.08)`), and high-contrast neon telemetry accents (Electric Cobalt `#3b82f6` and Neon Cyan `#06b6d4`).

---

## 2. Design Tokens

### 2.1 Color Tokens
| Token Name | Value | Role / Usage | WCAG Contrast Ratio |
|:---|:---|:---|:---:|
| `--bg-base` | `#0a0e17` | Canvas root background | — |
| `--bg-surface` | `#111827` | Solid card container background | $14.2:1$ against text-primary |
| `--bg-glass` | `rgba(17, 24, 39, 0.75)` | Elevated translucent panels with backdrop-blur | $12.5:1$ against text-primary |
| `--border-subtle` | `rgba(255, 255, 255, 0.08)` | Hairline container dividers | — |
| `--border-focus` | `#06b6d4` | High-contrast `:focus-visible` ring | $6.8:1$ against bg-base |
| `--text-primary` | `#f9fafb` | Primary headings, table data, and labels | $14.2:1$ against bg-base |
| `--text-secondary`| `#94a3b8` | Subheadings, descriptions, and metadata | $6.1:1$ against bg-base |
| `--text-muted` | `#7c8da5` | Timestamps, microcopy, and footnotes | $5.8:1$ against bg-base |
| `--accent-cobalt` | `#3b82f6` | Primary action buttons and branding | $5.2:1$ against bg-base |
| `--accent-cyan` | `#06b6d4` | Active tabs, glow accents, and focus indicators | $6.8:1$ against bg-base |
| `--status-valid` | `#10b981` | Verified / Shielded active proxies | $7.4:1$ against bg-base |
| `--status-warning` | `#f59e0b` | High latency / retrying endpoints | $8.1:1$ against bg-base |
| `--status-danger` | `#ef4444` | Dead / Honeypot / Dirty blocked proxies | $5.1:1$ against bg-base |
| `--status-revived` | `#8b5cf6` | Cloudflare WARP / Vwarp revived nodes | $5.8:1$ against bg-base |

### 2.2 Typography Scale
- **Display H1:** `2.5rem - 3.5rem` (`40px - 56px`), `font-weight: 700`, `letter-spacing: -0.03em`, `leading: 1.1`.
- **Section H2:** `1.75rem - 2.25rem` (`28px - 36px`), `font-weight: 600`, `letter-spacing: -0.02em`.
- **Card H3:** `1.125rem - 1.25rem` (`18px - 20px`), `font-weight: 600`.
- **Body Regular:** `0.9375rem` (`15px`), `font-weight: 400`, `line-height: 1.6`.
- **Data / Monospace:** `0.875rem` (`14px`), `font-family: ui-monospace, SFMono-Regular, "Cascadia Code", monospace`, with mandatory `font-variant-numeric: tabular-nums`.

### 2.3 Spacing Scale (4px Increments)
- `space-1`: `4px` (`0.25rem`)
- `space-2`: `8px` (`0.5rem`)
- `space-3`: `12px` (`0.75rem`)
- `space-4`: `16px` (`1.0rem`)
- `space-6`: `24px` (`1.5rem`)
- `space-8`: `32px` (`2.0rem`)
- `space-12`: `48px` (`3.0rem`)
- `space-16`: `64px` (`4.0rem`)

### 2.4 Border Radii
- `radius-sm`: `4px` (Tags, micro-badges, code snippets)
- `radius-md`: `8px` (Buttons, inputs, filter dropdowns)
- `radius-lg`: `12px` (Cards, telemetry widgets, dialogs)
- `radius-xl`: `16px` (Hero containers and prominent content panels)
- `radius-pill`: `9999px` (Status badges, pill tabs, scroll pills)

---

## 3. Component Architecture & Patterns

### 3.1 Buttons
- **Primary Glow Button:** Solid Cobalt background (`#3b82f6`) with subtle inner white border highlight (`inset 0 1px 0 rgba(255,255,255,0.2)`), active physical press feedback (`transform: scale(0.98)`).
- **Secondary Ghost / Outline Button:** Transparent background with 1px border (`rgba(255,255,255,0.15)`), hover elevation to `rgba(255,255,255,0.06)`.
- **Icon Button:** Strict minimum touch target of $24\times24\text{px}$ desktop / $44\times44\text{px}$ mobile with descriptive `aria-label`.

### 3.2 Data Tables (`frontend/proxies.html`)
- **Header:** Sticky top with subtle bottom border (`1px solid rgba(255, 255, 255, 0.1)`).
- **Cells:** Tabular figures on ping, port, and IP columns. Zero horizontal cell clipping.
- **Row Interaction:** Subtle background hover highlight (`rgba(255, 255, 255, 0.03)`).

### 3.3 Modal & Drawer Architecture
- **Backdrop:** Translucent blur layer (`backdrop-filter: blur(8px); background: rgba(0, 0, 0, 0.6)`).
- **Focus Trap:** Keyboard focus locked inside active drawer/modal; dismissed with `Escape` key and restored to trigger button.

---

## 4. Anti-Slop & Craft Directives

1. **No Generic AI Lila / Purple Gradient Default:** Base palettes must remain grounded in Cold Slate and Electric Cobalt.
2. **No Layout Shift on Async Telemetry:** Fixed minimum heights on all chart wrappers (`min-height: 400px`) and 3D globe canvases (`min-height: 500px`).
3. **Offscreen WebGL Freeze:** Suspend Three.js / Globe.gl `requestAnimationFrame` loops when viewport leaves intersection view.
4. **WCAG 2.2 AA Focus Standard:** Never remove `:focus` without applying `:focus-visible { outline: 2px solid var(--border-focus); outline-offset: 2px; }`.

---

## 5. Target Acceptance Criteria

The implementation is ready to verify only when all of the following have
evidence from the designated viewports (`375px`, `768px`, `1024px`, `1440px`):

- [ ] Tokens are implemented consistently across every public surface.
- [ ] Telemetry uses tabular numerals without layout jitter.
- [ ] The component state matrix covers hover, active, focus, disabled,
  loading, empty, and retry states.
- [ ] Keyboard, touch-target, contrast, reduced-motion, and reflow checks pass
  browser-backed accessibility testing.
- [ ] No structural emoji icons remain; approved SVG icons include accessible
  names where needed.

### 5.1 Delivery Rules

1. **One source of visual tokens:** define each approved token once in the
   shared stylesheet, then consume it rather than copying literal colors into
   page-specific rules.
2. **No hard-coded operational claims:** live node counts, timestamps,
   reliability rates, and “verified” labels must be derived from the validated
   artifact metadata. When data is unavailable or untrusted, show an explicit
   unavailable state rather than a placeholder value.
3. **A target is not a release gate until automated:** a target may be marked
   complete only after its implementation, test reference, and verification
   result are linked from the delivery change.
4. **Respect the existing information hierarchy:** visual redesign work must
   preserve the public artifact state, freshness warning, and error/empty
   states; polish must never hide a failed or stale release.

### 5.2 Component Delivery Matrix

| Area | Target behavior | Minimum evidence | Release impact if absent |
|---|---|---|---|
| Global navigation | Keyboard-visible focus, 44px touch targets, no covered anchor destination | Keyboard walkthrough at all four viewports | Blocks accessibility claim |
| Live telemetry | Stable numeric width, metadata-derived freshness, explicit unavailable state | Browser test with fresh, stale, and failed metadata fixtures | Blocks release trust claim |
| Proxy table | Semantic table behavior, readable overflow strategy, status text in addition to color | Keyboard, zoom, and screen-reader smoke test | Blocks proxy-page sign-off |
| Dialogs and drawers | Focus trap, Escape dismissal, focus restoration | Playwright interaction test | Blocks modal release |
| WebGL/globe | 500px reserve, DPR cap 1.5, pause offscreen, cleanup on route change | Browser test plus performance trace on mobile emulation | Feature may be omitted; must not block core subscription flow |
| Motion | Transform/opacity-only decoration and reduced-motion alternative | Reduced-motion screenshot and CSS lint/search evidence | Blocks animation claim |

---

## 6. UI/UX Pro Max Implementation Guidelines & Pre-Delivery Checklist (`/ui-ux-pro-max`)

### 6.1 Strict Component Rules
- **No Emoji Icons:** UI components and buttons must NEVER use emojis (e.g. 🚀, 🛡️, ⚙️) as structural interface icons. Use scalable SVG icons from Lucide or Simple Icons with fixed `viewBox="0 0 24 24"`.
- **Stable Hover Dynamics:** Hover feedback must use non-layout-shifting CSS properties (`color`, `opacity`, `border-color`, `box-shadow`). Geometric scaling (`transform: scale(...)`) on cards that reflow adjacent content is prohibited.
- **Cursor Pointer Enforced:** Every clickable card, interactive row, tab, and button must declare `cursor: pointer`.
- **Contrast Integrity:** Text elements in both light and dark modes must maintain $\ge 4.5:1$ contrast against their immediate surface background.

### 6.2 Pre-Delivery Verification Checklist
- [ ] All icons sourced from cohesive SVG sets with `aria-hidden="true"` or descriptive `aria-label`.
- [ ] Zero emojis used as structural UI icons.
- [ ] Hover states transition smoothly within 150ms–300ms without causing Cumulative Layout Shift (CLS).
- [ ] Focus states are clearly visible via `:focus-visible` ring (`outline: 2px solid #06b6d4`).
- [ ] Responsive layout verified across `375px` (Mobile Small), `768px` (Tablet), `1024px` (Desktop), and `1440px` (Wide).
- [ ] `@media (prefers-reduced-motion: reduce)` collapses all non-essential animations.

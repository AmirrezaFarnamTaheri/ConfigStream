# Frontend Design Deslop & Laboratory Audit Report

## 1. Visual System Audit & AI Slop Tells
The visual system heavily utilizes "Neumorphic Glassmorphism" tropes, resulting in visual clutter characteristic of AI-generated placeholder design.
- **Overdone Shadows**: Cards use intense, dual-layer shadows (`8px 8px 18px var(--shadow-1), -8px -8px 18px var(--shadow-2)`) which creates unnecessary visual noise and heavy depth layering.
- **Generic Gradients**: The brand gradient relies on a default purple/pink spectrum (`#5E55F1` to `#A855F7` to `#D83A8D`) typical of AI slop.
- **Border Radii**: Excessive use of `30px` and `40px` border radii (`--radius-lg` and `--radius-xl`), making the UI feel inflated and less rigorous.

**Adjective Commitments**: The UI should shift from "Bubbly and layered" to "Crisp, flat, and utilitarian".

## 2. Typography & Color Token Assessment (OKLCH Recommendations)
Current tokens rely entirely on raw HEX/RGBA, causing unpredictable contrast variations between light/dark modes.

**Current (Slop):**
```css
--bg-primary: #f0f4f8;
--brand-primary: #5E55F1;
--shadow-1: rgba(163, 177, 198, 0.4);
```

**Recommended (OKLCH):**
Transition to perceptually uniform OKLCH to guarantee mathematical contrast ratios:
```css
:root {
  --bg-primary: oklch(0.97 0.01 240);
  --bg-secondary: oklch(1 0 0);
  --brand-primary: oklch(0.55 0.18 260); /* 4.5+ Contrast against background */
  --brand-secondary: oklch(0.60 0.18 330);
  --border: oklch(0.85 0.01 240);
}
.dark {
  --bg-primary: oklch(0.18 0.02 240);
  --bg-secondary: oklch(0.22 0.02 240);
  --brand-primary: oklch(0.70 0.15 260);
  --border: oklch(0.35 0.02 240);
}
```

## 3. Component State Matrix Compliance Table
A rigorous audit of interactive primitives reveals missing states, especially on core elements like `.btn`.

| Component | Default | Hover | Active | Focus (Visible) | Disabled | Loading | Error |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `.btn` | 🟢 | 🟢 | 🟢 | 🟢 | 🔴 Missing | 🔴 Missing | N/A |
| `.lab-btn` | 🟢 | 🟢 | 🟢 | 🟢 | 🟢 | 🔴 Missing | N/A |
| `.nav-link`| 🟢 | 🟢 | 🟢 | 🟢 | N/A | N/A | N/A |
| `Inputs` | 🟢 | 🟢 | 🟢 | 🟢 | 🔴 Missing | N/A | 🔴 Missing |

*Note: The global `.btn` completely lacks a `:disabled` CSS rule in `style.css`. There are also no global `.btn.loading` spinner states defined.*

## 4. Accessibility & Security Findings
- **Touch Targets (WCAG 2.2 AA SC 2.5.8)**: Compliant. Buttons and navigation links have a minimum height of `44px` on mobile screens, vastly exceeding the 24px+ requirement.
- **Focus Indicators**: Compliant. Proper `:focus-visible` rings are established using `color-mix`.
- **Contrast Ratios**: Partial Failure. The Light mode `--brand-tertiary` (`#A855F7`) on white has a contrast of ~3.3:1, failing normal text WCAG AA (4.5:1). OKLCH migration will fix this.

## 5. Security Boundaries (DOMPurify in Lab UI)
**Critical Finding**: In `frontend/assets/js/lab/ui.js`, the `showResultHTML` function explicitly invokes `window.DOMPurify.sanitize()`. However, `purify.min.js` was entirely omitted from the `<head>` of `lab.html`.
- **Impact**: This forced the system into a fallback block that simply stripped `<br>` tags via regex and used `textContent`. It bypassed the intended HTML rendering pipeline, breaking visual output.
- **Remediation**: `assets/libs/purify.min.js` has been successfully injected into `lab.html`.

## 6. Concrete Refactoring Code Fixes
1. **Fix lab.html Security**: Added `<script src="assets/libs/purify.min.js" defer></script>` to `lab.html`.
2. **Remove Double Shadows**: Refactor `.card` shadows to a crisp single layer: `box-shadow: 0 4px 12px oklch(0 0 0 / 0.08);`.
3. **Implement Button States**: Add missing CSS:
   ```css
   .btn:disabled, .btn[disabled] { opacity: 0.5; pointer-events: none; filter: grayscale(1); }
   .btn.loading { color: transparent !important; pointer-events: none; }
   .btn.loading::after { content: ""; position: absolute; width: 16px; height: 16px; border: 2px solid white; border-top-color: transparent; border-radius: 50%; animation: spin 1s linear infinite; }
   ```

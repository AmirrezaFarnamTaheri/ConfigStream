# I18n Localization & RTL Layout Audit

## 1. Frontend i18n Architecture Diagram
```text
+-------------------+      (localStorage 'lang')       +-------------------+
|   User Action     |--------------------------------->|    I18n Manager   |
| (Select Language) |                                  |  (assets/js/i18n) |
+-------------------+                                  +---------+---------+
                                                                 |
                                        +------------------------+------------------------+
                                        |                        |                        |
                              [Async Fetch JSON]        [Apply DOM State]        [Render Content]
                                        v                        v                        v
                            +-----------------------+ +---------------------+ +-----------------------+
                            | assets/i18n/*.json    | | <html lang="fa">    | | Fallback:             |
                            | (en, fa, ar, zh, ru)  | | <html dir="rtl">    | | 1. Current Lang       |
                            +-----------------------+ +---------------------+ | 2. English (en)       |
                                                                              | 3. Key String         |
                                                                              +-----------------------+
```

## 2. Translation Key Parity & Missing Key Matrix

A deep-flattening analysis was conducted on all 5 language files (`en.json`, `fa.json`, `ar.json`, `zh.json`, `ru.json`).

| Language | Code | Total Keys | Missing Keys vs All Files |
|----------|------|------------|---------------------------|
| English  | `en` | 100%       | 0                         |
| Persian  | `fa` | 100%       | 0                         |
| Arabic   | `ar` | 100%       | 0                         |
| Chinese  | `zh` | 100%       | 0                         |
| Russian  | `ru` | 100%       | 0                         |

**Conclusion:** Perfect parity. There are **zero missing translation keys** across the localization files.

## 3. RTL Layout CSS & DOM Compliance Audit

Right-to-Left (RTL) support for Persian (`fa`) and Arabic (`ar`) was thoroughly reviewed:
- **DOM Attribute Toggling:** The `applyLanguageSettings(lang)` explicitly sets `document.documentElement.setAttribute('dir', 'rtl')`.
- **CSS Selectors:** Comprehensive layout mirroring is implemented via `[dir="rtl"]` and `html[dir="rtl"]` selectors in `style.css`.
- **Coverage:** Reversals successfully cover critical UI areas including:
  - Header, Nav, and Action Buttons (flex directions and margins)
  - Proxies Table (hover transforms `translateX(-4px)`, border radii, badges)
  - Status/Location Cells and Filter inputs
  - Stats Grid and Pagination controls
- **Compliance:** High. The targeted strategy minimizes layout shifting while strictly respecting text directionality norms for RTL languages.

## 4. XSS Security in Dynamic String Interpolation Assessment

**Risk Vector:** Translators injecting malicious scripts via HTML-rendered keys.
- **Handling:** `i18n.js` processes HTML rendering when `data-i18n-html="true"` is set.
- **Current Mitigation:** A custom built `sanitizeToFragment(input)` function sanitizes inputs using `DOMParser`.
  - Implements an `allowedTags` list (`STRONG`, `A`, `SPAN`, `DIV`, etc.).
  - Implements an `allowedAttrs` list (`href`, `class`, `id`, `target`, etc.).
  - Strips all `on*` inline event handlers.
  - Mitigates protocol-based XSS by removing `javascript:`, `vbscript:`, and `data:` from `href` and `src`.
- **Finding:** While effective against basic XSS vectors, custom DOM sanitizers are notoriously susceptible to edge-case bypasses (e.g., DOM clobbering, namespace/SVG confusion, parser mutation).

## 5. Fallback Behavior Check
- If a string is absent in the requested language, `I18n.t(key)` gracefully falls back to the English dictionary (`this.translations['en'][key]`).
- If missing in both, the system returns the raw string identifier (`key`), preventing a hard crash or `undefined` render. 

## 6. Hardening Recommendations

1. **Adopt DOMPurify:** The frontend currently bundles `assets/libs/purify.min.js`. Instead of using the custom `sanitizeToFragment()` logic, integrate `DOMPurify.sanitize()` for battle-tested, robust XSS defense on HTML-enabled localized strings.
2. **Implement CI/CD Key Validation:** Automate the JSON parsing parity script on PRs to ensure developers cannot commit features without synchronized keys across all 5 localization files.
3. **Template Substitution:** If dynamic variables (e.g., `Welcome {user}`) are added in the future, implement a safe regex substitution pattern that executes *after* HTML sanitization to prevent unescaped template values from bypassing the sanitizer.

# 06. Frontend Development

## Architecture: The Static SPA

The frontend is a **Static Single Page Application (SPA)**. It is hosted on GitHub Pages, which means no backend server is required for the UI to work. This aligns with our "Zero Budget" philosophy.

-   **Data Source**: It fetches `metadata.json` and `proxies.json` directly from the same domain.
-   **Framework**: Vanilla JavaScript (ES6+). No React/Vue/Angular.
-   **CSS**: Custom CSS variables for theming.

## Key Components

### 1. 3D Globe Visualization
We use `globe.gl` to render a 3D interactive earth.
-   **Data Mapping**: Country codes -> Lat/Lng.
-   **Visuals**: Arcs represent connections, points represent active proxies.

### 2. Downloads & Adapters
The frontend provides client-specific configuration files.
-   **Clash**: YAML.
-   **Sing-box**: JSON.
-   **Surge / Loon**: New additions.
-   **Quantumult X**: Custom configuration format.
-   **SIP008**: Standard interchange format.

### 3. Internationalization (i18n)
-   **Dictionary**: `assets/js/i18n.js`.
-   **RTL Support**: Dynamic direction switching for Farsi/Arabic.

### 4. Telegram Bot Integration
The frontend links to the Telegram Bot for users who prefer chat-based interaction.
-   **Deep Linking**: `t.me/ConfigStreamBot?start=US` (future feature) to request specific countries.

## Building & Deploying

There is no build step.
To test locally:
```bash
python -m http.server -d frontend 8000
```

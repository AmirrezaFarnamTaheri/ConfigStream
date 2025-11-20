# 06. Frontend Development

## Architecture: The Static SPA

The frontend is a **Static Single Page Application (SPA)**. It is hosted on GitHub Pages, which means no backend server is required for the UI to work. This aligns with our "Zero Budget" philosophy.

-   **Data Source**: It fetches `metadata.json` and `proxies.json` directly from the same domain (`/api/` requests are mocked or served as static files).
-   **Framework**: Vanilla JavaScript (ES6+). No React/Vue/Angular to keep the build process simple and the bundle size tiny.
-   **CSS**: Custom CSS variables for theming.

## Key Components

### 1. 3D Globe Visualization
We use `globe.gl` (a wrapper around Three.js) to render a 3D interactive earth.
-   **Data Mapping**: We map ISO Alpha-2 country codes from `metadata.json` to approximate lat/lng coordinates.
-   **Visuals**: Arcs represent connections, points represent active proxies. The size of the point correlates with the number of proxies.

### 2. Internationalization (i18n)
We implemented a custom, lightweight `I18n` class in `assets/js/i18n.js`.
-   **Dictionary**: A JSON object storing translations for `en`, `zh`, `fa`, `ru`, `ar`.
-   **RTL Support**: When switching to Farsi (`fa`) or Arabic (`ar`), we dynamically set `document.documentElement.setAttribute('dir', 'rtl')` to flip the layout.

### 3. PWA (Progressive Web App)
ConfigStream is installable.
-   **Manifest**: `manifest.json` defines the app icons, name, and theme color.
-   **Service Worker**: `service-worker.js` implements a caching strategy:
    -   **Assets (HTML/CSS/JS)**: Cache-First (Stale-While-Revalidate).
    -   **Data (JSON)**: Network-First (Fall back to cache if offline).

### 4. Natural Language Search
The search bar in `proxies.html` supports queries like:
-   `"fastest"`: Sorts by latency.
-   `"Germany < 100ms"`: Filters by country and latency.
-   `"vmess"`: Filters by protocol.

This logic is implemented in pure JS in `proxies.js` using regex parsing.

## Building & Deploying

There is no build step (e.g., Webpack/Vite). You can just edit the files and push.
To test locally:
```bash
python -m http.server -d frontend 8000
```

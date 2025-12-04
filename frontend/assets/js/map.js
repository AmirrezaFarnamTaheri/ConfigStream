/**
 * Map Controller for ConfigStream using Leaflet
 * Renders an interactive world map with markers for proxy locations.
 */

class MapWidget {
    constructor(containerId) {
        this.containerId = containerId;
        this.map = null;
    }

    init() {
        if (!document.getElementById(this.containerId)) return;

        // Initialize Leaflet map
        this.map = L.map(this.containerId).setView([20, 0], 2); // Center map globally

        // Add dark-themed tile layer (CartoDB Dark Matter)
        L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(this.map);
    }

    render(metadata) {
        if (!this.map || !metadata || !metadata.country_stats) return;

        const stats = metadata.country_stats;
        // stats is { "US": 100, "DE": 50 ... }
        // We need lat/lon for countries.
        // In a real app we would have a country center DB.
        // For this MVP, we will use a small embedded dictionary for top countries.

        const countryCenters = {
            "US": [37.0902, -95.7129],
            "CN": [35.8617, 104.1954],
            "JP": [36.2048, 138.2529],
            "DE": [51.1657, 10.4515],
            "GB": [55.3781, -3.4360],
            "FR": [46.2276, 2.2137],
            "BR": [-14.2350, -51.9253],
            "RU": [61.5240, 105.3188],
            "IN": [20.5937, 78.9629],
            "CA": [56.1304, -106.3468],
            "AU": [-25.2744, 133.7751],
            "KR": [35.9078, 127.7669],
            "SG": [1.3521, 103.8198],
            "NL": [52.1326, 5.2913],
            "TR": [38.9637, 35.2433],
            "IR": [32.4279, 53.6880],
            "UA": [48.3794, 31.1656],
            "ID": [-0.7893, 113.9213],
            "HK": [22.3193, 114.1694],
            "TW": [23.6978, 120.9605]
        };

        Object.entries(stats).forEach(([code, count]) => {
            const center = countryCenters[code.toUpperCase()];
            if (center) {
                // Scale circle radius by count (logarithmic)
                const radius = Math.log(count + 1) * 50000;

                const circle = L.circle(center, {
                    color: '#3b82f6',
                    fillColor: '#3b82f6',
                    fillOpacity: 0.5,
                    radius: radius
                }).addTo(this.map);

                circle.bindPopup(`<b>${code}</b>: ${count} Proxies`);

                circle.on('click', () => {
                     window.location.href = `proxies.html?country=${code}`;
                });
            }
        });
    }
}

// Initialize
document.addEventListener("DOMContentLoaded", async () => {
    const widget = new MapWidget("world-map-widget");
    widget.init();

    try {
        const response = await fetch('metadata.json');
        if (response.ok) {
            const metadata = await response.json();
            widget.render(metadata);
        }
    } catch (e) {
        console.error("Failed to load map data", e);
    }
});

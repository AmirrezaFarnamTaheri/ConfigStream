// 3D Globe Visualization using Globe.gl
// Replaces Leaflet map with an interactive, rotating 3D globe.

class GlobeWidget {
    constructor(containerId) {
        this.containerId = containerId;
        this.container = document.getElementById(containerId);
        this.globe = null;
        this.isHovering = false;
        this.cooldownTimer = null;
    }

    init() {
        if (!this.container) return;

        // Ensure container has dimensions
        const width = this.container.offsetWidth || window.innerWidth;
        const height = this.container.offsetHeight || 500;

        // Initialize Globe
        this.globe = Globe()
            (this.container)
            .width(width)
            .height(height)
            .globeImageUrl('//unpkg.com/three-globe/example/img/earth-night.jpg')
            .bumpImageUrl('//unpkg.com/three-globe/example/img/earth-topology.png')
            .backgroundImageUrl('//unpkg.com/three-globe/example/img/night-sky.png')
            .pointOfView({ altitude: 2.5 }) // Initial Zoom
            .enablePointerInteraction(false); // Disable interaction initially

        // Enable auto-rotation
        this.globe.controls().autoRotate = true;
        this.globe.controls().autoRotateSpeed = 0.6;

        // Initial state: Zoom disabled until interaction
        this.globe.controls().enableZoom = false;

        // Custom interaction handling
        this.setupInteraction();

        // Handle resize
        window.addEventListener('resize', () => {
             const w = this.container.offsetWidth || window.innerWidth;
             const h = this.container.offsetHeight || 500;
             this.globe.width(w).height(h);
        });
    }

    setupInteraction() {
        const enableInteraction = () => {
            // Enable controls
            this.globe.controls().enableZoom = true;
            this.globe.controls().enableRotate = true;
            this.globe.enablePointerInteraction(true);

            // Pause auto-rotation on interaction
            this.globe.controls().autoRotate = false;

            // Clear existing cooldown
            if (this.cooldownTimer) clearTimeout(this.cooldownTimer);

            // Set cooldown to resume rotation and disable zoom
            this.cooldownTimer = setTimeout(() => {
                this.globe.controls().autoRotate = true;
                this.globe.controls().enableZoom = false; // Disable zoom after cooldown
            }, 2000);
        };

        this.container.addEventListener('mousedown', enableInteraction);
        this.container.addEventListener('touchstart', enableInteraction);
        this.container.addEventListener('wheel', enableInteraction); // Also enable on scroll attempt

        // Resume rotation when mouse leaves
        this.container.addEventListener('mouseleave', () => {
            if (this.cooldownTimer) clearTimeout(this.cooldownTimer);
            this.globe.controls().autoRotate = true;
            this.globe.controls().enableZoom = false;
        });
    }

    render(metadata) {
        if (!this.globe || !metadata || !metadata.country_stats) return;

        const stats = metadata.country_stats;

        // Embedded centroids for mapping country codes to lat/lng
        const countryCenters = {
            "US": { lat: 37.0902, lng: -95.7129, name: "United States" },
            "CN": { lat: 35.8617, lng: 104.1954, name: "China" },
            "JP": { lat: 36.2048, lng: 138.2529, name: "Japan" },
            "DE": { lat: 51.1657, lng: 10.4515, name: "Germany" },
            "GB": { lat: 55.3781, lng: -3.4360, name: "United Kingdom" },
            "FR": { lat: 46.2276, lng: 2.2137, name: "France" },
            "BR": { lat: -14.2350, lng: -51.9253, name: "Brazil" },
            "RU": { lat: 61.5240, lng: 105.3188, name: "Russia" },
            "IN": { lat: 20.5937, lng: 78.9629, name: "India" },
            "CA": { lat: 56.1304, lng: -106.3468, name: "Canada" },
            "AU": { lat: -25.2744, lng: 133.7751, name: "Australia" },
            "KR": { lat: 35.9078, lng: 127.7669, name: "South Korea" },
            "SG": { lat: 1.3521, lng: 103.8198, name: "Singapore" },
            "NL": { lat: 52.1326, lng: 5.2913, name: "Netherlands" },
            "TR": { lat: 38.9637, lng: 35.2433, name: "Turkey" },
            "IR": { lat: 32.4279, lng: 53.6880, name: "Iran" },
            "UA": { lat: 48.3794, lng: 31.1656, name: "Ukraine" },
            "ID": { lat: -0.7893, lng: 113.9213, name: "Indonesia" },
            "HK": { lat: 22.3193, lng: 114.1694, name: "Hong Kong" },
            "TW": { lat: 23.6978, lng: 120.9605, name: "Taiwan" },
            "AE": { lat: 23.4241, lng: 53.8478, name: "UAE" },
            "ZA": { lat: -30.5595, lng: 22.9375, name: "South Africa" }
        };

        const points = [];
        const maxVal = Math.max(...Object.values(stats));

        Object.entries(stats).forEach(([code, count]) => {
            const country = countryCenters[code.toUpperCase()];
            if (country) {
                points.push({
                    lat: country.lat,
                    lng: country.lng,
                    size: Math.max(0.2, (count / maxVal) * 1.5),
                    color: '#5E55F1', // Brand Primary
                    label: `${country.name}: ${count} Proxies`
                });
            }
        });

        // Add Points (Cylinders/Bars)
        this.globe
            .pointsData(points)
            .pointAltitude('size')
            .pointColor('color')
            .pointRadius(0.5) // Thin bars
            .pointLabel('label');
    }
}

// Initialize
document.addEventListener("DOMContentLoaded", async () => {
    // Only init if container exists
    if (!document.getElementById("world-map-widget")) return;

    const widget = new GlobeWidget("world-map-widget");
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

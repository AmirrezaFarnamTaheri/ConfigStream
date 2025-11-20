class WorldMap {
    constructor(containerId, data) {
        this.container = document.getElementById(containerId);
        this.data = data; // { "US": 100, "DE": 50 }
        this.render();
    }

    render() {
        if (!this.container || !HEX_MAP_LAYOUT) return;

        const width = this.container.clientWidth;
        const height = 300;
        const hexSize = 25;

        // Find max count for color scaling
        const maxCount = Math.max(...Object.values(this.data), 1);

        let svgContent = `
            <svg width="${width}" height="${height}" viewBox="0 0 300 200">
                <g transform="translate(20, 20)">
        `;

        HEX_MAP_LAYOUT.forEach(tile => {
             // Simple hex math:
             // x pixel = tile.x * size * 1.5
             // y pixel = tile.y * size * sqrt(3) + (tile.x % 2) * size * sqrt(3) / 2
             const x = tile.x * hexSize * 1.1;
             const y = tile.y * hexSize * 1.1 + (tile.x % 2) * (hexSize * 1.1) / 2;

             const count = this.data[tile.id] || 0;
             const intensity = count / maxCount;

             // Color: Blue gradient
             // Low: #1e293b (slate-800) -> High: #3b82f6 (blue-500)
             const color = count > 0
                ? `rgba(59, 130, 246, ${0.3 + intensity * 0.7})`
                : '#1e293b';

             svgContent += `
                <g transform="translate(${x}, ${y})" class="map-tile" data-country="${tile.name}" data-count="${count}">
                    <rect x="0" y="0" width="${hexSize}" height="${hexSize}" rx="4" fill="${color}" stroke="#0f172a" stroke-width="2"/>
                    <text x="${hexSize/2}" y="${hexSize/2 + 4}" text-anchor="middle" font-size="8" fill="#fff" style="pointer-events: none;">${tile.id}</text>
                    <title>${tile.name}: ${count}</title>
                </g>
             `;
        });

        svgContent += `</g></svg>`;
        this.container.innerHTML = svgContent;
    }
}

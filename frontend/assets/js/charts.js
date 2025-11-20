// Simple Historical Chart using Chart.js (assumed to be loaded via CDN in production or bundled)
// For this demo, we'll write a lightweight SVG chart generator to avoid external dependencies.

class HistoryChart {
    constructor(containerId, data) {
        this.container = document.getElementById(containerId);
        this.data = data; // Expecting [{date: '2023-10-01', count: 120}, ...]
        this.render();
    }

    render() {
        if (!this.container || !this.data || this.data.length === 0) return;

        const width = this.container.clientWidth;
        const height = 200;
        const padding = 40;

        const maxVal = Math.max(...this.data.map(d => d.count));
        const minVal = 0;

        const xScale = (index) => padding + (index / (this.data.length - 1)) * (width - 2 * padding);
        const yScale = (val) => height - padding - ((val - minVal) / (maxVal - minVal)) * (height - 2 * padding);

        let pathD = `M ${xScale(0)} ${yScale(this.data[0].count)}`;
        this.data.forEach((d, i) => {
            pathD += ` L ${xScale(i)} ${yScale(d.count)}`;
        });

        // SVG Template
        const svg = `
            <svg width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
                <g class="grid">
                    <line x1="${padding}" y1="${height - padding}" x2="${width - padding}" y2="${height - padding}" stroke="#334155" />
                    <line x1="${padding}" y1="${padding}" x2="${padding}" y2="${height - padding}" stroke="#334155" />
                </g>
                <path d="${pathD}" fill="none" stroke="#3b82f6" stroke-width="2" />
                ${this.data.map((d, i) => `
                    <circle cx="${xScale(i)}" cy="${yScale(d.count)}" r="3" fill="#60a5fa">
                        <title>${d.date}: ${d.count}</title>
                    </circle>
                `).join('')}
            </svg>
        `;

        this.container.innerHTML = svg;
    }
}

// Example usage
// new HistoryChart('chart-container', [{date: 'Mon', count: 100}, {date: 'Tue', count: 150}]);

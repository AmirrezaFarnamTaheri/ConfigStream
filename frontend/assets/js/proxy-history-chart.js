/**
 * Proxy History Chart Visualization
 *
 * Zero-budget solution using pure SVG for charting.
 * Shows reliability trends over time without external dependencies.
 */

class ProxyHistoryChart {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.historyData = null;
        this.selectedProxy = null;
    }

    /**
     * Load history data from JSON file
     */
    async loadHistoryData() {
        try {
            const response = await fetch('data/proxy_history_viz.json');
            if (!response.ok) {
                console.warn('No history data available yet');
                return false;
            }
            this.historyData = await response.json();
            return true;
        } catch (error) {
            console.warn('Failed to load history data:', error);
            return false;
        }
    }

    /**
     * Render history chart for a specific proxy
     */
    renderChart(proxyConfig) {
        if (!this.historyData || !this.historyData[proxyConfig]) {
            this.container.innerHTML = '<p class="no-data">No historical data available for this proxy</p>';
            return;
        }

        const data = this.historyData[proxyConfig];
        this.selectedProxy = data;

        // Create chart HTML
        this.container.innerHTML = `
            <div class="history-chart-container">
                <div class="chart-header">
                    <h3>Reliability Trend</h3>
                    <div class="proxy-info">
                        <span>${data.protocol}://${data.address}:${data.port}</span>
                    </div>
                </div>

                <div class="chart-stats">
                    <div class="stat-card">
                        <div class="stat-label">Success Rate</div>
                        <div class="stat-value">${(data.stats.success_rate * 100).toFixed(1)}%</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Avg Latency</div>
                        <div class="stat-value">${data.stats.avg_latency.toFixed(0)}ms</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Uptime</div>
                        <div class="stat-value">${data.stats.uptime_percentage.toFixed(1)}%</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-label">Total Tests</div>
                        <div class="stat-value">${data.stats.total_tests}</div>
                    </div>
                </div>

                <div class="chart-area">
                    <svg id="history-svg" width="100%" height="300"></svg>
                </div>

                <div class="chart-legend">
                    <div class="legend-item">
                        <span class="legend-color" style="background: #10b981;"></span>
                        <span>Online</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-color" style="background: #ef4444;"></span>
                        <span>Offline</span>
                    </div>
                    <div class="legend-item">
                        <span class="legend-color" style="background: #3b82f6;"></span>
                        <span>Latency (ms)</span>
                    </div>
                </div>
            </div>
        `;

        // Draw the chart
        this.drawSVGChart(data.trend);
    }

    /**
     * Draw SVG chart with latency and status
     */
    drawSVGChart(trendData) {
        const svg = document.getElementById('history-svg');
        if (!svg) return;

        const width = svg.clientWidth || 800;
        const height = 300;
        const padding = { top: 20, right: 20, bottom: 40, left: 50 };
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;

        // Clear existing content
        svg.innerHTML = '';
        svg.setAttribute('viewBox', `0 0 ${width} ${height}`);

        const { timestamps, latencies, status } = trendData;

        if (timestamps.length === 0) {
            svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="#666">No data points available</text>';
            return;
        }

        // Calculate scales
        const maxLatency = Math.max(...latencies, 100);
        const xStep = chartWidth / Math.max(timestamps.length - 1, 1);

        // Helper function to get Y position for latency
        const getLatencyY = (latency) => {
            return padding.top + chartHeight - (latency / maxLatency) * chartHeight;
        };

        // Draw grid lines
        const gridLines = 5;
        for (let i = 0; i <= gridLines; i++) {
            const y = padding.top + (chartHeight / gridLines) * i;
            const latencyValue = maxLatency - (maxLatency / gridLines) * i;

            // Grid line
            const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
            line.setAttribute('x1', padding.left);
            line.setAttribute('y1', y);
            line.setAttribute('x2', width - padding.right);
            line.setAttribute('y2', y);
            line.setAttribute('stroke', '#e5e7eb');
            line.setAttribute('stroke-width', '1');
            svg.appendChild(line);

            // Y-axis label
            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', padding.left - 10);
            text.setAttribute('y', y + 5);
            text.setAttribute('text-anchor', 'end');
            text.setAttribute('fill', '#6b7280');
            text.setAttribute('font-size', '12');
            text.textContent = `${latencyValue.toFixed(0)}`;
            svg.appendChild(text);
        }

        // Draw status indicators (background bars)
        timestamps.forEach((timestamp, i) => {
            const x = padding.left + i * xStep;
            const isOnline = status[i] === 1;

            const rect = document.createElementNS('http://www.w3.org/2000/svg', 'rect');
            rect.setAttribute('x', x - 3);
            rect.setAttribute('y', padding.top);
            rect.setAttribute('width', '6');
            rect.setAttribute('height', chartHeight);
            rect.setAttribute('fill', isOnline ? '#10b981' : '#ef4444');
            rect.setAttribute('opacity', '0.2');
            svg.appendChild(rect);
        });

        // Draw latency line
        let pathData = '';
        latencies.forEach((latency, i) => {
            const x = padding.left + i * xStep;
            const y = getLatencyY(latency);

            if (i === 0) {
                pathData += `M ${x} ${y}`;
            } else {
                pathData += ` L ${x} ${y}`;
            }
        });

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', pathData);
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', '#3b82f6');
        path.setAttribute('stroke-width', '2');
        svg.appendChild(path);

        // Draw data points
        latencies.forEach((latency, i) => {
            const x = padding.left + i * xStep;
            const y = getLatencyY(latency);

            const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
            circle.setAttribute('cx', x);
            circle.setAttribute('cy', y);
            circle.setAttribute('r', '4');
            circle.setAttribute('fill', status[i] === 1 ? '#3b82f6' : '#ef4444');
            circle.setAttribute('stroke', 'white');
            circle.setAttribute('stroke-width', '2');

            // Tooltip
            const title = document.createElementNS('http://www.w3.org/2000/svg', 'title');
            const date = new Date(timestamps[i]).toLocaleString();
            title.textContent = `${date}\nLatency: ${latency}ms\nStatus: ${status[i] === 1 ? 'Online' : 'Offline'}`;
            circle.appendChild(title);

            svg.appendChild(circle);
        });

        // X-axis labels (show first, middle, last)
        const labelIndices = [0, Math.floor(timestamps.length / 2), timestamps.length - 1];
        labelIndices.forEach(i => {
            if (i >= timestamps.length) return;

            const x = padding.left + i * xStep;
            const y = height - padding.bottom + 20;
            const date = new Date(timestamps[i]);
            const label = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

            const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
            text.setAttribute('x', x);
            text.setAttribute('y', y);
            text.setAttribute('text-anchor', 'middle');
            text.setAttribute('fill', '#6b7280');
            text.setAttribute('font-size', '11');
            text.textContent = label;
            svg.appendChild(text);
        });

        // Y-axis label
        const yLabel = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        yLabel.setAttribute('x', -height / 2);
        yLabel.setAttribute('y', 15);
        yLabel.setAttribute('transform', 'rotate(-90)');
        yLabel.setAttribute('text-anchor', 'middle');
        yLabel.setAttribute('fill', '#6b7280');
        yLabel.setAttribute('font-size', '12');
        yLabel.textContent = 'Latency (ms)';
        svg.appendChild(yLabel);
    }

    /**
     * Render mini chart preview (for proxy cards)
     */
    renderMiniChart(proxyConfig, containerId) {
        const container = document.getElementById(containerId);
        if (!container || !this.historyData || !this.historyData[proxyConfig]) {
            return;
        }

        const data = this.historyData[proxyConfig];
        const { timestamps, latencies, status } = data.trend;

        if (timestamps.length < 2) {
            container.innerHTML = '<span class="mini-chart-no-data">No trend data</span>';
            return;
        }

        // Create mini sparkline
        const width = 100;
        const height = 30;
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('width', width);
        svg.setAttribute('height', height);
        svg.setAttribute('class', 'mini-chart');

        const maxLatency = Math.max(...latencies, 100);
        const xStep = width / (timestamps.length - 1);

        // Draw line
        let pathData = '';
        latencies.forEach((latency, i) => {
            const x = i * xStep;
            const y = height - (latency / maxLatency) * height;
            pathData += (i === 0 ? `M ${x} ${y}` : ` L ${x} ${y}`);
        });

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('d', pathData);
        path.setAttribute('fill', 'none');
        path.setAttribute('stroke', data.stats.success_rate > 0.7 ? '#10b981' : '#ef4444');
        path.setAttribute('stroke-width', '2');
        svg.appendChild(path);

        container.innerHTML = '';
        container.appendChild(svg);
    }

    /**
     * Get top reliable proxies
     */
    getTopReliableProxies(limit = 10) {
        if (!this.historyData) return [];

        const proxies = Object.entries(this.historyData)
            .map(([config, data]) => ({
                config,
                ...data,
                reliability: data.stats.uptime_percentage
            }))
            .sort((a, b) => b.reliability - a.reliability)
            .slice(0, limit);

        return proxies;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ProxyHistoryChart;
}

/**
 * Charts.js Controller for ConfigStream
 * Renders historical trend charts using Chart.js.
 */

class HistoryChart {
    constructor(canvasId) {
        this.canvasId = canvasId;
        this.chart = null;
    }

    render(data) {
        // data: [{label: 'Mon', value: 120}, ...]
        const ctx = document.getElementById(this.canvasId);
        if (!ctx) return;

        // Destroy existing if re-rendering
        if (this.chart) this.chart.destroy();

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: data.map(d => d.label),
                datasets: [{
                    label: 'Working Proxies',
                    data: data.map(d => d.value),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.2)',
                    tension: 0.4,
                    fill: true,
                    pointBackgroundColor: '#0f172a',
                    pointBorderColor: '#3b82f6',
                    pointBorderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false,
                        backgroundColor: '#1e293b',
                        titleColor: '#f8fafc',
                        bodyColor: '#cbd5e1',
                        borderColor: '#334155',
                        borderWidth: 1
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: '#334155'
                        },
                        ticks: {
                            color: '#94a3b8'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#94a3b8'
                        }
                    }
                }
            }
        });
    }
}

// Helper to load history data (reused)
async function loadHistoryData() {
    try {
        const rootPath = window.ROOT_PATH || '';
        const response = await fetch(rootPath + 'data/active_proxy_trend.json');
        if (response.ok) {
            const raw = await response.json();
            // raw: [{timestamp: "ISO", active_count: 123}, ...]

            // Aggregate by day (max count)
            const daily = {};
            raw.forEach(item => {
                const date = item.timestamp.split('T')[0];
                daily[date] = Math.max(daily[date] || 0, item.active_count);
            });

            const entries = Object.entries(daily)
                .sort((a, b) => a[0].localeCompare(b[0]))
                .slice(-7);

            return entries.map(([date, count]) => ({
                label: new Date(date).toLocaleDateString(undefined, { weekday: 'short' }),
                value: count
            }));
        }
    } catch (e) {
        // ignore
    }

    // Audit: Removed random mock data to prevent misleading users.
    // Return empty array or handle error in UI.
    console.warn("History data not available.");
    return [];
}

// Initialize
document.addEventListener("DOMContentLoaded", async () => {
    // Wait for Chart.js to load if CDN is slow, but bound the wait so a blocked
    // CDN cannot leave a 100ms interval polling forever.
    const POLL_INTERVAL_MS = 100;
    const MAX_WAIT_MS = 10000; // give up after 10s
    let waited = 0;
    const checkChartJs = setInterval(async () => {
        if (typeof Chart !== 'undefined') {
            clearInterval(checkChartJs);
            const chartWidget = new HistoryChart("historyChartCanvas"); // ID changed in index.html
            const data = await loadHistoryData();
            chartWidget.render(data);
            return;
        }
        waited += POLL_INTERVAL_MS;
        if (waited >= MAX_WAIT_MS) {
            clearInterval(checkChartJs);
            console.warn("Chart.js failed to load within timeout; history chart skipped.");
        }
    }, POLL_INTERVAL_MS);
});

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
    // ... (Same mock/fetch logic as before) ...
    try {
        const response = await fetch('files/history.json');
        if (response.ok) {
             // Assume history.json format: { "2023-10-01": 500, ... }
             const raw = await response.json();
             // Convert to array
             const entries = Object.entries(raw).sort((a,b) => a[0].localeCompare(b[0])).slice(-7); // Last 7 days
             return entries.map(([date, count]) => ({
                 label: new Date(date).toLocaleDateString(undefined, {weekday: 'short'}),
                 value: count
             }));
        }
    } catch (e) {
        // ignore
    }

    // Fallback Mock
    const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const today = new Date();
    const data = [];
    for (let i = 6; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(d.getDate() - i);
        data.push({
            label: days[d.getDay()],
            value: Math.floor(Math.random() * 500) + 1000
        });
    }
    return data;
}

// Initialize
document.addEventListener("DOMContentLoaded", async () => {
    // Wait for Chart.js to load if CDN is slow
    const checkChartJs = setInterval(async () => {
        if (typeof Chart !== 'undefined') {
            clearInterval(checkChartJs);
            const chartWidget = new HistoryChart("historyChartCanvas"); // ID changed in index.html
            const data = await loadHistoryData();
            chartWidget.render(data);
        }
    }, 100);
});

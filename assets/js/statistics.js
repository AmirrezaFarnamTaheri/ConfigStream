// Page-specific logic for the statistics page
document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('charts-card')) return;

    const chartsContainer = document.getElementById('chartsContainer');
    const chartsEmptyState = document.getElementById('chartsEmptyState');

    // Early return if required elements don't exist
    if (!chartsContainer || !chartsEmptyState) return;

    async function fetchProxyHistory() {
        try {
            const response = await fetchWithCache('output/proxy_history.json');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch proxy history:', error);
            return null;
        }
    }

    async function renderCharts() {
        try {
            const [stats, history] = await Promise.all([fetchStatistics(), fetchProxyHistory()]);

            if (!stats || !stats.protocols || Object.keys(stats.protocols).length === 0) {
                chartsContainer.classList.add('hidden');
                chartsEmptyState.classList.remove('hidden');
                return;
            }

            chartsContainer.classList.remove('hidden');
            chartsEmptyState.classList.add('hidden');

            const style = getComputedStyle(document.body);
            const textColor = style.getPropertyValue('--text-primary-dark');
            const gridColor = style.getPropertyValue('--border-dark');

            const commonOptions = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: textColor
                        }
                    }
                },
                scales: {
                    x: {
                        ticks: { color: textColor },
                        grid: { color: gridColor }
                    },
                    y: {
                        ticks: { color: textColor },
                        grid: { color: gridColor }
                    }
                }
            };

            // Protocol Chart
            const protocolChartCanvas = document.getElementById('protocolChart');
            if (stats.protocols && Object.keys(stats.protocols).length > 0) {
                new Chart(protocolChartCanvas, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(stats.protocols),
                        datasets: [{
                            data: Object.values(stats.protocols),
                            backgroundColor: [
                                'rgba(76, 154, 255, 0.8)',
                                'rgba(255, 86, 48, 0.8)',
                                'rgba(54, 210, 153, 0.8)',
                                'rgba(255, 206, 86, 0.8)',
                                'rgba(153, 102, 255, 0.8)',
                            ],
                            borderColor: style.getPropertyValue('--bg-secondary-dark'),
                        }]
                    },
                    options: { ...commonOptions, plugins: { legend: { ...commonOptions.plugins.legend, position: 'bottom' } } }
                });
            }

            // Country Chart
            const countryChartCanvas = document.getElementById('countryChart');
            const topCountries = Object.entries(stats.countries || {}).sort((a, b) => b[1] - a[1]).slice(0, 10);
            if (topCountries.length > 0) {
                new Chart(countryChartCanvas, {
                    type: 'bar',
                    data: {
                        labels: topCountries.map(c => c[0]),
                        datasets: [{
                            label: 'Proxy Count',
                            data: topCountries.map(c => c[1]),
                            backgroundColor: 'rgba(76, 154, 255, 0.7)',
                            borderColor: 'rgba(76, 154, 255, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: commonOptions
                });
            }

            // ASN Chart
            const asnChartCanvas = document.getElementById('asnChart');
            const topAsns = Object.entries(stats.asns || {}).sort((a, b) => b[1] - a[1]).slice(0, 10);
            if (topAsns.length > 0) {
                new Chart(asnChartCanvas, {
                    type: 'bar',
                    data: {
                        labels: topAsns.map(a => a[0]),
                        datasets: [{
                            label: 'Proxy Count',
                            data: topAsns.map(a => a[1]),
                            backgroundColor: 'rgba(54, 210, 153, 0.7)',
                            borderColor: 'rgba(54, 210, 153, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: commonOptions
                });
            }

            // Time-series Chart
            const timeChartCanvas = document.getElementById('timeChart');
            if (history && history.length > 0) {
                new Chart(timeChartCanvas, {
                    type: 'line',
                    data: {
                        labels: history.map(h => new Date(h.timestamp).toLocaleTimeString()),
                        datasets: [{
                            label: 'Working Proxies',
                            data: history.map(h => h.working),
                            fill: false,
                            borderColor: 'rgba(255, 86, 48, 1)',
                            tension: 0.1
                        }]
                    },
                    options: commonOptions
                });
            }

        } catch (error) {
            console.error('Error rendering charts:', error);
            chartsContainer.classList.add('hidden');
            chartsEmptyState.classList.remove('hidden');
        }
    }
    renderCharts();
});
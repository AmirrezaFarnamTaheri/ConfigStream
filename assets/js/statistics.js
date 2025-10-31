// Page-specific logic for the statistics page
document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('charts-card')) return;

    const chartsContainer = document.getElementById('chartsContainer');
    const chartsEmptyState = document.getElementById('chartsEmptyState');

    // Early return if required elements don't exist
    if (!chartsContainer || !chartsEmptyState) return;

    async function fetchProxyHistory() {
        try {
            const url = `output/proxy_history.json?cb=${Date.now()}`;
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch proxy history:', error);
            return null;
        }
    }

    function updateSummaryStats(stats) {
        // Update summary statistics
        if (stats.total_proxies !== undefined) {
            updateElement('#totalProxies', stats.total_proxies.toLocaleString());
        }
        if (stats.total_working !== undefined) {
            updateElement('#workingProxies', stats.total_working.toLocaleString());
        }
        if (stats.countries !== undefined) {
            updateElement('#totalCountries', Object.keys(stats.countries).length);
        }
        if (stats.protocols !== undefined) {
            updateElement('#totalProtocols', Object.keys(stats.protocols).length);
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

            // Update summary stats
            updateSummaryStats(stats);

            chartsContainer.classList.remove('hidden');
            chartsEmptyState.classList.add('hidden');

            const style = getComputedStyle(document.body);
            const textColor = style.getPropertyValue('--text-primary') || '#333';
            const gridColor = style.getPropertyValue('--border') || '#e0e0e0';
            const bgColor = style.getPropertyValue('--bg-secondary') || '#fff';

            const commonPluginOptions = {
                responsive: true,
                maintainAspectRatio: true,
                aspectRatio: 2,
                plugins: {
                    legend: {
                        labels: {
                            color: textColor,
                            padding: 12,
                            font: {
                                size: 12,
                                family: "'Be Vietnam Pro', sans-serif"
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: bgColor,
                        titleColor: textColor,
                        bodyColor: textColor,
                        borderColor: gridColor,
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 8
                    }
                }
            };

            const commonScaleOptions = {
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

            // Protocol Chart (Doughnut - no scales needed)
            const protocolChartCanvas = document.getElementById('protocolChart');
            if (stats.protocols && Object.keys(stats.protocols).length > 0) {
                new Chart(protocolChartCanvas, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(stats.protocols),
                        datasets: [{
                            data: Object.values(stats.protocols),
                            backgroundColor: [
                                'rgba(94, 85, 241, 0.85)',
                                'rgba(216, 58, 141, 0.85)',
                                'rgba(168, 85, 247, 0.85)',
                                'rgba(0, 191, 165, 0.85)',
                                'rgba(255, 86, 48, 0.85)',
                                'rgba(255, 206, 86, 0.85)',
                            ],
                            borderColor: bgColor,
                            borderWidth: 3,
                            hoverOffset: 8
                        }]
                    },
                    options: {
                        ...commonPluginOptions,
                        aspectRatio: 1.5,
                        plugins: {
                            ...commonPluginOptions.plugins,
                            legend: {
                                ...commonPluginOptions.plugins.legend,
                                position: 'bottom'
                            }
                        }
                    }
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
                            backgroundColor: 'rgba(94, 85, 241, 0.75)',
                            borderColor: 'rgba(94, 85, 241, 1)',
                            borderWidth: 2,
                            borderRadius: 8,
                            borderSkipped: false
                        }]
                    },
                    options: {
                        ...commonPluginOptions,
                        ...commonScaleOptions,
                        scales: {
                            ...commonScaleOptions.scales,
                            y: {
                                ...commonScaleOptions.scales.y,
                                beginAtZero: true
                            }
                        }
                    }
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
                            backgroundColor: 'rgba(0, 191, 165, 0.75)',
                            borderColor: 'rgba(0, 191, 165, 1)',
                            borderWidth: 2,
                            borderRadius: 8,
                            borderSkipped: false
                        }]
                    },
                    options: {
                        ...commonPluginOptions,
                        ...commonScaleOptions,
                        scales: {
                            ...commonScaleOptions.scales,
                            y: {
                                ...commonScaleOptions.scales.y,
                                beginAtZero: true
                            }
                        }
                    }
                });
            } else {
                // Hide ASN chart if no data
                const asnContainer = asnChartCanvas.closest('.chart-container');
                if (asnContainer) {
                    asnContainer.style.display = 'none';
                }
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
                            fill: true,
                            borderColor: 'rgba(216, 58, 141, 1)',
                            backgroundColor: 'rgba(216, 58, 141, 0.15)',
                            borderWidth: 3,
                            tension: 0.4,
                            pointRadius: 4,
                            pointBackgroundColor: 'rgba(216, 58, 141, 1)',
                            pointBorderColor: '#fff',
                            pointBorderWidth: 2,
                            pointHoverRadius: 6
                        }]
                    },
                    options: {
                        ...commonPluginOptions,
                        ...commonScaleOptions,
                        scales: {
                            ...commonScaleOptions.scales,
                            y: {
                                ...commonScaleOptions.scales.y,
                                beginAtZero: true
                            }
                        }
                    }
                });
            } else {
                // Hide time chart if no data
                const timeContainer = timeChartCanvas.closest('.chart-container');
                if (timeContainer) {
                    timeContainer.style.display = 'none';
                }
            }

        } catch (error) {
            console.error('Error rendering charts:', error);
            chartsContainer.classList.add('hidden');
            chartsEmptyState.classList.remove('hidden');
        }
    }
    renderCharts();
});
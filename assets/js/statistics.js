// Page-specific logic for the statistics page
document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('charts-card')) return;

    const chartsContainer = document.getElementById('chartsContainer');
    const chartsEmptyState = document.getElementById('chartsEmptyState');

    // Early return if required elements don't exist
    if (!chartsContainer || !chartsEmptyState) return;

    let currentStats = null;
    let currentProxies = null;

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

    function calculateMetrics(stats, proxies) {
        // Calculate additional metrics
        const metrics = {};

        // Success rate
        if (stats.total_proxies && stats.total_working) {
            metrics.successRate = ((stats.total_working / stats.total_proxies) * 100).toFixed(1);
        }

        // Average latency
        if (proxies && proxies.length > 0) {
            const validLatencies = proxies
                .filter(p => p.latency && p.latency > 0 && p.latency < 10000)
                .map(p => p.latency);

            if (validLatencies.length > 0) {
                metrics.avgLatency = Math.round(
                    validLatencies.reduce((a, b) => a + b, 0) / validLatencies.length
                );
                metrics.minLatency = Math.min(...validLatencies);
            }
        }

        return metrics;
    }

    function updateSummaryStats(stats, proxies) {
        // Update summary statistics
        if (stats.total_proxies !== undefined) {
            updateElement('#totalProxies', stats.total_proxies.toLocaleString());
        }

        if (stats.total_working !== undefined) {
            updateElement('#workingProxies', stats.total_working.toLocaleString());

            // Update percentage
            const successRate = stats.total_proxies > 0
                ? ((stats.total_working / stats.total_proxies) * 100).toFixed(1)
                : 0;
            updateElement('#workingProxiesPercent', `${successRate}% active`, { method: 'innerHTML' });
            updateElement('#successRate', successRate);
        }

        if (stats.countries !== undefined) {
            const countryCount = Object.keys(stats.countries).length;
            updateElement('#totalCountries', countryCount);
        }

        if (stats.protocols !== undefined) {
            updateElement('#totalProtocols', Object.keys(stats.protocols).length);
        }

        // Calculate and update additional metrics
        const metrics = calculateMetrics(stats, proxies);

        if (metrics.avgLatency !== undefined) {
            updateElement('#avgLatency', `${metrics.avgLatency}<span class="metric-unit">ms</span>`, { method: 'innerHTML' });
        }

        if (metrics.successRate !== undefined) {
            updateElement('#successRate', `${metrics.successRate}<span class="metric-unit">%</span>`, { method: 'innerHTML' });
        }

        // Update last updated time
        const now = new Date();
        updateElement('#lastUpdated', now.toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        }));
    }

    function updateInsights(stats, proxies) {
        const metrics = calculateMetrics(stats, proxies);

        // Network Health Score (based on success rate and diversity)
        if (metrics.successRate !== undefined) {
            const healthScore = parseFloat(metrics.successRate);
            let healthGrade = 'Poor';
            if (healthScore >= 90) healthGrade = 'Excellent';
            else if (healthScore >= 75) healthGrade = 'Good';
            else if (healthScore >= 50) healthGrade = 'Fair';

            updateElement('#networkHealthScore', healthGrade);
            updateElement('#networkHealthDesc', `${metrics.successRate}% of proxies are active and responding`);
        }

        // Top Region
        if (stats.countries && Object.keys(stats.countries).length > 0) {
            const topCountry = Object.entries(stats.countries)
                .sort((a, b) => b[1] - a[1])[0];
            const flag = getCountryFlag(topCountry[0]);
            updateElement('#topRegion', `${flag} ${topCountry[0]}`);
            updateElement('#topRegionDesc', `${topCountry[1]} proxies available in this region`);
        }

        // Best Protocol
        if (stats.protocols && Object.keys(stats.protocols).length > 0) {
            const topProtocol = Object.entries(stats.protocols)
                .sort((a, b) => b[1] - a[1])[0];
            updateElement('#bestProtocol', topProtocol[0].toUpperCase());
            updateElement('#bestProtocolDesc', `${topProtocol[1]} proxies using this protocol`);
        }

        // Fastest Response
        if (metrics.minLatency !== undefined) {
            updateElement('#fastestLatency', `${metrics.minLatency}ms`);
            updateElement('#fastestLatencyDesc', `Best response time in the network`);
        }
    }

    async function renderCharts() {
        try {
            const [stats, history, proxies] = await Promise.all([
                fetchStatistics(),
                fetchProxyHistory(),
                fetchProxies()
            ]);

            // Store for later use
            currentStats = stats;
            currentProxies = proxies;

            if (!stats || !stats.protocols || Object.keys(stats.protocols).length === 0) {
                chartsContainer.classList.add('hidden');
                chartsEmptyState.classList.remove('hidden');
                return;
            }

            // Update summary stats and insights
            updateSummaryStats(stats, proxies);
            updateInsights(stats, proxies);

            chartsContainer.classList.remove('hidden');
            chartsEmptyState.classList.add('hidden');

            const style = getComputedStyle(document.body);
            const textColor = style.getPropertyValue('--text-primary') || '#333';
            const gridColor = style.getPropertyValue('--border') || '#e0e0e0';
            const bgColor = style.getPropertyValue('--bg-secondary') || '#fff';

            const commonPluginOptions = {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: {
                            color: textColor
                        }
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
                                'rgba(76, 154, 255, 0.8)',
                                'rgba(255, 86, 48, 0.8)',
                                'rgba(54, 210, 153, 0.8)',
                                'rgba(255, 206, 86, 0.8)',
                                'rgba(153, 102, 255, 0.8)',
                                'rgba(255, 159, 64, 0.8)',
                            ],
                            borderColor: bgColor,
                            borderWidth: 2
                        }]
                    },
                    options: {
                        ...commonPluginOptions,
                        plugins: {
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
                            backgroundColor: 'rgba(76, 154, 255, 0.7)',
                            borderColor: 'rgba(76, 154, 255, 1)',
                            borderWidth: 1
                        }]
                    },
                    options: { ...commonPluginOptions, ...commonScaleOptions }
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
                    options: { ...commonPluginOptions, ...commonScaleOptions }
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
                            fill: false,
                            borderColor: 'rgba(255, 86, 48, 1)',
                            backgroundColor: 'rgba(255, 86, 48, 0.1)',
                            tension: 0.3
                        }]
                    },
                    options: { ...commonPluginOptions, ...commonScaleOptions }
                });
            }

        } catch (error) {
            console.error('Error rendering charts:', error);
            chartsContainer.classList.add('hidden');
            chartsEmptyState.classList.remove('hidden');
        }
    }

    // Refresh Data Button
    const refreshBtn = document.getElementById('refreshData');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            const icon = refreshBtn.querySelector('i');
            icon.style.animation = 'spin 1s linear infinite';
            refreshBtn.disabled = true;

            try {
                // Clear cache
                if (window.api && window.api.clearCache) {
                    window.api.clearCache();
                }

                // Re-render everything
                await renderCharts();

                // Success feedback
                setTimeout(() => {
                    icon.style.animation = '';
                    refreshBtn.disabled = false;
                }, 500);
            } catch (error) {
                console.error('Error refreshing data:', error);
                icon.style.animation = '';
                refreshBtn.disabled = false;
            }
        });
    }

    // Export Data Button
    const exportBtn = document.getElementById('exportData');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            if (!currentStats) {
                alert('No data available to export');
                return;
            }

            const exportData = {
                exported_at: new Date().toISOString(),
                statistics: currentStats,
                proxies_count: currentProxies ? currentProxies.length : 0,
                metrics: calculateMetrics(currentStats, currentProxies)
            };

            const jsonString = JSON.stringify(exportData, null, 2);
            const blob = new Blob([jsonString], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = `analytics-${Date.now()}.json`;
            link.click();
            URL.revokeObjectURL(url);
        });
    }

    // Initial render
    renderCharts();
});

// Add spin animation for refresh button
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);
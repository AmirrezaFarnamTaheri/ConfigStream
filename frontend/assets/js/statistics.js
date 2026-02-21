let countryNameToCode = {};

// Audit: Load country data asynchronously
async function loadCountryData() {
    try {
        const root = window.ROOT_PATH || '';
        const resp = await fetch(root + 'assets/data/countries.json');
        if (resp.ok) {
            countryNameToCode = await resp.json();
        } else {
             console.warn('Country data file not found (404), flags will be missing.');
        }
    } catch (e) {
        console.warn('Failed to load country data, flags might be missing.', e);
    }
}

// Page-specific logic for the statistics page
document.addEventListener('DOMContentLoaded', async () => {
    if (!document.getElementById('charts-card')) return;

    const chartsContainer = document.getElementById('chartsContainer');
    const chartsEmptyState = document.getElementById('chartsEmptyState');

    // Early return if required elements don't exist
    if (!chartsContainer || !chartsEmptyState) return;

    // Initialize country data before rendering charts.
    // If it fails, countryNameToCode will be empty, which is handled gracefully by flag logic.
    await loadCountryData();

    let currentStats = null;
    let currentProxies = null;

    const root = window.ROOT_PATH || '';
    async function fetchProxyHistory() {
        try {
            const url = `${root}data/active_proxy_trend.json?cb=${Date.now()}`;
            const response = await fetch(url);
            if (!response.ok) {
                // Not throwing error to allow partial rendering
                console.warn(`Proxy history fetch failed: ${response.status}`);
                return null;
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch proxy history:', error);
            return null;
        }
    }

    async function fetchEvasionTrend() {
        try {
            const url = `${root}data/evasion_trend.json?cb=${Date.now()}`;
            const response = await fetch(url);
            if (!response.ok) {
                console.warn(`Evasion trend fetch failed: ${response.status}`);
                return null;
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to fetch evasion trend:', error);
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

    // Centralized Color Logic
    // Using a seeded or hash-based color generator for consistency across charts
    function generateColor(label, index) {
        // Simple hash of the label to pick a hue
        let hash = 0;
        const str = label.toString();
        for (let i = 0; i < str.length; i++) {
            hash = str.charCodeAt(i) + ((hash << 5) - hash);
        }
        const hue = Math.abs(hash % 360);
        return `hsl(${hue}, 70%, 60%)`;
    }

    function updateSummaryStats(stats, proxies, metadata) {
        // STANDARDIZED - Use canonical backend field names only
        const totalSourced = (metadata && metadata.total_lines_sourced) || 0;
        updateElement('#totalSourced', totalSourced.toLocaleString());

        const uniqueCount = (metadata && metadata.total_unique_candidates) || 0;
        updateElement('#totalConfigs', uniqueCount.toLocaleString());

        // total_working = native + shielded (total usable); total_valid_proxies = native only
        const workingCount = (metadata && (metadata.total_working ?? metadata.total_valid_proxies ?? metadata.working)) || 0;
        updateElement('#workingConfigs', workingCount.toLocaleString());

        const revived = (metadata && metadata.total_revived) || 0;
        updateElement('#totalRevived', revived.toLocaleString());

        const threats = (metadata && metadata.total_dirty) || 0;
        updateElement('#threatsBlocked', threats.toLocaleString());
        updateElement('#threatsNeutralized', threats.toLocaleString());

        const smartChains = (metadata && metadata.total_smart_chains) || 0;
        updateElement('#smartChains', smartChains.toLocaleString());

        const vwarpWinRate = (metadata && metadata.vwarp_win_rate) || 0;
        updateElement('#vwarpWinRate', (vwarpWinRate !== undefined) ? Math.round(vwarpWinRate) + '%' : '0%');
        
        // Evasion metrics
        const shielded = (metadata && metadata.shielded_count) || 0;
        updateElement('#shieldedCount', shielded.toLocaleString());
        
        const evasionUtls = (metadata && metadata.evasion_utls_enabled) || 0;
        updateElement('#evasionUtls', evasionUtls.toLocaleString());
        
        const evasionDnsSafe = (metadata && metadata.evasion_dns_safe_count) || 0;
        updateElement('#evasionDnsSafe', evasionDnsSafe.toLocaleString());
        
        const evasionDnsHardened = (metadata && metadata.evasion_dns_hardened_count) || 0;
        updateElement('#evasionDnsHardened', evasionDnsHardened.toLocaleString());

        // Update Hero Stats (Source Count & Frequency)
        const totalSources = (metadata && metadata.total_configured_sources) || 0;
        const updateInterval = (metadata && metadata.update_interval_hours) || 6;
        updateElement('#heroSourceCount', totalSources.toLocaleString());
        updateElement('#heroUpdateFrequency', updateInterval.toString());

        const metrics = calculateMetrics(stats, proxies);

        // Use sanitize logic inside updateElement or manual sanitization.
        // Since updateElement uses DOMPurify by default unless trustedHTML is true,
        // we should avoid trustedHTML=true unless strictly necessary.
        // Here we are injecting simple HTML (<span>), so we construct it carefully.
        if (metrics.avgLatency !== undefined) {
             // Safe: metrics.avgLatency is a number
            updateElement('#avgLatency', `${metrics.avgLatency}<span class="metric-unit">ms</span>`, { method: 'innerHTML', trustedHTML: true });
        }

        if (metrics.successRate !== undefined) {
             // Safe: metrics.successRate is a number/string from toFixed
            updateElement('#successRate', `${metrics.successRate}<span class="metric-unit">%</span>`, { method: 'innerHTML', trustedHTML: true });
        }

        // Update last updated time
        if (metadata && metadata.last_updated_utc) {
            const date = new Date(metadata.last_updated_utc);
            const formattedTime = date.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            updateElement('#lastUpdated', formattedTime);
            updateElement('#footerUpdate', formatTimestamp(date));
        } else {
            const now = new Date();
            const formattedTime = now.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            updateElement('#lastUpdated', formattedTime);
            updateElement('#footerUpdate', formatTimestamp(now));
        }
    }

    function updateInsights(stats, proxies) {
        const metrics = calculateMetrics(stats, proxies);

        if (metrics.successRate !== undefined) {
            const healthScore = parseFloat(metrics.successRate);
            let healthGrade = 'Poor';
            if (healthScore >= 90) healthGrade = 'Excellent';
            else if (healthScore >= 75) healthGrade = 'Good';
            else if (healthScore >= 50) healthGrade = 'Fair';

            updateElement('#networkHealthScore', healthGrade);
            updateElement('#networkHealthDesc', `${metrics.successRate}% of proxies are active and responding`);
        }

        const countryStats = stats.country_stats || stats.countries || {};
        if (countryStats && Object.keys(countryStats).length > 0) {
            const topCountry = Object.entries(countryStats)
                .sort((a, b) => b[1] - a[1])[0];

            const countryKey = topCountry[0];
            let countryCode = null;
            let countryName = countryKey;

            if (countryKey.length === 2) {
                countryCode = countryKey.toUpperCase();
                const foundName = Object.keys(countryNameToCode).find(key => countryNameToCode[key] === countryCode);
                countryName = foundName || countryCode;
            } else {
                countryCode = countryNameToCode[countryKey];
            }

            // Sanitized insertion: getCountryFlag returns an emoji string
            const flag = countryCode ? getCountryFlag(countryCode) : '🌍';
            // countryName comes from our internal mapping or stats key. If stats key is untrusted, we should sanitize.
            // DOMPurify is handled by updateElement by default.
            // We use trustedHTML: false (default) and construct string safely?
            // updateElement with innerHTML sanitizes the whole string.
            updateElement('#topRegion', `${flag} ${countryName}`, { method: 'innerHTML' }); // Default sanitization applied
            updateElement('#topRegionDesc', `${topCountry[1]} proxies available in this region`);
        }

        if (stats.protocols && Object.keys(stats.protocols).length > 0) {
            const topProtocol = Object.entries(stats.protocols)
                .sort((a, b) => b[1] - a[1])[0];
            updateElement('#bestProtocol', topProtocol[0].toUpperCase());
            updateElement('#bestProtocolDesc', `${topProtocol[1]} proxies using this protocol`);
        }

        if (metrics.minLatency !== undefined) {
            updateElement('#fastestLatency', `${metrics.minLatency}ms`);
            updateElement('#fastestLatencyDesc', `Best response time in the network`);
        }
    }

    async function renderCharts() {
        try {
            const [stats, history, proxies, metadata, evasionTrend] = await Promise.all([
                fetchStatistics(),
                fetchProxyHistory(),
                fetchProxies(),
                fetchMetadata(),
                fetchEvasionTrend()
            ]);

            currentStats = stats;
            currentProxies = proxies;

            if (!stats || !stats.protocols || Object.keys(stats.protocols).length === 0) {
                chartsContainer.classList.add('hidden');
                chartsEmptyState.classList.remove('hidden');
                return;
            }

            updateSummaryStats(stats, proxies, metadata);
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
                        labels: { color: textColor }
                    }
                }
            };

            const commonScaleOptions = {
                scales: {
                    x: { ticks: { color: textColor }, grid: { color: gridColor } },
                    y: { ticks: { color: textColor }, grid: { color: gridColor } }
                }
            };

            // Protocol Chart
            const protocolChartCanvas = document.getElementById('protocolChart');
            if (stats.protocols && Object.keys(stats.protocols).length > 0) {
                const labels = Object.keys(stats.protocols);
                const chartColors = labels.map((p, i) => generateColor(p, i));

                new Chart(protocolChartCanvas, {
                    type: 'doughnut',
                    data: {
                        labels: labels,
                        datasets: [{
                            data: Object.values(stats.protocols),
                            backgroundColor: chartColors,
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
            const countryStats = stats.country_stats || stats.countries || {};
            const topCountries = Object.entries(countryStats || {}).sort((a, b) => b[1] - a[1]).slice(0, 10);
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
                const asnContainer = asnChartCanvas.closest('.chart-container');
                if (asnContainer) asnContainer.style.display = 'none';
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
                            data: history.map(h => h.active_count),
                            fill: true,
                            borderColor: 'rgba(255, 86, 48, 1)',
                            backgroundColor: 'rgba(255, 86, 48, 0.1)',
                            tension: 0.4,
                            pointRadius: 3,
                            pointHoverRadius: 5
                        }]
                    },
                    options: {
                        ...commonPluginOptions,
                        ...commonScaleOptions,
                        plugins: {
                            ...commonPluginOptions.plugins,
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return `Active Proxies: ${context.parsed.y}`;
                                    }
                                }
                            }
                        }
                    }
                });
            }

            // Evasion Trend Chart (Time-series)
            const evasionTrendCanvas = document.getElementById('evasionTrendChart');
            if (evasionTrendCanvas && evasionTrend && evasionTrend.length > 0) {
                const labels = evasionTrend.map(e => {
                    const date = new Date(e.timestamp);
                    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                });

                new Chart(evasionTrendCanvas, {
                    type: 'line',
                    data: {
                        labels: labels,
                        datasets: [
                            {
                                label: 'Shielded (Gold)',
                                data: evasionTrend.map(e => e.shielded_count || 0),
                                borderColor: 'rgba(255, 215, 0, 1)',
                                backgroundColor: 'rgba(255, 215, 0, 0.1)',
                                tension: 0.4,
                                pointRadius: 2,
                                pointHoverRadius: 4,
                                fill: true
                            },
                            {
                                label: 'Revived (WARP)',
                                data: evasionTrend.map(e => e.revived_warp || 0),
                                borderColor: 'rgba(76, 154, 255, 1)',
                                backgroundColor: 'rgba(76, 154, 255, 0.1)',
                                tension: 0.4,
                                pointRadius: 2,
                                pointHoverRadius: 4,
                                fill: true
                            },
                            {
                                label: 'Revived (VWARP)',
                                data: evasionTrend.map(e => e.revived_vwarp || 0),
                                borderColor: 'rgba(54, 210, 153, 1)',
                                backgroundColor: 'rgba(54, 210, 153, 0.1)',
                                tension: 0.4,
                                pointRadius: 2,
                                pointHoverRadius: 4,
                                fill: true
                            },
                            {
                                label: 'uTLS Enabled',
                                data: evasionTrend.map(e => e.evasion_utls_enabled || 0),
                                borderColor: 'rgba(74, 144, 226, 1)',
                                backgroundColor: 'rgba(74, 144, 226, 0.1)',
                                tension: 0.4,
                                pointRadius: 2,
                                pointHoverRadius: 4,
                                fill: false
                            },
                            {
                                label: 'DNS-Hardened',
                                data: evasionTrend.map(e => e.evasion_dns_hardened_count || 0),
                                borderColor: 'rgba(54, 210, 153, 1)',
                                backgroundColor: 'rgba(54, 210, 153, 0.1)',
                                tension: 0.4,
                                pointRadius: 2,
                                pointHoverRadius: 4,
                                fill: false,
                                borderDash: [5, 5]
                            }
                        ]
                    },
                    options: {
                        ...commonPluginOptions,
                        ...commonScaleOptions,
                        plugins: {
                            ...commonPluginOptions.plugins,
                            tooltip: {
                                mode: 'index',
                                intersect: false,
                                callbacks: {
                                    label: function(context) {
                                        return `${context.dataset.label}: ${context.parsed.y}`;
                                    }
                                }
                            },
                            legend: {
                                display: true,
                                position: 'bottom'
                            }
                        },
                        scales: {
                            ...commonScaleOptions.scales,
                            y: {
                                beginAtZero: true,
                                ticks: {
                                    precision: 0
                                }
                            }
                        }
                    }
                });
            } else if (evasionTrendCanvas) {
                // Hide chart container if no data
                const container = evasionTrendCanvas.closest('.chart-container');
                if (container) container.style.display = 'none';
            }

            // Latency by Country Chart
            const latencyByCountryCanvas = document.getElementById('latencyByCountryChart');
            if (latencyByCountryCanvas && proxies && proxies.length > 0) {
                const countryLatencies = {};
                const countryCounts = {};

                proxies.forEach(p => {
                    if (p.country && p.latency && p.latency > 0 && p.latency < 5000) {
                        const country = p.country.toUpperCase();
                        if (!countryLatencies[country]) {
                            countryLatencies[country] = 0;
                            countryCounts[country] = 0;
                        }
                        countryLatencies[country] += p.latency;
                        countryCounts[country]++;
                    }
                });

                const countryAvgLatencies = Object.entries(countryLatencies)
                    .map(([country, totalLatency]) => ({
                        country,
                        avgLatency: Math.round(totalLatency / countryCounts[country])
                    }))
                    .sort((a, b) => a.avgLatency - b.avgLatency)
                    .slice(0, 15);

                if (countryAvgLatencies.length > 0) {
                    new Chart(latencyByCountryCanvas, {
                        type: 'bar',
                        data: {
                            labels: countryAvgLatencies.map(c => c.country),
                            datasets: [{
                                label: 'Avg Latency (ms)',
                                data: countryAvgLatencies.map(c => c.avgLatency),
                                backgroundColor: 'rgba(75, 192, 192, 0.7)',
                                borderColor: 'rgba(75, 192, 192, 1)',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            ...commonPluginOptions,
                            ...commonScaleOptions,
                            plugins: {
                                ...commonPluginOptions.plugins,
                                legend: { display: false }
                            }
                        }
                    });
                }
            }

            // Misnamed charts. Use the correct ID from HTML or standardize.
            // HTML typically uses 'latencyByProtocolChart' or 'protocolPerformanceChart'.
            // We'll target 'latencyByProtocolChart' and remove duplicate logic for 'protocolPerformanceChart' if it was doing the same thing.

            const latencyByProtocolCanvas = document.getElementById('latencyByProtocolChart');
            if (latencyByProtocolCanvas && proxies && proxies.length > 0) {
                const protocolLatencies = {};
                const protocolCounts = {};

                proxies.forEach(p => {
                    if (p.protocol && p.latency && p.latency > 0 && p.latency < 10000) {
                        if (!protocolLatencies[p.protocol]) {
                            protocolLatencies[p.protocol] = 0;
                            protocolCounts[p.protocol] = 0;
                        }
                        protocolLatencies[p.protocol] += p.latency;
                        protocolCounts[p.protocol]++;
                    }
                });

                const protocolAvgLatencies = Object.entries(protocolLatencies)
                    .map(([protocol, totalLatency]) => ({
                        protocol,
                        avgLatency: Math.round(totalLatency / protocolCounts[protocol])
                    }))
                    .sort((a, b) => a.avgLatency - b.avgLatency)
                    .slice(0, 10);

                if (protocolAvgLatencies.length > 0) {
                    const existingChart = Chart.getChart(latencyByProtocolCanvas);
                    if (existingChart) existingChart.destroy();

                    const labels = protocolAvgLatencies.map(p => p.protocol.toUpperCase());
                    const colors = labels.map((p, i) => generateColor(p, i));

                    new Chart(latencyByProtocolCanvas, {
                        type: 'bar',
                        data: {
                            labels: labels,
                            datasets: [{
                                label: 'Avg Latency (ms)',
                                data: protocolAvgLatencies.map(p => p.avgLatency),
                                backgroundColor: colors,
                                borderColor: colors,
                                borderWidth: 1
                            }]
                        },
                        options: {
                            ...commonPluginOptions,
                            ...commonScaleOptions,
                            indexAxis: 'y',
                            plugins: {
                                ...commonPluginOptions.plugins,
                                legend: { display: false }
                            }
                        }
                    });
                }
            }

            // Latency Distribution Chart
            const latencyChartCanvas = document.getElementById('latencyChart');
            if (latencyChartCanvas && proxies && proxies.length > 0) {
                const validLatencies = proxies
                    .filter(p => p.latency && p.latency > 0 && p.latency < 10000)
                    .map(p => p.latency);

                if (validLatencies.length > 0) {
                    const bins = [0, 100, 200, 500, 1000, 2000, 5000, 10000];
                    const binLabels = ['<100ms', '100-200ms', '200-500ms', '500ms-1s', '1-2s', '2-5s', '5-10s'];
                    const binCounts = new Array(bins.length - 1).fill(0);

                    validLatencies.forEach(latency => {
                        for (let i = 0; i < bins.length - 1; i++) {
                            if (latency >= bins[i] && latency < bins[i + 1]) {
                                binCounts[i]++;
                                break;
                            }
                        }
                    });

                    new Chart(latencyChartCanvas, {
                        type: 'bar',
                        data: {
                            labels: binLabels,
                            datasets: [{
                                label: 'Proxy Count',
                                data: binCounts,
                                backgroundColor: 'rgba(153, 102, 255, 0.7)',
                                borderColor: 'rgba(153, 102, 255, 1)',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            ...commonPluginOptions,
                            ...commonScaleOptions,
                            plugins: {
                                ...commonPluginOptions.plugins,
                                legend: { display: false }
                            }
                        }
                    });
                }
            }

        } catch (error) {
            console.error('Error rendering charts:', error);
            chartsContainer.classList.add('hidden');
            chartsEmptyState.classList.remove('hidden');
        }
    }

    const refreshBtn = document.getElementById('refreshData');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', async () => {
            const icon = refreshBtn.querySelector('i');
            icon.style.animation = 'spin 1s linear infinite';
            refreshBtn.disabled = true;

            try {
                if (window.api && window.api.clearCache) {
                    window.api.clearCache();
                }
                await renderCharts();
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

    // Chart Action Buttons (3-dot menu)
    const chartActionButtons = document.querySelectorAll('.chart-action');
    chartActionButtons.forEach(button => {
        button.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();

            const chartContainer = button.closest('.chart-container');
            if (!chartContainer) return;

            const chartHeader = chartContainer.querySelector('.chart-header');
            if (!chartHeader) return;

            const chartTitle = chartHeader.querySelector('h3')?.textContent || 'Chart';
            const canvas = chartContainer.querySelector('canvas');
            if (!canvas) return;

            // Remove only an existing menu if one is already open
            const existingMenu = document.querySelector('.chart-action-menu');
            if (existingMenu) existingMenu.remove();

            const menu = document.createElement('div');
            menu.className = 'chart-action-menu';
            menu.setAttribute('role', 'menu');
            menu.tabIndex = -1;

            const rect = button.getBoundingClientRect();
            const margin = 8;
            const assumedMinWidth = 200;

            const computePosition = () => {
              let top = rect.bottom + margin;
              let left = rect.right - assumedMinWidth;
              const maxLeft = window.innerWidth - margin - assumedMinWidth;
              const maxTop = window.innerHeight - margin - 10;
              left = Math.max(margin, Math.min(left, maxLeft));
              top = Math.max(margin, Math.min(top, maxTop));
              menu.style.top = `${top}px`;
              menu.style.left = `${left}px`;
            };

            menu.style.cssText = `
              position: fixed;
              min-width: ${assumedMinWidth}px;
              z-index: 9999;
              background: var(--surface-card);
              border: 1px solid var(--border);
              box-shadow: 0 4px 6px rgba(0,0,0,0.1);
              border-radius: 4px;
            `;

            document.body.appendChild(menu);
            computePosition();

            const onResize = () => computePosition();
            window.addEventListener('resize', onResize);

            let rafId = null;
            const requestReposition = () => {
              if (rafId !== null) return;
              rafId = requestAnimationFrame(() => {
                rafId = null;
                computePosition();
              });
            };

            const closeMenu = () => {
              if (menu.parentNode) document.body.removeChild(menu);
              document.removeEventListener('click', handleOutsideClick, true);
              window.removeEventListener('resize', onResize);
              if (rafId !== null) cancelAnimationFrame(rafId);
              document.removeEventListener('keydown', onKeyDown);
              button?.focus?.();
            };

            const isClickOutside = (event) => {
              const target = event.target instanceof Node ? event.target : null;
              const path = typeof event.composedPath === 'function' ? event.composedPath() : null;
              const withinMenu = path ? path.includes(menu) : (target ? menu.contains(target) : false);
              const withinButton = button ? (path ? path.includes(button) : (target ? button.contains(target) || target === button : false)) : false;
              return !(withinMenu || withinButton);
            };

            const handleOutsideClick = (event) => {
              if (isClickOutside(event)) {
                closeMenu();
              }
            };

            const onKeyDown = (evt) => {
              if (evt.key === 'Escape') {
                evt.stopPropagation();
                closeMenu();
              }
            };

            const createMenuButton = (text, onClick, isLast = false) => {
              const btn = document.createElement('button');
              btn.type = 'button';
              btn.textContent = text;
              btn.setAttribute('role', 'menuitem');
              btn.style.cssText = `
                display: block;
                width: 100%;
                padding: 10px 12px;
                border: none;
                background: none;
                text-align: left;
                cursor: pointer;
                font-size: 14px;
                color: var(--text-primary);
                ${!isLast ? 'border-bottom: 1px solid var(--border);' : ''}
              `;
              btn.addEventListener('mouseover', () => {
                btn.style.backgroundColor = 'var(--bg-secondary)';
              });
              btn.addEventListener('mouseout', () => {
                btn.style.backgroundColor = '';
              });
              btn.addEventListener('click', (evt) => {
                evt.stopPropagation();
                try { onClick(); } catch (err) {
                  console.error('Chart action failed:', err);
                  alert('Action failed. Please try again.');
                } finally {
                  closeMenu();
                }
              });
              return btn;
            };

            // Use safe filenames for export
            // We strip unsafe chars from chartTitle in export function,
            // but we can ensure correctness here too.

            menu.appendChild(createMenuButton('📊 Export as PNG', () => {
              exportChartAsImage(canvas, chartTitle, 'png');
            }));
            menu.appendChild(createMenuButton('💾 Export Data as JSON', () => {
              exportChartData(canvas, chartTitle);
            }, true));

            setTimeout(() => {
              menu.focus();
              document.addEventListener('click', handleOutsideClick, true);
              document.addEventListener('keydown', onKeyDown);
            }, 0);
        });
    });

    function exportChartAsImage(canvas, title, format) {
        try {
            // Strict sanitization for filenames
            const safeTitle = title.replace(/[^a-z0-9]/gi, '-').toLowerCase();
            const filename = `${safeTitle}-${Date.now()}.png`;
            if (format === 'png') {
                canvas.toBlob(blob => {
                    if (!blob) {
                        alert('Failed to export chart image due to browser security restrictions.');
                        return;
                    }
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = filename;
                    try {
                        document.body.appendChild(link);
                        link.click();
                    } finally {
                        setTimeout(() => {
                            document.body.removeChild(link);
                            URL.revokeObjectURL(url);
                        }, 100);
                    }
                });
            }
        } catch (error) {
            console.error('Error exporting chart:', error);
            alert('Failed to export chart.');
        }
    }

    function exportChartData(canvas, title) {
        try {
            // Use Chart.js 4.x API instead of older internal properties
            const chartInstance = (typeof Chart !== 'undefined' && Chart.getChart) ? Chart.getChart(canvas) : null;
            if (!chartInstance || !chartInstance.data) {
                alert('Unable to export chart data. Chart instance not found.');
                return;
            }
            const data = chartInstance.data;
            const safeLabels = Array.isArray(data.labels) ? data.labels.slice() : [];
            const safeDatasets = Array.isArray(data.datasets)
                ? data.datasets.map(ds => ({
                    label: typeof ds.label === 'string' ? ds.label : '',
                    data: Array.isArray(ds.data) ? ds.data.slice() : []
                }))
                : [];

            // Sanitize content before export (defense in depth)
            const exportData = {
                title,
                exported_at: new Date().toISOString(),
                labels: safeLabels,
                datasets: safeDatasets
            };

            const jsonString = JSON.stringify(exportData, null, 2);
            const blob = new Blob([jsonString], { type: 'application/json' });
            const safeTitle = title.replace(/[^a-z0-9]/gi, '-').toLowerCase();
            const filename = `${safeTitle}-data-${Date.now()}.json`;
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            try {
                document.body.appendChild(link);
                link.click();
            } finally {
                setTimeout(() => {
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                }, 100);
            }
        } catch (error) {
            console.error('Error exporting data:', error);
            alert('Failed to export data.');
        }
    }

    renderCharts();
});

const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
`;
document.head.appendChild(style);

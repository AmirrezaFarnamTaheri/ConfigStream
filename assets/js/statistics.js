// Country name to ISO code mapping (complete ISO 3166-1 alpha-2)
const countryNameToCode = {
    'Andorra': 'AD', 'United Arab Emirates': 'AE', 'Afghanistan': 'AF', 'Antigua and Barbuda': 'AG',
    'Anguilla': 'AI', 'Albania': 'AL', 'Armenia': 'AM', 'Angola': 'AO', 'Antarctica': 'AQ',
    'Argentina': 'AR', 'American Samoa': 'AS', 'Austria': 'AT', 'Australia': 'AU', 'Aruba': 'AW',
    'Åland Islands': 'AX', 'Azerbaijan': 'AZ', 'Bosnia and Herzegovina': 'BA', 'Barbados': 'BB',
    'Bangladesh': 'BD', 'Belgium': 'BE', 'Burkina Faso': 'BF', 'Bulgaria': 'BG', 'Bahrain': 'BH',
    'Burundi': 'BI', 'Benin': 'BJ', 'Saint Barthélémy': 'BL', 'Bermuda': 'BM', 'Brunei': 'BN',
    'Bolivia': 'BO', 'Caribbean Netherlands': 'BQ', 'Brazil': 'BR', 'Bahamas': 'BS', 'Bhutan': 'BT',
    'Bouvet Island': 'BV', 'Botswana': 'BW', 'Belarus': 'BY', 'Belize': 'BZ', 'Canada': 'CA',
    'Cocos (Keeling) Islands': 'CC', 'DR Congo': 'CD', 'Central African Republic': 'CF',
    'Republic of the Congo': 'CG', 'Switzerland': 'CH', 'Ivory Coast': 'CI', 'Cook Islands': 'CK',
    'Chile': 'CL', 'Cameroon': 'CM', 'China': 'CN', 'Colombia': 'CO', 'Costa Rica': 'CR',
    'Cuba': 'CU', 'Cape Verde': 'CV', 'Curaçao': 'CW', 'Christmas Island': 'CX', 'Cyprus': 'CY',
    'Czechia': 'CZ', 'Germany': 'DE', 'Djibouti': 'DJ', 'Denmark': 'DK', 'Dominica': 'DM',
    'Dominican Republic': 'DO', 'Algeria': 'DZ', 'Ecuador': 'EC', 'Estonia': 'EE', 'Egypt': 'EG',
    'Western Sahara': 'EH', 'Eritrea': 'ER', 'Spain': 'ES', 'Ethiopia': 'ET', 'Finland': 'FI',
    'Fiji': 'FJ', 'Falkland Islands': 'FK', 'Micronesia': 'FM', 'Faroe Islands': 'FO', 'France': 'FR',
    'Gabon': 'GA', 'United Kingdom': 'GB', 'Grenada': 'GD', 'Georgia': 'GE', 'French Guiana': 'GF',
    'Guernsey': 'GG', 'Ghana': 'GH', 'Gibraltar': 'GI', 'Greenland': 'GL', 'Gambia': 'GM',
    'Guinea': 'GN', 'Guadeloupe': 'GP', 'Equatorial Guinea': 'GQ', 'Greece': 'GR', 'South Georgia': 'GS',
    'Guatemala': 'GT', 'Guam': 'GU', 'Guinea-Bissau': 'GW', 'Guyana': 'GY', 'Hong Kong': 'HK',
    'Heard Island and McDonald Islands': 'HM', 'Honduras': 'HN', 'Croatia': 'HR', 'Haiti': 'HT',
    'Hungary': 'HU', 'Indonesia': 'ID', 'Ireland': 'IE', 'Israel': 'IL', 'Isle of Man': 'IM',
    'India': 'IN', 'British Indian Ocean Territory': 'IO', 'Iraq': 'IQ', 'Iran': 'IR', 'Iceland': 'IS',
    'Italy': 'IT', 'Jersey': 'JE', 'Jamaica': 'JM', 'Jordan': 'JO', 'Japan': 'JP', 'Kenya': 'KE',
    'Kyrgyzstan': 'KG', 'Cambodia': 'KH', 'Kiribati': 'KI', 'Comoros': 'KM', 'Saint Kitts and Nevis': 'KN',
    'North Korea': 'KP', 'South Korea': 'KR', 'Kuwait': 'KW', 'Cayman Islands': 'KY', 'Kazakhstan': 'KZ',
    'Laos': 'LA', 'Lebanon': 'LB', 'Saint Lucia': 'LC', 'Liechtenstein': 'LI', 'Sri Lanka': 'LK',
    'Liberia': 'LR', 'Lesotho': 'LS', 'Lithuania': 'LT', 'Luxembourg': 'LU', 'Latvia': 'LV',
    'Libya': 'LY', 'Morocco': 'MA', 'Monaco': 'MC', 'Moldova': 'MD', 'Montenegro': 'ME',
    'Saint Martin': 'MF', 'Madagascar': 'MG', 'Marshall Islands': 'MH', 'North Macedonia': 'MK',
    'Mali': 'ML', 'Myanmar': 'MM', 'Mongolia': 'MN', 'Macau': 'MO', 'Northern Mariana Islands': 'MP',
    'Martinique': 'MQ', 'Mauritania': 'MR', 'Montserrat': 'MS', 'Malta': 'MT', 'Mauritius': 'MU',
    'Maldives': 'MV', 'Malawi': 'MW', 'Mexico': 'MX', 'Malaysia': 'MY', 'Mozambique': 'MZ',
    'Namibia': 'NA', 'New Caledonia': 'NC', 'Niger': 'NE', 'Norfolk Island': 'NF', 'Nigeria': 'NG',
    'Nicaragua': 'NI', 'Netherlands': 'NL', 'Norway': 'NO', 'Nepal': 'NP', 'Nauru': 'NR',
    'Niue': 'NU', 'New Zealand': 'NZ', 'Oman': 'OM', 'Panama': 'PA', 'Peru': 'PE',
    'French Polynesia': 'PF', 'Papua New Guinea': 'PG', 'Philippines': 'PH', 'Pakistan': 'PK',
    'Poland': 'PL', 'Saint Pierre and Miquelon': 'PM', 'Pitcairn Islands': 'PN', 'Puerto Rico': 'PR',
    'Palestine': 'PS', 'Portugal': 'PT', 'Palau': 'PW', 'Paraguay': 'PY', 'Qatar': 'QA',
    'Réunion': 'RE', 'Romania': 'RO', 'Serbia': 'RS', 'Russia': 'RU', 'Rwanda': 'RW',
    'Saudi Arabia': 'SA', 'Solomon Islands': 'SB', 'Seychelles': 'SC', 'Sudan': 'SD', 'Sweden': 'SE',
    'Singapore': 'SG', 'Saint Helena, Ascension and Tristan da Cunha': 'SH', 'Slovenia': 'SI',
    'Svalbard and Jan Mayen': 'SJ', 'Slovakia': 'SK', 'Sierra Leone': 'SL', 'San Marino': 'SM',
    'Senegal': 'SN', 'Somalia': 'SO', 'Suriname': 'SR', 'South Sudan': 'SS', 'São Tomé and Príncipe': 'ST',
    'El Salvador': 'SV', 'Sint Maarten': 'SX', 'Syria': 'SY', 'Eswatini': 'SZ',
    'Turks and Caicos Islands': 'TC', 'Chad': 'TD', 'French Southern and Antarctic Lands': 'TF',
    'Togo': 'TG', 'Thailand': 'TH', 'Tajikistan': 'TJ', 'Tokelau': 'TK', 'Timor-Leste': 'TL',
    'Turkmenistan': 'TM', 'Tunisia': 'TN', 'Tonga': 'TO', 'Turkey': 'TR', 'Trinidad and Tobago': 'TT',
    'Tuvalu': 'TV', 'Taiwan': 'TW', 'Tanzania': 'TZ', 'Ukraine': 'UA', 'Uganda': 'UG',
    'United States Minor Outlying Islands': 'UM', 'United States': 'US', 'Uruguay': 'UY',
    'Uzbekistan': 'UZ', 'Vatican City': 'VA', 'Saint Vincent and the Grenadines': 'VC',
    'Venezuela': 'VE', 'British Virgin Islands': 'VG', 'United States Virgin Islands': 'VI',
    'Vietnam': 'VN', 'Vanuatu': 'VU', 'Wallis and Futuna': 'WF', 'Samoa': 'WS', 'Kosovo': 'XK',
    'Yemen': 'YE', 'Mayotte': 'YT', 'South Africa': 'ZA', 'Zambia': 'ZM', 'Zimbabwe': 'ZW',
    // Common aliases
    'The Netherlands': 'NL', 'Türkiye': 'TR'
};

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

    function updateSummaryStats(stats, proxies, metadata) {
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
            updateElement('#avgLatency', `${metrics.avgLatency}<span class="metric-unit">ms</span>`, { method: 'innerHTML', trustedHTML: true });
        }

        if (metrics.successRate !== undefined) {
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

            // Also update footer timestamp
            const footerTimestamp = formatTimestamp(date);
            updateElement('#footerUpdate', footerTimestamp);
        } else {
            // Fallback to current time if metadata is not available
            const now = new Date();
            const formattedTime = now.toLocaleString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            });
            updateElement('#lastUpdated', formattedTime);
            const footerTimestamp = formatTimestamp(now);
            updateElement('#footerUpdate', footerTimestamp);
        }
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
            const countryName = topCountry[0];
            const countryCode = countryNameToCode[countryName];
            // Only use flag if we have a valid 2-letter country code
            const flag = countryCode ? getCountryFlag(countryCode) : '🌍';
            updateElement('#topRegion', `${flag} ${countryName}`);
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
            const [stats, history, proxies, metadata] = await Promise.all([
                fetchStatistics(),
                fetchProxyHistory(),
                fetchProxies(),
                fetchMetadata()
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

            // Latency Distribution Chart
            const latencyChartCanvas = document.getElementById('latencyChart');
            if (proxies && proxies.length > 0) {
                const validLatencies = proxies
                    .filter(p => p.latency && p.latency > 0 && p.latency < 10000)
                    .map(p => p.latency);

                if (validLatencies.length > 0) {
                    // Create histogram bins
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
                                legend: {
                                    display: false
                                }
                            }
                        }
                    });
                }
            }

            // Protocol Performance Chart
            const protocolPerformanceCanvas = document.getElementById('protocolPerformanceChart');
            if (proxies && proxies.length > 0) {
                // Calculate average latency per protocol
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
                    new Chart(protocolPerformanceCanvas, {
                        type: 'bar',
                        data: {
                            labels: protocolAvgLatencies.map(p => p.protocol.toUpperCase()),
                            datasets: [{
                                label: 'Avg Latency (ms)',
                                data: protocolAvgLatencies.map(p => p.avgLatency),
                                backgroundColor: 'rgba(255, 206, 86, 0.7)',
                                borderColor: 'rgba(255, 206, 86, 1)',
                                borderWidth: 1
                            }]
                        },
                        options: {
                            ...commonPluginOptions,
                            ...commonScaleOptions,
                            indexAxis: 'y',
                            plugins: {
                                ...commonPluginOptions.plugins,
                                legend: {
                                    display: false
                                }
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
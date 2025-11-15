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
            // Separate flag from gradient text to prevent overlay
            updateElement('#topRegion', `<span style="filter: none; -webkit-text-fill-color: initial;">${flag}</span> ${countryName}`, { method: 'innerHTML', trustedHTML: true });
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

            // Remove only an existing menu if one is already open (single instance policy)
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
            `;

            document.body.appendChild(menu);
            computePosition();

            const onResize = () => computePosition();
            // Only recompute on resize; fixed positioning keeps alignment on normal scroll
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

            menu.appendChild(createMenuButton('📊 Export as PNG', () => {
              exportChartAsImage(canvas, chartTitle, 'png');
            }));
            menu.appendChild(createMenuButton('💾 Export Data as JSON', () => {
              exportChartData(canvas, chartTitle);
            }, true));

            // Focus management and global listeners
            setTimeout(() => {
              menu.focus();
              document.addEventListener('click', handleOutsideClick, true);
              document.addEventListener('keydown', onKeyDown);
            }, 0);
        });
    });

    // Helper function to export chart as image
    // Helper function to export chart as image
    function exportChartAsImage(canvas, title, format) {
        try {
            const filename = `${title.toLowerCase().replace(/\s+/g, '-')}-${Date.now()}.png`;
            if (format === 'png') {
                canvas.toBlob(blob => {
                    if (!blob) {
                        console.error('Canvas export failed: blob is null (possibly tainted canvas or insufficient permissions).');
                        alert('Failed to export chart image due to browser security restrictions. The chart may contain external resources that prevent export.');
                        return;
                    }
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = filename;
                    try {
                        document.body.appendChild(link);
                        link.click();
                    } catch (clickError) {
                        console.error('Failed to trigger download:', clickError);
                        alert('Failed to download chart. Please try again.');
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
            alert('Failed to export chart. Please try again.');
        }
    }

    // Separate helper function to export chart data as JSON
    function exportChartData(canvas, title) {
        try {
            const ctx = canvas.getContext('2d');
            const chartInstance = ctx && (canvas.__chart__ || canvas.chart || ctx.canvas.chart);
            if (!chartInstance || !chartInstance.data) {
                console.error('Chart instance not found');
                alert('Unable to export chart data. Chart instance not found.');
                return;
            }
            const data = chartInstance.data;
            const safeLabels = Array.isArray(data.labels) ? data.labels.slice() : [];
            const safeDatasets = Array.isArray(data.datasets)
                ? data.datasets.map(ds => ({
                    label: typeof ds.label === 'string' ? ds.label : '',
                    data: Array.isArray(ds.data) ? ds.data.slice() : [],
                    backgroundColor: ds.backgroundColor ?? null,
                    borderColor: ds.borderColor ?? null,
                    borderWidth: typeof ds.borderWidth === 'number' ? ds.borderWidth : undefined
                }))
                : [];
            const exportData = {
                title,
                exported_at: new Date().toISOString(),
                labels: safeLabels,
                datasets: safeDatasets
            };
            let jsonString = '';
            try {
                jsonString = JSON.stringify(exportData, null, 2);
            } catch (serr) {
                console.error('Serialization failed:', serr);
                alert('Failed to serialize chart data for export.');
                return;
            }
            const blob = new Blob([jsonString], { type: 'application/json' });
            const filename = `${title.toLowerCase().replace(/\s+/g, '-')}-data-${Date.now()}.json`;
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = filename;
            try {
                document.body.appendChild(link);
                link.click();
            } catch (clickError) {
                console.error('Failed to trigger download:', clickError);
                alert('Failed to download data. Please try again.');
            } finally {
                setTimeout(() => {
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                }, 100);
            }
        } catch (error) {
            console.error('Error exporting data:', error);
            alert('Failed to export data. Please try again.');
        }
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
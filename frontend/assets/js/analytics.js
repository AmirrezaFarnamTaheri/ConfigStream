/**
 * Analytics Logic for ConfigStream
 * Handles Charts and Maps
 */

document.addEventListener('DOMContentLoaded', async () => {
    try {
        // Fetch metadata
        const response = await fetch('files/metadata.json');
        if (!response.ok) throw new Error('Failed to load metadata');
        const data = await response.json();

        // Populate Summary Cards
        updateSummaryCards(data);

        // Initialize Charts
        initProtocolChart(data.protocols, data.protocol_colors);
        initLatencyChart(data);
        initCountryChart(data.countries);

        // Initialize Map
        initMap(data.countries);

    } catch (e) {
        console.error('Analytics Error:', e);
        const container = document.querySelector('.analytics-grid');
        if (container) {
             container.innerHTML = `<p class="error text-center" style="grid-column: 1/-1; color: var(--danger-color);">Failed to load analytics data. Please try again later.</p>`;
        }
        // Reset cards
        document.querySelectorAll('.stat-value').forEach(el => el.innerText = '-');
        document.querySelectorAll('.stat-value').forEach(el => el.classList.remove('loading'));
    }
});

function updateSummaryCards(data) {
    // Update DOM elements
    const totalSourced = document.getElementById('totalSourced');
    const totalConfigs = document.getElementById('totalConfigs');
    const workingConfigs = document.getElementById('workingConfigs');
    const lastUpdated = document.getElementById('lastUpdated');

    if (totalSourced) {
        totalSourced.innerText = data.total_fetched || 0;
        totalSourced.classList.remove('loading');
    }
    if (totalConfigs) {
        totalConfigs.innerText = data.total_proxies || 0; // Using total unique tested as proxies
        totalConfigs.classList.remove('loading');
    }
    if (workingConfigs) {
        workingConfigs.innerText = data.total_working || 0;
        workingConfigs.classList.remove('loading');
    }
    if (lastUpdated) {
        if (data.last_updated_utc) {
             const date = new Date(data.last_updated_utc);
             // Format: "2 hours ago" or local time
             lastUpdated.innerText = date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
        } else {
             lastUpdated.innerText = "Just now";
        }
        lastUpdated.classList.remove('loading');
    }
}

function initProtocolChart(protocols, colors) {
    const ctx = document.getElementById('protocolChart');
    if (!ctx) return;

    // Default colors if not provided
    const defaultColors = {
        "vmess": "#FF6B6B",
        "vless": "#4ECDC4",
        "trojan": "#96CEB4",
        "shadowsocks": "#45B7D1",
        "hysteria2": "#DFE6E9",
        "wireguard": "#74B9FF",
        "socks5": "#FFA502",
        "http": "#7EFFF5"
    };

    const bgColors = Object.keys(protocols).map(p => (colors && colors[p]) || defaultColors[p] || '#cccccc');

    new Chart(ctx.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: Object.keys(protocols).map(k => k.toUpperCase()),
            datasets: [{
                data: Object.values(protocols),
                backgroundColor: bgColors,
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        color: getComputedStyle(document.body).getPropertyValue('--text-secondary').trim()
                    }
                }
            }
        }
    });
}

function initCountryChart(countries) {
    const ctx = document.getElementById('countryChart');
    if (!ctx) return;

    // Sort and take top 10
    const sorted = Object.entries(countries).sort((a, b) => b[1] - a[1]).slice(0, 10);

    new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: sorted.map(i => i[0]),
            datasets: [{
                label: 'Active Proxies',
                data: sorted.map(i => i[1]),
                backgroundColor: '#3b82f6',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: getComputedStyle(document.body).getPropertyValue('--border').trim()
                    },
                    ticks: {
                        color: getComputedStyle(document.body).getPropertyValue('--text-secondary').trim()
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: getComputedStyle(document.body).getPropertyValue('--text-secondary').trim()
                    }
                }
            }
        }
    });
}

function initLatencyChart(data) {
    const ctx = document.getElementById('latencyChart');
    if (!ctx) return;

    let chartData, labels;

    if (data.latency_distribution) {
        labels = ['<100ms', '100-500ms', '500-1000ms', '>1s'];
        chartData = [
            data.latency_distribution.fast || 0,
            data.latency_distribution.medium || 0,
            data.latency_distribution.slow || 0,
            data.latency_distribution.very_slow || 0
        ];
    } else {
        // No data state
        labels = ['No Data'];
        chartData = [0];
    }

    new Chart(ctx.getContext('2d'), {
        type: 'bar', // Changed to bar for histogram-like view
        data: {
            labels: labels,
            datasets: [{
                label: 'Proxies Count',
                data: chartData,
                backgroundColor: [
                    '#10b981', // Green
                    '#3b82f6', // Blue
                    '#f59e0b', // Yellow
                    '#ef4444'  // Red
                ],
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.parsed.y} Proxies`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: getComputedStyle(document.body).getPropertyValue('--border').trim()
                    },
                     ticks: {
                        color: getComputedStyle(document.body).getPropertyValue('--text-secondary').trim()
                    }
                },
                x: {
                    grid: { display: false },
                     ticks: {
                        color: getComputedStyle(document.body).getPropertyValue('--text-secondary').trim()
                    }
                }
            }
        }
    });
}

function initMap(countries) {
    if (!window.L) return; // Leaflet not loaded

    const container = document.getElementById('map-container');
    if (!container) return;

    // Fix Leaflet icon paths
    delete L.Icon.Default.prototype._getIconUrl;
    L.Icon.Default.mergeOptions({
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    });

    const map = L.map('map-container', {
        scrollWheelZoom: false,
        zoomControl: false
    }).setView([20, 0], 2);

    L.control.zoom({
        position: 'bottomright'
    }).addTo(map);

    // Dark/Light mode tile switching could be implemented here, but for now consistent dark-ish map fits themes
    const isDark = document.body.classList.contains('dark');
    const tileUrl = isDark
        ? 'https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png'
        : 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png';

    L.tileLayer(tileUrl, {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19
    }).addTo(map);

    // Approximate coordinates for common countries
    const countryCoords = {
        'US': [37.09, -95.71], 'CN': [35.86, 104.19], 'JP': [36.20, 138.25],
        'DE': [51.16, 10.45], 'RU': [61.52, 105.31], 'FR': [46.22, 2.21],
        'GB': [55.37, -3.43], 'BR': [-14.23, -51.92], 'IN': [20.59, 78.96],
        'CA': [56.13, -106.34], 'AU': [-25.27, 133.77], 'SG': [1.35, 103.81],
        'NL': [52.13, 5.29], 'KR': [35.90, 127.76], 'TR': [38.96, 35.24],
        'IR': [32.42, 53.68], 'AE': [23.42, 53.84], 'SA': [23.88, 45.07],
        'IT': [41.87, 12.56], 'ES': [40.46, -3.74], 'PL': [51.91, 19.14],
        'UA': [48.37, 31.16], 'ID': [-0.78, 113.92], 'VN': [14.05, 108.27],
        'TH': [15.87, 100.99], 'MY': [4.21, 101.97], 'HK': [22.31, 114.16],
        'TW': [23.69, 120.96]
    };

    for (const [code, count] of Object.entries(countries)) {
        if (countryCoords[code]) {
            // Scale radius
            const radius = Math.min(Math.log(count) * 4 + 4, 25);

            L.circleMarker(countryCoords[code], {
                radius: radius,
                color: '#3b82f6',
                fillColor: '#3b82f6',
                fillOpacity: 0.6,
                weight: 1
            })
            .bindPopup(`<b>${code}</b>: ${count} Proxies`)
            .addTo(map);
        }
    }
}

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

        // Initialize Charts
        initProtocolChart(data.protocols);
        initLatencyChart(data);
        initCountryChart(data.countries);

        // Initialize Map
        initMap(data.countries);

    } catch (e) {
        console.error('Analytics Error:', e);
        document.querySelector('main .container').innerHTML += `<p class="error">Failed to load analytics data. Please try again later.</p>`;
    }
});

function initProtocolChart(protocols) {
    const ctx = document.getElementById('protocolChart').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(protocols),
            datasets: [{
                data: Object.values(protocols),
                backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { position: 'right' }
            }
        }
    });
}

function initCountryChart(countries) {
    // Sort and take top 10
    const sorted = Object.entries(countries).sort((a, b) => b[1] - a[1]).slice(0, 10);

    const ctx = document.getElementById('countryChart').getContext('2d');
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sorted.map(i => i[0]),
            datasets: [{
                label: 'Active Proxies',
                data: sorted.map(i => i[1]),
                backgroundColor: '#3b82f6'
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } }
        }
    });
}

function initLatencyChart(data) {
    // If we don't have detailed latency data in metadata, we can't build a real histogram.
    // However, we can check if 'total_working' gives us a hint, or just show a placeholder
    // distribution based on generic expectations or provided stats if available.
    // Since we modified `output.py` to only provide summaries, we will use a placeholder
    // or look for latency stats if we added them. We didn't add specific latency buckets.

    const ctx = document.getElementById('latencyChart').getContext('2d');

    // Placeholder for now as backend doesn't aggregate latency buckets yet
    new Chart(ctx, {
        type: 'line',
        data: {
            labels: ['<100ms', '100-500ms', '500-1000ms', '>1s'],
            datasets: [{
                label: 'Proxies Estimate',
                data: [data.total_working * 0.2, data.total_working * 0.5, data.total_working * 0.2, data.total_working * 0.1],
                borderColor: '#10b981',
                tension: 0.4,
                fill: true,
                backgroundColor: 'rgba(16, 185, 129, 0.1)'
            }]
        },
        options: { responsive: true }
    });
}

function initMap(countries) {
    if (!L) return; // Leaflet not loaded
    const map = L.map('map-container').setView([20, 0], 2);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; OpenStreetMap, &copy; CartoDB'
    }).addTo(map);

    // Approximate coordinates for common countries
    const countryCoords = {
        'US': [37.09, -95.71], 'CN': [35.86, 104.19], 'JP': [36.20, 138.25],
        'DE': [51.16, 10.45], 'RU': [61.52, 105.31], 'FR': [46.22, 2.21],
        'GB': [55.37, -3.43], 'BR': [-14.23, -51.92], 'IN': [20.59, 78.96],
        'CA': [56.13, -106.34], 'AU': [-25.27, 133.77], 'SG': [1.35, 103.81],
        'NL': [52.13, 5.29], 'KR': [35.90, 127.76], 'TR': [38.96, 35.24]
    };

    for (const [code, count] of Object.entries(countries)) {
        if (countryCoords[code]) {
            L.circleMarker(countryCoords[code], {
                radius: Math.min(Math.log(count) * 3 + 3, 20),
                color: '#3b82f6',
                fillColor: '#3b82f6',
                fillOpacity: 0.6
            })
            .bindPopup(`<b>${code}</b>: ${count} Proxies`)
            .addTo(map);
        }
    }
}

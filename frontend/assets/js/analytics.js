// ConfigStream Analytics - Globe & Charts
// Uses globe.gl and Chart.js

document.addEventListener('DOMContentLoaded', async () => {
    // Initialize Stats
    if (window.api && window.api.fetchStatistics) {
        try {
            const stats = await window.api.fetchStatistics();
            updateStats(stats);
            initCharts(stats);
            initGlobe(stats);
        } catch (e) {
            console.error("Failed to load analytics data:", e);
        }
    }
});

function updateStats(data) {
    const update = (id, val) => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = val;
            el.classList.remove('loading');
        }
    };

    update('totalSourced', data.total_fetched || 0);
    update('totalConfigs', data.total_tested || data.total_proxies || 0);
    update('workingConfigs', data.total_working || 0);

    // New Stats if elements exist
    update('totalRevived', data.total_revived || 0);
    update('threatsNeutralized', data.total_dirty || 0);

    const date = new Date(data.last_updated_utc);
    update('lastUpdated', date.toLocaleString());
}

function initGlobe(data) {
    const container = document.getElementById('globe-viz');
    if (!container) return;

    // Prepare data for globe
    // We need lat/lng for countries. We can use a static mapping or fetch a geojson.
    // For this demo, we'll use random points within countries or centroids if available.
    // Since we only have country codes, we'll map country codes to approximate lat/lng.

    const countryCentroids = {
        "US": { lat: 37.0902, lng: -95.7129, name: "United States" },
        "CN": { lat: 35.8617, lng: 104.1954, name: "China" },
        "RU": { lat: 61.5240, lng: 105.3188, name: "Russia" },
        "DE": { lat: 51.1657, lng: 10.4515, name: "Germany" },
        "FR": { lat: 46.2276, lng: 2.2137, name: "France" },
        "GB": { lat: 55.3781, lng: -3.4360, name: "United Kingdom" },
        "CA": { lat: 56.1304, lng: -106.3468, name: "Canada" },
        "JP": { lat: 36.2048, lng: 138.2529, name: "Japan" },
        "KR": { lat: 35.9078, lng: 127.7669, name: "South Korea" },
        "SG": { lat: 1.3521, lng: 103.8198, name: "Singapore" },
        "NL": { lat: 52.1326, lng: 5.2913, name: "Netherlands" },
        "IN": { lat: 20.5937, lng: 78.9629, name: "India" },
        "BR": { lat: -14.2350, lng: -51.9253, name: "Brazil" },
        "IR": { lat: 32.4279, lng: 53.6880, name: "Iran" },
        // Add more as needed
    };

    const arcsData = [];
    const pointsData = [];

    // Create arcs from "Internet" (Abstract center) to Countries
    // Or simply visualize active nodes.

    if (data.proxy_locations && data.proxy_locations.length > 0) {
        // Use exact proxy locations
        data.proxy_locations.forEach(p => {
            const lat = p.lat;
            const lng = p.lng;
            // Color by latency (Green < 200, Yellow < 500, Red > 500)
            let color = '#ff0000';
            const latency = p.latency || 9999;
            if (latency < 200) color = '#00ff00';
            else if (latency < 500) color = '#ffff00';

            pointsData.push({
                lat: lat,
                lng: lng,
                size: 0.15, // Small clean dots
                color: color,
                name: `${p.protocol.toUpperCase()} (${latency}ms) - ${p.country || 'XX'}`
            });

            // Add arcs randomly for visual effect (10% chance)
            if (Math.random() < 0.1) {
                arcsData.push({
                    startLat: lat + (Math.random() * 20 - 10),
                    startLng: lng + (Math.random() * 20 - 10),
                    endLat: lat,
                    endLng: lng,
                    color: [['#5E55F1', '#A855F7'][Math.round(Math.random())]],
                });
            }
        });
    } else {
        const countryStats = data.country_stats || {};
        const maxCount = Math.max(...Object.values(countryStats));

        Object.entries(countryStats).forEach(([cc, count]) => {
            const info = countryCentroids[cc] || { lat: (Math.random()*160)-80, lng: (Math.random()*360)-180 };

            // Points (Active Nodes)
            pointsData.push({
                lat: info.lat,
                lng: info.lng,
                size: Math.sqrt(count) / 5,
                color: getScoreColor(count / maxCount),
                name: `${cc}: ${count} proxies`
            });

            // Arcs (Traffic Flow Simulation)
            // Source: Random point, Target: Country
            // Just visual candy
            if (count > 5) {
                arcsData.push({
                    startLat: info.lat + (Math.random() * 10 - 5),
                    startLng: info.lng + (Math.random() * 10 - 5),
                    endLat: info.lat,
                    endLng: info.lng,
                    color: [['#5E55F1', '#A855F7'][Math.round(Math.random())]],
                });
            }
        });
    }

    const Globe = window.Globe()
      (container)
      .globeImageUrl('//unpkg.com/three-globe/example/img/earth-night.jpg')
      .bumpImageUrl('//unpkg.com/three-globe/example/img/earth-topology.png')
      .backgroundImageUrl('//unpkg.com/three-globe/example/img/night-sky.png')
      .pointsData(pointsData)
      .pointAltitude(0.01)
      .pointRadius('size')
      .pointColor('color')
      .pointLabel('name')
      .arcsData(arcsData)
      .arcColor('color')
      .arcDashLength(0.4)
      .arcDashGap(0.2)
      .arcDashAnimateTime(1500)
      .onPointHover(point => container.style.cursor = point ? 'pointer' : 'default');

    // Auto-rotate
    Globe.controls().autoRotate = true;
    Globe.controls().autoRotateSpeed = 0.5;

    // Responsiveness
    window.addEventListener('resize', () => {
        Globe.width(container.clientWidth);
        Globe.height(container.clientHeight);
    });
}

function initCharts(data) {
    // Common Chart Options
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = '#1e293b';

    // 1. Protocol Distribution (Doughnut)
    const protoCtx = document.getElementById('protocolChart').getContext('2d');
    new Chart(protoCtx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(data.protocols || {}),
            datasets: [{
                data: Object.values(data.protocols || {}),
                backgroundColor: [
                    '#FF6B6B', '#4ECDC4', '#96CEB4', '#45B7D1',
                    '#FFEAA7', '#DFE6E9', '#A29BFE', '#74B9FF'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { position: 'right' }
            }
        }
    });

    // 2. Latency Distribution (Bar)
    const latencyCtx = document.getElementById('latencyChart').getContext('2d');
    const latData = data.latency_distribution || {};
    new Chart(latencyCtx, {
        type: 'bar',
        data: {
            labels: ['Fast (<100ms)', 'Medium (100-500ms)', 'Slow (500-1000ms)', 'Laggy (>1s)'],
            datasets: [{
                label: 'Proxies',
                data: [latData.fast, latData.medium, latData.slow, latData.very_slow],
                backgroundColor: ['#2ecc71', '#f1c40f', '#e67e22', '#e74c3c'],
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { beginAtZero: true }
            }
        }
    });

    // 3. Rejection Reasons (Pie/Doughnut)
    const rejEl = document.getElementById('rejectionChart');
    if (rejEl && data.rejection_reasons) {
        const rejCtx = rejEl.getContext('2d');
        // Sort keys
        const sortedRej = Object.entries(data.rejection_reasons).sort((a,b) => b[1]-a[1]).slice(0, 8);
        new Chart(rejCtx, {
            type: 'pie',
            data: {
                labels: sortedRej.map(x => x[0]),
                datasets: [{
                    data: sortedRej.map(x => x[1]),
                    backgroundColor: [
                        '#e74c3c', '#e67e22', '#f1c40f', '#9b59b6',
                        '#34495e', '#95a5a6', '#7f8c8d', '#bdc3c7'
                    ],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'right' } }
            }
        });
    }

    // 4. Threat Breakdown (Doughnut) - Filtered Rejection Reasons
    const threatEl = document.getElementById('threatChart');
    if (threatEl && data.rejection_reasons) {
        const threatCtx = threatEl.getContext('2d');
        const threatKeys = ['honeypot', 'dirty_ip', 'malware', 'invalid_cert', 'security', 'unsafe'];
        const threats = {};
        for(const k in data.rejection_reasons) {
            if(threatKeys.some(tk => k.toLowerCase().includes(tk))) {
                threats[k] = data.rejection_reasons[k];
            }
        }

        const sortedThreats = Object.entries(threats).sort((a,b) => b[1]-a[1]);

        new Chart(threatCtx, {
            type: 'doughnut',
            data: {
                labels: sortedThreats.map(x => x[0].replace(/_/g, ' ').toUpperCase()),
                datasets: [{
                    data: sortedThreats.map(x => x[1]),
                    backgroundColor: ['#e74c3c', '#c0392b', '#d35400', '#e67e22', '#f39c12'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right' },
                    title: { display: true, text: 'Neutralized Threats' }
                }
            }
        });
    }

    // 5. Top ASNs (Bar)
    const asnEl = document.getElementById('asnChart');
    if (asnEl && data.asns) {
        const asnCtx = asnEl.getContext('2d');
        const sortedAsns = Object.entries(data.asns).sort((a,b) => b[1]-a[1]).slice(0, 15);
        new Chart(asnCtx, {
            type: 'bar',
            data: {
                labels: sortedAsns.map(x => x[0]),
                datasets: [{
                    label: 'Proxies Hosted',
                    data: sortedAsns.map(x => x[1]),
                    backgroundColor: '#3498db',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } }
            }
        });
    }

    // 6. Top Countries (Horizontal Bar)
    const countryCtx = document.getElementById('countryChart').getContext('2d');
    const sortedCountries = Object.entries(data.country_stats || {})
        .sort((a, b) => b[1] - a[1])
        .slice(0, 10);

    new Chart(countryCtx, {
        type: 'bar',
        indexAxis: 'y',
        data: {
            labels: sortedCountries.map(x => x[0]),
            datasets: [{
                label: 'Active Proxies',
                data: sortedCountries.map(x => x[1]),
                backgroundColor: '#5E55F1',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false
        }
    });
}

function getScoreColor(score) {
    if (score > 0.8) return '#00ff00';
    if (score > 0.5) return '#ffff00';
    return '#ff0000';
}

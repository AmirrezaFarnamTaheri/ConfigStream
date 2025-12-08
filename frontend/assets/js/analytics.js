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

    // Helper function to format numbers with locale support
    const formatNum = (num) => window.i18n && window.i18n.formatNumber ? window.i18n.formatNumber(num) : num;

    // Fix: Use correct field with fallbacks
    // total_sourced = raw lines fetched from sources before dedup
    // total_fetched = same as above (legacy name)
    // total_proxies = after dedup, the actual tested count
    const totalSourced = data.total_sourced || data.total_fetched || data.fetched_lines || 0;
    update('totalSourced', formatNum(totalSourced));

    update('totalConfigs', formatNum(data.total_tested || data.total_proxies || 0));
    update('workingConfigs', formatNum(data.total_working || 0));

    // New Stats if elements exist
    const totalWorking = data.total_working || 0;
    const totalRevived = data.total_revived || 0;
    // Always calculate clean from working - revived (don't trust backend total_clean)
    const totalClean = Math.max(0, totalWorking - totalRevived);

    update('totalClean', formatNum(totalClean));
    update('totalRevived', formatNum(totalRevived));
    update('threatsNeutralized', formatNum(data.total_dirty || 0));

    const date = new Date(data.last_updated_utc);
    update('lastUpdated', date.toLocaleString());
}

function initGlobe(data) {
    const container = document.getElementById('globe-viz');
    if (!container) return;

    // Prepare data for globe
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
        "TR": { lat: 38.9637, lng: 35.2433, name: "Turkey" },
        "UA": { lat: 48.3794, lng: 31.1656, name: "Ukraine" },
        "HK": { lat: 22.3193, lng: 114.1694, name: "Hong Kong" },
    };

    const arcsData = [];
    const pointsData = [];

    if (data.proxy_locations && data.proxy_locations.length > 0) {
        // Use exact proxy locations if available in metadata
        data.proxy_locations.forEach(p => {
            const lat = p.lat;
            const lng = p.lng;
            let color = '#ff0000';
            const latency = p.latency || 9999;
            if (latency < 200) color = '#00ff00';
            else if (latency < 500) color = '#ffff00';

            pointsData.push({
                lat: lat,
                lng: lng,
                size: 0.15,
                color: color,
                name: `${p.protocol.toUpperCase()} (${latency}ms) - ${p.country || 'XX'}`
            });

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

            pointsData.push({
                lat: info.lat,
                lng: info.lng,
                size: Math.sqrt(count) / 5,
                color: getScoreColor(count / maxCount),
                name: `${cc}: ${count} proxies`
            });

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

    // Detect current theme for texture selection
    const isDarkMode = document.body.classList.contains('dark');

    // Use different textures based on theme
    const globeTexture = isDarkMode
        ? '//unpkg.com/three-globe/example/img/earth-night.jpg'
        : '//unpkg.com/three-globe/example/img/earth-blue-marble.jpg';

    const backgroundTexture = isDarkMode
        ? '//unpkg.com/three-globe/example/img/night-sky.png'
        : 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg"><rect fill="%23f0f4f8" width="100%" height="100%"/></svg>';

    const Globe = window.Globe()
      (container)
      .globeImageUrl(globeTexture)
      .bumpImageUrl('//unpkg.com/three-globe/example/img/earth-topology.png')
      .backgroundImageUrl(backgroundTexture)
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

    // Configure controls for better interactivity
    const controls = Globe.controls();
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.35; // Slower, more elegant rotation
    controls.enableZoom = false; // Disable zoom by default to prevent scroll conflicts
    controls.minDistance = 180; // Minimum zoom distance
    controls.maxDistance = 500; // Maximum zoom distance
    controls.enableDamping = true; // Smooth camera movements
    controls.dampingFactor = 0.05;

    // Auto-rotation cooldown logic
    let rotationCooldownTimer = null;
    const COOLDOWN_DURATION = 4000; // Resume rotation after 4 seconds of inactivity
    let zoomActive = false;

    // Pause rotation on user interaction, resume after cooldown
    const pauseRotation = () => {
        controls.autoRotate = false;

        // Clear existing timer
        if (rotationCooldownTimer) {
            clearTimeout(rotationCooldownTimer);
        }

        // Set new cooldown timer
        rotationCooldownTimer = setTimeout(() => {
            controls.autoRotate = true;
        }, COOLDOWN_DURATION);
    };

    // Activate zoom on container click, deactivate after cooldown
    const activateZoom = () => {
        if (!zoomActive) {
            zoomActive = true;
            controls.enableZoom = true;
            container.classList.add('zoom-active');
            container.classList.remove('zoom-inactive');

            // Auto-deactivate zoom after inactivity
            setTimeout(() => {
                zoomActive = false;
                controls.enableZoom = false;
                container.classList.remove('zoom-active');
                container.classList.add('zoom-inactive');
            }, 8000); // Deactivate after 8 seconds
        }
    };

    // Attach interaction listeners
    container.addEventListener('click', activateZoom);
    container.addEventListener('mousedown', pauseRotation);
    container.addEventListener('touchstart', pauseRotation);

    // Set initial state
    container.classList.add('zoom-inactive');

    // Center globe on initial load with better positioning
    // Point of View: Centered on prime meridian, slight tilt
    Globe.pointOfView({ lat: 20, lng: 0, altitude: 2.5 }, 0);

    // Handle window resize
    window.addEventListener('resize', () => {
        Globe.width(container.clientWidth);
        Globe.height(container.clientHeight);
    });

    // Listen for theme changes and update globe textures
    window.addEventListener('themechanged', (e) => {
        const newIsDark = e.detail.theme === 'dark';
        const newGlobeTexture = newIsDark
            ? '//unpkg.com/three-globe/example/img/earth-night.jpg'
            : '//unpkg.com/three-globe/example/img/earth-blue-marble.jpg';
        const newBackgroundTexture = newIsDark
            ? '//unpkg.com/three-globe/example/img/night-sky.png'
            : 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg"><rect fill="%23f0f4f8" width="100%" height="100%"/></svg>';

        Globe.globeImageUrl(newGlobeTexture);
        Globe.backgroundImageUrl(newBackgroundTexture);
    });

    // Store globe instance globally for debugging/external control
    window.globeInstance = Globe;
}

function initCharts(data) {
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
            plugins: { legend: { position: 'right' } }
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
            scales: { y: { beginAtZero: true } }
        }
    });

    // 3. Rejection Reasons (Pie)
    const rejEl = document.getElementById('rejectionChart');
    if (rejEl && data.rejection_reasons) {
        const rejCtx = rejEl.getContext('2d');
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

    // 4. Threat Breakdown - Actual Security Threats Only (Doughnut)
    const threatEl = document.getElementById('threatChart');
    if (threatEl) {
        const threatCtx = threatEl.getContext('2d');

        // Extract ALL threat categories from rejection_reasons
        // These map to backend SECURITY_CATEGORIES
        const threats = {
            // Critical Security Threats
            blockedIPs: 0,        // address_blocked (FireHol blocklist - dirty IPs)
            honeypots: 0,         // honeypot_suspected
            suspiciousNodes: 0,   // address_suspicious
            privateIPs: 0,        // address_private_ip

            // Configuration Issues
            dangerousPorts: 0,    // port_security
            invalidProtocols: 0,  // protocol_invalid
            malformedConfigs: 0,  // suspicious_config_malformed (null bytes)
            oversizedConfigs: 0,  // suspicious_config_format (too long)
            invalidUUIDs: 0,      // config_uuid_invalid

            // Filtering (not threats but rejections)
            duplicates: 0,        // duplicate
            invalidConfigs: 0,    // invalid (parsing failures)
        };

        if (data.rejection_reasons) {
            const reasons = data.rejection_reasons;

            // Map backend category names to threat types
            threats.blockedIPs = reasons.address_blocked || 0;
            threats.honeypots = reasons.honeypot_suspected || 0;
            threats.suspiciousNodes = reasons.address_suspicious || 0;
            threats.privateIPs = reasons.address_private_ip || 0;
            threats.dangerousPorts = reasons.port_security || 0;
            threats.invalidProtocols = reasons.protocol_invalid || 0;
            threats.malformedConfigs = reasons.suspicious_config_malformed || 0;
            threats.oversizedConfigs = reasons.suspicious_config_format || 0;
            threats.invalidUUIDs = reasons.config_uuid_invalid || 0;
            threats.duplicates = reasons.duplicate || 0;
            threats.invalidConfigs = reasons.invalid || 0;
        }

        // Build dynamic dataset - only show categories with data
        const dataset = [];
        const labels = [];
        const colors = [];

        // Critical Threats (Red shades)
        if (threats.blockedIPs > 0) {
            dataset.push(threats.blockedIPs);
            labels.push('Blocked IPs (FireHol)');
            colors.push('#e74c3c');
        }
        if (threats.honeypots > 0) {
            dataset.push(threats.honeypots);
            labels.push('Honeypot Traps');
            colors.push('#c0392b');
        }
        if (threats.suspiciousNodes > 0) {
            dataset.push(threats.suspiciousNodes);
            labels.push('Suspicious Domains');
            colors.push('#e67e22');
        }

        // Security Issues (Orange/Purple shades)
        if (threats.privateIPs > 0) {
            dataset.push(threats.privateIPs);
            labels.push('Private/Loopback IPs');
            colors.push('#f39c12');
        }
        if (threats.dangerousPorts > 0) {
            dataset.push(threats.dangerousPorts);
            labels.push('Dangerous Ports');
            colors.push('#d35400');
        }

        // Config Issues (Purple shades)
        if (threats.malformedConfigs > 0) {
            dataset.push(threats.malformedConfigs);
            labels.push('Malformed Configs');
            colors.push('#8e44ad');
        }
        if (threats.invalidProtocols > 0) {
            dataset.push(threats.invalidProtocols);
            labels.push('Invalid Protocols');
            colors.push('#9b59b6');
        }
        if (threats.invalidUUIDs > 0) {
            dataset.push(threats.invalidUUIDs);
            labels.push('Invalid UUIDs');
            colors.push('#a569bd');
        }
        if (threats.oversizedConfigs > 0) {
            dataset.push(threats.oversizedConfigs);
            labels.push('Oversized Configs');
            colors.push('#bb8fce');
        }

        // Non-Threats (Gray shades) - just filtering
        if (threats.duplicates > 0) {
            dataset.push(threats.duplicates);
            labels.push('Duplicates');
            colors.push('#95a5a6');
        }
        if (threats.invalidConfigs > 0) {
            dataset.push(threats.invalidConfigs);
            labels.push('Parse Failures');
            colors.push('#7f8c8d');
        }

        // Fallback if no data
        if (dataset.length === 0) {
            dataset.push(1);
            labels.push('No Threats Detected');
            colors.push('#2ecc71');
        }

        new Chart(threatCtx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: dataset,
                    backgroundColor: colors,
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { position: 'right' },
                    title: { display: true, text: 'Security Threats & Rejections' }
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

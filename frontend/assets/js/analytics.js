import logger from './utils/logger.js';

// ConfigStream Analytics - Globe & Charts
// Uses globe.gl and Chart.js

document.addEventListener('DOMContentLoaded', async () => {
    // Initialize Stats - with fallback for when API isn't available
    let stats = null;
    let evasionTrend = null;

    // Try multiple data sources - metadata.json is single source of truth
    try {
        if (window.api && window.api.fetchStatistics) {
            stats = await window.api.fetchStatistics();
        } else {
            // Fallback: Try direct fetch from metadata.json (unified stats file)
            const response = await fetch('metadata.json?cb=' + Date.now());
            if (response.ok) {
                stats = await response.json();
            }
        }

        // Fetch evasion trend data
        try {
            const evasionResponse = await fetch('data/evasion_trend.json?cb=' + Date.now());
            if (evasionResponse.ok) {
                evasionTrend = await evasionResponse.json();
            }
        } catch (e) {
            logger.warn("Failed to load evasion trend data:", e);
        }

        if (stats) {
            updateStats(stats);
            initCharts(stats, evasionTrend);
            initGlobe(stats);
        } else {
            logger.warn("No analytics data available");
            // Show empty state or placeholder
            showEmptyState();
        }
    } catch (e) {
        logger.error("Failed to load analytics data:", e);
        showEmptyState();
    }
});

function showEmptyState() {
    const container = document.getElementById('globe-viz');
    if (container) {
        container.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-secondary); font-size: 1.1rem;">Loading analytics data...</div>';
    }
}

// F6 Fix: Centralized Color Logic
function generateColor(label, index) {
    // Consistent hashing color generation
    let hash = 0;
    const str = label.toString();
    for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
    }
    const hue = Math.abs(hash % 360);
    return `hsl(${hue}, 70%, 60%)`;
}

function updateStats(data) {
    const update = (id, val) => {
        const el = document.getElementById(id);
        if (el) {
            el.textContent = val;
            el.classList.remove('loading');
        }
    };

    // Helper function to format numbers with locale support
    const formatNum = (num) => {
        if (num === undefined || num === null) return 'N/A';
        if (window.i18n && window.i18n.formatNumber) {
            return window.i18n.formatNumber(num);
        }
        return num.toLocaleString();
    };

    // Use canonical fields with comprehensive legacy fallbacks (consistent with main.js)
    // Use canonical backend field names only
    const totalSourced = data.total_lines_sourced;
    update('totalSourced', formatNum(totalSourced));

    const totalConfigs = data.total_unique_candidates;
    update('totalConfigs', formatNum(totalConfigs));

    const workingCount = data.total_valid_proxies;
    update('workingConfigs', formatNum(workingCount));

    const revivedWarp = data.revived_warp || 0;
    const revivedVwarp = data.revived_vwarp || 0;
    const totalRevived = data.total_revived ?? (revivedWarp + revivedVwarp);

    let cleanVal = data.total_clean;
    if (cleanVal === undefined && workingCount !== undefined && totalRevived !== undefined) {
        cleanVal = Math.max(0, workingCount - totalRevived);
    }

    update('totalClean', formatNum(cleanVal));
    update('totalRevived', formatNum(totalRevived));
    update('revivedWarp', formatNum(revivedWarp));
    update('revivedVwarp', formatNum(revivedVwarp));
    update('threatsBlocked', formatNum(data.total_dirty));

    // Smart Chains
    const smartChains = data.total_smart_chains;
    update('smartChains', formatNum(smartChains));

    // Vwarp Win Rate
    const vwarpWinRate = data.vwarp_win_rate;
    const washingEnabled = data.washing_enabled;
    const winRateDisplay = (washingEnabled !== false && vwarpWinRate !== undefined)
        ? `${Math.round(vwarpWinRate)}%` : 'N/A';
    update('vwarpWinRate', winRateDisplay);

    // Update Frequency
    const updateFreq = data.update_interval_hours || 6;
    update('updateFrequency', `${updateFreq} hrs`);

    // Update timestamp if available
    if (data.last_updated_utc) {
        const date = new Date(data.last_updated_utc);
        update('lastUpdated', date.toLocaleString());
    }
}

function initGlobe(data) {
    const container = document.getElementById('globe-viz');
    if (!container) return;

    // Show loading indicator
    container.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-secondary); font-size: 1.1rem;"><div class="spinner" style="border: 3px solid var(--border); border-top-color: var(--primary-color); border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin-right: 10px;"></div>Loading globe...</div>';

    // Wait for Globe.gl and THREE.js libraries to be available (retry mechanism)
    // Removed polling loop. Rely on standard load event.
    if (window.Globe && window.THREE) {
        _initGlobeInternal(data, container);
    } else {
        window.addEventListener('load', () => {
             if (window.Globe && window.THREE) _initGlobeInternal(data, container);
             else {
                 const missingLib = !window.THREE ? 'THREE.js' : 'Globe.gl';
                 logger.error(`${missingLib} library failed to load`);
                 container.innerHTML = '<div class="error-placeholder">Visualization Unavailable (Network Error)</div>';
             }
        });
    }
}

function _initGlobeInternal(data, container) {
    // Clear loading indicator
    container.innerHTML = '';

    // Check if Globe and THREE libraries are loaded
    if (!window.Globe || typeof window.Globe !== 'function') {
        logger.error('Globe.gl library not loaded');
        container.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--danger-color);">Globe visualization unavailable</div>';
        return;
    }
    if (!window.THREE) {
        logger.error('THREE.js library not loaded');
        container.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--danger-color);">3D rendering library unavailable</div>';
        return;
    }

    // Comprehensive list of country centroids
    const countryCentroids = {
        "AF": { lat: 33.9391, lng: 67.7100, name: "Afghanistan" },
        "AL": { lat: 41.1533, lng: 20.1683, name: "Albania" },
        "DZ": { lat: 28.0339, lng: 1.6596, name: "Algeria" },
        "AS": { lat: -14.2710, lng: -170.1320, name: "American Samoa" },
        "AD": { lat: 42.5462, lng: 1.6016, name: "Andorra" },
        "AO": { lat: -11.2027, lng: 17.8739, name: "Angola" },
        "AI": { lat: 18.2206, lng: -63.0686, name: "Anguilla" },
        "AQ": { lat: -75.2509, lng: -0.0714, name: "Antarctica" },
        "AG": { lat: 17.0608, lng: -61.7964, name: "Antigua and Barbuda" },
        "AR": { lat: -38.4161, lng: -63.6167, name: "Argentina" },
        "AM": { lat: 40.0691, lng: 45.0382, name: "Armenia" },
        "AW": { lat: 12.5211, lng: -69.9683, name: "Aruba" },
        "AU": { lat: -25.2744, lng: 133.7751, name: "Australia" },
        "AT": { lat: 47.5162, lng: 14.5501, name: "Austria" },
        "AZ": { lat: 40.1431, lng: 47.5769, name: "Azerbaijan" },
        "BS": { lat: 25.0343, lng: -77.3963, name: "Bahamas" },
        "BH": { lat: 26.0667, lng: 50.5577, name: "Bahrain" },
        "BD": { lat: 23.6850, lng: 90.3563, name: "Bangladesh" },
        "BB": { lat: 13.1939, lng: -59.5432, name: "Barbados" },
        "BY": { lat: 53.7098, lng: 27.9534, name: "Belarus" },
        "BE": { lat: 50.5039, lng: 4.4699, name: "Belgium" },
        "BZ": { lat: 17.1899, lng: -88.4976, name: "Belize" },
        "BJ": { lat: 9.3077, lng: 2.3158, name: "Benin" },
        "BM": { lat: 32.3214, lng: -64.7574, name: "Bermuda" },
        "BT": { lat: 27.5142, lng: 90.4336, name: "Bhutan" },
        "BO": { lat: -16.2902, lng: -63.5887, name: "Bolivia" },
        "BA": { lat: 43.9159, lng: 17.6791, name: "Bosnia and Herzegovina" },
        "BW": { lat: -22.3285, lng: 24.6849, name: "Botswana" },
        "BR": { lat: -14.2350, lng: -51.9253, name: "Brazil" },
        "BN": { lat: 4.5353, lng: 114.7277, name: "Brunei" },
        "BG": { lat: 42.7339, lng: 25.4858, name: "Bulgaria" },
        "BF": { lat: 12.2383, lng: -1.5616, name: "Burkina Faso" },
        "BI": { lat: -3.3731, lng: 29.9189, name: "Burundi" },
        "KH": { lat: 12.5657, lng: 104.9910, name: "Cambodia" },
        "CM": { lat: 7.3697, lng: 12.3547, name: "Cameroon" },
        "CA": { lat: 56.1304, lng: -106.3468, name: "Canada" },
        "CV": { lat: 16.0021, lng: -24.0131, name: "Cape Verde" },
        "KY": { lat: 19.3133, lng: -81.2546, name: "Cayman Islands" },
        "CF": { lat: 6.6111, lng: 20.9394, name: "Central African Republic" },
        "TD": { lat: 15.4542, lng: 18.7322, name: "Chad" },
        "CL": { lat: -35.6751, lng: -71.5430, name: "Chile" },
        "CN": { lat: 35.8617, lng: 104.1954, name: "China" },
        "CO": { lat: 4.5709, lng: -74.2973, name: "Colombia" },
        "KM": { lat: -11.8750, lng: 43.8722, name: "Comoros" },
        "CG": { lat: -0.2280, lng: 15.8277, name: "Congo" },
        "CD": { lat: -4.0383, lng: 21.7587, name: "DR Congo" },
        "CK": { lat: -21.2367, lng: -159.7777, name: "Cook Islands" },
        "CR": { lat: 9.7489, lng: -83.7534, name: "Costa Rica" },
        "CI": { lat: 7.5400, lng: -5.5471, name: "Côte d'Ivoire" },
        "HR": { lat: 45.1000, lng: 15.2000, name: "Croatia" },
        "CU": { lat: 21.5217, lng: -77.7812, name: "Cuba" },
        "CY": { lat: 35.1264, lng: 33.4299, name: "Cyprus" },
        "CZ": { lat: 49.8175, lng: 15.4730, name: "Czech Republic" },
        "DK": { lat: 56.2639, lng: 9.5018, name: "Denmark" },
        "DJ": { lat: 11.8251, lng: 42.5903, name: "Djibouti" },
        "DM": { lat: 15.4150, lng: -61.3710, name: "Dominica" },
        "DO": { lat: 18.7357, lng: -70.1627, name: "Dominican Republic" },
        "EC": { lat: -1.8312, lng: -78.1834, name: "Ecuador" },
        "EG": { lat: 26.8206, lng: 30.8025, name: "Egypt" },
        "SV": { lat: 13.7942, lng: -88.8965, name: "El Salvador" },
        "GQ": { lat: 1.6508, lng: 10.2679, name: "Equatorial Guinea" },
        "ER": { lat: 15.1794, lng: 39.7823, name: "Eritrea" },
        "EE": { lat: 58.5953, lng: 25.0136, name: "Estonia" },
        "ET": { lat: 9.1450, lng: 40.4897, name: "Ethiopia" },
        "FK": { lat: -51.7963, lng: -59.5236, name: "Falkland Islands" },
        "FO": { lat: 61.8926, lng: -6.9118, name: "Faroe Islands" },
        "FJ": { lat: -17.7134, lng: 178.0650, name: "Fiji" },
        "FI": { lat: 61.9241, lng: 25.7482, name: "Finland" },
        "FR": { lat: 46.2276, lng: 2.2137, name: "France" },
        "GF": { lat: 3.9339, lng: -53.1258, name: "French Guiana" },
        "PF": { lat: -17.6797, lng: -149.4068, name: "French Polynesia" },
        "GA": { lat: -0.8037, lng: 11.6094, name: "Gabon" },
        "GM": { lat: 13.4432, lng: -15.3101, name: "Gambia" },
        "GE": { lat: 42.3154, lng: 43.3569, name: "Georgia" },
        "DE": { lat: 51.1657, lng: 10.4515, name: "Germany" },
        "GH": { lat: 7.9465, lng: -1.0232, name: "Ghana" },
        "GI": { lat: 36.1408, lng: -5.3536, name: "Gibraltar" },
        "GR": { lat: 39.0742, lng: 21.8243, name: "Greece" },
        "GL": { lat: 71.7069, lng: -42.6043, name: "Greenland" },
        "GD": { lat: 12.1165, lng: -61.6790, name: "Grenada" },
        "GP": { lat: 16.2650, lng: -61.5510, name: "Guadeloupe" },
        "GU": { lat: 13.4443, lng: 144.7937, name: "Guam" },
        "GT": { lat: 15.7835, lng: -90.2308, name: "Guatemala" },
        "GG": { lat: 49.4482, lng: -2.5895, name: "Guernsey" },
        "GN": { lat: 9.9456, lng: -9.6966, name: "Guinea" },
        "GW": { lat: 11.8037, lng: -15.1804, name: "Guinea-Bissau" },
        "GY": { lat: 4.8604, lng: -58.9302, name: "Guyana" },
        "HT": { lat: 18.9712, lng: -72.2852, name: "Haiti" },
        "HN": { lat: 15.2000, lng: -86.2419, name: "Honduras" },
        "HK": { lat: 22.3193, lng: 114.1694, name: "Hong Kong" },
        "HU": { lat: 47.1625, lng: 19.5033, name: "Hungary" },
        "IS": { lat: 64.9631, lng: -19.0208, name: "Iceland" },
        "IN": { lat: 20.5937, lng: 78.9629, name: "India" },
        "ID": { lat: -0.7893, lng: 113.9213, name: "Indonesia" },
        "IR": { lat: 32.4279, lng: 53.6880, name: "Iran" },
        "IQ": { lat: 33.2232, lng: 43.6793, name: "Iraq" },
        "IE": { lat: 53.1424, lng: -7.6921, name: "Ireland" },
        "IM": { lat: 54.2361, lng: -4.5481, name: "Isle of Man" },
        "IL": { lat: 31.0461, lng: 34.8516, name: "Israel" },
        "IT": { lat: 41.8719, lng: 12.5674, name: "Italy" },
        "JM": { lat: 18.1096, lng: -77.2975, name: "Jamaica" },
        "JP": { lat: 36.2048, lng: 138.2529, name: "Japan" },
        "JE": { lat: 49.2144, lng: -2.1313, name: "Jersey" },
        "JO": { lat: 30.5852, lng: 36.2384, name: "Jordan" },
        "KZ": { lat: 48.0196, lng: 66.9237, name: "Kazakhstan" },
        "KE": { lat: -0.0236, lng: 37.9062, name: "Kenya" },
        "KI": { lat: -3.3704, lng: -168.7340, name: "Kiribati" },
        "KP": { lat: 40.3399, lng: 127.5101, name: "North Korea" },
        "KR": { lat: 35.9078, lng: 127.7669, name: "South Korea" },
        "KW": { lat: 29.3117, lng: 47.4818, name: "Kuwait" },
        "KG": { lat: 41.2044, lng: 74.7661, name: "Kyrgyzstan" },
        "LA": { lat: 19.8563, lng: 102.4955, name: "Laos" },
        "LV": { lat: 56.8796, lng: 24.6032, name: "Latvia" },
        "LB": { lat: 33.8547, lng: 35.8623, name: "Lebanon" },
        "LS": { lat: -29.6099, lng: 28.2336, name: "Lesotho" },
        "LR": { lat: 6.4281, lng: -9.4295, name: "Liberia" },
        "LY": { lat: 26.3351, lng: 17.2283, name: "Libya" },
        "LI": { lat: 47.1660, lng: 9.5554, name: "Liechtenstein" },
        "LT": { lat: 55.1694, lng: 23.8813, name: "Lithuania" },
        "LU": { lat: 49.8153, lng: 6.1296, name: "Luxembourg" },
        "MO": { lat: 22.1987, lng: 113.5439, name: "Macau" },
        "MK": { lat: 41.6086, lng: 21.7453, name: "North Macedonia" },
        "MG": { lat: -18.7669, lng: 46.8691, name: "Madagascar" },
        "MW": { lat: -13.2543, lng: 34.3015, name: "Malawi" },
        "MY": { lat: 4.2105, lng: 101.9758, name: "Malaysia" },
        "MV": { lat: 3.2028, lng: 73.2207, name: "Maldives" },
        "ML": { lat: 17.5707, lng: -3.9962, name: "Mali" },
        "MT": { lat: 35.9375, lng: 14.3754, name: "Malta" },
        "MH": { lat: 7.1315, lng: 171.1845, name: "Marshall Islands" },
        "MQ": { lat: 14.6415, lng: -61.0242, name: "Martinique" },
        "MR": { lat: 21.0079, lng: -10.9408, name: "Mauritania" },
        "MU": { lat: -20.3484, lng: 57.5522, name: "Mauritius" },
        "YT": { lat: -12.8275, lng: 45.1662, name: "Mayotte" },
        "MX": { lat: 23.6345, lng: -102.5528, name: "Mexico" },
        "FM": { lat: 7.4256, lng: 150.5508, name: "Micronesia" },
        "MD": { lat: 47.4116, lng: 28.3699, name: "Moldova" },
        "MC": { lat: 43.7384, lng: 7.4246, name: "Monaco" },
        "MN": { lat: 46.8625, lng: 103.8467, name: "Mongolia" },
        "ME": { lat: 42.7087, lng: 19.3744, name: "Montenegro" },
        "MS": { lat: 16.7425, lng: -62.1874, name: "Montserrat" },
        "MA": { lat: 31.7917, lng: -7.0926, name: "Morocco" },
        "MZ": { lat: -18.6657, lng: 35.5296, name: "Mozambique" },
        "MM": { lat: 21.9162, lng: 95.9560, name: "Myanmar" },
        "NA": { lat: -22.9576, lng: 18.4904, name: "Namibia" },
        "NR": { lat: -0.5228, lng: 166.9315, name: "Nauru" },
        "NP": { lat: 28.3949, lng: 84.1240, name: "Nepal" },
        "NL": { lat: 52.1326, lng: 5.2913, name: "Netherlands" },
        "NC": { lat: -20.9043, lng: 165.6180, name: "New Caledonia" },
        "NZ": { lat: -40.9006, lng: 174.8860, name: "New Zealand" },
        "NI": { lat: 12.8654, lng: -85.2072, name: "Nicaragua" },
        "NE": { lat: 17.6078, lng: 8.0817, name: "Niger" },
        "NG": { lat: 9.0820, lng: 8.6753, name: "Nigeria" },
        "NU": { lat: -19.0544, lng: -169.8672, name: "Niue" },
        "NF": { lat: -29.0408, lng: 167.9547, name: "Norfolk Island" },
        "MP": { lat: 17.3308, lng: 145.3847, name: "Northern Mariana Islands" },
        "NO": { lat: 60.4720, lng: 8.4689, name: "Norway" },
        "OM": { lat: 21.5126, lng: 55.9233, name: "Oman" },
        "PK": { lat: 30.3753, lng: 69.3451, name: "Pakistan" },
        "PW": { lat: 7.5150, lng: 134.5825, name: "Palau" },
        "PS": { lat: 31.9522, lng: 35.2332, name: "Palestine" },
        "PA": { lat: 8.5380, lng: -80.7821, name: "Panama" },
        "PG": { lat: -6.3150, lng: 143.9555, name: "Papua New Guinea" },
        "PY": { lat: -23.4425, lng: -58.4438, name: "Paraguay" },
        "PE": { lat: -9.1900, lng: -75.0152, name: "Peru" },
        "PH": { lat: 12.8797, lng: 121.7740, name: "Philippines" },
        "PN": { lat: -24.7036, lng: -127.4393, name: "Pitcairn" },
        "PL": { lat: 51.9194, lng: 19.1451, name: "Poland" },
        "PT": { lat: 39.3999, lng: -8.2245, name: "Portugal" },
        "PR": { lat: 18.2208, lng: -66.5901, name: "Puerto Rico" },
        "QA": { lat: 25.3548, lng: 51.1839, name: "Qatar" },
        "RE": { lat: -21.1151, lng: 55.5364, name: "Réunion" },
        "RO": { lat: 45.9432, lng: 24.9668, name: "Romania" },
        "RU": { lat: 61.5240, lng: 105.3188, name: "Russia" },
        "RW": { lat: -1.9403, lng: 29.8739, name: "Rwanda" },
        "BL": { lat: 17.9000, lng: -62.8333, name: "Saint Barthélemy" },
        "SH": { lat: -15.9650, lng: -5.7089, name: "Saint Helena" },
        "KN": { lat: 17.3578, lng: -62.7830, name: "Saint Kitts and Nevis" },
        "LC": { lat: 13.9094, lng: -60.9789, name: "Saint Lucia" },
        "MF": { lat: 18.0708, lng: -63.0501, name: "Saint Martin" },
        "PM": { lat: 46.9419, lng: -56.2711, name: "Saint Pierre and Miquelon" },
        "VC": { lat: 12.9843, lng: -61.2872, name: "Saint Vincent and the Grenadines" },
        "WS": { lat: -13.7590, lng: -172.1046, name: "Samoa" },
        "SM": { lat: 43.9424, lng: 12.4578, name: "San Marino" },
        "ST": { lat: 0.1864, lng: 6.6131, name: "Sao Tome and Principe" },
        "SA": { lat: 23.8859, lng: 45.0792, name: "Saudi Arabia" },
        "SN": { lat: 14.4974, lng: -14.4524, name: "Senegal" },
        "RS": { lat: 44.0165, lng: 21.0059, name: "Serbia" },
        "SC": { lat: -4.6796, lng: 55.4920, name: "Seychelles" },
        "SL": { lat: 8.4606, lng: -11.7799, name: "Sierra Leone" },
        "SG": { lat: 1.3521, lng: 103.8198, name: "Singapore" },
        "SX": { lat: 18.0425, lng: -63.0548, name: "Sint Maarten" },
        "SK": { lat: 48.6690, lng: 19.6990, name: "Slovakia" },
        "SI": { lat: 46.1512, lng: 14.9955, name: "Slovenia" },
        "SB": { lat: -9.6457, lng: 160.1562, name: "Solomon Islands" },
        "SO": { lat: 5.1521, lng: 46.1996, name: "Somalia" },
        "ZA": { lat: -30.5595, lng: 22.9375, name: "South Africa" },
        "GS": { lat: -54.4296, lng: -36.5879, name: "South Georgia and the South Sandwich Islands" },
        "SS": { lat: 6.8770, lng: 31.3070, name: "South Sudan" },
        "ES": { lat: 40.4637, lng: -3.7492, name: "Spain" },
        "LK": { lat: 7.8731, lng: 80.7718, name: "Sri Lanka" },
        "SD": { lat: 12.8628, lng: 30.2176, name: "Sudan" },
        "SR": { lat: 3.9193, lng: -56.0278, name: "Suriname" },
        "SJ": { lat: 77.5536, lng: 23.6703, name: "Svalbard and Jan Mayen" },
        "SZ": { lat: -26.5225, lng: 31.4659, name: "Eswatini" },
        "SE": { lat: 60.1282, lng: 18.6435, name: "Sweden" },
        "CH": { lat: 46.8182, lng: 8.2275, name: "Switzerland" },
        "SY": { lat: 34.8021, lng: 38.9968, name: "Syria" },
        "TW": { lat: 23.6978, lng: 120.9605, name: "Taiwan" },
        "TJ": { lat: 38.8610, lng: 71.2761, name: "Tajikistan" },
        "TZ": { lat: -6.3690, lng: 34.8888, name: "Tanzania" },
        "TH": { lat: 15.8700, lng: 100.9925, name: "Thailand" },
        "TL": { lat: -8.8742, lng: 125.7275, name: "Timor-Leste" },
        "TG": { lat: 8.6195, lng: 0.8248, name: "Togo" },
        "TK": { lat: -8.9673, lng: -171.8559, name: "Tokelau" },
        "TO": { lat: -21.1790, lng: -175.1982, name: "Tonga" },
        "TT": { lat: 10.6918, lng: -61.2225, name: "Trinidad and Tobago" },
        "TN": { lat: 33.8869, lng: 9.5375, name: "Tunisia" },
        "TR": { lat: 38.9637, lng: 35.2433, name: "Turkey" },
        "TM": { lat: 38.9697, lng: 59.5563, name: "Turkmenistan" },
        "TC": { lat: 21.6940, lng: -71.7979, name: "Turks and Caicos Islands" },
        "TV": { lat: -7.1095, lng: 177.6493, name: "Tuvalu" },
        "UG": { lat: 1.3733, lng: 32.2903, name: "Uganda" },
        "UA": { lat: 48.3794, lng: 31.1656, name: "Ukraine" },
        "AE": { lat: 23.4241, lng: 53.8478, name: "United Arab Emirates" },
        "GB": { lat: 55.3781, lng: -3.4360, name: "United Kingdom" },
        "US": { lat: 37.0902, lng: -95.7129, name: "United States" },
        "UY": { lat: -32.5228, lng: -55.7658, name: "Uruguay" },
        "UZ": { lat: 41.3775, lng: 64.5853, name: "Uzbekistan" },
        "VU": { lat: -15.3767, lng: 166.9592, name: "Vanuatu" },
        "VE": { lat: 6.4238, lng: -66.5897, name: "Venezuela" },
        "VN": { lat: 14.0583, lng: 108.2772, name: "Vietnam" },
        "WF": { lat: -13.7691, lng: -177.1561, name: "Wallis and Futuna" },
        "EH": { lat: 24.2155, lng: -12.8858, name: "Western Sahara" },
        "YE": { lat: 15.5527, lng: 48.5164, name: "Yemen" },
        "ZM": { lat: -13.1339, lng: 27.8493, name: "Zambia" },
        "ZW": { lat: -19.0154, lng: 29.1549, name: "Zimbabwe" }
    };

    function getDeterministicLocation(cc) {
        // Simple hash to map CC to a lat/lng on the map (stable)
        let hash = 0;
        for (let i = 0; i < cc.length; i++) {
            hash = cc.charCodeAt(i) + ((hash << 5) - hash);
        }
        // Map to lat (-60 to 80), lng (-180 to 180) to avoid poles
        const lat = (Math.abs(hash) % 140) - 60;
        const lng = (Math.abs(hash >> 8) % 360) - 180;
        return { lat, lng, name: cc };
    }

    const arcsData = [];
    const pointsData = [];

    if (data.proxy_locations && data.proxy_locations.length > 0) {
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

        Object.entries(countryStats).forEach(([ccRaw, count]) => {
            const cc = ccRaw.toUpperCase();
            const info = countryCentroids[cc] || getDeterministicLocation(cc);

            pointsData.push({
                lat: info.lat,
                lng: info.lng,
                size: Math.sqrt(count) / 5,
                // F6 Fix: Use centralized or standard color logic if needed, but here getScoreColor is specific to heatmap
                color: getScoreColor(count / maxCount),
                name: `${info.name || cc}: ${count} proxies`
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

    const isDarkMode = document.body.classList.contains('dark');
    const globeTexture = isDarkMode
        ? '//unpkg.com/three-globe/example/img/earth-night.jpg'
        : '//unpkg.com/three-globe/example/img/earth-blue-marble.jpg';

    // Renamed from 'Globe' to 'globe' to avoid shadowing window.Globe
    // which causes "Cannot access 'Globe' before initialization" error
    let globe;
    try {
        globe = window.Globe()
          (container)
          .globeImageUrl(globeTexture)
          .bumpImageUrl('//unpkg.com/three-globe/example/img/earth-topology.png')
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

        if (isDarkMode) {
            globe.backgroundImageUrl('//unpkg.com/three-globe/example/img/night-sky.png');
        } else {
            const scene = globe.scene();
            if (scene) {
                scene.background = new THREE.Color(0xf0f4f8);
            }
        }
    } catch (e) {
        logger.error("Failed to initialize Globe:", e);
        container.innerHTML = '<div style="display: flex; align-items: center; justify-content: center; height: 100%; flex-direction: column; color: var(--text-secondary);"><i data-feather="globe" style="width: 48px; height: 48px; margin-bottom: 1rem; opacity: 0.5;"></i><span>3D Visualization Unavailable</span><span style="font-size: 0.8rem; opacity: 0.7; margin-top: 0.5rem;">WebGL is not supported in this environment</span></div>';
        if (window.feather) window.feather.replace();
        return;
    }

    const controls = globe.controls();
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.35;
    controls.enableZoom = false; // Default: No Zoom
    controls.minDistance = 180;
    controls.maxDistance = 500;
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;

    let rotationCooldownTimer = null;
    const COOLDOWN_DURATION = 2000;
    let interactionActive = false;

    // Handler for interaction
    const handleInteraction = () => {
        // Stop auto rotation immediately
        controls.autoRotate = false;

        // Enable zoom if not already enabled (cooldown active logic)
        if (!interactionActive) {
            interactionActive = true;
            controls.enableZoom = true; // Enable zoom when interacting
            container.classList.add('zoom-active');
            container.classList.remove('zoom-inactive');
        }

        // Reset cooldown timer
        if (rotationCooldownTimer) {
            clearTimeout(rotationCooldownTimer);
        }

        // Set timer to resume auto-rotation and disable zoom after 2s of inactivity
        rotationCooldownTimer = setTimeout(() => {
            controls.autoRotate = true; // Auto spin on
            interactionActive = false;
            controls.enableZoom = false; // Zoom off
            container.classList.remove('zoom-active');
            container.classList.add('zoom-inactive');
        }, COOLDOWN_DURATION);
    };

    container.addEventListener('mousedown', handleInteraction);
    container.addEventListener('touchstart', handleInteraction);
    container.addEventListener('wheel', handleInteraction);

    // Do NOT set zoom-inactive initially which set pointer-events: none
    // container.classList.add('zoom-inactive');

    // Instead just ensure zoom is disabled in controls initially (done above)
    // and let CSS cursor indicate grabbable

    globe.pointOfView({ lat: 20, lng: 0, altitude: 2.5 }, 0);

    window.addEventListener('resize', () => {
        globe.width(container.clientWidth);
        globe.height(container.clientHeight);
    });

    window.addEventListener('themechanged', (e) => {
        const newIsDark = e.detail.theme === 'dark';
        const newGlobeTexture = newIsDark
            ? '//unpkg.com/three-globe/example/img/earth-night.jpg'
            : '//unpkg.com/three-globe/example/img/earth-blue-marble.jpg';

        globe.globeImageUrl(newGlobeTexture);

        if (newIsDark) {
            globe.backgroundImageUrl('//unpkg.com/three-globe/example/img/night-sky.png');
        } else {
            const scene = globe.scene();
            if (scene) {
                scene.background = new THREE.Color(0xf0f4f8);
            }
            globe.backgroundImageUrl(null);
        }
    });

    window.globeInstance = globe;
}

function initCharts(data, evasionTrend = null) {
    Chart.defaults.color = '#94a3b8';
    Chart.defaults.borderColor = '#1e293b';

    // FIX: Defensive computation of latency_by_country and latency_by_protocol
    // If these fields are missing but proxy_locations exists, compute them
    if (!data.latency_by_country && data.proxy_locations && data.proxy_locations.length > 0) {
        const latByCountry = {};
        const countByCountry = {};
        for (const p of data.proxy_locations) {
            const cc = p.country || 'XX';
            if (p.latency && p.latency < 9000) {
                if (!latByCountry[cc]) {
                    latByCountry[cc] = 0;
                    countByCountry[cc] = 0;
                }
                latByCountry[cc] += p.latency;
                countByCountry[cc]++;
            }
        }
        data.latency_by_country = {};
        for (const cc in latByCountry) {
            data.latency_by_country[cc] = Math.round(latByCountry[cc] / countByCountry[cc]);
        }
    }

    if (!data.latency_by_protocol && data.proxy_locations && data.proxy_locations.length > 0) {
        const latByProto = {};
        const countByProto = {};
        for (const p of data.proxy_locations) {
            const proto = p.protocol || 'unknown';
            if (p.latency && p.latency < 9000) {
                if (!latByProto[proto]) {
                    latByProto[proto] = 0;
                    countByProto[proto] = 0;
                }
                latByProto[proto] += p.latency;
                countByProto[proto]++;
            }
        }
        data.latency_by_protocol = {};
        for (const proto in latByProto) {
            data.latency_by_protocol[proto] = Math.round(latByProto[proto] / countByProto[proto]);
        }
    }

    // 1. Protocol Distribution
    const protoEl = document.getElementById('protocolChart');
    if (protoEl) {
    const protoCtx = protoEl.getContext('2d');
    const protoLabels = Object.keys(data.protocols || {});
    // F6 Fix: Use centralized color logic
    const protoColors = protoLabels.map((p, i) => generateColor(p, i));

    new Chart(protoCtx, {
        type: 'doughnut',
        data: {
            labels: protoLabels,
            datasets: [{
                data: Object.values(data.protocols || {}),
                backgroundColor: protoColors,
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

    // 2. Latency Distribution
    const latencyEl = document.getElementById('latencyChart');
    if (latencyEl) {
    const latencyCtx = latencyEl.getContext('2d');
    const latData = data.latency_distribution || {};
    // Sync labels with backend thresholds (output_logic.py:150-158)
    // Backend: fast<200ms, medium:200-800ms, slow:800-2000ms, very_slow>2000ms
    new Chart(latencyCtx, {
        type: 'bar',
        data: {
            labels: ['Fast (<200ms)', 'Medium (200-800ms)', 'Slow (800-2000ms)', 'Very Slow (>2s)'],
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
    }

    // 3. Rejection Reasons
    const rejEl = document.getElementById('rejectionChart');
    if (rejEl && data.rejection_reasons) {
        const rejCtx = rejEl.getContext('2d');
        const sortedRej = Object.entries(data.rejection_reasons).sort((a,b) => b[1]-a[1]).slice(0, 8);
        // F6: Use colors?
        const rejColors = sortedRej.map((r, i) => generateColor(r[0], i));

        new Chart(rejCtx, {
            type: 'pie',
            data: {
                labels: sortedRej.map(x => x[0]),
                datasets: [{
                    data: sortedRej.map(x => x[1]),
                    backgroundColor: rejColors,
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

    // 4. Threat Breakdown (Updated Logic)
    const threatEl = document.getElementById('threatChart');
    if (threatEl) {
        const threatCtx = threatEl.getContext('2d');
        const reasons = data.rejection_reasons || {};

        // Define standard categories for color mapping
        const categoryColors = {
            'dirty_ip': '#e74c3c', // Red
            'honeypot': '#c0392b', // Dark Red
            'address_blocked': '#d35400', // Pumpkin
            'address_private_ip': '#f39c12', // Orange
            'private_ip': '#f39c12',
            'timeout': '#95a5a6', // Gray
            'connection_error': '#7f8c8d',
            'handshake_fail': '#bdc3c7',
            'protocol_invalid': '#9b59b6', // Purple
            'parse_error': '#8e44ad',
            'unknown': '#34495e'
        };

        const dataset = [];
        const labels = [];
        const colors = [];

        // Collect all reasons
        const allReasons = Object.entries(reasons);

        // Sort by count descending
        allReasons.sort((a, b) => b[1] - a[1]);

        for (const [key, count] of allReasons) {
            // Assuming all rejection reasons are worth showing if present
            if (count > 0) {
                let label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                let color = categoryColors[key] || generateColor(key, 0);

                dataset.push(count);
                labels.push(label);
                colors.push(color);
            }
        }

        // Fallback if empty but total_dirty > 0
        if (dataset.length === 0 && (data.total_dirty > 0)) {
             dataset.push(data.total_dirty);
             labels.push("Blocked Threats");
             colors.push('#e74c3c');
        }

        if (dataset.length === 0) {
            dataset.push(1);
            labels.push('No Threats');
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
                    title: { display: true, text: 'Threats & Rejections' }
                }
            }
        });
    }

    // 5. Top ASNs
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

    // 6. Top Countries
    const countryEl = document.getElementById('countryChart');
    if (countryEl) {
    const countryCtx = countryEl.getContext('2d');
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

    // 7. Latency by Country
    const latencyByCountryEl = document.getElementById('latencyByCountryChart');
    if (latencyByCountryEl && data.latency_by_country) {
        const latencyByCountryCtx = latencyByCountryEl.getContext('2d');
        const sortedLatencyCountries = Object.entries(data.latency_by_country)
            .sort((a, b) => a[1] - b[1])
            .slice(0, 15);

        new Chart(latencyByCountryCtx, {
            type: 'bar',
            data: {
                labels: sortedLatencyCountries.map(x => x[0]),
                datasets: [{
                    label: 'Avg Latency (ms)',
                    data: sortedLatencyCountries.map(x => x[1]),
                    backgroundColor: sortedLatencyCountries.map(x =>
                        x[1] < 100 ? '#2ecc71' :
                        x[1] < 200 ? '#f39c12' :
                        '#e74c3c'
                    ),
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Latency (ms)' } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }

    // 9. Evasion Trend Chart (Time-series)
    const evasionTrendEl = document.getElementById('evasionTrendChart');
    if (evasionTrendEl && evasionTrend && evasionTrend.length > 0) {
        const evasionTrendCtx = evasionTrendEl.getContext('2d');
        const labels = evasionTrend.map(e => {
            const date = new Date(e.timestamp);
            return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        });

        new Chart(evasionTrendCtx, {
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
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            precision: 0
                        }
                    }
                }
            }
        });
    } else if (evasionTrendEl) {
        // Hide chart container if no data
        evasionTrendEl.closest('.chart-container').style.display = 'none';
    }

    // 8. Latency by Protocol
    const latencyByProtocolEl = document.getElementById('latencyByProtocolChart');
    if (latencyByProtocolEl && data.latency_by_protocol) {
        const latencyByProtocolCtx = latencyByProtocolEl.getContext('2d');
        const protocolLatencies = Object.entries(data.latency_by_protocol)
            .sort((a, b) => a[1] - b[1]);

        new Chart(latencyByProtocolCtx, {
            type: 'bar',
            data: {
                labels: protocolLatencies.map(x => x[0].toUpperCase()),
                datasets: [{
                    label: 'Avg Latency (ms)',
                    data: protocolLatencies.map(x => x[1]),
                    backgroundColor: '#A855F7',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: { beginAtZero: true, title: { display: true, text: 'Latency (ms)' } }
                },
                plugins: { legend: { display: false } }
            }
        });
    }
}

function getScoreColor(score) {
    if (score > 0.8) return '#00ff00';
    if (score > 0.5) return '#ffff00';
    return '#ff0000';
}

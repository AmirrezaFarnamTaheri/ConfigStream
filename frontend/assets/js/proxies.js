import logger from './utils/logger.js';
import { renderTrustState } from './trust-state.js';

// --- COUNTRY THEMES ---
const COUNTRY_THEMES = {
    'US': { p: '#3C3B6E', s: '#B22234', t: '#FFFFFF' }, // USA: Navy, Red, White
    'DE': { p: '#FFCE00', s: '#DD0000', t: '#000000' }, // Germany: Gold, Red, Black
    'GB': { p: '#012169', s: '#C8102E', t: '#FFFFFF' }, // UK: Navy, Red, White
    'FR': { p: '#0055A4', s: '#EF4135', t: '#FFFFFF' }, // France: Blue, Red, White
    'NL': { p: '#FF9B00', s: '#AE1C28', t: '#21468B' }, // Netherlands: Orange, Red, Blue
    'RU': { p: '#0039A6', s: '#D52B1E', t: '#FFFFFF' }, // Russia: Blue, Red, White
    'CN': { p: '#EE1C25', s: '#FFFF00', t: '#EE1C25' }, // China: Red, Gold
    'IR': { p: '#239F40', s: '#DA0000', t: '#FFFFFF' }, // Iran: Green, Red, White
    'TR': { p: '#E30A17', s: '#FFFFFF', t: '#E30A17' }, // Turkey: Red, White
    'UA': { p: '#0057B8', s: '#FFD700', t: '#FFFFFF' }, // Ukraine: Blue, Yellow
    'JP': { p: '#BC002D', s: '#FFFFFF', t: '#BC002D' }, // Japan: Red, White
    'KR': { p: '#0047A0', s: '#CD2E3A', t: '#FFFFFF' }, // South Korea: Blue, Red, White
    'SG': { p: '#EF3340', s: '#FFFFFF', t: '#EF3340' }, // Singapore: Red, White
    'CA': { p: '#FF0000', s: '#FFFFFF', t: '#FF0000' }, // Canada: Red, White
    'AU': { p: '#00008B', s: '#FF0000', t: '#FFFFFF' }, // Australia: Blue, Red, White
    'IN': { p: '#FF9933', s: '#138808', t: '#FFFFFF' }, // India: Saffron, Green, White
    'BR': { p: '#009739', s: '#FEDD00', t: '#002776' }, // Brazil: Green, Yellow, Blue
    // Default / Fallback
    'XX': { p: '#5E55F1', s: '#A855F7', t: '#D83A8D' }  // ConfigStream Default (Purple/Pink)
};

/**
 * Calculates brightness of a hex color to determine text color.
 * Returns '#000000' (Black) for light backgrounds, '#FFFFFF' (White) for dark.
 */
function getContrastColor(hexColor) {
    if (!hexColor) return '#FFFFFF';
    // Remove hash if present
    let hex = hexColor.replace('#', '');

    // Handle shorthand hex codes (e.g., "03F" -> "0033FF")
    if (hex.length === 3) {
        hex = hex.split('').map(char => char + char).join('');
    }

    // If hex is not 6 characters after expansion, it's invalid.
    if (hex.length !== 6) {
        return '#FFFFFF'; // Fallback for invalid format
    }

    // Parse RGB
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);

    // YIQ equation for brightness
    const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;

    return (yiq >= 128) ? '#000000' : '#FFFFFF';
}

/**
 * Applies the country theme to the CSS variables.
 */
function applyCountryTheme(countryCode) {
    const root = document.documentElement;
    const code = (countryCode || 'XX').toUpperCase();
    const theme = COUNTRY_THEMES[code] || COUNTRY_THEMES['XX'];

    // 1. Set Main Brand Colors
    root.style.setProperty('--brand-primary', theme.p);
    root.style.setProperty('--brand-secondary', theme.s);
    root.style.setProperty('--brand-tertiary', theme.t);

    // 2. Set Contrast Text Colors
    // If Primary is light (e.g., Yellow for Germany), text becomes Black.
    const textContrast = getContrastColor(theme.p);
    root.style.setProperty('--brand-text-contrast', textContrast);

    // 3. Dynamic Gradient
    // Creates a gradient using the 3 flag colors
    const gradient = `linear-gradient(135deg, ${theme.p} 0%, ${theme.t} 50%, ${theme.s} 100%)`;
    root.style.setProperty('--brand-gradient', gradient);

    // 4. Special Handling for Very Light Backgrounds
    // Adds a class to body so we can add borders/shadows if the background is too white
    const body = document.body;
    if (!body) return;

    if (textContrast === '#000000') {
        body.classList.add('theme-light-primary');
    } else {
        body.classList.remove('theme-light-primary');
    }
}

// Global State
let allProxies = [];
let filteredProxies = [];
let currentPage = 1;
let itemsPerPage = 50;
let currentSort = { field: 'latency', order: 'asc' }; // default: fastest first

// Stats for tags
let stats = {
    revived: 0,
    smartChains: 0
};

// HTML escape helper
function escapeHtml(text) {
    if (!text) return '';
    return String(text).replace(/[&<>"']/g, char => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    })[char]);
}

// Similarity Calculator for Search
const calculateSimilarity = (queryTokens, proxy) => {
    let score = 0;
    const protocol = proxy.protocol ? proxy.protocol.toLowerCase() : '';
    const country = proxy.country_code ? proxy.country_code.toLowerCase() : '';
    const city = proxy.city ? proxy.city.toLowerCase() : '';
    const org = proxy.org ? proxy.org.toLowerCase() : '';
    const tags = proxy.tags ? (Array.isArray(proxy.tags) ? proxy.tags.join(' ') : proxy.tags).toLowerCase() : '';

    for (let i = 0; i < queryTokens.length; i++) {
        const token = queryTokens[i];
        if (country === token) { score += 20; continue; }
        if (protocol.includes(token)) { score += 5; }
        if (country.includes(token)) { score += 2; }
        if (city.includes(token)) { score += 5; }
        if (org.includes(token)) { score += 2; }
        if (tags.includes(token)) { score += 3; }
    }
    return score;
};

// Data Processor
function processProxyData(raw) {
    const tags = raw.tags ? (Array.isArray(raw.tags) ? raw.tags.join(' ') : raw.tags) : '';
    const tagsLower = tags.toLowerCase();
    const proc = (raw.process || 'native').toLowerCase();
    const shieldedVerified = raw.shielded_verified === true || raw.verification_status === 'shielded_verified';
    const isWashed = tagsLower.includes('warp') || tagsLower.includes('secure') || tagsLower.includes('optimal') || proc === 'washed';
    const isShielded = proc === 'shielded';
    const isCandidateOnly = isShielded && !shieldedVerified;
    const isSmart = tagsLower.includes('relay') || tagsLower.includes('intranet') || tagsLower.includes('streaming') || proc === 'chain';
    const effectiveIsWorking = Boolean(raw.is_working) && !isCandidateOnly;
    const statusClass = isCandidateOnly ? 'status-candidate' : (effectiveIsWorking ? 'status-online' : 'status-offline');
    const statusText = isCandidateOnly ? 'Candidate' : (effectiveIsWorking ? 'Online' : 'Offline');

    // Determine Type Tag
    let typeTag = null;
    if (isShielded) {
        typeTag = 'optimal';
    } else if (isWashed) {
        if (tagsLower.includes('optimal')) typeTag = 'optimal';
        else typeTag = 'secure';
    } else if (isSmart) {
        if (tagsLower.includes('intranet')) typeTag = 'intranet';
        else typeTag = 'smart';
    }

    return {
        ...raw,
        isCandidateOnly,
        effectiveIsWorking,
        statusClass,
        statusText,
        latencyVal: raw.latency ?? 9999,
        region: raw.country_code || 'XX',
        protocol: raw.protocol || 'unknown',
        typeTag: typeTag
    };
}

// Global Trust State
let currentTrustState = 'loading'; // 'loading', 'fresh', 'stale', 'invalid', 'empty', 'error'
let cachedMetadata = null;

// --- 5-STATE TRUST UI CONTRACT & PROVENANCE BANNER ---
function applyTrustState(state, metadata, options = {}) {
    currentTrustState = state;
    if (metadata) cachedMetadata = metadata;
    renderTrustState(state, metadata, {
        emptyMessage: 'No proxies match your criteria.',
        errorMessage: state === 'empty' ? 'No proxies match your criteria.' : 'Error loading proxies.',
        ...options,
    });
}

// Operational guard checking fail-closed distribution permission
function isActionAllowed() {
    if (currentTrustState === 'invalid') return false;
    if (window.ConfigStreamArtifactState && typeof window.ConfigStreamArtifactState.canDistribute === 'function') {
        return window.ConfigStreamArtifactState.canDistribute();
    }
    return currentTrustState === 'fresh' || currentTrustState === 'stale';
}

// Global artifact-state event listener for reactive trust transitions
if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
    window.addEventListener('configstream:artifact-state', (event) => {
        const detail = event.detail;
        if (detail) {
            if (detail.status === 'blocked' || detail.canDistribute === false) {
                applyTrustState('invalid', detail.metadata, {
                    errorMessage: 'Security Alert: Detached cryptographic verification failed. Feeds blocked.',
                    onRetry: () => loadProxiesPage()
                });
            }
        }
    });
}

// Initialization & Page Data Loader
async function loadProxiesPage() {
    const loadingEl = document.getElementById('loadingContainer');
    const tableEl = document.getElementById('proxiesTable');
    const emptyState = document.getElementById('emptyState');

    applyTrustState('loading');
    if (loadingEl) {
        loadingEl.classList.remove('hidden');
        loadingEl.replaceChildren();
        const obj = document.createElement('object');
        obj.setAttribute('data', 'assets/svg/logo-loading.svg');
        obj.setAttribute('type', 'image/svg+xml');
        obj.setAttribute('width', '80');
        obj.setAttribute('height', '80');
        obj.setAttribute('aria-hidden', 'true');
        const fallbackImg = document.createElement('img');
        fallbackImg.src = 'assets/svg/favicon.svg';
        fallbackImg.alt = '';
        obj.appendChild(fallbackImg);
        const text = document.createElement('p');
        text.textContent = 'Loading and testing live proxies...';
        loadingEl.appendChild(obj);
        loadingEl.appendChild(text);
    }
    if (tableEl) tableEl.classList.add('hidden');
    if (emptyState) emptyState.classList.add('hidden');

    try {
        if (!window.api) throw new Error("API module missing");

        if (typeof window.api.requireVerifiedArtifact === 'function') {
            await window.api.requireVerifiedArtifact();
        }

        let metadata = null;
        if (window.api.fetchMetadata) {
            try {
                metadata = await window.api.fetchMetadata();
                cachedMetadata = metadata;
            } catch (err) {
                logger.warn("Metadata load failed", err);
            }
        }

        // Fetch Stats
        if (window.api.fetchStatistics) {
            try {
                const meta = await window.api.fetchStatistics();
                stats.revived = meta.total_revived || 0;
                stats.smartChains = meta.total_smart_chains || 0;
                if (!metadata) {
                    metadata = meta;
                    cachedMetadata = meta;
                }
            } catch (err) {
                logger.warn("Stats load failed", err);
            }
        }

        // Fetch Proxies
        // Use fetchProxies() (canonical API entrypoint) instead of fetchAllProxies().
        const proxies = await window.api.fetchProxies();

        if (!Array.isArray(proxies) || proxies.length === 0) {
            applyTrustState('empty', metadata, {
                errorMessage: 'No proxies currently available.',
                onRetry: () => loadProxiesPage()
            });
            if (loadingEl) loadingEl.classList.add('hidden');
            if (tableEl) tableEl.classList.add('hidden');
            if (emptyState) emptyState.classList.remove('hidden');
            allProxies = [];
            filteredProxies = [];
            return;
        }

        // Truthful freshness evaluation strictly referencing metadata.last_updated_utc
        const rawDate = metadata?.last_updated_utc || metadata?.generated_at;
        const genDate = rawDate ? new Date(rawDate) : null;
        const isFallback = proxies.some(p => p.source === 'fallback');
        const intervalHours = Number(metadata?.update_interval_hours || 6);
        const maxAgeHours = Math.min(48, Math.max(12, intervalHours * 2));
        const ageMs = genDate ? (Date.now() - genDate.getTime()) : Infinity;
        const isStale = isFallback || !genDate || Number.isNaN(genDate.getTime()) || (ageMs > maxAgeHours * 60 * 60 * 1000);

        if (isStale) {
            applyTrustState('stale', metadata);
        } else {
            applyTrustState('fresh', metadata);
        }

        // Hide loading, show table
        if (loadingEl) loadingEl.classList.add('hidden');
        if (tableEl) tableEl.classList.remove('hidden');

        // Initial Data Processing
        allProxies = proxies.map(processProxyData);
        filteredProxies = [...allProxies];

        // Populate Dropdowns
        populateDropdowns(allProxies);

        // Initial Render
        renderTable();
        updatePaginationInfo();

        // Update Footer Date strictly from metadata.last_updated_utc
        const footerDate = document.getElementById('footerUpdate');
        if (footerDate) {
            if (genDate && !Number.isNaN(genDate.getTime())) {
                footerDate.textContent = typeof formatTimestamp === 'function' ? formatTimestamp(genDate) : genDate.toISOString();
            } else {
                footerDate.textContent = 'N/A';
            }
            footerDate.classList.remove('loading');
        }

    } catch (e) {
        logger.error("Failed to load proxies:", e);
        const errorMsg = e?.message || String(e);
        const isSecurity = /verification|signature|digest|manifest|blocked|tamper|cryptographic/i.test(errorMsg);
        const isEmptyArtifact = /no verified working proxies|artifact health is degraded/i.test(errorMsg);

        if (isEmptyArtifact) {
            applyTrustState('empty', null, {
                errorMessage: 'No verified working proxies are available in this signed release.',
                onRetry: () => loadProxiesPage()
            });
        } else if (isSecurity) {
            applyTrustState('invalid', null, {
                errorMessage: 'Security Alert: Detached cryptographic verification failed. Feeds blocked.',
                onRetry: () => loadProxiesPage()
            });
        } else {
            applyTrustState('error', null, {
                errorMessage: `Error loading proxies: ${errorMsg}`,
                onRetry: () => loadProxiesPage()
            });
        }

        if (loadingEl) {
            loadingEl.classList.remove('hidden');
            loadingEl.replaceChildren();
            const errorP = document.createElement('p');
            errorP.style.color = 'var(--danger-color)';
            errorP.textContent = isEmptyArtifact
                ? 'No verified working proxies are available in this signed release.'
                : isSecurity
                ? 'Security Alert: Detached cryptographic verification failed. Feeds blocked.'
                : 'Error loading proxies. Please check console or click retry.';
            loadingEl.appendChild(errorP);

            const retryBtn = document.createElement('button');
            retryBtn.className = 'btn btn-primary retry-btn';
            retryBtn.style.marginTop = '12px';
            retryBtn.textContent = 'Retry';
            retryBtn.addEventListener('click', () => {
                loadProxiesPage();
            });
            loadingEl.appendChild(retryBtn);
        }
        if (tableEl) tableEl.classList.add('hidden');
        if (emptyState && isEmptyArtifact) emptyState.classList.remove('hidden');

        const footerDate = document.getElementById('footerUpdate');
        if (footerDate) {
            footerDate.textContent = 'N/A';
            footerDate.classList.remove('loading');
        }
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    setupFilters();
    setupSorting();
    setupPagination();
    setupActionButtons();

    // Initialize Proxy History Chart
    if (typeof ProxyHistoryChart !== 'undefined') {
        window.proxyHistoryChart = new ProxyHistoryChart('history-container');
        await window.proxyHistoryChart.loadHistoryData();
    }

    await loadProxiesPage();
});

// UI Helpers
function renderTable() {
    const tbody = document.getElementById('proxiesTableBody');
    const emptyState = document.getElementById('emptyState');
    if(!tbody) return;

    tbody.replaceChildren();

    if (filteredProxies.length === 0) {
        if(emptyState) emptyState.classList.remove('hidden');
        document.getElementById('proxiesTable').classList.add('hidden');
        return;
    }

    if(emptyState) emptyState.classList.add('hidden');
    document.getElementById('proxiesTable').classList.remove('hidden');

    const start = (currentPage - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    const pageData = filteredProxies.slice(start, end);
    const frag = document.createDocumentFragment();

    pageData.forEach((p, index) => {
        const row = document.createElement('tr');
        row.style.setProperty('--delay', `${index * 0.02}s`);
        row.className = p.effectiveIsWorking ? 'proxy-row' : 'proxy-row proxy-row--offline';

        // Protocol
        const protoCell = document.createElement('td');
        protoCell.setAttribute('data-label', 'Protocol');
        const protoBadge = document.createElement('span');
        protoBadge.className = 'badge badge-protocol';
        protoBadge.textContent = p.protocol.toUpperCase();
        protoCell.appendChild(protoBadge);

        if (p.typeTag) {
            let tagClass = 'badge-info';
            let tagText = 'Smart';
            let icon = '';
            if (p.typeTag === 'secure') { tagClass = 'badge-success'; tagText = 'Secure'; icon = '🛡️'; }
            if (p.typeTag === 'optimal') { tagClass = 'badge-warning'; tagText = 'Optimal'; icon = '⚡'; }
            if (p.typeTag === 'intranet') { tagClass = 'badge-primary'; tagText = 'Intranet'; icon = '🏢'; }
            
            const tagBadge = document.createElement('span');
            tagBadge.className = `badge ${tagClass}`;
            tagBadge.style.fontSize = '0.7em';
            tagBadge.style.marginInlineStart = '5px';
            tagBadge.textContent = `${icon} ${tagText}`;
            protoCell.appendChild(document.createTextNode(' '));
            protoCell.appendChild(tagBadge);
        }
        row.appendChild(protoCell);

        // Location
        const locCell = document.createElement('td');
        locCell.setAttribute('data-label', 'Location');
        locCell.className = 'location-cell';
        const safeCountryCode = p.country_code || 'Unknown';
        const normalizedCountryCode = typeof p.country_code === 'string' ? p.country_code.trim().toLowerCase() : '';
        const hasLocalFlag = /^[a-z]{2}$/.test(normalizedCountryCode) && normalizedCountryCode !== 'xx';
        
        if (hasLocalFlag) {
            const flag = document.createElement('img');
            flag.src = `assets/images/flags/w20/${normalizedCountryCode}.png`;
            flag.className = 'country-flag';
            flag.alt = safeCountryCode;
            flag.addEventListener('error', () => {
                const span = document.createElement('span');
                span.className = 'country-flag country-flag-text';
                span.textContent = safeCountryCode;
                span.ariaLabel = safeCountryCode;
                flag.replaceWith(span);
            });
            locCell.appendChild(flag);
        } else {
            const flagIcon = document.createElement('i');
            flagIcon.dataset.feather = 'globe';
            flagIcon.className = 'country-flag-icon';
            locCell.appendChild(flagIcon);
        }
        
        const locTextSpan = document.createElement('span');
        locTextSpan.textContent = p.city ? `${p.city}, ${safeCountryCode}` : safeCountryCode;
        locCell.appendChild(document.createTextNode(' '));
        locCell.appendChild(locTextSpan);
        row.appendChild(locCell);

        // Latency
        const latCell = document.createElement('td');
        latCell.setAttribute('data-label', 'Latency');
        latCell.className = 'latency-cell tabular-nums';
        const latVal = p.latencyVal === 9999 ? 'N/A' : `${p.latencyVal}ms`;
        // Simple color coding
        let latColor = 'var(--text-primary)';
        if(p.latencyVal < 200) latColor = 'var(--success-color)';
        else if(p.latencyVal > 800) latColor = 'var(--danger-color)';

        const latSpan = document.createElement('span');
        latSpan.className = 'tabular-nums';
        latSpan.style.color = latColor;
        latSpan.style.fontWeight = 'bold';
        latSpan.textContent = latVal;
        latCell.appendChild(latSpan);
        row.appendChild(latCell);

        // Status
        const statusCell = document.createElement('td');
        statusCell.setAttribute('data-label', 'Status');
        statusCell.className = 'status-cell';

        const statusBadge = document.createElement('span');
        statusBadge.className = `status-badge ${p.statusClass}`;
        statusBadge.textContent = p.statusText;
        statusCell.appendChild(statusBadge);
        row.appendChild(statusCell);

        // Process Type (Replaces History)
        const processCell = document.createElement('td');
        processCell.setAttribute('data-label', 'Process');
        processCell.className = 'process-cell';
        const processType = p.process || 'native';
        let pBadge = 'badge-secondary';
        if (processType === 'washed') pBadge = 'badge-success';
        if (processType === 'shielded') pBadge = 'badge-warning';
        if (processType === 'revived' || processType.startsWith('revived-')) pBadge = 'badge-warning';
        if (processType === 'chain') pBadge = 'badge-info';
        if (processType === 'smart') pBadge = 'badge-primary';

        const pBadgeSpan = document.createElement('span');
        pBadgeSpan.className = `badge ${pBadge}`;
        pBadgeSpan.style.fontSize = '0.75em';
        pBadgeSpan.textContent = processType.toUpperCase();
        processCell.appendChild(pBadgeSpan);
        row.appendChild(processCell);

        // Trend (Latency History Sparkline)
        const trendCell = document.createElement('td');
        trendCell.setAttribute('data-label', 'Trend');
        trendCell.className = 'trend-cell tabular-nums';

        // Add trend visualization using history data
        const history = p.history || [];
        if (history.length >= 2) {
            // Create mini sparkline SVG
            const width = 80;
            const height = 24;
            const validHistory = history.filter(l => l > 0 && l < 9999);

            if (validHistory.length >= 2) {
                const maxLat = Math.max(...validHistory, 100);
                const minLat = Math.min(...validHistory);
                const range = maxLat - minLat || 1;

                // Build path
                const points = validHistory.map((lat, idx) => {
                    const x = (idx / (validHistory.length - 1)) * width;
                    const y = height - ((lat - minLat) / range) * (height - 4) - 2;
                    return `${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
                }).join(' ');

                // Determine trend direction
                const firstVal = validHistory[0];
                const lastVal = validHistory[validHistory.length - 1];
                const trendColor = lastVal < firstVal ? '#ef4444' : (lastVal > firstVal ? '#10b981' : '#6366f1');
                const trendIcon = lastVal < firstVal ? '↓' : (lastVal > firstVal ? '↑' : '→');

                const trendWrapper = document.createElement('div');
                trendWrapper.className = 'trend-sparkline tabular-nums';
                trendWrapper.title = `Latency trend: ${history.length} data points`;

                const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
                svg.setAttribute('width', width);
                svg.setAttribute('height', height);
                svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
                svg.setAttribute('aria-hidden', 'true');

                const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
                path.setAttribute('d', points);
                path.setAttribute('fill', 'none');
                path.setAttribute('stroke', trendColor);
                path.setAttribute('stroke-width', '2');
                path.setAttribute('stroke-linecap', 'round');
                
                svg.appendChild(path);
                trendWrapper.appendChild(svg);

                const iconSpan = document.createElement('span');
                iconSpan.style.color = trendColor;
                iconSpan.style.fontSize = '0.8em';
                iconSpan.style.marginLeft = '4px';
                iconSpan.textContent = trendIcon;
                trendWrapper.appendChild(iconSpan);

                trendCell.appendChild(trendWrapper);
            } else {
                const noDataSpan = document.createElement('span');
                noDataSpan.className = 'trend-no-data tabular-nums';
                noDataSpan.textContent = '-';
                trendCell.appendChild(noDataSpan);
            }
        } else {
            const noDataSpan = document.createElement('span');
            noDataSpan.className = 'trend-no-data tabular-nums';
            noDataSpan.textContent = '-';
            trendCell.appendChild(noDataSpan);
        }
        row.appendChild(trendCell);

        // Action
        const actionCell = document.createElement('td');
        actionCell.setAttribute('data-label', 'Action');
        const btn = document.createElement('button');
        btn.className = 'btn btn-secondary copy-btn';
        btn.setAttribute('aria-label', `Copy ${p.protocol} configuration`);
        
        const copyIcon = document.createElement('i');
        copyIcon.dataset.feather = 'copy';
        copyIcon.setAttribute('aria-hidden', 'true');
        btn.appendChild(copyIcon);
        
        // We use data-config attribute or just pass it
        // p.config might be the full URL/URI
        const configStr = p.config || '';
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (!isActionAllowed()) {
                if (window.stateManager && window.stateManager.setError) {
                    window.stateManager.setError('Copy blocked: Artifact verification failed');
                }
                return;
            }
            window.copyToClipboard(configStr, btn);
        });
        actionCell.appendChild(btn);
        row.appendChild(actionCell);

        frag.appendChild(row);
    });

    tbody.appendChild(frag);
    if(window.inlineIcons) window.inlineIcons.replace();

    // History charts removed in favor of Process column
}

function populateDropdowns(proxies) {
    // Countries
    const countries = new Set(proxies.map(p => p.country_code).filter(c => c && c !== 'XX'));
    const countrySel = document.getElementById('filterCountry');
    if(countrySel) {
        countrySel.replaceChildren();
        const defaultOpt = document.createElement('option');
        defaultOpt.value = '';
        defaultOpt.textContent = 'All Countries';
        countrySel.appendChild(defaultOpt);

        [...countries].sort().forEach(cc => {
            const opt = document.createElement('option');
            opt.value = cc;
            try {
                const name = new Intl.DisplayNames(['en'], { type: 'region' }).of(cc);
                opt.textContent = `${name} (${cc})`;
            } catch(e) { opt.textContent = cc; }
            countrySel.appendChild(opt);
        });
    }

    // Protocols
    const protocols = new Set(proxies.map(p => p.protocol));
    const protoSel = document.getElementById('filterProtocol');
    if(protoSel) {
        protoSel.replaceChildren();
        const defaultOpt = document.createElement('option');
        defaultOpt.value = '';
        defaultOpt.textContent = 'All Protocols';
        protoSel.appendChild(defaultOpt);

        [...protocols].sort().forEach(p => {
            const opt = document.createElement('option');
            opt.value = p;
            opt.textContent = p.toUpperCase();
            protoSel.appendChild(opt);
        });
    }

    // Cities
    const cities = new Set(proxies.map(p => p.city).filter(c => c));
    const citySel = document.getElementById('filterCity');
    if(citySel) {
        citySel.replaceChildren();
        const defaultOpt = document.createElement('option');
        defaultOpt.value = '';
        defaultOpt.textContent = 'All Cities';
        citySel.appendChild(defaultOpt);

        [...cities].sort().forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c;
            citySel.appendChild(opt);
        });
    }
}

function setupFilters() {
    const apply = () => {
        const searchInput = document.getElementById('searchInput');
        const search = searchInput ? searchInput.value.toLowerCase() : '';
        const fProto = document.getElementById('filterProtocol').value;
        const fCountry = document.getElementById('filterCountry').value;
        const fCity = document.getElementById('filterCity') ? document.getElementById('filterCity').value : '';
        const minLatInput = document.getElementById('filterLatencyMin');
        const maxLatInput = document.getElementById('filterLatencyMax');

        const minLat = minLatInput && minLatInput.value ? parseInt(minLatInput.value) : 0;
        const maxLat = maxLatInput && maxLatInput.value ? parseInt(maxLatInput.value) : 9999;

        // Base filtering
        let temp = allProxies.filter(p => {
            if (fProto && p.protocol !== fProto) return false;
            if (fCountry && p.country_code !== fCountry) return false;
            if (fCity && p.city !== fCity) return false;
            if (p.latencyVal < minLat || p.latencyVal > maxLat) return false;
            return true;
        });

        // Search logic
        if (search) {
            const queryTokens = search.split(/\s+/);
            const scored = [];
            for (let i = 0; i < temp.length; i++) {
                const score = calculateSimilarity(queryTokens, temp[i]);
                if (score > 0) {
                    scored.push({ proxy: temp[i], score: score });
                }
            }
            scored.sort((a, b) => b.score - a.score);
            temp = scored.map(item => item.proxy);
        }

        filteredProxies = temp;
        currentPage = 1;

        applyCountryTheme(fCountry);
        sortProxies();
        renderTable();
        updatePaginationInfo();
    };

    ['searchInput', 'filterProtocol', 'filterCountry', 'filterCity', 'filterLatencyMin', 'filterLatencyMax'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', apply);
    });

    const clearBtn = document.getElementById('clearFilters');
    if(clearBtn) {
        clearBtn.addEventListener('click', () => {
            document.getElementById('searchInput').value = '';
            document.getElementById('filterProtocol').value = '';
            document.getElementById('filterCountry').value = '';
            if(document.getElementById('filterCity')) document.getElementById('filterCity').value = '';
            document.getElementById('filterLatencyMin').value = '';
            document.getElementById('filterLatencyMax').value = '';
            apply();
        });
    }
}

function setupSorting() {
    const headers = document.querySelectorAll('th.sortable');
    headers.forEach(th => {
        const button = th.querySelector('button.sort-button');
        if (!button) return;

        const activateSort = () => {
            const field = button.dataset.sort;
            if (currentSort.field === field) {
                currentSort.order = currentSort.order === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.field = field;
                currentSort.order = 'asc';
            }

            headers.forEach(h => h.setAttribute('aria-sort', 'none'));
            th.setAttribute('aria-sort', currentSort.order === 'asc' ? 'ascending' : 'descending');

            sortProxies();
            renderTable();
        };
        // Native buttons supply keyboard activation once per deliberate
        // action, without a custom keydown handler firing on key repeat.
        button.addEventListener('click', activateSort);
    });
}

function sortProxies() {
    filteredProxies.sort((a, b) => {
        let valA, valB;
        switch (currentSort.field) {
            case 'latency': valA = a.latencyVal; valB = b.latencyVal; break;
            case 'location': valA = a.country_code; valB = b.country_code; break;
            case 'protocol': valA = a.protocol; valB = b.protocol; break;
            case 'status': valA = a.is_working ? 1 : 0; valB = b.is_working ? 1 : 0; break;
            default: valA = a.latencyVal; valB = b.latencyVal;
        }
        if (valA < valB) return currentSort.order === 'asc' ? -1 : 1;
        if (valA > valB) return currentSort.order === 'asc' ? 1 : -1;
        return 0;
    });
}

function setupPagination() {
    const pageSizeEl = document.getElementById('pageSize');
    if(pageSizeEl) {
        pageSizeEl.addEventListener('change', (e) => {
            itemsPerPage = parseInt(e.target.value);
            currentPage = 1;
            renderTable();
            updatePaginationInfo();
        });
    }
}

function updatePaginationInfo() {
    const total = filteredProxies.length;
    const countEl = document.getElementById('filterCount');
    if(countEl) {
        if (window.innerWidth < 768) {
            countEl.textContent = `${filteredProxies.length}/${allProxies.length}`;
        } else {
            countEl.textContent = `Showing ${Math.min(itemsPerPage, total)} of ${total} proxies`;
        }
    }

    const container = document.getElementById('pagination-container');
    if(!container) return;
    container.replaceChildren();

    const totalPages = Math.ceil(total / itemsPerPage);
    if (totalPages <= 1) return;

    const createBtn = (text, page, disabled) => {
        const b = document.createElement('button');
        b.className = 'pagination-btn';
        b.textContent = text;
        b.disabled = disabled;
        b.addEventListener('click', () => { 
            currentPage = page; 
            renderTable(); 
            updatePaginationInfo(); 
        });
        return b;
    };

    // Use Unicode arrows (‹ U+2039, › U+203A) instead of HTML entities
    container.appendChild(createBtn('‹', currentPage - 1, currentPage === 1));

    const span = document.createElement('span');
    span.className = 'pagination-info';
    span.textContent = `Page ${currentPage} of ${totalPages}`;
    container.appendChild(span);

    container.appendChild(createBtn('›', currentPage + 1, currentPage === totalPages));
}

// --- Copy All / Copy Filtered / Download Filtered ---
function getVisibleConfigs(useAll) {
    const source = useAll ? allProxies : filteredProxies;
    return source.map(p => p.config).filter(Boolean);
}

function setupActionButtons() {
    const copyAllBtn = document.getElementById('copyAll');
    if (copyAllBtn) {
        copyAllBtn.addEventListener('click', async () => {
            if (!isActionAllowed()) {
                if (window.stateManager && window.stateManager.setError) {
                    window.stateManager.setError('Copy blocked: Distribution disabled until artifact verification succeeds');
                }
                return;
            }
            const configs = getVisibleConfigs(true);
            if (configs.length === 0) return;
            if (window.copyToClipboard) {
                await window.copyToClipboard(configs.join('\n'), copyAllBtn);
            }
        });
    }

    const copyFilteredBtn = document.getElementById('copyFiltered');
    if (copyFilteredBtn) {
        copyFilteredBtn.addEventListener('click', async () => {
            if (!isActionAllowed()) {
                if (window.stateManager && window.stateManager.setError) {
                    window.stateManager.setError('Copy blocked: Distribution disabled until artifact verification succeeds');
                }
                return;
            }
            const configs = getVisibleConfigs(false);
            if (configs.length === 0) return;
            if (window.copyToClipboard) {
                await window.copyToClipboard(configs.join('\n'), copyFilteredBtn);
            }
        });
    }

    const downloadFilteredBtn = document.getElementById('downloadFiltered');
    if (downloadFilteredBtn) {
        downloadFilteredBtn.addEventListener('click', () => {
            if (!isActionAllowed()) {
                if (window.stateManager && window.stateManager.setError) {
                    window.stateManager.setError('Download blocked: Distribution disabled until artifact verification succeeds');
                }
                return;
            }
            const configs = getVisibleConfigs(false);
            if (configs.length === 0) return;
            const blob = new Blob([configs.join('\n')], { type: 'text/plain' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'configstream-proxies.txt';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
    }
}

export { processProxyData, applyTrustState, loadProxiesPage };

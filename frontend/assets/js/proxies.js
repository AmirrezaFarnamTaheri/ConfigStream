@ -1,370 +1,352 @@
console.log('Proxies script loaded');
// Page-specific logic for the proxies page

// HTML escape function to prevent XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('proxiesTable')) return;

    let allProxies = [];
    let allVectors = {}; // For Natural Language Search
    let currentSort = { key: 'latency', asc: true };
    let currentPage = 1;
    let proxiesPerPage = 50;

    // Filter & Search Elements
    const protocolFilter = document.getElementById('filterProtocol');
    const countryFilter = document.getElementById('filterCountry');
    const cityFilter = document.getElementById('filterCity');
    const searchInput = document.getElementById('searchInput');
    const tableBody = document.getElementById('proxiesTableBody');
    const emptyState = document.getElementById('emptyState');
    const proxiesTable = document.getElementById('proxiesTable');

    // Controls
    const clearFiltersBtn = document.getElementById('clearFilters');
    const copyAllBtn = document.getElementById('copyAll');
    const copyFilteredBtn = document.getElementById('copyFiltered');
    const downloadFilteredBtn = document.getElementById('downloadFiltered');
    const filterCount = document.getElementById('filterCount');
    const latencyMinInput = document.getElementById('filterLatencyMin');
    const latencyMaxInput = document.getElementById('filterLatencyMax');
    const paginationContainer = document.getElementById('pagination-container');
    const pageSizeSelector = document.getElementById('pageSize');

    // Early return
    if (!protocolFilter || !countryFilter || !tableBody || !emptyState) return;

    // --- Vector Search Helper ---
    // Calculates simple cosine similarity or token overlap
    // Optimized to avoid excessive string concatenation
    const calculateSimilarity = (queryTokens, proxy) => {
        let score = 0;

        // Pre-compute string for search only once per proxy?
        // Actually, let's check fields directly to avoid giant string concat
        const protocol = proxy.protocol ? proxy.protocol.toLowerCase() : '';
        const country = proxy.country_code ? proxy.country_code.toLowerCase() : '';
        const city = proxy.city ? proxy.city.toLowerCase() : '';
        const org = proxy.org ? proxy.org.toLowerCase() : '';
        const tags = proxy.tags ? proxy.tags.join(' ').toLowerCase() : '';

        for (let i = 0; i < queryTokens.length; i++) {
            const token = queryTokens[i];
            if (country === token) { score += 20; continue; }
            if (protocol.includes(token)) { score += 5; }
            if (country.includes(token)) { score += 2; }
            if (city.includes(token)) { score += 5; }
            if (org.includes(token)) { score += 2; }
            if (tags.includes(token)) { score += 3; }
// Proxies Page Logic
// Handles filtering, sorting, rendering, and interaction on proxies.html

// We rely on window.api (from utils.js) for data fetching
// and window.format for display logic

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

document.addEventListener('DOMContentLoaded', async () => {
    // 1. Initialize UI Listeners
    setupFilters();
    setupSorting();
    setupPagination();

    // 2. Load Data
    const loadingEl = document.getElementById('loadingContainer');
    const tableEl = document.getElementById('proxiesTable');

    try {
        if (!window.api) throw new Error("API module missing");

        // Use Metadata to populate stats if available
        if (window.api.fetchStatistics) {
            try {
                const meta = await window.api.fetchStatistics();
                stats.revived = meta.total_revived || 0;
                stats.smartChains = meta.total_smart_chains || 0;
            } catch(e) { console.warn("Metadata load failed", e); }
        }

        return score;
    };

    const getFilteredProxies = () => {
        const protoFilter = protocolFilter.value.toLowerCase();
        const countryFilterValue = countryFilter.value.toLowerCase();
        const cityFilterValue = cityFilter.value.toLowerCase();
        const latencyMin = latencyMinInput && latencyMinInput.value ? parseInt(latencyMinInput.value) : null;
        const latencyMax = latencyMaxInput && latencyMaxInput.value ? parseInt(latencyMaxInput.value) : null;
        const searchQuery = searchInput ? searchInput.value.toLowerCase().trim() : '';

        // 1. First Pass: Hard Filters
        let filtered = allProxies.filter(p => {
            const protocol = p.protocol.toLowerCase();
            const country = p.country_code ? p.country_code.toLowerCase() : '';
            const city = p.city ? p.city.toLowerCase() : '';
            const latency = p.latency || 0;

            const matchesProtocol = protoFilter === '' || protocol.includes(protoFilter);
            const matchesCountry = countryFilterValue === '' || country.includes(countryFilterValue);
            const matchesCity = cityFilterValue === '' || city.includes(cityFilterValue);
            const matchesLatencyMin = latencyMin === null || latency >= latencyMin;
            const matchesLatencyMax = latencyMax === null || latency <= latencyMax;

            return matchesProtocol && matchesCountry && matchesCity && matchesLatencyMin && matchesLatencyMax;
        });

        // 2. Second Pass: Search / Vectors
        if (searchQuery) {
            // Check for explicit latency queries like "<100ms"
            const latencyLimitMatch = searchQuery.match(/<(\d+)(ms)?/);
            if (latencyLimitMatch) {
                const limit = parseInt(latencyLimitMatch[1]);
                filtered = filtered.filter(p => (p.latency || 9999) < limit);
            }
        const proxies = await window.api.fetchAllProxies();

            // Optimize: Tokenize once
            const queryTokens = searchQuery.split(/\s+/);

            // Rank by similarity
            // Use a temporary array to store scores to avoid re-sorting overhead on objects
            const scored = [];
            for (let i = 0; i < filtered.length; i++) {
                const score = calculateSimilarity(queryTokens, filtered[i]);
                if (score > 0) {
                    scored.push({ proxy: filtered[i], score: score });
                }
            }
        // Hide loading
        loadingEl.classList.add('hidden');
        tableEl.classList.remove('hidden');

            scored.sort((a, b) => b.score - a.score);
            filtered = scored.map(item => item.proxy);
        }
        // Initial Data Processing
        allProxies = proxies.map(processProxyData);
        filteredProxies = [...allProxies];

        return filtered;
    };
        // Populate Filter Dropdowns
        populateDropdowns(allProxies);

    const generateSparkline = (history) => {
        if (!Array.isArray(history) || history.length < 2) return '';
        // Initial Render
        renderTable();
        updatePaginationInfo();

        // Coerce and validate numeric values to avoid injecting arbitrary strings into SVG.
        const numericHistory = history
            .map((v) => Number(v))
            .filter((v) => Number.isFinite(v));
        // Update Footer Date
        const footerDate = document.getElementById('footerUpdate');
        if (footerDate) footerDate.textContent = new Date().toLocaleString();
        if (footerDate) footerDate.classList.remove('loading');

        if (numericHistory.length < 2) return '';
    } catch (e) {
        console.error("Failed to load proxies:", e);
        loadingEl.innerHTML = `<p style="color:var(--danger-color)">Error loading proxies. Please check console.</p>`;
    }
});

        // SVG dimensions
        const width = 60;
        const height = 20;
function processProxyData(raw) {
    // Normalize data for sorting/filtering
    // Raw might be just the config object or enriched
    // We expect window.api.fetchAllProxies to return list of enriched objects if possible
    // or we assume standard fields.

    // Check if tags string exists
    const tags = raw.tags ? (Array.isArray(raw.tags) ? raw.tags.join(' ') : raw.tags) : '';
    const isWashed = tags.includes('WARP') || tags.includes('Secure') || tags.includes('Optimal');
    const isSmart = tags.includes('RELAY') || tags.includes('INTRANET') || tags.includes('STREAMING');

    // Determine Type Tag
    let typeTag = null;
    if (isWashed) {
        if (tags.includes('Optimal')) typeTag = 'optimal';
        else typeTag = 'secure';
    } else if (isSmart) {
        if (tags.includes('INTRANET')) typeTag = 'intranet';
        else typeTag = 'smart';
    }

    return {
        ...raw,
        // Computed fields for easier sorting
        latencyVal: raw.latency || 9999,
        region: raw.country_code || 'XX',
        protocol: raw.protocol || 'unknown',
        typeTag: typeTag
    };
}

        const min = Math.min(...numericHistory);
        const max = Math.max(...numericHistory);
        const range = max - min || 1;
function renderTable() {
    const tbody = document.getElementById('proxiesTableBody');
    const emptyState = document.getElementById('emptyState');
    tbody.innerHTML = '';

        const points = numericHistory
            .map((val, i) => {
                const x = (i / (numericHistory.length - 1)) * width;
                const y = height - ((val - min) / range) * height;
                return `${x},${y}`;
            })
            .join(' ');
    if (filteredProxies.length === 0) {
        emptyState.classList.remove('hidden');
        document.getElementById('proxiesTable').classList.add('hidden');
        return;
    }

        // Color based on trend (last point vs avg)
        const avg =
            numericHistory.reduce((a, b) => a + b, 0) / numericHistory.length;
        const last = numericHistory[numericHistory.length - 1];
        const color = last > avg * 1.5 ? '#ff4d4d' : '#4caf50'; // Red if spiking, Green if stable
    emptyState.classList.add('hidden');
    document.getElementById('proxiesTable').classList.remove('hidden');

        return `<svg width="${width}" height="${height}" class="sparkline"><polyline points="${points}" fill="none" stroke="${color}" stroke-width="1.5" /></svg>`;
    };
    const start = (currentPage - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    const pageData = filteredProxies.slice(start, end);

    const renderTable = () => {
        let filteredProxies = getFilteredProxies();
    const frag = document.createDocumentFragment();

        // Update count
        if (filterCount) {
             if (window.innerWidth < 768) {
                 filterCount.textContent = `${filteredProxies.length}/${allProxies.length}`;
             } else {
                 filterCount.textContent = `Showing ${filteredProxies.length} of ${allProxies.length} proxies`;
             }
        }
    pageData.forEach(p => {
        const row = document.createElement('tr');

        if (filteredProxies.length === 0) {
            proxiesTable.classList.add('hidden');
            emptyState.classList.remove('hidden');
            return;
        } else {
            proxiesTable.classList.remove('hidden');
            emptyState.classList.add('hidden');
        }
        // Protocol
        const protoCell = document.createElement('td');
        protoCell.innerHTML = `<span class="badge badge-protocol">${p.protocol.toUpperCase()}</span>`;
        if (p.typeTag) {
             let tagClass = 'badge-info';
             let tagText = 'Smart';
             let icon = '';

        // Sort (only if no search query is active, as search implies relevance sort)
        if (!searchInput.value) {
            filteredProxies.sort((a, b) => {
                let valA, valB;
                if (currentSort.key === 'location') {
                    valA = a.country_code || '';
                    valB = b.country_code || '';
                } else if (currentSort.key === 'status') {
                    valA = a.is_working ? 1 : 0;
                    valB = b.is_working ? 1 : 0;
                } else {
                    valA = a[currentSort.key];
                    valB = b[currentSort.key];
                }
                if (valA < valB) return currentSort.asc ? -1 : 1;
                if (valA > valB) return currentSort.asc ? 1 : -1;
                return 0;
            });
        }
             if (p.typeTag === 'secure') { tagClass = 'badge-success'; tagText = 'Secure'; icon = '🛡️'; }
             if (p.typeTag === 'optimal') { tagClass = 'badge-warning'; tagText = 'Optimal'; icon = '⚡'; }
             if (p.typeTag === 'intranet') { tagClass = 'badge-primary'; tagText = 'Intranet'; icon = '🏢'; }

        // Pagination
        const maxPage = Math.ceil(filteredProxies.length / proxiesPerPage) || 1;
        currentPage = Math.max(1, Math.min(currentPage, maxPage));
        const currentProxies = filteredProxies.slice((currentPage - 1) * proxiesPerPage, currentPage * proxiesPerPage);

        const rowsHTML = currentProxies.map((p, index) => {
            const countryCode = (p.country_code && p.country_code !== 'XX') ? escapeHtml(p.country_code) : null;
            const country = countryCode || 'Unknown';
            const city = escapeHtml(p.city) || '';
            const location = city ? `${city}, ${country}` : country;
            const latency = p.latency ? `${escapeHtml(String(p.latency))}ms` : 'N/A';
            const protocol = escapeHtml(p.protocol) || 'N/A';

            // Sparkline Generation
            // Ensure p.history exists (it comes from backend now)
            const sparklineHTML = p.history ? generateSparkline(p.history) : '';

            // Washed Badge
            const isWashed = p.tags && (p.tags.includes('washed'));
            const protocolBadge = isWashed ? ' <span class="shield-badge" title="Securely Washed">🛡️</span>' : '';

            const statusClass = p.is_working ? 'status-online' : 'status-offline';

            return `
                <tr class="proxy-row" style="--delay: ${index * 0.02}s">
                    <td data-label="Protocol">${protocol}${protocolBadge}</td>
                    <td class="location-cell" data-label="Location">
                        ${countryCode ? `<img src="https://flagcdn.com/w20/${countryCode.toLowerCase()}.png" class="country-flag" alt="${country}">` : `<i data-feather="globe"></i>`}
                        <span>${location}</span>
                    </td>
                    <td data-label="Latency">
                        <div class="latency-wrapper">
                            <span>${latency}</span>
                            ${sparklineHTML}
                        </div>
                    </td>
                    <td class="status-cell" data-label="Status">
                        <span class="status-badge ${statusClass}">${p.is_working ? 'Online' : 'Offline'}</span>
                    </td>
                    <td data-label="Action">
                        <button class="btn btn-secondary copy-btn" data-config="${encodeURIComponent(p.config)}">
                            <i data-feather="copy"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

        // Sanitize the constructed table rows before inserting
        if (window.DOMPurify) {
             tableBody.innerHTML = window.DOMPurify.sanitize(rowsHTML, {
                 ADD_TAGS: ['img', 'button', 'i', 'span', 'tr', 'td', 'div', 'svg', 'polyline'],
                 ADD_ATTR: ['src', 'alt', 'class', 'data-label', 'data-config', 'data-feather', 'title', 'width', 'height', 'points', 'fill', 'stroke', 'stroke-width', 'style']
             });
        } else {
             tableBody.innerHTML = rowsHTML; // Fallback (escapeHtml is used inside map)
             protoCell.innerHTML += ` <span class="badge ${tagClass}" style="font-size: 0.7em; margin-left:5px;">${icon} ${tagText}</span>`;
        }
        row.appendChild(protoCell);

        // Location
        const locCell = document.createElement('td');
        locCell.innerHTML = window.format ? window.format.location(p.country_code, p.city) : `${p.country_code} - ${p.city}`;
        row.appendChild(locCell);

        // Latency
        const latCell = document.createElement('td');
        latCell.innerHTML = window.format ? window.format.latency(p.latencyVal) : `${p.latencyVal}ms`;
        row.appendChild(latCell);

        // Status / ISP
        const statusCell = document.createElement('td');
        const isp = p.asn || p.isp || 'Unknown ISP';
        // Truncate ISP if too long
        const shortISP = isp.length > 20 ? isp.substring(0, 20) + '...' : isp;
        statusCell.textContent = shortISP;
        statusCell.title = isp;
        statusCell.classList.add('text-muted');
        row.appendChild(statusCell);

        // Copy Button
        const actionCell = document.createElement('td');
        const btn = document.createElement('button');
        btn.className = 'btn-icon-small';
        btn.innerHTML = `<i data-feather="copy"></i>`;
        btn.onclick = () => copyToClipboard(p.config, btn);
        actionCell.appendChild(btn);
        row.appendChild(actionCell);

        frag.appendChild(row);
    });

        if (window.feather) window.feather.replace();
        renderPagination(filteredProxies.length);
    };

    // Pagination Logic (Simplified for brevity)
    const renderPagination = (total) => {
        const totalPages = Math.ceil(total / proxiesPerPage) || 1;
        let html = '';
    tbody.appendChild(frag);
    if(window.feather) feather.replace();
}

        // Prev
        html += `<button class="pagination-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="changePage(${currentPage - 1})">&lsaquo;</button>`;
function populateDropdowns(proxies) {
    // Countries
    const countries = new Set(proxies.map(p => p.country_code).filter(c => c && c !== 'XX'));
    const countrySel = document.getElementById('filterCountry');
    [...countries].sort().forEach(cc => {
        const opt = document.createElement('option');
        opt.value = cc;
        // Use native names if available via Intl.DisplayNames, else code
        try {
            const name = new Intl.DisplayNames(['en'], { type: 'region' }).of(cc);
            opt.textContent = `${name} (${cc})`;
        } catch(e) { opt.textContent = cc; }
        countrySel.appendChild(opt);
    });

        // Page info
        html += `<span class="pagination-info">Page ${currentPage} of ${totalPages}</span>`;
    // Protocols
    const protocols = new Set(proxies.map(p => p.protocol));
    const protoSel = document.getElementById('filterProtocol');
    [...protocols].sort().forEach(p => {
        const opt = document.createElement('option');
        opt.value = p;
        opt.textContent = p.toUpperCase();
        protoSel.appendChild(opt);
    });

        // Next
        html += `<button class="pagination-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="changePage(${currentPage + 1})">&rsaquo;</button>`;
    // Populate cities on country change (listener added in setupFilters)
}

        if (window.DOMPurify) {
            paginationContainer.innerHTML = window.DOMPurify.sanitize(html);
        } else {
            paginationContainer.innerHTML = html;
        }
    };
function setupFilters() {
    const apply = () => {
        const search = document.getElementById('searchInput').value.toLowerCase();
        const fProto = document.getElementById('filterProtocol').value;
        const fCountry = document.getElementById('filterCountry').value;
        const fCity = document.getElementById('filterCity').value; // if implemented
        const minLat = parseInt(document.getElementById('filterLatencyMin').value) || 0;
        const maxLat = parseInt(document.getElementById('filterLatencyMax').value) || 9999;

        filteredProxies = allProxies.filter(p => {
            if (fProto && p.protocol !== fProto) return false;
            if (fCountry && p.country_code !== fCountry) return false;
            if (p.latencyVal < minLat || p.latencyVal > maxLat) return false;

            if (search) {
                // Search in config, tags, location
                const text = JSON.stringify(p).toLowerCase();
                if (!text.includes(search)) return false;
            }
            return true;
        });

    // Global function for pagination clicks (dirty but simple for vanilla JS)
    window.changePage = (p) => {
        currentPage = p;
        currentPage = 1;
        sortProxies();
        renderTable();
        updatePaginationInfo();
    };

    // Event Listeners
    if(searchInput) searchInput.addEventListener('input', () => { currentPage = 1; renderTable(); });
    protocolFilter.addEventListener('change', () => { currentPage = 1; renderTable(); });
    countryFilter.addEventListener('change', () => { currentPage = 1; renderTable(); });

    // Load Data
    const loadData = async () => { console.log('Inside loadData');
        try {
            // Fetch Proxies
            allProxies = await window.api.fetchProxies();
    ['searchInput', 'filterProtocol', 'filterCountry', 'filterCity', 'filterLatencyMin', 'filterLatencyMax'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', apply); // or change
    });

            // Fetch Vectors (Optional, fails gracefully)
            try {
                const vecRes = await fetch('vectors.json');
                if (vecRes.ok) allVectors = await vecRes.json();
            } catch (e) { console.warn("Vectors not found, search will be basic."); }
    document.getElementById('clearFilters').addEventListener('click', () => {
        document.getElementById('searchInput').value = '';
        document.getElementById('filterProtocol').value = '';
        document.getElementById('filterCountry').value = '';
        document.getElementById('filterLatencyMin').value = '';
        document.getElementById('filterLatencyMax').value = '';
        apply();
    });
}

            populateFilters(allProxies); // Assuming this function exists from previous code
            renderTable();
        } catch (e) {
            console.error(e);
            if(emptyState) emptyState.textContent = "Failed to load proxies.";
        }
    };
function setupSorting() {
    const headers = document.querySelectorAll('th.sortable');
    headers.forEach(th => {
        th.addEventListener('click', () => {
            const field = th.dataset.sort;
            // Toggle order
            if (currentSort.field === field) {
                currentSort.order = currentSort.order === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.field = field;
                currentSort.order = 'asc';
            }

    // Helper to populate filters (Preserved logic)
    const populateFilters = (proxies) => {
        const protos = new Set(proxies.map(p => p.protocol).filter(Boolean));
        const countries = new Set(proxies.map(p => p.country_code).filter(Boolean));
            // UI Update
            headers.forEach(h => h.setAttribute('aria-sort', 'none'));
            th.setAttribute('aria-sort', currentSort.order === 'asc' ? 'ascending' : 'descending');

        protos.forEach(p => {
             const opt = document.createElement('option');
             opt.value = p; opt.textContent = p.toUpperCase();
             protocolFilter.appendChild(opt);
            sortProxies();
            renderTable();
        });
    });
}

        countries.forEach(c => {
             const opt = document.createElement('option');
             opt.value = c; opt.textContent = c;
             countryFilter.appendChild(opt);
        });
    };
function sortProxies() {
    filteredProxies.sort((a, b) => {
        let valA, valB;

        switch (currentSort.field) {
            case 'latency':
                valA = a.latencyVal;
                valB = b.latencyVal;
                break;
            case 'location':
                valA = a.country_code;
                valB = b.country_code;
                break;
            case 'protocol':
                valA = a.protocol;
                valB = b.protocol;
                break;
            case 'status':
                valA = a.is_working ? 1 : 0; // simple status check
                valB = b.is_working ? 1 : 0;
                break;
            default:
                valA = a.latencyVal;
                valB = b.latencyVal;
        }

    console.log('Calling loadData'); loadData();

    // WASM Testing Hook
    document.getElementById('testWasm')?.addEventListener('click', async () => {
         const visible = getFilteredProxies().slice(0, 5);
         alert(`Testing top ${visible.length} proxies in browser... check console.`);
         for(const p of visible) {
             if(window.checkProxy) {
                 const res = await window.checkProxy(JSON.stringify(p));
                 console.log(`[WASM] ${p.address}:`, res);
             }
         }
        if (valA < valB) return currentSort.order === 'asc' ? -1 : 1;
        if (valA > valB) return currentSort.order === 'asc' ? 1 : -1;
        return 0;
    });
}

    // --- New Local Verification (WASM) ---
    window.runLocalVerification = async () => {
        const btn = document.getElementById('btn-verify-local');
        const status = document.getElementById('wasm-status');
function setupPagination() {
    document.getElementById('pageSize').addEventListener('change', (e) => {
        itemsPerPage = parseInt(e.target.value);
        currentPage = 1;
        renderTable();
        updatePaginationInfo();
    });
}

        btn.disabled = true;
        status.innerText = "Testing nodes against YOUR internet...";
function updatePaginationInfo() {
    const total = filteredProxies.length;
    const countEl = document.getElementById('filterCount');
    countEl.textContent = `Showing ${Math.min(itemsPerPage, total)} of ${total}`;

    const container = document.getElementById('pagination-container');
    container.innerHTML = '';

    const totalPages = Math.ceil(total / itemsPerPage);
    if (totalPages <= 1) return;

    // Simple Prev/Next
    const createBtn = (text, page, disabled) => {
        const b = document.createElement('button');
        b.className = 'btn btn-secondary';
        b.textContent = text;
        b.disabled = disabled;
        b.onclick = () => { currentPage = page; renderTable(); updatePaginationInfo(); };
        return b;
    };

        // 'allProxies' is our global list
        if (!allProxies || allProxies.length === 0) {
            status.innerText = "No proxies to test.";
            btn.disabled = false;
            return;
        }
    container.appendChild(createBtn('Prev', currentPage - 1, currentPage === 1));

        const optimizedProxies = await window.verifyProxyBatch(allProxies);
    const span = document.createElement('span');
    span.textContent = ` Page ${currentPage} of ${totalPages} `;
    span.style.margin = '0 10px';
    container.appendChild(span);

        // Update global list and re-render
        allProxies = optimizedProxies;
        renderTable();
    container.appendChild(createBtn('Next', currentPage + 1, currentPage === totalPages));
}

        status.innerText = `Verified! Top node: ${optimizedProxies[0].latency}ms`;
        btn.disabled = false;
    };
});
function copyToClipboard(text, btn) {
    if (!text) return;
    navigator.clipboard.writeText(text).then(() => {
        const originalHtml = btn.innerHTML;
        btn.innerHTML = `<i data-feather="check" style="color:var(--success-color)"></i>`;
        if(window.feather) feather.replace();
        setTimeout(() => {
            btn.innerHTML = originalHtml;
            if(window.feather) feather.replace();
        }, 1500);
    });
}
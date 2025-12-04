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

            scored.sort((a, b) => b.score - a.score);
            filtered = scored.map(item => item.proxy);
        }

        return filtered;
    };

    const generateSparkline = (history) => {
        if (!Array.isArray(history) || history.length < 2) return '';

        // Coerce and validate numeric values to avoid injecting arbitrary strings into SVG.
        const numericHistory = history
            .map((v) => Number(v))
            .filter((v) => Number.isFinite(v));

        if (numericHistory.length < 2) return '';

        // SVG dimensions
        const width = 60;
        const height = 20;

        const min = Math.min(...numericHistory);
        const max = Math.max(...numericHistory);
        const range = max - min || 1;

        const points = numericHistory
            .map((val, i) => {
                const x = (i / (numericHistory.length - 1)) * width;
                const y = height - ((val - min) / range) * height;
                return `${x},${y}`;
            })
            .join(' ');

        // Color based on trend (last point vs avg)
        const avg =
            numericHistory.reduce((a, b) => a + b, 0) / numericHistory.length;
        const last = numericHistory[numericHistory.length - 1];
        const color = last > avg * 1.5 ? '#ff4d4d' : '#4caf50'; // Red if spiking, Green if stable

        return `<svg width="${width}" height="${height}" class="sparkline"><polyline points="${points}" fill="none" stroke="${color}" stroke-width="1.5" /></svg>`;
    };

    const renderTable = () => {
        let filteredProxies = getFilteredProxies();

        // Update count
        if (filterCount) {
             if (window.innerWidth < 768) {
                 filterCount.textContent = `${filteredProxies.length}/${allProxies.length}`;
             } else {
                 filterCount.textContent = `Showing ${filteredProxies.length} of ${allProxies.length} proxies`;
             }
        }

        if (filteredProxies.length === 0) {
            proxiesTable.classList.add('hidden');
            emptyState.classList.remove('hidden');
            return;
        } else {
            proxiesTable.classList.remove('hidden');
            emptyState.classList.add('hidden');
        }

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
        }

        if (window.feather) window.feather.replace();
        renderPagination(filteredProxies.length);
    };

    // Pagination Logic (Simplified for brevity)
    const renderPagination = (total) => {
        const totalPages = Math.ceil(total / proxiesPerPage) || 1;
        let html = '';

        // Prev
        html += `<button class="pagination-btn" ${currentPage === 1 ? 'disabled' : ''} onclick="changePage(${currentPage - 1})">&lsaquo;</button>`;

        // Page info
        html += `<span class="pagination-info">Page ${currentPage} of ${totalPages}</span>`;

        // Next
        html += `<button class="pagination-btn" ${currentPage === totalPages ? 'disabled' : ''} onclick="changePage(${currentPage + 1})">&rsaquo;</button>`;

        if (window.DOMPurify) {
            paginationContainer.innerHTML = window.DOMPurify.sanitize(html);
        } else {
            paginationContainer.innerHTML = html;
        }
    };

    // Global function for pagination clicks (dirty but simple for vanilla JS)
    window.changePage = (p) => {
        currentPage = p;
        renderTable();
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

            // Fetch Vectors (Optional, fails gracefully)
            try {
                const vecRes = await fetch('vectors.json');
                if (vecRes.ok) allVectors = await vecRes.json();
            } catch (e) { console.warn("Vectors not found, search will be basic."); }

            populateFilters(allProxies); // Assuming this function exists from previous code
            renderTable();
        } catch (e) {
            console.error(e);
            if(emptyState) emptyState.textContent = "Failed to load proxies.";
        }
    };

    // Helper to populate filters (Preserved logic)
    const populateFilters = (proxies) => {
        const protos = new Set(proxies.map(p => p.protocol).filter(Boolean));
        const countries = new Set(proxies.map(p => p.country_code).filter(Boolean));

        protos.forEach(p => {
             const opt = document.createElement('option');
             opt.value = p; opt.textContent = p.toUpperCase();
             protocolFilter.appendChild(opt);
        });

        countries.forEach(c => {
             const opt = document.createElement('option');
             opt.value = c; opt.textContent = c;
             countryFilter.appendChild(opt);
        });
    };

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
    });

    // --- New Local Verification (WASM) ---
    window.runLocalVerification = async () => {
        const btn = document.getElementById('btn-verify-local');
        const status = document.getElementById('wasm-status');

        btn.disabled = true;
        status.innerText = "Testing nodes against YOUR internet...";

        // 'allProxies' is our global list
        if (!allProxies || allProxies.length === 0) {
            status.innerText = "No proxies to test.";
            btn.disabled = false;
            return;
        }

        const optimizedProxies = await window.verifyProxyBatch(allProxies);

        // Update global list and re-render
        allProxies = optimizedProxies;
        renderTable();

        status.innerText = `Verified! Top node: ${optimizedProxies[0].latency}ms`;
        btn.disabled = false;
    };
});

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

        const proxies = await window.api.fetchAllProxies();

        // Hide loading
        loadingEl.classList.add('hidden');
        tableEl.classList.remove('hidden');

        // Initial Data Processing
        allProxies = proxies.map(processProxyData);
        filteredProxies = [...allProxies];

        // Populate Filter Dropdowns
        populateDropdowns(allProxies);

        // Initial Render
        renderTable();
        updatePaginationInfo();

        // Update Footer Date
        const footerDate = document.getElementById('footerUpdate');
        if (footerDate) footerDate.textContent = new Date().toLocaleString();
        if (footerDate) footerDate.classList.remove('loading');

    } catch (e) {
        console.error("Failed to load proxies:", e);
        loadingEl.innerHTML = `<p style="color:var(--danger-color)">Error loading proxies. Please check console.</p>`;
    }
});

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

function renderTable() {
    const tbody = document.getElementById('proxiesTableBody');
    const emptyState = document.getElementById('emptyState');
    tbody.innerHTML = '';

    if (filteredProxies.length === 0) {
        emptyState.classList.remove('hidden');
        document.getElementById('proxiesTable').classList.add('hidden');
        return;
    }

    emptyState.classList.add('hidden');
    document.getElementById('proxiesTable').classList.remove('hidden');

    const start = (currentPage - 1) * itemsPerPage;
    const end = start + itemsPerPage;
    const pageData = filteredProxies.slice(start, end);

    const frag = document.createDocumentFragment();

    pageData.forEach(p => {
        const row = document.createElement('tr');

        // Protocol
        const protoCell = document.createElement('td');
        protoCell.innerHTML = `<span class="badge badge-protocol">${p.protocol.toUpperCase()}</span>`;
        if (p.typeTag) {
             let tagClass = 'badge-info';
             let tagText = 'Smart';
             let icon = '';

             if (p.typeTag === 'secure') { tagClass = 'badge-success'; tagText = 'Secure'; icon = '🛡️'; }
             if (p.typeTag === 'optimal') { tagClass = 'badge-warning'; tagText = 'Optimal'; icon = '⚡'; }
             if (p.typeTag === 'intranet') { tagClass = 'badge-primary'; tagText = 'Intranet'; icon = '🏢'; }

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

    tbody.appendChild(frag);
    if(window.feather) feather.replace();
}

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

    // Protocols
    const protocols = new Set(proxies.map(p => p.protocol));
    const protoSel = document.getElementById('filterProtocol');
    [...protocols].sort().forEach(p => {
        const opt = document.createElement('option');
        opt.value = p;
        opt.textContent = p.toUpperCase();
        protoSel.appendChild(opt);
    });

    // Populate cities on country change (listener added in setupFilters)
}

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

        currentPage = 1;
        sortProxies();
        renderTable();
        updatePaginationInfo();
    };

    ['searchInput', 'filterProtocol', 'filterCountry', 'filterCity', 'filterLatencyMin', 'filterLatencyMax'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', apply); // or change
    });

    document.getElementById('clearFilters').addEventListener('click', () => {
        document.getElementById('searchInput').value = '';
        document.getElementById('filterProtocol').value = '';
        document.getElementById('filterCountry').value = '';
        document.getElementById('filterLatencyMin').value = '';
        document.getElementById('filterLatencyMax').value = '';
        apply();
    });
}

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

            // UI Update
            headers.forEach(h => h.setAttribute('aria-sort', 'none'));
            th.setAttribute('aria-sort', currentSort.order === 'asc' ? 'ascending' : 'descending');

            sortProxies();
            renderTable();
        });
    });
}

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

        if (valA < valB) return currentSort.order === 'asc' ? -1 : 1;
        if (valA > valB) return currentSort.order === 'asc' ? 1 : -1;
        return 0;
    });
}

function setupPagination() {
    document.getElementById('pageSize').addEventListener('change', (e) => {
        itemsPerPage = parseInt(e.target.value);
        currentPage = 1;
        renderTable();
        updatePaginationInfo();
    });
}

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

    container.appendChild(createBtn('Prev', currentPage - 1, currentPage === 1));

    const span = document.createElement('span');
    span.textContent = ` Page ${currentPage} of ${totalPages} `;
    span.style.margin = '0 10px';
    container.appendChild(span);

    container.appendChild(createBtn('Next', currentPage + 1, currentPage === totalPages));
}

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

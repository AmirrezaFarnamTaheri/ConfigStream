// Page-specific logic for the proxies page
document.addEventListener('DOMContentLoaded', () => {
    if (!document.getElementById('proxiesTable')) return;

    let allProxies = [];
    let currentSort = { key: 'latency', asc: true };
    let currentPage = 1;
    let proxiesPerPage = 50; // Default value, can be changed by the user

    const protocolFilter = document.getElementById('filterProtocol');
    const countryFilter = document.getElementById('filterCountry');
    const cityFilter = document.getElementById('filterCity');
    const tableBody = document.getElementById('proxiesTableBody');
    const emptyState = document.getElementById('emptyState');
    const proxiesTable = document.getElementById('proxiesTable');
    const clearFiltersBtn = document.getElementById('clearFilters');
    const copyFilteredBtn = document.getElementById('copyFiltered');
    const downloadFilteredBtn = document.getElementById('downloadFiltered');
    const filterCount = document.getElementById('filterCount');
    const latencyMinInput = document.getElementById('filterLatencyMin');
    const latencyMaxInput = document.getElementById('filterLatencyMax');
    const paginationContainer = document.getElementById('pagination-container');
    const pageSizeSelector = document.getElementById('pageSize');

    // Early return if required elements don't exist
    if (!protocolFilter || !countryFilter || !tableBody || !emptyState) return;

    const getFilteredProxies = () => {
        const protoFilter = protocolFilter.value.toLowerCase();
        const countryFilterValue = countryFilter.value.toLowerCase();
        const cityFilterValue = cityFilter.value.toLowerCase();
        const latencyMin = latencyMinInput && latencyMinInput.value ? parseInt(latencyMinInput.value) : null;
        const latencyMax = latencyMaxInput && latencyMaxInput.value ? parseInt(latencyMaxInput.value) : null;

        return allProxies.filter(p => {
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
    };

    const renderTable = () => {
        const filteredProxies = getFilteredProxies();

        // Update filter count
        if (filterCount) {
            const fallbackMode = allProxies.some(proxy => proxy.source === 'fallback');
            const fallbackNote = fallbackMode ? ' (fallback data)' : '';
            filterCount.textContent = `Showing ${filteredProxies.length} of ${allProxies.length} proxies${fallbackNote}`;
        }

        if (filteredProxies.length === 0) {
            proxiesTable.classList.add('hidden');
            emptyState.classList.remove('hidden');
        } else {
            proxiesTable.classList.remove('hidden');
            emptyState.classList.add('hidden');
        }

        // Sort
        filteredProxies.sort((a, b) => {
            let valA, valB;
            if (currentSort.key === 'location') {
                valA = a.country_code || '';
                valB = b.country_code || '';
            } else {
                valA = a[currentSort.key];
                valB = b[currentSort.key];
            }

            if (valA < valB) return currentSort.asc ? -1 : 1;
            if (valA > valB) return currentSort.asc ? 1 : -1;
            return 0;
        });

        // Clamp currentPage to valid range after filtering/sorting
        const maxPage = Math.ceil(filteredProxies.length / proxiesPerPage) || 1;
        currentPage = Math.max(1, Math.min(currentPage, maxPage));

        const indexOfLastProxy = currentPage * proxiesPerPage;
        const indexOfFirstProxy = indexOfLastProxy - proxiesPerPage;
        const currentProxies = filteredProxies.slice(indexOfFirstProxy, indexOfLastProxy);

        tableBody.innerHTML = currentProxies.map((p, index) => {
            // Handle XX or unknown country codes
            const countryCode = (p.country_code && p.country_code !== 'XX') ? p.country_code : null;
            const country = countryCode || 'Unknown';
            const city = p.city || '';
            const location = city ? `${city}, ${country}` : country;
            const latency = p.latency ? `${p.latency}ms` : 'N/A';
            const protocol = p.protocol || 'N/A';
            const config = p.config || '';
            const rowClasses = ['proxy-row'];
            if (p.source === 'fallback') {
                rowClasses.push('proxy-row--fallback');
            }
            if (!p.is_working) {
                rowClasses.push('proxy-row--offline');
            }
            return `
                <tr class="${rowClasses.join(' ')}" style="--delay: ${index * 0.03}s" data-source="${p.source}">
                    <td>${protocol}${p.is_working ? '' : ' <span class="status-pill status-pill--offline">Offline</span>'}</td>
                    <td class="location-cell">
                        ${countryCode ? `<img src="https://flagcdn.com/w20/${countryCode.toLowerCase()}.png" alt="${countryCode}" class="country-flag" onerror="this.onerror=null;this.outerHTML='<i data-feather=\\\'globe\\\' class=\\\'country-flag-icon\\\'></i>'">` : `<i data-feather="globe" class="country-flag-icon"></i>`}
                        <span>${location}</span>
                    </td>
                    <td>${latency}</td>
                    <td><button class="btn btn-secondary copy-btn" data-config="${encodeURIComponent(config)}" aria-label="Copy proxy link"><i data-feather="copy"></i></button></td>
                </tr>
            `;
        }).join('');
        if (window.inlineIcons) {
            window.inlineIcons.replace();
        }

        renderPagination(filteredProxies.length);
    };

    const renderPagination = (totalProxies) => {
        const totalPages = Math.ceil(totalProxies / proxiesPerPage) || 1;

        let paginationHTML = '';

        // Previous Button
        paginationHTML += `<button class="pagination-btn" id="first-btn" ${currentPage === 1 ? 'disabled' : ''}>&laquo; First</button>`;
        paginationHTML += `<button class="pagination-btn" id="prev-btn" ${currentPage === 1 ? 'disabled' : ''}>&lsaquo; Prev</button>`;

        // Page numbers with ellipsis
        const maxPagesToShow = 5;
        let startPage, endPage;

        if (totalPages <= maxPagesToShow) {
            startPage = 1;
            endPage = totalPages;
        } else {
            if (currentPage <= Math.floor(maxPagesToShow / 2)) {
                startPage = 1;
                endPage = maxPagesToShow;
            } else if (currentPage + Math.floor(maxPagesToShow / 2) >= totalPages) {
                startPage = totalPages - maxPagesToShow + 1;
                endPage = totalPages;
            } else {
                startPage = currentPage - Math.floor(maxPagesToShow / 2);
                endPage = currentPage + Math.floor(maxPagesToShow / 2);
            }
        }

        if (startPage > 1) {
            paginationHTML += `<button class="pagination-btn" data-page="1">1</button>`;
            if (startPage > 2) {
                paginationHTML += `<span class="pagination-ellipsis">...</span>`;
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `<button class="pagination-btn ${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
        }

        if (endPage < totalPages) {
            if (endPage < totalPages - 1) {
                paginationHTML += `<span class="pagination-ellipsis">...</span>`;
            }
            paginationHTML += `<button class="pagination-btn" data-page="${totalPages}">${totalPages}</button>`;
        }

        // Next Button
        paginationHTML += `<button class="pagination-btn" id="next-btn" ${currentPage === totalPages ? 'disabled' : ''}>Next &rsaquo;</button>`;
        paginationHTML += `<button class="pagination-btn" id="last-btn" ${currentPage === totalPages ? 'disabled' : ''}>Last &raquo;</button>`;

        paginationContainer.innerHTML = paginationHTML;
    };

    paginationContainer.addEventListener('click', (e) => {
        const totalPages = Math.ceil(getFilteredProxies().length / proxiesPerPage) || 1;
        if (e.target.matches('#first-btn')) {
            currentPage = 1;
            renderTable();
        } else if (e.target.matches('#prev-btn')) {
            currentPage = Math.max(1, currentPage - 1);
            renderTable();
        } else if (e.target.matches('#next-btn')) {
            currentPage = Math.min(totalPages, currentPage + 1);
            renderTable();
        } else if (e.target.matches('#last-btn')) {
            currentPage = totalPages;
            renderTable();
        } else if (e.target.matches('.pagination-btn[data-page]')) {
            currentPage = parseInt(e.target.dataset.page);
            renderTable();
        }
    });

    // Add event listeners for filters
    protocolFilter.addEventListener('input', renderTable);
    countryFilter.addEventListener('input', () => {
        const selectedOption = countryFilter.options[countryFilter.selectedIndex];
        const countryCode = selectedOption.dataset.countryCode || '';
        updateFlagDisplay(countryCode, 'country');
        renderTable();
    });
    cityFilter.addEventListener('input', () => {
        const selectedOption = cityFilter.options[cityFilter.selectedIndex];
        const countryCode = selectedOption.dataset.countryCode || '';
        updateFlagDisplay(countryCode, 'city');
        renderTable();
    });

    if (latencyMinInput) {
        latencyMinInput.addEventListener('input', renderTable);
    }
    if (latencyMaxInput) {
        latencyMaxInput.addEventListener('input', renderTable);
    }
    if (pageSizeSelector) {
        pageSizeSelector.addEventListener('change', (e) => {
            proxiesPerPage = parseInt(e.target.value);
            currentPage = 1; // Reset to first page
            renderTable();
        });
    }

    // Batch actions
    if (copyFilteredBtn) {
        copyFilteredBtn.addEventListener('click', () => {
            const proxies = getFilteredProxies();
            const configs = proxies.map(p => p.config).join('\n');
            copyToClipboard(configs, copyFilteredBtn);
        });
    }

    if (downloadFilteredBtn) {
        downloadFilteredBtn.addEventListener('click', () => {
            const proxies = getFilteredProxies();
            const configs = proxies.map(p => p.config).join('\n');
            const blob = new Blob([configs], { type: 'text/plain;charset=utf-8' });
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'filtered_proxies.txt';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(url);
        });
    }

    // Clear filters button
    if (clearFiltersBtn) {
        clearFiltersBtn.addEventListener('click', () => {
            protocolFilter.value = '';
            countryFilter.value = '';
            cityFilter.value = '';
            if (latencyMinInput) latencyMinInput.value = '';
            if (latencyMaxInput) latencyMaxInput.value = '';
            updateFlagDisplay('', 'country');
            updateFlagDisplay('', 'city');
            renderTable();
        });
    }

    document.querySelectorAll('#proxiesTable th[data-sort]').forEach(th => {
        th.addEventListener('click', () => {
            const sortKey = th.dataset.sort;
            if (currentSort.key === sortKey) {
                currentSort.asc = !currentSort.asc;
            } else {
                currentSort.key = sortKey;
                currentSort.asc = true;
            }

            document.querySelectorAll('#proxiesTable th[data-sort]').forEach(header => {
                if (header !== th) {
                    header.removeAttribute('aria-sort');
                }
            });
            th.setAttribute('aria-sort', currentSort.asc ? 'ascending' : 'descending');

            renderTable();
        });
    });

    // Helper function to get country name from country code
    function getCountryName(countryCode) {
        const countryNames = {
            'XX': 'Unknown',
            'US': 'United States', 'GB': 'United Kingdom', 'CA': 'Canada', 'DE': 'Germany',
            'FR': 'France', 'NL': 'Netherlands', 'SG': 'Singapore', 'JP': 'Japan',
            'AU': 'Australia', 'IN': 'India', 'BR': 'Brazil', 'RU': 'Russia',
            'CN': 'China', 'HK': 'Hong Kong', 'KR': 'South Korea', 'IT': 'Italy',
            'ES': 'Spain', 'SE': 'Sweden', 'CH': 'Switzerland', 'PL': 'Poland'
        };
        return countryNames[countryCode] || countryCode;
    }

    // Helper function to update flag displays
    function updateFlagDisplay(countryCode, type = 'country') {
        const displayEl = type === 'country'
            ? document.getElementById('countryFlagDisplay')
            : document.getElementById('cityFlagDisplay');

        if (!displayEl) return;

        if (!countryCode || countryCode === '') {
            displayEl.innerHTML = '<i data-feather="globe" class="country-flag-icon-small"></i>';
            if (window.inlineIcons) window.inlineIcons.replace();
        } else {
            displayEl.innerHTML = `<img src="https://flagcdn.com/w20/${countryCode.toLowerCase()}.png" alt="${countryCode}" onerror="this.outerHTML='<i data-feather=\\'globe\\' class=\\'country-flag-icon-small\\'></i>'">`;
        }
    }

    // Populate filter dropdowns dynamically with only available options
    function populateFilters() {
        // Get unique protocols, countries and cities (excluding XX and invalid values)
        const protocols = new Set();
        const countries = new Set();
        const cities = new Set();
        const cityToCountry = new Map(); // Map cities to their country codes

        allProxies.forEach(p => {
            if (p.protocol) protocols.add(p.protocol);
            // Exclude empty country codes
            if (p.country_code) {
                countries.add(p.country_code);
                if (p.city) {
                    cities.add(p.city);
                    cityToCountry.set(p.city, p.country_code);
                }
            }
        });

        // Populate protocol filter
        const sortedProtocols = Array.from(protocols).sort();
        protocolFilter.length = 1; // Preserve "All Protocols"
        sortedProtocols.forEach(protocol => {
            const option = document.createElement('option');
            option.value = protocol;
            option.textContent = protocol.toUpperCase();
            protocolFilter.appendChild(option);
        });

        // Sort and populate country filter with flags
        const sortedCountries = Array.from(countries).sort();
        countryFilter.length = 1; // Preserve "All Countries"
        sortedCountries.forEach(country => {
            const option = document.createElement('option');
            option.value = country;
            option.textContent = `${country} ${getCountryName(country)}`;
            option.dataset.countryCode = country;
            countryFilter.appendChild(option);
        });

        // Sort and populate city filter
        const sortedCities = Array.from(cities).sort();
        cityFilter.length = 1; // Preserve "All Cities"
        sortedCities.forEach(city => {
            const option = document.createElement('option');
            option.value = city;
            const countryCode = cityToCountry.get(city) || '';
            option.textContent = countryCode ? `${city} (${countryCode})` : city;
            option.dataset.countryCode = countryCode;
            cityFilter.appendChild(option);
        });

        // Store city to country mapping for later use
        window.cityToCountryMap = cityToCountry;
    }

    async function fetchAndRenderProxies() {
        const loadingContainer = document.getElementById('loadingContainer');
        const proxiesTable = document.getElementById('proxiesTable');

        if (loadingContainer) loadingContainer.classList.remove('hidden');
        proxiesTable.classList.add('hidden');

        try {
            allProxies = await window.api.fetchProxies();
            const fallbackMode = allProxies.some(proxy => proxy.source === 'fallback');
            if (fallbackMode && window.stateManager) {
                window.stateManager.setInfo('Showing the most recent tested proxies because no verified proxies are currently online.', true);
            }
            populateFilters();
            renderTable();
        } catch (error) {
            if (window.stateManager) {
                window.stateManager.setError('Failed to load proxies.', error);
            }
        } finally {
            if (loadingContainer) loadingContainer.classList.add('hidden');
        }
    }

    fetchAndRenderProxies();
});